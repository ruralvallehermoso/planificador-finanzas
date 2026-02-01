import yfinance as yf

tickers = ["0P0001CLDK.F", "EGLN.L"]
data = yf.download(tickers, start="2025-11-20", end="2025-11-28")
print(data['Close'])
