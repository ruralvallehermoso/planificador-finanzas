from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_sim():
    payload = {
        "mortgage": {
            "principal": 127000,
            "annual_rate": 2.5,
            "years": 15
        },
        "tax_rate": 19,
        "start_date": "2025-11-24"
    }
    
    try:
        response = client.post("/api/simulator/compare", json=payload)
        data = response.json()
        
        print(f"Status: {response.status_code}")
        if "backend_debug" in data:
            print("SUCCESS: 'backend_debug' found.")
            print(json.dumps(data["backend_debug"], indent=2))
        else:
            print("FAILURE: 'backend_debug' MISSING in response.")
            print("Keys found:", list(data.keys()))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sim()
