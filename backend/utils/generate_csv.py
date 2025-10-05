import os
import netCDF4 as nc
import numpy as np
import pandas as pd

def generate_monthly_csv(lat: float, lon: float) -> pd.DataFrame:
    YEAR_FROM, YEAR_TO = 2020, 2025

    rows = {}
    def ensure_row(y, m):
        key = (y, m)
        if key not in rows:
            rows[key] = {
                "year/month": f"{y:04d}/{m:02d}",
                "lat": float(lat), "lon": float(lon),
                "per": np.nan, "tem": np.nan, "hum": np.nan, "wind": np.nan, "pm25": np.nan
            }
        return rows[key]

    # ---------- 1) Precipitation (IMERG, HDF5) ----------
    precip_dir = "./data/precipitation/"
    for y in range(YEAR_FROM, YEAR_TO + 1):
        for m in range(1, 13):
            if y == 2025 and m > 5:
                break
            fname = f"{y}/{m:02d}/3B-MO.MS.MRG.3IMERG.{y}{m:02d}01-S000000-E235959.{m:02d}.V07B.HDF5"
            fpath = os.path.join(precip_dir, fname)
            if not os.path.exists(fpath):
                continue
            try:
                ds = nc.Dataset(fpath)
                grp = ds.groups["Grid"]
                lat_arr = grp["lat"][:]
                lon_arr = grp["lon"][:]
                li = int(np.abs(lat_arr - lat).argmin())
                xi = int(np.abs(lon_arr - lon).argmin())
                per = float(grp["precipitation"][0, xi, li])  # mm/h
            finally:
                ds.close()
            ensure_row(y, m)["per"] = per
    # ---------- 2) Temperature, Humidity, Wind (MERRA-2 SLV) ----------
    slv_dir = "../data/temperature/"
    for y in range(YEAR_FROM, YEAR_TO + 1):
        for m in range(1, 13):
            if y == 2025 and m > 5:
                break
            fname = f"{y}/{m:02d}/MERRA2_400.tavgM_2d_slv_Nx.{y}{m:02d}.nc4"
            fname2 = f"{y}/{m:02d}/MERRA2_401.tavgM_2d_slv_Nx.{y}{m:02d}.nc4"
            fpath = os.path.join(slv_dir, fname)
            if not os.path.exists(fpath):
                fpath = os.path.join(slv_dir, fname2)
                if not os.path.exists(fpath):
                    continue
        
            try:
                ds = nc.Dataset(fpath)
                lat_arr = ds["lat"][:]
                lon_arr = ds["lon"][:]
                li = int(np.abs(lat_arr - lat).argmin())
                xi = int(np.abs(lon_arr - lon).argmin())

                t2m  = float(ds["T2M"][0, li, xi]) - 273.15         # °C
                qv2m = float(ds["QV2M"][0, li, xi]) * 1000.0        # g/kg
                u10  = float(ds["U10M"][0, li, xi])
                v10  = float(ds["V10M"][0, li, xi])
                wind = float(np.sqrt(u10**2 + v10**2))              # m/s
            finally:
                ds.close()
            row = ensure_row(y, m)
            row["tem"]  = t2m
            row["hum"]  = qv2m
            row["wind"] = wind

    # ---------- 3) PM2.5 (MERRA-2 AER) ----------
    aer_dir = "../data/air_quality/"
    for y in range(YEAR_FROM, YEAR_TO + 1):
        for m in range(1, 13):
            fname1 = f"{y}/{m:02d}/MERRA2_400.tavgM_2d_aer_Nx.{y}{m:02d}.nc4"
            fname2 = f"{y}/{m:02d}/MERRA2_401.tavgM_2d_aer_Nx.{y}{m:02d}.nc4"
            fpath = os.path.join(aer_dir, fname1)
            if not os.path.exists(fpath):
                fpath = os.path.join(aer_dir, fname2)
                if not os.path.exists(fpath):
                    continue
            try:
                ds = nc.Dataset(fpath)
                lat_arr = ds["lat"][:]
                lon_arr = ds["lon"][:]
                li = int(np.abs(lat_arr - lat).argmin())
                xi = int(np.abs(lon_arr - lon).argmin())

                bc   = float(ds["BCSMASS"][0, li, xi])     # kg/m^3
                oc   = float(ds["OCSMASS"][0, li, xi])
                so4  = float(ds["SO4SMASS"][0, li, xi])
                dust = float(ds["DUSMASS25"][0, li, xi])
                sea  = float(ds["SSSMASS25"][0, li, xi])
            finally:
                ds.close()
            pm25 = (bc + oc + 1.375*so4 + dust + sea) * 1e9  # µg/m³
            ensure_row(y, m)["pm25"] = pm25

    if not rows:
        return pd.DataFrame(columns=["year/month","lat","lon","per","tem","hum","wind","pm25"])

    df = pd.DataFrame([rows[k] for k in sorted(rows.keys())])

    def ym_key(s: str):
        y, m = s.split("/")
        return (int(y), int(m))
    df = df.sort_values(by="year/month", key=lambda s: s.map(ym_key)).reset_index(drop=True)

    df = df[["year/month","lat","lon","per","tem","hum","wind","pm25"]]
    return df

if __name__ == "__main__":
    df = generate_monthly_csv(25.04, 121.56)
    os.makedirs("../result/csv", exist_ok=True)
    df.to_csv("../result/csv/history_25.04_121.56.csv", index=False)