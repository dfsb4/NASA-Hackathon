# -*- coding: utf-8 -*-
import os
import re
import netCDF4 as nc
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor

# ==============================
# 路徑設定（請依你實際資料夾調整）
# ==============================
BASE_DIR = "./data/"
DIRS_MONTHLY = {
    "rain": os.path.join(BASE_DIR, "precipitation"),  # IMERG month
    "slv":  os.path.join(BASE_DIR, "temperature"),          # MERRA-2 month (T2M, PS, QV2M, U10M, V10M)
    "aer":  os.path.join(BASE_DIR, "air_quality"),                               # MERRA-2 month aerosol
}
DIRS_DAILY_2024 = {
    "rain": os.path.join(BASE_DIR, "rain_daily"),   # IMERG day
    "slv":  os.path.join(BASE_DIR, "temp_daily"),   # MERRA-2 day slv
    "aer":  os.path.join(BASE_DIR, "aer_daily"),    # MERRA-2 day aer (可無)
}

# ==============================
# 使用者輸入
# ==============================
# TARGET_LAT = float(input("Enter latitude (e.g., 25.0): ") or 25.0)
# TARGET_LON = float(input("Enter longitude (e.g., 121.5): ") or 121.5)
# START_DATE = input("Start date (YYYY-MM-DD): ").strip()
# END_DATE   = input("End   date (YYYY-MM-DD): ").strip()
# START_DT = datetime.strptime(START_DATE, "%Y-%m-%d")
# END_DT   = datetime.strptime(END_DATE,   "%Y-%m-%d")
# if END_DT < START_DT:
#     raise ValueError("End date must be >= Start date")

# ==============================
# 工具函數
# ==============================
def extract_yyyymm(fname):
    m = re.search(r"(19|20)\d{4,6}", fname)
    if not m:
        return None
    yyyymm = m.group()[:6]
    try:
        return datetime.strptime(yyyymm, "%Y%m")
    except:
        return None

def extract_yyyymmdd(fname):
    m = re.search(r"(19|20)\d{6,8}", fname)
    if not m:
        return None
    yyyymmdd = m.group()[:8]
    try:
        return datetime.strptime(yyyymmdd, "%Y%m%d")
    except:
        return None

def iter_month_dirs_with_year(root_dir, year_min=2022, year_max=2024):
    """
    依序回傳 ./<root>/<year>/<month> 這些存在的資料夾路徑
    只吃 year_min ~ year_max 範圍內的四位數年份
    """
    if not os.path.isdir(root_dir):
        return
    for name in sorted(os.listdir(root_dir)):
        if not re.fullmatch(r"\d{4}", name):
            continue
        y = int(name)
        if not (year_min <= y <= year_max):
            continue
        year_dir = os.path.join(root_dir, name)
        if not os.path.isdir(year_dir):
            continue
        # 01..12
        for mm in range(1, 13):
            month_dir = os.path.join(year_dir, f"{mm:02d}")
            if os.path.isdir(month_dir):
                yield month_dir

def list_year_subdirs(root_dir):
    """返回 root_dir 下長得像西元年的子資料夾完整路徑（四位數，依數字排序）"""
    out = []
    for name in sorted(os.listdir(root_dir)):
        p = os.path.join(root_dir, name)
        if os.path.isdir(p) and re.fullmatch(r"\d{4}", name):
            out.append(p)
    return out

def list_month_subdirs(root_dir):
    out = []
    for mm in range(1, 13):
        p = os.path.join(root_dir, f"{mm:02d}")
        if os.path.isdir(p):
            out.append(p)
    print(f"  - Found {len(out)} month subdirs in {root_dir}")
    return out


def get_indices(ds, lat, lon):
    lats, lons = ds.variables["lat"][:], ds.variables["lon"][:]
    lat_idx = int(np.abs(lats - lat).argmin())
    lon_idx = int(np.abs(lons - lon).argmin())
    return lat_idx, lon_idx

def iter_nc_files(root_dir):
    for root, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith(".nc4"):
                yield os.path.join(root, f)

