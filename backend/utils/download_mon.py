# fetch_imerg_monthly.py
import os
import sys
import time
import calendar
from typing import Tuple, Optional, List, Dict, Union
import numpy as np

import earthaccess
from dotenv import load_dotenv

# precipitation
SHORT_NAME = "GPM_3IMERGM"   # IMERG Monthly Final Run V07
VERSION    = "07"
BBOX       = (-180, -90, 180, 90)  # (min_lon, min_lat, max_lon, max_lat)
OUT_ROOT   = "../data/precipitation" 
SLEEP_BETWEEN_CALLS = 0.6  

TEMP_OUT_ROOT = "../data/temperature"
AIR_OUT_ROOT = "../data/air_quality"
def month_date_range(year: int, month: int) -> Tuple[str, str]:
    last_day = calendar.monthrange(year, month)[1]
    return (f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}")

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def already_downloaded(dirpath: str) -> bool:
    if not os.path.isdir(dirpath):
        return False
    for name in os.listdir(dirpath):
        if name.lower().endswith((".nc4", ".nc", ".hdf5", ".h5")):
            return True
    return False

def download_one_month(year: int, month: int,
                       short_name: str = SHORT_NAME,
                       version: str = VERSION,
                       bbox: Tuple[float, float, float, float] = BBOX,
                       out_root: str = OUT_ROOT) -> Optional[List[str]]:
    start, end = month_date_range(year, month)
    out_dir = os.path.join(out_root, f"{year:04d}", f"{month:02d}")
    ensure_dir(out_dir)

    if already_downloaded(out_dir):
        print(f"✅ [{year}-{month:02d}] has files skipping：{out_dir}")
        return None

    print(f"🔎 {short_name} v{version},  {start} ~ {end}，bbox={bbox}")
    try:
        results = earthaccess.search_data(
            short_name=short_name,
            version=version,
            temporal=(start, end),
            bounding_box=bbox
        )
    except Exception as e:
        return None

    if not results:
        print(f"⚠️  no data:{year}-{month:02d}")
        return None

    print(f"⬇️  prepare to download {len(results)} files → {out_dir}")
    try:
        files = earthaccess.download(results, local_path=out_dir)
        if files:
            print(f"finish {year}-{month:02d}：{len(files)} files")
        else:
            print(f"fail: {year}-{month:02d}")
        return files
    except Exception as e:
        print(f"fail: {e}")
        return None

def precipitation():
    load_dotenv()

    print("🔐 Earthdata loggin")
    earthaccess.login(strategy="environment")

    years = list(range(2020, 2025))
    months = list(range(1, 13))

    if len(sys.argv) == 3:
        y0, y1 = int(sys.argv[1]), int(sys.argv[2])
        years = list(range(y0, y1 + 1))


    for y in years:
        for m in months:
            download_one_month(y, m)
            time.sleep(SLEEP_BETWEEN_CALLS)

    print("finished")

# temperature
def temperature(dataset: str = "merra2_t2m"):
    load_dotenv()
    print("🔐 Earthdata login")
    earthaccess.login(strategy="environment")

    years = list(range(2020, 2025))
    months = list(range(1, 13))
    if len(sys.argv) == 4:
        y0, y1 = int(sys.argv[2]), int(sys.argv[3])
        years = list(range(y0, y1 + 1))

    if dataset == "merra2_t2m":
        short_name = "M2TMNXSLV"
        version = "5.12.4"
        out_root = TEMP_OUT_ROOT
        bbox = (-180, -90, 180, 90) 
    elif dataset == "merra2_aer":
        short_name = "M2TMNXAER"
        version = "5.12.4"
        out_root = AIR_OUT_ROOT
        bbox = (-180, -90, 180, 90)
    else:
        raise ValueError("fail")

    for y in years:
        for m in months:
            download_one_month(
                year=y, month=m,
                short_name=short_name,
                version=version,
                bbox=bbox,
                out_root=out_root
            )
            time.sleep(SLEEP_BETWEEN_CALLS)

    print("temperature download finished")
    
if __name__ == "__main__":
    # precipitation()
    temperature("merra2_t2m")
    # temperature("merra2_aer")