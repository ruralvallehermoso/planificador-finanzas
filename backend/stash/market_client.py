from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
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



