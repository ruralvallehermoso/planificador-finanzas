from typing import Iterable, List, Optional, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

import models, schemas


def get_assets(db: Session) -> List[models.Asset]:
    return db.query(models.Asset).all()


def get_assets_by_category(db: Session, category: str) -> List[models.Asset]:
    return db.query(models.Asset).filter(models.Asset.category == category).all()


def get_asset(db: Session, asset_id: str) -> Optional[models.Asset]:
    return db.get(models.Asset, asset_id)


def create_assets(db: Session, assets: Iterable[schemas.AssetCreate]) -> None:
    for asset in assets:
        db_asset = models.Asset(**asset.model_dump())
        db.merge(db_asset)
    db.commit()


def create_asset_direct(db: Session, asset: schemas.AssetCreate) -> models.Asset:
    db_asset = models.Asset(**asset.model_dump())
    db.add(db_asset)
    return db_asset


def update_asset(db: Session, asset_id: str, data: schemas.AssetUpdate) -> Optional[models.Asset]:
    db_asset = get_asset(db, asset_id)
    if not db_asset:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_asset, field, value)
    db.commit()
    db.refresh(db_asset)
    return db_asset


def update_prices_bulk(db: Session, prices: dict[str, float]) -> None:
    """
    Actualiza en bloque los precios en EUR de los activos según un dict:
    {asset_id: new_price_eur}
    """
    if not prices:
        return
    for asset_id, price in prices.items():
        asset = get_asset(db, asset_id)
        if asset and price is not None:
            asset.price_eur = float(price)
    db.commit()


def save_historical_points(db: Session, points: Dict[str, Dict]) -> None:
    """
    Guarda precios históricos en la tabla historical_prices.
    points: {asset_id: {date: price_eur, ...}, ...}
    Evita duplicados: si ya existe un registro para (asset_id, date), lo actualiza.
    """
    if not points:
        return
    for asset_id, series in points.items():
        for d, price in series.items():
            # Verificar si ya existe
            existing = db.query(models.HistoricalPrice).filter(
                models.HistoricalPrice.asset_id == asset_id,
                models.HistoricalPrice.date == d
            ).first()
            if existing:
                existing.price_eur = float(price)
            else:
                hp = models.HistoricalPrice(asset_id=asset_id, date=d, price_eur=float(price))
                db.add(hp)
    db.commit()


def get_history_for_asset(db: Session, asset_id: str, limit_days: int = 365 * 5) -> List[models.HistoricalPrice]:
    """
    Devuelve histórico de un activo, limitado (por defecto) a ~5 años.
    """
    stmt = (
        select(models.HistoricalPrice)
        .where(models.HistoricalPrice.asset_id == asset_id)
        .order_by(models.HistoricalPrice.date.desc())
        .limit(limit_days)
    )
    result = db.execute(stmt).scalars().all()
    return list(reversed(result))


# ============= Portfolio History Functions =============

from datetime import date, timedelta


def get_portfolio_snapshots(
    db: Session,
    start_date: date,
    end_date: date,
    category: Optional[str] = None,
    asset_id: Optional[str] = None
) -> List[models.PortfolioSnapshot]:
    """
    Obtiene snapshots del portafolio para un rango de fechas.
    """
    stmt = (
        select(models.PortfolioSnapshot)
        .where(models.PortfolioSnapshot.date >= start_date)
        .where(models.PortfolioSnapshot.date <= end_date)
    )
    
    if category is not None:
        stmt = stmt.where(models.PortfolioSnapshot.category == category)
    else:
        stmt = stmt.where(models.PortfolioSnapshot.category.is_(None))
    
    if asset_id is not None:
        stmt = stmt.where(models.PortfolioSnapshot.asset_id == asset_id)
    else:
        stmt = stmt.where(models.PortfolioSnapshot.asset_id.is_(None))
    
    stmt = stmt.order_by(models.PortfolioSnapshot.date.asc())
    
    return list(db.execute(stmt).scalars().all())


