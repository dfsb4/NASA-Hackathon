from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import List, Literal
from pydantic import BaseModel, Field
import os

from utils.plot import plot_all

app = FastAPI(title="My Monorepo API", version="0.1.0")

allow_origins = os.getenv("ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BACKEND_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BACKEND_DIR)), name="static")

@app.get("/api/health")
def health():
    return {"DFSB4-NASA-Hackathon": True}

class EchoIn(BaseModel):
    message: str

@app.post("/api/echo")
def echo(body: EchoIn):
    return {"echo": body.message}


class PlotIn(BaseModel):
    month: Literal["01","02","03","04","05","06","07","08","09","10","11","12"]
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

@app.post("/api/plot")
def plot(body: PlotIn):
    out_paths = plot_all(body.month, body.lat, body.lon)
    urls = [f"/static{p.replace('\\', '/')}" for p in out_paths]
    return JSONResponse({"month": body.month, "lat": body.lat, "lon": body.lon, "images": urls})

# local test: uvicorn main:app --host 0.0.0.0 --port 8000