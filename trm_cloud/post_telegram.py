# trm_cloud/post_telegram.py
import os
import csv
import asyncio
import pandas as pd
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRETTY_CSV = os.path.join(ROOT, "..", "TRM_REPORT_PRETTY.csv")
LOG_CSV = os.path.join(ROOT, "..", "TELEGRAM_POST_LOG.csv")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or "0")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION = os.getenv("TELEGRAM_SESSION", "")
SOURCES_RAW = os.getenv("TELEGRAM_SOURCE", "")  # çoklu satır destekli
BATCH = int(os.getenv("TELEGRAM_BATCH", "20") or "20")

def load_sources():
    if not SOURCES_RAW.strip():
        return []
    # newline, virgül ve boşluk ayırıcı
    parts = []
    for ln in SOURCES_RAW.replace(",", "\n").splitlines():
        s = ln.strip()
        if not s:
            continue
        # t.me/ links → @handle
        if "t.me/" in s and not s.startswith("@"):
            s = s.split("t.me/")[-1].strip("/")
            if not s.startswith("@"):
                s = f"@{s}"
        parts.append(s)
    return parts

def load_log():
    posted = set()
    if os.path.exists(LOG_CSV):
        with open(LOG_CSV, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                posted.add(row.get("sku","").strip())
    return posted

def append_log(rows):
    exists = os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sku","name"])
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow({"sku": r.get("sku",""), "name": r.get("name","")})

async def run():
    if API_ID == 0 or not API_HASH or not SESSION:
        print("[TG] API/SESSION eksik, gönderim atlandı.")
        return

    if not os.path.exists(PRETTY_CSV):
        print("[TG] TRM_REPORT_PRETTY.csv yok; gönderim atlandı.")
        return

    df = pd.read_csv(PRETTY_CSV, dtype=str, encoding="utf-8", engine="python").fillna("")
    sources = load_sources()
    if not len(df):
        print("[TG] Gönderilecek ürün yok.")
        return
    if not sources:
        print("[TG] TELEGRAM_SOURCE boş; gönderim atlandı.")
        return

    already = load_log()
    # tekrar gönderme
    candidates = []
    for _, row in df.iterrows():
        sku = row.get("sku","").strip()
        if not sku or sku in already:
            continue
        candidates.append(row.to_dict())
        if len(candidates) >= BATCH:
            break

    if not candidates:
        print("[TG] Yeni ürün bulunamadı (log’a göre).")
        return

    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("[TG] Session yetkisiz; yeni session gerekiyor.")
        return

    sent = []
    for row in candidates:
        name = row.get("name","").strip()
        price = row.get("price","").strip()
        url = row.get("url","").strip()
        sku = row.get("sku","").strip()

        # mesaj
        lines = []
        if name: lines.append(f"**{name}**")
        if price: lines.append(f"Fiyat: {price}")
        if url: lines.append(f"{url}")
        else: lines.append(f"SKU: {sku}")
        msg = "\n".join(lines)

        for target in sources:
            try:
                entity = await client.get_entity(target)
                await client.send_message(entity, msg, link_preview=True)
            except FloodWaitError as e:
                print(f"[TG] Flood wait: {e.seconds}s bekleniyor…")
                await asyncio.sleep(e.seconds + 1)
                entity = await client.get_entity(target)
                await client.send_message(entity, msg, link_preview=True)
            except Exception as ex:
                print(f"[TG] '{target}' için hata: {ex}")

        sent.append({"sku": sku, "name": name})

    if sent:
        append_log(sent)
        print(f"[TG] {len(sent)} ürün gönderildi ve log’a işlendi.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run())
