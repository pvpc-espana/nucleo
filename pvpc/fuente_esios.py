"""Cliente de la API de e·sios (REE), indicador 1001: PVPC 2.0TD."""

from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from .fechas import limites_dia
from .http import obtener_json

URL = "https://api.esios.ree.es/indicators/1001"
GEO_PENINSULA = 8741


def url_dia(dia: date) -> str:
    inicio, fin = limites_dia(dia)
    parametros = {
        "start_date": inicio.isoformat(),
        "end_date": (fin - timedelta(seconds=1)).isoformat(),
        "geo_ids[]": GEO_PENINSULA,
    }
    return f"{URL}?{urlencode(parametros)}"


def extraer(respuesta: dict) -> list[tuple[datetime, float]]:
    """Periodos (inicio, €/MWh) de la zona peninsular, en orden."""
    valores = respuesta.get("indicator", {}).get("values", [])
    periodos = [
        (datetime.fromisoformat(v["datetime"]), float(v["value"]))
        for v in valores
        if v.get("geo_id") == GEO_PENINSULA
    ]
    return sorted(periodos)


def obtener(dia: date, testigo: str) -> list[tuple[datetime, float]]:
    cabeceras = {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "x-api-key": testigo,
    }
    return extraer(obtener_json(url_dia(dia), cabeceras))
