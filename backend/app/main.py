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

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
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
from .gmail import GmailClient
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
    description="Consolidate and analyze credit card expenses from Gmail",
    version="1.0.0",
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


# ─── Auth ──────────────────────────────────────────────────────────────────────

COOKIE_NAME = "session_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def get_credentials(request: Request):
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = get_session(session_id)
    if not session or "credentials" not in session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    creds = credentials_from_dict(session["credentials"])
    creds = refresh_credentials(creds)
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
def auth_google(response: Response):
    auth_url, state = get_authorization_url()
    return {"auth_url": auth_url, "state": state}


@app.get("/auth/callback")
def auth_callback(
    request: Request,
    response: Response,
    code: str = Query(...),
    state: str = Query(default=""),
    error: Optional[str] = Query(default=None),
):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}?error={error}")

    try:
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


# ─── Sync ──────────────────────────────────────────────────────────────────────

@app.post("/sync", response_model=SyncResponse)
def sync_transactions(
    body: SyncRequest,
    db: Session = Depends(get_db),
    creds=Depends(get_credentials),
):
    """Fetch emails from Gmail and import new transactions."""
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
                bank=_detect_bank(tx.external_id),
                description=tx.description,
                amount=tx.amount,
                transaction_date=tx.transaction_date,
                category=category,
                invoice_month=tx.invoice_month,
                invoice_year=tx.invoice_year,
            )
            db.add(db_tx)
            imported += 1

        # Update sync status
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


def _detect_bank(external_id: str) -> BankEnum:
    if "nubank" in external_id.lower():
        return BankEnum.NUBANK
    if "itau" in external_id.lower():
        return BankEnum.ITAU
    if "santander" in external_id.lower():
        return BankEnum.SANTANDER
    return BankEnum.NUBANK


# ─── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    months: int = Query(default=3, ge=1, le=24),
    db: Session = Depends(get_db),
    creds=Depends(get_credentials),
):
    data = compute_analytics(db, months)
    return DashboardResponse(**data)


@app.get("/transactions", response_model=list[Transaction])
def get_transactions(
    months: int = Query(default=3, ge=1, le=24),
    bank: Optional[BankEnum] = Query(default=None),
    category: Optional[CategoryEnum] = Query(default=None),
    db: Session = Depends(get_db),
    creds=Depends(get_credentials),
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

    # Filter by date range
    filtered = [
        t for t in txs
        if (t.invoice_year, t.invoice_month) >= (cutoff_year, cutoff_month)
    ]

    return filtered


@app.put("/transactions/{tx_id}/category")
def update_category(
    tx_id: int,
    category: CategoryEnum,
    db: Session = Depends(get_db),
    creds=Depends(get_credentials),
):
    tx = db.query(TransactionDB).filter(TransactionDB.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tx.category = category
    db.commit()
    return {"success": True}


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
