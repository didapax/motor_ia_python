#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
motor_ia.py — Motor principal ADAN v3.0 (multi-área, historial persistente)
"""

import json
import random
import time
import re
import os
import uuid
import csv
import io
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime

from nlp_utils import (
    normalizar,
    mejor_coincidencia,
    detectar_intencion,
    extraer_palabras_clave,
    UMBRAL_SIMILITUD,
)

# ─── Rutas base ───────────────────────────────────────────────────────────────

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
AREAS_DIR     = os.path.join(BASE_DIR, "areas")
HISTORIAL_DIR = os.path.join(BASE_DIR, "historial")

os.makedirs(HISTORIAL_DIR, exist_ok=True)

UMBRAL_BUSQUEDA = 70

# ─── Config de área ───────────────────────────────────────────────────────────

_CONFIG_DEFAULT = {
    "nombre": "Asistente ADAN",
    "descripcion": "Asistente virtual de propósito general",
    "avatar": "🤖",
    "color_primario": "#7c6af7",
    "color_secundario": "#4ecdc4",
    "tema_restriccion": "",
    "mensaje_fuera_area": "No encontré información sobre ese tema. ¿Quieres enseñármelo?",
    "permitir_busqueda_web": True,
    "permitir_aprendizaje": True,
    "pin_admin": "1234",
}


def cargar_config(area: str) -> dict:
    """Carga la configuración de un área. Retorna config por defecto si no existe."""
    ruta = os.path.join(AREAS_DIR, area, "config.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            config = json.load(f)
        return {**_CONFIG_DEFAULT, **config}
    except FileNotFoundError:
        return dict(_CONFIG_DEFAULT)


def guardar_config(area: str, config: dict) -> bool:
    """Guarda la configuración de un área."""
    ruta = os.path.join(AREAS_DIR, area, "config.json")
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[ADAN] Error al guardar config: {e}")
        return False


def listar_areas() -> list[dict]:
    """Lista todas las áreas disponibles con su config básica."""
    areas = []
    if not os.path.exists(AREAS_DIR):
        return areas
    for nombre in sorted(os.listdir(AREAS_DIR)):
        ruta = os.path.join(AREAS_DIR, nombre)
        if os.path.isdir(ruta):
            config = cargar_config(nombre)
            areas.append({
                "id": nombre,
                "nombre": config["nombre"],
                "descripcion": config["descripcion"],
                "avatar": config["avatar"],
                "color_primario": config["color_primario"],
            })
    return areas


# ─── Base de Conocimiento ─────────────────────────────────────────────────────

class BaseConocimiento:
    """Base de conocimiento para un área específica."""

    def __init__(self, area: str = "general"):
        self.area = area
        self.ruta = os.path.join(AREAS_DIR, area, "mente.json")
        self.datos: dict = {}
        self.sinonimos: dict = {}
        self._cargar()

    def _cargar(self):
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                lista = json.load(f)
        except FileNotFoundError:
            lista = []
        except json.JSONDecodeError as e:
            print(f"[ADAN] Error JSON en {self.ruta}: {e}")
            lista = []

        self.datos = {}
        self.sinonimos = {}

        for item in lista:
            for clave, valor in item.items():
                clave_n = normalizar(clave)
                self.datos[clave_n] = {"_clave_original": clave, **valor}
                self.sinonimos[clave_n] = clave_n
                for sin in valor.get("sinonimos", []):
                    sin_n = normalizar(sin)
                    self.sinonimos[sin_n] = clave_n

    def recargar(self):
        self._cargar()

    def todas_las_claves(self) -> list[str]:
        return list(self.sinonimos.keys())

    def buscar(self, texto: str):
        texto_n = normalizar(texto)
        if texto_n in self.sinonimos:
            clave_n = self.sinonimos[texto_n]
            return self.datos.get(clave_n)
        candidatos = self.todas_las_claves()
        clave_encontrada, score = mejor_coincidencia(texto_n, candidatos, UMBRAL_BUSQUEDA)
        if clave_encontrada:
            clave_n = self.sinonimos.get(clave_encontrada, clave_encontrada)
            return self.datos.get(clave_n)
        return None

    def listar_entradas(self) -> list[dict]:
        """Retorna todas las entradas para el panel admin."""
        entradas = []
        for clave_n, valor in self.datos.items():
            entradas.append({
                "clave": valor.get("_clave_original", clave_n),
                "clave_n": clave_n,
                "respuestas": valor.get("respuestas", [valor.get("respuesta", "")]),
                "explica": valor.get("explica", ""),
                "otra_pregunta": valor.get("otra_pregunta", ""),
                "sinonimos": valor.get("sinonimos", []),
                "intencion": valor.get("intencion", ""),
            })
        return sorted(entradas, key=lambda x: x["clave"])

    def guardar_entrada(self, clave: str, explica: str, respuestas: list,
                        otra_pregunta: str, sinonimos: list) -> bool:
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                lista = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            lista = []

        nueva = {
            "respuestas": respuestas if isinstance(respuestas, list) else [respuestas],
            "explica": explica,
            "otra_pregunta": otra_pregunta,
            "sinonimos": sinonimos if isinstance(sinonimos, list) else [s.strip() for s in sinonimos.split("|") if s.strip()],
            "intencion": detectar_intencion(clave),
        }

        actualizado = False
        clave_upper = clave.upper()
        for item in lista:
            if clave_upper in item:
                item[clave_upper] = nueva
                actualizado = True
                break
        if not actualizado:
            lista.append({clave_upper: nueva})

        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=4)

        self.recargar()
        return True

    def eliminar_entrada(self, clave: str) -> bool:
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                lista = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return False

        clave_upper = clave.upper()
        lista_nueva = [item for item in lista if clave_upper not in item]

        if len(lista_nueva) == len(lista):
            return False  # No se encontró

        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(lista_nueva, f, ensure_ascii=False, indent=4)

        self.recargar()
        return True

    def importar_csv(self, contenido_csv: str) -> dict:
        """
        Importa entradas desde CSV.
        Formato: clave,explica,respuesta,otra_pregunta,sinonimos
        sinonimos separados por | dentro del campo.
        Retorna {"importadas": N, "errores": [...]}
        """
        importadas = 0
        errores = []
        reader = csv.DictReader(io.StringIO(contenido_csv))

        for i, fila in enumerate(reader, start=2):
            try:
                clave = fila.get("clave", "").strip()
                if not clave:
                    errores.append(f"Fila {i}: clave vacía")
                    continue
                respuesta = fila.get("respuesta", "").strip()
                explica = fila.get("explica", respuesta[:50]).strip()
                otra_pregunta = fila.get("otra_pregunta", "").strip()
                sins_raw = fila.get("sinonimos", "").strip()
                sinonimos = [s.strip() for s in sins_raw.split("|") if s.strip()]

                self.guardar_entrada(clave, explica, [respuesta], otra_pregunta, sinonimos)
                importadas += 1
            except Exception as e:
                errores.append(f"Fila {i}: {str(e)}")

        return {"importadas": importadas, "errores": errores}

    def exportar_csv(self) -> str:
        """Exporta la base de conocimiento a formato CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["clave", "explica", "respuesta", "otra_pregunta", "sinonimos"])
        for entrada in self.listar_entradas():
            respuesta = entrada["respuestas"][0] if entrada["respuestas"] else ""
            writer.writerow([
                entrada["clave"],
                entrada["explica"],
                respuesta,
                entrada["otra_pregunta"],
                "|".join(entrada["sinonimos"]),
            ])
        return output.getvalue()

    def estadisticas(self) -> dict:
        return {
            "total_entradas": len(self.datos),
            "total_sinonimos": len(self.sinonimos),
        }


