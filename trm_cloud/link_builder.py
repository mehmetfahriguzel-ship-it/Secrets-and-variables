# trm_cloud/link_builder.py
import urllib.parse
import csv
from pathlib import Path

INPUT = Path("trm_reports/TRM_PRODUCTS.csv")   # scrape.py’nin ürettiği ürün listesi
OUTPUT = Path("trm_reports/TRM_UTM_LINKS.csv")

def build_link(name: str, kanal="telegram", platform="bot"):
    # Ürün adını URL-encode yap
    q = urllib.parse.quote_plus(name)
    # UTM linkini oluştur
    return f"https://trendurunlermarket.com/?s={q}&utm_source={kanal}&utm_medium={platform}&utm_campaign=trm"

def main():
    if not INPUT.exists():
        print("Ürün listesi bulunamadı:", INPUT)
        return

    with INPUT.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out_rows = []
    for r in rows:
        name = r.get("name", "").strip()
        if not name:
            continue
        link = build_link(name, kanal="telegram", platform="bot")
        out_rows.append({
            "name": name,
            "price": r.get("price",""),
            "utm_link": link
        })

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name","price","utm_link"])
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)

    print(f"OK | {len(out_rows)} ürün için UTM linki üretildi → {OUTPUT}")

if __name__ == "__main__":
    main()
