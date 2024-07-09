#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# enable debugging

import json
import motor_ia


from colorama import Fore, Back, Style, init
init()

def main():
    texto = ""
    nombre_invitado = "INVITADO"    
    print(Fore.YELLOW +"\n..\n..Bienvenido Mi nombre es ADAN"+ Style.RESET_ALL)
    while texto != "EXIT":
        texto = input(f"-{nombre_invitado}> ").upper()
        texto = motor_ia.limpiar(texto)
        if len(texto) > 0:
            result = motor_ia.init(texto,"local")
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

        datos = {
            "explica": explica,
            "respuesta": respuesta,
            "otra_pregunta": otraPregunta
        }
        
        with open(pregunta, "w") as archivo:
            json.dump(datos, archivo, indent=4)
    
        sinonimo = input(Fore.YELLOW +"Por favor, un sinónimo de (" + pregunta + ")\n"
                                  "Si no lo conoces, escribe el mismo:\n"+ Style.RESET_ALL)
        sinonimo = sinonimo.upper()
        sinonimo = motor_ia.limpiar(sinonimo)
        print(Fore.YELLOW +"Gracias por tu ayuda...\n"+Style.RESET_ALL)
        with open(sinonimo, "w") as img_archivo:
            json.dump(datos, img_archivo, indent=4)


if __name__ == "__main__":
    main()