def save_portfolio_snapshot(
    db: Session,
    snapshot_date: date,
    total_value: float,
    category: Optional[str] = None,
    asset_id: Optional[str] = None
) -> models.PortfolioSnapshot:
    """
    Guarda un snapshot del valor del portafolio. Si ya existe uno para la fecha/filtro, lo actualiza.
    """
    # Buscar si ya existe
    stmt = select(models.PortfolioSnapshot).where(
        models.PortfolioSnapshot.date == snapshot_date,
        models.PortfolioSnapshot.category == category,
        models.PortfolioSnapshot.asset_id == asset_id
    )
    existing = db.execute(stmt).scalars().first()
    
    if existing:
        existing.total_value_eur = total_value
        db.commit()
        db.refresh(existing)
        return existing
    else:
        snapshot = models.PortfolioSnapshot(
            date=snapshot_date,
            category=category,
            asset_id=asset_id,
            total_value_eur=total_value
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot


def reconstruct_portfolio_history(
    db: Session,
    start_date: date,
    end_date: date,
    category: Optional[str] = None,
    asset_id: Optional[str] = None,
    asset_ids: Optional[List[str]] = None
) -> List[Dict]:
    """
    Reconstruye el histórico del portafolio basándose en precios históricos
    y cantidades actuales de activos.
    
    Usa forward-fill: si no hay precio para una fecha, usa el último conocido.
    
    Returns: Lista de {date, value}
    """
    # Obtener activos filtrados
    assets = get_assets(db)
    if category:
        assets = [a for a in assets if a.category == category]
    if asset_id:
        assets = [a for a in assets if a.id == asset_id]
        
    if asset_ids:
        assets = [a for a in assets if a.id in asset_ids]
    
    # Exclude idx_1 (total Indexa) if individual Indexa accounts exist to avoid double-counting
    individual_indexa = [a for a in assets if a.id.startswith('idx_') and a.id != 'idx_1']
    if individual_indexa:
        assets = [a for a in assets if a.id != 'idx_1']
    
    if not assets:
        return []
    
    # Obtener todos los precios históricos para los activos seleccionados
    asset_ids = [a.id for a in assets]
    all_prices: Dict[str, Dict[date, float]] = {}
    
    for aid in asset_ids:
        history = get_history_for_asset(db, aid, limit_days=365 * 5)
        all_prices[aid] = {h.date: h.price_eur for h in history}
    
    # Construir serie temporal con forward-fill
    result = []
    current = start_date
    asset_qty = {a.id: a.quantity for a in assets}
    
    # Inicializar último precio conocido por activo (buscar precio más antiguo antes de start_date)
    last_known_price = {}
    for aid in asset_ids:
        prices = all_prices.get(aid, {})
        # Buscar el precio más reciente anterior o igual a start_date
        earlier_prices = [(d, p) for d, p in prices.items() if d <= start_date]
        if earlier_prices:
            last_known_price[aid] = max(earlier_prices, key=lambda x: x[0])[1]
        else:
            # Si no hay precio anterior, usar el primer precio disponible o 0
            if prices:
                last_known_price[aid] = min(prices.items(), key=lambda x: x[0])[1]
            else:
                last_known_price[aid] = 0.0
    
    while current <= end_date:
        total = 0.0
        for aid in asset_ids:
            price = all_prices.get(aid, {}).get(current)
            if price is not None:
                last_known_price[aid] = price
            # Usar el último precio conocido (forward-fill)
            total += last_known_price.get(aid, 0) * asset_qty.get(aid, 0)
        
        # Solo añadir si hay algún valor (evita días antes de tener datos)
        if total > 0:
            result.append({"date": current, "value": total})
        
        current += timedelta(days=1)
    
    return result


def calculate_portfolio_value(
    db: Session, 
    category: Optional[str] = None, 
    asset_id: Optional[str] = None,
    asset_ids: Optional[List[str]] = None
) -> float:
    """
    Calcula el valor actual del portafolio.
    """
    assets = get_assets(db)
    
    if category:
        assets = [a for a in assets if a.category == category]
    if asset_id:
        assets = [a for a in assets if a.id == asset_id]
        
    if asset_ids:
        assets = [a for a in assets if a.id in asset_ids]
    
    # Exclude idx_1 (total Indexa) if individual Indexa accounts exist to avoid double-counting
    individual_indexa = [a for a in assets if a.id.startswith('idx_') and a.id != 'idx_1']
    if individual_indexa:
        assets = [a for a in assets if a.id != 'idx_1']
    
    return sum(a.price_eur * a.quantity for a in assets)


def get_period_dates(period: str) -> tuple[date, date]:
    """
    Convierte un string de periodo a fechas de inicio y fin.
    """
    today = date.today()
    periods = {
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "1m": timedelta(days=30),
        "3m": timedelta(days=90),
        "6m": timedelta(days=180),
        "1y": timedelta(days=365),
        "3y": timedelta(days=365 * 3),
    }
    delta = periods.get(period, timedelta(days=30))
    return (today - delta, today)


def get_assets_with_performance(db: Session, category: Optional[str] = None) -> List[models.Asset]:
    """
    Returns assets with 'change_24h_pct' populated.
    
    Uses Yahoo Finance API's previousClose for stocks/funds and Indexa API
    for Indexa accounts, instead of relying on DB historical prices which
    may be ephemeral on serverless deployments.
    """
    import requests
    
    # 1. Fetch Assets
    if category and category.lower() != "all":
        ids_query = select(models.Asset).where(models.Asset.category == category)
        assets = list(db.execute(ids_query).scalars().all())
    else:
        assets = db.query(models.Asset).all()

    if not assets:
        return []

    YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    YAHOO_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    # 2. Fetch live change data from Yahoo for assets with yahoo_symbol
    yahoo_changes = {}
    for asset in assets:
        if asset.yahoo_symbol and not asset.manual:
            try:
                url = YAHOO_CHART_URL.format(symbol=asset.yahoo_symbol)
                res = requests.get(url, headers=YAHOO_HEADERS, timeout=10)
                if res.ok:
                    data = res.json()
                    meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                    current = meta.get("regularMarketPrice", 0)
                    previous = meta.get("chartPreviousClose", 0) or meta.get("previousClose", 0)
                    
                    if previous and previous > 0 and current and current > 0:
                        change = ((current - previous) / previous) * 100
                        yahoo_changes[asset.id] = round(change, 2)
            except Exception as e:
                print(f"⚠️ Yahoo change fetch error for {asset.id}: {e}")

    # 3. Fallback: use DB historical prices for any remaining assets
    today = date.today()
    since_date = today - timedelta(days=14) # Búsqueda hasta 10 días para sortear fines de semana
    asset_ids = [a.id for a in assets]

    stmt = (
        select(models.HistoricalPrice)
        .where(models.HistoricalPrice.asset_id.in_(asset_ids))
        .where(models.HistoricalPrice.date >= since_date)
        .where(models.HistoricalPrice.date < today)
        .order_by(models.HistoricalPrice.date.desc())
    )
    history = db.execute(stmt).scalars().all()

    # Agrupar historial por asset_id
    history_by_asset = {}
    for h in history:
        if h.asset_id not in history_by_asset:
            history_by_asset[h.asset_id] = []
        history_by_asset[h.asset_id].append(h)

    # 4. Apply changes to assets — Yahoo live data takes priority, then DB fallback
    for asset in assets:
        change = 0.0
        
        if asset.id in yahoo_changes:
            change = yahoo_changes[asset.id]
        elif asset.id in history_by_asset:
            asset_history = history_by_asset[asset.id]
            current = asset.price_eur
            previous = None
            
            # Buscar el primer precio histórico que difiera del precio actual (último cierre distinto)
            for h in asset_history:
                # Si hay diferencia de más del 0.01%
                if abs(h.price_eur - current) / current > 0.0001:
                    previous = h.price_eur
                    break
                    
            # Si todos los precios recientes son iguales, devolvemos el cambio a 0.0%
            if previous and previous > 0:
                change = ((current - previous) / previous) * 100.0
        
        asset.change_24h_pct = round(change, 2)

    return assets



