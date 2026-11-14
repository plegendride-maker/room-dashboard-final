import json, os, re
from datetime import datetime, timezone, timedelta
from html import escape
import boto3

table = boto3.resource("dynamodb").Table("ApartmentRooms")
s3 = boto3.client("s3")
BUCKET = os.environ.get("BUCKET", "")          # ชื่อ S3 bucket (ตั้งใน Environment variables)
PREFIX = os.environ.get("PREFIX", "reports/")  # โฟลเดอร์ใน bucket
TH = timezone(timedelta(hours=7))              # เวลาไทย


def scan_all():
    items, kwargs = [], {}
    while True:
        r = table.scan(**kwargs)
        items += r["Items"]
        if "LastEvaluatedKey" not in r:
            return items
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def summarize(items):
    """สรุปเฉพาะห้องเช่า (ไม่รวมห้องเจ้าของ) ใช้กติกาเดียวกับหน้ารายงานผู้ดูแล"""
    floors = {}
    for r in items:
        if not r.get("is_rentable"):
            continue
        f = int(r["floor"])
        fl = floors.setdefault(f, {"floor": f, "rentable": 0, "vacant": 0, "occupied": 0,
                                   "unknown": 0, "income": 0, "vacant_rooms": []})
        st = str(r.get("status", "")).lower()
        price = int(r["price"]) if r.get("price") is not None else 0
        fl["rentable"] += 1
        if st == "vacant":
            fl["vacant"] += 1
            size = float(r["size_sqm"]) if r.get("size_sqm") is not None else None
            fl["vacant_rooms"].append({"room_id": r["room_id"], "price": price, "size_sqm": size})
        elif st == "occupied":
            fl["occupied"] += 1
            fl["income"] += price
        else:
            fl["unknown"] += 1
    fl_list = [floors[k] for k in sorted(floors)]
    for fl in fl_list:
        fl["vacant_rooms"].sort(key=lambda x: x["room_id"])
        fl["occupancy_pct"] = round(fl["occupied"] / fl["rentable"] * 100, 1) if fl["rentable"] and not fl["unknown"] else None
    t = {k: sum(f[k] for f in fl_list) for k in ("rentable", "vacant", "occupied", "unknown", "income")}
    t["occupancy_pct"] = round(t["occupied"] / t["rentable"] * 100, 1) if t["rentable"] and not t["unknown"] else None
    return t, fl_list


def render_html(report):
    def pct(v):
        return "-" if v is None else f"{v:.1f}%"
    rows = "".join(
        f"<tr><td>{f['floor']}</td><td>{f['rentable']}</td><td>{f['occupied']}</td><td>{f['vacant']}</td>"
        f"<td>{pct(f['occupancy_pct'])}</td><td>{f['income']:,}</td></tr>" for f in report["floors"])
    t = report["totals"]
    rows += (f"<tr class='t'><td>รวม</td><td>{t['rentable']}</td><td>{t['occupied']}</td><td>{t['vacant']}</td>"
             f"<td>{pct(t['occupancy_pct'])}</td><td>{t['income']:,}</td></tr>")
    vac = "".join(f"<li>{escape(v['room_id'])} (ชั้น {f['floor']}) {v['price']:,} บาท</li>"
                  for f in report["floors"] for v in f["vacant_rooms"]) or "<li>ไม่มีห้องว่าง</li>"
    return f"""<!doctype html><html lang="th"><head><meta charset="utf-8"><title>รายงานสรุปรายเดือน {escape(report['month'])}</title>
<style>body{{font-family:sans-serif;max-width:720px;margin:24px auto;padding:0 16px;color:#1b2430}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #cbd3dd;padding:6px 10px;text-align:right}}
th:first-child,td:first-child{{text-align:left}}th{{background:#eef2f7}}tr.t td{{font-weight:700;background:#f6f8fb}}
small{{color:#5b6675}}</style></head><body>
<h1>รายงานสรุปรายเดือน {escape(report['month'])}</h1>
<p><b>Occupancy {pct(t['occupancy_pct'])}</b> ({t['occupied']} จาก {t['rentable']} ห้องเช่า) · รายได้ค่าเช่าประมาณ <b>{t['income']:,} บาท/เดือน</b></p>
<table><tr><th>ชั้น</th><th>ห้องเช่า</th><th>มีผู้เช่า</th><th>ว่าง</th><th>Occupancy</th><th>รายได้ (บาท)</th></tr>{rows}</table>
<h2>ห้องว่าง ({t['vacant']} ห้อง)</h2><ul>{vac}</ul>
<p><small>บันทึก ณ {escape(report['generated_at'])} · รายได้คำนวณจากราคาห้องที่มีผู้เช่า เป็นค่าประมาณ ไม่ใช่เงินที่รับจริง</small></p>
</body></html>"""


def lambda_handler(event, context):
    if not BUCKET:
        raise RuntimeError("ยังไม่ได้ตั้ง Environment variable ชื่อ BUCKET")
    now = datetime.now(TH)
    month = (event or {}).get("month") or now.strftime("%Y-%m")  # ทดสอบเดือนอื่นได้: {"month": "2026-10"}
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("month ต้องอยู่ในรูปแบบ YYYY-MM เช่น 2026-11")
    totals, floors = summarize(scan_all())
    report = {"month": month, "generated_at": now.isoformat(timespec="seconds"),
              "totals": totals, "floors": floors}
    keys = {f"{PREFIX}{month}.json": ("application/json; charset=utf-8",
                                      json.dumps(report, ensure_ascii=False, indent=2)),
            f"{PREFIX}{month}.html": ("text/html; charset=utf-8", render_html(report))}
    for key, (ctype, body) in keys.items():
        s3.put_object(Bucket=BUCKET, Key=key, Body=body.encode("utf-8"), ContentType=ctype)
    return {"saved": [f"s3://{BUCKET}/{k}" for k in keys], "month": month,
            "occupancy_pct": totals["occupancy_pct"], "income": totals["income"]}
