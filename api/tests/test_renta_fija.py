from fastapi.testclient import TestClient
import sys
import os

# Ensure api module is found
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from index import app
import market_client

def test_renta_fija_asset_present_and_crud():
    with TestClient(app) as client:
        # 1. Test GET assets contains seeded Bono del Estado Español
        response = client.get("/api/assets")
        assert response.status_code == 200
        assets = response.json()
        
        bono = next((a for a in assets if a["id"] == "bono_es_10y"), None)
        assert bono is not None, "Bono del Estado Español 10A must be present in assets"
        assert bono["category"] == "Renta Fija"
        assert bono["quantity"] == 30000
        assert bono["coupon_rate"] == 3.7
        assert bono["ticker"] == "ES10Y"

        # 2. Test Filter by Renta Fija category
        rf_response = client.get("/api/assets?category=Renta Fija")
        assert rf_response.status_code == 200
        rf_assets = rf_response.json()
        assert any(a["id"] == "bono_es_10y" for a in rf_assets)
        assert all(a["category"] == "Renta Fija" for a in rf_assets)

        # 3. Test POST new asset
        new_bond_payload = {
            "id": "bono_test_5y",
            "name": "Bonos Estado Español 5A Test",
            "ticker": "ES5Y",
            "category": "Renta Fija",
            "platform": "Tesoro",
            "quantity": 10000,
            "price_eur": 1.0,
            "coupon_rate": 3.1,
            "yahoo_symbol": "5YESP.BD",
            "manual": False
        }
        create_res = client.post("/api/assets", json=new_bond_payload)
        assert create_res.status_code == 200
        created = create_res.json()
        assert created["id"] == "bono_test_5y"
        assert created["coupon_rate"] == 3.1

        # 4. Test PUT update asset
        update_res = client.put("/api/assets/bono_test_5y", json={"quantity": 15000, "price_eur": 1.02})
        assert update_res.status_code == 200
        updated = update_res.json()
        assert updated["quantity"] == 15000
        assert updated["price_eur"] == 1.02

        # 5. Test GET detail
        detail_res = client.get("/api/assets/bono_test_5y")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["name"] == "Bonos Estado Español 5A Test"

        # 6. Test DELETE asset
        del_res = client.delete("/api/assets/bono_test_5y")
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # Verify deleted
        verify_del = client.get("/api/assets/bono_test_5y")
        assert verify_del.status_code == 404


def test_bond_price_and_yield_calculation():
    # Test market_client bond price calculation
    sample_bonds = [
        {
            "id": "bono_es_10y",
            "yahoo_symbol": "10YESP.BD",
            "coupon_rate": 3.7,
            "price_eur": 1.0
        }
    ]
    prices = market_client.fetch_bond_prices(sample_bonds)
    assert "bono_es_10y" in prices
    assert prices["bono_es_10y"] > 0
    print(f"Calculated bond price: {prices['bono_es_10y']}")

    # Test synthetic history generation
    history = market_client.generate_bond_history(coupon_rate=3.7, base_price=1.0, years=1)
    assert len(history) >= 365
    assert history[0][1] < history[-1][1]  # Price grows over time according to coupon rate
    print(f"Generated {len(history)} historical bond points")
