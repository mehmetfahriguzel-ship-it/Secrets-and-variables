# trm_cloud/scrape.py
import os
import csv
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.trendurunlermarket.com"

# Denenecek sayfa yolları (hangi çalışırsa onu kullanacağız)
CANDIDATES = [
    "/",                 # ana sayfa
    "/shop",             # WooCommerce varsayılan
    "/magaza",           # TR tema kullananlar
    "/urunler",          # sık kullanılan
    "/store",            # bazı temalar
    "/products",         # bazı temalar
]

OUT_PATH = "TRM_PRODUCTS.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
}

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    return r

def pick_working_listing():
    """Aday yolları dene; 200 dönen ve içinde ürün linki sinyali olan ilk sayfayı seç."""
    for path in CANDIDATES:
        full = urljoin(BASE, path)
        try:
            r = fetch(full)
        except Exception as e:
            print(f"[SKIP] {full} -> req error: {e}")
            continue

        if r.status_code != 200:
            print(f"[SKIP] {full} -> HTTP {r.status_code}")
            continue

        soup = BeautifulSoup(r.text, "lxml")

        # Ürün bağlantısı için yaygın seçiciler
        product_links = soup.select(
            "a.woocommerce-LoopProduct-link, a.product.type-product, a[href*='/product/'], a[href*='/urun/'], a[href*='?product=']"
        )
        if product_links:
            print(f"[OK] Liste sayfası bulundu: {full}  (ürün sinyali tespit edildi)")
            return full, soup

        # Liste sinyali görülmediyse yine de bu sayfanın ürün kart seçicilerini deneriz:
        grid_cards = soup.select(".products .product, ul.products li.product, .product-grid .product")
        if grid_cards:
            print(f"[OK] Liste sayfası bulundu: {full}  (grid tespit edildi)")
            return full, soup

        print(f"[SKIP] {full} -> 200 ama ürün sinyali yok")

    return None, None

def parse_listing(soup, base_url):
    """Liste sayfasından ürün adı, fiyat ve linkleri çıkar."""
    items = []

    # En yaygın kart seçicileri
    cards = soup.select("ul.products li.product, .products .product, .product-grid .product")
    if not cards:
        # Alternatif: doğrudan link seçicileri
        links = soup.select("a.woocommerce-LoopProduct-link, a[href*='/product/'], a[href*='/urun/']")
        for a in links[:100]:
            name = (a.get_text(strip=True) or "")[:150]
            href = a.get("href") or ""
            if not href:
                continue
            url = href if href.startswith("http") else urljoin(base_url, href)
            # Fiyatı yakınındaki etiketlerden tahmin
            price_el = a.find_next(class_="price")
            price_text = price_el.get_text(" ", strip=True) if price_el else ""
            items.append((name, price_text, url))
        return items

    for card in cards[:100]:  # güvenlik için ilk 100
        # İsim
        name_el = card.select_one(".woocommerce-loop-product__title, .product-title, h2, h3")
        name = name_el.get_text(" ", strip=True)[:150] if name_el else ""

        # Link
        a = card.select_one("a.woocommerce-LoopProduct-link, a[href*='/product/'], a[href*='/urun/']")
        href = a.get("href") if a else ""
        url = href if href.startswith("http") else (urljoin(base_url, href) if href else "")

        # Fiyat
        price_el = card.select_one(".price, .woocommerce-Price-amount, .amount")
        price = price_el.get_text(" ", strip=True) if price_el else ""

        if name or url:
            items.append((name, price, url))

    return items

def main():
    listing_url, soup = pick_working_listing()
    if not soup:
        print(f"SCRAPE HATA: Uygun liste sayfası bulunamadı. Denenen yollar: {', '.join(CANDIDATES)}")
        sys.exit(1)

    items = parse_listing(soup, listing_url)

    if not items:
        print(f"SCRAPE UYARI: Ürün bulunamadı: {listing_url}")
        sys.exit(1)

    # CSV yaz
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "price", "url"])
        for row in items:
            w.writerow(row)

    print(f"SCRAPE OK: {len(items)} ürün → {OUT_PATH}")

if __name__ == "__main__":
    main()
