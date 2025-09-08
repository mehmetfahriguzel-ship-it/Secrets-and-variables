# trm_cloud/main.py
import os
import math
import json
import time
import pandas as pd
from pathlib import Path
import requests

CSV_PATH = Path("TRM_REPORT_PRETTY.csv")

def ensure_csv():
    """CSV yoksa örnek veri oluşturur; varsa dokunmaz."""
    if CSV_PATH.exists():
        return
    rows = [
        {"sku_name": "SKU-A", "price": 199.90, "commission": 18.0, "estimated_commission_try": 35.98},
        {"sku_name": "SKU-B", "price": 89.90,  "commission": 20.0, "estimated_commission_try": 17.98},
        {"sku_name": "SKU-C", "price": 349.00, "commission": 15.0, "estimated_commission_try": 52.35},
    ]
    df = pd.DataFrame(rows)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

def load_rows(limit=10):
    df = pd.read_csv(CSV_PATH)
    # sütun adlarını normalize et (boşluk vs. sorun olmasın)
    df.columns = [c.strip() for c in df.columns]
    # en fazla limit kadar gönder
    return df.head(limit).to_dict(orient="records")

def chunk_text(text, max_len=3900):
    """Telegram 4096 sınırı için güvenli parçalama."""
    parts, i = [], 0
    while i < len(text):
        parts.append(text[i:i+max_len])
        i += max_len
    return parts

def send_telegram(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID bulunamadı; mesaj atlanıyor.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ok_all = True
    for part in chunk_text(text):
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": part,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=30)
        if resp.status_code != 200:
            ok_all = False
            print("Telegram hata:", resp.status_code, resp.text)
        time.sleep(0.4)  # flood protection
    return ok_all

def build_message(rows):
    lines = ["<b>TRM Günlük Ürün Özeti</b>\n"]
    for r in rows:
        name = str(r.get("sku_name", "—"))
        price = r.get("price", "—")
        com = r.get("commission", "—")
        est = r.get("estimated_commission_try", "—")
        line = f"• <b>{name}</b> — Fiyat: {price}₺ | Komisyon: {com}% | Tahmini Kazanç: <b>{est}₺</b>"
        lines.append(line)
    lines.append("\n#trendurunler #otopost #trm")
    return "\n".join(lines)

def main():
    ensure_csv()
    rows = load_rows(limit=10)
    msg = build_message(rows)
    print("Gönderilecek mesaj:\n", msg)
    sent = send_telegram(msg)
    if sent:
        print("✅ Telegram’a gönderildi.")
    else:
        print("⚠️ Telegram gönderimi yapılmadı / başarısız.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Loga düşsün, workflow kırmızıya boyansın diye exception’ı yeniden fırlat
        print("Hata:", e)
        raise