def read_imerg_precip_month(ds, lat_idx, lon_idx):
    var = ds.variables.get("precipitation")
    if var is None:
        return np.nan
    # 抓值
    if var.ndim == 3:
        if "lat" in var.dimensions[1].lower():
            val = float(var[0, lat_idx, lon_idx])
        else:
            val = float(var[0, lon_idx, lat_idx])
    elif var.ndim == 2:
        val = float(var[lat_idx, lon_idx])
    else:
        return np.nan
    # 換單位到 mm/day
    units = (getattr(var, "units", "") or "").lower()
    if "mm/hr" in units:
        val *= 24.0
    elif "mm/month" in units:
        # 沒有月天數就假定 30
        val = val / float(getattr(ds, "days_in_month", 30))
    # mm/day 保持不變
    return val

def read_imerg_precip_day(ds, lat_idx, lon_idx):
    """回傳 mm/day（日檔，通常變數 precipitation 已是當日累計或 mm/day）"""
    var = ds.variables.get("precipitation")
    if var is None:
        return np.nan
    # (time, lon, lat) or (time, lat, lon)
    if var.ndim == 3:
        d1, d2 = var.dimensions[1], var.dimensions[2]
        if "lat" in d1.lower():
            val = float(var[0, lat_idx, lon_idx])
        else:
            val = float(var[0, lon_idx, lat_idx])
    elif var.ndim == 2:
        val = float(var[lat_idx, lon_idx])
    else:
        return np.nan
    # 單位若是 mm/hr → 轉 mm/day；其它預設 mm/day
    units = (getattr(var, "units", "") or "").lower()
    if "mm/hr" in units:
        val *= 24.0
    return val

def merra_humidity_gpkg(q_kgkg):
    if q_kgkg is None or np.isnan(q_kgkg):
        return np.nan
    q = np.clip(float(q_kgkg), 1e-9, 0.04)
    return 1000.0 * q / (1.0 - q)

def compute_pm25_from_aer_vars(ds, lat_idx, lon_idx):
    """回傳 µg/m³，若缺變數則回 NaN"""
    needed = ["BCSMASS", "OCSMASS", "SO4SMASS", "DUSMASS25", "SSSMASS25"]
    if not all(v in ds.variables for v in needed):
        return np.nan
    bc  = ds["BCSMASS"][0, lat_idx, lon_idx]
    oc  = ds["OCSMASS"][0, lat_idx, lon_idx]
    so4 = ds["SO4SMASS"][0, lat_idx, lon_idx] * 1.375
    du  = ds["DUSMASS25"][0, lat_idx, lon_idx]
    ss  = ds["SSSMASS25"][0, lat_idx, lon_idx]
    return float((bc + oc + so4 + du + ss) * 1e9)

