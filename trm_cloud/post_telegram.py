raw = os.getenv("TELEGRAM_BATCH", "").strip()
BATCH_SIZE = int(raw) if raw.isdigit() else 20
