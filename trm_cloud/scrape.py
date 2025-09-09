# -*- coding: utf-8 -*-
"""
Trend Ürünler Market kategori sayfalarından ürün adı, fiyat ve ürün URL'lerini çeker.
- KATEGORI_URLLERI listesine birebir tarayıcıdan kopyaladığın kategori linklerini koy.
- Site yapısı Opencart/benzeri ise aşağıdaki seçiciler çalışır; olmazsa alternatiflere düşer.
"""

import csv
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# >>> BURAYA KENDİ KATEGORİ LİNKLERİNİ YAPIŞTIR <<<
KATEGORI_URLLERI = [
    "https://www.trendurunlermarket.com/giyim-C4/",
    "https://www.trendurunlermarket.com/otomotiv-C13/",
    "https://www.trendurunlermarket.com/hobi-kitap-C11/",
    "https://www.trendurunlermarket.com/mucevher-saat-C7/",
]
# --------------------------------------------------

# Çıkış dosyası
OUT_DIR = Path("trm_reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "TRM_PRODUCTS.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}

# Farklı tema olasılıkları için birden fazla seçici dene
SELECTOR_KUME = [
    # Opencart klasik
    {"kutu": ".product-layout .product-thumb",
     "ad": ".caption h4 a, h4 a",
     "fiyat": ".price"},
    # Alternatif grid
    {"kutu": ".product-grid .product-thumb, .product-item",
     "ad": ".product-name a, .title a, .name a",
     "fiyat": ".price, .product-price"},
    # Prestashop/benzeri
    {"kutu": ".product-miniature",
     "ad": ".product-title a",
     "fiyat": ".price"}
]

def temiz_fiyat(text: str) -> str:
    if not text:
        return ""
    t = " ".join(text.split())
    # virgül/nokta karışıklığına girmeden ham metni dön
    return t

def parse_sayfa(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 404:
        raise RuntimeError(f"SCRAPE HATA: 404 Not Found: {url}")
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def urunleri_cikar(soup: BeautifulSoup, base: str):
    for sel in SELECTOR_KUME:
        kartlar = soup.select(sel["kutu"])
        if kartlar:
            for k in kartlar:
                a = k.select_one(sel["ad"])
                f = k.select_one(sel["fiyat"])
                ad = (a.get_text(strip=True) if a else "").strip()
                href = a.get("href") if a and a.has_attr("href") else ""
                link = urljoin(base, href) if href else ""
                fiyat = temiz_fiyat(f.get_text() if f else "")
                if ad and link:
                    yield {"name": ad, "price": fiyat, "url": link}
            return  # bu seçici setiyle bulduysak diğerlerine bakmaya gerek yok

def sonraki_sayfa_linki(soup: BeautifulSoup, base: str):
    # ">" veya rel="next" olan linkleri dene
    nxt = soup.select_one("ul.pagination li.active + li a, a[rel=next]")
    if not nxt:
        # bazı temalarda son sayfa linki .next ile
        nxt = soup.select_one(".pagination .next a, .results .next a")
    if nxt and nxt.get("href"):
        return urljoin(base, nxt["href"])
    return None

def tarat(kategori_url: str):
    base = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(kategori_url))
    url = kategori_url
    sayac = 1
    while url:
        print(f"[SCRAPE] {url}")
        soup = parse_sayfa(url)
        for u in urunleri_cikar(soup, base):
            yield u
        url = sonraki_sayfa_linki(soup, base)
        sayac += 1
        if sayac > 50:  # sonsuz döngü güvenliği
            break
        time.sleep(0.8)  # nazik olalım

def main():
    tum = []
    for kat in KATEGORI_URLLERI:
        try:
            for ur in tarat(kat):
                tum.append(ur)
        except Exception as e:
            print(f"[SCRAPE UYARI] {kat} -> {e}")

    # Dosyaya yaz
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "price", "url"])
        w.writeheader()
        for row in tum:
            w.writerow(row)

    print(f"[OK] {len(tum)} ürün yazıldı: {OUT_CSV}")

if __name__ == "__main__":
    main()
