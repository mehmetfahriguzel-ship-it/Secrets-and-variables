import os
import requests
from pathlib import Path
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FILES = [
    Path("TRM_REPORT_PRETTY.csv"),
    Path("TRM_PRODUCTS.csv"),
]

API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None

def send_text(text: str):
    if not (API and CHAT_ID):
        print("TELEGRAM secrets yok; gönderim atlandı.")
        return
    try:
        r = requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": text})
        r.raise_for_status()
        print("Telegram text OK")
    except Exception as e:
        print("Telegram text ERR:", e)

def send_file(path: Path, caption: str = ""):
    if not (API and CHAT_ID):
        return
    if not path.exists():
        print(f"Gönderilecek dosya yok: {path}")
        return
    try:
        with open(path, "rb") as f:
            r = requests.post(
                f"{API}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"document": (path.name, f, "text/csv")},
                timeout=60,
            )
        r.raise_for_status()
        print(f"Telegram file OK: {path.name}")
    except Exception as e:
        print(f"Telegram file ERR ({path.name}):", e)

def main():
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    send_text(f"✅ TRM Cloud Automation tamamlandı ({ts})")
    for p in FILES:
        send_file(p, caption=p.name)

if __name__ == "__main__":
    main()