# ========== 讀月資料（2022–2025）做當月基線 ==========
def load_monthly_records(lat, lon):
    records = {}  # dt(YYYY-MM-01) -> dict

    def month_dirs_under(root, y0, y1):
        # 走 ./<root>/<year>/<month>
        for yname in sorted(os.listdir(root)):
            ypath = os.path.join(root, yname)
            if not (os.path.isdir(ypath) and re.fullmatch(r"\d{4}", yname)):
                continue
            y = int(yname)
            if y < y0 or y > y1:
                continue
            for mm in range(1, 13):
                mpath = os.path.join(ypath, f"{mm:02d}")
                if os.path.isdir(mpath):
                    yield mpath

    # -------- rain (IMERG monthly) --------
    if os.path.isdir(DIRS_MONTHLY["rain"]):
        print("📅 Loading monthly precipitation...")
        root = DIRS_MONTHLY["rain"]

        # ./precipitation/<year>/<month>/*
        for month_dir in month_dirs_under(root, 2022, 2024):
            print(f"  - Scanning {month_dir} ...")
            files = [f for f in os.listdir(month_dir)
                     if f.lower().endswith((".nc4", ".hdf5", ".h5", ".nc"))]
            for fname in sorted(files):
                dt = extract_yyyymm(fname)
                if not dt:
                    continue
                fpath = os.path.join(month_dir, fname)
                try:
                    ds = nc.Dataset(fpath)
                    lat_idx, lon_idx = get_indices(ds, lat, lon)
                    rain = read_imerg_precip_month(ds, lat_idx, lon_idx)
                except:
                    rain = np.nan
                finally:
                    try: ds.close()
                    except: pass
                records.setdefault(dt, {})["rain"] = rain

        # 後援：若有平放在根目錄
        flat_files = [f for f in os.listdir(root)
                      if f.lower().endswith((".nc4", ".hdf5", ".h5", ".nc"))]
        for fname in sorted(flat_files):
            dt = extract_yyyymm(fname)
            if not dt:
                continue
            fpath = os.path.join(root, fname)
            try:
                ds = nc.Dataset(fpath)
                lat_idx, lon_idx = get_indices(ds, lat, lon)
                rain = read_imerg_precip_month(ds, lat_idx, lon_idx)
            except:
                rain = np.nan
            finally:
                try: ds.close()
                except: pass
            records.setdefault(dt, {})["rain"] = rain

    # -------- slv (MERRA-2 monthly) --------
    if os.path.isdir(DIRS_MONTHLY["slv"]):
        print("📅 Loading monthly SLV (T2M/PS/QV2M/U10M/V10M)...")
        root = DIRS_MONTHLY["slv"]

        for month_dir in month_dirs_under(root, 2022, 2024):
            print(f"  - Scanning {month_dir} ...")
            files = [f for f in os.listdir(month_dir)
                     if f.lower().endswith((".nc4", ".nc"))]
            for fname in sorted(files):
                dt = extract_yyyymm(fname)
                if not dt:
                    continue
                fpath = os.path.join(month_dir, fname)
                try:
                    ds = nc.Dataset(fpath)
                    lat_idx, lon_idx = get_indices(ds, lat, lon)
                    t2m = float(ds["T2M"][0, lat_idx, lon_idx]) - 273.15 if "T2M"  in ds.variables else np.nan
                    ps  = float(ds["PS"][0,  lat_idx, lon_idx]) / 100.0   if "PS"   in ds.variables else np.nan
                    q   = float(ds["QV2M"][0,lat_idx, lon_idx])           if "QV2M" in ds.variables else np.nan
                    hum = merra_humidity_gpkg(q)
                    if "U10M" in ds.variables and "V10M" in ds.variables:
                        u10 = float(ds["U10M"][0, lat_idx, lon_idx])
                        v10 = float(ds["V10M"][0, lat_idx, lon_idx])
                        wind = float(np.sqrt(u10**2 + v10**2))
                    else:
                        wind = np.nan
                except:
                    t2m = ps = hum = wind = np.nan
                finally:
                    try: ds.close()
                    except: pass
                records.setdefault(dt, {}).update(
                    {"temp": t2m, "pressure": ps, "humidity": hum, "wind": wind}
                )

        # 後援：平放在根目錄
        flat_files = [f for f in os.listdir(root)
                      if f.lower().endswith((".nc4", ".nc"))]
        for fname in sorted(flat_files):
            dt = extract_yyyymm(fname)
            if not dt:
                continue
            fpath = os.path.join(root, fname)
            try:
                ds = nc.Dataset(fpath)
                lat_idx, lon_idx = get_indices(ds, lat, lon)
                t2m = float(ds["T2M"][0, lat_idx, lon_idx]) - 273.15 if "T2M"  in ds.variables else np.nan
                ps  = float(ds["PS"][0,  lat_idx, lon_idx]) / 100.0   if "PS"   in ds.variables else np.nan
                q   = float(ds["QV2M"][0,lat_idx, lon_idx])           if "QV2M" in ds.variables else np.nan
                hum = merra_humidity_gpkg(q)
                if "U10M" in ds.variables and "V10M" in ds.variables:
                    u10 = float(ds["U10M"][0, lat_idx, lon_idx])
                    v10 = float(ds["V10M"][0, lat_idx, lon_idx])
                    wind = float(np.sqrt(u10**2 + v10**2))
                else:
                    wind = np.nan
            except:
                t2m = ps = hum = wind = np.nan
            finally:
                try: ds.close()
                except: pass
            records.setdefault(dt, {}).update(
                {"temp": t2m, "pressure": ps, "humidity": hum, "wind": wind}
            )

    # -------- aer (MERRA-2 aerosol monthly) --------
    if os.path.isdir(DIRS_MONTHLY["aer"]):
        print("📅 Loading monthly aerosol (PM2.5 components)...")
        root = DIRS_MONTHLY["aer"]

        for month_dir in month_dirs_under(root, 2022, 2024):
            print(f"  - Scanning {month_dir} ...")
            files = [f for f in os.listdir(month_dir)
                     if f.lower().endswith((".nc4", ".nc"))]
            for fname in sorted(files):
                dt = extract_yyyymm(fname)
                if not dt:
                    continue
                fpath = os.path.join(month_dir, fname)
                try:
                    ds = nc.Dataset(fpath)
                    lat_idx, lon_idx = get_indices(ds, lat, lon)
                    pm25 = compute_pm25_from_aer_vars(ds, lat_idx, lon_idx)
                except:
                    pm25 = np.nan
                finally:
                    try: ds.close()
                    except: pass
                records.setdefault(dt, {})["pm25"] = pm25

        # 後援：平放在根目錄
        flat_files = [f for f in os.listdir(root)
                      if f.lower().endswith((".nc4", ".nc"))]
        for fname in sorted(flat_files):
            dt = extract_yyyymm(fname)
            if not dt:
                continue
            fpath = os.path.join(root, fname)
            try:
                ds = nc.Dataset(fpath)
                lat_idx, lon_idx = get_indices(ds, lat, lon)
                pm25 = compute_pm25_from_aer_vars(ds, lat_idx, lon_idx)
            except:
                pm25 = np.nan
            finally:
                try: ds.close()
                except: pass
            records.setdefault(dt, {})["pm25"] = pm25

    # -------- 組成 DataFrame --------
    rows = []
    for dt, v in records.items():
        rows.append({
            "date": dt,
            "year": dt.year,
            "month": dt.month,
            "rain": v.get("rain", np.nan),
            "temp": v.get("temp", np.nan),
            "pressure": v.get("pressure", np.nan),
            "humidity": v.get("humidity", np.nan),
            "wind": v.get("wind", np.nan),
            "pm25": v.get("pm25", np.nan),
        })
    dfm = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    # 若 pm25 缺，proxy
    miss = dfm["pm25"].isna()
    if miss.any():
        dfm.loc[miss, "pm25"] = np.clip(
            0.8 * dfm.loc[miss, "humidity"].fillna(dfm["humidity"].median()) +
            8.0 * np.maximum(0, 2.0 - dfm.loc[miss, "wind"].fillna(dfm["wind"].median())) -
            0.05 * dfm.loc[miss, "rain"].fillna(dfm["rain"].median()),
            5, 150
        )
    return dfm


