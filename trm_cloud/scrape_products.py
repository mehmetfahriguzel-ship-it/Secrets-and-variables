# -*- coding: utf-8 -*-
"""
TRM - Trend Ürünler Market Scraper
----------------------------------
- Kategorileri categories.txt dosyasından okur (her satıra bir URL).
- Ürünleri toplar ve iki CSV üretir:
    * TRM_PRODUCTS.csv           (ham veri)
    * TRM_REPORT_PRETTY.csv      (Excel uyumlu rapor)
- CSV yazımı: encoding='utf-8-sig', sep=';'  (TR/Excel için)

Koşum şekli (GitHub Actions veya lokal):
    python trm_cloud/scrape_products.py
"""

import os
import re
import time
import csv
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import pandas as pd


# -------------------------------
# YAPILANDIRMA
# -------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_FILE = os.path.join(ROOT_DIR, "categories.txt")

OUT_RAW = os.path.join(ROOT_DIR, "TRM_PRODUCTS.csv")
OUT_PRETTY = os.path.join(ROOT_DIR, "TRM_REPORT_PRETTY.csv")

# HTTP ayarları
HDRS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT = 20
SLEEP_BETWEEN = 0.8  # istekler arasında bekleme (sn)


# -------------------------------
# SEÇİCİLER (esnek tutuldu)
# -------------------------------
SELECTORS = {
    "product_card": [
        ".product-card",
        ".product-item",
        "article.product",
        "li.product",
        "div.product",
    ],
    "title": [
        ".product-title",
        ".card-title",
        "h2 a",
        "h2.product-title a",
        "h3 a",
        "a.product-name",
    ],
    "price": [
        ".price",
        ".current-price",
        ".product-price",
        ".amount",
        "span.woocommerce-Price-amount",
    ],
    "link": [
        "a.product-link",
        ".product-title a",
        "a.card-link",
        "a",
    ],
    "sku": [
        "[data-sku]",
        ".sku",
        ".product-sku",
    ],
    "pagination_next": [
        "a.next",
        "a[rel='next']",
        ".pagination .next a",
    ],
}


# -------------------------------
# YARDIMCI FONKSİYONLAR
# -------------------------------
def read_categories(fp: str) -> List[str]:
    urls = []
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                u = line.strip()
                if not u or u.startswith("#"):
                    continue
                urls.append(u)
    return urls


def soup_get(url: str) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=HDRS, timeout=TIMEOUT)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None


def first_text(el) -> str:
    if not el:
        return ""
    if isinstance(el, list):
        el = el[0] if el else None
    if not el:
        return ""
    return " ".join(el.get_text(" ", strip=True).split())


def pick_first(soup: BeautifulSoup, selectors: List[str]):
    for sel in selectors:
        hit = soup.select_one(sel)
        if hit:
            return hit
    return None


def pick_many(soup: BeautifulSoup, selectors: List[str]):
    # ilk bulunan seçicidekilerin hepsini döndür
    for sel in selectors:
        hits = soup.select(sel)
        if hits:
            return hits
    return []


def price_to_float(txt: str) -> Optional[float]:
    if not txt:
        return None
    # sayıları ayıkla (12.345,67 veya 12,345.67 vb. durumlar)
    cleaned = txt
    cleaned = cleaned.replace("\u00A0", " ").replace("\xa0", " ")
    cleaned = re.sub(r"[^\d,.\s]", "", cleaned)
    # virgül nokta normalizasyonu
    # önce '12.345,67' tipi için nokta ayırıcıyı at, virgülü noktaya çevir
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned and "." not in cleaned:
        # '123,45' → 123.45
        cleaned = cleaned.replace(",", ".")
    try:
        return float(re.findall(r"\d+(?:\.\d+)?", cleaned)[0])
    except Exception:
        return None


def find_product_cards(page: BeautifulSoup):
    cards = []
    for sel in SELECTORS["product_card"]:
        hits = page.select(sel)
        if hits:
            cards = hits
            break
    return cards


def next_page_url(page: BeautifulSoup, base_url: str) -> Optional[str]:
    for sel in SELECTORS["pagination_next"]:
        a = page.select_one(sel)
        if a and a.get("href"):
            return urljoin(base_url, a["href"])
    return None


