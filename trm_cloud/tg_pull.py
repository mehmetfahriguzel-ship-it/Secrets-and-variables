# trm_cloud/tg_pull.py
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import csv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors.rpcerrorlist import ChannelPrivateError, ChannelInvalidError

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION = os.getenv("TELEGRAM_SESSION", "")  # StringSession
SOURCE = os.getenv("TELEGRAM_SOURCE", "")    # @kanal / @grup / t.me linki
LIMIT  = int(os.getenv("TELEGRAM_LIMIT", "200"))

OUT_DIR = Path("trm_reports")
OUT_DIR.mkdir(exist_ok=True, parents=True)
OUT_CSV = OUT_DIR / "TELEGRAM_PULL.csv"

def main():
    if not (API_ID and API_HASH and SESSION and SOURCE):
        print("Eksik env: TELEGRAM_API_ID / TELEGRAM_API_HASH / TELEGRAM_SESSION / TELEGRAM_SOURCE")
        return

    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    client.connect()
    if not client.is_user_authorized():
        print("Yetkisiz oturum (SESSION yanlış/expired olabilir).")
        return

    try:
        entity = client.get_entity(SOURCE)
    except (ChannelPrivateError, ChannelInvalidError) as e:
        print(f"Kaynağa erişilemedi: {e}")
        return
    except Exception as e:
        print(f"Kaynak okunamadı: {e}")
        return

    rows = []
    for msg in client.iter_messages(entity, limit=LIMIT):
        if not msg:
            continue
        rows.append({
            "id": msg.id,
            "date": msg.date.isoformat() if msg.date else "",
            "sender_id": getattr(msg, "sender_id", ""),
            "text": (getattr(msg, "message", "") or "").replace("\n", " ").strip(),
            "views": getattr(msg, "views", ""),
            "forwards": getattr(msg, "forwards", ""),
            "replies": getattr(getattr(msg, "replies", None), "replies", ""),
            "link": f"https://t.me/{getattr(entity, 'username', '')}/{msg.id}" if getattr(entity, "username", "") else ""
        })

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","date","sender_id","text","views","forwards","replies","link"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"OK | {len(rows)} mesaj yazıldı -> {OUT_CSV}")

if __name__ == "__main__":
    main()
