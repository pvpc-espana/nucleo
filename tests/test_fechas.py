from datetime import UTC, date, datetime

from pvpc.fechas import horas_del_dia, hoy, limites_dia, rango


def test_limites_con_desfase_en_cambio_de_hora():
    inicio, fin = limites_dia(date(2026, 10, 25))
    assert inicio.isoformat() == "2026-10-25T00:00:00+02:00"
    assert fin.isoformat() == "2026-10-26T00:00:00+01:00"


def test_horas_del_dia():
    assert horas_del_dia(date(2026, 10, 24)) == 24
    assert horas_del_dia(date(2026, 10, 25)) == 25
    assert horas_del_dia(date(2026, 3, 29)) == 23


def test_hoy_en_hora_peninsular():
    # 23:30 UTC del 24 ya es 25 en Madrid (verano)
    assert hoy(datetime(2026, 7, 24, 23, 30, tzinfo=UTC)) == date(2026, 7, 25)


def test_rango():
    assert rango(date(2026, 1, 30), date(2026, 2, 1)) == [
        date(2026, 1, 30),
        date(2026, 1, 31),
        date(2026, 2, 1),
    ]
