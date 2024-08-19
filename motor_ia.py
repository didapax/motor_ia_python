#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# enable debugging

import json
import requests
import random
import time
from urllib.parse import quote
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup

def leer_archivo_json(ruta_archivo):
    try:
        with open(ruta_archivo, "r") as archivo:
            datos_json = json.load(archivo)
            
            if isinstance(datos_json, list):
                return datos_json
            elif isinstance(datos_json, dict):
                return list(datos_json)
            else:
                print("El archivo JSON contiene otro tipo de datos.")

    except FileNotFoundError:
        print(f"El archivo '{ruta_archivo}' no existe.")
        return None
    except json.JSONDecodeError:
        print(f"Error al decodificar el archivo JSON '{ruta_archivo}'.")
        return None
        

def update_clave_json(ruta_archivo, datos):
    try:
        with open(ruta_archivo, "w") as archivo:
            json.dump(datos, archivo, indent=4)
    except Exception as e:
        print(f"Error al guardar el archivo JSON: {e}")


def update_dic_json(ruta_archivo, datos):
    try:
        with open(ruta_archivo, "w") as archivo:
            json.dump(datos, archivo, indent=4)
    except Exception as e:
        print(f"Error al guardar el archivo JSON: {e}")


def agregar_datos_json(ruta_archivo, nuevos_datos):
    datos_json = leer_archivo_json(ruta_archivo)
    if datos_json is not None:
        datos_json.update(nuevos_datos)
        guardar_archivo_json(ruta_archivo, datos_json)


def agregar_elemento_lista_json(ruta_archivo, clave_lista="", nuevo_elemento=""):
    datos_json = leer_archivo_json(ruta_archivo)
    if datos_json is not None:
        if clave_lista:
            if clave_lista in datos_json and isinstance(datos_json[clave_lista], list):
                datos_json[clave_lista].append(nuevo_elemento)
            else:
                print(f"La clave '{clave_lista}' no existe o no es una lista.")
                return
        else:
            if isinstance(datos_json, list):
                datos_json.append(nuevo_elemento)
            else:
                print("El archivo JSON no contiene una lista en la raíz.")
                return

        update_dic_json(ruta_archivo, datos_json)


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
        "COMO",
        "CONOCES"
    }
    tokens = text.upper().split()  # Convertimos a mayúsculas y dividimos por espacios
    return any(token in matriz for token in tokens)


def analiza_pregunta(pregunta, tipo, base):
    #base puede ser: "local", "mongo;host_backed_parametro_busqueda_GET",...
    rand = randomBoolean()
    result = responder(pregunta, rand, base)
    if not result:
        if interrogante(pregunta):
            palabras = pregunta.split()  # Divide la cadena en palabras            
            ultima_palabra = palabras[-1] if palabras else ""  # Obtiene la última palabra
            penultima_palabra = palabras[-2] if palabras else ""
            result = responder(ultima_palabra, tipo, base)
            if not result:
                compuesto = f"{penultima_palabra} {ultima_palabra}"
                result = responder(compuesto, tipo, base)
                
                if not result:                         
                    result = buscarRespuestaInternet(ultima_palabra.capitalize())                    
                
                    if not result:
                        compuesto = f"{penultima_palabra.capitalize()}_{ultima_palabra.capitalize()}" 
                        time.sleep(1)
                        result = buscarRespuestaInternet(compuesto)

    return result


def responder(text, tipo, base):
    #base puede ser: "local", "mongo;host_backed_parametro_busqueda_GET",...
    mensaje="";
    if base == "local":
            datos_json = leer_archivo_json('mente.json')            
            for item in datos_json:
                if text in item:                    
                    valor = item[text]
                    mensaje = buscaRespuesta(valor, tipo)

    if "mongo" in base:
        try:
            parametro = base.split(';')
            url_backend = parametro[1]
            datos_json = obtener_datos_del_backend(text,url_backend)
            for item in datos_json:
                if text in item:                    
                    valor = item[text]
                    mensaje = buscaRespuesta(valor, tipo)
                    
        except FileNotFoundError:
                #preguntar(text)
                mensaje="";
    
    return mensaje
    

def buscarRespuestaInternet(text):
    # Codificar el texto para que sea una URL válida
    encoded_text = quote(text)
    url = f"https://es.wikipedia.org/wiki/{encoded_text}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Parsear el contenido HTML de la página
            soup = BeautifulSoup(response.content, 'html.parser')

            # Iterar sobre todos los párrafos y seleccionar el primero que contenga texto significativo
            paragraphs = soup.find_all('p')
            for paragraph in paragraphs:
                text = paragraph.get_text().strip()
                if len(text) > 10:  # Asegurarse de que el párrafo no esté vacío o sea muy corto
                    return text

            return "No se encontró información suficiente."
        else:
            return f"Error al realizar la solicitud: {response.status_code}"
    except HTTPError as e:
        return f"El servidor no pudo cumplir con la solicitud: {e}"
    except URLError as e:
        return f"La URL no es válida o no está accesible: {e}"
    except Exception as e:
        return f"Ocurrió un error inesperado: {e}"


def buscaRespuesta(datos, tipo):    
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
    return analiza_pregunta(texto, True, base)

            
