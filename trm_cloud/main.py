import os
import json
from pathlib import Path
import pandas as pd
import requests

# -------- Ayarlar --------
OUT_DIR = Path("trm_reports")
CSV_NAME = "TRM_REPORT_PRETTY.csv"
CSV_PATH = OUT_DIR / CSV_NAME

# -------- Örnek veri (burayı gerçek verinle değiştirebilirsin) --------
def build_rows():
    return [
        {"sku_name": "SKU-A", "price": 199.90, "commission": 18.0, "estimated_commission_try": 35.98},
        {"sku_name": "SKU-B", "price":  89.90, "commission": 20.0, "estimated_commission_try": 17.98},
        {"sku_name": "SKU-C", "price": 349.00, "commission": 15.0, "estimated_commission_try": 52.35},
    ]

# -------- Google Drive: servis hesabı ile yükleme --------
def upload_to_gdrive_via_service_account(local_path, folder_id):
    """pydrive2 ile Drive'a yükle"""
    from pydrive2.auth import ServiceAccountCredentials, GoogleAuth
    from pydrive2.drive import GoogleDrive

    sa_json = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        print("GDRIVE_SERVICE_ACCOUNT_JSON bulunamadı; Drive yükleme atlandı.")
        return None

    # JSON string -> dict -> geçici dosya
    creds_dict = json.loads(sa_json)
    tmp_json = Path("sa.json")
    tmp_json.write_text(json.dumps(creds_dict), encoding="utf-8")

    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(str(tmp_json), scope)
    drive = GoogleDrive(gauth)

    file = drive.CreateFile({"title": local_path.name, "parents": [{"id": folder_id}]})
    file.SetContentFile(str(local_path))
    file.Upload()
    link = f"https://drive.google.com/file/d/{file['id']}/view"
    print("Drive'a yüklendi:", link)
    try:
        tmp_json.unlink(missing_ok=True)
    except Exception:
        pass
    return link

# -------- Telegram bildirim --------
def send_telegram_message(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID yok; Telegram atlanıyor.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text})
    print("Telegram status:", r.status_code, r.text[:120])

# -------- Ana akış --------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Veri hazırla ve CSV yaz
    rows = build_rows()
    df = pd.DataFrame(rows)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"CSV üretildi: {CSV_PATH}")

    # 2) Drive'a yükle (varsa)
    drive_folder = os.environ.get("GDRIVE_FOLDER_ID", "").strip()
    drive_link = None
    if drive_folder:
        try:
            drive_link = upload_to_gdrive_via_service_account(CSV_PATH, drive_folder)
        except Exception as e:
            print("Drive yükleme hatası:", e)

    # 3) Telegram bildirimi
    msg = "TRM Cloud Automation ✅\nRapor: " + CSV_NAME
    if drive_link:
        msg += f"\nDrive: {drive_link}"
    send_telegram_message(msg)

    print("TRM Cloud Automation başarıyla çalıştı ✅")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Genel hata:", e)
        raise