# ========== 讀 2024 daily（用於 anomaly） ==========
def load_daily_2024(lat, lon):
    rec = {} 
    # rain
    if os.path.isdir(DIRS_DAILY_2024["rain"]):
        for fname in sorted(os.listdir(DIRS_DAILY_2024["rain"])):
            print(f"  - Scanning {fname} ...")
            if not fname or not fname.endswith(".nc4"): continue
            dt = extract_yyyymmdd(fname)
            if not dt or dt.year != 2024: continue
            fpath = os.path.join(DIRS_DAILY_2024["rain"], fname)
            try:
                ds = nc.Dataset(fpath)
                lat_idx, lon_idx = get_indices(ds, lat, lon)
                rain = read_imerg_precip_day(ds, lat_idx, lon_idx)
            except:
                rain = np.nan
            finally:
                try: ds.close()
                except: pass
            rec.setdefault(dt, {})["rain"] = rain
    # slv
    if os.path.isdir(DIRS_DAILY_2024["slv"]):
        for fname in sorted(os.listdir(DIRS_DAILY_2024["slv"])):
            print(f"  - Scanning {fname} ...")
            if not fname.endswith(".nc4"): continue
            dt = extract_yyyymmdd(fname)
            if not dt or dt.year != 2024: continue
            fpath = os.path.join(DIRS_DAILY_2024["slv"], fname)
            try:
                ds = nc.Dataset(fpath)
                lat_idx, lon_idx = get_indices(ds, lat, lon)
                t2m = float(ds["T2M"][0, lat_idx, lon_idx]) - 273.15 if "T2M" in ds.variables else np.nan
                ps  = float(ds["PS"][0,  lat_idx, lon_idx]) / 100.0   if "PS"  in ds.variables else np.nan
                q   = float(ds["QV2M"][0,lat_idx, lon_idx])           if "QV2M" in ds.variables else np.nan
                hum = merra_humidity_gpkg(q)
                if "U10M" in ds.variables and "V10M" in ds.variables:
                    u10 = float(ds["U10M"][0, lat_idx, lon_idx])
                    v10 = float(ds["V10M"][0, lat_idx, lon_idx])
                    wind = float(np.sqrt(u10**2 + v10**2))
                else:
                    wind = np.nan
            except:
                t2m = ps = hum = wind = np.nan
            finally:
                try: ds.close()
                except: pass
            rec.setdefault(dt, {}).update({"temp": t2m, "pressure": ps, "humidity": hum, "wind": wind})
    # aer
    if os.path.isdir(DIRS_DAILY_2024["aer"]):
        for fname in sorted(os.listdir(DIRS_DAILY_2024["aer"])):
            if not fname.endswith(".nc4"): continue
            dt = extract_yyyymmdd(fname)
            if not dt or dt.year != 2024: continue
            fpath = os.path.join(DIRS_DAILY_2024["aer"], fname)
            try:
                ds = nc.Dataset(fpath)
                lat_idx, lon_idx = get_indices(ds, lat, lon)
                pm25 = compute_pm25_from_aer_vars(ds, lat_idx, lon_idx)
            except:
                pm25 = np.nan
            finally:
                try: ds.close()
                except: pass
            rec.setdefault(dt, {})["pm25"] = pm25

    rows = []
    for dt, v in rec.items():
        rows.append({
            "date": dt,
            "year": dt.year, "month": dt.month, "day": dt.day, "doy": dt.timetuple().tm_yday,
            "rain": v.get("rain", np.nan),
            "temp": v.get("temp", np.nan),
            "pressure": v.get("pressure", np.nan),
            "humidity": v.get("humidity", np.nan),
            "wind": v.get("wind", np.nan),
            "pm25": v.get("pm25", np.nan),
        })
    dfd = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return dfd

