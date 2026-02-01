import yfinance as yf
from datetime import datetime

tickers = {
    "0P0001CLDK.F": "Fondo MyInvestor",
    "EGLN.L": "Oro / Gold"
}

start_date = "2025-11-24"
end_date = "2025-11-26" # +1/2 days to ensure we catch the close

print(f"Fetching prices for {start_date}...")

for symbol, name in tickers.items():
    try:
        data = yf.download(symbol, start=start_date, end=end_date, interval="1d", progress=False)
        if not data.empty:
            # Get the price on 2025-11-24 (or nearest)
            # Row index 0 is start_date
            price = data["Close"].iloc[0] if not data["Close"].empty else None
            if price is not None:
                # yfinance returns pandas Series/DataFrame. Convert to float.
                val = float(price.iloc[0]) if hasattr(price, "iloc") else float(price)
                print(f"✅ {name} ({symbol}): {val}")
            else:
                print(f"⚠️ {name} ({symbol}): No Close data")
        else:
             print(f"⚠️ {name} ({symbol}): No data found")
    except Exception as e:
        print(f"❌ Error {symbol}: {e}")
