from fastapi import FastAPI
import sys

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Minimal Backend v1", "python": sys.version}

@app.get("/api/sanity")
def sanity():
    return {"status": "alive"}
