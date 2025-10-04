import os
import netCDF4 as nc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt

# === Basic settings ===
data_dir = "./data/precipitation/"
target_lat, target_lon = 25.0, 121.5
records = []

# === Automatically load all monthly files ===
for year in range(2022, 2026):
    for month in range(1, 13):
        if (year == 2025 and month > 5):  # up to 2025/05
            break
        fname = f"{year}/{month:02d}/3B-MO.MS.MRG.3IMERG.{year}{month:02d}01-S000000-E235959.{month:02d}.V07B.HDF5.nc4"
        fpath = os.path.join(data_dir, fname)
        if not os.path.exists(fpath):
            print(f"⚠️ Missing: {fname}")
            continue

        ds = nc.Dataset(fpath)
        lat, lon = ds.variables['lat'][:], ds.variables['lon'][:]
        lat_idx, lon_idx = np.abs(lat - target_lat).argmin(), np.abs(lon - target_lon).argmin()

        rain_amt = float(ds.variables['precipitation'][0, lon_idx, lat_idx])
        quality = float(ds.variables['precipitationQualityIndex'][0, lon_idx, lat_idx])
        gauge = float(ds.variables['gaugeRelativeWeighting'][0, lon_idx, lat_idx])
        error = float(ds.variables['randomError'][0, lon_idx, lat_idx])
        ds.close()

        records.append({
            'date': datetime(year, month, 1),
            'year': year,
            'month': month,
            'precipitation': rain_amt,
            'quality_index': quality,
            'gauge_weight': gauge,
            'random_error': error
        })

# === Create DataFrame ===
df = pd.DataFrame(records).sort_values('date').reset_index(drop=True)
print(f"\n📊 Loaded {len(df)} months from {df['date'].min().strftime('%Y-%m')} to {df['date'].max().strftime('%Y-%m')}")

# === Normalize precipitation as proxy for rain probability (0–100) ===
p = df['precipitation'].astype(float)
pmin, pmax = np.nanpercentile(p, 5), np.nanpercentile(p, 95)
df['rain_prob'] = (np.clip(p, pmin, pmax) - pmin) / (pmax - pmin) * 100.0

# === Train per-month models ===
forecast_list = []
predict_years = [2025, 2026]
predict_months = list(range(10, 13)) + list(range(1, 6))  # 2025/10–2026/05

for year in predict_years:
    for month in predict_months:
        if year == 2025 and month < 10:
            continue
        if year == 2026 and month > 5:
            continue

        # Extract same-month historical data
        month_df = df[df['month'] == month]
        if len(month_df) < 3:
            print(f"⚠️ {year}/{month:02d} - Not enough samples ({len(month_df)})")
            continue

        features = ['precipitation', 'quality_index', 'gauge_weight', 'random_error']
        X = month_df[features]
        y = month_df['rain_prob']

        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(X[:-1], y[:-1])  # Train on previous years
        pred = model.predict([X.iloc[-1].values])[0]  # Predict next year

        forecast_list.append({'date': datetime(year, month, 1), 'predicted_rain_prob': pred})

forecast_df = pd.DataFrame(forecast_list).sort_values('date').reset_index(drop=True)

# === Classification and description ===
def classify_rain_level(value):
    if value < 40:
        return "Dry, mostly sunny ☀️"
    elif value < 70:
        return "Moderate rainfall, occasional showers 🌤️"
    elif value < 90:
        return "Wet season, frequent rainfall 🌧️"
    else:
        return "Heavy rainfall, possible storms ⛈️"

forecast_df['rain_level'] = forecast_df['predicted_rain_prob'].apply(classify_rain_level)

# === Output English descriptions ===
print("\n🌦️ Rainfall outlook for Oct 2025 – May 2026:\n")
for _, row in forecast_df.iterrows():
    ym = row['date'].strftime('%B %Y')
    prob = row['predicted_rain_prob']
    desc = row['rain_level']
    print(f"{ym}: Predicted rain index {prob:.1f}. {desc}")

# === Visualization ===
plt.figure(figsize=(10,5))
plt.plot(df['date'], df['rain_prob'], 'o-', color='gray', alpha=0.6, label='Observed (2022/06–2025/05)')
plt.plot(forecast_df['date'], forecast_df['predicted_rain_prob'], 'r--', label='Predicted (Oct 2025–May 2026)')
plt.title('Rain Probability Forecast (Taipei, by Month Similarity Model)')
plt.ylabel('Rain Probability Index (0–100)')
plt.xlabel('Date')
plt.legend()
plt.grid(True)
plt.show()

oct_hist = df[df['month'] == 10][['date', 'rain_prob']].copy()
oct_hist['year'] = oct_hist['date'].dt.year
oct_hist = oct_hist.sort_values('year')

oct_pred = forecast_df[forecast_df['date'].dt.month == 10][['date', 'predicted_rain_prob']].copy()
oct_pred['year'] = oct_pred['date'].dt.year

plot_df_hist = oct_hist[['year', 'rain_prob']].rename(columns={'rain_prob': 'value'})
plot_df_hist['type'] = 'Observed'
plot_df_pred = oct_pred[['year', 'predicted_rain_prob']].rename(columns={'predicted_rain_prob': 'value'})
plot_df_pred['type'] = 'Predicted'

plot_df = pd.concat([plot_df_hist, plot_df_pred], ignore_index=True).sort_values('year')

plt.figure(figsize=(8,5))
hist_part = plot_df[plot_df['type']=='Observed']
plt.bar(hist_part['year'].astype(str), hist_part['value'], label='Observed Oct rain index', alpha=0.6, edgecolor='black')
pred_part = plot_df[plot_df['type']=='Predicted']
plt.bar(pred_part['year'].astype(str), pred_part['value'], label='Predicted Oct 2025 rain index', alpha=0.9, edgecolor='black')

for _, r in plot_df.iterrows():
    plt.text(str(r['year']), r['value']+1, f"{r['value']:.1f}", ha='center', va='bottom', fontsize=9)

plt.title('October Rain Probability Index: Observed vs Predicted')
plt.ylabel('Rain Probability Index (0–100)')
plt.xlabel('Year (October)')
plt.ylim(0, 105)
plt.grid(axis='y', linestyle='--', alpha=0.4)
plt.legend()
plt.tight_layout()
plt.show()