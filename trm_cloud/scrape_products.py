# trm_cloud/scrape_products.py
import os, sys, csv, time
import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD_CSV = os.path.join(ROOT, "..", "TRM_PRODUCTS.csv")
PRETTY_CSV = os.path.join(ROOT, "..", "TRM_REPORT_PRETTY.csv")
CATEGORIES_TXT = os.path.join(ROOT, "..", "categories.txt")

def save_csv(rows):
    if not rows:
        return
    df = pd.DataFrame(rows)
    # kolonları sabitle
    want_cols = ["sku","name","price","commission","estimated_commission","estimated_commission_try","url"]
    for c in want_cols:
        if c not in df.columns: df[c] = ""
    df = df[want_cols]
    # ana csv
    df.to_csv(PROD_CSV, index=False, encoding="utf-8-sig")
    # pretty csv (aynı)
    df.to_csv(PRETTY_CSV, index=False, encoding="utf-8-sig")

def parse_category(url):
    """Genel seçicilerle ürün çekmeyi dener; site sınıfları değişse bile patlamasın."""
    rows = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; TRMBot/1.0)"
    })
    page = 1
    while True:
        u = url.rstrip("/")
        candidate = f"{u}?page={page}"
        try:
            r = session.get(candidate, timeout=20)
            if r.status_code >= 400:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            # bir kaç muhtemel blok:
            cards = soup.select(".product, .product-item, .card, li.product") or []
            if not cards and page > 1:
                break
            found = 0
            for c in cards:
                name = (c.select_one(".product-name, .name, .title, a") or {}).get_text(strip=True) if hasattr((c.select_one(".product-name, .name, .title, a") or {}),'get_text') else ""
                price = (c.select_one(".price, .product-price, .current") or {}).get_text(strip=True) if hasattr((c.select_one(".price, .product-price, .current") or {}),'get_text') else ""
                link_el = c.select_one("a[href]")
                href = link_el["href"].strip() if link_el and link_el.has_attr("href") else ""
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    p = urlparse(u)
                    href = f"{p.scheme}://{p.netloc}{href}"
                if not name:
                    continue
                sku = f"SKU-{abs(hash(name)) % 10**8}"
                rows.append({
                    "sku": sku,
                    "name": name,
                    "price": price,
                    "commission": "",
                    "estimated_commission": "",
                    "estimated_commission_try": "",
                    "url": href
                })
                found += 1
            if found == 0:
                break
            page += 1
            time.sleep(0.5)
        except Exception:
            break
    return rows

def main():
    all_rows = []
    if os.path.exists(CATEGORIES_TXT):
        with open(CATEGORIES_TXT, "r", encoding="utf-8") as f:
            cats = [ln.strip() for ln in f if ln.strip()]
        for url in cats:
            rows = parse_category(url)
            all_rows.extend(rows)
    # kayıt
    if all_rows:
        save_csv(all_rows)
        print(f"[SCRAPE] {len(all_rows)} ürün kaydedildi.")
        return

    # Ürün bulunamadıysa, mevcut csv’leri düzenle (Excel Türkçe sorunu için)
    if os.path.exists(PROD_CSV):
        df = pd.read_csv(PROD_CSV, dtype=str, encoding="utf-8", engine="python")
        df.to_csv(PROD_CSV, index=False, encoding="utf-8-sig")
        df.to_csv(PRETTY_CSV, index=False, encoding="utf-8-sig")
        print("[SCRAPE] Var olan CSV yeniden yazıldı (utf-8-sig).")
    elif os.path.exists(PRETTY_CSV):
        df = pd.read_csv(PRETTY_CSV, dtype=str, encoding="utf-8", engine="python")
        df.to_csv(PRETTY_CSV, index=False, encoding="utf-8-sig")
        print("[SCRAPE] Pretty CSV yeniden yazıldı (utf-8-sig).")
    else:
        # dosya yoksa boş dosya bırak
        pd.DataFrame(columns=["sku","name","price","commission","estimated_commission","estimated_commission_try","url"]).to_csv(PRETTY_CSV, index=False, encoding="utf-8-sig")
        print("[SCRAPE] Ürün bulunamadı; boş rapor oluşturuldu.")

if __name__ == "__main__":
    main()
