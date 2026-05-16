"""
Description: Resilient download pipeline for pension datasets from Sociálna poisťovňa.
Prerequisites:
    - Directory structure: ROOT/data/raw, ROOT/logs
    - Third-party packages: pip install requests
"""

import os
import requests
from datetime import datetime
from urllib.parse import quote

START_YEAR = 2020
BASE_URL = "https://www.socpoist.sk/sites/default/files"

# Ensure target directory exists
def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)

# Write timestamped log message to file
def log_event(log_path: str, message: str) -> None:
    ensure_directory(os.path.dirname(log_path))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")

# Return potential filenames including historical typo overrides
def get_filename_candidates(year: int) -> list:
    standard = f"Štatistické údaje z oblasti dôchodkového poistenia rok {year}.xlsx"
    if year == 2020:
        return ["Štatistické údaje z oblasti dôchodkového pistenia rok 2020.xlsx", standard]
    return [standard]

# Generate prioritized list of remote YYYY-MM directory paths
def get_folder_candidates(year: int) -> list:
    candidates = []
    curr_year, curr_month = datetime.now().year, datetime.now().month

    # Handle historical batch upload anomalies
    if year in [2020, 2021]:
        candidates.append("2022-10")

    # Add standard corporate publication release windows
    candidates.extend([f"{year + 1}-02", f"{year + 1}-01", f"{year}-12"])

    # Sweep backwards from latest calendar month to ensure progressive data capture
    end_sweep = min(year + 1, curr_year) if year < curr_year else curr_year
    for y in range(end_sweep, year - 1, -1):
        max_m = curr_month if y == curr_year else 12
        for m in range(max_m, 0, -1):
            folder_str = f"{y}-{m:02d}"
            if folder_str not in candidates:
                candidates.append(folder_str)
    return candidates

# Execute resilient download pipeline for pension datasets
def sp_download() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir) if os.path.basename(script_dir) == "scripts" else script_dir
    
    raw_dir = os.path.join(root_dir, "data", "raw")
    log_path = os.path.join(root_dir, "logs", "sp_download.log")
    ensure_directory(raw_dir)
    
    log_event(log_path, "=== START AUTOMATED DOWNLOAD PIPELINE ===")
    http_headers = {"User-Agent": "Mozilla/5.0 AssetPipeline/3.0"}
    max_year = datetime.now().year

    for year in range(START_YEAR, max_year + 1):
        log_event(log_path, f"Scanning options for Year: {year}")
        success = False
        
        # Grid search over potential folder and filename combinations
        for folder in get_folder_candidates(year):
            for filename in get_filename_candidates(year):
                url = f"{BASE_URL}/{folder}/{quote(filename)}"
                try:
                    # Verify asset presence with fast HTTP HEAD check
                    res = requests.head(url, timeout=10, headers=http_headers, allow_redirects=True)
                    if res.status_code == 200:
                        log_event(log_path, f"  Found endpoint: {url}")
                        
                        # Stream payload from validated endpoint
                        data_res = requests.get(url, timeout=45, headers=http_headers)
                        if data_res.status_code == 200:
                            out_name = f"socpoist_dochodky_{year}.xlsx"
                            with open(os.path.join(raw_dir, out_name), "wb") as out_file:
                                out_file.write(data_res.content)
                            
                            log_event(log_path, f"  Success saving: {out_name} using remote context [{folder}]")
                            success = True
                            break
                except Exception:
                    continue
            if success:
                break
                
        if not success:
            log_event(log_path, f"FATAL ERROR {year}: Target asset could not be located.")

    log_event(log_path, "=== END AUTOMATED DOWNLOAD PIPELINE ===")

if __name__ == "__main__":
    sp_download()