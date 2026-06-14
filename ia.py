#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
ia.py — Interfaz de línea de comandos mejorada para ADAN
"""

import sys
import motor_ia
from colorama import Fore, Back, Style, init as colorama_init

colorama_init()

# ─── Helpers visuales ─────────────────────────────────────────────────────────

FUENTE_COLOR = {
    "local":       Fore.GREEN,
    "Wikipedia":   Fore.CYAN,
    "DuckDuckGo":  Fore.BLUE,
    "aprendido":   Fore.MAGENTA,
    "":            Fore.WHITE,
}

BANNER = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════╗
║  {Fore.WHITE}██████╗ {Fore.YELLOW}██████╗  █████╗ ███╗   ██╗{Fore.CYAN}               ║
║  {Fore.WHITE}██╔══██╗{Fore.YELLOW}██╔══██╗██╔══██╗████╗  ██║{Fore.CYAN}               ║
║  {Fore.WHITE}███████║{Fore.YELLOW}██║  ██║███████║██╔██╗ ██║{Fore.CYAN}               ║
║  {Fore.WHITE}██╔══██║{Fore.YELLOW}██║  ██║██╔══██║██║╚██╗██║{Fore.CYAN}               ║
║  {Fore.WHITE}██║  ██║{Fore.YELLOW}██████╔╝██║  ██║██║ ╚████║{Fore.CYAN}               ║
║  {Fore.WHITE}╚═╝  ╚═╝{Fore.YELLOW}╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝{Fore.CYAN}               ║
║                                                  ║
║  {Fore.WHITE}Asistente Virtual Inteligente  v2.0{Fore.CYAN}             ║
║  {Fore.WHITE}Escribe {Fore.YELLOW}/ayuda{Fore.WHITE} para ver los comandos{Fore.CYAN}           ║
╚══════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

AYUDA = f"""
{Fore.YELLOW}╔══════════════════════════════════════════════════╗
║  COMANDOS ESPECIALES                             ║
╠══════════════════════════════════════════════════╣
║  /ayuda        Muestra esta ayuda                ║
║  /historial    Muestra el historial de la sesión ║
║  /stats        Estadísticas de la base de datos  ║
║  /limpiar      Limpia el historial de la sesión  ║
║  /salir        Sale del programa                 ║
╚══════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

INDICADORES_FUENTE = {
    "local":       f"{Fore.GREEN}[LOCAL]{Style.RESET_ALL}",
    "Wikipedia":   f"{Fore.CYAN}[WIKI]{Style.RESET_ALL}",
    "DuckDuckGo":  f"{Fore.BLUE}[DDG]{Style.RESET_ALL}",
    "aprendido":   f"{Fore.MAGENTA}[NUEVO]{Style.RESET_ALL}",
}


def imprimir_respuesta(respuesta: str, fuente: str):
    indicador = INDICADORES_FUENTE.get(fuente, "")
    color = FUENTE_COLOR.get(fuente, Fore.WHITE)
    print(f"\n{Fore.YELLOW}┌─ ADAN {indicador}")
    for linea in respuesta.split("\n"):
        print(f"{Fore.YELLOW}│{Style.RESET_ALL} {color}{linea}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}└{'─' * 49}{Style.RESET_ALL}\n")


