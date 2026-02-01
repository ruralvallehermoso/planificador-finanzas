
import requests
import json

# URL = "http://localhost:8000/api/simulator/compare"
URL = "https://backend-rho-two-p1x4gg922k.vercel.app/api/simulator/compare"

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
    print(f"Checking {URL}...")
    res = requests.post(URL, json=payload, timeout=15)
    print(f"Status Code: {res.status_code}")
    
    data = res.json()
    
    breakdown = data.get("asset_breakdown", [])
    found = False
    for item in breakdown:
        if "Gold" in item["name"] or "Oro" in item["name"]:
            found = True
            print(f"Asset: {item['name']}")
            print(f"Current Value: {item['current_value']}")
            print(f"Initial Value: {item['initial_value']}")
    
    if not found:
        print("Gold asset not found in response!")

except Exception as e:
    print(f"Error: {e}")
