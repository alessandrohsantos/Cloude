import re
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Transaction:
    external_id: str
    description: str
    amount: float
    transaction_date: date
    invoice_month: int
    invoice_year: int


def parse_brl_amount(text: str) -> Optional[float]:
    """Parse currency strings in both BR (1.234,56) and US (1,234.56) formats."""
    text = text.strip().replace("\xa0", " ").replace("​", "")
    match = re.search(r"R?\$?\s*([\d.,]+)", text)
    if not match:
        return None
    raw = match.group(1).strip()

    last_dot = raw.rfind(".")
    last_comma = raw.rfind(",")

    if last_dot > 0 and last_comma > 0:
        if last_comma > last_dot:
            # BR format: "1.234,56" — dot=thousands, comma=decimal
            raw = raw.replace(".", "").replace(",", ".")
        else:
            # US format: "1,234.56" — comma=thousands, dot=decimal
            raw = raw.replace(",", "")
    elif last_comma > 0:
        after = raw[last_comma + 1:]
        if len(after) <= 2:
            # Looks like decimal: "1234,56"
            raw = raw.replace(",", ".")
        else:
            # Looks like thousands separator: "1,500"
            raw = raw.replace(",", "")
    elif last_dot > 0:
        after = raw[last_dot + 1:]
        if len(after) == 3:
            # Dot as thousands separator: "1.500"
            raw = raw.replace(".", "")
        # else: dot as decimal — leave as-is

    try:
        value = float(raw)
        return value if value > 0 else None
    except ValueError:
        return None


def parse_pt_date(text: str) -> Optional[date]:
    """Parse dates in common Brazilian formats: DD/MM/YYYY, DD/MM/YY, DD MMM YYYY"""
    PT_MONTHS = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
        "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
        "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    }

    # DD/MM/YYYY or DD/MM/YY
    m = re.search(r"(\d{2})/(\d{2})/(\d{2,4})", text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            pass

    # DD Mon YYYY
    m = re.search(r"(\d{1,2})\s+([a-záêçõ]+)\.?\s+(\d{4})", text, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        month = PT_MONTHS.get(m.group(2).lower()[:3].replace("ç", "c").replace("ã", "a"))
        year = int(m.group(3))
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                pass

    # YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    return None
