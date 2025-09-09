import re
import time
import json
import math
import html
import random
import string
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode

BASE = "https://trendurunlermarket.com/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

TIMEOUT = 20

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    return r

def clean_text(t):
    if not t:
        return ""
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def extract_price(txt):
    if not txt:
        return ""
    # 12.345,67 ₺  veya 12,34 TL gibi
    txt = txt.replace("\xa0", " ")
    m = re.search(r"([\d\.\,]+)", txt)
    if not m:
        return clean_text(txt)
    val = m.group(1)
    # Türkçe biçimi: 12.345,67 -> 12345.67
    val = val.replace(".", "").replace(",", ".")
    try:
        return float(val)
    except:
        return clean_text(txt)

def discover_category_links():
    """Ana sayfadan ve görünen kategori sayfalarından tüm kategori/alt kategori linklerini çıkarır."""
    found = set()

    def collect_from_html(page_url, html_text):
        soup = BeautifulSoup(html_text, "lxml")
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            href = urljoin(page_url, href)
            # Aynı domain
            if urlparse(href).netloc and urlparse(href).netloc not in urlparse(BASE).netloc:
                continue
            # Kategori linklerini yakalamak için pragmatik filtreler:
            if re.search(r"/(kategori|category|cat|C\d+|/c/)", href, re.I) or re.search(r"-C\d+\b", href):
                found.add(href.split("#")[0])

    # 1) Ana sayfa
    r = get(BASE)
    if r.status_code == 200:
        collect_from_html(BASE, r.text)
    else:
        print(f"[WARN] Ana sayfa {r.status_code}")

    # 2) Ana menüde görünen üst başlıklar (hard-fallback)
    seed_fallbacks = [
        "giyim-C4", "otomotiv-C13", "hobi-kitap-C11", "spor-outdoor-C5",
        "mucevher-saat-C6", "kozmetik-bakim-C8", "anne-bebek-C10",
        "ev-yasam-C12", "elektronik-C7", "firsatlar-C9"
    ]
    for slug in seed_fallbacks:
        found.add(urljoin(BASE, slug))

    # 3) Bulunan kategori sayfalarının içinden de alt kategorileri çek
    snapshot = list(found)
    for link in snapshot:
        try:
            r = get(link)
            if r.status_code != 200:
                continue
            collect_from_html(link, r.text)
        except Exception as e:
            print(f"[WARN] {link} alınamadı: {e}")

    # Normalize & temizle
    clean = set()
    for u in found:
        # query’siz
        p = urlparse(u)
        u2 = urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
        clean.add(u2)

    lst = sorted(clean)
    print(f"[INFO] {len(lst)} kategori/alt kategori linki bulundu.")
    return lst

def iter_pages(category_url, first_html):
    """Basit sayfalama arayıcı: ?page=, &page= veya sayfalama linkleri."""
    yield category_url, first_html

    soup = BeautifulSoup(first_html, "lxml")
    # 1) Sayfalama linklerinden max sayfa bul
    pages = set()
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        if "page=" in href:
            full = urljoin(category_url, href)
            pages.add(full)

    # 2) Eğer hiç link bulamazsak klasik ?page=2,3… deneyelim (en fazla 10)
    if not pages:
        for i in range(2, 11):
            # varsa zaten çalışır, yoksa 404 döner keseriz
            if "page=" in category_url:
                break
            sep = "&" if "?" in category_url else "?"
            pages.add(f"{category_url}{sep}page={i}")

    # Bu sayfalara git
    for url in sorted(pages):
        r = get(url)
        if r.status_code != 200:
            break
        yield url, r.text

def parse_products(html_text, page_url):
    soup = BeautifulSoup(html_text, "lxml")
    products = []

    # Farklı tema olasılıklarına karşı birkaç seçici dene
    candidates = [
        ".product-item",
        ".productItem",
        ".product",
        "div[class*=product]",
        "li[class*=product]"
    ]
    boxes = []
    for sel in candidates:
        boxes = soup.select(sel)
        if len(boxes) >= 3:  # makul sayıda kutu bulduysa
            break
    if not boxes:
        boxes = soup.select("div,li")

    for box in boxes:
        # Ad adayları
        name_el = (
            box.select_one(".product-title")
            or box.select_one(".name")
            or box.select_one(".productName")
            or box.select_one("h3 a")
            or box.select_one("h2 a")
            or box.select_one("a[title]")
        )
        # Fiyat adayları
        price_el = (
            box.select_one(".price-new")
            or box.select_one(".new_price")
            or box.select_one(".price")
            or box.select_one('[class*="price"]')
        )

        name = clean_text(name_el.get_text()) if name_el else ""
        price_raw = clean_text(price_el.get_text()) if price_el else ""

        if not name or not price_raw:
            continue

        price = extract_price(price_raw)

        # Ürün linki
        link = ""
        if name_el and name_el.name == "a" and name_el.get("href"):
            link = urljoin(page_url, name_el.get("href"))
        else:
            a = box.select_one("a[href]")
            if a:
                link = urljoin(page_url, a.get("href"))

        products.append({
            "name": name,
            "price": price,
            "url": link if link else page_url
        })

    return products

def main():
    categories = discover_category_links()
    all_rows = []

    for ci, cat in enumerate(categories, 1):
        try:
            r = get(cat)
            if r.status_code != 200:
                print(f"[SKIP] {cat} -> HTTP {r.status_code}")
                continue

            for page_url, html_text in iter_pages(cat, r.text):
                rows = parse_products(html_text, page_url)
                if rows:
                    all_rows.extend(rows)
                # nazik olalım
                time.sleep(0.7)
        except Exception as e:
            print(f"[ERR] {cat}: {e}")

    if not all_rows:
        print("⚠️ Ürün çıkmadı.")
        return

    df = pd.DataFrame(all_rows).drop_duplicates()
    df.to_csv("TRM_PRODUCTS.csv", index=False, encoding="utf-8")
    print(f"✅ TRM_PRODUCTS.csv yazıldı. Toplam ürün: {len(df)}")

if __name__ == "__main__":
    main()
