import requests
import json

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/BTBT?interval=1d&range=5d"
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json"
}

res = requests.get(YAHOO_CHART_URL, headers=YAHOO_HEADERS)
data = res.json()
print(json.dumps(data, indent=2))
