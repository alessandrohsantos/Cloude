"""
Local PDF file processor — detects bank from filename and parses transactions.
"""
import hashlib
import re
from datetime import date, datetime
from typing import Optional

from .parsers.base import Transaction
from .parsers.itau import ItauParser
from .parsers.santander import SantanderParser
from .parsers.nubank import NubankParser


def detect_bank(filename: str) -> Optional[str]:
    name = filename.lower()
    # Normalize accented chars for matching
    name = name.replace("ã", "a").replace("á", "a").replace("ú", "u").replace("í", "i")
    if re.search(r"itau|ita[uú]", name):
        return "itau"
    if "santander" in name:
        return "santander"
    if "nubank" in name:
        return "nubank"
    return None


def process_pdf(
    filename: str,
    content: bytes,
    received_date: Optional[date] = None,
) -> tuple[str, list[Transaction]]:
    """
    Parse a PDF invoice file. Returns (bank, transactions).
    If bank cannot be inferred from filename, tries all three parsers.
    """
    if received_date is None:
        received_date = datetime.now().date()

    # Use a stable ID derived from filename + size so re-uploading the same
    # file won't create duplicate transactions.
    file_hash = hashlib.md5(f"{filename}:{len(content)}".encode()).hexdigest()

    bank = detect_bank(filename)
    candidates = [bank] if bank else ["itau", "santander", "nubank"]

    for candidate in candidates:
        txs = _try_parse(candidate, file_hash, filename, content, received_date)
        if txs:
            return candidate, txs

    return bank or "unknown", []


def _try_parse(
    bank: str,
    file_hash: str,
    filename: str,
    content: bytes,
    received_date: date,
) -> list[Transaction]:
    try:
        if bank == "itau":
            parser = ItauParser()
        elif bank == "santander":
            parser = SantanderParser()
        elif bank == "nubank":
            parser = NubankParser()
        else:
            return []

        kwargs = dict(
            message_id=file_hash,
            subject=filename,
            body_html="",
            body_text="",
            received_date=received_date,
        )
        if bank in ("itau", "santander"):
            kwargs["pdf_attachments"] = [content]

        return parser.parse(**kwargs)
    except Exception:
        return []
