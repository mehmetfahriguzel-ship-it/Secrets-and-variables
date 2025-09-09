import re
import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.trendurunlermarket.com"
OUT_DIR = Path(".")
PROD_CSV = OUT_DIR / "TRM_PRODUCTS.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

# --------- yardımcılar ---------
def get(url: str) -> requests.Response:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r

def clean_text(s: str) -> str:
    return " ".join(s.split()).strip()

def parse_price(text: str) -> float | None:
    """
    '1.299,90 TL' -> 1299.90
    '1299.90'     -> 1299.90
    """
    if not text:
        return None
    t = text.lower().replace("tl", "").replace("₺", "").strip()
    t = t.replace(".", "").replace(",", ".")
    try:
        return float(re.findall(r"-?\d+(\.\d+)?", t)[0])
    except Exception:
        return None

# --------- kategori linklerini topla (otomatik) ---------
def discover_category_links() -> list[str]:
    links: set[str] = set()
    resp = get(BASE + "/")
    soup = BeautifulSoup(resp.text, "lxml")

    # Menüde kategori görünen tüm linkler: '-C<rakamlar>' kalıbı
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            url = href
        else:
            url = BASE + "/" + href.lstrip("/")

        if re.search(r"-C\d+/?$", url):
            links.add(url.rstrip("/") + "/")

    return sorted(links)

# --------- kategori sayfasından ürünleri çek ---------
def scrape_category(cat_url: str) -> list[dict]:
    items = []
    try:
        resp = get(cat_url)
    except requests.HTTPError as e:
        print(f"[SKIP] {cat_url} -> HTTP {e.response.status_code}")
        return items
    except Exception as e:
        print(f"[SKIP] {cat_url} -> {e}")
        return items

    soup = BeautifulSoup(resp.text, "lxml")

    # Muhtemel ürün kutuları (generic seçimler)
    candidates = []
    candidates += soup.select('[class*="product"] a[href]')
    candidates += soup.select('a[href*="/urun"]')
    candidates += soup.select('a[href*="-p-"]')
    candidates += soup.select('a[href*="/product"]')

    seen = set()
    for a in candidates:
        href = a.get("href", "")
        name = clean_text(a.get("title") or a.get_text() or "")
        if not name:
            continue

        if href.startswith("http"):
            url = href
        else:
            url = BASE + "/" + href.lstrip("/")

        key = (name, url)
        if key in seen:
            continue
        seen.add(key)

        # Fiyatı bul: aynı kartın içinde ya da yakınında
        price = None
        card = a.find_parent()
        for _ in range(4):
            if not card:
                break
            # sınıfında 'price' ya da 'fiyat' geçen her şeyi dene
            p_nodes = []
            p_nodes += card.select('[class*="price"]')
            p_nodes += card.select('[class*="fiyat"]')
            for p in p_nodes:
                price = parse_price(clean_text(p.get_text()))
                if price:
                    break
            if price:
                break
            card = card.find_parent()

        items.append({"name": name, "price": price, "url": url})

    return items

def main():
    cat_links = discover_category_links()
    if not cat_links:
        print("SCRAPE NOT: Kategori linki bulunamadı, ana sayfa yapısı değişmiş olabilir.")
        return

    all_rows = []
    for cat in cat_links:
        print(f"[CAT] {cat}")
        rows = scrape_category(cat)
        print(f"  -> {len(rows)} ürün")
        all_rows.extend(rows)

    # Boş gelirse yine de dosya oluştur
    with open(PROD_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "price", "url"])
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    print(f"SCRAPE OK: {PROD_CSV.name} yazıldı ({len(all_rows)} satır).")

if __name__ == "__main__":
    main()
