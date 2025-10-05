from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import List, Literal
from pydantic import BaseModel, Field
from datetime import datetime as dt
import os
import io

from utils.plot import plot_all
from month.precipitation import pred_precipitation
from month.temperature import pred
from month.air import pred_air_quality
from utils.generate_csv import generate_monthly_csv

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
    urls = [f"/static{Path(p).as_posix()}" for p in out_paths]
    return JSONResponse({"month": body.month, "lat": body.lat, "lon": body.lon, "images": urls})


@app.get("/api/weather")
def get_weather(
    request: Request,
    latitude: float,
    longitude: float,
    datetime: str,
):
    data = {
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "datetime": datetime,
        "units": "metric",
        "data": {
            "temperature": {
                "value": 28.4,
                "unit": "°C"
            },
            "precipitation": {
                "value": 0.3,
                "unit": "mm/h"
            },
            "humidity": {
                "value": 68,
                "unit": "%"
            },
            "windspeed": {
                "value": 2.7,
                "unit": "m/s"
            },
            "air_quality": {
                "value": "50 (pm2.5)",
                "unit": "μg/m³"
            },
            "extreme_weather": {
                "typhoon_probability": 0.02,
                "heatwave_probability": 0.1,
                "cold_wave_probability": 0.0,
                "heavy_rain_probability": 0.08,
                "strong_wind_probability": 0.05,
                "thunderstorm_probability": 0.12
            },
            "comfort_index": {
                "very_hot": 0.25,
                "very_cold": 0.00,
                "very_windy": 0.05,
                "very_wet": 0.10,
                "very_uncomfortable": 0.15
            },
            "climate_description": "Warm and humid morning with light southern wind. Low chance of extreme weather. Slightly uncomfortable due to humidity."
        }
    }

    return JSONResponse(data)


@app.get("/api/weather/month")
def get_monthly_weather(
    request: Request,
    latitude: float,
    longitude: float,
    datetime: str,
):
    try:
        iso = datetime.replace("Z", "+00:00")
        t = dt.fromisoformat(iso)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime. Use ISO 8601, e.g. 2025-10-04T08:00:00Z")
    month = f"{t.month:02d}"
    description = []
    temperature, humidity, windspeed, level = pred(latitude, longitude)
    precipitation, rain_level = pred_precipitation(latitude, longitude)
    air_quality, air_level = pred_air_quality(latitude, longitude)
    description.append(level)
    description.append(rain_level)
    description.append(air_level)

    url_map = {
        "temperature":   "/static/result/temperature/forecast_series.png",
        "precipitation": "/static/result/precipitation/forecast_series.png",
        "humidity":      "/static/result/humidity/forecast_series.png",
        "windspeed":     "/static/result/windspeed/forecast_series.png",
        "air_quality":   "/static/result/air_quality/forecast_series.png",
    }

    payload = {
        "location": {"latitude": latitude, "longitude": longitude},
        "datetime": datetime,
        "data": {
            "temperature":   {"value": round(temperature, 1), "unit": "°C"},
            "precipitation": {"value": round(precipitation, 2), "unit": "mm/h"},
            "humidity":      {"value": int(humidity), "unit": "%"},
            "windspeed":     {"value": round(windspeed, 1), "unit": "m/s"},
            "air_quality":   {"value": int(air_quality), "unit": "μg/m³"},
            "url": url_map,
            "climate_description": (
                description[0] + " " + description[1] + " " + description[2]
            ),
        },
    }
    return JSONResponse(payload)

@app.get("/api/history.csv")
def get_history_csv(
    request: Request,
    latitude: float,
    longitude: float,
):
    df = generate_monthly_csv(latitude, longitude)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data found for the given parameters.")
   
    csv_io = io.StringIO()
    df.to_csv(csv_io, index=False)
    csv_io.seek(0)

    filename = f"history_{latitude:.2f}_{longitude:.2f}.csv"
    return StreamingResponse(
        csv_io,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
# local test: uvicorn main:app --host 0.0.0.0 --port 8000