from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any, Dict, List, Tuple

import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
ESMA_FIRDS_URL = "https://registers.esma.europa.eu/solr/esma_registers_firds/select"
BOERSE_FRANKFURT_PRICE_URL = "https://api.boerse-frankfurt.de/v1/data/price_information/single?isin={isin}"
BOERSE_FRANKFURT_QUOTE_URL = "https://api.boerse-frankfurt.de/v1/data/quote_box/single?isin={isin}"
COINGECKO_SIMPLE_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"
COINCAP_BASE_URL = "https://rest.coincap.io/v3"
COINCAP_HISTORY_URL = "https://rest.coincap.io/v3/assets/{id}/history"
CRYPTOCOMPARE_HISTODAY_URL = "https://min-api.cryptocompare.com/data/v2/histoday"
INDEXA_PROXY_URL = "http://localhost:5001"
INDEXA_BASE_URL = "https://api.indexacapital.com"
SERVICE_NAME = "DashboardFinanciero"
USERNAME = "indexa_api"
COINCAP_USERNAME = "coincap_api"
TIMEOUT_SECONDS = 15

# Headers para evitar bloqueos por falta de User-Agent
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json"
}

# Configuración de pesos de cuentas Indexa (Legacy Logic)
INDEXA_WEIGHTS = {
    "2RALDY9V": 0.0,      # Excluida
    "76B4EQKT": 0.44,     # Solo el 44%
    # "23LLWQDX": 1.0     # Default
}


def fetch_usd_eur_rate() -> float | None:
    """Devuelve el cambio USD/EUR usando EUR=X en Yahoo Finance."""
    try:
        url = YAHOO_CHART_URL.format(symbol="EUR=X")
        res = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except Exception as e:
        print(f"⚠️ Error fetching USD/EUR rate: {e}")
        return None


def fetch_yahoo_prices(symbols: Dict[str, str], usd_to_eur: float | None = None) -> Dict[str, float]:
    """
    symbols: {asset_id: yahoo_symbol}
    Devuelve {asset_id: price_eur}
    """
    prices: Dict[str, float] = {}
    for asset_id, symbol in symbols.items():
        try:
            url = YAHOO_CHART_URL.format(symbol=symbol)
            res = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
            res.raise_for_status()
            data = res.json()
            price = float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
            currency = data["chart"]["result"][0]["meta"].get("currency", "EUR")
            if currency == "USD" and usd_to_eur:
                price *= usd_to_eur
            prices[asset_id] = price
        except Exception as e:
            print(f"⚠️ Error fetching Yahoo price for {asset_id} ({symbol}): {e}")
            continue
    return prices


