# fetch_imerg_monthly.py
import os
import sys
import time
import calendar
import shutil
from datetime import datetime
from typing import Tuple, Optional, List, Iterable

import earthaccess
from dotenv import load_dotenv

# === Dataset roots ===
OUT_ROOT       = "./data/precipitation"   # IMERG monthly
TEMP_OUT_ROOT  = "./data/temperature"     # MERRA2 SLV
AIR_OUT_ROOT   = "./data/air_quality"     # MERRA2 AER

# === IMERG monthly (precipitation) ===
SHORT_NAME = "GPM_3IMERGM"     # IMERG Monthly Final Run V07
VERSION    = "07"
BBOX       = (-180, -90, 180, 90)
SLEEP_BETWEEN_CALLS = 0.6

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

def download_one_month(year: int,
                       month: int,
                       short_name: str = SHORT_NAME,
                       version: str = VERSION,
                       bbox = BBOX,
                       out_root: str = OUT_ROOT) -> Optional[List[str]]:
    start, end = month_date_range(year, month)
    out_dir = os.path.join(out_root, f"{year:04d}", f"{month:02d}")
    ensure_dir(out_dir)

    if already_downloaded(out_dir):
        print(f"✅ [{year}-{month:02d}] 已存在檔案，跳過：{out_dir}")
        return None

    print(f"🔎 搜尋 {short_name} v{version}, 時間 {start} ~ {end}, bbox={bbox}")
    try:
        results = earthaccess.search_data(
            short_name=short_name,
            version=version,
            temporal=(start, end),
            bounding_box=bbox
        )
    except Exception as e:
        print(f"⚠️ search 失敗：{e}")
        return None

    if not results:
        print(f"⚠️ 無資料：{year}-{month:02d}")
        return None

    print(f"⬇️ 準備下載 {len(results)} 個檔案 → {out_dir}")
    try:
        files = earthaccess.download(results, local_path=out_dir)
        if files:
            print(f"✅ 完成 {year}-{month:02d}：{len(files)} 檔")
        else:
            print(f"⚠️ 下載結果為空：{year}-{month:02d}")
        return files
    except Exception as e:
        print(f"❌ 下載失敗：{e}")
        return None

# -------- dataset profiles (溫度 / 空氣品質) --------
def dataset_profile(kind: str):
    if kind == "precipitation":
        return ("GPM_3IMERGM", "07", (-180, -90, 180, 90), OUT_ROOT)
    if kind == "temperature":
        # MERRA-2 Monthly single-level diagnostics
        return ("M2TMNXSLV", "5.12.4", (-180, -90, 180, 90), TEMP_OUT_ROOT)
    if kind == "air_quality":
        # MERRA-2 Monthly aerosol diagnostics
        return ("M2TMNXAER", "5.12.4", (-180, -90, 180, 90), AIR_OUT_ROOT)
    raise ValueError("kind 必須是 precip | temp | air")

# -------- Five-year downloader (指定月份) --------
def download_month_across_years(kind: str, month: int):
    """
    給定月份，在連續五年下載（預設為 現在年份往回 4 年）
    可用 start_year 指定起點，例如 start_year=2020 → 2020..2024
    """
    if not (1 <= month <= 12):
        raise ValueError("month 必須是 1..12")

    load_dotenv()
    print("🔐 Earthdata login")
    earthaccess.login(strategy="environment")

    years = list(range(2020, 2025))

    short_name, version, bbox, out_root = dataset_profile(kind)

    print(f"▶️  任務：{kind}，月份 {month:02d}，年份 {years[0]}–{years[-1]}")
    for y in years:
        download_one_month(
            year=y, month=month,
            short_name=short_name,
            version=version,
            bbox=bbox,
            out_root=out_root
        )
        time.sleep(SLEEP_BETWEEN_CALLS)
    print("✅ 下載完成")

# -------- 安全刪除（指定月份 × 多個年份） --------
def _safe_rmtree(target_dir: str, allowed_roots: Iterable[str], dry_run: bool = False) -> None:
    target_abs = os.path.abspath(target_dir)
    allowed_abs = [os.path.abspath(r) for r in allowed_roots]

    if not os.path.isdir(target_abs):
        print(f"⚠️  不存在或不是資料夾：{target_dir}")
        return

    if target_abs in ("/", "C:\\", "D:\\"):
        raise ValueError(f"❌ 危險：拒絕刪除根目錄：{target_abs}")

    if not any(os.path.commonpath([target_abs, root]) == root for root in allowed_abs):
        raise ValueError(f"❌ 非允許範圍：{target_abs}\n允許：{allowed_abs}")

    if dry_run:
        print(f"🧪 (dry-run) 將刪除：{target_abs}")
        return

    shutil.rmtree(target_abs)
    print(f"🗑️  已刪除：{target_abs}")

def delete_month_across_years(kind: str, month: int,
                              start_year: Optional[int] = None,
                              years_count: int = 5,
                              dry_run: bool = False) -> None:
    if not (1 <= month <= 12):
        raise ValueError("month 必須是 1..12")

    years = list(range(2020, 2025))

    _, _, _, out_root = dataset_profile(kind)
    for y in years:
        month_dir = os.path.join(out_root, f"{y:04d}", f"{month:02d}")
        _safe_rmtree(month_dir, allowed_roots=[OUT_ROOT, TEMP_OUT_ROOT, AIR_OUT_ROOT], dry_run=dry_run)

    # 順手清掉變空的年份資料夾（可選）
    for y in years:
        year_dir = os.path.join(out_root, f"{y:04d}")
        if os.path.isdir(year_dir) and not os.listdir(year_dir):
            _safe_rmtree(year_dir, allowed_roots=[OUT_ROOT, TEMP_OUT_ROOT, AIR_OUT_ROOT], dry_run=dry_run)

# -------- CLI --------
def main_cli():
    import argparse
    p = argparse.ArgumentParser(description="Download / Delete monthly data across five years")
    sub = p.add_subparsers(dest="cmd")

    # fetch：指定月份＋資料類型；可指定起始年
    fetch = sub.add_parser("fetch", help="下載指定月份，連續五年")
    fetch.add_argument("kind", choices=["precipitation", "temperature", "air_quality"], help="資料類型")
    fetch.add_argument("month", type=int, help="月份 1-12")
    fetch.add_argument("--start-year", type=int, help="起始年（例如 2020 代表 2020..2024）")
    fetch.add_argument("--years", type=int, default=5, help="年數（預設 5）")

    # rm：刪除指定月份在連續五年的資料夾
    rm = sub.add_parser("rm", help="刪除指定月份（連續五年）的資料夾")
    rm.add_argument("kind", choices=["precip", "temp", "air"], help="資料類型")
    rm.add_argument("month", type=int, help="月份 1-12")
    rm.add_argument("--start-year", type=int, help="起始年（例如 2020 代表 2020..2024）")
    rm.add_argument("--years", type=int, default=5, help="年數（預設 5）")
    rm.add_argument("--dry-run", action="store_true", help="試跑不刪")

    args = p.parse_args()

    if args.cmd == "fetch":
        download_month_across_years(args.kind, args.month)
        return
    if args.cmd == "rm":
        delete_month_across_years(args.kind, args.month)
        return

    p.print_help()

if __name__ == "__main__":
    main_cli()
