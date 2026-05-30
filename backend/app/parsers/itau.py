"""
Itaú email parser.

Handles:
1. Monthly invoice notification emails with embedded transaction tables
2. PDF invoice attachments (via pdfplumber)
"""
import hashlib
import io
import re
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup

from .base import Transaction, parse_brl_amount, parse_pt_date

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


ITAU_SENDERS = [
    "itau@itau.com.br",
    "fatura@itau.com.br",
    "extrato@itau.com.br",
    "marketing@itau.com.br",
    "noreply@itau.com.br",
    "no-reply@itau.com.br",
]

ITAU_SUBJECT_PATTERNS = [
    r"ita[uú]",
    r"fatura.*ita",
    r"extrato.*ita",
    r"cartao.*ita[uú]",
]


def is_itau_email(sender: str, subject: str) -> bool:
    sender_lower = sender.lower()
    if any(s in sender_lower for s in ITAU_SENDERS) or "itau" in sender_lower:
        return True
    subject_lower = subject.lower()
    return any(re.search(p, subject_lower) for p in ITAU_SUBJECT_PATTERNS)


class ItauParser:
    BANK = "itau"

    def parse(
        self,
        message_id: str,
        subject: str,
        body_html: str,
        body_text: str,
        received_date: date,
        pdf_attachments: Optional[list[bytes]] = None,
    ) -> list[Transaction]:
        # Try PDF first (most complete data)
        if pdf_attachments and HAS_PDFPLUMBER:
            transactions = []
            for pdf_bytes in pdf_attachments:
                transactions.extend(
                    self._parse_pdf(message_id, pdf_bytes, received_date)
                )
            if transactions:
                return transactions

        # Fallback to HTML
        if body_html:
            transactions = self._parse_html(message_id, body_html, received_date)
            if transactions:
                return transactions

        # Fallback to plain text
        if body_text:
            return self._parse_text(message_id, body_text, received_date)

        return []

    def _parse_pdf(
        self, message_id: str, pdf_bytes: bytes, received_date: date
    ) -> list[Transaction]:
        transactions = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            tx = self._parse_row(message_id, [str(c or "") for c in row], received_date)
                            if tx:
                                transactions.append(tx)

                    # Extract text lines as fallback
                    if not transactions:
                        text = page.extract_text() or ""
                        for line in text.splitlines():
                            tx = self._parse_line(message_id, line.strip(), received_date)
                            if tx:
                                transactions.append(tx)
        except Exception:
            pass
        return transactions

    def _parse_html(
        self, message_id: str, html: str, received_date: date
    ) -> list[Transaction]:
        transactions = []
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()

        # Table rows
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                texts = [c.get_text(separator=" ", strip=True) for c in cells]
                tx = self._parse_row(message_id, texts, received_date)
                if tx:
                    transactions.append(tx)

        if transactions:
            return transactions

        # Line-by-line
        text = soup.get_text(separator="\n")
        for line in text.splitlines():
            tx = self._parse_line(message_id, line.strip(), received_date)
            if tx:
                transactions.append(tx)

        return transactions

    def _parse_text(
        self, message_id: str, text: str, received_date: date
    ) -> list[Transaction]:
        transactions = []
        for line in text.splitlines():
            tx = self._parse_line(message_id, line.strip(), received_date)
            if tx:
                transactions.append(tx)
        return transactions

    def _parse_row(
        self, message_id: str, cells: list[str], received_date: date
    ) -> Optional[Transaction]:
        amount = None
        tx_date = None
        description = None

        for cell in cells:
            cell = cell.strip()
            if not cell:
                continue
            if tx_date is None:
                d = parse_pt_date(cell)
                if d:
                    tx_date = d
                    continue
            if amount is None:
                a = parse_brl_amount(cell)
                if a is not None and a > 0:
                    amount = a
                    continue
            if description is None and len(cell) > 3 and not re.match(r"^[\d/.,R$\s\-]+$", cell):
                description = cell

        if amount and description:
            if tx_date is None:
                tx_date = received_date
            ext_id = hashlib.md5(
                f"itau|{description}|{amount}|{tx_date}".encode()
            ).hexdigest()
            return Transaction(
                external_id=f"{message_id}_{ext_id}",
                description=description,
                amount=amount,
                transaction_date=tx_date,
                invoice_month=tx_date.month,
                invoice_year=tx_date.year,
            )
        return None

    def _parse_line(
        self, message_id: str, line: str, received_date: date
    ) -> Optional[Transaction]:
        if not line or len(line) < 10:
            return None

        # Pattern: "DD/MM  Description  R$ X.XXX,XX"
        m = re.search(
            r"(\d{2}/\d{2}(?:/\d{2,4})?)\s+(.+?)\s+R?\$?\s*([\d.]+,\d{2})\s*$",
            line,
        )
        if m:
            raw_date = m.group(1)
            description = m.group(2).strip()
            raw_amount = m.group(3)

            if "/" not in raw_date[5:]:
                raw_date += f"/{received_date.year}"

            tx_date = parse_pt_date(raw_date) or received_date
            amount = parse_brl_amount(raw_amount)

            if amount and description and len(description) > 2:
                ext_id = hashlib.md5(
                    f"itau|{description}|{amount}|{tx_date}".encode()
                ).hexdigest()
                return Transaction(
                    external_id=f"{message_id}_{ext_id}",
                    description=description,
                    amount=amount,
                    transaction_date=tx_date,
                    invoice_month=tx_date.month,
                    invoice_year=tx_date.year,
                )
        return None