# ========== 用歷史月資料做「當月基線」（加快運算） ==========
_baseline_cache = {}

def monthly_baseline(dfm, year, month):
    key = (year, month)
    if key in _baseline_cache:
        return _baseline_cache[key]

    hist = dfm[dfm["month"] == month].copy()
    feature_cols = ["rain","temp","pressure","humidity","wind","pm25"]
    target_cols  = feature_cols
    out = {}

    if hist.empty:
        for c in target_cols: out[c] = np.nan
        _baseline_cache[key] = out
        return out

    hist["weight"] = 1 + 0.5 * (hist["year"] - (hist["year"].max() - 3))
    ref = hist[feature_cols].mean()

    model_cache = {}
    for tgt in target_cols:
        sub = hist.dropna(subset=[tgt])
        if len(sub) >= 3:
            if tgt not in model_cache:
                model = RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1)
                model.fit(sub[feature_cols], sub[tgt], sample_weight=sub["weight"])
                model_cache[tgt] = model
            out[tgt] = float(model_cache[tgt].predict(ref.values.reshape(1, -1))[0])
        else:
            out[tgt] = float(sub[tgt].mean()) if len(sub) else np.nan

    _baseline_cache[key] = out
    return out

# ========== 用 2024 daily 做「當日 anomaly」 ==========
def daily_anomaly_from_2024(dfd, month, day, var):
    """以 NumPy 加速 2024 同月日 anomaly 查找"""
    subm = dfd[dfd["month"] == month]
    if subm.empty or var not in subm.columns:
        return np.nan

    arr_day = subm["day"].to_numpy()
    arr_val = subm[var].to_numpy()
    month_mean = np.nanmean(arr_val)
    mask = np.where(arr_day == day)[0]
    if mask.size > 0 and not np.isnan(arr_val[mask[0]]):
        return float(arr_val[mask[0]] - month_mean)

    # ±2天範圍搜尋
    for offset in [1, 2]:
        for delta in [-offset, offset]:
            dd = day + delta
            mask = np.where(arr_day == dd)[0]
            if mask.size > 0 and not np.isnan(arr_val[mask[0]]):
                return float(arr_val[mask[0]] - month_mean)
    return 0.0

