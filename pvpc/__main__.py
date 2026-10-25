"""CLI: python -m pvpc --salida ../datos/docs [--fecha AAAA-MM-DD | --desde … --hasta …]"""

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from . import fuente_esios, fuente_ree
from .fechas import hoy, rango
from .normalizar import DatosInvalidos, normalizar
from .publicar import actualizar_indice, publicar_dia

log = logging.getLogger("pvpc")


def obtener_periodos(dia: date, testigo: str | None):
    if testigo:
        try:
            return fuente_esios.obtener(dia, testigo)
        except Exception as error:  # noqa: BLE001 - cualquier fallo pasa al respaldo
            log.warning("%s: e·sios falló (%s); se usa apidatos.ree.es", dia, error)
    return fuente_ree.obtener(dia)


def procesar(dias: list[date], salida: Path, testigo: str | None) -> tuple[list[date], bool]:
    """Publica los días disponibles. Devuelve (días sin publicar, hubo errores)."""
    pendientes, errores, cambios = [], False, False
    for dia in dias:
        try:
            documento = normalizar(dia, obtener_periodos(dia, testigo))
        except DatosInvalidos as error:
            log.error("%s", error)
            errores = True
            continue
        except Exception as error:  # noqa: BLE001
            log.error("%s: no se pudo obtener (%s)", dia, error)
            errores = True
            continue
        if documento is None:
            log.info("%s: aún sin publicar", dia)
            pendientes.append(dia)
        elif publicar_dia(salida, documento):
            log.info(
                "%s: actualizado (%d periodos %s, media %.5f €/kWh)",
                dia,
                len(documento["precios"]),
                documento["resolucion"],
                documento["resumen"]["media"],
            )
            cambios = True
        else:
            log.info("%s: sin cambios", dia)
    if cambios:
        actualizar_indice(salida)
    return pendientes, errores


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pvpc", description=__doc__)
    parser.add_argument("--salida", type=Path, required=True, help="carpeta docs de datos")
    parser.add_argument("--fecha", type=date.fromisoformat, help="un día concreto")
    parser.add_argument("--desde", type=date.fromisoformat, help="inicio de un rango")
    parser.add_argument("--hasta", type=date.fromisoformat, help="fin de un rango")
    parser.add_argument(
        "--exigir-manana",
        action="store_true",
        help="termina con error si mañana aún no está publicado",
    )
    parser.add_argument(
        "--exigir-hoy",
        action="store_true",
        help="termina con error si el día en curso no está publicado",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    hoy_ = hoy()
    if args.fecha:
        dias = [args.fecha]
    elif args.desde:
        dias = rango(args.desde, args.hasta or hoy_)
    else:
        dias = [hoy_, hoy_ + timedelta(days=1)]

    testigo = os.environ.get("TESTIGO") or None
    if not testigo:
        log.warning("Sin TESTIGO: se usa sólo apidatos.ree.es")
    pendientes, errores = procesar(dias, args.salida, testigo)

    if args.exigir_manana and hoy_ + timedelta(days=1) in pendientes:
        log.error("Los precios de mañana siguen sin publicarse")
        return 1
    if args.exigir_hoy and hoy_ in pendientes:
        log.error("Los precios del día en curso no están publicados")
        return 1
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
