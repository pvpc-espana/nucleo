from datetime import date, timedelta

import pytest

from pvpc.normalizar import DatosInvalidos, normalizar

from .conftest import periodos_dia


@pytest.mark.parametrize(
    ("dia", "horas"),
    [(date(2026, 10, 24), 24), (date(2026, 10, 25), 25), (date(2026, 3, 29), 23)],
)
def test_dias_completos(dia, horas):
    documento = normalizar(dia, periodos_dia(dia))
    assert documento["fecha"] == dia.isoformat()
    assert documento["resolucion"] == "PT1H"
    assert len(documento["precios"]) == horas


def test_dia_de_25_horas_repite_las_dos_con_otro_desfase():
    documento = normalizar(date(2026, 10, 25), periodos_dia(date(2026, 10, 25)))
    inicios = [p["inicio"] for p in documento["precios"]]
    assert inicios[:4] == [
        "2026-10-25T00:00:00+02:00",
        "2026-10-25T01:00:00+02:00",
        "2026-10-25T02:00:00+02:00",
        "2026-10-25T02:00:00+01:00",
    ]
    assert inicios[-1] == "2026-10-25T23:00:00+01:00"


def test_conversion_y_resumen():
    dia = date(2026, 10, 24)
    documento = normalizar(dia, periodos_dia(dia, base=41.4))
    assert documento["unidad"] == "EUR/kWh"
    assert documento["precios"][0]["precio"] == 0.0414
    assert documento["resumen"] == {"min": 0.0414, "max": 0.0644, "media": 0.0529}


def test_cuartohorario():
    dia = date(2026, 10, 24)
    documento = normalizar(dia, periodos_dia(dia, minutos=15))
    assert documento["resolucion"] == "PT15M"
    assert len(documento["precios"]) == 96


def test_sin_publicar():
    assert normalizar(date(2026, 10, 25), []) is None


def test_ignora_periodos_de_otros_dias():
    dia = date(2026, 10, 24)
    extra = periodos_dia(dia + timedelta(days=1))[:3]
    assert len(normalizar(dia, periodos_dia(dia) + extra)["precios"]) == 24


def test_dia_incompleto():
    dia = date(2026, 10, 25)
    with pytest.raises(DatosInvalidos, match="22 periodos"):
        normalizar(dia, periodos_dia(dia)[3:])


def test_hueco():
    dia = date(2026, 10, 24)
    periodos = periodos_dia(dia, minutos=15)
    periodos = periodos[:10] + periodos[11:] + periodos[-1:]
    with pytest.raises(DatosInvalidos):
        normalizar(dia, periodos)


def test_precio_fuera_de_rango():
    dia = date(2026, 10, 24)
    periodos = periodos_dia(dia)
    periodos[5] = (periodos[5][0], 99999.0)
    with pytest.raises(DatosInvalidos, match="fuera de rango"):
        normalizar(dia, periodos)
