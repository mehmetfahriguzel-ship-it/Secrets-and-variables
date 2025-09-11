import re, os, csv, time, json
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE = "https://trendurunlermarket.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TRMBot/1.0)"}

CATEGORIES_FILE = "trm_cloud/categories.txt"
OUT_PRODUCTS = "TRM_PRODUCTS.csv"
STATE_FILE = "trm_cloud/_posted_state.json"   # gönderilenleri tutar

def read_categories():
    if not os.path.exists(CATEGORIES_FILE):
        print(f"[HATA] {CATEGORIES_FILE} yok. Kategori linklerini bu dosyaya tek tek yaz.")
        return []
    with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
        cats = [l.strip() for l in f if l.strip()]
    print(f"[INFO] {len(cats)} kategori bulundu.")
    return cats

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def parse_list_items(soup):
    """
    Site teması değişse bile yaygın seçicilerle deneriz.
    Döndürdüğü her dict: {name, price, url, image}
    """
    items = []
    # 1) Kartlar
    cards = soup.select(".product, .product-card, .productItem, .product-item, li.product, .col-product")
    if not cards:
        # Fallback: linklerde ürün sayfaları
        cards = soup.select("a[href*='/urun-'], a[href*='/p-'], a[href*='/Product-']")
    for c in cards:
        # URL
        a = c.select_one("a[href]")
        href = a["href"] if a else None
        if href and href.startswith("/"):
            href = urljoin(BASE, href)
        # İsim
        name = None
        for sel in ["[itemprop='name']", ".product-name", ".name", "h3", "h2", "h4", "span"]:
            el = c.select_one(sel)
            if el and el.get_text(strip=True):
                name = el.get_text(" ", strip=True)
                break
        # Fiyat
        price = None
        price_candidates = c.select(".price, .product-price, [itemprop='price'], .current, .new-price, .urunFiyat, .prc")
        if price_candidates:
            price = price_candidates[0].get_text(" ", strip=True)
        else:
            txt = c.get_text(" ", strip=True)
            m = re.search(r"(\d[\d\.]*,\d{2}|\d[\d\.]*)\s*TL", txt, re.I)
            if m: price = m.group(0)
        # Resim
        img = None
        imgel = c.select_one("img[src]")
        if imgel:
            img = imgel.get("data-src") or imgel.get("src")
            if img and img.startswith("/"):
                img = urljoin(BASE, img)
        if href and name:
            items.append({"name": name, "price": price or "", "url": href, "image": img or ""})
    return items

def has_next_page(soup):
    nxt = soup.select_one("a[rel='next'], .pagination a.next, .pages a.next, a[aria-label='Next']")
    return bool(nxt)

def build_page_url(cat_url, page):
    # yaygın pagination: ?pg=2, ?page=2, /?PAGEN_2=2, /page/2
    if page == 1: 
        return cat_url
    for sep in ["?pg=", "?page=", "&page="]:
        if sep in cat_url:
            base = re.sub(r"([?&](pg|page)=)\d+", r"\g<1>"+str(page), cat_url)
            return base
    if "?" in cat_url:
        return f"{cat_url}&page={page}"
    return f"{cat_url}?page={page}"

def scrape_category(cat_url, limit_pages=50, sleep=1.0):
    page = 1
    all_items = []
    while page <= limit_pages:
        url = build_page_url(cat_url, page)
        print(f"[{page}] {url}")
        try:
            soup = get_soup(url)
        except Exception as e:
            print(f"[WARN] {e}")
            break
        items = parse_list_items(soup)
        if not items:
            # başka seçicilerle deneyip yine yoksa dur
            print("[INFO] Ürün bulunamadı; durduruldu.")
            break
        all_items.extend(items)
        if not has_next_page(soup):
            break
        page += 1
        time.sleep(sleep)
    return all_items

def main():
    cats = read_categories()
    all_rows = []
    for cu in cats:
        try:
            rows = scrape_category(cu)
            print(f"[OK] {cu} → {len(rows)} ürün")
            all_rows.extend(rows)
        except Exception as e:
            print(f"[ERR] {cu}: {e}")

    # uniq URL
    seen = set()
    uniq = []
    for r in all_rows:
        if r["url"] in seen: 
            continue
        seen.add(r["url"])
        uniq.append(r)

    with open(OUT_PRODUCTS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name","price","url","image"])
        w.writeheader()
        w.writerows(uniq)

    print(f"\n✓ TOPLAM: {len(uniq)} ürün yazıldı → {OUT_PRODUCTS}")

    # state dosyası yoksa üret (telegram için ilk koşuda hepsini “gönderilmedi” sayalım)
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"posted_urls": []}, f)

if __name__ == "__main__":
    main()
