import os
import pandas as pd
from pathlib import Path
import requests

INPUT_CSV = Path("trm_cloud/products.csv")
OUT_DIR = Path("trm_reports")
OUT_CSV = OUT_DIR / "TRM_REPORT_PRETTY.csv"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def load_products():
    df = pd.read_csv(INPUT_CSV)
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ["sku_name", "price_try", "commission", "product_url"]:
        if col not in df.columns:
            raise ValueError(f"Eksik kolon: {col}")
    # opsiyonel image_url
    if "image_url" not in df.columns:
        df["image_url"] = ""
    df["price_try"] = pd.to_numeric(df["price_try"], errors="coerce").fillna(0)
    df["commission"] = pd.to_numeric(df["commission"], errors="coerce").fillna(0)
    df["estimated_commission_try"] = (df["price_try"] * df["commission"] / 100).round(2)
    return df

def save_report(df: pd.DataFrame):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = ["sku_name","price_try","commission","estimated_commission_try","product_url","image_url"]
    df[cols].to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print("Rapor yazıldı:", OUT_CSV)

def send_telegram_text(text: str):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print("Telegram secrets yok; gönderim atlandı.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": False})
    print("Telegram text status:", r.status_code)

def send_telegram_photo(caption: str, image_url: str):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print("Telegram secrets yok; gönderim atlandı.")
        return
    if not image_url:
        return send_telegram_text(caption)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, files=None, json=None, params=None, 
                      # Telegram sendPhoto uzaktan URL'yi destekler:
                      # requests ile 'data' ve 'files' yerine aşağıdaki gibi form-data göndermek yerine direkt parametreyle de çalışır.
                      )
    # Bazı istemcilerde yukarıdaki basit çağrı URL ekini desteklemediği için alternatif:
    r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "photo": image_url})
    print("Telegram photo status:", r.status_code)

def format_caption(row) -> str:
    # Kısa ve vurucu tanıtım metni
    return (f"🔥 {row['sku_name']}\n"
            f"💸 Fiyat: {row['price_try']:.2f} TL\n"
            f"💰 Komisyon: %{row['commission']:.0f} (Tahmini: {row['estimated_commission_try']:.2f} TL)\n"
            f"🔗 Satın al: {row['product_url']}")

def main():
    df = load_products()
    save_report(df)

    # Kaç ürünü paylaşalım? (örn. ilk 3)
    share_count = min(3, len(df))
    for i in range(share_count):
        row = df.iloc[i]
        caption = format_caption(row)
        img = str(row.get("image_url") or "").strip()
        if img:
            send_telegram_photo(caption, img)
        else:
            send_telegram_text(caption)

    print("Tanıtım gönderimleri tamamlandı ✅")

if __name__ == "__main__":
    main()
