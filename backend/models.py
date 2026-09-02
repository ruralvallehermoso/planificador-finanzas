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

    # Flags de actualización y Renta Fija
    yahoo_symbol = Column(String, nullable=True)
    # ISIN del instrumento. Es lo que permite cotizar deuda soberana individual
    # (un bono del Estado no tiene ticker en Yahoo, pero sí cotiza por ISIN en
    # Börse Frankfurt): ver market_client.fetch_isin_price. Tiene prioridad sobre
    # yahoo_symbol y sobre el devengo de cupón al valorar Renta Fija.
    isin = Column(String, nullable=True, index=True)
    coingecko_id = Column(String, nullable=True)
    coincap_id = Column(String, nullable=True)  # CoinCap API asset ID
    indexa_api = Column(Boolean, default=False)
    manual = Column(Boolean, default=False)
    coupon_rate = Column(Float, nullable=True)  # % de rentabilidad/cupón anual para Renta Fija (ej: 3.7)
    # Fecha desde la que se devenga el cupón (normalmente, cuando se dio de alta el bono).
    # Sin ticker de mercado real, el "precio" de un bono se calcula como
    # 1.0 + cupón_anual% * (días transcurridos desde esta fecha / 365) — interés simple,
    # no compuesto, que crece linealmente cada año en vez de recalcularse en cada
    # actualización de mercado (lo que antes componía varias veces al día).
    bond_start_date = Column(Date, nullable=True)
    # Fecha de vencimiento del bono. En la deuda soberana europea el cupón se paga
    # en su aniversario, así que es la que fija el calendario de pagos y permite
    # calcular el cupón corrido sobre el precio limpio de mercado. Se rellena sola
    # desde el registro FIRDS de ESMA cuando el activo tiene ISIN.
    bond_maturity_date = Column(Date, nullable=True)
    # Pagos de cupón al año: 1 anual (deuda española y alemana), 2 semestral
    # (Treasuries y buena parte del crédito), 4 trimestral.
    coupon_frequency = Column(Integer, nullable=True, default=1)

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


