with open("TRM_REPORT_PRETTY.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sku", "name", "price", "commission", "estimated_commission", "estimated_commission_try"])
    writer.writerows(rows)
