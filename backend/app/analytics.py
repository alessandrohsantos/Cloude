"""
Spending analytics and trend forecasting.
"""
from datetime import date
from collections import defaultdict
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from .models import (
    TransactionDB,
    CategoryTotal,
    MonthlyTotal,
    TrendPoint,
    CategoryTrend,
    BankEnum,
    CategoryEnum,
)


def _month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def _fill_month_range(
    data: dict[str, float], months: int
) -> list[tuple[int, int, float]]:
    """Return a chronologically ordered list of (year, month, amount) for the given range."""
    today = date.today()
    result = []
    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        key = _month_key(year, month)
        result.append((year, month, data.get(key, 0.0)))
    return result


def compute_analytics(db: Session, months: int) -> dict:
    """Compute all analytics from the database."""
    transactions = db.query(TransactionDB).all()

    if not transactions:
        return _empty_analytics(months)

    # Filter to the requested time range
    today = date.today()
    cutoff_year, cutoff_month = today.year, today.month
    cutoff_year -= (months - 1) // 12
    cutoff_month -= (months - 1) % 12
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1

    filtered = [
        t for t in transactions
        if (t.invoice_year, t.invoice_month) >= (cutoff_year, cutoff_month)
    ]

    if not filtered:
        return _empty_analytics(months)

    # Totals
    total_period = sum(t.amount for t in filtered)

    # By category
    cat_totals: dict[str, float] = defaultdict(float)
    cat_counts: dict[str, int] = defaultdict(int)
    for t in filtered:
        cat_totals[t.category.value] += t.amount
        cat_counts[t.category.value] += 1

    categories = [
        CategoryTotal(
            category=cat,
            total=round(total, 2),
            count=cat_counts[cat],
            percentage=round(total / total_period * 100, 1) if total_period > 0 else 0,
        )
        for cat, total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    # By bank
    bank_totals: dict[str, float] = defaultdict(float)
    for t in filtered:
        bank_totals[t.bank.value] += t.amount
    by_bank = {k: round(v, 2) for k, v in bank_totals.items()}

    # Monthly totals
    monthly_by_month: dict[str, float] = defaultdict(float)
    monthly_by_bank: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    monthly_by_cat: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for t in filtered:
        key = _month_key(t.invoice_year, t.invoice_month)
        monthly_by_month[key] += t.amount
        monthly_by_bank[key][t.bank.value] += t.amount
        monthly_by_cat[key][t.category.value] += t.amount

    monthly_totals = []
    for year, month, total in _fill_month_range(monthly_by_month, months):
        key = _month_key(year, month)
        monthly_totals.append(
            MonthlyTotal(
                year=year,
                month=month,
                total=round(total, 2),
                by_bank={k: round(v, 2) for k, v in monthly_by_bank.get(key, {}).items()},
                by_category={
                    k: round(v, 2) for k, v in monthly_by_cat.get(key, {}).items()
                },
            )
        )

    # Overall trend + forecast (3 months ahead)
    trends = _compute_trend(monthly_totals, forecast_months=3)

    # Per-category trends
    category_trends = _compute_category_trends(filtered, months, forecast_months=3)

    from .models import SyncStatusDB
    sync = db.query(SyncStatusDB).first()

    return {
        "total_period": round(total_period, 2),
        "months_analyzed": months,
        "transactions_count": len(filtered),
        "categories": categories,
        "monthly_totals": monthly_totals,
        "trends": trends,
        "category_trends": category_trends,
        "by_bank": by_bank,
        "last_sync": sync.last_sync if sync else None,
    }


def _compute_trend(
    monthly_totals: list[MonthlyTotal], forecast_months: int = 3
) -> list[TrendPoint]:
    """Linear regression on historical data + forecast."""
    if not monthly_totals:
        return []

    x = np.arange(len(monthly_totals))
    y = np.array([m.total for m in monthly_totals])

    non_zero = y[y > 0]
    if len(non_zero) < 2:
        return [
            TrendPoint(year=m.year, month=m.month, total=m.total, is_forecast=False)
            for m in monthly_totals
        ]

    coeffs = np.polyfit(x, y, 1)
    poly = np.poly1d(coeffs)

    points = [
        TrendPoint(
            year=m.year,
            month=m.month,
            total=round(float(poly(i)), 2),
            is_forecast=False,
        )
        for i, m in enumerate(monthly_totals)
    ]

    # Forecast ahead
    last = monthly_totals[-1]
    for j in range(1, forecast_months + 1):
        year = last.year
        month = last.month + j
        while month > 12:
            month -= 12
            year += 1
        forecast_val = max(0.0, float(poly(len(monthly_totals) - 1 + j)))
        points.append(
            TrendPoint(
                year=year,
                month=month,
                total=round(forecast_val, 2),
                is_forecast=True,
            )
        )

    return points


def _compute_category_trends(
    transactions: list[TransactionDB],
    months: int,
    forecast_months: int = 3,
) -> list[CategoryTrend]:
    """Per-category trend with forecast."""
    cat_monthly: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for t in transactions:
        key = _month_key(t.invoice_year, t.invoice_month)
        cat_monthly[t.category.value][key] += t.amount

    today = date.today()
    month_list = []
    for i in range(months - 1, -1, -1):
        year, month = today.year, today.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_list.append((year, month))

    result = []
    for cat, monthly_data in cat_monthly.items():
        y_vals = [monthly_data.get(_month_key(yr, mo), 0.0) for yr, mo in month_list]
        y = np.array(y_vals)

        if sum(v > 0 for v in y_vals) < 2:
            points = [
                TrendPoint(year=yr, month=mo, total=round(v, 2), is_forecast=False)
                for (yr, mo), v in zip(month_list, y_vals)
            ]
        else:
            x = np.arange(len(month_list))
            coeffs = np.polyfit(x, y, 1)
            poly = np.poly1d(coeffs)
            points = [
                TrendPoint(
                    year=yr,
                    month=mo,
                    total=round(max(0.0, float(poly(i))), 2),
                    is_forecast=False,
                )
                for i, (yr, mo) in enumerate(month_list)
            ]

        # Forecast
        last_yr, last_mo = month_list[-1]
        for j in range(1, forecast_months + 1):
            yr = last_yr
            mo = last_mo + j
            while mo > 12:
                mo -= 12
                yr += 1
            if sum(v > 0 for v in y_vals) >= 2:
                fval = max(0.0, float(poly(len(month_list) - 1 + j)))
            else:
                fval = float(np.mean(y[y > 0])) if any(v > 0 for v in y_vals) else 0.0
            points.append(
                TrendPoint(year=yr, month=mo, total=round(fval, 2), is_forecast=True)
            )

        result.append(CategoryTrend(category=cat, points=points))

    # Sort by total descending
    result.sort(
        key=lambda ct: sum(p.total for p in ct.points if not p.is_forecast),
        reverse=True,
    )
    return result


def _empty_analytics(months: int) -> dict:
    return {
        "total_period": 0.0,
        "months_analyzed": months,
        "transactions_count": 0,
        "categories": [],
        "monthly_totals": [],
        "trends": [],
        "category_trends": [],
        "by_bank": {},
        "last_sync": None,
    }
