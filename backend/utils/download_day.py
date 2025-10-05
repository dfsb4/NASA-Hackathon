import os
import calendar
import earthaccess
from dotenv import load_dotenv
import xarray as xr
import matplotlib
matplotlib.use("Agg")            # 改用無 GUI 後端
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

# === 登入 Earthdata ===
load_dotenv()
earthaccess.login(strategy="environment")

# === 逐月下載 MERRA-2 每日資料 ===
for month in range(7, 13):  # 1 到 12 月
    days_in_month = calendar.monthrange(2024, month)[1]  # 該月實際天數
    for day in range(1, days_in_month + 1):
        start_date = f"2024-{month:02d}-{day:02d}"
        end_date = start_date  # 同一天

        print(f"🔍 Searching for data on {start_date} ...")
        results = earthaccess.search_data(
            short_name="M2T1NXSLV",
            version="5.12.4",
            temporal=(start_date, end_date),
            bounding_box=(-180, 0, 180, 90)  # 北半球
        )

        if not results:
            print(f"⚠️ No data found for {start_date}")
            continue

        downloaded_files = earthaccess.download(
            results,
            local_path="../data/temperature/2024/day",
        )

        # 讀取 NetCDF 並檢查變數
        ds = xr.open_mfdataset(downloaded_files, engine="netcdf4", combine="by_coords")

        print("✅ Dataset loaded for", start_date)
        print("Variables:", list(ds.data_vars.keys()))

        # ============ 取出氣溫 (°C) ============
        if "T2M" in ds.data_vars:
            t2m = ds["T2M"].isel(time=0) - 273.15
            print(f"Mean temperature on {start_date}: {t2m.mean().values:.2f} °C")

        # ============ 如需畫圖可解開下列區塊 ============
        """
        fig = plt.figure(figsize=(12, 6))
        ax = plt.axes(projection=ccrs.PlateCarree())
        t2m.plot(
            ax=ax,
            transform=ccrs.PlateCarree(),
            cmap="coolwarm",
            cbar_kwargs={"label": "Temperature (°C)"}
        )
        ax.coastlines()
        ax.set_title(f"MERRA-2 T2M on {start_date}")
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, color="gray", alpha=0.5)
        gl.top_labels = False
        gl.right_labels = False
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        plt.savefig(f"./data/temperature/MERRA-2_T2M_{start_date}.png", dpi=300)
        plt.close()
        """