def fetch_bond_reference_data(isin: str) -> Dict[str, Any] | None:
    """
    Ficha del bono (vencimiento, cupón y nombre oficial) desde FIRDS, el registro
    público de instrumentos financieros de ESMA.

    Es la fuente que da la FECHA DE PAGO DEL CUPÓN, que no expone ni Yahoo ni la
    API de cotización de Fráncfort: en la deuda soberana europea el cupón se paga
    en el aniversario del vencimiento (`bnd_maturity_date`), así que con esa fecha
    y el tipo (`bnd_fixed_rate`) ya se puede calcular el cupón corrido.

    Registro oficial, gratuito y sin clave, que cubre cualquier ISIN admitido a
    negociación en la UE: deuda española y alemana, y también Treasuries listados
    aquí. Devuelve None si el ISIN no está o la consulta falla.
    """
    if not isin:
        return None
    clean_isin = re.sub(r"[^A-Za-z0-9]", "", str(isin)).upper()
    if not clean_isin:
        return None

    params = {
        "q": f"isin:{clean_isin}",
        "wt": "json",
        "rows": 5,
        "fl": "gnr_full_name,bnd_maturity_date,bnd_fixed_rate,gnr_notional_curr_code",
    }
    try:
        res = requests.get(ESMA_FIRDS_URL, params=params, headers=DEFAULT_HEADERS, timeout=TIMEOUT_SECONDS)
        res.raise_for_status()
        docs = res.json().get("response", {}).get("docs", [])
    except Exception as e:
        print(f"⚠️ Error consultando ESMA FIRDS para {clean_isin}: {e}")
        return None

    # El mismo ISIN aparece una vez por mercado donde cotiza; la ficha del emisor
    # es idéntica en todas, así que vale la primera que traiga vencimiento.
    for doc in docs:
        raw_maturity = doc.get("bnd_maturity_date")
        if not raw_maturity:
            continue
        try:
            maturity = datetime.strptime(str(raw_maturity)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        try:
            coupon = float(doc["bnd_fixed_rate"]) if doc.get("bnd_fixed_rate") is not None else None
        except (TypeError, ValueError):
            coupon = None
        name = (doc.get("gnr_full_name") or "").strip()
        return {
            "isin": clean_isin,
            "name": " ".join(name.split()) or None,
            "maturity_date": maturity,
            "coupon_rate": coupon,
            "currency": doc.get("gnr_notional_curr_code"),
        }
    return None


def _shift_months(reference: date, months: int) -> date:
    """Suma (o resta) meses conservando el día, recortándolo si el mes es más corto."""
    total = reference.year * 12 + (reference.month - 1) + months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    day = min(reference.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def accrued_coupon_fraction(coupon_rate: float | None, maturity_date: date | None,
                            frequency: int | None = 1, today: date | None = None) -> float:
    """
    Cupón corrido, en tanto por uno del nominal, con base ACT/ACT (la que usan el
    Tesoro y el resto de deuda soberana europea).

    Lo que cotiza el mercado es el precio LIMPIO: no incluye el cupón que el bono
    lleva devengado desde el último pago. Quien compra hoy paga limpio + corrido,
    y esa suma es lo que vale de verdad la posición.

    Los pagos caen en el aniversario del vencimiento (y en sus fracciones si el
    cupón no es anual), así que el calendario se reconstruye retrocediendo desde
    `maturity_date` en saltos de 12/frecuencia meses.

    Salvedad conocida: el primer período de un bono recién emitido suele ser
    irregular (corre desde la emisión, no desde el aniversario anterior), así que
    durante ese primer año el corrido puede salir algo alto. A partir del primer
    pago el cálculo ya es exacto.
    """
    if not coupon_rate or coupon_rate <= 0 or not maturity_date:
        return 0.0

    freq = int(frequency or 1)
    if freq <= 0 or 12 % freq != 0:
        freq = 1

    today = today or date.today()
    if today >= maturity_date:
        return 0.0

    step = 12 // freq
    next_payment = maturity_date
    while _shift_months(next_payment, -step) > today:
        next_payment = _shift_months(next_payment, -step)
    prev_payment = _shift_months(next_payment, -step)

    period_days = (next_payment - prev_payment).days
    if period_days <= 0:
        return 0.0
    elapsed_days = max(0, (today - prev_payment).days)
    return (coupon_rate / 100.0 / freq) * (elapsed_days / period_days)


def fetch_isin_quote(isin: str, usd_to_eur: float | None = None) -> Dict[str, Any] | None:
    """
    Precio de mercado real de un instrumento a partir de su ISIN, vía la API
    pública de la Bolsa de Fráncfort (Börse Frankfurt).

    Es la pieza que le faltaba a la deuda soberana individual: Yahoo Finance no
    indexa un bono del Estado concreto (ES0000012O67 y sus hermanos devuelven
    "No data found, symbol may be delisted" con y sin sufijo de mercado), pero
    Fráncfort sí lista esos bonos y los cotiza por ISIN, con su variación diaria.

    Los bonos cotizan en PORCENTAJE DEL NOMINAL (banderas `tradedInPercent` /
    `nominal` de la API): un lastPrice de 96.21 son 96,21 € por cada 100 € de
    nominal. Se devuelve dividido entre 100 para respetar la convención que la
    app ya usa en Renta Fija, donde `quantity` es el nominal en euros y
    `price_eur` el valor de cada euro nominal (10.000 € nominales × 0,9621 =
    9.621 €). Acciones y ETFs (`nominal` false) se devuelven tal cual.

    Es el precio "limpio" (ex-cupón) del mercado; igual que con un ETF cotizado,
    no se le suma devengo aparte, porque ya es el valor real al que el bono se
    compra y se vende hoy.

    Devuelve el precio ya normalizado junto con `quoted_in_percent`, que es lo que
    permite a quien llama saber si toca sumarle el cupón corrido (un bono) o no
    (una acción o un ETF). None si el ISIN no está listado allí o la API falla,
    para que se pueda caer al método anterior en vez de dejar el activo a cero.
    """
    if not isin:
        return None
    clean_isin = str(isin).strip().upper()

    payload = None
    for url in (BOERSE_FRANKFURT_PRICE_URL.format(isin=clean_isin),
                BOERSE_FRANKFURT_QUOTE_URL.format(isin=clean_isin)):
        try:
            res = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT_SECONDS)
            if res.status_code != 200:
                continue
            data = res.json()
            if data and data.get("lastPrice"):
                payload = data
                break
        except Exception as e:
            print(f"⚠️ Error consultando Börse Frankfurt para {clean_isin}: {e}")
    if not payload:
        return None

    try:
        price = float(payload.get("lastPrice") or 0.0)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    # `tradedInPercent` lo trae price_information; `nominal`, quote_box.
    quoted_in_percent = bool(payload.get("tradedInPercent") or payload.get("nominal"))
    if quoted_in_percent:
        price /= 100.0

    currency = payload.get("currency")
    if isinstance(currency, dict):
        currency = currency.get("originalValue")
    if currency == "USD" and usd_to_eur:
        price *= usd_to_eur

    return {"price": round(price, 6), "quoted_in_percent": quoted_in_percent}


def fetch_isin_price(isin: str, usd_to_eur: float | None = None) -> float | None:
    """Precio suelto por ISIN, para quien no necesite saber cómo cotiza (ver fetch_isin_quote)."""
    quote = fetch_isin_quote(isin, usd_to_eur=usd_to_eur)
    return quote["price"] if quote else None


def fetch_bond_prices(bonds: List[Any], usd_to_eur: float | None = None) -> Dict[str, float]:
    """
    Calcula el precio de activos de Renta Fija (Bonos).

    - Si el activo tiene ISIN, se pide su cotización real a Börse Frankfurt
      (ver fetch_isin_quote). Es la vía que sí cubre deuda soberana individual
      como un bono del Estado español, y da precio dinámico de verdad: sube y
      baja con los tipos, no es una recta. A ese precio limpio se le suma el
      cupón corrido si se conoce la fecha de vencimiento, que es la que marca el
      pago del cupón (ver accrued_coupon_fraction y fetch_bond_reference_data).
    - Si el yahoo_symbol resuelve a una cotización de mercado real (precio > 5,
      típico de un ETF/fondo de renta fija cotizado — la deuda soberana individual
      no tiene tickers públicos gratuitos en Yahoo Finance), se usa ese precio tal
      cual: el valor es tan dinámico como lo sea ese instrumento. Al ser un precio
      de mercado real, ya incorpora en su cotización cualquier efecto del cupón, así
      que no se le suma devengo aparte.
    - Si no hay ticker, o Yahoo no lo reconoce, se valora a la par (1.0) más el
      interés simple devengado desde bond_start_date:
      1.0 + cupón_anual% * (días transcurridos / 365).
      Crece linealmente cada año que pasa (interés simple, no compuesto) reflejando
      lo que supondría ir cobrando el cupón, sin recalcularse desde el precio actual
      en cada llamada (lo que antes componía varias veces al día si el endpoint se
      invocaba con frecuencia) ni crecer sin límite.
    """
    from datetime import date as date_type

    prices: Dict[str, float] = {}
    for bond in bonds:
        asset_id = getattr(bond, "id", None) or (bond.get("id") if isinstance(bond, dict) else None)
        if not asset_id:
            continue
        symbol = getattr(bond, "yahoo_symbol", None) or (bond.get("yahoo_symbol") if isinstance(bond, dict) else None)
        isin = getattr(bond, "isin", None) or (bond.get("isin") if isinstance(bond, dict) else None)
        coupon = getattr(bond, "coupon_rate", None) or (bond.get("coupon_rate") if isinstance(bond, dict) else None)
        start_date = getattr(bond, "bond_start_date", None) or (bond.get("bond_start_date") if isinstance(bond, dict) else None)
        maturity = getattr(bond, "bond_maturity_date", None) or (bond.get("bond_maturity_date") if isinstance(bond, dict) else None)
        frequency = getattr(bond, "coupon_frequency", None) or (bond.get("coupon_frequency") if isinstance(bond, dict) else None)

        market_price = None
        accrued = 0.0
        if isin:
            quote = fetch_isin_quote(isin, usd_to_eur=usd_to_eur)
            if quote:
                market_price = quote["price"]
                # Solo los bonos cotizan limpio y en % del nominal; a un ETF de renta
                # fija no hay que sumarle nada, su cotización ya lo lleva dentro.
                if quote["quoted_in_percent"]:
                    accrued = accrued_coupon_fraction(coupon, maturity, frequency)
        if market_price is None and symbol:
            try:
                url = YAHOO_CHART_URL.format(symbol=symbol)
                res = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    chart_result = data.get("chart", {}).get("result", [])
                    if chart_result and "meta" in chart_result[0]:
                        raw_price = float(chart_result[0]["meta"].get("regularMarketPrice", 0.0))
                        currency = chart_result[0]["meta"].get("currency", "EUR")
                        if raw_price > 5.0:
                            if currency == "USD" and usd_to_eur:
                                raw_price *= usd_to_eur
                            market_price = raw_price
            except Exception as e:
                print(f"⚠️ Error fetching bond price from Yahoo for {asset_id} ({symbol}): {e}")

        if market_price is not None:
            prices[asset_id] = round(market_price + accrued, 6)
        elif coupon and coupon > 0:
            reference = start_date or date_type.today()
            days_elapsed = max(0, (date_type.today() - reference).days)
            accrued_fraction = (coupon / 100.0) * (days_elapsed / 365.0)
            prices[asset_id] = round(1.0 + accrued_fraction, 6)
        # Sin ticker de mercado real y sin cupón: no hay nada que actualizar aquí,
        # se deja el precio como está (no se incluye en el dict de precios nuevos).

    return prices


def generate_bond_history(coupon_rate: float = 3.7, base_price: float = 1.0, years: int = 5) -> List[Tuple[datetime, float]]:
    """
    Genera histórico sintético diario para un bono con tasa de cupón fija.
    """
    from datetime import timedelta
    end_date = datetime.now()
    total_days = years * 365
    start_date = end_date - timedelta(days=total_days)
    
    daily_rate = (coupon_rate / 100.0) / 365.0
    out: List[Tuple[datetime, float]] = []
    
    initial_price = base_price / ((1.0 + daily_rate) ** total_days)
    
    for day_i in range(total_days + 1):
        dt = start_date + timedelta(days=day_i)
        curr = initial_price * ((1.0 + daily_rate) ** day_i)
        out.append((dt, round(curr, 6)))
        
    return out


def fetch_coingecko_prices(ids: Dict[str, str]) -> Dict[str, float]:
    """
    ids: {asset_id: coingecko_id}
    Devuelve {asset_id: price_eur}
    """
    if not ids:
        return {}
    try:
        unique_ids = ",".join(sorted(set(ids.values())))
        res = requests.get(
            COINGECKO_SIMPLE_URL,
            params={"ids": unique_ids, "vs_currencies": "eur"},
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
        prices: Dict[str, float] = {}
        for asset_id, cg_id in ids.items():
            price = data.get(cg_id, {}).get("eur")
            if price is not None:
                prices[asset_id] = float(price)
        return prices
    except Exception:
        return {}


def fetch_cryptocompare_prices(symbols: Dict[str, str]) -> Dict[str, float]:
    """
    symbols: {asset_id: ticker} (e.g. {"btc_id": "BTC"})
    Devuelve {asset_id: price_eur}
    Usa la API de CryptoCompare (pricemulti).
    """
    if not symbols:
        return {}
        
    try:
        # CryptoCompare fsyms limit is ~300 chars, usually enough for 20-30 coins.
        # If we have many, we should batch. For now assume < 30 coins.
        unique_tickers = list(set(sym.upper() for sym in symbols.values()))
        ticker_str = ",".join(unique_tickers)
        
        url = "https://min-api.cryptocompare.com/data/pricemulti"
        params = {
            "fsyms": ticker_str,
            "tsyms": "EUR"
        }
        
        res = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        # CryptoCompare structure: {"BTC": {"EUR": 50000}, "ETH": {"EUR": 3000}}
        if data.get("Response") == "Error":
             print(f"⚠️ CryptoCompare API Error: {data.get('Message')}")
             return {}
             
        prices: Dict[str, float] = {}
        for asset_id, ticker in symbols.items():
            t_upper = ticker.upper()
            if t_upper in data:
                price = data[t_upper].get("EUR")
                if price is not None:
                    prices[asset_id] = float(price)
        
        return prices
    except Exception as e:
        print(f"⚠️ CryptoCompare Price Error: {e}")
        return {}


def _get_indexa_token() -> str:
    """Obtiene el token de Indexa desde variables de entorno."""
    token = os.getenv("INDEXA_TOKEN")
    if not token:
        # Fallback para desarrollo local o si no está configurado
        print("⚠️ INDEXA_TOKEN no encontrado en variables de entorno")
        return ""
    return token.strip()


def _get_coincap_token() -> str | None:
    """Obtiene el token de CoinCap desde variables de entorno."""
    return os.getenv("COINCAP_TOKEN")


def _get_indexa_session() -> requests.Session:
    """Crea una sesión con estrategia de reintentos para Indexa."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _make_indexa_request(endpoint: str, session: requests.Session) -> dict:
    """Realiza una petición autenticada a la API de Indexa."""
    token = _get_indexa_token()
    # Indexa autentica con la cabecera X-AUTH-TOKEN (comprobado: devuelve 200,
    # mientras que Authorization: Bearer devuelve 401). Ojo: sus respuestas 401
    # incluyen 'WWW-Authenticate: Bearer', pero es un valor por defecto genérico
    # de su framework, no el esquema que aceptan.
    headers = {"X-AUTH-TOKEN": token}
    url = f"{INDEXA_BASE_URL}{endpoint}"
    
    response = session.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def fetch_indexa_accounts() -> dict | None:
    """
    Obtiene información de todas las cuentas de Indexa Capital directamente.
    Emula la respuesta del anterior proxy para mantener compatibilidad.
    """
    try:
        session = _get_indexa_session()
        
        # 1. Obtener info del usuario y sus cuentas
        user_data = _make_indexa_request("/users/me", session)
        accounts = user_data.get("accounts", [])
        
        result = []
        total_value = 0.0
        
        for account in accounts:
            acct_num = account.get("account_number")
            acct_name = account.get("main_holder_name", "Indexa")
            risk_profile = account.get("risk", 0)
            
            # 2. Obtener el portfolio actual de cada cuenta
            try:
                portfolio_response = _make_indexa_request(f"/accounts/{acct_num}/portfolio", session)
                portfolio = portfolio_response.get("portfolio", {})
                market_value = portfolio.get("total_amount", 0.0)
                instruments_cost = portfolio.get("instruments_cost", 0.0)
            except Exception:
                market_value = 0.0
                instruments_cost = 0.0
            
            # Logica original: valores brutos
            # weight = INDEXA_WEIGHTS.get(acct_num, 1.0) # Removed global weighting
            
            # if weight != 1.0: ...
                
            # Si el peso es 0, podemos querer omitirla o incluirla a 0.
            # El dashboard original la incluía con valor 0.
            
            total_value += market_value
            
            result.append({
                "account_number": acct_num,
                "name": f"{acct_name} ({risk_profile}/10)",
                "risk_profile": risk_profile,
                "market_value": market_value,
                "instruments_cost": instruments_cost,
                "variation_pct": ((market_value / instruments_cost) - 1) * 100 if instruments_cost > 0 else 0
            })
        
        return {
            "success": True,
            "total_value": total_value,
            "accounts": result
        }

    except Exception as e:
        print(f"⚠️ Error en fetch_indexa_accounts: {e}")
        return {"success": False, "error": str(e)}


def fetch_indexa_history(years: int = 3) -> dict | None:
    """
    Obtiene histórico de rendimiento de todas las cuentas de Indexa Capital.
    Usa el endpoint /performance que devuelve portfolio con total_amount diario.
    """
    from datetime import datetime, timedelta
    
    try:
        session = _get_indexa_session()
        
        # 1. Obtener info del usuario y sus cuentas
        user_data = _make_indexa_request("/users/me", session)
        accounts = user_data.get("accounts", [])
        
        result = {}
        
        for account in accounts:
            acct_num = account.get("account_number")
            acct_name = account.get("main_holder_name", "Indexa")
            risk_profile = account.get("risk", 0)
            
            # 2. Obtener histórico de rendimiento
            try:
                perf_response = _make_indexa_request(f"/accounts/{acct_num}/performance", session)
                portfolio_data = perf_response.get("portfolios", [])  # Note: 'portfolios' plural
                
                if not portfolio_data:
                    print(f"⚠️ No portfolio data for {acct_num}")
                    continue
                
                # Extraer total_amount de cada día
                history_points: List[Tuple[datetime, float]] = []
                current_value = 0.0
                
                for point in portfolio_data:
                    date_str = point.get("date")
                    total_amount = point.get("total_amount", 0)
                    
                    if date_str and total_amount > 0:
                        try:
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                            
                            # Logica original: valores brutos
                            weighted_amount = float(total_amount)
                            
                            history_points.append((dt, weighted_amount))
                            current_value = weighted_amount # Ultimo valor
                        except (ValueError, TypeError):
                            continue
                
                # Ordenar por fecha ascendente
                history_points.sort(key=lambda x: x[0])
                
                if history_points:
                    asset_id = f"idx_{acct_num}"
                    result[asset_id] = {
                        "name": f"{acct_name} ({risk_profile}/10)",
                        "history": history_points,
                        "current_value": current_value
                    }
                    
                    print(f"✅ Indexa history for {acct_num}: {len(history_points)} points, current: {current_value:.2f}€")
                
            except Exception as e:
                print(f"⚠️ Error getting performance for {acct_num}: {e}")
                continue
        
        return {
            "success": True,
            "accounts": result
        }
    
    except Exception as e:
        print(f"⚠️ Error en fetch_indexa_history: {e}")
        return {"success": False, "error": str(e)}


def fetch_history_yahoo(symbol: str, years: int = 5) -> List[Tuple[datetime, float]]:
    """
    Devuelve histórico diario (fecha, precio) para un símbolo de Yahoo.
    Usa range=Xy para simplificar.
    Incluye reintentos con backoff exponencial para manejar rate limiting.
    Los precios se devuelven en EUR (convierte desde USD si es necesario).
    """
    import time
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={years}y"
    max_retries = 3
    base_delay = 2  # segundos
    
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
            
            # Si es rate limited, esperar y reintentar
            if res.status_code == 429:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ Yahoo rate limited for {symbol}, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            res.raise_for_status()
            data = res.json()
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            closes = result["indicators"]["quote"][0]["close"]
            
            # Verificar la divisa y obtener tasa de conversión si es necesario
            currency = result.get("meta", {}).get("currency", "EUR")
            usd_to_eur = None
            if currency == "USD":
                usd_to_eur = fetch_usd_eur_rate() or 0.92  # Fallback rate
                print(f"📊 {symbol} is in USD, converting with rate {usd_to_eur}")
            
            out: List[Tuple[datetime, float]] = []
            for ts, close in zip(timestamps, closes):
                if close is None:
                    continue
                dt = datetime.utcfromtimestamp(ts)
                price = float(close)
                # Convertir a EUR si el precio está en USD
                if usd_to_eur:
                    price *= usd_to_eur
                out.append((dt, price))
            return out
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ Yahoo rate limited for {symbol}, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            print(f"❌ Yahoo history error for {symbol}: {e}")
            return []
        except Exception as e:
            print(f"❌ Yahoo history error for {symbol}: {e}")
            return []
    
    return []


def fetch_history_coingecko(coin_id: str, years: int = 5) -> List[Tuple[datetime, float]]:
    """
    Devuelve histórico diario (fecha, precio) para un id de CoinGecko.
    Usa el endpoint market_chart con days=365*years.
    Incluye reintentos con backoff exponencial para manejar rate limiting.
    """
    import time
    
    days = 365 * years
    max_retries = 3
    base_delay = 2  # segundos
    
    for attempt in range(max_retries):
        try:
            res = requests.get(
                COINGECKO_MARKET_CHART_URL.format(id=coin_id),
                headers=DEFAULT_HEADERS,
                params={"vs_currency": "eur", "days": days},
                timeout=30,
            )
            
            # Si es rate limited, esperar y reintentar
            if res.status_code == 429:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ Rate limited for {coin_id}, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            res.raise_for_status()
            data = res.json()
            prices = data.get("prices", [])
            out: List[Tuple[datetime, float]] = []
            for ts_ms, price in prices:
                dt = datetime.utcfromtimestamp(ts_ms / 1000.0)
                out.append((dt, float(price)))
            return out
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ Rate limited for {coin_id}, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            print(f"❌ CoinGecko history error for {coin_id}: {e}")
            return []
        except Exception as e:
            print(f"❌ CoinGecko history error for {coin_id}: {e}")
            return []
    
    return []


def fetch_history_coincap(coin_id: str, years: int = 5) -> List[Tuple[datetime, float]]:
    """
    Devuelve histórico diario (fecha, precio) para un id de CoinCap.
    Usa el endpoint /assets/{id}/history con interval=d1 para datos diarios.
    CoinCap ofrece hasta 11 años de datos históricos.
    
    Los precios se devuelven en USD y se convierten a EUR usando el tipo de cambio actual.
    """
    import time
    
    token = _get_coincap_token()
    if not token:
        print(f"⚠️ CoinCap token no configurado. Ejecuta setup_coincap_token.py")
        return []
    
    # Calcular fecha límite para filtrar resultados
    end = datetime.now()
    start_limit = datetime(end.year - years, end.month, end.day)
    
    url = COINCAP_HISTORY_URL.format(id=coin_id)
    # CoinCap API no acepta bien los parámetros start/end, así que pedimos todo
    params = {
        "interval": "d1"  # Daily data - returns all available history
    }
    headers = {
        **DEFAULT_HEADERS,
        "Authorization": f"Bearer {token}"
    }
    
    max_retries = 3
    base_delay = 2
    
    # Obtener tipo de cambio USD/EUR
    usd_to_eur = fetch_usd_eur_rate() or 0.92  # Fallback rate
    
    for attempt in range(max_retries):
        try:
            res = requests.get(url, params=params, headers=headers, timeout=30)
            
            if res.status_code == 401:
                print(f"❌ CoinCap unauthorized for {coin_id}. Check your API key.")
                return []
            
            if res.status_code == 429:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ CoinCap rate limited for {coin_id}, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            res.raise_for_status()
            data = res.json()
            history_data = data.get("data", [])
            
            out: List[Tuple[datetime, float]] = []
            for point in history_data:
                # CoinCap returns timestamp in milliseconds
                ts_ms = point.get("time")
                price_usd = point.get("priceUsd")
                
                if ts_ms is not None and price_usd is not None:
                    dt = datetime.utcfromtimestamp(ts_ms / 1000.0)
                    # Filtrar por rango de fechas
                    if dt >= start_limit:
                        price_eur = float(price_usd) * usd_to_eur
                        out.append((dt, price_eur))
            
            print(f"✅ CoinCap history for {coin_id}: {len(out)} points")
            return out
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ CoinCap rate limited for {coin_id}, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            print(f"❌ CoinCap history error for {coin_id}: {e}")
            return []
        except Exception as e:
            print(f"❌ CoinCap history error for {coin_id}: {e}")
            return []
    
    return []


def fetch_history_cryptocompare(symbol: str, years: int = 5) -> List[Tuple[datetime, float]]:
    """
    Devuelve histórico diario (fecha, precio) para un símbolo usando CryptoCompare.
    
    Ventajas:
    - No requiere API key para uso básico
    - Devuelve hasta 2000 puntos diarios (~5.5 años)
    - Datos directamente en EUR (sin conversión necesaria)
    
    Args:
        symbol: Símbolo del crypto (ej: "BTC", "ETH", "SOL")
        years: Años de histórico a obtener (máx ~5.5 años con limit=2000)
    """
    import time
    
    # Calcular límite de puntos basado en años (365 días por año)
    limit = min(years * 365, 2000)  # CryptoCompare max es 2000
    
    params = {
        "fsym": symbol.upper(),
        "tsym": "EUR",
        "limit": limit
    }
    
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            res = requests.get(
                CRYPTOCOMPARE_HISTODAY_URL,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=30
            )
            
            if res.status_code == 429:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ CryptoCompare rate limited for {symbol}, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            res.raise_for_status()
            data = res.json()
            
            if data.get("Response") != "Success":
                print(f"⚠️ CryptoCompare error for {symbol}: {data.get('Message', 'Unknown error')}")
                return []
            
            history_data = data.get("Data", {}).get("Data", [])
            
            out: List[Tuple[datetime, float]] = []
            for point in history_data:
                ts = point.get("time")
                close_price = point.get("close")
                
                if ts is not None and close_price is not None and close_price > 0:
                    dt = datetime.utcfromtimestamp(ts)
                    out.append((dt, float(close_price)))
            
            print(f"✅ CryptoCompare history for {symbol}: {len(out)} points")
            return out
            
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response.status_code == 429 and attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ CryptoCompare rate limited for {symbol}, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            print(f"❌ CryptoCompare history error for {symbol}: {e}")
            return []
        except Exception as e:
            print(f"❌ CryptoCompare history error for {symbol}: {e}")
            return []
    
    return []



