from datetime import date
from typing import Optional, List, Dict, Any

from pydantic import BaseModel


class AssetBase(BaseModel):
    id: str
    name: str
    ticker: Optional[str] = None
    category: str
    platform: Optional[str] = None
    quantity: float
    price_eur: float
    currency: Optional[str] = None
    yahoo_symbol: Optional[str] = None
    coingecko_id: Optional[str] = None
    coincap_id: Optional[str] = None
    indexa_api: bool = False
    manual: bool = False
    image_url: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    quantity: Optional[float] = None
    price_eur: Optional[float] = None
    manual: Optional[bool] = None


class Asset(AssetBase):
    change_24h_pct: Optional[float] = None

    class Config:
        from_attributes = True


class HistoricalPoint(BaseModel):
    date: date
    price_eur: float


class AssetDetail(Asset):
    history: List[HistoricalPoint] = []


class PortfolioHistoryPoint(BaseModel):
    """Punto de histórico de cartera."""
    date: date
    value: float


class PortfolioPerformance(BaseModel):
    """Rendimiento de cartera en un periodo."""
    current_value: float
    previous_value: float
    change_percent: float
    change_absolute: float
    period: str



class MortgageParams(BaseModel):
    principal: float
    annual_rate: float
    years: int
    start_date: Optional[date] = None

class SimulatorRequest(BaseModel):
    mortgage: MortgageParams
    portfolio_basis: Optional[float] = None  # Manual override for investment cost
    tax_rate: float = 19.0
    start_date: date = date(2025, 11, 24)

class AmortizationPoint(BaseModel):
    month: int
    payment: float
    interest: float
    principal: float
    remaining_balance: float
    cumulative_interest: float
    cumulative_principal: float

class SimulatorResponse(BaseModel):
    portfolio_value: float
    portfolio_basis: float
    net_benefit: float
    total_interest_paid: float
    balance: float
    is_profitable: bool
    roi_pct: float
    amortization_schedule: List[AmortizationPoint]
    daily_history: List[Dict[str, Any]]
    asset_breakdown: List[Dict[str, Any]]
    debug_info: Optional[Dict[str, Any]] = None
