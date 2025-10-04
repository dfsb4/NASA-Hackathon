import os
import netCDF4 as nc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt

# === Config ===
data_dir = "./data/air_quality/" 
target_lat, target_lon = 28.7, 77.1
records = []

# === Read monthly data ===
for year in range(2022, 2025):
    for month in range(1, 13):
        fname = f"{year}/{month:02d}/MERRA2_400.tavgM_2d_aer_Nx.{year}{month:02d}.nc4.nc4"
        fpath = os.path.join(data_dir, fname)
        if not os.path.exists(fpath):
            print(f"⚠️ Missing: {fname}")
            continue

        ds = nc.Dataset(fpath)
        lat, lon = ds['lat'][:], ds['lon'][:]
        lat_idx, lon_idx = np.abs(lat - target_lat).argmin(), np.abs(lon - target_lon).argmin()

        bc = float(ds['BCSMASS'][0, lat_idx, lon_idx])
        oc = float(ds['OCSMASS'][0, lat_idx, lon_idx])
        so4 = float(ds['SO4SMASS'][0, lat_idx, lon_idx])
        dust = float(ds['DUSMASS25'][0, lat_idx, lon_idx])
        sea = float(ds['SSSMASS25'][0, lat_idx, lon_idx])
        ds.close()

        pm25 = (bc + oc + so4 * 1.375 + dust + sea) * 1e9

        records.append({
            "date": datetime(year, month, 1),
            "year": year,
            "month": month,
            "pm25": pm25,
            "bc": bc * 1e9,
            "oc": oc * 1e9,
            "so4": so4 * 1e9,
            "dust": dust * 1e9,
            "sea": sea * 1e9
        })

df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
print(f"📊 Loaded {len(df)} months from {df['date'].min()} to {df['date'].max()}")

# === Predict each future month (2025/10–2026/05) ===
forecast_list = []
predict_years = [2025, 2026]
predict_months = list(range(10, 13)) + list(range(1, 6))

for year in predict_years:
    for month in predict_months:
        if year == 2025 and month < 10: continue
        if year == 2026 and month > 5: continue

        month_df = df[df["month"] == month]
        if len(month_df) < 3:
            print(f"⚠️ {year}/{month:02d} insufficient samples ({len(month_df)})")
            continue

        X = month_df[["bc", "oc", "so4", "dust", "sea"]]
        y = month_df["pm25"]

        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(X[:-1], y[:-1])
        pred = model.predict([X.iloc[-1].values])[0]

        forecast_list.append({"date": datetime(year, month, 1), "pred_pm25": pred})

forecast_df = pd.DataFrame(forecast_list).sort_values("date")

# === Air quality classification ===
def classify_pm25(v):
    if v <= 12:
        return "Good 🟢 — Air quality is satisfactory."
    elif v <= 35.4:
        return "Moderate 🟡 — Acceptable air quality; minor concern for sensitive people."
    elif v <= 55.4:
        return "Unhealthy for Sensitive Groups 🟠 — Sensitive individuals may experience effects."
    elif v <= 150.4:
        return "Unhealthy 🔴 — Everyone may begin to experience health effects."
    elif v <= 250.4:
        return "Very Unhealthy 🟣 — Health alert: serious effects possible."
    else:
        return "Hazardous 🟤 — Emergency conditions; avoid outdoor exposure."

forecast_df["category"] = forecast_df["pred_pm25"].apply(classify_pm25)

# === Output ===
print("\n🌫️ PM2.5 Forecast (Taipei, 2025/10–2026/05):\n")
for _, r in forecast_df.iterrows():
    ym = r["date"].strftime("%B %Y")
    print(f"{ym}: Predicted PM2.5 = {r['pred_pm25']:.1f} µg/m³ — {r['category']}")

# === Plot ===
plt.figure(figsize=(10,5))
plt.plot(df["date"], df["pm25"], "o-", label="Observed (2022–2025)", alpha=0.6)
plt.plot(forecast_df["date"], forecast_df["pred_pm25"], "r--o", label="Predicted (2025/10–2026/05)")
plt.title("Predicted Monthly PM2.5")
plt.ylabel("PM2.5 (µg/m³)")
plt.xlabel("Date")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()