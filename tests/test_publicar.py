import json
from datetime import UTC, date, datetime
from unittest import mock

from pvpc import __main__ as cli
from pvpc.normalizar import normalizar
from pvpc.publicar import actualizar_indice, publicar_dia, ruta_dia

from .conftest import periodos_dia

AHORA = datetime(2026, 10, 24, 19, 41, 12, tzinfo=UTC)


def test_publicar_solo_si_cambia(salida):
    documento = normalizar(date(2026, 10, 25), periodos_dia(date(2026, 10, 25)))
    assert publicar_dia(salida, documento) is True
    assert publicar_dia(salida, documento) is False
    ruta = ruta_dia(salida, "2026-10-25")
    assert ruta.relative_to(salida).as_posix() == "v1/2026/10/2026-10-25.json"
    assert ruta.read_text(encoding="utf-8").endswith("}\n")


def test_indice(salida):
    for dia in (date(2026, 10, 24), date(2026, 10, 25)):
        publicar_dia(salida, normalizar(dia, periodos_dia(dia)))
    assert actualizar_indice(salida, AHORA) is True
    indice = json.loads((salida / "v1" / "indice.json").read_text(encoding="utf-8"))
    assert indice == {
        "version": 1,
        "primera": "2026-10-24",
        "ultima": "2026-10-25",
        "actualizado": "2026-10-24T19:41:12Z",
    }


def test_cli_sin_cambios_no_toca_nada(salida):
    datos = {
        date(2026, 10, 24): periodos_dia(date(2026, 10, 24)),
        date(2026, 10, 25): [],
    }
    with (
        mock.patch.object(cli, "obtener_periodos", side_effect=lambda d, t: datos[d]),
        mock.patch.object(cli, "hoy", return_value=date(2026, 10, 24)),
    ):
        assert cli.main(["--salida", str(salida)]) == 0
        indice = salida / "v1" / "indice.json"
        primera = indice.stat().st_mtime_ns
        assert cli.main(["--salida", str(salida)]) == 0
        assert indice.stat().st_mtime_ns == primera
        assert cli.main(["--salida", str(salida), "--exigir-manana"]) == 1
        assert cli.main(["--salida", str(salida), "--exigir-hoy"]) == 0


def test_cli_error_de_datos_devuelve_1(salida):
    with (
        mock.patch.object(
            cli,
            "obtener_periodos",
            return_value=periodos_dia(date(2026, 10, 24))[:5],
        ),
        mock.patch.object(cli, "hoy", return_value=date(2026, 10, 24)),
    ):
        assert cli.main(["--salida", str(salida), "--fecha", "2026-10-24"]) == 1
