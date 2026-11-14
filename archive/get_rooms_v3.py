import json, os, base64, hmac, hashlib, time
from html import escape
from urllib.parse import parse_qs
import boto3

table = boto3.resource("dynamodb").Table("ApartmentRooms")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
COOKIE_FLAGS = "Path=/; HttpOnly; Secure; SameSite=Lax"

STATUS_TH = {
    "vacant": "ว่าง",
    "occupied": "มีผู้เช่า",
    "unknown": "ยังไม่ระบุ",
    "owner": "ห้องเจ้าของ",
}


STYLE = """
*{box-sizing:border-box}
body{margin:0;background:#eef1f6;color:#1b2540;font-family:"Prompt","Noto Sans Thai",system-ui,-apple-system,sans-serif;line-height:1.5}
a{color:inherit;text-decoration:none}
.nav{background:linear-gradient(160deg,#1e3a8a,#3b5bdb);color:#fff;padding:0 20px;min-height:60px;display:flex;align-items:center;gap:22px;flex-wrap:wrap}
.nav .logo{font-weight:700;font-size:17px;padding:14px 0}
.nav .lk{font-size:14px;opacity:.85;padding:19px 0;border-bottom:3px solid transparent}
.nav .lk.on{opacity:1;font-weight:600;border-bottom-color:#fff}
.nav .sp{flex:1}
.nav .nb{background:#fff;color:#1e3a8a;border:0;border-radius:20px;padding:7px 18px;font:inherit;font-size:13px;font-weight:600;cursor:pointer}
.nav form{margin:0}
.w{max-width:1100px;margin:0 auto;padding:22px 16px}
.card{background:#fff;border-radius:18px;padding:20px;box-shadow:0 6px 20px rgba(30,58,138,.10);margin-bottom:18px}
.card h3{margin:0 0 12px;font-size:16px;font-weight:600}
.hero{display:grid;grid-template-columns:300px 1fr;gap:18px;margin-bottom:18px}
.hero .card{margin:0}
.dn{display:grid;place-items:center;text-align:center}
.ring{width:190px;height:190px;border-radius:50%;display:grid;place-items:center;margin:6px auto}
.ring div{width:140px;height:140px;border-radius:50%;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center}
.ring b{font-size:34px;color:#1e3a8a;line-height:1.1}
.ring b.w2{font-size:20px}
.ring small{font-size:12px;color:#5d6b8a}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.stats div{background:#eef1f6;border-radius:14px;padding:12px;text-align:center}
.stats small{display:block;font-size:12px;color:#5d6b8a}
.stats b{font-size:26px;font-weight:600}
.g{color:#1f8a4c}.r{color:#d4483b}.m{color:#667085}
.fl{display:flex;align-items:flex-start;gap:12px;padding:9px 0;border-bottom:1px solid #eef1f6}
.fl:last-of-type{border-bottom:0}
.fl>b{width:46px;flex:none;font-size:13px;padding-top:6px}
.t{display:flex;flex-wrap:wrap;gap:6px}
.t i{font-style:normal;width:48px;height:32px;border-radius:8px;font-size:11px;font-weight:600;display:flex;align-items:center;justify-content:center;color:#fff}
.t .vacant{background:#2f9e5e}
.t .occupied{background:#d4483b}
.t .unknown{background:#fff;border:1px dashed #9aa5b8;color:#7d8aa5}
.t .owner{background:#9aa5b8}
.lg{display:flex;gap:14px;font-size:12px;color:#5d6b8a;margin-top:10px;flex-wrap:wrap}
.lg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.fh{display:flex;justify-content:space-between;border-bottom:2px solid #1e3a8a;padding-bottom:4px;margin:14px 0 8px;font-size:14px}
.fh span{font-size:12px;color:#5d6b8a}
.vl{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}
.vr{background:#eef1f6;border-radius:14px;padding:10px 14px;display:flex;align-items:center;gap:10px;border-left:5px solid #2f9e5e}
.vr b{color:#1f8a4c;font-size:16px}
.vr span{flex:1;font-size:12px;color:#5d6b8a}
.vr em{font-style:normal;font-weight:600;font-size:13px;white-space:nowrap}
.none{font-size:12px;color:#667085}
.ar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:7px 0;border-bottom:1px solid #eef1f6}
.rid{width:50px;font-weight:600;font-size:13px}
.bd{font-size:11px;border-radius:10px;padding:2px 8px;width:80px;text-align:center}
.bd.vacant{background:#e3f6ea;color:#1f8a4c}
.bd.occupied{background:#fdeceb;color:#d4483b}
.bd.unknown{background:#eef1f6;color:#667085}
.bt{display:flex;gap:6px;margin-left:auto}
.b{font:inherit;font-size:12px;padding:6px 12px;border:1px solid #c3cbe0;background:#fff;border-radius:16px;color:#1b2540;cursor:pointer}
.b.on{background:#3b5bdb;border-color:#3b5bdb;color:#fff}
.foot{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:12px;color:#5d6b8a;margin-top:6px;flex-wrap:wrap}
.foot a{color:#3b5bdb}
.lo{font:inherit;font-size:12px;border:1px solid #c3cbe0;background:#fff;border-radius:16px;padding:6px 14px;cursor:pointer}
.login{max-width:360px;margin:50px auto}
.login h3{margin-bottom:6px}
.login input{width:100%;font:inherit;padding:11px 14px;border:1px solid #c3cbe0;border-radius:12px;margin:8px 0}
.login button{width:100%;font:inherit;padding:11px;border:0;border-radius:20px;background:#3b5bdb;color:#fff;cursor:pointer}
.err{color:#d4483b;font-size:13px}
.rtop{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid #1e3a8a;padding-bottom:8px;margin-bottom:14px;gap:8px}
.rtop h1{margin:0;font-size:20px}
.rtop small{display:block;font-size:12px;color:#5d6b8a}
.rtop span{font-size:12px;color:#5d6b8a;text-align:right}
.sec{font-size:13px;font-weight:600;color:#1e3a8a;margin:16px 0 8px}
.rh{display:flex;gap:18px;align-items:center;background:#eef1f6;border-radius:14px;padding:14px 16px}
.big{font-size:34px;font-weight:700;color:#1e3a8a;line-height:1;white-space:nowrap}
.big small{display:block;font-size:12px;font-weight:400;color:#5d6b8a;margin-bottom:4px}
.sb{flex:1}
.stack{display:flex;height:14px;border-radius:7px;overflow:hidden;background:#dfe5f1}
.stack i{display:block;height:100%}
.leg{display:flex;gap:14px;margin-top:8px;font-size:12px;flex-wrap:wrap}
.leg b{font-size:15px}
.leg i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:5px}
.money{margin-top:8px;font-size:13px;color:#5d6b8a}
.money b{color:#1b2540}
.rp{width:100%;border-collapse:collapse;font-size:13px}
.rp th{background:#1e3a8a;color:#fff;text-align:left;padding:8px 10px;font-weight:500}
.rp td{padding:8px 10px;border-bottom:1px solid #eef1f6}
.rp .n{text-align:right}
.rp .tot td{font-weight:700;background:#e8edfa}
.rp td.fl2{font-weight:700;background:#eef1f6;width:60px;vertical-align:top}
.note{font-size:11px;color:#5d6b8a;margin-top:10px;line-height:1.7}
@media(max-width:760px){
.hero{grid-template-columns:1fr}
.stats{grid-template-columns:repeat(2,1fr)}
.fl{flex-direction:column;gap:4px}
.fl>b{padding-top:0}
.t i{width:44px}
.bt{margin-left:0;width:100%}.b{flex:1}
.rh{flex-direction:column;align-items:stretch}
.nav{gap:14px}
}
@media print{body{background:#fff}.noprint{display:none!important}.nav{display:none}.card{box-shadow:none;padding:0}.rp th,.rp .tot td,.stack i,.rh{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

THAI_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
               "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]


# ---------- admin cookie ----------
def make_cookie():
    exp = int(time.time()) + 3600
    sig = hmac.new(ADMIN_KEY.encode(), str(exp).encode(), hashlib.sha256).hexdigest()
    return f"admin={exp}.{sig}; Max-Age=3600; {COOKIE_FLAGS}"


def clear_cookie():
    return f"admin=; Max-Age=0; {COOKIE_FLAGS}"


def verify_token(value):
    exp, _, sig = value.partition(".")
    if not exp.isdigit() or int(exp) < time.time():
        return False
    good = hmac.new(ADMIN_KEY.encode(), exp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig.encode(), good.encode())


def is_admin(event):
    if not ADMIN_KEY:
        return False
    for c in event.get("cookies") or []:
        name, _, value = c.strip().partition("=")
        if name == "admin":
            return verify_token(value)
    return False


def read_form(event):
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return {k: v[0] for k, v in parse_qs(body).items()}


# ---------- data ----------
def scan_all():
    items, kwargs = [], {}
    while True:
        r = table.scan(**kwargs)
        items += r["Items"]
        if "LastEvaluatedKey" not in r:
            return items
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def build_floors():
    floors = {}
    for r in scan_all():
        f = int(r["floor"])
        fl = floors.setdefault(f, {"floor": f, "rentable": 0, "vacant": 0,
                                   "occupied": 0, "unknown": 0, "rooms": []})
        status = str(r.get("status", "")).lower()
        if not r.get("is_rentable"):
            status = "owner"
        else:
            fl["rentable"] += 1
            if status == "vacant":
                fl["vacant"] += 1
            elif status == "occupied":
                fl["occupied"] += 1
            else:
                status = "unknown"
                fl["unknown"] += 1
        price = r.get("price")
        size = r.get("size_sqm")
        fl["rooms"].append({
            "room_id": r["room_id"],
            "price": int(price) if price is not None else None,
            "size_sqm": float(size) if size is not None else None,
            "status": status,
        })
    for fl in floors.values():
        fl["rooms"].sort(key=lambda x: x["room_id"])
    return [floors[k] for k in sorted(floors)]



# ---------- html ----------
FONT = ("<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">")


def page(body):
    return ("<!doctype html><html lang=\"th\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>ห้องว่างและอัตราการเข้าพัก</title>" + FONT +
            "<style>" + STYLE + "</style></head><body>" + body + "</body></html>")


def nav(admin, active="home"):
    def lk(href, label, key):
        on = " on" if active == key else ""
        return f"<a class=\"lk{on}\" href=\"{href}\">{label}</a>"

    out = "<div class=\"nav noprint\"><span class=\"logo\">● Room Dashboard</span>"
    out += lk("/", "ภาพรวม", "home") + lk("/#vacant", "ห้องว่าง", "vacant")
    if admin:
        out += lk("/?report=1", "รายงานสรุป", "report") + lk("/#admin", "จัดการสถานะ", "admin")
    out += "<span class=\"sp\"></span>"
    if admin:
        out += ("<form method=\"post\"><input type=\"hidden\" name=\"action\" value=\"logout\">"
                "<button class=\"nb\">ออกจากระบบ</button></form>")
    else:
        out += "<a class=\"nb\" href=\"/?login=1\">เข้าสู่ระบบผู้ดูแล</a>"
    return out + "</div>"


def chip(r):
    price = f"{r['price']:,} บาท" if r["price"] is not None else "-"
    size = f"{r['size_sqm']:g} ตร.ม." if r["size_sqm"] is not None else "-"
    return (f"<div class=\"vr\"><b>{escape(r['room_id'])}</b>"
            f"<span>{size}</span><em>{price}</em></div>")


def tile_row(fl):
    tiles = "".join(f"<i class=\"{r['status']}\">{escape(r['room_id'])}</i>" for r in fl["rooms"])
    return f"<div class=\"fl\"><b>ชั้น {fl['floor']}</b><div class=\"t\">{tiles}</div></div>"


def vacant_block(fl):
    head = (f"<div class=\"fh\"><b>ชั้น {fl['floor']}</b>"
            f"<span>ว่าง {fl['vacant']} จาก {fl['rentable']} ห้อง</span></div>")
    vacants = [r for r in fl["rooms"] if r["status"] == "vacant"]
    if vacants:
        return head + "<div class=\"vl\">" + "".join(chip(r) for r in vacants) + "</div>"
    if fl["unknown"]:
        return head + f"<div class=\"none\">ยังไม่ระบุสถานะ {fl['unknown']} ห้อง</div>"
    return head + "<div class=\"none\">ไม่มีห้องว่าง</div>"


def admin_row(r):
    rid = escape(r["room_id"])

    def btn(val, label):
        on = " on" if r["status"] == val else ""
        return f"<button class=\"b{on}\" name=\"status\" value=\"{val}\">{label}</button>"

    return ("<form method=\"post\" class=\"ar\">"
            "<input type=\"hidden\" name=\"action\" value=\"set\">"
            f"<input type=\"hidden\" name=\"room_id\" value=\"{rid}\">"
            f"<span class=\"rid\">{rid}</span>"
            f"<span class=\"bd {r['status']}\">{STATUS_TH[r['status']]}</span>"
            f"<span class=\"bt\">{btn('vacant', 'ว่าง')}{btn('occupied', 'มีผู้เช่า')}</span>"
            "</form>")


def admin_block(floors):
    out = "<div id=\"admin\" class=\"card\"><h3>จัดการสถานะห้อง (ผู้ดูแล)</h3>"
    for fl in floors:
        out += f"<div class=\"fh\"><b>ชั้น {fl['floor']}</b><span>{fl['rentable']} ห้องเช่า</span></div>"
        out += "".join(admin_row(r) for r in fl["rooms"] if r["status"] != "owner")
    return out + "</div>"


def occ_text(rentable, occupied, unknown):
    if rentable and unknown == 0:
        return f"{occupied / rentable * 100:.1f}%"
    return "รอข้อมูล"


def render(floors, admin):
    rentable = sum(f["rentable"] for f in floors)
    vacant = sum(f["vacant"] for f in floors)
    occupied = sum(f["occupied"] for f in floors)
    unknown = sum(f["unknown"] for f in floors)
    known = rentable > 0 and unknown == 0
    if known:
        pct = occupied / rentable * 100
        big = f"<b>{pct:.1f}%</b>"
        sub = f"{occupied} จาก {rentable} ห้อง"
        ring = f"background:conic-gradient(#3b5bdb {pct * 3.6:.1f}deg,#e4e9f5 0)"
    else:
        big = "<b class=\"w2\">รอข้อมูล</b>"
        sub = "ระบุสถานะยังไม่ครบ"
        ring = "background:#e4e9f5"

    donut = ("<div class=\"card dn\"><h3>อัตราการเข้าพัก</h3>"
             f"<div class=\"ring\" style=\"{ring}\"><div>{big}<small>{sub}</small></div></div></div>")

    stats = ("<div class=\"stats\">"
             f"<div><small>ห้องเช่า</small><b>{rentable}</b></div>"
             f"<div><small>มีผู้เช่า</small><b class=\"r\">{occupied}</b></div>"
             f"<div><small>ห้องว่าง</small><b class=\"g\">{vacant}</b></div>"
             f"<div><small>ยังไม่ระบุ</small><b class=\"m\">{unknown}</b></div></div>")

    plan = ("<div class=\"card\">" + stats + "<h3>ผังห้องทั้งตึก</h3>"
            + "".join(tile_row(fl) for fl in reversed(floors))
            + "<div class=\"lg\">"
              "<span><i style=\"background:#2f9e5e\"></i>ว่าง</span>"
              "<span><i style=\"background:#d4483b\"></i>มีผู้เช่า</span>"
              "<span><i style=\"border:1px dashed #9aa5b8\"></i>ยังไม่ระบุ</span>"
              "<span><i style=\"background:#9aa5b8\"></i>ห้องเจ้าของ</span></div></div>")

    vac = ("<div id=\"vacant\" class=\"card\"><h3>ห้องว่างแต่ละชั้น</h3>"
           + "".join(vacant_block(fl) for fl in floors) + "</div>")

    extra = admin_block(floors) if admin else ""
    foot = ("<div class=\"foot\"><span>ข้อมูลจาก DynamoDB"
            + (" · โหมดผู้ดูแล (หมดอายุใน 1 ชั่วโมง)" if admin else "") + "</span></div>")

    return page(nav(admin, "home") + "<div class=\"w\"><div class=\"hero\">" + donut + plan
                + "</div>" + vac + extra + foot + "</div>")


def render_login(error=""):
    msg = f"<div class=\"err\">{escape(error)}</div>" if error else ""
    return page(nav(False, "") + "<div class=\"w\"><div class=\"card login\"><h3>เข้าสู่ระบบผู้ดูแล</h3>"
                "<form method=\"post\">"
                "<input type=\"hidden\" name=\"action\" value=\"login\">"
                "<label>รหัสผู้ดูแล</label>"
                "<input type=\"password\" name=\"key\" autocomplete=\"current-password\" autofocus>"
                + msg + "<button>เข้าสู่ระบบ</button></form>"
                "<div class=\"foot\" style=\"margin-top:12px\"><a href=\"/\">กลับหน้าหลัก</a></div></div></div>")


def render_report(floors, admin):
    t = time.gmtime(time.time() + 7 * 3600)  # เวลาไทย (UTC+7)
    month = f"{THAI_MONTHS[t.tm_mon - 1]} {t.tm_year + 543}"
    stamp = time.strftime("%d/%m/%Y %H:%M", t)

    rentable = sum(f["rentable"] for f in floors)
    vacant = sum(f["vacant"] for f in floors)
    occupied = sum(f["occupied"] for f in floors)
    unknown = sum(f["unknown"] for f in floors)

    def income(fl):
        return sum(r["price"] for r in fl["rooms"]
                   if r["status"] == "occupied" and r["price"])

    total_income = sum(income(f) for f in floors)

    def pct(n):
        return f"{n / rentable * 100:.1f}" if rentable else "0"

    big = occ_text(rentable, occupied, unknown)
    wait = "<br><small style=\"margin:4px 0 0\">ระบุสถานะยังไม่ครบ</small>" if big == "รอข้อมูล" else ""
    hero = ("<div class=\"rh\"><div class=\"big\"><small>Occupancy</small>" + big + wait + "</div>"
            "<div class=\"sb\"><div class=\"stack\">"
            f"<i style=\"width:{pct(occupied)}%;background:#d4483b\"></i>"
            f"<i style=\"width:{pct(vacant)}%;background:#2f9e5e\"></i>"
            f"<i style=\"width:{pct(unknown)}%;background:#9aa5b8\"></i></div>"
            "<div class=\"leg\">"
            f"<span><i style=\"background:#d4483b\"></i>มีผู้เช่า <b>{occupied}</b></span>"
            f"<span><i style=\"background:#2f9e5e\"></i>ว่าง <b>{vacant}</b></span>"
            f"<span><i style=\"background:#9aa5b8\"></i>ยังไม่ระบุ <b>{unknown}</b></span></div>"
            f"<div class=\"money\">รายได้ค่าเช่า <b>{total_income:,} บาท/เดือน</b></div>"
            "</div></div>")

    rows = ""
    for fl in floors:
        rows += (f"<tr><td>{fl['floor']}</td><td class=\"n\">{fl['rentable']}</td>"
                 f"<td class=\"n\">{fl['occupied']}</td><td class=\"n\">{fl['vacant']}</td>"
                 f"<td class=\"n\">{occ_text(fl['rentable'], fl['occupied'], fl['unknown'])}</td>"
                 f"<td class=\"n\">{income(fl):,}</td></tr>")
    rows += (f"<tr class=\"tot\"><td>รวม</td><td class=\"n\">{rentable}</td>"
             f"<td class=\"n\">{occupied}</td><td class=\"n\">{vacant}</td>"
             f"<td class=\"n\">{occ_text(rentable, occupied, unknown)}</td>"
             f"<td class=\"n\">{total_income:,}</td></tr>")
    summary = ("<table class=\"rp\"><tr><th>ชั้น</th><th class=\"n\">ห้องเช่า</th>"
               "<th class=\"n\">มีผู้เช่า</th><th class=\"n\">ว่าง</th>"
               "<th class=\"n\">Occupancy</th><th class=\"n\">รายได้ (บาท)</th></tr>"
               + rows + "</table>")

    vrows = ""
    for fl in floors:
        rooms = [r for r in fl["rooms"] if r["status"] == "vacant"]
        for i, r in enumerate(rooms):
            price = f"{r['price']:,}" if r["price"] is not None else "-"
            size = f"{r['size_sqm']:g}" if r["size_sqm"] is not None else "-"
            first = (f"<td class=\"fl2\" rowspan=\"{len(rooms)}\">{fl['floor']}</td>" if i == 0 else "")
            vrows += (f"<tr>{first}<td><b>{escape(r['room_id'])}</b></td>"
                      f"<td class=\"n\">{price}</td><td class=\"n\">{size}</td></tr>")
    if vrows:
        vtable = ("<table class=\"rp\"><tr><th>ชั้น</th><th>ห้อง</th><th class=\"n\">ราคา (บาท)</th>"
                  "<th class=\"n\">ขนาด (ตร.ม.)</th></tr>" + vrows + "</table>")
    else:
        vtable = "<div class=\"none\">ไม่มีห้องว่าง</div>"

    note = ("Occupancy = ห้องมีผู้เช่า ÷ ห้องเช่าทั้งหมด (ไม่นับห้องเจ้าของ P211) "
            "และจะแสดงเป็นตัวเลขเมื่อระบุสถานะครบทุกห้อง · "
            "รายได้ค่าเช่า = ผลรวมราคาของห้องที่มีผู้เช่า")
    buttons = ("<div class=\"foot noprint\" style=\"margin-top:14px\"><a href=\"/\">กลับหน้าหลัก</a>"
               "<button class=\"lo\" onclick=\"window.print()\">พิมพ์ / บันทึกเป็น PDF</button></div>")

    return page(nav(True, "report") + "<div class=\"w\"><div class=\"card\">"
                "<div class=\"rtop\"><div><h1>รายงานสรุปห้องพัก</h1>"
                f"<small>ประจำเดือน {month}</small></div>"
                f"<span>ข้อมูล ณ {stamp}<br>ห้องเช่า {rentable} ห้อง</span></div>"
                "<div class=\"sec\" style=\"margin-top:0\">1. ภาพรวม</div>" + hero +
                "<div class=\"sec\">2. สรุปรายชั้น</div>" + summary +
                f"<div class=\"sec\">3. ห้องว่าง ({vacant} ห้อง)</div>" + vtable +
                f"<div class=\"note\">{note}</div>" + buttons + "</div></div>")


# ---------- responses ----------
def reply(status, body, content_type="text/html; charset=utf-8", cookies=None):
    res = {"statusCode": status,
           "headers": {"Content-Type": content_type, "Cache-Control": "no-store"},
           "body": body}
    if cookies:
        res["cookies"] = cookies
    return res


def redirect(location="/", cookies=None):
    res = {"statusCode": 303, "headers": {"Location": location, "Cache-Control": "no-store"}, "body": ""}
    if cookies:
        res["cookies"] = cookies
    return res


# ---------- handler ----------
def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    qs = event.get("queryStringParameters") or {}

    if method == "POST":
        form = read_form(event)
        action = form.get("action")

        if action == "login":
            key = form.get("key", "")
            if ADMIN_KEY and hmac.compare_digest(key.encode(), ADMIN_KEY.encode()):
                return redirect("/#admin", [make_cookie()])
            return reply(401, render_login("รหัสไม่ถูกต้อง"))

        if action == "logout":
            return redirect("/", [clear_cookie()])

        if action == "set":
            if not is_admin(event):
                return reply(401, render_login("กรุณาเข้าสู่ระบบอีกครั้ง"))
            room_id = form.get("room_id", "")
            status = form.get("status", "")
            if status not in ("vacant", "occupied"):
                return reply(400, "invalid status", "text/plain; charset=utf-8")
            item = table.get_item(Key={"room_id": room_id}).get("Item")
            if not item or not item.get("is_rentable"):
                return reply(400, "invalid room", "text/plain; charset=utf-8")
            table.update_item(
                Key={"room_id": room_id},
                UpdateExpression="SET #s = :s",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": status})
            return redirect("/#admin")

        return reply(400, "bad request", "text/plain; charset=utf-8")

    if qs.get("login") == "1":
        return reply(200, render_login())

    floors = build_floors()
    if qs.get("format") == "json":
        return reply(200, json.dumps(floors, ensure_ascii=False),
                     "application/json; charset=utf-8")
    if qs.get("report") == "1":
        if not is_admin(event):
            return reply(401, render_login("กรุณาเข้าสู่ระบบผู้ดูแลเพื่อดูรายงาน"))
        return reply(200, render_report(floors, True))
    return reply(200, render(floors, is_admin(event)))
