"""
Credit Card Expense Tracker API
"""
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .auth import (
    clear_session,
    credentials_from_dict,
    credentials_to_dict,
    exchange_code,
    get_authorization_url,
    get_session,
    refresh_credentials,
    store_session,
)
from .analytics import compute_analytics
from .categorizer import classify
from .database import get_db, init_db
from .file_processor import detect_bank, process_pdf
from .models import (
    AuthStatus,
    BankEnum,
    CategoryEnum,
    DashboardResponse,
    SyncRequest,
    SyncResponse,
    SyncStatusDB,
    Transaction,
    TransactionDB,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Credit Card Expense Tracker",
    description="Consolidate and analyze credit card expenses from local PDF files",
    version="2.0.0",
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ─── Auth (optional — only needed for Gmail sync) ──────────────────────────────

COOKIE_NAME = "session_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def get_optional_credentials(request: Request):
    """Returns credentials or None — does not raise."""
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        return None
    session = get_session(session_id)
    if not session or "credentials" not in session:
        return None
    try:
        creds = credentials_from_dict(session["credentials"])
        return refresh_credentials(creds)
    except Exception:
        return None


def require_credentials(request: Request):
    creds = get_optional_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Gmail authentication required")
    return creds


@app.get("/auth/status", response_model=AuthStatus)
def auth_status(request: Request):
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        return AuthStatus(authenticated=False)
    session = get_session(session_id)
    if not session or "credentials" not in session:
        return AuthStatus(authenticated=False)
    return AuthStatus(authenticated=True, email=session.get("email"))


@app.get("/auth/google")
def auth_google():
    auth_url, state = get_authorization_url()
    return {"auth_url": auth_url, "state": state}


@app.get("/auth/callback")
def auth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(default=""),
    error: Optional[str] = Query(default=None),
):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}?error={error}")

    try:
        from .gmail import GmailClient
        creds = exchange_code(code, state)
        client = GmailClient(creds)
        email = client.get_user_email()

        session_id = str(uuid.uuid4())
        store_session(session_id, {
            "credentials": credentials_to_dict(creds),
            "email": email,
        })

        redirect = RedirectResponse(url=FRONTEND_URL)
        redirect.set_cookie(
            key=COOKIE_NAME,
            value=session_id,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
        return redirect
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}?error=auth_failed")


@app.post("/auth/logout")
def auth_logout(request: Request, response: Response):
    session_id = request.cookies.get(COOKIE_NAME)
    if session_id:
        clear_session(session_id)
    response.delete_cookie(COOKIE_NAME)
    return {"success": True}


# ─── Local file upload ─────────────────────────────────────────────────────────

class UploadResult:
    def __init__(self):
        self.files: list[dict] = []
        self.total_imported = 0


from pydantic import BaseModel

class FileResult(BaseModel):
    filename: str
    bank: Optional[str]
    transactions_found: int
    transactions_imported: int
    error: Optional[str] = None


class UploadResponse(BaseModel):
    success: bool
    files: list[FileResult]
    total_imported: int
    message: str


