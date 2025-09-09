import requests
from bs4 import BeautifulSoup
import pandas as pd

# Trendurunlermarket kategori linkleri
CATEGORY_URLS = [
    "https://trendurunlermarket.com/giyim-C4",
    "https://trendurunlermarket.com/otomotiv-C13",
    "https://trendurunlermarket.com/hobi-kitap-C11",
    "https://trendurunlermarket.com/mucevher-saat-C6",
    "https://trendurunlermarket.com/kozmetik-bakim-C8",
    "https://trendurunlermarket.com/anne-bebek-C10",
    "https://trendurunlermarket.com/ev-yasam-C12",
    "https://trendurunlermarket.com/elektronik-C7",
    # Buraya diğer alt kategori linklerini de ekleyebilirsin
]

def scrape_category(url):
    print(f"Scraping: {url}")
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        print(f"❌ HATA: {url} -> {r.status_code}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    products = []

    for item in soup.select(".product-item"):  # ürün kutusu CSS class
        name = item.select_one(".product-title")
        price = item.select_one(".price-new")

        if name and price:
            products.append({
                "name": name.get_text(strip=True),
                "price": price.get_text(strip=True),
                "url": url
            })
    return products

def main():
    all_products = []
    for link in CATEGORY_URLS:
        all_products.extend(scrape_category(link))

    if not all_products:
        print("⚠️ Hiç ürün bulunamadı.")
        return

    df = pd.DataFrame(all_products)
    df.to_csv("TRM_PRODUCTS.csv", index=False, encoding="utf-8")
    print(f"✅ Kaydedildi: {len(all_products)} ürün")

if __name__ == "__main__":
    main()
