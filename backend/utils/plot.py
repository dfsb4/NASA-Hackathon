import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import xarray as xr
import os

def plot_monthly_variable(month, years, values, var_name, unit):
    os.makedirs(f"./result/{var_name}", exist_ok=True)
    df = pd.DataFrame({
        "year": years,
        var_name: values
    })
    
    plt.figure(figsize=(8,5))
    
    if var_name in ["precipitation"]:
        plt.bar(df["year"], df[var_name], color="skyblue")
    else:
        plt.plot(df["year"], df[var_name], marker='o', linewidth=2,
                 color={'temperature':'orange','humidity':'teal','windspeed':'purple'}.get(var_name,'gray'))
        plt.scatter(df["year"], df[var_name], s=60)
    
    plt.title(f"{month} {var_name.replace('_',' ').title()} ({years[0]}–{years[-1]})")
    plt.xlabel("Year")
    plt.ylabel(f"{var_name.replace('_',' ').title()} ({unit})")
    plt.xticks(df["year"])
    plt.tight_layout()
    plt.savefig(f"./result/{var_name}/{month}_{var_name}.png")
    plt.close()

def plot_all(month, lat, lon):
    years = [2022, 2023, 2024]
    month = month
    lat = lat
    lon = lon
    out_paths = []

    preciplist = []
    for year in years:
        path = f"./data/precipitation/{year}/{month}/3B-MO.MS.MRG.3IMERG.{year}{month}01-S000000-E235959.{month}.V07B.HDF5"
        ds = xr.open_dataset(
            path,
            engine="h5netcdf",
            group="Grid"
        )
        ds = xr.open_dataset(path, engine="h5netcdf", group="Grid")
        da = ds["precipitation"] 
        if "time" in da.dims:
            da = da.isel(time=0)          

        value = float(da.sel(lat=lat, lon=lon, method="nearest").values)
        preciplist.append(value)
        # print(f"{year}-{month} mean precipitation: {value:.6f} mm/hr")
    plot_monthly_variable(month, years, preciplist, "precipitation", "mm")
    out_paths.append(f"/result/precipitation/{month}_precipitation.png")

    
    temperaturelist = []
    humiditylist = []
    windspeedlist = []
    for year in years:
        path_400 = f"./data/temperature/{year}/{month}/MERRA2_400.tavgM_2d_slv_Nx.{year}{month}.nc4"
        path_401 = f"./data/temperature/{year}/{month}/MERRA2_401.tavgM_2d_slv_Nx.{year}{month}.nc4"

        if os.path.exists(path_400):
            path = path_400
        elif os.path.exists(path_401):
            path = path_401
        else:
            continue
        ds = xr.open_dataset(
            path,
            engine="netcdf4"
        )
        # temperature
        t2m = ds["T2M"].isel(time=0) - 273.15 
        if "time" in t2m.dims:
            t2m = t2m.isel(time=0)
        value = float(t2m.sel(lat=lat, lon=lon, method="nearest").values)
        temperaturelist.append(value)
        # print(f"{year}-{month} mean temperature: {value:.6f} °C")
        out_paths.append(f"/result/temperature/{month}_temperature.png")

        # humidity
        T = ds["T2M"] - 273.15
        Td = ds["T2MDEW"] - 273.15
        def es(t_c):
            return 6.112 * np.exp((17.67 * t_c) / (t_c + 243.5))
        RH2m = 100.0 * (es(Td) / es(T))
        rh_val = float(RH2m.sel(lat=lat, lon=lon, method="nearest"))
        humiditylist.append(rh_val)
        # print(f"{year}-{month} mean humidity: {rh_val:.6f} %")
        out_paths.append(f"/result/humidity/{month}_humidity.png")

        # windspeed
        u2, v2 = ds["U2M"].isel(time=0), ds["V2M"].isel(time=0)
        ws2 = np.sqrt(u2**2 + v2**2)
        ws_val = float(ws2.sel(lat=lat, lon=lon, method="nearest").values)
        windspeedlist.append(ws_val)
        # print(f"{year}-{month} mean windspeed: {ws_val:.6f} m/s")
        out_paths.append(f"/result/windspeed/{month}_windspeed.png")
    plot_monthly_variable(month, years, temperaturelist, "temperature", "°C")
    plot_monthly_variable(month, years, humiditylist, "humidity", "%")
    plot_monthly_variable(month, years, windspeedlist, "windspeed", "m/s")

    
    airqualitylist = []
    for year in years:
        path_400 = f"./data/air_quality/{year}/{month}/MERRA2_400.tavgM_2d_aer_Nx.{year}{month}.nc4"
        path_401 = f"./data/air_quality/{year}/{month}/MERRA2_401.tavgM_2d_aer_Nx.{year}{month}.nc4"

        if os.path.exists(path_400):
            path = path_400
        elif os.path.exists(path_401):
            path = path_401
        else:
            continue

        ds = xr.open_dataset(
            path,
            engine="netcdf4"
        )
        pm25 = (ds["BCSMASS"] + ds["OCSMASS"] + 1.375*ds["SO4SMASS"]
            + ds["DUSMASS25"] + ds["SSSMASS25"]) * 1e9

        if "time" in pm25.dims:
            pm25 = pm25.isel(time=0)

        value = float(pm25.sel(lat=lat, lon=lon, method="nearest").values)
        airqualitylist.append(value)
        print(f"{year}-{month} mean air quality (PM2.5): {value:.6f} μg/m³")
    plot_monthly_variable(month, years, airqualitylist, "air_quality", "μg/m³")
    out_paths.append(f"/result/air_quality/{month}_air_quality.png")
    return out_paths