@app.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload one or more PDF invoice files for processing."""
    results: list[FileResult] = []
    total_imported = 0

    for upload in files:
        filename = upload.filename or "arquivo.pdf"

        if not filename.lower().endswith(".pdf"):
            results.append(FileResult(
                filename=filename,
                bank=None,
                transactions_found=0,
                transactions_imported=0,
                error="Apenas arquivos PDF são suportados",
            ))
            continue

        try:
            content = await upload.read()
            bank_name, raw_transactions = process_pdf(filename, content)

            imported = 0
            for tx in raw_transactions:
                existing = db.query(TransactionDB).filter(
                    TransactionDB.external_id == tx.external_id
                ).first()
                if existing:
                    continue

                bank_enum = _name_to_bank_enum(bank_name)
                category = classify(tx.description)
                db_tx = TransactionDB(
                    external_id=tx.external_id,
                    bank=bank_enum,
                    description=tx.description,
                    amount=tx.amount,
                    transaction_date=tx.transaction_date,
                    category=category,
                    invoice_month=tx.invoice_month,
                    invoice_year=tx.invoice_year,
                )
                db.add(db_tx)
                imported += 1

            total_imported += imported

            results.append(FileResult(
                filename=filename,
                bank=bank_name if bank_name != "unknown" else None,
                transactions_found=len(raw_transactions),
                transactions_imported=imported,
            ))

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}", exc_info=True)
            results.append(FileResult(
                filename=filename,
                bank=detect_bank(filename),
                transactions_found=0,
                transactions_imported=0,
                error=str(e),
            ))

    # Update sync status
    try:
        sync = db.query(SyncStatusDB).first()
        if not sync:
            sync = SyncStatusDB()
            db.add(sync)
        sync.last_sync = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()

    return UploadResponse(
        success=True,
        files=results,
        total_imported=total_imported,
        message=f"{total_imported} transações importadas de {len(files)} arquivo(s).",
    )


def _name_to_bank_enum(name: str) -> BankEnum:
    mapping = {"nubank": BankEnum.NUBANK, "itau": BankEnum.ITAU, "santander": BankEnum.SANTANDER}
    return mapping.get(name, BankEnum.NUBANK)


# ─── Gmail sync (optional, requires Google auth) ───────────────────────────────

@app.post("/sync", response_model=SyncResponse)
def sync_transactions(
    body: SyncRequest,
    db: Session = Depends(get_db),
    creds=Depends(require_credentials),
):
    """Fetch emails from Gmail and import new transactions."""
    from .gmail import GmailClient
    months = max(1, min(body.months, 24))

    try:
        client = GmailClient(creds)
        raw_transactions = client.fetch_transactions(months=months)
        logger.info(f"Parsed {len(raw_transactions)} raw transactions from Gmail")

        imported = 0
        for tx in raw_transactions:
            existing = db.query(TransactionDB).filter(
                TransactionDB.external_id == tx.external_id
            ).first()
            if existing:
                continue

            category = classify(tx.description)
            db_tx = TransactionDB(
                external_id=tx.external_id,
                bank=_detect_bank_from_id(tx.external_id),
                description=tx.description,
                amount=tx.amount,
                transaction_date=tx.transaction_date,
                category=category,
                invoice_month=tx.invoice_month,
                invoice_year=tx.invoice_year,
            )
            db.add(db_tx)
            imported += 1

        sync = db.query(SyncStatusDB).first()
        if not sync:
            sync = SyncStatusDB()
            db.add(sync)
        sync.last_sync = datetime.utcnow()
        sync.months_synced = months
        db.commit()

        return SyncResponse(
            success=True,
            transactions_imported=imported,
            message=f"Sincronizado com sucesso. {imported} novas transações importadas.",
        )

    except Exception as e:
        logger.error(f"Sync error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro na sincronização: {str(e)}")


def _detect_bank_from_id(external_id: str) -> BankEnum:
    eid = external_id.lower()
    if "itau" in eid:
        return BankEnum.ITAU
    if "santander" in eid:
        return BankEnum.SANTANDER
    return BankEnum.NUBANK


# ─── Dashboard & Transactions (no auth required) ───────────────────────────────

@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    months: int = Query(default=3, ge=1, le=24),
    db: Session = Depends(get_db),
):
    data = compute_analytics(db, months)
    return DashboardResponse(**data)


@app.get("/transactions", response_model=list[Transaction])
def get_transactions(
    months: int = Query(default=3, ge=1, le=24),
    bank: Optional[BankEnum] = Query(default=None),
    category: Optional[CategoryEnum] = Query(default=None),
    db: Session = Depends(get_db),
):
    from datetime import date
    today = date.today()
    cutoff_month = today.month - (months - 1)
    cutoff_year = today.year
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1

    query = db.query(TransactionDB)
    if bank:
        query = query.filter(TransactionDB.bank == bank)
    if category:
        query = query.filter(TransactionDB.category == category)

    txs = query.order_by(
        TransactionDB.invoice_year.desc(),
        TransactionDB.invoice_month.desc(),
        TransactionDB.transaction_date.desc(),
    ).all()

    return [
        t for t in txs
        if (t.invoice_year, t.invoice_month) >= (cutoff_year, cutoff_month)
    ]


@app.put("/transactions/{tx_id}/category")
def update_category(
    tx_id: int,
    category: CategoryEnum,
    db: Session = Depends(get_db),
):
    tx = db.query(TransactionDB).filter(TransactionDB.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tx.category = category
    db.commit()
    return {"success": True}


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
