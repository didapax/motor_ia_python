#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# enable debugging

import json
import requests
import random
import time


def insert(res, url="http://localhost:8080/", headers=None):
    if headers is None:
        headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, data=json.dumps(res), headers=headers)
        return response.status_code
    except requests.RequestException as e:
        print(f"Error al enviar la solicitud: {e}")
        return None   
    
def obtener_datos_del_backend(text,url="http://localhost:8080/", headers=None):
    if headers is None:
        headers = {"Content-Type": "application/json"}
    try:
        res_url = f"{url}&valor={text}";
        response = requests.get(res_url, headers=headers)
        response.raise_for_status()  # Lanza una excepción si la solicitud no es exitosa
        return response.json()
    except requests.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return None

        
def randomBoolean():
    random.seed(int(time.time()))
    random_val = random.randint(0, 1)
    return random_val == 1


def upcase(text):
    return text.upper()


def limpiar(cadena):
    vowels = ["#", "}", "{", "@", ".", "¿", "?", ",", "'", "\"","!"]
    return cadena.upper().translate(str.maketrans("", "", "".join(vowels)))


def interrogante(text):
    matriz = {
        "QUE",
        "SOBRE",
        "ADAN",
        "TIENES",
        "QUIEN",
        "DIME",
        "EXPLICAME",
        "SABES",
        "HABLAME",
        "CUAL",
        "CONOCES"
    }
    tokens = text.upper().split()  # Convertimos a mayúsculas y dividimos por espacios
    return any(token in matriz for token in tokens)


def analiza_pregunta(pregunta, tipo, base):
    #base puede ser: "local", "mongo;host_backed_parametro_busqueda_GET",...
    palabras = pregunta.split()  # Divide la cadena en palabras
    ultima_palabra = palabras[-1] if palabras else ""  # Obtiene la última palabra
    result = responder(pregunta, tipo, base)
    if result == "":
        result = responder(ultima_palabra, tipo, base)
    
    return result


def responder(text, tipo, base):
    #base puede ser: "local", "mongo;host_backed_parametro_busqueda_GET",...
    mensaje="";
    if base == "local":
        try:
            with open(text, "r") as archivo:
                datos_json = json.load(archivo)
                mensaje = buscaRespuesta(datos_json, tipo)
        except FileNotFoundError:
                #preguntar(text)
                mensaje="";
                
    if "mongo" in base:
        try:
            parametro = base.split(';')
            url_backend = parametro[1]
            datos_obtenidos = obtener_datos_del_backend(text,url_backend)
            if datos_obtenidos:            
                mensaje = buscaRespuesta(datos_obtenidos, tipo)
        except FileNotFoundError:
                #preguntar(text)
                mensaje="";
    
    return mensaje
    

def buscaRespuesta(datos, tipo):
    """
    Busca una respuesta o explicación en los datos proporcionados.

    Args:
        datos (dict): Datos en formato JSON con claves 'explica', 'respuesta' y 'pregunta'.
        tipo (bool): Indica si se busca una respuesta (True) o una explicación (False).

    Returns:
        str: Respuesta o explicación combinada con otra pregunta.
    """
    explica = datos.get('explica', '')
    respuesta = datos.get('respuesta', '')
    otra_pregunta = datos.get('otra_pregunta', '')
    resultado = randomBoolean()

    if tipo:
        resultado_texto = respuesta if resultado else ""
    else:
        resultado_texto = explica if resultado else ""

    if resultado_texto == "" and otra_pregunta == "":
        return ""
    else:
        return f"{resultado_texto}\n\n{otra_pregunta}"


def init(texto, base):
    if interrogante(texto):
        result = analiza_pregunta(texto, True, base)
    else:
        resultado = randomBoolean()
        result = responder(texto, resultado, base)
        
    return result
            