# ========== 極端機率（線性接近門檻） ==========
def extreme_probs(pred):
    temp = float(pred.get("temp", np.nan))
    rain = float(pred.get("rain", np.nan))
    press= float(pred.get("pressure", np.nan))
    hum  = float(pred.get("humidity", np.nan))
    wind = float(pred.get("wind", np.nan))
    pm25 = float(pred.get("pm25", np.nan))

    def up(x, lo, hi):     # x<=lo→0, x>=hi→100
        if np.isnan(x): return 0.0
        return float(np.clip((x - lo)/(hi - lo), 0, 1)*100)
    def down(x, lo, hi):   # x>=hi→0, x<=lo→100
        if np.isnan(x): return 0.0
        return float(np.clip((hi - x)/(hi - lo), 0, 1)*100)

    probs = {}
    probs["heatwave_probability"]          = round(up(temp, 30, 35), 1)
    probs["cold_wave_probability"]        = round(down(temp, 5, 15), 1)
    probs["heavy_rain_probability"]        = round(up(rain, 10, 50), 1)
    dry_r = down(rain, 0.2, 3.0)
    dry_h = down(hum,  0.0, 8.0)
    drought = 0.7*dry_r + 0.3*dry_h
    if not np.isnan(rain) and rain >= 5.0:
        drought = 0.0
    probs["drought_probability"]          = round(drought, 1)

    # 颱風/低壓（加入濕度與風）
    p_score = down(press, 990, 1008)
    h_score = up(hum, 10, 18)
    t_score = up(temp, 25, 30)
    w_score = up(wind, 8, 20)
    probs["typhoon_probability"]   = round((0.4*p_score + 0.25*h_score + 0.25*t_score + 0.1*w_score), 1)

    probs["strong_wind_probability"]       = round(up(wind, 10, 17), 1)
    # 雷暴：高濕 + 有降雨
    probs["thunderstorm_probability"]      = round(0.6*up(hum, 15, 30) + 0.4*up(rain, 5, 25), 1)
    probs["AQ"]          = round(up(pm25, 35, 150), 1)

    # 互斥修正：豪雨高 → 乾旱降低
    if probs["heavy_rain_probability"] > 50:
        probs["drought_probability"] = round(probs["drought_probability"] * 0.2, 1)
    return probs

def compute_comfort_index(pred):
    t = pred.get("temp", np.nan)
    h = pred.get("humidity", np.nan)
    w = pred.get("wind", np.nan)
    r = pred.get("rain", np.nan)

    def lin(x, lo, hi):  # 線性映射 0~1
        return float(np.clip((x - lo) / (hi - lo), 0, 1)) if not np.isnan(x) else 0

    very_hot  = lin(t, 30, 38)
    very_cold = lin(10 - t, -5, 10)
    very_windy = lin(w, 8, 18)
    very_wet  = max(lin(h, 15, 25), lin(r, 5, 20))
    very_uncomfortable = np.clip(0.4*very_hot + 0.2*very_wet + 0.2*very_windy + 0.2*very_cold, 0, 1)

    return {
        "very_hot": round(very_hot, 2),
        "very_cold": round(very_cold, 2),
        "very_windy": round(very_windy, 2),
        "very_wet": round(very_wet, 2),
        "very_uncomfortable": float(round(very_uncomfortable, 2))
    }
    
