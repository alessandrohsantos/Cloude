from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class BankEnum(str, Enum):
    NUBANK = "nubank"
    ITAU = "itau"
    SANTANDER = "santander"


class CategoryEnum(str, Enum):
    ALIMENTACAO = "Alimentação"
    MERCADO = "Mercado"
    TRANSPORTE = "Transporte"
    SAUDE = "Saúde"
    EDUCACAO = "Educação"
    ENTRETENIMENTO = "Entretenimento"
    VESTUARIO = "Vestuário"
    FARMACIA = "Farmácia"
    VIAGEM = "Viagem"
    SERVICOS = "Serviços"
    CASA = "Casa"
    TECNOLOGIA = "Tecnologia"
    OUTROS = "Outros"


class TransactionDB(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    bank = Column(SAEnum(BankEnum), nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_date = Column(Date, nullable=False)
    category = Column(SAEnum(CategoryEnum), default=CategoryEnum.OUTROS)
    invoice_month = Column(Integer, nullable=False)
    invoice_year = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("external_id", name="uq_external_id"),
    )


class SyncStatusDB(Base):
    __tablename__ = "sync_status"

    id = Column(Integer, primary_key=True)
    last_sync = Column(DateTime)
    months_synced = Column(Integer, default=0)


# Pydantic schemas

class Transaction(BaseModel):
    id: int
    external_id: str
    bank: BankEnum
    description: str
    amount: float
    transaction_date: date
    category: CategoryEnum
    invoice_month: int
    invoice_year: int

    class Config:
        from_attributes = True


class CategoryTotal(BaseModel):
    category: str
    total: float
    count: int
    percentage: float


class MonthlyTotal(BaseModel):
    year: int
    month: int
    total: float
    by_bank: dict[str, float]
    by_category: dict[str, float]


class TrendPoint(BaseModel):
    year: int
    month: int
    total: float
    is_forecast: bool


class CategoryTrend(BaseModel):
    category: str
    points: list[TrendPoint]


class DashboardResponse(BaseModel):
    total_period: float
    months_analyzed: int
    transactions_count: int
    categories: list[CategoryTotal]
    monthly_totals: list[MonthlyTotal]
    trends: list[TrendPoint]
    category_trends: list[CategoryTrend]
    by_bank: dict[str, float]
    last_sync: Optional[datetime]


class SyncRequest(BaseModel):
    months: int = 3


class SyncResponse(BaseModel):
    success: bool
    transactions_imported: int
    message: str


class AuthStatus(BaseModel):
    authenticated: bool
    email: Optional[str] = None
