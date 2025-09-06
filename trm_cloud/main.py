import csv
from pathlib import Path

def safe_float(x):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return 0.0

def main():
    csv_file = Path("TRM_REPORT_PRETTY.csv")
    out_dir = Path("trm_reports")
    out_dir.mkdir(exist_ok=True)

    out_path = out_dir / "summary.txt"
    with open(out_path, "w", encoding="utf-8") as out:
        if not csv_file.exists():
            msg = "❌ TRM_REPORT_PRETTY.csv bulunamadı. Lütfen repo köküne ekleyin."
            print(msg); out.write(msg + "\n")
            return

        print("✅ TRM_REPORT_PRETTY.csv bulundu, işleniyor...\n")
        out.write("✅ TRM_REPORT_PRETTY.csv bulundu, işleniyor...\n\n")

        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"Toplam satır: {len(rows)}")
        out.write(f"Toplam satır: {len(rows)}\n")

        total_est = 0.0
        shown = 0
        for r in rows[:5]:
            sku = r.get("sku") or r.get("sku_name") or r.get("SKU") or ""
            name = r.get("name") or r.get("urun") or r.get("Ürün") or ""
            price = safe_float(r.get("price"))
            comm = safe_float(r.get("commission"))
            est = price * comm if price and comm else safe_float(r.get("estimated_commission_try"))
            total_est += est
            shown += 1
            line = f"- {sku} {name} | fiyat: {price:.2f} | komisyon: {comm:.2%} | tahmini: {est:.2f}"
            print(line); out.write(line + "\n")

        print(f"\nToplam tahmini komisyon (ilk {shown} satır): {total_est:.2f}")
        out.write(f"\nToplam tahmini komisyon (ilk {shown} satır): {total_est:.2f}\n")

if __name__ == "__main__":
    main()

    except Exception as e:
        print(f"Fiyatları işlerken hata: {e}")

if __name__ == "__main__":
    main()
