from sqlalchemy import Boolean, Column, Float, String, Integer, Date

from database import Base


class Asset(Base):
    """Modelo principal de activo en cartera."""

    __tablename__ = "assets"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=True)
    category = Column(String, nullable=False)  # Acciones, Cripto, Fondos, Cash...
    platform = Column(String, nullable=True)

    quantity = Column(Float, nullable=False, default=0.0)
    price_eur = Column(Float, nullable=False, default=0.0)

    currency = Column(String, nullable=True)  # Por si se almacena en USD u otra

    # Flags de actualización
    yahoo_symbol = Column(String, nullable=True)
    coingecko_id = Column(String, nullable=True)
    coincap_id = Column(String, nullable=True)  # CoinCap API asset ID
    indexa_api = Column(Boolean, default=False)
    manual = Column(Boolean, default=False)

    # Extras UI
    image_url = Column(String, nullable=True)


class HistoricalPrice(Base):
    """Precio histórico diario en EUR por activo (pensado para ~5 años)."""

    __tablename__ = "historical_prices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    price_eur = Column(Float, nullable=False)


class PortfolioSnapshot(Base):
    """Snapshot diario del valor del portafolio - total, por categoría o por activo."""

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    category = Column(String, nullable=True, index=True)  # None = global
    asset_id = Column(String, nullable=True, index=True)  # None = aggregated
    total_value_eur = Column(Float, nullable=False)


