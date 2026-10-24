"""Cliente de respaldo: API pública apidatos.ree.es (sin autenticación)."""

from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from .fechas import limites_dia
from .http import obtener_json

URL = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"


def url_dia(dia: date) -> str:
    inicio, fin = limites_dia(dia)
    parametros = {
        "start_date": inicio.strftime("%Y-%m-%dT%H:%M"),
        "end_date": (fin - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M"),
        "time_trunc": "hour",
    }
    return f"{URL}?{urlencode(parametros)}"


def extraer(respuesta: dict) -> list[tuple[datetime, float]]:
    """Periodos (inicio, €/MWh) de la serie PVPC, en orden."""
    for serie in respuesta.get("included", []):
        if serie.get("id") == "1001" or "PVPC" in serie.get("type", ""):
            valores = serie.get("attributes", {}).get("values", [])
            return sorted(
                (datetime.fromisoformat(v["datetime"]), float(v["value"])) for v in valores
            )
    return []


def obtener(dia: date) -> list[tuple[datetime, float]]:
    return extraer(obtener_json(url_dia(dia), {"Accept": "application/json"}))
