from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import List, Literal,Dict
from pydantic import BaseModel, Field
from datetime import datetime as dt, timedelta
import os
import io
import numpy as np
import json

from utils.plot import plot_all
from month.precipitation import pred_precipitation
from month.temperature import pred
from month.air import pred_air_quality
from day.daily import run_climate_forecast
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


def _to_ymd(s: str) -> str:
    """接受 'YYYY-MM-DD' 或 ISO8601（含 'T'），回傳 'YYYY-MM-DD'。"""
    if not isinstance(s, str) or len(s) < 10:
        raise HTTPException(status_code=400, detail="startdate/enddate must be 'YYYY-MM-DD' or ISO8601 string")
    return s[:10]

def _parse_date(s: str) -> dt:
    try:
        return dt.strptime(_to_ymd(s), "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {s}. Expect 'YYYY-MM-DD' or ISO8601.")

def _nn(x):
    """NaN -> None，其他轉 float。"""
    try:
        x = float(x)
        return None if np.isnan(x) else round(x, 2)
    except Exception:
        return None
    
@app.get("/api/weather")
def get_weather(
    request: Request,
    latitude: float,
    longitude: float,
    datetime: str,  
):
    s = _to_ymd(datetime)
    sd = _parse_date(s)

    ed = sd + timedelta(days=3)
    e = ed.strftime("%Y-%m-%d")
    try:
        result_json = run_climate_forecast(latitude, longitude, s, e)
        result = json.loads(result_json)
    except SystemExit as ex:
        raise HTTPException(status_code=422, detail=f"No data available: {ex}")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {ex}")

    # 3) 組裝回傳
    summary = result.get("summary", {}) or {}
    summary_avg = summary.get("average_conditions", {}) or {}
    probs = summary.get("extreme_event_probabilities", {}) or {}
    first_day = (result.get("daily_reports") or [{}])[0]

    data_block = {
        "temperature":   {"value": _nn(summary_avg.get("temp")),   "unit": "°C"},
        "precipitation": {"value": _nn(summary_avg.get("rain")),   "unit": "mm/day"},
        "humidity":      {"value": _nn(summary_avg.get("humidity")),"unit": "g/kg"},
        "windspeed":     {"value": _nn(summary_avg.get("wind")),   "unit": "m/s"},
        "air_quality":   {"value": _nn(summary_avg.get("pm25")),   "unit": "μg/m³"},
        "extreme_weather": {
            # 從 % 轉成 0~1 機率
            "typhoon_probability":      round(float(probs.get("typhoon_probability", 0))/100.0, 3),
            "heatwave_probability":     round(float(probs.get("heatwave_probability", 0))/100.0, 3),
            "cold_wave_probability":    round(float(probs.get("cold_wave_probability", 0))/100.0, 3),
            "heavy_rain_probability":   round(float(probs.get("heavy_rain_probability", 0))/100.0, 3),
            "strong_wind_probability":  round(float(probs.get("strong_wind_probability", 0))/100.0, 3),
            "thunderstorm_probability": round(float(probs.get("thunderstorm_probability", 0))/100.0, 3),
        },
        "comfort_index": first_day.get("comfort_index"),
        "climate_description": first_day.get("climate_description"),
    }

    payload = {
        "location": {"latitude": latitude, "longitude": longitude},
        "datetime": s,  
        "data": data_block,
    }
    return JSONResponse(payload)


@app.get("/api/weather/month")
def get_monthly_weather(
    request: Request,
    latitude: float,
    longitude: float,
    starttime: str,
    endtime: str,
):
    try:
        iso = starttime.replace("Z", "+00:00")
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
        "starttime": starttime,
        "endtime": endtime,
        "data": {
            "temperature":   {"value": round(temperature, 1), "unit": "°C"},
            "precipitation": {"value": round(precipitation, 2), "unit": "mm/h"},
            "humidity":      {"value": int(humidity), "unit": "%"},
            "windspeed":     {"value": round(windspeed, 1), "unit": "m/s"},
            "air_quality":   {"value": int(air_quality), "unit": "μg/m³"},
            "images": {k: v for k, v in url_map.items()},
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