# trm_cloud/scrape.py
import csv
import time
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://trendurunlermarket.com"  # alan adın buysa bırak; değilse düzelt

# --- Yalnızca şunları değiştirmen gerekebilir (site HTML'ine göre) ---
PRODUCT_CARD_SEL = ".product-card, .product, .woocommerce ul.products li.product"
TITLE_SEL        = ".product-title, .woocommerce-loop-product__title, h3, h2"
PRICE_SEL        = ".price, .woocommerce-Price-amount, .amount"
LINK_IN_CARD_SEL = "a"
# ---------------------------------------------------------------------

OUT_CSV = Path("TRM_PRODUCTS.csv")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0 Safari/537.36"
}

def clean_text(x: str) -> str:
    return " ".join((x or "").replace("\xa0", " ").strip().split())

def parse_price(text: str) -> str:
    # Rakamları ve ayraçları koru, simgeleri at
    if not text:
        return ""
    keep = []
    for ch in text:
        if ch.isdigit() or ch in ",.":
            keep.append(ch)
    s = "".join(keep)
    # virgül-nokta normalize etmeye çalışma; CSV'ye string olarak yaz
    return s

def fetch(url: str) -> BeautifulSoup:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return BeautifulSoup(r.text, "lxml")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.2)
    raise RuntimeError("fetch failed")

def extract_products_from_page(soup: BeautifulSoup):
    items = []
    cards = soup.select(PRODUCT_CARD_SEL)
    for c in cards:
        # başlık
        title_el = c.select_one(TITLE_SEL)
        title = clean_text(title_el.get_text()) if title_el else ""

        # fiyat
        price_el = c.select_one(PRICE_SEL)
        price = parse_price(price_el.get_text()) if price_el else ""

        # link
        a = c.select_one(LINK_IN_CARD_SEL)
        href = a.get("href") if a else ""
        if href and href.startswith("/"):
            href = BASE_URL.rstrip("/") + href

        if title and href:
            items.append({
                "name": title,
                "price": price,
                "url": href
            })
    return items

def find_pagination_links(soup: BeautifulSoup):
    # Basit: rel="next" ya da sayfa numaraları
    next_links = []
    next_a = soup.find("a", rel="next")
    if next_a and next_a.get("href"):
        next_links.append(next_a["href"])
    # Alternatif: .pagination içindeki <a>
    for a in soup.select(".pagination a, .page-numbers a"):
        href = a.get("href")
        if href:
            next_links.append(href)
    # uniq ve sırala
    seen = set()
    uniq = []
    for u in next_links:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq

def crawl_listing(start_urls, max_pages=10):
    collected = []
    to_visit = list(start_urls)
    visited = set()
    while to_visit and len(collected) < 500 and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        soup = fetch(url)
        collected.extend(extract_products_from_page(soup))
        # sayfalama
        for nxt in find_pagination_links(soup):
            if nxt not in visited and nxt not in to_visit and len(visited) + len(to_visit) < max_pages:
                if nxt.startswith("/"):
                    nxt = BASE_URL.rstrip("/") + nxt
                to_visit.append(nxt)
    return collected

def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "price", "url"])
        w.writeheader()
        for r in rows:
            w.writerow({"name": r["name"], "price": r["price"], "url": r["url"]})

def main():
    # Başlangıç: ana sayfa ve muhtemel “/shop/”, “/urunler/” vb.
    start = [
        f"{BASE_URL}/",
        f"{BASE_URL}/shop/",
        f"{BASE_URL}/urunler/",
    ]
    try:
        products = crawl_listing(start_urls=start, max_pages=12)
        if not products:
            print("Uyarı: Ürün bulunamadı; seçicileri (selectors) kontrol et.")
        write_csv(products, OUT_CSV)
        print(f"OK: {len(products)} ürün yazıldı -> {OUT_CSV}")
    except Exception as e:
        print("SCRAPE HATA:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
