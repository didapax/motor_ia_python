#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
nlp_utils.py — Utilidades de Procesamiento de Lenguaje Natural para ADAN
"""

import re
import unicodedata
from rapidfuzz import fuzz, process


# ─── Normalización ────────────────────────────────────────────────────────────

def normalizar(texto: str) -> str:
    """
    Convierte el texto a mayúsculas, elimina acentos, puntuación
    y espacios extra para comparaciones uniformes.
    """
    if not texto:
        return ""
    # Convertir a mayúsculas
    texto = texto.upper()
    # Eliminar acentos usando unicodedata
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    # Eliminar puntuación y caracteres especiales
    texto = re.sub(r"[^\w\s]", " ", texto)
    # Colapsar espacios múltiples
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar(texto: str) -> list[str]:
    """Divide el texto normalizado en tokens."""
    return normalizar(texto).split()


# ─── Similitud ────────────────────────────────────────────────────────────────

UMBRAL_SIMILITUD = 75  # Porcentaje mínimo de similitud para aceptar una coincidencia

def similitud(a: str, b: str) -> float:
    """
    Calcula la similitud entre dos cadenas (0-100).
    Usa ratio ponderado para equilibrar similitud exacta y parcial.
    """
    a_n = normalizar(a)
    b_n = normalizar(b)
    ratio = fuzz.ratio(a_n, b_n)
    partial = fuzz.partial_ratio(a_n, b_n)
    token_sort = fuzz.token_sort_ratio(a_n, b_n)
    # Ponderación: más peso al token_sort para manejar palabras reordenadas
    return (ratio * 0.3) + (partial * 0.3) + (token_sort * 0.4)


def mejor_coincidencia(texto: str, candidatos: list[str], umbral: int = UMBRAL_SIMILITUD):
    """
    Encuentra la mejor coincidencia para `texto` dentro de `candidatos`.
    Retorna (clave, score) o (None, 0) si ninguna supera el umbral.
    """
    if not candidatos:
        return None, 0
    texto_n = normalizar(texto)
    candidatos_n = {normalizar(c): c for c in candidatos}
    resultado = process.extractOne(
        texto_n,
        list(candidatos_n.keys()),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=umbral,
    )
    if resultado:
        clave_n, score, _ = resultado
        return candidatos_n[clave_n], score
    return None, 0


# ─── Detección de Intención ───────────────────────────────────────────────────

_INTENCIONES = {
    "saludo": {
        "HOLA", "BUENOS DIAS", "BUENAS TARDES", "BUENAS NOCHES", "BUENAS",
        "HI", "HELLO", "EY", "OYE", "SALUDOS", "QUE TAL", "QUE HUBO",
        "COMO ESTAS", "COMO ESTAS", "COMO ANDAS",
    },
    "despedida": {
        "ADIOS", "HASTA LUEGO", "CHAO", "BYE", "NOS VEMOS", "HASTA PRONTO",
        "CUÍDATE", "EXIT", "SALIR", "CIAO", "HASTA MANANA",
    },
    "agradecimiento": {
        "GRACIAS", "MUCHAS GRACIAS", "TE LO AGRADEZCO", "AGRADECIDO",
        "AGRADECIDA", "MERCI", "THANKS",
    },
    "pregunta": {
        "QUE", "QUIEN", "COMO", "CUANDO", "DONDE", "POR QUE", "CUAL",
        "CUANTO", "CUANTOS", "PARA QUE", "DIME", "EXPLICAME", "SABES",
        "CONOCES", "HABLAME", "SOBRE", "CUÉNTAME",
    },
    "aprender": {
        "APRENDE", "APRENDER", "ENSENATE", "ENSENATE", "MEMORIZA",
        "GUARDA", "RECUERDA",
    },
}

# Normalizar los sets de intenciones al inicio
_INTENCIONES_N = {
    intencion: {normalizar(kw) for kw in keywords}
    for intencion, keywords in _INTENCIONES.items()
}


def detectar_intencion(texto: str) -> str:
    """
    Detecta la intención principal de un mensaje.
    Retorna: 'saludo', 'despedida', 'agradecimiento', 'pregunta', 'aprender', o 'desconocido'.
    """
    texto_n = normalizar(texto)
    tokens = set(texto_n.split())

    for intencion, keywords in _INTENCIONES_N.items():
        # Coincidencia exacta de tokens
        if tokens & keywords:
            return intencion
        # Coincidencia de frases completas
        if texto_n in keywords:
            return intencion

    return "desconocido"


# ─── Extracción de Palabras Clave ─────────────────────────────────────────────

_STOP_WORDS = {
    "EL", "LA", "LOS", "LAS", "UN", "UNA", "UNOS", "UNAS",
    "DE", "DEL", "EN", "CON", "POR", "PARA", "A", "AL",
    "ES", "SON", "SEA", "ERA", "FUE", "HAS", "HAN",
    "ME", "TE", "SE", "NOS", "LO", "LE", "SU", "SUS",
    "MI", "TU", "Y", "O", "E", "U", "QUE", "COMO", "QUIEN",
    "CUAL", "CUANDO", "DONDE", "SOBRE", "DIME", "EXPLICAME",
    "SABES", "CONOCES", "HABLAME", "TIENES", "ERES",
}


def extraer_palabras_clave(texto: str) -> list[str]:
    """
    Extrae las palabras más relevantes eliminando stop words.
    Retorna lista ordenada por longitud (más largas primero = más específicas).
    """
    tokens = tokenizar(texto)
    claves = [t for t in tokens if t not in _STOP_WORDS and len(t) > 2]
    return sorted(claves, key=len, reverse=True)
