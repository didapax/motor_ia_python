#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
app.py — Servidor web Flask para el asistente ADAN
"""

from flask import Flask, request, jsonify, render_template
import motor_ia
from nlp_utils import detectar_intencion, normalizar
import time

app = Flask(__name__)

# ─── Rutas de la interfaz ─────────────────────────────────────────────────────

@app.route("/")
def index():
    """Página principal — interfaz de chat."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Endpoint principal de conversación.
    Recibe: { "mensaje": "texto del usuario" }
    Retorna: { "respuesta": "...", "fuente": "...", "intencion": "..." }
    """
    data = request.get_json(silent=True)
    if not data or "mensaje" not in data:
        return jsonify({"error": "Se requiere el campo 'mensaje'"}), 400

    mensaje = data["mensaje"].strip()
    if not mensaje:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400

    intencion = detectar_intencion(mensaje)

    respuesta, fuente = motor_ia.init(mensaje)

    if not respuesta:
        respuesta = ""

    return jsonify({
        "respuesta": respuesta,
        "fuente": fuente,
        "intencion": intencion,
        "encontrado": bool(respuesta),
    })


@app.route("/api/aprender", methods=["POST"])
def aprender():
    """
    Endpoint para enseñar algo nuevo a ADAN.
    Recibe: { "clave": "...", "explica": "...", "respuesta": "...", "otra_pregunta": "...", "sinonimo": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Datos inválidos"}), 400

    clave = data.get("clave", "").strip()
    explica = data.get("explica", "").strip()
    respuesta = data.get("respuesta", "").strip()
    otra_pregunta = data.get("otra_pregunta", "").strip()
    sinonimo = data.get("sinonimo", "").strip()

    if not clave or not explica or not respuesta:
        return jsonify({"error": "Se requieren al menos: clave, explica y respuesta"}), 400

    exito = motor_ia.aprender(
        clave=normalizar(clave),
        explica=explica,
        respuesta=respuesta,
        otra_pregunta=otra_pregunta,
        sinonimo=normalizar(sinonimo) if sinonimo else "",
    )

    if exito:
        return jsonify({"mensaje": f"¡Aprendido! Ahora conozco sobre '{clave}'."})
    else:
        return jsonify({"error": "No se pudo guardar la información"}), 500


@app.route("/api/stats", methods=["GET"])
def stats():
    """Retorna estadísticas de la base de conocimiento."""
    return jsonify(motor_ia.obtener_estadisticas())


@app.route("/api/historial", methods=["GET"])
def historial():
    """Retorna el historial de la conversación actual."""
    ctx = motor_ia.obtener_contexto()
    return jsonify({"historial": ctx.historial})


@app.route("/api/limpiar", methods=["POST"])
def limpiar_historial():
    """Limpia el historial de la conversación."""
    motor_ia.obtener_contexto().limpiar()
    return jsonify({"mensaje": "Historial limpiado correctamente."})


# ─── Inicio ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🤖 ADAN Web Server iniciando...")
    print("   Accede en: http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
