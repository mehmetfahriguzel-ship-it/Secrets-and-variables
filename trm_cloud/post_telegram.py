# -*- coding: utf-8 -*-
import os, time, csv
from pathlib import Path
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
API       = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None

PRODUCTS_CSV = Path("TRM_PRODUCTS.csv")          # name, price, url
MAX_ITEMS    = 20                                 # İlk 20 ürünü gönder
PAUSE_SEC    = 0.8                                # Mesajlar arasında bekleme

def send_text(text: str):
    if not (API and CHAT_ID):
        print("TELEGRAM SECRETS YOK → gönderim atlandı.")
        return
    try:
        r = requests.post(f"{API}/sendMessage",
                          data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
                          timeout=30)
        r.raise_for_status()
        print("OK text")
    except Exception as e:
        print("ERR text:", e)

def main():
    if not PRODUCTS_CSV.exists():
        print("Ürün dosyası yok:", PRODUCTS_CSV)
        return

    rows = []
    with PRODUCTS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        send_text("⚠️ Ürün bulunamadı.")
        return

    send_text("✅ Trend Ürünler Market — Otomatik Paylaşım Başladı")

    sent = 0
    for r in rows[:MAX_ITEMS]:
        name = (r.get("name") or "").strip()
        price = (r.get("price") or "").strip()
        url = (r.get("url") or "").strip()

        # Fiyatı güzel göster
        if price and isinstance(price, str) and price.replace(".", "", 1).isdigit():
            try:
                price = f"{float(price):.2f} ₺"
            except:
                pass
        msg = f"• {name}\nFiyat: {price}\n{url}"
        send_text(msg)
        sent += 1
        time.sleep(PAUSE_SEC)

    send_text(f"✅ Bitti. Toplam {sent} ürün paylaşıldı.")

if __name__ == "__main__":
    main()
