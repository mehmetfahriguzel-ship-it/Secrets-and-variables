# trm_cloud/scrape.py
import csv, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# ---- Ayarlar ----
BASE = "https://trendurunler.com"
CATEGORIES = [
    "/kategori/telefon-aksesuarlari",
    "/kategori/oyun-aksesuarlari",
    "/kategori/ev-yasam",
]
OUT_DIR = Path("trm_reports"); OUT_DIR.mkdir(exist_ok=True)
OUT_CSV = OUT_DIR / "TRM_PRODUCTS.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
}

def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def parse_total_pages(soup: BeautifulSoup) -> int:
    # Sayfalama seçicileri: sitene göre otomatik denemeler
    pagers = soup.select("a.page, a.pagination, li.page a, ul.pagination li a")
    pages = []
    for a in pagers:
        t = (a.get_text(strip=True) or "").replace("…", "")
        if t.isdigit():
            pages.append(int(t))
    return max(pages) if pages else 1

def parse_list(soup: BeautifulSoup):
    # Ürün kartı seçicileri (genel)
    cards = soup.select(
        ".product-card, .product, li.product, div.product, .card.product, .product-item"
    )
    rows = []
    for c in cards:
        name_el  = c.select_one(".product-title, .name, h2, h3, .title")
        price_el = c.select_one(".price, .product-price, .amount, .current-price")
        link_el  = c.select_one("a[href]")
        name  = name_el.get_text(" ", strip=True) if name_el else ""
        price = price_el.get_text(" ", strip=True) if price_el else ""
        href  = link_el["href"] if link_el and link_el.has_attr("href") else ""
        if href.startswith("/"):
            href = BASE + href
        if name and href:
            rows.append({"name": name, "price": price, "url": href})
    return rows

def crawl_category(path: str):
    url = BASE + path
    soup = get_soup(url)
    total = parse_total_pages(soup)
    all_rows = []
    for page in range(1, total + 1):
        page_url = url if page == 1 else f"{url}?page={page}"
        psoup = get_soup(page_url)
        all_rows += parse_list(psoup)
        time.sleep(1.0)  # nazik ol
    return all_rows

def main():
    all_rows = []
    for cat in CATEGORIES:
        try:
            all_rows += crawl_category(cat)
        except Exception as e:
            print("Kategori hatası:", cat, e)

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "price", "url"])
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    print(f"OK | {len(all_rows)} ürün -> {OUT_CSV}")

if __name__ == "__main__":
    main()
