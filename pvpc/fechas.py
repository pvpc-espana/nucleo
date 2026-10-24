"""Cálculo de días y límites horarios en hora peninsular."""

from datetime import UTC, date, datetime, time, timedelta

from . import ZONA


def limites_dia(dia: date) -> tuple[datetime, datetime]:
    """Devuelve la medianoche (con desfase) del día y la del día siguiente."""
    inicio = datetime.combine(dia, time(0), tzinfo=ZONA)
    fin = datetime.combine(dia + timedelta(days=1), time(0), tzinfo=ZONA)
    return inicio, fin


def horas_del_dia(dia: date) -> int:
    """Número de horas reales del día: 23, 24 o 25 según el cambio de hora."""
    inicio, fin = limites_dia(dia)
    # Restar en UTC: entre fechas con la misma zona Python resta la hora de reloj
    return int((fin.astimezone(UTC) - inicio.astimezone(UTC)).total_seconds() // 3600)


def hoy(ahora: datetime | None = None) -> date:
    """Fecha actual en hora peninsular."""
    return (ahora or datetime.now(ZONA)).astimezone(ZONA).date()


def rango(desde: date, hasta: date) -> list[date]:
    """Lista de días entre ``desde`` y ``hasta`` (ambos incluidos)."""
    return [desde + timedelta(days=n) for n in range((hasta - desde).days + 1)]
