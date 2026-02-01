from fastapi.testclient import TestClient
import sys
import os

# Ensure api module is found
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from index import app

client = TestClient(app)

def test_sanity():
    response = client.get("/api/sanity")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "version" in data
    print(f"Sanity Check Passed: Version {data['version']}")