# ─── Historial Persistente ────────────────────────────────────────────────────

class Historial:
    """Gestiona el historial de conversación de una sesión."""

    def __init__(self, session_id: str, area: str):
        self.session_id = session_id
        self.area = area
        self.ruta = os.path.join(HISTORIAL_DIR, f"{session_id}.json")
        self.mensajes: list[dict] = []
        self.inicio = datetime.now().isoformat()
        self._cargar()

    def _cargar(self):
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.mensajes = data.get("mensajes", [])
                self.inicio = data.get("inicio", self.inicio)
        except FileNotFoundError:
            self.mensajes = []

    def agregar(self, rol: str, mensaje: str, fuente: str = ""):
        self.mensajes.append({
            "rol": rol,
            "mensaje": mensaje,
            "fuente": fuente,
            "timestamp": datetime.now().isoformat(),
        })
        self._guardar()

    def _guardar(self):
        data = {
            "session_id": self.session_id,
            "area": self.area,
            "inicio": self.inicio,
            "ultimo_acceso": datetime.now().isoformat(),
            "total_mensajes": len(self.mensajes),
            "mensajes": self.mensajes[-100:],  # máximo 100 mensajes
        }
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def como_lista(self) -> list[dict]:
        return self.mensajes

    def limpiar(self):
        self.mensajes = []
        self._guardar()


