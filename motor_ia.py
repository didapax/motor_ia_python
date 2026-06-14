#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
motor_ia.py — Motor principal del asistente ADAN (versión mejorada)
"""

import json
import random
import time
import re
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

from nlp_utils import (
    normalizar,
    similitud,
    mejor_coincidencia,
    detectar_intencion,
    extraer_palabras_clave,
    UMBRAL_SIMILITUD,
)


# ─── Constantes ───────────────────────────────────────────────────────────────

RUTA_MENTE = "mente.json"
UMBRAL_BUSQUEDA = 70  # Umbral mínimo para aceptar una coincidencia fuzzy


# ─── Clase: Base de Conocimiento ──────────────────────────────────────────────

class BaseConocimiento:
    """
    Gestiona la base de conocimiento local (mente.json).
    Construye un índice en memoria para búsqueda rápida y fuzzy.
    """

    def __init__(self, ruta: str = RUTA_MENTE):
        self.ruta = ruta
        self.datos: dict = {}          # clave_normalizada → entrada completa
        self.sinonimos: dict = {}      # sinonimo_normalizado → clave_normalizada
        self._cargar()

    def _cargar(self):
        """Carga el JSON y construye los índices en memoria."""
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                lista = json.load(f)
        except FileNotFoundError:
            print(f"[ADAN] Advertencia: No se encontró '{self.ruta}'. Iniciando con base vacía.")
            lista = []
        except json.JSONDecodeError as e:
            print(f"[ADAN] Error al leer '{self.ruta}': {e}")
            lista = []

        self.datos = {}
        self.sinonimos = {}

        for item in lista:
            for clave, valor in item.items():
                clave_n = normalizar(clave)
                self.datos[clave_n] = valor
                # Registrar la clave como su propio sinónimo
                self.sinonimos[clave_n] = clave_n
                # Registrar sinónimos adicionales
                for sin in valor.get("sinonimos", []):
                    sin_n = normalizar(sin)
                    self.sinonimos[sin_n] = clave_n

    def recargar(self):
        """Recarga los datos desde disco (útil tras aprender algo nuevo)."""
        self._cargar()

    def todas_las_claves(self) -> list[str]:
        """Devuelve todas las claves y sinónimos normalizados."""
        return list(self.sinonimos.keys())

    def buscar(self, texto: str):
        """
        Busca una entrada en la base de conocimiento.
        1. Búsqueda exacta sobre claves y sinónimos
        2. Búsqueda fuzzy si no hay exacta
        Retorna la entrada (dict) o None.
        """
        texto_n = normalizar(texto)

        # 1. Búsqueda exacta
        if texto_n in self.sinonimos:
            clave_n = self.sinonimos[texto_n]
            return self.datos.get(clave_n)

        # 2. Búsqueda fuzzy
        candidatos = self.todas_las_claves()
        clave_encontrada, score = mejor_coincidencia(texto_n, candidatos, UMBRAL_BUSQUEDA)
        if clave_encontrada:
            clave_n = self.sinonimos.get(clave_encontrada, clave_encontrada)
            return self.datos.get(clave_n)

        return None

    def guardar_entrada(self, clave: str, explica: str, respuesta: str, otra_pregunta: str, sinonimo: str = ""):
        """
        Guarda una nueva entrada en el archivo JSON y recarga el índice.
        """
        clave_n = normalizar(clave)
        nueva_entrada = {
            clave: {
                "respuestas": [respuesta],
                "explica": explica,
                "otra_pregunta": otra_pregunta,
                "sinonimos": [sinonimo] if sinonimo and sinonimo != clave else [],
                "intencion": detectar_intencion(clave),
            }
        }

        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                lista = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            lista = []

        # Actualizar si existe, agregar si no
        actualizado = False
        for item in lista:
            if clave in item:
                item[clave] = nueva_entrada[clave]
                actualizado = True
                break
        if not actualizado:
            lista.append(nueva_entrada)

        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=4)

        self.recargar()

    def estadisticas(self) -> dict:
        """Retorna estadísticas de la base de conocimiento."""
        return {
            "total_entradas": len(self.datos),
            "total_sinonimos": len(self.sinonimos),
            "claves": list(self.datos.keys()),
        }


# ─── Clase: Contexto de Conversación ──────────────────────────────────────────

class ContextoConversacion:
    """
    Mantiene el historial de la conversación actual en memoria.
    """

    def __init__(self, max_turnos: int = 10):
        self.max_turnos = max_turnos
        self.historial: list[dict] = []
        self.ultimo_tema: str = ""

    def agregar(self, rol: str, mensaje: str, fuente: str = ""):
        """
        Agrega un turno al historial.
        rol: 'usuario' o 'adan'
        fuente: 'local', 'wikipedia', 'duckduckgo', 'aprendido'
        """
        self.historial.append({
            "rol": rol,
            "mensaje": mensaje,
            "fuente": fuente,
            "timestamp": time.time(),
        })
        # Mantener solo los últimos N turnos
        if len(self.historial) > self.max_turnos * 2:
            self.historial = self.historial[-(self.max_turnos * 2):]

    def ultimo_mensaje_usuario(self) -> str:
        """Retorna el último mensaje del usuario (antes del actual)."""
        mensajes_usuario = [h for h in self.historial[:-1] if h["rol"] == "usuario"]
        return mensajes_usuario[-1]["mensaje"] if mensajes_usuario else ""

    def como_texto(self) -> str:
        """Retorna el historial formateado como texto."""
        lineas = []
        for h in self.historial:
            prefijo = "Tú" if h["rol"] == "usuario" else "ADAN"
            lineas.append(f"{prefijo}: {h['mensaje']}")
        return "\n".join(lineas)

    def limpiar(self):
        """Limpia el historial."""
        self.historial = []
        self.ultimo_tema = ""


# ─── Búsqueda en Internet ─────────────────────────────────────────────────────

def _limpiar_texto_wikipedia(texto: str) -> str:
    """Elimina referencias [1], [2], etc. y limpia el texto de Wikipedia."""
    texto = re.sub(r'\[\d+\]', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    # Limitar a 400 caracteres para respuestas concisas
    if len(texto) > 400:
        texto = texto[:400].rsplit(' ', 1)[0] + "..."
    return texto


def buscar_wikipedia(termino: str) -> tuple[str, str]:
    """
    Busca información en Wikipedia en español.
    Retorna (texto, fuente) o ("", "") si no encuentra.
    """
    encoded = quote(termino)
    url = f"https://es.wikipedia.org/wiki/{encoded}"
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Verificar si es una página de desambiguación
            if soup.find('div', {'id': 'mw-content-text'}):
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    texto = p.get_text().strip()
                    if len(texto) > 50:
                        return _limpiar_texto_wikipedia(texto), "Wikipedia"
    except Exception:
        pass
    return "", ""


def buscar_duckduckgo(termino: str) -> tuple[str, str]:
    """
    Usa la Instant Answer API de DuckDuckGo (gratuita, sin API key).
    Retorna (texto, fuente) o ("", "") si no encuentra.
    """
    url = "https://api.duckduckgo.com/"
    params = {
        "q": termino,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
        "l": "es_ES",
    }
    try:
        response = requests.get(url, params=params, timeout=8)
        if response.status_code == 200:
            data = response.json()
            abstract = data.get("AbstractText", "").strip()
            if abstract:
                if len(abstract) > 400:
                    abstract = abstract[:400].rsplit(' ', 1)[0] + "..."
                return abstract, "DuckDuckGo"
            # Intentar con el primer resultado relacionado
            related = data.get("RelatedTopics", [])
            for item in related:
                if isinstance(item, dict) and item.get("Text"):
                    texto = item["Text"][:300]
                    return texto, "DuckDuckGo"
    except Exception:
        pass
    return "", ""


def buscar_en_internet(texto: str) -> tuple[str, str]:
    """
    Busca información en internet usando múltiples fuentes.
    Retorna (respuesta, fuente).
    """
    palabras = extraer_palabras_clave(texto)
    termino_principal = " ".join(palabras[:2]) if palabras else texto

    # Intentar primero DuckDuckGo (más rápido)
    respuesta, fuente = buscar_duckduckgo(termino_principal)
    if respuesta:
        return respuesta, fuente

    # Fallback a Wikipedia
    termino_wiki = "_".join(p.capitalize() for p in palabras[:2]) if palabras else texto.capitalize()
    respuesta, fuente = buscar_wikipedia(termino_wiki)
    if respuesta:
        return respuesta, fuente

    # Último intento con término completo en Wikipedia
    respuesta, fuente = buscar_wikipedia(texto.capitalize())
    return respuesta, fuente


# ─── Motor Principal ──────────────────────────────────────────────────────────

# Instancia global de la base de conocimiento
_base = BaseConocimiento()
_contexto = ContextoConversacion()


def _seleccionar_respuesta(entrada: dict) -> str:
    """
    Selecciona una respuesta de la entrada del conocimiento.
    Prioriza el campo 'respuestas' (lista), con fallback a 'explica'.
    """
    respuestas = entrada.get("respuestas", [])
    if not respuestas:
        # Compatibilidad con formato antiguo
        respuesta_simple = entrada.get("respuesta", "")
        explica = entrada.get("explica", "")
        respuestas = [r for r in [respuesta_simple, explica] if r]

    if not respuestas:
        return ""

    texto = random.choice(respuestas)
    otra = entrada.get("otra_pregunta", "")

    if otra:
        return f"{texto}\n\n{otra}"
    return texto


def responder_desde_base(texto: str) -> tuple[str, str]:
    """
    Busca una respuesta en la base de conocimiento local.
    Retorna (respuesta, fuente) o ("", "").
    """
    entrada = _base.buscar(texto)
    if entrada:
        return _seleccionar_respuesta(entrada), "local"
    return "", ""


def analizar_y_responder(texto: str) -> tuple[str, str]:
    """
    Pipeline completo de procesamiento:
    1. Base de conocimiento — texto completo (exacta + fuzzy)
    2. Búsqueda token a token (maneja "hola adan", "buenas tardes amigo", etc.)
    3. Búsqueda por bigramas y palabras clave extraídas (para preguntas)
    4. Búsqueda en internet como fallback final
    Retorna (respuesta, fuente).
    """
    texto_n = normalizar(texto)
    intencion = detectar_intencion(texto)

    # 1. Buscar texto completo en base local
    respuesta, fuente = responder_desde_base(texto_n)
    if respuesta:
        return respuesta, fuente

    # 2. Búsqueda token a token — cubre saludos/despedidas con palabras extra
    tokens = texto_n.split()
    # Probar bigramas primero (más específicos)
    for i in range(len(tokens) - 1):
        bigrama = f"{tokens[i]} {tokens[i+1]}"
        respuesta, fuente = responder_desde_base(bigrama)
        if respuesta:
            return respuesta, fuente
    # Luego tokens individuales
    for token in tokens:
        if len(token) > 2:
            respuesta, fuente = responder_desde_base(token)
            if respuesta:
                return respuesta, fuente

    # 3. Para preguntas, búsqueda adicional por palabras clave semánticas
    if intencion in ("pregunta", "desconocido"):
        palabras = extraer_palabras_clave(texto)

        if len(palabras) >= 2:
            compuesto = " ".join(palabras[:2])
            respuesta, fuente = responder_desde_base(compuesto)
            if respuesta:
                return respuesta, fuente

        # 4. Buscar en internet
        respuesta, fuente = buscar_en_internet(texto)
        if respuesta:
            return respuesta, fuente

    return "", ""


def init(texto: str, base: str = "local") -> tuple[str, str]:
    """
    Punto de entrada principal del motor ADAN.
    
    Args:
        texto: El mensaje del usuario
        base: Fuente de datos ('local' por defecto, parámetro legacy)
    
    Returns:
        (respuesta, fuente) donde fuente indica de dónde vino la respuesta.
    """
    # Recargar base si es necesario (soporte para base legacy)
    global _base
    if base != "local" and not hasattr(_base, '_inicializado'):
        _base = BaseConocimiento()

    respuesta, fuente = analizar_y_responder(texto)

    # Registrar en contexto
    _contexto.agregar("usuario", texto)
    if respuesta:
        _contexto.agregar("adan", respuesta, fuente)

    return respuesta, fuente


def aprender(clave: str, explica: str, respuesta: str, otra_pregunta: str, sinonimo: str = "") -> bool:
    """
    Agrega o actualiza una entrada en la base de conocimiento.
    Retorna True si se guardó correctamente.
    """
    try:
        _base.guardar_entrada(normalizar(clave), explica, respuesta, otra_pregunta, normalizar(sinonimo))
        return True
    except Exception as e:
        print(f"[ADAN] Error al aprender: {e}")
        return False


def obtener_contexto() -> ContextoConversacion:
    """Retorna el objeto de contexto actual."""
    return _contexto


def obtener_estadisticas() -> dict:
    """Retorna estadísticas de la base de conocimiento."""
    return _base.estadisticas()


# ─── Utilidades Legacy (compatibilidad con ia.py existente) ───────────────────

def limpiar(cadena: str) -> str:
    """Limpia la cadena eliminando caracteres especiales (legacy)."""
    return normalizar(cadena)


def agregar_elemento_lista_json(ruta: str, clave_lista: str = "", nuevo_elemento: dict = None):
    """Compatibilidad con el formato antiguo de aprendizaje."""
    if nuevo_elemento is None:
        return
    for clave, valor in nuevo_elemento.items():
        _base.guardar_entrada(
            clave=clave,
            explica=valor.get("explica", ""),
            respuesta=valor.get("respuesta", valor.get("respuestas", [""])[0] if valor.get("respuestas") else ""),
            otra_pregunta=valor.get("otra_pregunta", ""),
        )
