
import requests
import json
from datetime import date

URL = "http://localhost:8000/api/simulator/compare"

payload = {
  "start_date": "2025-11-24",
  "tax_rate": 19,
  "mortgage": {
    "principal": 128000,
    "annual_rate": 2.25,
    "years": 24
  }
}

try:
    res = requests.post(URL, json=payload, timeout=10)
    data = res.json()
    
    breakdown = data.get("asset_breakdown", [])
    for item in breakdown:
        if "Gold" in item["name"] or "Oro" in item["name"]:
            print(f"Asset: {item['name']}")
            print(f"Current Value: {item['current_value']}")
            print(f"Initial Value: {item['initial_value']}")
            
except Exception as e:
    print(f"Error: {e}")
