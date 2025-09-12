# trm_cloud/scrape.py
# Amaç: TRM_REPORT_PRETTY.csv dosyasını Excel dostu "utf-8-sig" ile üretmek.
# - Eğer TRM_REPORT_PRETTY.csv zaten varsa -> doğru kodlamayla yeniden yazar.
# - Yoksa ve TRM_PRODUCTS.csv varsa -> ondan temel bir "pretty" dosyası üretir.
# - Kodlama: Excel'de Türkçe karakterler (ç, ğ, ö, ş, ü) bozulmasın diye utf-8-sig.

import os
import csv

PRODUCTS_CSV = "TRM_PRODUCTS.csv"
PRETTY_CSV = "TRM_REPORT_PRETTY.csv"

def _read_any(path):
    """Dosyayı uygun kodlamayla oku (utf-8/sig olmazsa cp1254 dener)."""
    tried = []
    for enc in ("utf-8", "utf-8-sig", "cp1254", "latin-1"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                data = f.read()
            return data
        except Exception as e:
            tried.append(f"{enc}: {e}")
    raise RuntimeError(f"Dosya okunamadı: {path}\nDenemeler:\n" + "\n".join(tried))

def _rewrite_utf8_sig(text, path):
    """Metni utf-8-sig ile yaz (Excel doğru görsün)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)

def _from_products_make_pretty():
    """TRM_PRODUCTS.csv'den basit bir PRETTY üret. Sütunlar yoksa eldeki kadarını taşır."""
    if not os.path.exists(PRODUCTS_CSV):
        print("Uyarı: TRM_PRODUCTS.csv bulunamadı; atlanıyor.")
        return False

    # TRM_PRODUCTS.csv'i oku
    raw = _read_any(PRODUCTS_CSV).splitlines()
    rows = list(csv.reader(raw))
    if not rows:
        print("Uyarı: TRM_PRODUCTS.csv boş; atlanıyor.")
        return False

    header = [h.strip() for h in rows[0]]
    data = rows[1:]

    # İsimleri normalize et
    def first_match(*names):
        for n in names:
            if n in header:
                return n
        return None

    sku_col   = first_match("sku", "SKU", "id", "product_id")
    name_col  = first_match("name", "title", "product_name")
    price_col = first_match("price", "Price", "sale_price", "regular_price")
    comm_col  = first_match("commission", "commission_rate")
    est_col   = first_match("estimated_commission", "estimated_commission_usd", "estimated")
    est_try   = first_match("estimated_commission_try", "estimated_try")

    # Çıkış başlığı
    out_header = ["sku","name","price","commission","estimated_commission","estimated_commission_try"]

    with open(PRETTY_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(out_header)
        for r in data:
            def val(col):
                if col is None: return ""
                idx = header.index(col)
                return r[idx] if idx < len(r) else ""

            w.writerow([
                val(sku_col),
                val(name_col),
                val(price_col),
                val(comm_col),
                val(est_col),
                val(est_try),
            ])

    print(f"PRETTY üretildi: {PRETTY_CSV} (utf-8-sig) — {len(data)} satır")
    return True

def main():
    if os.path.exists(PRETTY_CSV):
        # Varsa yeniden kodla
        txt = _read_any(PRETTY_CSV)
        _rewrite_utf8_sig(txt, PRETTY_CSV)
        print(f"{PRETTY_CSV} yeniden yazıldı (utf-8-sig).")
    else:
        # Yoksa PRODUCTS'tan üret
        ok = _from_products_make_pretty()
        if not ok:
            print("Uyarı: PRETTY dosyası üretilemedi.")

if __name__ == "__main__":
    main()