def preguntar_aprender(texto: str):
    """Flujo interactivo para enseñar algo nuevo a ADAN."""
    print(f"\n{Fore.YELLOW}┌─ ADAN [APRENDIZAJE]")
    print(f"{Fore.YELLOW}│{Style.RESET_ALL} No conozco '{texto}'. ¿Deseas enseñarme? (S/N)")
    print(f"{Fore.YELLOW}└{'─' * 49}{Style.RESET_ALL}")

    opcion = input(f"{Fore.CYAN}  Tu respuesta: {Style.RESET_ALL}").strip().upper()
    if opcion != 'S':
        return

    print(f"\n{Fore.YELLOW}📝 Enséñame sobre: {Fore.WHITE}{texto}{Style.RESET_ALL}")

    explica = input(f"{Fore.CYAN}  Respuesta breve (¿qué es?): {Style.RESET_ALL}").strip()
    if not explica:
        return

    respuesta = input(f"{Fore.CYAN}  Explicación detallada: {Style.RESET_ALL}").strip()
    otra_pregunta = input(f"{Fore.CYAN}  ¿Qué pregunta yo debo hacer después? (opcional): {Style.RESET_ALL}").strip()
    sinonimo = input(f"{Fore.CYAN}  Sinónimo de '{texto}' (o Enter para omitir): {Style.RESET_ALL}").strip()

    texto_normalizado = motor_ia.limpiar(texto)
    sinonimo_normalizado = motor_ia.limpiar(sinonimo) if sinonimo else ""

    exito = motor_ia.aprender(
        clave=texto_normalizado,
        explica=explica,
        respuesta=respuesta,
        otra_pregunta=otra_pregunta,
        sinonimo=sinonimo_normalizado,
    )

    if exito:
        print(f"\n{Fore.GREEN}✅ ¡Perfecto! He aprendido sobre '{texto}'. ¡Gracias por enseñarme!{Style.RESET_ALL}\n")
    else:
        print(f"\n{Fore.RED}❌ Hubo un problema al guardar. Inténtalo de nuevo.{Style.RESET_ALL}\n")


def manejar_comando(comando: str) -> bool:
    """
    Maneja comandos especiales. Retorna True si el programa debe continuar.
    """
    ctx = motor_ia.obtener_contexto()

    if comando == "/ayuda":
        print(AYUDA)
    elif comando == "/historial":
        historial = ctx.como_texto()
        if historial:
            print(f"\n{Fore.YELLOW}═══ Historial de la sesión ═══{Style.RESET_ALL}")
            print(historial)
            print(f"{Fore.YELLOW}{'═' * 32}{Style.RESET_ALL}\n")
        else:
            print(f"\n{Fore.YELLOW}El historial está vacío.{Style.RESET_ALL}\n")
    elif comando == "/stats":
        stats = motor_ia.obtener_estadisticas()
        print(f"\n{Fore.YELLOW}═══ Estadísticas ═══{Style.RESET_ALL}")
        print(f"  Entradas en la base: {Fore.GREEN}{stats['total_entradas']}{Style.RESET_ALL}")
        print(f"  Sinónimos indexados: {Fore.GREEN}{stats['total_sinonimos']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'═' * 22}{Style.RESET_ALL}\n")
    elif comando == "/limpiar":
        ctx.limpiar()
        print(f"\n{Fore.GREEN}✅ Historial limpiado.{Style.RESET_ALL}\n")
    elif comando in ("/salir", "/exit"):
        print(f"\n{Fore.YELLOW}¡Hasta luego! Que tengas un excelente día. 👋{Style.RESET_ALL}\n")
        return False
    else:
        print(f"\n{Fore.RED}Comando no reconocido. Escribe /ayuda para ver los comandos.{Style.RESET_ALL}\n")

    return True


# ─── Loop principal ───────────────────────────────────────────────────────────

def main():
    print(BANNER)

    nombre_usuario = input(f"{Fore.CYAN}¿Cómo te llamas? (Enter para omitir): {Style.RESET_ALL}").strip()
    if not nombre_usuario:
        nombre_usuario = "Usuario"

    print(f"\n{Fore.GREEN}¡Bienvenido, {nombre_usuario}! Estoy listo para ayudarte.{Style.RESET_ALL}\n")

    continuar = True
    while continuar:
        try:
            texto = input(f"{Fore.WHITE}{nombre_usuario}{Fore.YELLOW}>{Style.RESET_ALL} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{Fore.YELLOW}¡Hasta luego! 👋{Style.RESET_ALL}\n")
            break

        if not texto:
            continue

        # Comandos especiales
        if texto.startswith("/"):
            continuar = manejar_comando(texto.lower())
            continue

        # Limpiar y procesar
        texto_limpio = motor_ia.limpiar(texto)

        # Detectar despedida
        from nlp_utils import detectar_intencion
        if detectar_intencion(texto_limpio) == "despedida":
            imprimir_respuesta(f"¡Hasta luego, {nombre_usuario}! Que tengas un excelente día. 👋", "local")
            break

        # Obtener respuesta
        respuesta, fuente = motor_ia.init(texto_limpio)

        if respuesta:
            imprimir_respuesta(respuesta, fuente)
        else:
            preguntar_aprender(texto)


if __name__ == "__main__":
    main()
