"""Validación y conversión de los periodos al formato publicado v1."""

from datetime import UTC, date, datetime

from . import ZONA
from .fechas import horas_del_dia, limites_dia

DECIMALES = 5
PRECIO_MIN, PRECIO_MAX = -1.0, 5.0  # €/kWh; fuera de este rango se considera un error


class DatosInvalidos(ValueError):
    pass


def normalizar(dia: date, periodos: list[tuple[datetime, float]]) -> dict | None:
    """Convierte periodos (inicio, €/MWh) en el documento diario v1.

    Devuelve ``None`` si el día aún no está publicado (sin periodos) y lanza
    ``DatosInvalidos`` si los datos están incompletos o fuera de rango.
    """
    # Todo en UTC: con la zona de Madrid Python compara y resta la hora de reloj,
    # lo que confunde las dos 02:00 del día de 25 horas.
    inicio, fin = (m.astimezone(UTC) for m in limites_dia(dia))
    periodos = [(m.astimezone(UTC), v) for m, v in periodos]
    periodos = sorted({m: (m, v) for m, v in periodos if inicio <= m < fin}.values())
    if not periodos:
        return None

    horas = horas_del_dia(dia)
    if len(periodos) == horas:
        resolucion, minutos = "PT1H", 60
    elif len(periodos) == horas * 4:
        resolucion, minutos = "PT15M", 15
    else:
        raise DatosInvalidos(f"{dia}: {len(periodos)} periodos para un día de {horas} horas")

    for anterior, siguiente in zip(periodos, periodos[1:], strict=False):
        if (siguiente[0] - anterior[0]).total_seconds() != minutos * 60:
            raise DatosInvalidos(f"{dia}: hueco o solape en {siguiente[0].isoformat()}")

    precios = []
    for momento, mwh in periodos:
        kwh = round(mwh / 1000, DECIMALES)
        if not PRECIO_MIN < kwh < PRECIO_MAX:
            raise DatosInvalidos(f"{dia}: precio fuera de rango {kwh} en {momento.isoformat()}")
        precios.append({"inicio": momento.astimezone(ZONA).isoformat(), "precio": kwh})

    valores = [p["precio"] for p in precios]
    return {
        "fecha": dia.isoformat(),
        "zona": "peninsula",
        "unidad": "EUR/kWh",
        "resolucion": resolucion,
        "fuente": "REE",
        "resumen": {
            "min": min(valores),
            "max": max(valores),
            "media": round(sum(valores) / len(valores), DECIMALES),
        },
        "precios": precios,
    }