def listar_historiales(area: str = None) -> list[dict]:
    """Lista todos los historiales, opcionalmente filtrados por área."""
    historiales = []
    if not os.path.exists(HISTORIAL_DIR):
        return historiales
    for archivo in sorted(os.listdir(HISTORIAL_DIR), reverse=True):
        if archivo.endswith(".json"):
            ruta = os.path.join(HISTORIAL_DIR, archivo)
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if area and data.get("area") != area:
                    continue
                historiales.append({
                    "session_id": data.get("session_id"),
                    "area": data.get("area"),
                    "inicio": data.get("inicio"),
                    "ultimo_acceso": data.get("ultimo_acceso"),
                    "total_mensajes": data.get("total_mensajes", 0),
                })
            except Exception:
                pass
    return historiales


# ─── Cache de bases por área ──────────────────────────────────────────────────

_bases: dict[str, BaseConocimiento] = {}
_historiales: dict[str, Historial] = {}


def obtener_base(area: str) -> BaseConocimiento:
    if area not in _bases:
        _bases[area] = BaseConocimiento(area)
    return _bases[area]


def obtener_historial(session_id: str, area: str) -> Historial:
    key = f"{session_id}:{area}"
    if key not in _historiales:
        _historiales[key] = Historial(session_id, area)
    return _historiales[key]


# ─── Búsqueda en Internet ─────────────────────────────────────────────────────

