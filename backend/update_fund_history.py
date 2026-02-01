import os
import sys
import yfinance as yf
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import crud
import schemas

# Map Asset ID -> Ticker
ASSETS = {
    "myinv": "0P0001CLDK.F",
    "gold": "EGLN.L",
    "goog": "GOOG",
    "spot": "SPOT",
    "el": "EL.PA",
    "btbt": "BTBT",
    "btc": "BTC-EUR", # yfinance ticker for BTC in EUR? often BTC-EUR
    "eth": "ETH-EUR",
    "sol": "SOL-EUR"
}

# Add crypto mapping for yfinance if needed, or rely on crud?
# crud uses CoinCap/CoinGecko. 
# This script specifically targets the FUNDS (MyInv, Gold) which rely on Yahoo.

FUNDS = {
    "myinv": "0P0001CLDK.F",
    "gold": "EGLN.L"
}

def update_history():
    db = SessionLocal()
    try:
        print("Starting history update for funds...")
        for asset_id, ticker in FUNDS.items():
            print(f"Fetching history for {asset_id} ({ticker})...")
            try:
                # Fetch max history
                # Interval 1d
                dat = yf.download(ticker, period="2y", interval="1d", progress=False)
                
                if dat.empty:
                    print(f"⚠️ No data for {ticker}")
                    continue
                
                # Convert to format required by crud.save_historical_points
                # {asset_id: {date: price}}
                points = {}
                history_list = [] # For saving directly via crud or custom
                
                # yfinance dataframe index is datetime
                for dt, row in dat.iterrows():
                    # Handle MultiIndex check if needed
                    price = row['Close']
                    if hasattr(price, "iloc"):
                        price = price.iloc[0]
                    
                    price_val = float(price)
                    date_obj = dt.date()
                    points[date_obj] = price_val
                
                if points:
                    print(f"✅ Saving {len(points)} points for {asset_id}")
                    crud.save_historical_points(db, {asset_id: points})
                else:
                     print(f"⚠️ No points parsed for {asset_id}")

            except Exception as e:
                print(f"❌ Error {asset_id}: {e}")
        
    finally:
        db.close()

if __name__ == "__main__":
    update_history()
