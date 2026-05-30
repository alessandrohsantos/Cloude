"""
Gmail API client for fetching credit card invoice emails.
"""
import base64
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .parsers import NubankParser, ItauParser, SantanderParser
from .parsers.nubank import is_nubank_email
from .parsers.itau import is_itau_email
from .parsers.santander import is_santander_email
from .parsers.base import Transaction

logger = logging.getLogger(__name__)

BANK_QUERIES = {
    "nubank": (
        '(from:nubank.com.br OR subject:nubank OR subject:"fatura nubank") '
        'subject:(fatura OR compra OR pagamento OR extrato)'
    ),
    "itau": (
        '(from:itau.com.br OR subject:itau OR subject:itaú) '
        'subject:(fatura OR extrato OR cartao)'
    ),
    "santander": (
        '(from:santander.com.br OR subject:santander) '
        'subject:(fatura OR extrato OR cartao)'
    ),
}


def _decode_payload(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "==")


def _extract_body(payload: dict) -> tuple[str, str, list[bytes]]:
    """Returns (html_body, text_body, pdf_attachments)."""
    html_parts = []
    text_parts = []
    pdfs = []

    def walk(part: dict):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        filename = part.get("filename", "")

        if mime == "text/html" and body.get("data"):
            html_parts.append(_decode_payload(body["data"]).decode("utf-8", errors="replace"))
        elif mime == "text/plain" and body.get("data"):
            text_parts.append(_decode_payload(body["data"]).decode("utf-8", errors="replace"))
        elif mime == "application/pdf" and body.get("attachmentId"):
            pdfs.append(body["attachmentId"])
        elif filename.lower().endswith(".pdf") and body.get("attachmentId"):
            pdfs.append(body["attachmentId"])

        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)
    return "\n".join(html_parts), "\n".join(text_parts), pdfs


class GmailClient:
    def __init__(self, credentials: Credentials):
        self.service = build("gmail", "v1", credentials=credentials)

    def get_user_email(self) -> str:
        profile = self.service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")

    def fetch_transactions(self, months: int = 3) -> list[Transaction]:
        """Fetch and parse transactions from all three banks."""
        since_date = datetime.now() - timedelta(days=months * 31)
        after_str = since_date.strftime("%Y/%m/%d")

        all_transactions: list[Transaction] = []
        parsers = {
            "nubank": (NubankParser(), is_nubank_email),
            "itau": (ItauParser(), is_itau_email),
            "santander": (SantanderParser(), is_santander_email),
        }

        for bank, (parser, detector) in parsers.items():
            query = f"{BANK_QUERIES[bank]} after:{after_str}"
            logger.info(f"Searching Gmail for {bank}: {query}")

            try:
                messages = self._list_messages(query)
                logger.info(f"Found {len(messages)} emails for {bank}")

                for msg_meta in messages:
                    msg_id = msg_meta["id"]
                    try:
                        msg = self._get_message(msg_id)
                        transactions = self._process_message(
                            msg, msg_id, parser, detector
                        )
                        all_transactions.extend(transactions)
                    except Exception as e:
                        logger.warning(f"Error processing message {msg_id}: {e}")

            except HttpError as e:
                logger.error(f"Gmail API error for {bank}: {e}")

        return all_transactions

    def _list_messages(self, query: str) -> list[dict]:
        messages = []
        request = self.service.users().messages().list(
            userId="me", q=query, maxResults=500
        )
        while request:
            response = request.execute()
            messages.extend(response.get("messages", []))
            request = self.service.users().messages().list_next(request, response)
        return messages

    def _get_message(self, message_id: str) -> dict:
        return self.service.users().messages().get(
            userId="me", messageId=message_id, format="full"
        ).execute()

    def _process_message(
        self, msg: dict, msg_id: str, parser, detector
    ) -> list[Transaction]:
        payload = msg.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

        sender = headers.get("from", "")
        subject = headers.get("subject", "")
        date_str = headers.get("date", "")

        received_date = self._parse_email_date(date_str)

        # Verify it's the right bank
        if not detector(sender, subject):
            return []

        html_body, text_body, pdf_attachment_ids = _extract_body(payload)

        # Fetch PDF attachments
        pdf_bytes_list = []
        for att_id in pdf_attachment_ids:
            try:
                att = self.service.users().messages().attachments().get(
                    userId="me", messageId=msg_id, id=att_id
                ).execute()
                pdf_bytes_list.append(_decode_payload(att["data"]))
            except Exception as e:
                logger.warning(f"Could not fetch attachment {att_id}: {e}")

        # Parse
        if hasattr(parser, "parse"):
            kwargs = {
                "message_id": msg_id,
                "subject": subject,
                "body_html": html_body,
                "body_text": text_body,
                "received_date": received_date,
            }
            if pdf_bytes_list:
                kwargs["pdf_attachments"] = pdf_bytes_list
            try:
                return parser.parse(**kwargs)
            except Exception as e:
                logger.warning(f"Parser error for {msg_id}: {e}")

        return []

    @staticmethod
    def _parse_email_date(date_str: str) -> date:
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %Z",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:31].strip(), fmt).date()
            except ValueError:
                continue
        return datetime.now().date()
