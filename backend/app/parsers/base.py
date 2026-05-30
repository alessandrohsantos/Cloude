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
    """Parse Brazilian currency strings like R$ 1.234,56 or 1234,56"""
    text = text.strip()
    match = re.search(r"R?\$?\s*([\d.,]+)", text.replace("\xa0", " "))
    if not match:
        return None
    raw = match.group(1)
    raw = raw.replace(".", "").replace(",", ".")
    try:
        return float(raw)
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
