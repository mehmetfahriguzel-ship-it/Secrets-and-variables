# trm_cloud/scrape.py
# -*- coding: utf-8 -*-
import csv, re, time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path("TRM_PRODUCTS.csv")

# --- Sabitler ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
TIMEOUT = 20

# Bu liste, gönderdiğin kategori linklerinden derlendi (dokümandaki linkler).
CATEGORIES = [
    "https://www.trendurunlermarket.com/giyim-C4/",
    "https://www.trendurunlermarket.com/hobi--kitap-C11/",
    "https://www.trendurunlermarket.com/spor--outdoor-C10/",
    "https://www.trendurunlermarket.com/mucevher--saat-C9/",
    "https://www.trendurunlermarket.com/kozmetik--bakim-C8/",
    "https://www.trendurunlermarket.com/anne--bebek-C7/",
    "https://www.trendurunlermarket.com/ev--yasam-C6/",
    "https://www.trendurunlermarket.com/elektronik-C5/",
    # “Fırsatlar” sayfası ayrı yapıda; link yok demiştin, o yüzden eklemedim.
]

# --- Yardımcılar ---
_price_num = re.compile(r"[\d.,]+")

def clean_text(x: str) -> str:
    return re.sub(r"\s+", " ", x).strip()

def parse_price(txt: str) -> float | None:
    m = _price_num.search(txt.replace("\xa0", " "))
    if not m: 
        return None
    s = m.group(0).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return None

def extract_products(html: str, base_url: str) -> list[dict]:
    """
    Tema farklarına dayanıklı, esnek seçiciler.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1) En yaygın kutular
    cards = (
        soup.select(".product, .product-item, .product-card, li.product, .col-product")
        or soup.select("div[class*='product'] a[href*='-P']")  # bazı temalar
    )

    items = []
    seen = set()

    for card in cards:
        # Ürün linki
        a = card.select_one("a[href]") or card.find("a", href=True)
        url = (a["href"] if a else "").strip()
        if url and url.startswith("/"):
            url = base_url.rstrip("/") + url
        # İsim
        name_el = (
            card.select_one(".product-name, .name, .title, h3, h2, .productTitle")
            or (a if a and a.text.strip() else None)
        )
        name = clean_text(name_el.get_text()) if name_el else ""
        # Fiyat
        price_el = card.select_one(
            ".price, .product-price, .current, .new-price, .urunFiyat, [class*=price]"
        )
        price = parse_price(price_el.get_text()) if price_el else None

        # Filtrele
        key = (name, url)
        if name and url and key not in seen:
            seen.add(key)
            items.append({"name": name, "price": price, "url": url})

    return items

def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"SCRAPE HATA: HTTP {r.status_code} -> {url}")
    return r.text

def main():
    all_rows = []

    for cat in CATEGORIES:
        base = "https://www.trendurunlermarket.com"
        try:
            html = fetch(cat)
            rows = extract_products(html, base)
            # Boş gelirse sorun etmeyelim; site tema/HTML farklı olabilir
            if not rows:
                print(f"Uyarı: {cat} sayfasında ürün seçilemedi (tema farkı olabilir).")
            all_rows.extend(rows)
            time.sleep(1.0)
        except Exception as e:
            print(f"SCRAPE Uyarı: {e}")

    # En azından başlıkla birlikte kaydet
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "price", "url"])
        for r in all_rows:
            w.writerow([r["name"], ("" if r["price"] is None else r["price"]), r["url"]])

    print(f"TOPLAM KAYIT: {len(all_rows)} -> {OUT}")

if __name__ == "__main__":
    main()
