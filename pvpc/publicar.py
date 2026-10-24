"""Escritura determinista de los ficheros publicados en el repositorio de datos."""

import json
from datetime import UTC, datetime
from pathlib import Path

VERSION = 1


def serializar(documento: dict) -> str:
    return json.dumps(documento, ensure_ascii=False, indent=2) + "\n"


def ruta_dia(salida: Path, fecha: str) -> Path:
    anio, mes, _ = fecha.split("-")
    return salida / f"v{VERSION}" / anio / mes / f"{fecha}.json"


def escribir_si_cambia(ruta: Path, contenido: str) -> bool:
    if ruta.exists() and ruta.read_text(encoding="utf-8") == contenido:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    return True


def publicar_dia(salida: Path, documento: dict) -> bool:
    """Escribe el fichero del día; devuelve ``True`` si ha cambiado."""
    return escribir_si_cambia(ruta_dia(salida, documento["fecha"]), serializar(documento))


def actualizar_indice(salida: Path, ahora: datetime | None = None) -> bool:
    """Reescribe ``indice.json`` con el rango disponible y la hora de actualización.

    Sólo debe llamarse cuando algún día ha cambiado, para no generar commits vacíos.
    """
    fechas = sorted(p.stem for p in (salida / f"v{VERSION}").glob("*/*/*.json"))
    if not fechas:
        return False
    momento = (ahora or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    indice = {
        "version": VERSION,
        "primera": fechas[0],
        "ultima": fechas[-1],
        "actualizado": momento.isoformat().replace("+00:00", "Z"),
    }
    return escribir_si_cambia(salida / f"v{VERSION}" / "indice.json", serializar(indice))
