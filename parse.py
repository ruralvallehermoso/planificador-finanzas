import urllib.request, json
req = urllib.request.Request("https://backend-rho-two-p1x4gg922k.vercel.app/api/assets", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())
    for a in data:
        if a.get("id", "").startswith("idx_"):
            print(f"{a.get('id')}: {a.get('change_24h_pct')}%")
