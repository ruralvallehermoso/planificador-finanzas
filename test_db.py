from temp_backend_auth.database import SessionLocal
import temp_backend_auth.crud as crud
from temp_backend_auth.models import Asset, HistoricalPrice
import temp_backend_auth.market_client as market_client

db = SessionLocal()
assets = db.query(Asset).filter(Asset.id.like('idx_%')).all()
for a in assets:
    print(f"Asset: {a.id}, Price: {a.price_eur}")
    hists = db.query(HistoricalPrice).filter(HistoricalPrice.asset_id == a.id).order_by(HistoricalPrice.date.desc()).limit(5).all()
    for h in hists:
        print(f"  - {h.date}: {h.price_eur}")
    
    # Also check what fetch_indexa_history says
    print("-----")

# Test how fetch_indexa_history performs
# data = market_client.fetch_indexa_history(years=1)
# print(data)
