# trm_cloud/post_telegram.py
# Çalışma: GitHub Secrets -> TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION,
# TELEGRAM_SOURCE (tek kanal @kanal veya birden çok satırlı liste), TELEGRAM_BATCH (opsiyonel).
# Gönderim: TRM_REPORT_PRETTY.csv'den okur, her ürünü mesaj olarak yollar.

import os
import csv
import asyncio
from telethon import TelegramClient

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION = os.environ["TELEGRAM_SESSION"]

# Kaynak/ hedef kanal(lar): birden fazla satır desteklenir (her satır bir kanal veya tam t.me linki)
RAW_SOURCE = os.environ.get("TELEGRAM_SOURCE", "").strip()
SOURCES = [s.strip() for s in RAW_SOURCE.splitlines() if s.strip()]

# Kaç mesaj yollayalım (int’e çevrilemezse 20)
try:
    BATCH_SIZE = int(os.environ.get("TELEGRAM_BATCH", "20").strip())
except Exception:
    BATCH_SIZE = 20

CSV_PATH = "TRM_REPORT_PRETTY.csv"

def load_rows(path: str, limit: int):
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV bulunamadı: {path}")

    # Excel dostu olarak yazdığımız için utf-8-sig ile açıyoruz
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)

    # İlk limit kadar
    return rows[:max(limit, 0)]

def build_message(row: dict) -> str:
    sku  = row.get("sku","").strip()
    name = row.get("name","").strip()
    price = row.get("price","").strip()
    commission = row.get("commission","").strip()
    est = row.get("estimated_commission","").strip()
    est_try = row.get("estimated_commission_try","").strip()

    lines = [
        f"🛍️ *{name}*",
        f"SKU: `{sku}`",
    ]
    if price: lines.append(f"Fiyat: {price}")
    if commission: lines.append(f"Komisyon: {commission}")
    if est: lines.append(f"Tahmini Komisyon: {est}")
    if est_try: lines.append(f"Tahmini Komisyon (₺): {est_try}")

    return "\n".join(lines)

async def main():
    if not SOURCES:
        raise RuntimeError("TELEGRAM_SOURCE boş. Secrets kısmına @kanal veya t.me/… gir.")

    rows = load_rows(CSV_PATH, BATCH_SIZE)
    if not rows:
        print("Gönderilecek satır yok.")
        return

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    # Her hedef için sırayla gönder
    for dest in SOURCES:
        print(f"Gönderim başlıyor → {dest} (adet={len(rows)})")
        for row in rows:
            msg = build_message(row)
            try:
                await client.send_message(dest, msg, parse_mode="md")
            except Exception as e:
                print(f"⚠️ Gönderim hatası ({dest}): {e}")
        print(f"Gönderim bitti → {dest}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
