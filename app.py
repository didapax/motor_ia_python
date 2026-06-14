#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
app.py — Servidor Flask ADAN v3.0
"""

import os
import uuid
from flask import Flask, request, jsonify, render_template, session, send_file
import motor_ia
import io

app = Flask(__name__)
app.secret_key = os.environ.get("ADAN_SECRET", "adan-secret-2024-motor-ia")

# ─── Chat ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    mensaje = data.get("mensaje", "").strip()
    area = data.get("area", "general").strip() or "general"

    if not mensaje:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400

    session_id = session.get("session_id", str(uuid.uuid4()))
    resultado = motor_ia.procesar(mensaje, area=area, session_id=session_id)
    return jsonify(resultado)


@app.route("/api/areas", methods=["GET"])
def areas():
    return jsonify(motor_ia.listar_areas())


@app.route("/api/config/<area>", methods=["GET"])
def config_area(area):
    config = motor_ia.cargar_config(area)
    # No exponer PIN en el frontend
    config_publica = {k: v for k, v in config.items() if k != "pin_admin"}
    return jsonify(config_publica)


@app.route("/api/stats/<area>", methods=["GET"])
def stats(area):
    return jsonify(motor_ia.obtener_estadisticas(area))


# ─── Aprendizaje (chat) ────────────────────────────────────────────────────────

@app.route("/api/aprender", methods=["POST"])
def aprender():
    data = request.get_json(silent=True) or {}
    area = data.get("area", "general")
    config = motor_ia.cargar_config(area)

    if not config.get("permitir_aprendizaje", True):
        return jsonify({"error": "El aprendizaje está desactivado para esta área"}), 403

    clave = data.get("clave", "").strip()
    explica = data.get("explica", "").strip()
    respuesta = data.get("respuesta", "").strip()
    otra_pregunta = data.get("otra_pregunta", "").strip()
    sinonimos_raw = data.get("sinonimos", "")
    sinonimos = [s.strip() for s in sinonimos_raw.split("|") if s.strip()] if isinstance(sinonimos_raw, str) else sinonimos_raw

    if not clave or not explica or not respuesta:
        return jsonify({"error": "Se requieren clave, explica y respuesta"}), 400

    exito = motor_ia.aprender(clave, explica, respuesta, otra_pregunta, sinonimos, area)
    if exito:
        return jsonify({"mensaje": f"¡Aprendido! Ahora conozco sobre '{clave}' en el área '{area}'."})
    return jsonify({"error": "No se pudo guardar"}), 500


# ─── Admin ─────────────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    area = data.get("area", "general")
    pin = data.get("pin", "")
    config = motor_ia.cargar_config(area)
    if str(pin) == str(config.get("pin_admin", "1234")):
        session[f"admin_{area}"] = True
        return jsonify({"ok": True, "config": {k: v for k, v in config.items() if k != "pin_admin"}})
    return jsonify({"ok": False, "error": "PIN incorrecto"}), 401


def _verificar_admin(area: str):
    """Verifica que la sesión tenga acceso admin al área."""
    return session.get(f"admin_{area}", False)


@app.route("/api/admin/entradas/<area>", methods=["GET"])
def admin_listar(area):
    if not _verificar_admin(area):
        return jsonify({"error": "No autorizado"}), 401
    base = motor_ia.obtener_base(area)
    return jsonify(base.listar_entradas())


@app.route("/api/admin/entrada/<area>", methods=["POST"])
def admin_crear(area):
    if not _verificar_admin(area):
        return jsonify({"error": "No autorizado"}), 401
    data = request.get_json(silent=True) or {}
    base = motor_ia.obtener_base(area)
    respuestas_raw = data.get("respuestas", data.get("respuesta", ""))
    respuestas = respuestas_raw if isinstance(respuestas_raw, list) else [respuestas_raw]
    sinonimos_raw = data.get("sinonimos", "")
    sinonimos = sinonimos_raw if isinstance(sinonimos_raw, list) else [s.strip() for s in sinonimos_raw.split("|") if s.strip()]
    ok = base.guardar_entrada(
        clave=data.get("clave", ""),
        explica=data.get("explica", ""),
        respuestas=respuestas,
        otra_pregunta=data.get("otra_pregunta", ""),
        sinonimos=sinonimos,
    )
    # Invalidar cache
    motor_ia._bases.pop(area, None)
    return jsonify({"ok": ok})


@app.route("/api/admin/entrada/<area>/<clave>", methods=["DELETE"])
def admin_eliminar(area, clave):
    if not _verificar_admin(area):
        return jsonify({"error": "No autorizado"}), 401
    base = motor_ia.obtener_base(area)
    ok = base.eliminar_entrada(clave)
    motor_ia._bases.pop(area, None)
    return jsonify({"ok": ok})


@app.route("/api/admin/importar/<area>", methods=["POST"])
def admin_importar(area):
    if not _verificar_admin(area):
        return jsonify({"error": "No autorizado"}), 401
    if "archivo" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    archivo = request.files["archivo"]
    contenido = archivo.read().decode("utf-8-sig")  # utf-8-sig para manejar BOM de Excel
    base = motor_ia.obtener_base(area)
    resultado = base.importar_csv(contenido)
    motor_ia._bases.pop(area, None)
    return jsonify(resultado)


@app.route("/api/admin/exportar/<area>", methods=["GET"])
def admin_exportar(area):
    if not _verificar_admin(area):
        return jsonify({"error": "No autorizado"}), 401
    base = motor_ia.obtener_base(area)
    csv_data = base.exportar_csv()
    return send_file(
        io.BytesIO(csv_data.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"mente_{area}.csv",
    )


@app.route("/api/admin/config/<area>", methods=["PUT"])
def admin_actualizar_config(area):
    if not _verificar_admin(area):
        return jsonify({"error": "No autorizado"}), 401
    data = request.get_json(silent=True) or {}
    config_actual = motor_ia.cargar_config(area)
    # Campos editables (sin PIN por seguridad — PIN se actualiza por separado)
    campos_editables = [
        "nombre", "descripcion", "avatar", "color_primario", "color_secundario",
        "tema_restriccion", "mensaje_fuera_area", "permitir_busqueda_web", "permitir_aprendizaje"
    ]
    for campo in campos_editables:
        if campo in data:
            config_actual[campo] = data[campo]
    if "pin_nuevo" in data and data["pin_nuevo"]:
        config_actual["pin_admin"] = str(data["pin_nuevo"])
    ok = motor_ia.guardar_config(area, config_actual)
    return jsonify({"ok": ok})


# ─── Historial ─────────────────────────────────────────────────────────────────

@app.route("/api/admin/historial/<area>", methods=["GET"])
def admin_historial(area):
    if not _verificar_admin(area):
        return jsonify({"error": "No autorizado"}), 401
    return jsonify(motor_ia.listar_historiales(area))


@app.route("/api/admin/historial/<area>/<session_id>", methods=["GET"])
def admin_historial_detalle(area, session_id):
    if not _verificar_admin(area):
        return jsonify({"error": "No autorizado"}), 401
    hist = motor_ia.obtener_historial(session_id, area)
    return jsonify({"mensajes": hist.como_lista()})


@app.route("/api/historial/limpiar", methods=["POST"])
def limpiar_historial():
    data = request.get_json(silent=True) or {}
    area = data.get("area", "general")
    session_id = session.get("session_id", "")
    if session_id:
        hist = motor_ia.obtener_historial(session_id, area)
        hist.limpiar()
        session["session_id"] = str(uuid.uuid4())
    return jsonify({"ok": True})


# ─── Inicio ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🤖 ADAN v3.0 — Motor de Asistentes Especializados")
    print("   Chat:  http://localhost:5000")
    print("   Admin: http://localhost:5000/admin\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
