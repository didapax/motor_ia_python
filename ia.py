#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# enable debugging

import json
import motor_ia


from colorama import Fore, Back, Style, init
init()

host = "local"

def main():
    texto = ""
    nombre_invitado = "INVITADO"    
    print(Fore.YELLOW +"\n..\n..Bienvenido Mi nombre es ADAN"+ Style.RESET_ALL)
    while texto != "EXIT":
        texto = input(f"-{nombre_invitado}> ").upper()
        texto = motor_ia.limpiar(texto)
        if len(texto) > 0:
            result = motor_ia.init(texto, host)
            if result == "":
                preguntar(texto)
            else:
                print (f"--ADAN>{result}")


def preguntar(pregunta):
    opcion = input(Fore.YELLOW +f"¿Qué es ¿{pregunta}? No lo conozco, por favor explícamelo. (S/N)\n"+ Style.RESET_ALL)
    opcion = opcion.upper()
    if opcion == 'S':
        explica = input(Fore.YELLOW + f"\n..\n..¿Qué debo responder a: {pregunta}? (Sé breve):\n"+ Style.RESET_ALL)
        explica = explica.upper()  # Convertimos a mayúsculas para usar Upcase
        respuesta = input(Fore.YELLOW +"Dame una explicación un poco detallada:\n"+ Style.RESET_ALL)
        respuesta = respuesta.upper()
        otraPregunta = input(Fore.YELLOW +"Ahora algo que yo deba preguntar o responder:\n"+ Style.RESET_ALL)
        otraPregunta = otraPregunta.upper()

        datos = {pregunta:{
            "explica": explica,
            "respuesta": respuesta,
            "otra_pregunta": otraPregunta
        }}
        motor_ia.agregar_elemento_lista_json("mente.json", "",datos)
    
        sinonimo = input(Fore.YELLOW +"Por favor, un sinónimo de (" + pregunta + ")\n"
                                  "Si no lo conoces, escribe el mismo:\n"+ Style.RESET_ALL)
        sinonimo = sinonimo.upper()
        sinonimo = motor_ia.limpiar(sinonimo)
        print(Fore.YELLOW +"Gracias por tu ayuda...\n"+Style.RESET_ALL)
        
        if sinonimo != pregunta:
            revisar = motor_ia.responder(sinonimo,True,host)
            if not revisar:
                datos = {sinonimo :{
                    "explica": explica,
                    "respuesta": respuesta,
                    "otra_pregunta": otraPregunta
                }}       
                motor_ia.agregar_elemento_lista_json("mente.json","", datos)


if __name__ == "__main__":
    main()