def describe_daily_weather(row):
        """為每日各氣象項目生成一句自然語句"""
        t = float(row["temp_C"])
        r = float(row["rain_mm_day"])
        p = float(row["pressure_hPa"])
        h = float(row["humidity_gkg"])
        w = float(row["wind_ms"])
        pm = float(row["pm25_ugm3"])

        desc = {}

        # 🌧️ 降雨 Rain
        if r == 0:
            desc["rain"] = "No rainfall today, skies remain clear."
        elif r < 2:
            desc["rain"] = "A few light drizzles may occur during the day."
        elif r < 10:
            desc["rain"] = "Intermittent showers expected throughout the day."
        elif r < 30:
            desc["rain"] = "Moderate rain is likely; carry an umbrella."
        elif r < 50:
            desc["rain"] = "Heavy rainfall expected; potential localized flooding."
        else:
            desc["rain"] = "Torrential rain throughout the day with possible storm activity."

        # 🌡️ 溫度 Temperature
        if t < 5:
            desc["temp"] = "Temperatures are freezing cold; bundle up if heading outdoors."
        elif t < 10:
            desc["temp"] = "A very cold day with chilly winds."
        elif t < 15:
            desc["temp"] = "Cool weather, suitable for light jackets."
        elif t < 22:
            desc["temp"] = "Mild and comfortable temperatures."
        elif t < 30:
            desc["temp"] = "Warm conditions with a pleasant feel."
        elif t < 35:
            desc["temp"] = "A hot day; stay hydrated under the sun."
        else:
            desc["temp"] = "Extremely hot weather; heat stress precautions advised."

        # 💨 氣壓 Pressure
        if p < 995:
            desc["pressure"] = "A low-pressure system may bring unstable weather or storms."
        elif p < 1005:
            desc["pressure"] = "Slightly low pressure, possibly cloudy conditions."
        elif p < 1020:
            desc["pressure"] = "Normal atmospheric pressure, stable overall."
        else:
            desc["pressure"] = "High pressure dominates, indicating calm and fair weather."

        # 💧 濕度 Humidity
        if h < 5:
            desc["humidity"] = "Very dry air today, comfortable but static-prone."
        elif h < 10:
            desc["humidity"] = "Slightly dry conditions with mild comfort."
        elif h < 18:
            desc["humidity"] = "Moderate humidity with balanced comfort levels."
        elif h < 25:
            desc["humidity"] = "Humid air making the day feel warmer."
        else:
            desc["humidity"] = "Extremely humid conditions; discomfort likely."

        # 🌬️ 風速 Wind
        if w < 1:
            desc["wind"] = "Calm air with almost no wind movement."
        elif w < 3:
            desc["wind"] = "A gentle breeze providing mild ventilation."
        elif w < 8:
            desc["wind"] = "Light winds keep the air fresh and moving."
        elif w < 12:
            desc["wind"] = "Moderate winds noticeable throughout the day."
        elif w < 20:
            desc["wind"] = "Strong winds may cause dust and light debris movement."
        else:
            desc["wind"] = "Very strong winds — potential for gusty or hazardous conditions."

        # 🌫️ 空氣品質 PM2.5
        if pm < 12:
            desc["pm25"] = "Excellent air quality with clean, breathable air."
        elif pm < 35:
            desc["pm25"] = "Good air quality; no health concerns."
        elif pm < 55:
            desc["pm25"] = "Moderate air quality; sensitive groups should limit exposure."
        elif pm < 150:
            desc["pm25"] = "Poor air quality; prolonged outdoor activity is discouraged."
        else:
            desc["pm25"] = "Hazardous air pollution levels; stay indoors if possible."

        return desc
    
def generate_comfort_summary(comfort):

        hot = comfort.get("very_hot", 0)
        cold = comfort.get("very_cold", 0)
        wind = comfort.get("very_windy", 0)
        wet = comfort.get("very_wet", 0)
        uncomfort = comfort.get("very_uncomfortable", 0)

        # --- Temperature impression ---
        if hot > 0.6:
            temp_phrase = "The day feels quite hot, with noticeable warmth throughout."
        elif cold > 0.6:
            temp_phrase = "It feels rather cold, especially during early hours."
        elif hot > 0.3:
            temp_phrase = "The weather is warm and mild."
        elif cold > 0.3:
            temp_phrase = "Slight chill can be felt, but conditions remain pleasant."
        else:
            temp_phrase = "Temperature stays comfortable and balanced."

        # --- Humidity & rain ---
        if wet > 0.6:
            moisture_phrase = "Humidity and moisture are high, giving a sticky or damp sensation."
        elif wet > 0.3:
            moisture_phrase = "The air feels slightly humid, but still breathable."
        else:
            moisture_phrase = "Air remains dry and comfortable."

        # --- Wind ---
        if wind > 0.6:
            wind_phrase = "Strong winds may add some chill or cause minor discomfort outdoors."
        elif wind > 0.3:
            wind_phrase = "A gentle breeze keeps the air fresh and pleasant."
        else:
            wind_phrase = "Winds are calm, contributing to a stable atmosphere."

        # --- Overall comfort ---
        if uncomfort > 0.75:
            overall_phrase = "Overall, the weather may feel quite uncomfortable due to combined heat, humidity, or wind."
        elif uncomfort > 0.45:
            overall_phrase = "Some mild discomfort may occur, but most conditions remain tolerable."
        else:
            overall_phrase = "Overall comfort is high, offering an enjoyable and relaxing day."

        # --- Combine into a concise paragraph (2–3 sentences) ---
        return f"{temp_phrase} {moisture_phrase} {wind_phrase} {overall_phrase}"
