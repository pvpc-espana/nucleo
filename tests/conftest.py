from datetime import UTC, date, timedelta

import pytest

from pvpc import ZONA
from pvpc.fechas import limites_dia


def periodos_dia(dia: date, minutos: int = 60, base: float = 100.0):
    """Periodos sintéticos (inicio, €/MWh) que cubren el día completo."""
    inicio, fin = (m.astimezone(UTC) for m in limites_dia(dia))
    periodos, momento, n = [], inicio, 0
    while momento < fin:
        periodos.append((momento.astimezone(ZONA), base + n))
        momento += timedelta(minutes=minutos)
        n += 1
    return periodos


def respuesta_esios(periodos, geo_id: int = 8741) -> dict:
    return {
        "indicator": {
            "id": 1001,
            "short_name": "PVPC T. 2.0TD",
            "geos": [{"geo_id": geo_id, "geo_name": "Península"}],
            "values": [
                {
                    "value": valor,
                    "datetime": momento.isoformat(timespec="milliseconds"),
                    "geo_id": geo_id,
                    "geo_name": "Península",
                }
                for momento, valor in periodos
            ],
        }
    }


@pytest.fixture
def salida(tmp_path):
    return tmp_path / "docs"
