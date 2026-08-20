"""Agregação das leituras de água e cálculo da conta do período."""
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy.orm import Session

from ..models import WaterReadingDB, WaterSyncStatusDB, WaterReading, WaterMonthlyTotal, WaterDashboardResponse
from .tariff import calcular_conta


def compute_water_dashboard(db: Session, months: int) -> dict:
    today = date.today()
    cutoff_year, cutoff_month = today.year, today.month
    cutoff_year -= (months - 1) // 12
    cutoff_month -= (months - 1) % 12
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    cutoff_date = date(cutoff_year, cutoff_month, 1)

    rows = (
        db.query(WaterReadingDB)
        .filter(WaterReadingDB.reading_date >= cutoff_date)
        .order_by(WaterReadingDB.reading_date)
        .all()
    )

    readings = [WaterReading(reading_date=r.reading_date, consumo_m3=r.consumo_m3) for r in rows]

    monthly: dict[tuple[int, int], float] = defaultdict(float)
    for r in rows:
        monthly[(r.reading_date.year, r.reading_date.month)] += r.consumo_m3
    monthly_totals = [
        WaterMonthlyTotal(year=y, month=m, consumo_m3=round(v, 3))
        for (y, m), v in sorted(monthly.items())
    ]

    consumo_periodo = sum(r.consumo_m3 for r in rows)
    dias = max(1, (rows[-1].reading_date - rows[0].reading_date).days + 1) if rows else 1
    media_diaria = consumo_periodo / dias if rows else 0.0

    # A conta é calculada sobre o consumo do mês corrente (como uma fatura mensal),
    # não sobre a soma de todo o período selecionado.
    consumo_mes_atual = monthly.get((today.year, today.month), 0.0)
    bill = calcular_conta(consumo_mes_atual)

    sync = db.query(WaterSyncStatusDB).first()

    return {
        "readings": readings,
        "monthly_totals": monthly_totals,
        "consumo_periodo_m3": round(consumo_periodo, 3),
        "media_diaria_m3": round(media_diaria, 3),
        "bill": bill,
        "last_sync": sync.last_sync if sync else None,
    }
