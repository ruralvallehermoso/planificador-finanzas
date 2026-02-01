from fastapi import FastAPI
import sys

app = FastAPI()

@app.get("/api/sanity")
def sanity():
    return {"status": "alive", "version": "v3-EXPLICIT-BUILD", "python": sys.version}

@app.get("/api/{full_path:path}")
def catch_all(full_path: str):
    return {"message": "Caught by Zero Config", "path": full_path}
