import pandas as pd
from pathlib import Path

rows = [
    {"sku_name": "SKU-A", "price": 199.90, "commission": 18.0, "estimated_commission_try": 35.98},
    {"sku_name": "SKU-B", "price": 89.90,  "commission": 20.0, "estimated_commission_try": 17.98},
    {"sku_name": "SKU-C", "price": 349.00, "commission": 15.0, "estimated_commission_try": 52.35},
]

df = pd.DataFrame(rows)
Path("trm_reports").mkdir(parents=True, exist_ok=True)
df.to_csv("TRM_REPORT_PRETTY.csv", index=False, encoding="utf-8-sig")
df.to_csv("trm_reports/TRM_REPORT_PRETTY.csv", index=False, encoding="utf-8-sig")
print("TRM Cloud Automation başarıyla çalıştı ✅")

    except Exception as e:
        print(f"Fiyatları işlerken hata: {e}")

if __name__ == "__main__":
    main()
