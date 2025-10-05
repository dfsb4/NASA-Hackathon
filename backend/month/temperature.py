import os
import netCDF4 as nc
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def pred(lat, lon):
    # === Basic Config ===
    data_dir = "./data/temperature/"  # MERRA-2 tavgM_2d_slv_Nx monthly files
    target_lat, target_lon = lat, lon
    records = []

    # === Read monthly data 2022/06–2025/05 ===
    for year in range(2022, 2026):
        for month in range(1, 13):
            if (year == 2022 and month < 6):
                continue
            if (year == 2025 and month > 5):
                break

            fname = f"{year}/{month:02d}/MERRA2_400.tavgM_2d_slv_Nx.{year}{month:02d}.nc4"
            fpath = os.path.join(data_dir, fname)
            if not os.path.exists(fpath):
                print(f"⚠️ Missing: {fname}")
                continue

            ds = nc.Dataset(fpath)
            lat = ds.variables['lat'][:]
            lon = ds.variables['lon'][:]
            lat_idx = np.abs(lat - target_lat).argmin()
            lon_idx = np.abs(lon - target_lon).argmin()

            # Extract key variables
            t2m = float(ds.variables['T2M'][0, lat_idx, lon_idx]) - 273.15  # °C
            qv2m = float(ds.variables['QV2M'][0, lat_idx, lon_idx]) * 1000  # g/kg (rough conversion)
            slp = float(ds.variables['SLP'][0, lat_idx, lon_idx]) / 100.0   # hPa
            u10m = float(ds.variables['U10M'][0, lat_idx, lon_idx])
            v10m = float(ds.variables['V10M'][0, lat_idx, lon_idx])
            wind_speed = np.sqrt(u10m**2 + v10m**2)  # m/s
            ds.close()

            records.append({
                'date': datetime(year, month, 1),
                'year': year,
                'month': month,
                'T2M': t2m,
                'QV2M': qv2m,
                'SLP': slp,
                'WIND': wind_speed
            })

    # === Build DataFrame ===
    df = pd.DataFrame(records).sort_values('date').reset_index(drop=True)
    print(f"\n📊 Loaded {len(df)} months from {df['date'].min().strftime('%Y-%m')} to {df['date'].max().strftime('%Y-%m')}")

    # === Prediction setup ===
    forecast_list = []
    predict_years = [2025, 2026]
    predict_months = list(range(10, 13)) + list(range(1, 6))

    def rf_forecast(month_df, var_name, year):
        """Train and predict one variable"""
        if len(month_df) < 3:
            return None
        X = month_df[['year']]
        y = month_df[var_name]
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(X.iloc[:-1], y.iloc[:-1])
        X_next = pd.DataFrame({'year': [year]})
        return float(model.predict(X_next)[0])

    # === Train & Predict ===
    for year in predict_years:
        for month in predict_months:
            if year == 2025 and month < 10:
                continue
            if year == 2026 and month > 5:
                continue

            month_df = df[df['month'] == month]
            if len(month_df) < 3:
                print(f"⚠️ {year}/{month:02d} insufficient data ({len(month_df)} samples)")
                continue

            temp_pred = rf_forecast(month_df, 'T2M', year)
            humid_pred = rf_forecast(month_df, 'QV2M', year)
            pres_pred = rf_forecast(month_df, 'SLP', year)
            wind_pred = rf_forecast(month_df, 'WIND', year)

            forecast_list.append({
                'date': datetime(year, month, 1),
                'Pred_Temp': temp_pred,
                'Pred_Humidity': humid_pred,
                'Pred_Pressure': pres_pred,
                'Pred_Wind': wind_pred
            })

    forecast_df = pd.DataFrame(forecast_list).sort_values('date').reset_index(drop=True)

    # === Classification (based on temperature & humidity) ===
    def classify_weather(temp, humidity, wind):
        if temp < 15:
            desc = "Cold — frequent cold fronts ❄️"
        elif temp < 20:
            desc = "Cool — mild winter or early spring 🍂"
        elif temp < 25:
            desc = "Moderate — comfortable season 🌤️"
        elif temp < 30:
            desc = "Warm — typical summer ☀️"
        else:
            desc = "Hot — high heat stress 🔥"

        if humidity > 15:
            desc += " (humid)"
        elif humidity < 8:
            desc += " (dry)"
        if wind > 5:
            desc += " with noticeable wind 🌬️"
        return desc

    forecast_df['description'] = forecast_df.apply(lambda r: classify_weather(r.Pred_Temp, r.Pred_Humidity, r.Pred_Wind), axis=1)

    # === Output summary ===
    print("\n Predicted Climate Summary (Taipei, 2025/10–2026/05):\n")
    for _, row in forecast_df.iterrows():
        ym = row['date'].strftime('%Y-%m')
        print(f"{ym}: Temp {row.Pred_Temp:.1f}°C, Humidity {row.Pred_Humidity:.1f} g/kg, "
            f"Pressure {row.Pred_Pressure:.1f} hPa, Wind {row.Pred_Wind:.1f} m/s — {row.description}")

    # === Visualization ===
    out_dir = "./result/temperature/"
    os.makedirs(out_dir, exist_ok=True)

    # 1) Temperature (°C)
    plt.figure(figsize=(12,6))
    plt.plot(df['date'], df['T2M'], 'gray', alpha=0.5, label='Observed Temp (°C)')
    plt.plot(forecast_df['date'], forecast_df['Pred_Temp'], 'r--o', label='Predicted Temp')
    plt.title("Predicted Monthly Temperature (2025/10–2026/05)")
    plt.ylabel("Temperature (°C)")
    plt.xlabel("Date")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    temp_series_path = os.path.join(out_dir, "forecast_series.png")
    plt.savefig(temp_series_path, dpi=150, bbox_inches="tight")
    plt.close()

    # 2) Humidity (QV2M, g/kg)
    out_dir = "./result/humidity/"
    plt.figure(figsize=(12,6))
    plt.plot(df['date'], df['QV2M'], 'gray', alpha=0.5, label='Observed Humidity (g/kg)')
    plt.plot(forecast_df['date'], forecast_df['Pred_Humidity'], 'r--o', label='Predicted Humidity')
    plt.title("Predicted Monthly Humidity (2025/10–2026/05)")
    plt.ylabel("Specific Humidity (g/kg)")
    plt.xlabel("Date")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    humid_series_path = os.path.join(out_dir, "forecast_series.png")
    plt.savefig(humid_series_path, dpi=150, bbox_inches="tight")
    plt.close()

    # 3) Wind (m/s)
    out_dir = "./result/windspeed/"
    plt.figure(figsize=(12,6))
    plt.plot(df['date'], df['WIND'], 'gray', alpha=0.5, label='Observed Wind (m/s)')
    plt.plot(forecast_df['date'], forecast_df['Pred_Wind'], 'r--o', label='Predicted Wind')
    plt.title("Predicted Monthly Wind Speed (2025/10–2026/05)")
    plt.ylabel("Wind Speed (m/s)")
    plt.xlabel("Date")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    wind_series_path = os.path.join(out_dir, "forecast_series.png")
    plt.savefig(wind_series_path, dpi=150, bbox_inches="tight")
    plt.close()

    return forecast_df.iloc[0]['Pred_Temp'], forecast_df.iloc[0]['Pred_Humidity'], forecast_df.iloc[0]['Pred_Wind'], forecast_df.iloc[0]['description']