# ==============================
# 主流程
# ==============================
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def run_climate_forecast(lat, lon, start_date, end_date):
    """
    執行整段氣象預測流程。
    傳入：
        lat, lon: float
        start_date, end_date: 'YYYY-MM-DD' 格式字串
    回傳：
        dict -> JSON 格式資料
    """
    START_DT = datetime.strptime(start_date, "%Y-%m-%d")
    END_DT = datetime.strptime(end_date, "%Y-%m-%d")
    if END_DT < START_DT:
        raise ValueError("End date must be >= Start date")

    print("📥 Loading monthly climatology ...")
    df_month = load_monthly_records(lat, lon)
    if df_month.empty:
        raise SystemExit("No monthly records found. Check DIRS_MONTHLY paths.")

    print("📥 Loading 2024 daily data for anomaly adjustment ...")
    df_daily_2024 = load_daily_2024(lat, lon)
    if df_daily_2024.empty:
        print("⚠️ No 2024 daily data found. Will skip anomaly nudging.")

    # 主迴圈
    results = []
    for d in pd.date_range(START_DT, END_DT, freq="D"):
        base = monthly_baseline(df_month, d.year, d.month)
        adjusted = {}
        for var in ["rain","temp","pressure","humidity","wind","pm25"]:
            base_val = base.get(var, np.nan)
            if df_daily_2024.empty or np.isnan(base_val):
                adj_val = base_val
            else:
                anom = daily_anomaly_from_2024(df_daily_2024, d.month, d.day, var)
                adj_val = base_val + (anom if not np.isnan(anom) else 0.0)
            if var in ["rain", "humidity", "pm25"]:
                adj_val = max(0.0, adj_val)
            adjusted[var] = float(round(adj_val, 2))

        comfort = compute_comfort_index(adjusted)
        description = generate_comfort_summary(comfort)
        daily_desc = describe_daily_weather({
            "rain_mm_day": adjusted["rain"],
            "temp_C": adjusted["temp"],
            "pressure_hPa": adjusted["pressure"],
            "humidity_gkg": adjusted["humidity"],
            "wind_ms": adjusted["wind"],
            "pm25_ugm3": adjusted["pm25"]
        })

        results.append({
            "date": d.date().isoformat(),
            "rain": adjusted["rain"],
            "rain_desc": daily_desc["rain"],
            "temp": adjusted["temp"],
            "temp_desc": daily_desc["temp"],
            "pressure": adjusted["pressure"],
            "pressure_desc": daily_desc["pressure"],
            "humidity": adjusted["humidity"],
            "humidity_desc": daily_desc["humidity"],
            "wind": adjusted["wind"],
            "wind_desc": daily_desc["wind"],
            "pm25": adjusted["pm25"],
            "pm25_desc": daily_desc["pm25"],
            "comfort_index": comfort,
            "climate_description": description
        })

    # 整期間平均 + 極端氣候機率
    out_df = pd.DataFrame(results)
    period_mean = {
        "rain": out_df["rain"].mean(),
        "temp": out_df["temp"].mean(),
        "pressure": out_df["pressure"].mean(),
        "humidity": out_df["humidity"].mean(),
        "wind": out_df["wind"].mean(),
        "pm25": out_df["pm25"].mean(),
    }
    period_probs = extreme_probs(period_mean)

    output = {
        "location": {"lat": lat, "lon": lon},
        "period": {"start": start_date, "end": end_date},
        "summary": {
            "average_conditions": {k: round(float(v), 2) for k, v in period_mean.items()},
            "extreme_event_probabilities": period_probs
        },
        "daily_reports": results
    }

    # 輸出 JSON 字串（可直接 print 或回傳給 API）
    return json.dumps(output, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    result_json = run_climate_forecast(TARGET_LAT, TARGET_LON, START_DATE, END_DATE)
    print(result_json)