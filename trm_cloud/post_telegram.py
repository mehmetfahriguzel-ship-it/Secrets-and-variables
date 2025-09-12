import os
import time
from typing import Optional

import pandas as pd
from telethon import TelegramClient
from telethon.sessions import StringSession


# -------- helpers --------
def env_int(name: str, default: int) -> int:
    """Güvenli int parse: boş/yanlışsa default döner."""
    val = os.getenv(name, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def read_csv_any(path: str) -> pd.DataFrame:
    """UTF-8/utf-8-sig/Windows kodlamalarına toleranslı oku."""
    for enc in ("utf-8", "utf-8-sig", "cp1254", "latin1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    # son çare enkodlama belirtmeden dene
    return pd.read_csv(path)


def prettify_row(row: pd.Series) -> str:
    """
    CSV'de beklenen kolonlar:
      sku_name, price, commission, estimated_commission, estimated_commission_try
    Bulunmayan olursa olanlarla mesaj kurar.
    """
    parts = []
    name = row.get("sku_name") or row.get("name") or row.get("title") or ""
    price = row.get("price")
    commission = row.get("commission")
    est_comm = row.get("estimated_commission")
    est_comm_try = row.get("estimated_commission_try")

    if name:
        parts.append(f"🛍️ {name}")
    if pd.notna(price):
        parts.append(f"💸 Fiyat: {price}")
    if pd.notna(commission):
        parts.append(f"📈 Komisyon: {commission}")
    if pd.notna(est_comm):
        parts.append(f"≈ Tahmini Komisyon: {est_comm}")
    if pd.notna(est_comm_try):
        parts.append(f"≈ Tahmini Komisyon (TRY): {est_comm_try}")

    if not parts:
        return "Yeni ürün"
    return "\n".join(parts)


# -------- env --------
API_ID = os.environ["TELEGRAM_API_ID"]
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION_STRING = os.environ["TELEGRAM_SESSION"]

# Nereye post atılacak?
# Sağlam bir varsayılan: "me" → Saved Messages
TARGET = os.getenv("TELEGRAM_DEST", "").strip() or "me"

# Kaç ürün gönderilsin? (hatalıysa 20)
BATCH_SIZE = env_int("TELEGRAM_BATCH", 20)

# Hangi dosyadan okuyalım?
# Öncelik güzel formatlı rapor; yoksa ürün listesi
INPUTS = ["TRM_REPORT_PRETTY.csv", "TRM_PRODUCTS.csv"]


def main():
    # veri oku
    df: Optional[pd.DataFrame] = None
    used_path = None
    for p in INPUTS:
        if os.path.exists(p):
            df = read_csv_any(p)
            used_path = p
            break
    if df is None or df.empty:
        raise SystemExit("Gönderilecek veri bulunamadı. CSV yok ya da boş.")

    # Mesaj gövdesini hazırlayalım
    msgs = [prettify_row(r) for _, r in df.head(BATCH_SIZE).iterrows()]

    # Telegram istemcisi
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    client.connect()
    if not client.is_user_authorized():
        raise SystemExit("Telegram oturum yetkili değil (SESSION_STRING geçersiz olabilir).")

    print(f"Kaynak dosya: {used_path}")
    print(f"Hedef: {TARGET} | Gönderilecek öğe: {len(msgs)}")

    sent_rows = []
    for i, msg in enumerate(msgs, 1):
        client.send_message(TARGET, msg)
        sent_rows.append(msg)
        print(f"[{i}/{len(msgs)}] gönderildi")
        time.sleep(1)  # nazik hız

    client.disconnect()

    # Log/çıktı – Excel Türkçe karakter bozmaması için utf-8-sig
    out = pd.DataFrame({"posted_message": sent_rows})
    out.to_csv("POSTED_TO_TELEGRAM.csv", index=False, encoding="utf-8-sig")
    print("Bitti: POSTED_TO_TELEGRAM.csv yazıldı.")


if __name__ == "__main__":
    main()
