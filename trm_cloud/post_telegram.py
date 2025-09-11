import os, csv, json, asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION = os.getenv("TELEGRAM_SESSION")
TARGET = os.getenv("TELEGRAM_TARGET")  # @kanaladi veya https://t.me/kanaladi

CSV_FILE = "TRM_PRODUCTS.csv"
STATE_FILE = "trm_cloud/_posted_state.json"
BATCH_SIZE = int(os.getenv("TELEGRAM_BATCH", "20"))

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"posted_urls": []}

def save_state(st):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)

def read_products():
    rows = []
    with open(CSV_FILE, encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f)):
            rows.append(r)
    return rows

def caption(r):
    parts = [f"🛍️ {r['name']}"]
    if r.get("price"):
        parts.append(f"💸 {r['price']}")
    parts.append(f"🔗 {r['url']}")
    return "\n".join(parts)

async def main():
    state = load_state()
    posted = set(state.get("posted_urls", []))

    products = [p for p in read_products() if p["url"] not in posted]
    if not products:
        print("Gönderilecek yeni ürün yok.")
        return

    async with TelegramClient(StringSession(SESSION), API_ID, API_HASH) as client:
        # Hedefe eriş (gerekirse katıl)
        try:
            if TARGET.startswith("http"):
                entity = await client.get_entity(TARGET)
            elif TARGET.startswith("@"):
                entity = await client.get_entity(TARGET)
            else:
                entity = await client.get_entity(f"@{TARGET}")
        except Exception:
            # davet linkiyse katılmayı dene
            try:
                await client(JoinChannelRequest(TARGET))
                entity = await client.get_entity(TARGET)
            except Exception as e:
                print(f"[HATA] Kanala ulaşılamadı: {e}")
                return

        count = 0
        for r in products:
            try:
                img = r["image"] if r["image"] else None
                text = caption(r)
                if img:
                    await client.send_file(entity, img, caption=text)
                else:
                    await client.send_message(entity, text)
                posted.add(r["url"])
                count += 1
                if count >= BATCH_SIZE:
                    break
            except Exception as e:
                print(f"[WARN] Gönderilemedi: {r['url']} → {e}")

    state["posted_urls"] = list(posted)
    save_state(state)
    print(f"✓ Telegram’a gönderilen ürün sayısı: {count}")

if __name__ == "__main__":
    asyncio.run(main())