# -------------------------------
# ÇEKİRDEK SCRAPE
# -------------------------------
def scrape_category(cat_url: str) -> List[Dict]:
    out: List[Dict] = []
    seen_urls = set()
    url = cat_url

    for _ in range(50):  # güvenlik amaçlı maksimum sayfa
        page = soup_get(url)
        if not page:
            break

        cards = find_product_cards(page)
        for c in cards:
            # link
            link_el = pick_first(BeautifulSoup(str(c), "html.parser"), SELECTORS["link"])
            href = link_el.get("href").strip() if link_el and link_el.get("href") else ""
            full = urljoin(url, href) if href else ""

            if full and full in seen_urls:
                continue
            if full:
                seen_urls.add(full)

            # başlık
            title_el = pick_first(BeautifulSoup(str(c), "html.parser"), SELECTORS["title"])
            title = first_text(title_el)
            # fiyat
            price_el = pick_first(BeautifulSoup(str(c), "html.parser"), SELECTORS["price"])
            price_txt = first_text(price_el)
            price_val = price_to_float(price_txt)

            # sku
            sku_el = pick_first(BeautifulSoup(str(c), "html.parser"), SELECTORS["sku"])
            sku = ""
            if sku_el:
                if sku_el.has_attr("data-sku"):
                    sku = sku_el["data-sku"]
                else:
                    sku = first_text(sku_el)

            if title or price_val or full:
                out.append(
                    {
                        "sku": sku or "",
                        "name": title or "",
                        "price": price_val if price_val is not None else "",
                        "url": full or "",
                        "source_category": cat_url,
                    }
                )

        nxt = next_page_url(page, url)
        if not nxt or nxt == url:
            break
        url = nxt
        time.sleep(SLEEP_BETWEEN)

    return out


def scrape_all(categories: List[str]) -> pd.DataFrame:
    rows: List[Dict] = []
    for idx, cu in enumerate(categories, 1):
        print(f"[SCRAPE] ({idx}/{len(categories)}) {cu}")
        try:
            rows.extend(scrape_category(cu))
        except Exception as e:
            print(f"[WARN] {cu} hatası: {e}")
        time.sleep(SLEEP_BETWEEN)
    if not rows:
        return pd.DataFrame(columns=["sku", "name", "price", "url", "source_category"])
    return pd.DataFrame(rows)


# -------------------------------
# KAYIT (Excel uyumlu)
# -------------------------------
def save_csv(df: pd.DataFrame, path: str):
    # Excel/TR uyumu için:
    #  - utf-8-sig (BOM'lu UTF-8)
    #  - sep=';' (TR yerelde Excel’in beklediği ayraç)
    df.to_csv(path, index=False, encoding="utf-8-sig", sep=";")


def make_pretty(df: pd.DataFrame) -> pd.DataFrame:
    # Örnek komisyon/rapor alanları
    df2 = df.copy()
    # fiyat sayı değilse boş kalsın
    def _num(x):
        try:
            return float(x)
        except Exception:
            return None

    df2["price"] = df2["price"].apply(_num)
    df2["commission"] = df2["price"].apply(lambda x: round((x or 0) * 0.1, 2))
    df2["estimated_commission"] = df2["commission"]
    # TRY kolonu
    df2["estimated_commission_try"] = df2["estimated_commission"]
    # Çıktı sütun sırası
    cols = ["sku", "name", "price", "commission", "estimated_commission", "estimated_commission_try", "url"]
    return df2.reindex(columns=cols)


# -------------------------------
# ANA
# -------------------------------
def main():
    cats = read_categories(CATEGORIES_FILE)
    if not cats:
        print(f"[SCRAPE] Uyarı: '{CATEGORIES_FILE}' bulunamadı veya boş.")
        return

    df = scrape_all(cats)

    if df.empty:
        print("[SCRAPE] Ürün bulunamadı, mevcut CSV’ler varsa sadece Excel uyumlu formatta yeniden kaydedilecek.")
        # varsa önceki dosyaları utf-8-sig + ; ile yeniden yaz
        if os.path.exists(OUT_RAW):
            pd.read_csv(OUT_RAW, engine="python").to_csv(OUT_RAW, index=False, encoding="utf-8-sig", sep=";")
        if os.path.exists(OUT_PRETTY):
            pd.read_csv(OUT_PRETTY, engine="python").to_csv(OUT_PRETTY, index=False, encoding="utf-8-sig", sep=";")
        return

    # KAYIT
    print(f"[SCRAPE] {len(df)} ürün bulundu, dosyalar yazılıyor...")
    save_csv(df, OUT_RAW)

    pretty = make_pretty(df)
    save_csv(pretty, OUT_PRETTY)

    print("[SCRAPE] Kayıt tamamlandı:")
    print(f" - {OUT_RAW}")
    print(f" - {OUT_PRETTY}")


if __name__ == "__main__":
    main()
