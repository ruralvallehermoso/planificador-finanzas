import yfinance as yf

tickers = ["0P0001CLDK.F", "EGLN.L"]

print("Checking currency metadata...")
for t in tickers:
    try:
        data = yf.Ticker(t)
        # Fast way to get currency is history metadata or info (slow)
        hist = data.history(period="1d")
        # yfinance often puts currency in metadata
        # Or try data.info (might be slow/rate limited)
        meta = data.history_metadata
        curr = meta.get("currency") if meta else "Unknown"
        print(f"✅ {t}: Currency = {curr}")
        # Also print raw price
        if not hist.empty:
            print(f"   Price: {hist['Close'].iloc[0]}")
    except Exception as e:
        print(f"❌ {t}: {e}")
