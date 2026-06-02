"""
Nubank email/PDF parser.

Handles:
1. Individual transaction notifications: "Compra no débito/crédito aprovada"
2. Monthly invoice summaries: "A fatura do seu cartão Nubank está fechada"
3. PDF invoice files (no password)
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


NUBANK_SENDERS = [
    "todomundo@nubank.com.br",
    "faleconosco@nubank.com.br",
    "no-reply@nubank.com.br",
    "contato@nubank.com.br",
]

NUBANK_SUBJECT_PATTERNS = [
    r"nubank",
    r"fatura.*cartao",
    r"cart[aã]o.*nubank",
    r"pagamento.*nubank",
    r"vencimento.*nubank",
]


def is_nubank_email(sender: str, subject: str) -> bool:
    sender_lower = sender.lower()
    if any(s in sender_lower for s in NUBANK_SENDERS):
        return True
    subject_lower = subject.lower()
    return any(re.search(p, subject_lower) for p in NUBANK_SUBJECT_PATTERNS)


class NubankParser:
    BANK = "nubank"

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
                transactions.extend(self._parse_pdf(message_id, pdf_bytes, received_date))
            if transactions:
                return transactions

        # Try HTML/text invoice parsing
        transactions = self._parse_invoice(message_id, body_html, body_text, received_date)
        if transactions:
            return transactions

        # Fallback: single transaction notification
        tx = self._parse_single_notification(message_id, subject, body_html, body_text, received_date)
        if tx:
            return [tx]

        return []

    def _parse_pdf(
        self, message_id: str, pdf_bytes: bytes, received_date: date
    ) -> list[Transaction]:
        """Parse a Nubank PDF invoice (no password required)."""
        transactions = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            tx = self._try_parse_row(
                                message_id, [str(c or "") for c in row], received_date
                            )
                            if tx:
                                transactions.append(tx)

                    if not transactions:
                        text = page.extract_text() or ""
                        for line in text.splitlines():
                            tx = self._try_extract_transaction(
                                message_id, line.strip(), received_date
                            )
                            if tx:
                                transactions.append(tx)
        except Exception:
            pass
        return transactions

    def _parse_invoice(
        self, message_id: str, html: str, text: str, received_date: date
    ) -> list[Transaction]:
        """Parse a full monthly invoice email."""
        transactions = []

        if not html:
            return self._parse_invoice_text(message_id, text, received_date)

        soup = BeautifulSoup(html, "lxml")

        # Remove script/style tags
        for tag in soup(["script", "style"]):
            tag.decompose()

        # Nubank invoice tables usually have rows with: date, merchant, amount
        # Pattern 1: table rows with 3+ columns
        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                texts = [c.get_text(strip=True) for c in cells]
                tx = self._try_parse_row(message_id, texts, received_date)
                if tx:
                    transactions.append(tx)

        if transactions:
            return transactions

        # Pattern 2: div-based layouts with date + description + amount
        lines = []
        for el in soup.find_all(["p", "div", "span", "td", "li"]):
            t = el.get_text(separator=" ", strip=True)
            if t:
                lines.append(t)

        return self._parse_lines(message_id, lines, received_date)

    def _parse_invoice_text(
        self, message_id: str, text: str, received_date: date
    ) -> list[Transaction]:
        if not text:
            return []
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return self._parse_lines(message_id, lines, received_date)

    def _parse_lines(
        self, message_id: str, lines: list[str], received_date: date
    ) -> list[Transaction]:
        transactions = []
        # Look for pattern: line with date, followed by description, followed by amount
        # or combined in single line
        for line in lines:
            tx = self._try_extract_transaction(message_id, line, received_date)
            if tx:
                transactions.append(tx)
        return transactions

    def _try_parse_row(
        self, message_id: str, cells: list[str], received_date: date
    ) -> Optional[Transaction]:
        """Try to parse a table row as a transaction."""
        amount = None
        tx_date = None
        description = None

        for cell in cells:
            if amount is None:
                a = parse_brl_amount(cell)
                if a is not None and a > 0:
                    amount = a

            if tx_date is None:
                d = parse_pt_date(cell)
                if d:
                    tx_date = d

            if description is None and len(cell) > 3 and not re.match(r"^[\d/.,R$\s]+$", cell):
                description = cell

        if amount and description:
            if tx_date is None:
                tx_date = received_date
            invoice_month = tx_date.month
            invoice_year = tx_date.year
            ext_id = hashlib.md5(
                f"nubank|{description}|{amount}|{tx_date}".encode()
            ).hexdigest()
            return Transaction(
                external_id=f"{message_id}_{ext_id}",
                description=description,
                amount=amount,
                transaction_date=tx_date,
                invoice_month=invoice_month,
                invoice_year=invoice_year,
            )
        return None

    def _try_extract_transaction(
        self, message_id: str, line: str, received_date: date
    ) -> Optional[Transaction]:
        """Try to extract a transaction from a single line of text."""
        # Pattern: "DD/MM  Merchant Name  R$ X.XXX,XX"
        m = re.search(
            r"(\d{2}/\d{2}(?:/\d{2,4})?)\s+(.+?)\s+R?\$?\s*([\d.]+,\d{2})",
            line,
        )
        if m:
            raw_date = m.group(1)
            description = m.group(2).strip()
            raw_amount = m.group(3)

            if len(raw_date) <= 5:  # DD/MM without year
                raw_date += f"/{received_date.year}"

            tx_date = parse_pt_date(raw_date) or received_date
            amount = parse_brl_amount(raw_amount)

            if amount and description and len(description) > 2:
                ext_id = hashlib.md5(
                    f"nubank|{description}|{amount}|{tx_date}".encode()
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

    def _parse_single_notification(
        self,
        message_id: str,
        subject: str,
        html: str,
        text: str,
        received_date: date,
    ) -> Optional[Transaction]:
        """Parse a single transaction notification email."""
        content = html or text or subject

        # "Você utilizou R$ 123,45 no Merchant em 01/01/2024"
        m = re.search(
            r"[Vv]oc[êe]\s+utilizou?\s+R?\$?\s*([\d.]+,\d{2})\s+(?:no|na|em|n[ao])\s+(.+?)(?:\s+em\s+(\d{2}/\d{2}/?\d*))?[.\n]",
            content,
            re.DOTALL,
        )
        if m:
            amount = parse_brl_amount(m.group(1))
            description = m.group(2).strip()[:100]
            raw_date = m.group(3)
            tx_date = parse_pt_date(raw_date) if raw_date else received_date

            if amount and description:
                ext_id = hashlib.md5(
                    f"nubank|{description}|{amount}|{tx_date}".encode()
                ).hexdigest()
                return Transaction(
                    external_id=f"{message_id}_{ext_id}",
                    description=description,
                    amount=amount,
                    transaction_date=tx_date or received_date,
                    invoice_month=(tx_date or received_date).month,
                    invoice_year=(tx_date or received_date).year,
                )

        # "Compra de R$ 123,45 aprovada - Merchant"
        m = re.search(
            r"[Cc]ompra?\s+de?\s+R?\$?\s*([\d.]+,\d{2})\s+aprovada?\s*[-–]\s*(.+?)[\n.]",
            content,
            re.DOTALL,
        )
        if m:
            amount = parse_brl_amount(m.group(1))
            description = m.group(2).strip()[:100]
            if amount and description:
                ext_id = hashlib.md5(
                    f"nubank|{description}|{amount}|{received_date}".encode()
                ).hexdigest()
                return Transaction(
                    external_id=f"{message_id}_{ext_id}",
                    description=description,
                    amount=amount,
                    transaction_date=received_date,
                    invoice_month=received_date.month,
                    invoice_year=received_date.year,
                )

        return None
