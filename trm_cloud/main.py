import csv
from pathlib import Path

import pandas as pd

PROD_CSV = Path("TRM_PRODUCTS.csv")
REPORT_CSV = Path("TRM_REPORT_PRETTY.csv")

DEFAULT_ROWS = [
    {"name": "Acer X A", "price": 199.90, "url": "https://example.com/a"},
    {"name": "Acer B",   "price":  89.90, "url": "https://example.com/b"},
    {"name": "Acer C",   "price": 349.00, "url": "https://example.com/c"},
    {"name": "Acer D",   "price":  59.90, "url": "https://example.com/d"},
    {"name": "Acer E",   "price": 129.02, "url": "https://example.com/e"},
]

def read_products() -> pd.DataFrame:
    if PROD_CSV.exists():
        df = pd.read_csv(PROD_CSV)
    else:
        df = pd.DataFrame(DEFAULT_ROWS)

    # fiyatı normalize et
    def norm_price(v):
        if pd.isna(v):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).lower().replace("tl", "").replace("₺", "").strip()
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except Exception:
            return None

    df["price"] = df["price"].apply(norm_price)
    return df

def main():
    df = read_products()

    if "name" not in df.columns:
        df["name"] = ""

    df["commission"] = 18.0
    df["estimated_commission_try"] = (df["price"].fillna(0) * df["commission"] / 100).round(2)

    # sku üret
    df = df.reset_index(drop=True)
    df["sku"] = df.index.map(lambda i: f"SKU-{chr(65 + (i % 26))}")

    out = df[["sku", "name", "price", "commission", "estimated_commission_try"]]
    out.to_csv(REPORT_CSV, index=False, encoding="utf-8")
    print("RAPOR:", REPORT_CSV.name, "hazır.")

if __name__ == "__main__":
    main()
