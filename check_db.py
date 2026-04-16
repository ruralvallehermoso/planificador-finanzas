import requests
import json

r = requests.post("https://backend-rho-two-p1x4gg922k.vercel.app/api/debug/sync_indexa_history")
print(r.text)
