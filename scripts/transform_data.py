"""
Description: ETL pipeline transforming raw Sociálna poisťovňa Excel sheets into Star Schema (Fact/Dim tables).
Prerequisites:
    - Directory structure: ROOT/data/raw (with source files), ROOT/data/processed, ROOT/logs
    - Third-party packages: pip install pandas openpyxl
"""

import os
import glob
import re
import unicodedata
import pandas as pd
from datetime import datetime

# Define unified metric and dimension mapping lookups
METRIC_MAP = {
    "priemerna vyska": "Avg_Amount", 
    "pocet vyplacanych": "Count_Paid", 
    "novopriznane": "Count_New"
}
MONTH_MAP = {
    "januar": 1, "februar": 2, "marec": 3, "april": 4, "maj": 5, "jun": 6,
    "jul": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "december": 12
}
PENSION_MAP = {
    "starobny": "Starobný dôchodok",
    "predcasny": "Predčasný starobný dôchodok",
    "invalidny do 70": "Invalidný dôchodok do 70 %",
    "invalidny nad 70": "Invalidný dôchodok nad 70 %",
    "vdovsky": "Vdovský dôchodok",
    "vdovecky": "Vdovecký dôchodok",
    "sirotsky": "Sirotský dôchodok"
}

# Normalize string by stripping diacritics and converting to lowercase
def clean_string(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    return "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)).lower().strip()

# Parse raw excel cell value into clean float
def parse_numeric(val) -> float:
    if pd.isna(val):
        return None
    clean_val = str(val).strip().replace(" ", "").replace(",", "")
    if clean_val in ["*", "-", "", "nan", "nan.1"]:
        return None
    try:
        return float(clean_val)
    except ValueError:
        return None

# Map localized raw column names to standardized dimension members
def resolve_pension_type(raw_name: str) -> str:
    norm = clean_string(raw_name)
    
    # Map invalidity pensions directly using lookups from PENSION_MAP
    if "invalidny" in norm:
        if "do 70" in norm or "30" in norm:
            return PENSION_MAP["invalidny do 70"]
        if "nad 70" in norm:
            return PENSION_MAP["invalidny nad 70"]
        return None
        
    # Scan keys from longest to shortest to prevent "starobny" from shadowing "predcasny"
    for key in sorted(PENSION_MAP.keys(), key=len, reverse=True):
        if key in norm:
            return PENSION_MAP[key]
            
    return None

# Run professional ETL pipeline converting raw Excel sheets to Star Schema
def sp_transform() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir) if os.path.basename(script_dir) == "scripts" else script_dir
    
    raw_dir = os.path.join(root_dir, "data", "raw")
    proc_dir = os.path.join(root_dir, "data", "processed")
    log_path = os.path.join(root_dir, "logs", "sp_transform.log")
    
    for folder in [raw_dir, proc_dir, os.path.dirname(log_path)]:
        os.makedirs(folder, exist_ok=True)

    def write_log(msg: str) -> None:
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
        print(line)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    write_log("=== START ETL TRANSFORMATION PIPELINE ===")
    source_files = glob.glob(os.path.join(raw_dir, "*.xlsx"))
    write_log(f"Found {len(source_files)} Excel files for extraction.")
    
    all_records = []

    for path in source_files:
        filename = os.path.basename(path)
        if filename.startswith("~$") or not (year_match := re.search(r"(\d{4})", filename)):
            continue
        year = int(year_match.group(1))
        write_log(f"Processing workbook: {filename} ({year})")
        
        try:
            excel_obj = pd.ExcelFile(path)
            for sheet in excel_obj.sheet_names:
                norm_sheet = clean_string(sheet)
                metric_code = next((code for kw, code in METRIC_MAP.items() if clean_string(kw) in norm_sheet), None)
                if not metric_code:
                    continue
                
                write_log(f"  Target sheet found: [{sheet}] -> {metric_code}")
                df_raw = pd.read_excel(excel_obj, sheet_name=sheet, header=None)
                
                # Dynamic anchor detection for standard months
                anchor_row, month_col = None, None
                for r_idx, row in df_raw.iterrows():
                    for c_idx, val in enumerate(row):
                        if pd.notna(val) and "januar" in clean_string(str(val)):
                            anchor_row, month_col = r_idx, c_idx
                            break
                    if anchor_row is not None:
                        break
                        
                if anchor_row is None:
                    continue

                # Unroll merged cells and combine multi-tier headers
                h_main = df_raw.iloc[anchor_row - 2].copy().ffill()
                h_sub = df_raw.iloc[anchor_row - 1].copy()
                
                headers = []
                for c in range(df_raw.shape[1]):
                    m, s = str(h_main.iloc[c]).strip(), str(h_sub.iloc[c]).strip()
                    if m and s and not any(x in m.lower() or x in s.lower() for x in ["unnamed", "nan"]):
                        headers.append(f"{m} | {s}")
                    elif m and not any(x in m.lower() for x in ["unnamed", "nan"]):
                        headers.append(m)
                    else:
                        headers.append("Month_Column_Anchor")
                        
                df_raw.columns = headers
                df_data = df_raw.iloc[anchor_row:].copy()
                df_data.rename(columns={headers[month_col]: "Mesiac"}, inplace=True)
                
                # Unpivot wide structure into long format
                df_melt = df_data.melt(id_vars=["Mesiac"], var_name="Raw_Type", value_name="Value")
                df_melt["Month_Num"] = df_melt["Mesiac"].astype(str).apply(clean_string).map(MONTH_MAP)
                df_melt = df_melt.dropna(subset=["Month_Num"])
                
                # Filter aggregates and map dimension fields
                df_melt = df_melt[~df_melt["Raw_Type"].str.contains("celkom|spolu|úhrn|uhrn|z toho", case=False, na=False)]
                df_melt["Clean_Type"] = df_melt["Raw_Type"].apply(resolve_pension_type)
                df_melt = df_melt.dropna(subset=["Clean_Type"])
                
                if not df_melt.empty:
                    df_melt["Date"] = df_melt["Month_Num"].apply(lambda m: f"{year}-{int(m):02d}-01")
                    df_melt["Value"] = df_melt["Value"].apply(parse_numeric)
                    df_melt["Metric"] = metric_code
                    all_records.append(df_melt[["Date", "Clean_Type", "Metric", "Value"]])
                    
        except Exception as e:
            write_log(f"FATAL ERROR on file {filename}: {repr(e)}")

    if not all_records:
        write_log("FATAL ERROR: No staging data extracted. Termination.")
        return

    # Consolidate staging logs and build analytical Star Schema structures
    df_master = pd.concat(all_records, ignore_index=True)

    # 1. Dim_Pension_Type
    dim_pension = pd.DataFrame({"Pension_Type_Name": sorted(df_master["Clean_Type"].unique())})
    dim_pension.index = dim_pension.index + 1
    dim_pension = dim_pension.reset_index().rename(columns={"index": "Pension_Type_ID"})
    sort_mapping = {
        "Starobný dôchodok": 1,
        "Predčasný starobný dôchodok": 2
    }
    dim_pension["Pension_Sort_Order"] = dim_pension["Pension_Type_Name"].map(sort_mapping).fillna(3).astype(int)
    dim_pension.to_csv(os.path.join(proc_dir, "dim_pension_type.csv"), index=False, encoding="utf-8-sig")
    write_log(f"Saved dimension: dim_pension_type.csv ({len(dim_pension)} entries)")

    # 2. Fact_Pensions
    df_master = df_master.merge(dim_pension, left_on="Clean_Type", right_on="Pension_Type_Name", how="left")
    fact_pensions = df_master.pivot_table(
        index=["Date", "Pension_Type_ID"], columns="Metric", values="Value", aggfunc="first"
    ).reset_index()
    
    for col in ["Count_Paid", "Avg_Amount", "Count_New"]:
        if col not in fact_pensions.columns:
            fact_pensions[col] = None
            
    fact_pensions = fact_pensions[["Date", "Pension_Type_ID", "Count_Paid", "Avg_Amount", "Count_New"]]
    fact_pensions.to_csv(os.path.join(proc_dir, "fact_pensions.csv"), index=False, encoding="utf-8-sig")
    write_log(f"Saved fact table: fact_pensions.csv ({len(fact_pensions)} records)")

    # 3. Dim_Date
    dim_date = pd.DataFrame({"Date": pd.to_datetime(df_master["Date"].unique())}).sort_values("Date").reset_index(drop=True)
    dim_date["Year"] = dim_date["Date"].dt.year
    dim_date["Month_Num"] = dim_date["Date"].dt.month
    dim_date["Month_Name"] = dim_date["Date"].dt.strftime("%B")
    dim_date["Quarter"] = dim_date["Date"].dt.quarter
    dim_date["Year_Month"] = dim_date["Date"].dt.strftime("%Y-%m")
    dim_date.to_csv(os.path.join(proc_dir, "dim_date.csv"), index=False, encoding="utf-8-sig")
    
    write_log(f"Saved dimension: dim_date.csv ({len(dim_date)} dates)")
    write_log("=== ETL PIPELINE FINISHED SUCCESSFULLY ===")

if __name__ == "__main__":
    sp_transform()