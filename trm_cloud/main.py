import pandas as pd
from pathlib import Path

INPUT_CSV = Path("trm_cloud/products.csv")
OUT_DIR = Path("trm_reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "TRM_REPORT_PRETTY.csv"

def load_products(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Kolon isimlerini normalize et
    df.columns = [c.strip().lower() for c in df.columns]
    expected = {"sku_name", "price_try", "commission"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Eksik kolon(lar): {', '.join(sorted(missing))}")
    return df

def compute_report(df: pd.DataFrame) -> pd.DataFrame:
    # Sayısal tipler
    df["price_try"] = pd.to_numeric(df["price_try"], errors="coerce").fillna(0)
    df["commission"] = pd.to_numeric(df["commission"], errors="coerce").fillna(0)

    df["estimated_commission_try"] = (df["price_try"] * df["commission"] / 100).round(2)
    # Sütun sırası
    return df[["sku_name", "price_try", "commission", "estimated_commission_try"]]

def main():
    df = load_products(INPUT_CSV)
    rep = compute_report(df)
    rep.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print("TRM Cloud Automation raporu üretildi ->", OUT_CSV)

if __name__ == "__main__":
    main()