def _limpiar_texto(texto: str) -> str:
    texto = re.sub(r'\[\d+\]', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    if len(texto) > 400:
        texto = texto[:400].rsplit(' ', 1)[0] + "..."
    return texto


def buscar_duckduckgo(termino: str) -> tuple[str, str]:
    params = {"q": termino, "format": "json", "no_html": "1", "skip_disambig": "1", "l": "es_ES"}
    try:
        r = requests.get("https://api.duckduckgo.com/", params=params, timeout=8)
        if r.ok:
            data = r.json()
            abstract = data.get("AbstractText", "").strip()
            if abstract:
                return _limpiar_texto(abstract), "DuckDuckGo"
            for item in data.get("RelatedTopics", []):
                if isinstance(item, dict) and item.get("Text"):
                    return _limpiar_texto(item["Text"][:300]), "DuckDuckGo"
    except Exception:
        pass
    return "", ""


def buscar_wikipedia(termino: str) -> tuple[str, str]:
    try:
        url = f"https://es.wikipedia.org/wiki/{quote(termino)}"
        r = requests.get(url, timeout=8)
        if r.ok:
            soup = BeautifulSoup(r.content, 'html.parser')
            for p in soup.find_all('p'):
                texto = p.get_text().strip()
                if len(texto) > 50:
                    return _limpiar_texto(texto), "Wikipedia"
    except Exception:
        pass
    return "", ""


def buscar_en_internet(texto: str) -> tuple[str, str]:
    palabras = extraer_palabras_clave(texto)
    termino = " ".join(palabras[:2]) if palabras else texto
    r, f = buscar_duckduckgo(termino)
    if r:
        return r, f
    termino_wiki = "_".join(p.capitalize() for p in palabras[:2]) if palabras else texto.capitalize()
    r, f = buscar_wikipedia(termino_wiki)
    if r:
        return r, f
    return buscar_wikipedia(texto.capitalize())


# ─── Selección de respuesta ───────────────────────────────────────────────────

def _seleccionar_respuesta(entrada: dict) -> str:
    respuestas = entrada.get("respuestas", [])
    if not respuestas:
        respuestas = [r for r in [entrada.get("respuesta", ""), entrada.get("explica", "")] if r]
    if not respuestas:
        return ""
    texto = random.choice(respuestas)
    otra = entrada.get("otra_pregunta", "")
    return f"{texto}\n\n{otra}" if otra else texto


# ─── Pipeline principal ───────────────────────────────────────────────────────

def _buscar_en_base(texto: str, base: BaseConocimiento) -> tuple[str, str]:
    entrada = base.buscar(texto)
    if entrada:
        return _seleccionar_respuesta(entrada), "local"
    return "", ""


def procesar(texto: str, area: str = "general", session_id: str = None) -> dict:
    """
    Punto de entrada principal del motor ADAN v3.0.

    Args:
        texto: Mensaje del usuario
        area: Área activa
        session_id: ID de sesión para historial

    Returns:
        dict con: respuesta, fuente, intencion, encontrado
    """
    if not session_id:
        session_id = str(uuid.uuid4())

    config = cargar_config(area)
    base = obtener_base(area)
    historial = obtener_historial(session_id, area)

    texto_n = normalizar(texto)
    intencion = detectar_intencion(texto)

    historial.agregar("usuario", texto)

    # 1. Búsqueda exacta + fuzzy en base local
    respuesta, fuente = _buscar_en_base(texto_n, base)

    # 2. Búsqueda token a token (cubre "hola adan", "buenos dias amigo")
    if not respuesta:
        tokens = texto_n.split()
        for i in range(len(tokens) - 1):
            bigrama = f"{tokens[i]} {tokens[i+1]}"
            respuesta, fuente = _buscar_en_base(bigrama, base)
            if respuesta:
                break
        if not respuesta:
            for token in tokens:
                if len(token) > 2:
                    respuesta, fuente = _buscar_en_base(token, base)
                    if respuesta:
                        break

    # 3. Búsqueda web (solo si área lo permite)
    if not respuesta and intencion in ("pregunta", "desconocido"):
        if config.get("permitir_busqueda_web", True):
            palabras = extraer_palabras_clave(texto)
            if len(palabras) >= 2:
                compuesto = " ".join(palabras[:2])
                respuesta, fuente = _buscar_en_base(compuesto, base)
            if not respuesta:
                respuesta, fuente = buscar_en_internet(texto)
        else:
            # Área con restricción de tema
            respuesta = config.get("mensaje_fuera_area", "")
            fuente = "restriccion"

    if respuesta:
        historial.agregar("adan", respuesta, fuente)

    return {
        "respuesta": respuesta,
        "fuente": fuente,
        "intencion": intencion,
        "encontrado": bool(respuesta),
        "session_id": session_id,
    }


def aprender(clave: str, explica: str, respuesta: str, otra_pregunta: str,
             sinonimos: list = None, area: str = "general") -> bool:
    """Agrega o actualiza una entrada en la base de un área."""
    base = obtener_base(area)
    _bases.pop(area, None)  # Invalidar cache
    return base.guardar_entrada(
        clave=clave,
        explica=explica,
        respuestas=[respuesta],
        otra_pregunta=otra_pregunta,
        sinonimos=sinonimos or [],
    )


# ─── Compatibilidad legacy ────────────────────────────────────────────────────

def init(texto: str, base: str = "local") -> tuple[str, str]:
    """Compatibilidad con ia.py (CLI)."""
    resultado = procesar(texto, area="general")
    return resultado["respuesta"], resultado["fuente"]


def limpiar(cadena: str) -> str:
    return normalizar(cadena)


def obtener_estadisticas(area: str = "general") -> dict:
    return obtener_base(area).estadisticas()


def obtener_contexto():
    """Stub para compatibilidad con ia.py."""
    class _Ctx:
        def como_texto(self): return ""
        def limpiar(self): pass
    return _Ctx()
