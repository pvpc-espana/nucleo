from datetime import date
from urllib.parse import parse_qs, urlparse

from pvpc import fuente_esios, fuente_ree

from .conftest import periodos_dia, respuesta_esios


def test_url_esios_de_medianoche_a_medianoche_en_madrid():
    consulta = parse_qs(urlparse(fuente_esios.url_dia(date(2026, 10, 25))).query)
    assert consulta["start_date"] == ["2026-10-25T00:00:00+02:00"]
    assert consulta["end_date"] == ["2026-10-25T23:59:59+01:00"]
    assert consulta["geo_ids[]"] == ["8741"]


def test_extraer_esios_filtra_peninsula_y_ordena():
    dia = date(2026, 10, 24)
    respuesta = respuesta_esios(list(reversed(periodos_dia(dia))))
    respuesta["indicator"]["values"].append(
        {"value": 999, "datetime": "2026-10-24T00:00:00.000+02:00", "geo_id": 8744}
    )
    periodos = fuente_esios.extraer(respuesta)
    assert len(periodos) == 24
    assert periodos[0][0].isoformat() == "2026-10-24T00:00:00+02:00"
    assert periodos[0][1] == 100.0


def test_extraer_esios_sin_publicar():
    assert fuente_esios.extraer({"indicator": {"values": []}}) == []


def test_extraer_ree():
    respuesta = {
        "included": [
            {"id": "600", "type": "Precio mercado spot (€/MWh)", "attributes": {"values": []}},
            {
                "id": "1001",
                "type": "PVPC (€/MWh)",
                "attributes": {
                    "values": [
                        {"value": 120.5, "datetime": "2026-10-24T01:00:00.000+02:00"},
                        {"value": 110.0, "datetime": "2026-10-24T00:00:00.000+02:00"},
                    ]
                },
            },
        ]
    }
    periodos = fuente_ree.extraer(respuesta)
    assert [v for _, v in periodos] == [110.0, 120.5]
