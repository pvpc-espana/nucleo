"""Petición HTTP con reintentos y espera exponencial (sólo biblioteca estándar)."""

import json
import logging
import time
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

AGENTE = "pvpc-espana/nucleo (+https://github.com/pvpc-espana/nucleo)"


def obtener_json(url: str, cabeceras: dict[str, str], intentos: int = 4, espera: float = 2.0):
    """Descarga ``url`` y devuelve el JSON. Reintenta errores de red y 5xx/429."""
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE, **cabeceras})
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                return json.load(respuesta)
        except urllib.error.HTTPError as error:
            if error.code < 500 and error.code != 429 or intento == intentos:
                raise
            log.warning("HTTP %s (intento %d/%d)", error.code, intento, intentos)
        except (urllib.error.URLError, TimeoutError) as error:
            if intento == intentos:
                raise
            log.warning("Error de red: %s (intento %d/%d)", error, intento, intentos)
        time.sleep(espera * 2 ** (intento - 1))
    raise RuntimeError("inalcanzable")
