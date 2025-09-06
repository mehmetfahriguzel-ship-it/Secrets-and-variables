import csv
from pathlib import Path

def main():
    # CSV dosyasının yolu
    csv_file = Path("TRM_REPORT_PRETTY.csv")

    if not csv_file.exists():
        print("❌ TRM_REPORT_PRETTY.csv bulunamadı.")
        return

    print("✅ TRM_REPORT_PRETTY.csv bulundu, işleniyor...\n")

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Toplam satır sayısı
    print(f"Toplam ürün sayısı: {len(rows)}")

    # İlk 3 ürünü gösterelim
    for row in rows[:3]:
        print(f"- {row['sku_name']} | Fiyat: {row['price']} | Komisyon: {row['commission']}")

    # Ortalama fiyat hesaplama
    try:
        prices = [float(row["price"]) for row in rows if row["price"]]
        avg_price = sum(prices) / len(prices) if prices else 0
        print(f"\nOrtalama fiyat: {avg_price:.2f} TL")
    except Exception as e:
        print(f"Fiyatları işlerken hata: {e}")

if __name__ == "__main__":
    main()
