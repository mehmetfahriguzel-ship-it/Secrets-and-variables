# trm_cloud/post_telegram.py
import os
import time
import csv
from typing import List, Dict, Any

# --- Telethon ---
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

# --- pandas opsiyonel ---
USE_PANDAS = True
try:
    import pandas as pd  # type: ignore
except Exception:
    USE_PANDAS = False


# ========================= Yardımcılar =========================
def env_int(name: str, default: int) -> int:
    """Env değişkenini güvenle tam sayıya çevir; boş/yanlışsa default döner."""
    raw = (os.getenv(name, "") or "").strip()
    try:
        return int(raw)
    except Exception:
        return default


def parse_targets(raw: str) -> List[str]:
    """
    Hedef listesi: satır satır / virgül / noktalı virgül ayraçlarını destekler.
    Yinelenenleri eler.
    """
    if not raw:
        return []
    parts: List[str] = []
    for line in raw.splitlines():
        for piece in line.replace(";", "\n").replace(",", "\n").splitlines():
            p = piece.strip()
            if p:
                parts.append(p)
    uniq, seen = [], set()
    for p in parts:
        if p not in seen:
            uniq.append(p); seen.add(p)
    return uniq


def pick(row: Dict[str, Any], *keys: str) -> Any:
    """Satırdan ilk bulunan anahtarı getirir."""
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return None


def load_rows() -> List[Dict[str, Any]]:
    """
    Aynı klasördeki rapor dosyalarından yükler.
    Öncelik: TRM_REPORT_PRETTY.csv -> TRM_PRODUCTS.csv
    """
    candidates = ["TRM_REPORT_PRETTY.csv", "TRM_PRODUCTS.csv"]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        print("UYARI: TRM_REPORT_PRETTY.csv / TRM_PRODUCTS.csv bulunamadı.")
        return []

    try:
        if USE_PANDAS:
            df = pd.read_csv(path, encoding="utf-8-sig")
            rows = df.to_dict(orient="records")
        else:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
        print(f"INFO: {path} okundu, satır: {len(rows)}")
        return rows
    except Exception as e:
        print(f"HATA: CSV okunamadı: {e}")
        return []


def build_message(row: Dict[str, Any]) -> str:
    """Bir ürün satırından Telegram mesajı üretir."""
    name = pick(row, "name", "title", "sku_name", "product_name")
    url = pick(row, "url", "link", "product_url", "page_url")
    price = pick(row, "price", "current_price", "price_text")
    comm = pick(row, "estimated_commission_try", "estimated_commission", "commission_try", "commission")

    lines = []
    if name:  lines.append(f"🛍️ {name}")
    if price: lines.append(f"💸 Fiyat: {price}")
    if comm:  lines.append(f"💰 Komisyon (tahmini): {comm}")
    if url:   lines.append(f"🔗 {url}")
    if not lines:
        lines.append(str(row))
    return "\n".join(lines)


# ========================= Ana Akış =========================
def main() -> None:
    api_id = env_int("TELEGRAM_API_ID", 0)
    api_hash = (os.getenv("TELEGRAM_API_HASH", "") or "").strip()
    session = (os.getenv("TELEGRAM_SESSION", "") or "").strip()

    # Hedefler: TELEGRAM_TARGETS varsa onu; yoksa TELEGRAM_SOURCE'u kullan
    targets_raw = os.getenv("TELEGRAM_TARGETS") or os.getenv("TELEGRAM_SOURCE") or ""
    targets = parse_targets(targets_raw)

    batch_size = env_int("TELEGRAM_BATCH", 20)          # varsayılan 20
    delay_sec  = env_int("TELEGRAM_DELAY_MS", 700) / 1000.0  # varsayılan 700ms

    if not api_id or not api_hash or not session:
        raise SystemExit("HATA: TELEGRAM_API_ID / TELEGRAM_API_HASH / TELEGRAM_SESSION eksik.")
    if not targets:
        raise SystemExit("HATA: TELEGRAM_TARGETS veya TELEGRAM_SOURCE boş.")
    rows = load_rows()
    if not rows:
        raise SystemExit("HATA: Gönderilecek satır yok.")

    rows = rows[:batch_size]
    print(f"INFO: Hedef={len(targets)} | Mesaj={len(rows)} | Bekleme={delay_sec:.2f}s")

    client = TelegramClient(StringSession(session), api_id, api_hash)

    sent_total = 0
    failed_total = 0

    async def _run():
        nonlocal sent_total, failed_total
        await client.connect()
        if not await client.is_user_authorized():
            raise SystemExit("HATA: Oturum yetkili değil (session string yanlış/sona ermiş).")

        for target in targets:
            try:
                entity = await client.get_entity(target)
            except Exception as e:
                print(f"UYARI: Hedef çözümlenemedi ({target}): {e}")
                failed_total += len(rows)
                continue

            print(f"--- Gönderim: {target} ---")
            for i, row in enumerate(rows, 1):
                msg = build_message(row)
                try:
                    await client.send_message(entity, msg, link_preview=False)
                    sent_total += 1
                    print(f"[OK] {i}/{len(rows)}")
                except RPCError as e:
                    failed_total += 1
                    print(f"[RPC HATA] {e}")
                except Exception as e:
                    failed_total += 1
                    print(f"[HATA] {e}")
                time.sleep(delay_sec)

        await client.disconnect()

    client.loop.run_until_complete(_run())
    print(f"BİTTİ ✅ Başarılı: {sent_total} | Hatalı: {failed_total}")


if __name__ == "__main__":
    main()
