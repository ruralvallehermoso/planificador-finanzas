import sys
import os
from datetime import date
from sqlalchemy.orm import Session
from database import SessionLocal
import keyring
import market_client
import crud
import models

# --- Auth Setup ---
SERVICE_NAME = "DashboardFinanciero"
USERNAME = "indexa_api"

print("🔑 Fetching token from Keyring...")
token = keyring.get_password(SERVICE_NAME, USERNAME)
if token:
    print("✅ Token found.")
    os.environ["INDEXA_TOKEN"] = token
else:
    print("❌ Token not found in Keyring. Please run setup_indexa_token.py")
    sys.exit(1)
# ------------------

def fix_indexa_history():
    print("🚀 Starting Indexa History Fix...")
    db = SessionLocal()
    try:
        # 1. Fetch weighted history from API
        print("📡 Fetching weighted history from Indexa API...")
        history_data = market_client.fetch_indexa_history()
        
        if not history_data or not history_data.get("success"):
            print("❌ Failed to fetch history")
            return

        accounts = history_data.get("accounts", {})
        
        # 2. Aggregate history day by day
        aggregated_history = {} # date -> total_value
        
        for acct_id, data in accounts.items():
            points = data.get("history", [])
            print(f"📄 Processing {acct_id}: {len(points)} points")
            for dt, val in points:
                d = dt.date()  # Convert to date
                aggregated_history[d] = aggregated_history.get(d, 0.0) + val
                
        print(f"✅ Aggregated {len(aggregated_history)} daily points.")
        
        # 3. Update idx_1 history
        idx_1_history = {
            "idx_1": aggregated_history
        }
        
        print("💾 Saving to database for idx_1...")
        crud.save_historical_points(db, idx_1_history)
        print("✅ Saved.")
        
        # 4. Verify start date value (2025-11-24)
        check_date = date(2025, 11, 24)
        val = aggregated_history.get(check_date)
        print(f"🧐 Value on {check_date}: {val:.2f}€")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_indexa_history()
