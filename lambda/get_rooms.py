import json, os, re, base64, hmac, hashlib, time, math
from html import escape
from urllib.parse import parse_qs
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("ApartmentRooms")
login_table = dynamodb.Table(os.environ.get("LOGIN_TABLE", "LoginAttempts"))  # ตารางนับครั้งล็อกอินผิด (แยกจากข้อมูลห้อง)
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
REPORT_BUCKET = os.environ.get("REPORT_BUCKET", "")          # S3 bucket เก็บรายงานรายเดือน (ว่าง = ปิดส่วนรายงานย้อนหลัง)
REPORT_PREFIX = os.environ.get("REPORT_PREFIX", "reports/")  # โฟลเดอร์ใน bucket (ตรงกับ Lambda save-monthly-report)
MONTH_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
COOKIE_FLAGS = "Path=/; HttpOnly; Secure; SameSite=Lax"
DEFAULT_SIZE = 26.3  # ใช้คำนวณความกว้างช่องในผังเมื่อห้องไม่มีข้อมูลขนาด

STATUS_TH = {
    "vacant": "ว่าง",
    "occupied": "มีผู้เช่า",
    "unknown": "ยังไม่ระบุ",
    "owner": "ห้องเจ้าของ",
}

STYLE = """
*{box-sizing:border-box}
html,body{min-height:100%}
body{min-height:100vh;display:flex;flex-direction:column;margin:0;background:#eef1f6;color:#1b2540;font-family:"Prompt","Noto Sans Thai",system-ui,-apple-system,sans-serif;line-height:1.5}
a{color:inherit;text-decoration:none}
.nav{background:linear-gradient(160deg,#1e3a8a,#3b5bdb);color:#fff}
.ni{max-width:1180px;margin:0 auto;padding:0 24px;min-height:60px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.nav .logo{font-weight:700;font-size:17px}
.nav .nb{background:rgba(255,255,255,.18);color:#fff;border:0;border-radius:20px;padding:7px 16px;font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}
.nav form{margin:0}
.tabs{background:#fff;border-bottom:1px solid #dbe2f0;overflow-x:auto}
.ti{max-width:1180px;margin:0 auto;padding:0 16px;display:flex;min-width:max-content}
.tabs a{font-weight:600;font-size:15px;color:#5d6b8a;padding:12px 22px;border-bottom:3px solid transparent;white-space:nowrap}
.tabs a.on{color:#1e3a8a;border-color:#1e3a8a}
.tabs a.adm{color:#7a5b00}
.tabs a.adm.on{border-color:#7a5b00}
.w{max-width:1180px;width:100%;margin:20px auto;padding:0 16px;display:grid;grid-template-columns:330px 1fr;gap:18px;align-items:stretch;flex:1}
.w1{grid-template-columns:1fr}
.pw{grid-template-columns:1fr 1fr;align-items:stretch}
.vg{display:grid;grid-template-columns:1fr;grid-auto-rows:1fr;gap:10px;flex:1}
.vg>div{display:flex;flex-direction:column}
.vg .its{flex:1;display:flex;flex-wrap:wrap;gap:12px;align-items:stretch;margin-top:10px}
.vg .none{flex:1;display:flex;align-items:center}
.vcard{display:flex;flex-direction:column}
.vg .it{padding:14px 24px;font-size:17px;align-items:center;min-width:260px;flex:0 1 300px}
.vg .it span{font-size:14px}
.vg .it b{font-size:20px}
.vg .fh{margin-top:4px}
.rcol{display:flex;flex-direction:column;gap:18px;min-width:0}
.card{background:#fff;border-radius:18px;padding:20px;box-shadow:0 6px 20px rgba(30,58,138,.10);min-width:0}
.card h3{margin:0 0 4px;font-size:17px;font-weight:600}
.sub{color:#5d6b8a;font-size:13px;margin-bottom:10px}
.bigv{font-size:50px;font-weight:700;color:#2f9e5e;line-height:1}
.bigv span{font-size:18px;color:#1b2540;font-weight:400}
.g{border:1px solid #dbe2f0;border-radius:14px;padding:12px;margin-top:12px}
.gs{font-weight:600}
.gn{font-size:32px;font-weight:700;color:#2f9e5e;line-height:1.2}
.gn span{font-size:14px;color:#1b2540;font-weight:400}
.gp{color:#5d6b8a;font-size:13px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:6px 0 16px}
.stats div{background:#eef1f6;border-radius:14px;padding:12px;text-align:center}
.stats small{display:block;font-size:13px;color:#5d6b8a}
.stats b{font-size:34px;font-weight:600}
.r{color:#d4483b}.gg{color:#1f8a4c}.m{color:#667085}
.dn{display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center}
.dn h3{align-self:flex-start}
.badge{font-size:12px;background:#fff3cd;color:#7a5b00;border-radius:20px;padding:3px 10px;font-weight:600}
.ring{width:190px;height:190px;border-radius:50%;display:flex;align-items:center;justify-content:center}
.ring>div{width:132px;height:132px;border-radius:50%;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center}
.ring b{font-size:34px;color:#1e3a8a;line-height:1.1}
.ring b.w2{font-size:20px}
.ring small{font-size:12px;color:#5d6b8a}
.fl{display:flex;gap:10px;margin-bottom:14px;align-items:stretch;flex:1}
.fn{align-self:center}
.mapc{display:flex;flex-direction:column}
.fn{width:50px;font-weight:600;font-size:15px;flex:none}
.rooms{display:flex;gap:4px;flex:1;min-width:0}
.rm{height:auto;min-height:88px;border-radius:8px;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:0;overflow:hidden}
.rm b{font-size:18px;margin-bottom:6px}
.rm small{font-size:13px;line-height:1.5}
.rm .sz{opacity:.85}
.rm .ph{visibility:hidden}
.rm .ow{font-size:12px}
.rm.vacant{background:#2f9e5e}
.rm.occupied{background:#d4483b}
.rm.owner{background:#9aa5b8}
.rm.unknown{background:#fff;border:1px dashed #9aa5b8;color:#7d8aa5}
.rm.gy{background:#dfe4ee;color:#6b7690}
.lg{display:flex;gap:16px;font-size:12px;color:#5d6b8a;margin-top:8px;flex-wrap:wrap}
.lg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.fh{display:flex;justify-content:space-between;border-bottom:2px solid #1e3a8a;margin:14px 0 8px;padding-bottom:4px;font-size:14px}
.fh span{color:#5d6b8a;font-size:13px}
.its{display:flex;gap:8px;flex-wrap:wrap}
.it{display:flex;gap:10px;align-items:baseline;background:#edf0f6;border-left:4px solid #2f9e5e;border-radius:10px;padding:8px 14px;min-width:200px;justify-content:space-between}
.it b{color:#2f9e5e}
.it span{color:#5d6b8a;font-size:12px}
.it em{font-style:normal;font-weight:700}
.none{font-size:13px;color:#667085}
.pc{display:flex;flex-direction:column;align-items:center}
.pc h3,.pc .sub{align-self:flex-start}
.pc svg{max-width:100%;height:auto}
.pc{padding:24px}
.note{font-size:12px;color:#5d6b8a;margin-top:12px}
.mg{display:grid;grid-template-columns:1fr 1fr;gap:0 24px}
.ar{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #e3e8f1;margin:0}
.rid{font-weight:700;width:52px}
.bd{font-size:12px;padding:2px 10px;border-radius:12px;color:#fff;width:74px;text-align:center}
.bd.vacant{background:#2f9e5e}
.bd.occupied{background:#d4483b}
.bd.unknown{background:#9aa5b8}
.bt{margin-left:auto;display:flex;gap:6px}
.rb{position:relative;cursor:pointer}
.rb input{position:absolute;opacity:0;width:0;height:0}
.rb span{display:block;font-size:13px;font-weight:600;padding:5px 12px;border-radius:14px;border:1px solid #c9d2e6;color:#5d6b8a;background:#fff}
.rb input:checked+span{background:#3b5bdb;border-color:#3b5bdb;color:#fff}
.rb input:focus-visible+span{outline:2px solid #1e3a8a;outline-offset:2px}
.ar.chg{background:#fff8e1}
.ok{background:#e6f6ec;color:#1f7a45;border-radius:10px;padding:10px 14px;margin:8px 0;font-weight:600;font-size:14px}
.sbar{position:sticky;bottom:0;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;background:#fff;border-top:2px solid #e3e8f1;padding:12px 0;margin-top:14px}
#cnt{font-size:14px;color:#5d6b8a}
.sbtn{display:flex;gap:8px}
.cx,.sv{font:inherit;font-size:14px;font-weight:600;border-radius:20px;padding:9px 20px;cursor:pointer}
.cx{background:#fff;border:1px solid #c9d2e6;color:#5d6b8a}
.sv{background:#3b5bdb;border:1px solid #3b5bdb;color:#fff}
.sv:disabled{background:#c9d2e6;border-color:#c9d2e6;cursor:not-allowed}
.foot{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:12px;color:#5d6b8a;margin-top:6px;flex-wrap:wrap}
.foot a{color:#3b5bdb}
.lo{font:inherit;font-size:14px;border:0;background:#3b5bdb;color:#fff;border-radius:20px;padding:9px 18px;cursor:pointer}
.login{max-width:360px;width:100%;margin:50px auto;align-self:start}
.login input{width:100%;font:inherit;padding:11px 14px;border:1px solid #c3cbe0;border-radius:12px;margin:8px 0}
.login button{width:100%;font:inherit;padding:11px;border:0;border-radius:20px;background:#3b5bdb;color:#fff;cursor:pointer}
.err{color:#d4483b;font-size:13px}
.rtop{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;border-bottom:2px solid #1e3a8a;padding-bottom:12px}
.rtop h1{margin:0;font-size:22px}
.rtop small,.rtop>span{color:#5d6b8a;font-size:13px}
.rtop>span{text-align:right}
.sec{font-weight:700;color:#1e3a8a;margin:20px 0 10px}
.rh{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.rh .bg{font-size:46px;font-weight:700;color:#1e3a8a;line-height:1;white-space:nowrap}
.rh .bg small{display:block;font-size:13px;color:#5d6b8a;font-weight:400}
.sb{flex:1;min-width:220px}
.stack{display:flex;height:14px;border-radius:7px;overflow:hidden;background:#e3e8f1}
.stack i{display:block}
.leg{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;margin-top:8px}
.leg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px}
.money{margin-top:8px;font-size:14px}
.money b{color:#1e3a8a;font-size:18px}
.tw{overflow-x:auto}
.rp{width:100%;border-collapse:collapse;font-size:14px}
.rp th{background:#eef1f6;text-align:left;padding:8px 10px;font-weight:600}
.rp td{padding:8px 10px;border-bottom:1px solid #e3e8f1}
.rp .n{text-align:right}
.rp .tot td{font-weight:700;background:#f5f7fc}
.rp td.fl2{font-weight:700;vertical-align:top}
.pb{margin-top:16px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.pb a{font-size:14px;padding:9px 18px;border-radius:20px;border:1px solid #3b5bdb;color:#3b5bdb}
.rw{grid-template-columns:minmax(0,1fr) 250px;align-items:start}
.rmain{min-width:0}
.hs{padding:16px}
.hs h3{margin:0 0 8px}
.hs a{display:block;padding:7px 10px;border-radius:10px;font-size:14px;color:#3b5bdb}
.hs a.on{background:#e8eefc;color:#1e3a8a;font-weight:600}
.hs details{margin-top:6px;border-top:1px solid #e3e8f1;padding-top:6px}
.hs summary{cursor:pointer;font-weight:600;font-size:15px;padding:6px 10px}
.hs summary small{color:#5d6b8a;font-weight:400;font-size:12px}
.hs details a{padding-left:22px}
.hn{font-size:13px;color:#5d6b8a;padding:6px 10px}
.hf{font-size:12px;color:#5d6b8a;margin-top:14px;padding:0 4px;display:flex;gap:4px}
.stag{background:#e8eefc;color:#1e3a8a;border-radius:10px;padding:1px 8px;font-size:12px;margin-left:6px}
@media(max-width:700px){
.ni{padding:12px 16px}
.vg{grid-auto-rows:auto}.vg .its{flex:none}.vg .it{padding:8px 14px;min-width:100%;flex:none}
.w,.pw{grid-template-columns:1fr;padding:0 16px;margin:14px auto;gap:14px}
.card{padding:16px}
.rooms{display:grid;grid-template-columns:repeat(5,1fr)}
.rm{height:58px;min-height:0}.fl{flex:none}.rm b{font-size:13px;margin-bottom:0}.rm small{font-size:9px;line-height:1.25}.fn{font-size:14px}
.fl{display:block}.fn{width:auto;margin:6px 0 4px}
.stats{gap:6px}.stats div{padding:8px 2px}.stats b{font-size:22px}.stats small{font-size:11px}
.it{min-width:100%}
.mg{grid-template-columns:1fr}
.rtop{flex-direction:column}.rtop>span{text-align:left}
.rh .bg{font-size:38px}
.tabs a{padding:12px 14px;font-size:14px}
}
@media print{.rw{grid-template-columns:1fr}body{background:#fff}.noprint{display:none!important}.card{box-shadow:none;padding:0}.rp th,.rp .tot td,.stack i{-webkit-print-color-adjust:exact;print-color-adjust:exact}.w{margin:0;min-height:0}body{display:block}}
"""

THAI_MONTH_SHORT = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
                    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
THAI_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
               "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]

# ขนาดกว้าง x ยาว (เมตร) ของแปลนจำลอง — เป็นภาพประกอบ ไม่ใช่แบบจริงของอาคาร
PLAN_DIMS = {26.3: (3.5, 7.5), 32.0: (4.0, 8.0)}


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


# ---------- จำกัดจำนวนครั้งที่ลองรหัสผิด (ต่อ IP) ----------
MAX_FAILS = 5        # ผิดได้กี่ครั้ง
LOCK_SECONDS = 900   # ล็อก 15 นาที นับจากครั้งแรกที่ผิด


def client_key(event):
    ip = event.get("requestContext", {}).get("http", {}).get("sourceIp", "unknown")
    return hashlib.sha256(ip.encode()).hexdigest()[:16]  # ไม่เก็บ IP จริง


def log_event(name, key, fails):
    """เขียนบันทึกลง CloudWatch Logs ให้ตั้ง metric filter / alarm ได้ (ไม่บันทึกรหัสหรือ IP จริง)"""
    print(json.dumps({"event": name, "client": key, "fails": fails}))


def login_state(key):
    """คืน (จำนวนครั้งที่ผิด, เวลาที่ผิดครั้งแรก) ถ้าหมดเวลาแล้วนับใหม่"""
    try:
        item = login_table.get_item(Key={"client_key": key}).get("Item")
    except Exception:
        return 0, 0  # อ่านตัวนับไม่ได้ ไม่ให้ระบบล็อกอินพัง
    if not item:
        return 0, 0
    fails, first = int(item.get("fails", 0)), int(item.get("first", 0))
    if int(time.time()) - first >= LOCK_SECONDS:
        return 0, 0
    return fails, first


def record_fail(key, fails, first):
    now = int(time.time())
    fails, first = fails + 1, (first if fails else now)
    try:
        login_table.put_item(Item={"client_key": key, "fails": fails, "first": first,
                                    "expires": first + LOCK_SECONDS})  # expires ใช้กับ TTL ให้ DynamoDB ลบเอง
    except Exception:
        pass
    return fails, first


def clear_fails(key):
    try:
        login_table.delete_item(Key={"client_key": key})
    except Exception:
        pass


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
            "size_sqm": float(size) if size is not None else (DEFAULT_SIZE if status == "owner" else None),
            "status": status,
        })
    for fl in floors.values():
        fl["rooms"].sort(key=lambda x: x["room_id"])
    return [floors[k] for k in sorted(floors)]


def totals(floors):
    t = {k: sum(f[k] for f in floors) for k in ("rentable", "vacant", "occupied", "unknown")}
    t["income"] = sum(r["price"] for f in floors for r in f["rooms"]
                      if r["status"] == "occupied" and r["price"])
    return t


def size_groups(floors):
    """รวมห้องตามขนาด: {ขนาด: {"all": [...], "vacant": [...]}} เฉพาะห้องเช่าที่มีขนาด"""
    groups = {}
    for fl in floors:
        for r in fl["rooms"]:
            if r["status"] == "owner" or r["size_sqm"] is None:
                continue
            g = groups.setdefault(r["size_sqm"], {"all": [], "vacant": []})
            g["all"].append(r)
            if r["status"] == "vacant":
                g["vacant"].append(r)
    return dict(sorted(groups.items()))


def price_range(rooms):
    prices = sorted({r["price"] for r in rooms if r["price"] is not None})
    if not prices:
        return "-"
    if len(prices) == 1:
        return f"{prices[0]:,} บาท/เดือน"
    return f"{prices[0]:,} – {prices[-1]:,} บาท/เดือน"


# ---------- html ----------
FONT = ("<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">")


def page(body):
    return ("<!doctype html><html lang=\"th\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>Room Dashboard · ห้องว่าง</title>" + FONT +
            "<style>" + STYLE + "</style></head><body>" + body + "</body></html>")


def nav(admin, active="home"):
    tabs = [("/", "ภาพรวม", "home", ""), ("/?tab=vacant", "ห้องว่าง", "vacant", ""),
            ("/?tab=plan", "แปลนห้อง", "plan", "")]
    if admin:
        tabs += [("/?report=1", "รายงานสรุป", "report", " adm"),
                 ("/?tab=manage", "จัดการสถานะ", "manage", " adm")]
    links = "".join(
        f"<a class=\"{'on' if active == key else ''}{cls}\" href=\"{href}\">{label}</a>"
        for href, label, key, cls in tabs)
    if admin:
        btn = ("<form method=\"post\"><input type=\"hidden\" name=\"action\" value=\"logout\">"
               "<button class=\"nb\">ออกจากระบบ</button></form>")
    else:
        btn = "<a class=\"nb\" href=\"/?login=1\">เข้าสู่ระบบผู้ดูแล</a>"
    return ("<div class=\"noprint\"><div class=\"nav\"><div class=\"ni\"><span class=\"logo\">● Room Dashboard</span>"
            + btn + "</div></div><div class=\"tabs\"><div class=\"ti\">" + links + "</div></div></div>")


def tile(r, admin):
    rid = escape(r["room_id"])
    short = rid[1:] if rid[:1] == "P" else rid
    flex = r["size_sqm"] or DEFAULT_SIZE
    if admin:
        cls = r["status"]
    else:
        cls = "vacant" if r["status"] == "vacant" else "gy"
    ph = "<small class=\"ph\">&nbsp;</small>"
    lines = f"<b>{short}</b>"
    size_line = f"<small class=\"sz\">{r['size_sqm']:g}</small>" if r["size_sqm"] is not None else ph
    if r["status"] == "owner" and admin:
        lines += size_line + "<small class=\"ow\">เจ้าของ</small>"
    else:
        price_line = f"<small>{r['price']:,}</small>" if r["price"] is not None else ph
        lines += size_line + price_line
    return f"<div class=\"rm {cls}\" style=\"flex:{flex:g}\">{lines}</div>"


def map_card(floors, admin):
    t = totals(floors)
    stats = ""
    if admin:
        stats = ("<div class=\"stats\">"
                 f"<div><small>ห้องเช่า</small><b>{t['rentable']}</b></div>"
                 f"<div><small>มีผู้เช่า</small><b class=\"r\">{t['occupied']}</b></div>"
                 f"<div><small>ห้องว่าง</small><b class=\"gg\">{t['vacant']}</b></div>"
                 f"<div><small>ยังไม่ระบุ</small><b class=\"m\">{t['unknown']}</b></div></div>")
    rows = "".join(
        f"<div class=\"fl\"><div class=\"fn\">ชั้น {fl['floor']}</div><div class=\"rooms\">"
        + "".join(tile(r, admin) for r in fl["rooms"]) + "</div></div>"
        for fl in reversed(floors))
    if admin:
        legend = ("<div class=\"lg\"><span><i style=\"background:#2f9e5e\"></i>ว่าง</span>"
                  "<span><i style=\"background:#d4483b\"></i>มีผู้เช่า</span>"
                  "<span><i style=\"border:1.5px dashed #9aa5b8\"></i>ยังไม่ระบุ</span>"
                  "<span><i style=\"background:#9aa5b8\"></i>ห้องเจ้าของ</span></div>")
    else:
        legend = ("<div class=\"lg\"><span><i style=\"background:#2f9e5e\"></i>ว่าง</span>"
                  "<span><i style=\"background:#dfe4ee\"></i>ไม่ว่าง</span></div>")
    return ("<div class=\"card mapc\"><h3>ผังห้อง (กว้างตามขนาดห้อง)</h3>"
            "<div class=\"sub\">เลขห้อง · ขนาด (ตร.ม.) · ราคา (บาท/เดือน)</div>"
            + stats + rows + legend + "</div>")


def vacancy_card(floors):
    t = totals(floors)
    out = ("<div class=\"card\"><h3>ห้องว่างตอนนี้</h3><div class=\"sub\">เลือกขนาดที่ต้องการ</div>"
           f"<div class=\"bigv\">{t['vacant']}<span> ห้อง</span></div>")
    for size, g in size_groups(floors).items():
        out += ("<div class=\"g\">"
                f"<div class=\"gs\">ห้อง {size:g} ตร.ม.</div>"
                f"<div class=\"gn\">{len(g['vacant'])}<span> ห้องว่าง</span></div>"
                f"<div class=\"gp\">{price_range(g['all'])}</div></div>")
    return out + "</div>"


def donut_card(floors):
    t = totals(floors)
    rentable, occupied, vacant = t["rentable"], t["occupied"], t["vacant"]
    if rentable > 0 and t["unknown"] == 0:
        pct = occupied / rentable * 100
        a = pct * 3.6
        b = a + vacant / rentable * 360
        ring = (f"background:conic-gradient(#d4483b 0 {a:.1f}deg,#2f9e5e {a:.1f}deg {b:.1f}deg,"
                f"#e3e8f1 {b:.1f}deg 360deg)")
        big = f"<b>{pct:.1f}%</b>"
        sub = f"{occupied} จาก {rentable} ห้อง"
    else:
        ring = "background:#e3e8f1"
        big = "<b class=\"w2\">รอข้อมูล</b>"
        sub = "ระบุสถานะยังไม่ครบ"
    return ("<div class=\"card dn\"><h3>อัตราการเข้าพัก</h3><span class=\"badge\">เห็นเฉพาะผู้ดูแล</span>"
            f"<div class=\"ring\" style=\"{ring}\"><div>{big}<small>{sub}</small></div></div>"
            "<div class=\"gp\">มีผู้เช่า ÷ ห้องเช่าทั้งหมด</div>"
            "<div class=\"g\" style=\"width:100%;text-align:left\"><div class=\"gs\">รายได้ค่าเช่า (ประมาณการ)</div>"
            f"<div class=\"gn\" style=\"color:#1e3a8a;font-size:26px\">฿{t['income']:,}"
            "<span> /เดือน</span></div></div></div>")


def vacant_list(floors, admin):
    out = "<div class=\"vg\">"
    for fl in floors:
        vacants = [r for r in fl["rooms"] if r["status"] == "vacant"]
        count = (f"ว่าง {len(vacants)} จาก {fl['rentable']} ห้อง" if admin
                 else f"ว่าง {len(vacants)} ห้อง")
        out += "<div>" + f"<div class=\"fh\"><b>ชั้น {fl['floor']}</b><span>{count}</span></div>"
        if vacants:
            items = ""
            for r in vacants:
                size = f"{r['size_sqm']:g} ตร.ม." if r["size_sqm"] is not None else "-"
                price = f"{r['price']:,} บาท" if r["price"] is not None else "-"
                items += (f"<div class=\"it\"><b>{escape(r['room_id'])}</b>"
                          f"<span>{size}</span><em>{price}</em></div>")
            out += f"<div class=\"its\">{items}</div>"
        elif admin and fl["unknown"]:
            out += f"<div class=\"none\">ยังไม่ระบุสถานะ {fl['unknown']} ห้อง</div>"
        else:
            out += "<div class=\"none\">ไม่มีห้องว่าง</div>"
        out += "</div>"
    return out + "</div>"


def plan_svg(size):
    w, h = PLAN_DIMS.get(size) or (round(math.sqrt(size / 2), 1), 0)
    if not h:
        h = round(size / w, 1)
    s = 34
    pw, ph = w * s, h * s
    bw, bh = 1.6 * s, 2.0 * s
    vw, vh = pw + 24, ph + 30
    return (f"<svg viewBox=\"0 0 {vw:g} {vh:g}\" width=\"{vw * 2:.0f}\" height=\"{vh * 2:.0f}\">"
            "<g transform=\"translate(12,10)\">"
            f"<rect width=\"{pw:g}\" height=\"{ph:g}\" fill=\"#fff\" stroke=\"#1e3a8a\" stroke-width=\"3\"/>"
            f"<rect width=\"{bw:g}\" height=\"{bh:g}\" fill=\"#dbe4ff\" stroke=\"#1e3a8a\" stroke-width=\"1.5\"/>"
            f"<text x=\"{bw / 2:g}\" y=\"{bh / 2 + 4:g}\" font-size=\"10\" text-anchor=\"middle\" fill=\"#1e3a8a\">น้ำ</text>"
            f"<rect x=\"{pw * 0.25:g}\" y=\"{ph - 3:g}\" width=\"{pw * 0.5:g}\" height=\"6\" fill=\"#3b82f6\"/>"
            f"<text x=\"{pw / 2:g}\" y=\"{ph - 10:g}\" font-size=\"9\" text-anchor=\"middle\" fill=\"#1e3a8a\">หน้าต่าง/ระเบียง</text>"
            f"<rect x=\"{pw - 3:g}\" y=\"{bh + 6:g}\" width=\"6\" height=\"{s * 0.9:g}\" fill=\"#f59e0b\"/>"
            f"<text x=\"{pw - 10:g}\" y=\"{bh + s * 0.45 + 8:g}\" font-size=\"9\" text-anchor=\"end\" fill=\"#92400e\">ประตู</text>"
            f"<text x=\"{pw / 2:g}\" y=\"{ph / 2 - 2:g}\" font-size=\"12\" font-weight=\"700\" text-anchor=\"middle\" fill=\"#0f172a\">{size:g} ตร.ม.</text>"
            f"<text x=\"{pw / 2:g}\" y=\"{ph / 2 + 13:g}\" font-size=\"9\" text-anchor=\"middle\" fill=\"#5d6b8a\">{w:g} × {h:g} ม. (โดยประมาณ)</text>"
            "</g></svg>")


def plan_cards(floors):
    out = ""
    for size, g in size_groups(floors).items():
        w, h = PLAN_DIMS.get(size) or (round(math.sqrt(size / 2), 1), 0)
        if not h:
            h = round(size / w, 1)
        out += (f"<div class=\"card pc\"><h3>ห้อง {size:g} ตร.ม.</h3>"
                f"<div class=\"sub\">ประมาณ {w:g} × {h:g} ม. · {price_range(g['all'])}</div>"
                + plan_svg(size) + "</div>")
    return out + "<div class=\"note\" style=\"grid-column:1/-1\">* แปลนเป็นภาพจำลอง ไม่ใช่แบบจริงของอาคาร</div>"


def admin_row(r):
    rid = escape(r["room_id"])

    def opt(val, label):
        chk = " checked" if r["status"] == val else ""
        return (f"<label class=\"rb\"><input type=\"radio\" name=\"s_{rid}\" value=\"{val}\"{chk}>"
                f"<span>{label}</span></label>")

    return (f"<div class=\"ar\" data-orig=\"{r['status']}\">"
            f"<span class=\"rid\">{rid}</span>"
            f"<span class=\"bd {r['status']}\">{STATUS_TH[r['status']]}</span>"
            f"<span class=\"bt\">{opt('vacant', 'ว่าง')}{opt('occupied', 'มีผู้เช่า')}</span>"
            "</div>")


MANAGE_JS = """<script>
(function(){
  var f=document.getElementById('mf'); if(!f) return;
  var cnt=document.getElementById('cnt'), sv=document.getElementById('sv');
  function upd(){
    var n=0;
    f.querySelectorAll('.ar').forEach(function(row){
      var c=row.querySelector('input:checked');
      var ch=!!c && c.value!==row.getAttribute('data-orig');
      row.classList.toggle('chg',ch); if(ch) n++;
    });
    cnt.textContent = n ? 'เปลี่ยนแปลง '+n+' ห้อง (ยังไม่บันทึก)' : 'ยังไม่มีการเปลี่ยนแปลง';
    sv.disabled = n===0;
  }
  f.addEventListener('change',upd);
  f.addEventListener('reset',function(){setTimeout(upd,0)});
  upd();
})();
</script>"""


def manage_card(floors, saved=None):
    banner = ""
    if saved is not None:
        banner = (f"<div class=\"ok\">บันทึกแล้ว {saved} ห้อง</div>" if saved
                  else "<div class=\"ok\">ไม่มีรายการที่เปลี่ยน</div>")
    out = ("<div class=\"card\"><h3>จัดการสถานะห้อง (ผู้ดูแล)</h3>"
           "<div class=\"sub\">เลือก \"ว่าง\" หรือ \"มีผู้เช่า\" ของแต่ละห้อง แล้วกด \"บันทึกการเปลี่ยนแปลง\" "
           "(ยังไม่บันทึกจนกว่าจะกดบันทึก กด \"ยกเลิก\" เพื่อคืนค่าเดิม)</div>" + banner +
           "<form method=\"post\" id=\"mf\"><input type=\"hidden\" name=\"action\" value=\"save\">")
    for fl in floors:
        out += f"<div class=\"fh\"><b>ชั้น {fl['floor']}</b><span>{fl['rentable']} ห้องเช่า</span></div><div class=\"mg\">"
        out += "".join(admin_row(r) for r in fl["rooms"] if r["status"] != "owner")
        out += "</div>"
    out += ("<div class=\"sbar\"><span id=\"cnt\">ยังไม่มีการเปลี่ยนแปลง</span>"
            "<span class=\"sbtn\"><button type=\"reset\" class=\"cx\">ยกเลิก</button>"
            "<button type=\"submit\" id=\"sv\" class=\"sv\">บันทึกการเปลี่ยนแปลง</button></span></div>"
            "</form></div>" + MANAGE_JS)
    return out


def occ_text(rentable, occupied, unknown):
    if rentable and unknown == 0:
        return f"{occupied / rentable * 100:.1f}%"
    return "รอข้อมูล"



# ---------- รายงานย้อนหลังจาก S3 (ไฟล์ที่ Lambda save-monthly-report บันทึกไว้) ----------
def _n(v, d=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return d


def report_history():
    """รายชื่อเดือนที่มีรายงานใน S3 ถ้าไม่ได้ตั้ง REPORT_BUCKET หรืออ่านไม่ได้ จะไม่กระทบหน้ารายงานปัจจุบัน"""
    if not REPORT_BUCKET:
        return {"on": False, "ok": True, "months": []}
    try:
        s3 = boto3.client("s3")
        months, kwargs = [], {"Bucket": REPORT_BUCKET, "Prefix": REPORT_PREFIX}
        while True:
            r = s3.list_objects_v2(**kwargs)
            for o in r.get("Contents", []):
                name = o["Key"][len(REPORT_PREFIX):]
                if name.endswith(".json") and MONTH_RE.fullmatch(name[:-5]):
                    months.append(name[:-5])
            if not r.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = r["NextContinuationToken"]
        return {"on": True, "ok": True, "months": sorted(set(months))}
    except Exception:
        return {"on": True, "ok": False, "months": []}


def load_saved(month):
    """อ่านรายงานเดือนที่เลือก (ตรวจรูปแบบ YYYY-MM เท่านั้น จึงเปิดได้เฉพาะไฟล์ในโฟลเดอร์รายงาน)"""
    if not REPORT_BUCKET or not MONTH_RE.fullmatch(month or ""):
        return None
    try:
        obj = boto3.client("s3").get_object(Bucket=REPORT_BUCKET, Key=f"{REPORT_PREFIX}{month}.json")
        rep = json.loads(obj["Body"].read().decode("utf-8"))
        if isinstance(rep.get("totals"), dict) and isinstance(rep.get("floors"), list):
            return rep
    except Exception:
        pass
    return None


def month_label(key):
    return f"{THAI_MONTH_SHORT[int(key[5:7]) - 1]} {key[:4]}"


def history_side(hist, cur):
    live = "hl on" if cur is None else "hl"
    out = ["<aside class=\"card hs noprint\"><h3>รายงานย้อนหลัง*</h3>",
           f"<a class=\"{live}\" href=\"/?report=1\">รายงานปัจจุบัน</a>"]
    if not hist["ok"]:
        out.append("<div class=\"hn\">โหลดรายงานย้อนหลังไม่ได้ชั่วคราว</div>")
    elif not hist["months"]:
        out.append("<div class=\"hn\">ยังไม่มีรายงานที่บันทึกไว้</div>")
    else:
        years = {}
        for k in hist["months"]:
            years.setdefault(k[:4], []).append(k)
        for y in sorted(years, reverse=True):
            op = " open" if cur and cur[:4] == y else ""
            links = "".join(
                f"<a class=\"{'on' if k == cur else ''}\" href=\"/?report=1&amp;month={k}\">{month_label(k)}</a>"
                for k in sorted(years[y]))
            out.append(f"<details{op}><summary>{y} <small>({len(years[y])} เดือน)</small></summary>{links}</details>")
    out.append("<div class=\"hf\"><span>*</span><span>บันทึกอัตโนมัติทุกวันที่ <span style=\"white-space:nowrap\">28 เวลา 15.00 น.</span></span></div></aside>")
    return "".join(out)


def report_wrap(card, hist, cur):
    if not hist or not hist["on"]:
        return "<div class=\"w w1\">" + card + "</div>"
    return "<div class=\"w rw\"><div class=\"rmain\">" + card + "</div>" + history_side(hist, cur) + "</div>"


def render_saved(rep, month, hist):
    y, m = int(month[:4]), int(month[5:7])
    t = rep["totals"]
    rentable, vacant, occupied, unknown = (_n(t.get(k)) for k in ("rentable", "vacant", "occupied", "unknown"))
    income = _n(t.get("income"))
    gen = str(rep.get("generated_at", ""))
    stamp = escape(f"{gen[8:10]}/{gen[5:7]}/{gen[0:4]} {gen[11:16]}" if len(gen) >= 16 else gen)

    def pct(n):
        return f"{n / rentable * 100:.1f}" if rentable else "0"

    big = occ_text(rentable, occupied, unknown)
    wait = "<small>ระบุสถานะยังไม่ครบ</small>" if big == "รอข้อมูล" else ""
    hero = ("<div class=\"rh\"><div class=\"bg\"><small>Occupancy</small>" + big + wait + "</div>"
            "<div class=\"sb\"><div class=\"stack\">"
            f"<i style=\"width:{pct(occupied)}%;background:#d4483b\"></i>"
            f"<i style=\"width:{pct(vacant)}%;background:#2f9e5e\"></i>"
            f"<i style=\"width:{pct(unknown)}%;background:#9aa5b8\"></i></div>"
            "<div class=\"leg\">"
            f"<span><i style=\"background:#d4483b\"></i>มีผู้เช่า <b>{occupied}</b></span>"
            f"<span><i style=\"background:#2f9e5e\"></i>ว่าง <b>{vacant}</b></span>"
            f"<span><i style=\"background:#9aa5b8\"></i>ยังไม่ระบุ <b>{unknown}</b></span></div>"
            f"<div class=\"money\">รายได้ค่าเช่า <b>{income:,} บาท/เดือน</b></div>"
            "</div></div>")

    rows, vrows = "", ""
    for fl in rep["floors"]:
        if not isinstance(fl, dict):
            continue
        fr, fo, fv, fu = (_n(fl.get(k)) for k in ("rentable", "occupied", "vacant", "unknown"))
        rows += (f"<tr><td>{_n(fl.get('floor'))}</td><td class=\"n\">{fr}</td><td class=\"n\">{fo}</td>"
                 f"<td class=\"n\">{fv}</td><td class=\"n\">{occ_text(fr, fo, fu)}</td>"
                 f"<td class=\"n\">{_n(fl.get('income')):,}</td></tr>")
        vac = [v for v in fl.get("vacant_rooms", []) if isinstance(v, dict)]
        for i, v in enumerate(vac):
            try:
                size = f"{float(v['size_sqm']):g}"
            except (KeyError, TypeError, ValueError):
                size = "-"
            first = f"<td class=\"fl2\" rowspan=\"{len(vac)}\">{_n(fl.get('floor'))}</td>" if i == 0 else ""
            vrows += (f"<tr>{first}<td><b>{escape(str(v.get('room_id', '')))}</b></td>"
                      f"<td class=\"n\">{_n(v.get('price')):,}</td><td class=\"n\">{size}</td></tr>")
    rows += (f"<tr class=\"tot\"><td>รวม</td><td class=\"n\">{rentable}</td><td class=\"n\">{occupied}</td>"
             f"<td class=\"n\">{vacant}</td><td class=\"n\">{big}</td><td class=\"n\">{income:,}</td></tr>")
    summary = ("<div class=\"tw\"><table class=\"rp\"><tr><th>ชั้น</th><th class=\"n\">ห้องเช่า</th>"
               "<th class=\"n\">มีผู้เช่า</th><th class=\"n\">ว่าง</th><th class=\"n\">Occupancy</th>"
               "<th class=\"n\">รายได้ (บาท)</th></tr>" + rows + "</table></div>")
    vtable = ("<div class=\"tw\"><table class=\"rp\"><tr><th>ชั้น</th><th>ห้อง</th><th class=\"n\">ราคา (บาท)</th>"
              "<th class=\"n\">ขนาด (ตร.ม.)</th></tr>" + vrows + "</table></div>") if vrows else "<div class=\"none\">ไม่มีห้องว่าง</div>"
    note = ("รายงานนี้บันทึกไว้โดยอัตโนมัติ ณ เวลาที่ระบุ ไม่เปลี่ยนตามสถานะห้องที่แก้ไขภายหลัง · "
            "รายได้ค่าเช่า = ผลรวมราคาของห้องที่มีผู้เช่า (ประมาณการ ไม่ใช่เงินที่รับจริง) · ไม่นับห้องเจ้าของ")
    buttons = ("<div class=\"pb noprint\"><a href=\"/?report=1\">ดูรายงานปัจจุบัน</a>"
               "<button class=\"lo\" onclick=\"window.print()\">พิมพ์ / บันทึกเป็น PDF</button></div>")
    card = ("<div class=\"card\"><div class=\"rtop\"><div><h1>รายงานสรุปห้องพัก</h1>"
            f"<small>ประจำเดือน {THAI_MONTHS[m - 1]} {y + 543} ({y})<span class=\"stag\">รายงานที่บันทึกไว้</span></small></div>"
            f"<span>บันทึกเมื่อ {stamp}<br>ห้องเช่า {rentable} ห้อง</span></div>"
            "<div class=\"sec\" style=\"margin-top:16px\">1. ภาพรวม</div>" + hero +
            "<div class=\"sec\">2. สรุปรายชั้น</div>" + summary +
            f"<div class=\"sec\">3. ห้องว่าง ({vacant} ห้อง)</div>" + vtable +
            f"<div class=\"note\">{note}</div>" + buttons + "</div>")
    return page(nav(True, "report") + report_wrap(card, hist, month))


def render_saved_missing(hist):
    card = ("<div class=\"card\"><h1 style=\"margin:0 0 8px;font-size:22px\">ไม่พบรายงานของเดือนที่เลือก</h1>"
            "<p class=\"sub\">ไฟล์รายงานเดือนนี้ยังไม่ถูกบันทึก หรือเปิดอ่านไม่ได้ในขณะนี้</p>"
            "<div class=\"pb noprint\"><a href=\"/?report=1\">ดูรายงานปัจจุบัน</a></div></div>")
    return page(nav(True, "report") + report_wrap(card, hist, "none"))


# ---------- pages ----------
def render_home(floors, admin):
    left = (donut_card(floors) if admin else "") + vacancy_card(floors)
    body = f"<div class=\"w\"><div class=\"rcol\">{left}</div>{map_card(floors, admin)}</div>"
    return page(nav(admin, "home") + body)


def render_vacant(floors, admin):
    body = ("<div class=\"w w1\"><div class=\"card vcard\"><h3>ห้องว่างแต่ละชั้น</h3>"
            + vacant_list(floors, admin) + "</div></div>")
    return page(nav(admin, "vacant") + body)


def render_plan(floors, admin):
    return page(nav(admin, "plan") + "<div class=\"w pw\">" + plan_cards(floors) + "</div>")


def render_manage(floors, saved=None):
    return page(nav(True, "manage") + "<div class=\"w w1\">" + manage_card(floors, saved) + "</div>")


def render_login(error=""):
    msg = f"<div class=\"err\">{escape(error)}</div>" if error else ""
    return page(nav(False, "") + "<div class=\"w w1\"><div class=\"card login\"><h3>เข้าสู่ระบบผู้ดูแล</h3>"
                "<form method=\"post\">"
                "<input type=\"hidden\" name=\"action\" value=\"login\">"
                "<label>รหัสผู้ดูแล</label>"
                "<input type=\"password\" name=\"key\" autocomplete=\"current-password\" autofocus>"
                + msg + "<button>เข้าสู่ระบบ</button></form>"
                "<div class=\"foot\" style=\"margin-top:12px\"><a href=\"/\">กลับหน้าหลัก</a></div></div></div>")


def render_report(floors, hist=None):
    t = time.gmtime(time.time() + 7 * 3600)  # เวลาไทย (UTC+7)
    month = f"{THAI_MONTHS[t.tm_mon - 1]} {t.tm_year + 543}"
    stamp = time.strftime("%d/%m/%Y %H:%M", t)

    tt = totals(floors)
    rentable, vacant, occupied, unknown = tt["rentable"], tt["vacant"], tt["occupied"], tt["unknown"]
    total_income = tt["income"]

    def income(fl):
        return sum(r["price"] for r in fl["rooms"]
                   if r["status"] == "occupied" and r["price"])

    def pct(n):
        return f"{n / rentable * 100:.1f}" if rentable else "0"

    big = occ_text(rentable, occupied, unknown)
    wait = "<small>ระบุสถานะยังไม่ครบ</small>" if big == "รอข้อมูล" else ""
    hero = ("<div class=\"rh\"><div class=\"bg\"><small>Occupancy</small>" + big + wait + "</div>"
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
    summary = ("<div class=\"tw\"><table class=\"rp\"><tr><th>ชั้น</th><th class=\"n\">ห้องเช่า</th>"
               "<th class=\"n\">มีผู้เช่า</th><th class=\"n\">ว่าง</th>"
               "<th class=\"n\">Occupancy</th><th class=\"n\">รายได้ (บาท)</th></tr>"
               + rows + "</table></div>")

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
        vtable = ("<div class=\"tw\"><table class=\"rp\"><tr><th>ชั้น</th><th>ห้อง</th>"
                  "<th class=\"n\">ราคา (บาท)</th><th class=\"n\">ขนาด (ตร.ม.)</th></tr>"
                  + vrows + "</table></div>")
    else:
        vtable = "<div class=\"none\">ไม่มีห้องว่าง</div>"

    note = ("Occupancy = ห้องมีผู้เช่า ÷ ห้องเช่าทั้งหมด (ไม่นับห้องเจ้าของ P211) "
            "และจะแสดงเป็นตัวเลขเมื่อระบุสถานะครบทุกห้อง · "
            "รายได้ค่าเช่า = ผลรวมราคาของห้องที่มีผู้เช่า (ประมาณการตามสถานะห้อง ไม่ใช่เงินที่รับจริง)")
    buttons = ("<div class=\"pb noprint\"><a href=\"/\">กลับหน้าหลัก</a>"
               "<button class=\"lo\" onclick=\"window.print()\">พิมพ์ / บันทึกเป็น PDF</button></div>")

    card = ("<div class=\"card\">"
                "<div class=\"rtop\"><div><h1>รายงานสรุปห้องพัก</h1>"
                f"<small>ประจำเดือน {month}</small></div>"
                f"<span>ข้อมูล ณ {stamp}<br>ห้องเช่า {rentable} ห้อง</span></div>"
                "<div class=\"sec\" style=\"margin-top:16px\">1. ภาพรวม</div>" + hero +
                "<div class=\"sec\">2. สรุปรายชั้น</div>" + summary +
                f"<div class=\"sec\">3. ห้องว่าง ({vacant} ห้อง)</div>" + vtable +
                f"<div class=\"note\">{note}</div>" + buttons + "</div>")
    return page(nav(True, "report") + report_wrap(card, hist, None))


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


def public_json(floors):
    """JSON สำหรับคนทั่วไป: เฉพาะห้องว่าง ไม่เปิดเผยสถานะห้องอื่น"""
    return [{"room_id": r["room_id"], "floor": fl["floor"],
             "price": r["price"], "size_sqm": r["size_sqm"]}
            for fl in floors for r in fl["rooms"] if r["status"] == "vacant"]


# ---------- handler ----------
def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    qs = event.get("queryStringParameters") or {}

    if method == "POST":
        form = read_form(event)
        action = form.get("action")

        if action == "login":
            ck = client_key(event)
            fails, first = login_state(ck)
            if fails >= MAX_FAILS:  # ถูกล็อกอยู่ แม้กรอกรหัสถูกก็ไม่รับ
                mins = max(1, -(-(first + LOCK_SECONDS - int(time.time())) // 60))
                log_event("login_blocked", ck, fails)
                return reply(429, render_login(f"ลองรหัสผิดหลายครั้ง กรุณารออีกประมาณ {mins} นาที"))
            key = form.get("key", "")
            if ADMIN_KEY and hmac.compare_digest(key.encode(), ADMIN_KEY.encode()):
                log_event("login_ok", ck, fails)  # บันทึกการล็อกอินสำเร็จ (ใช้ตั้ง alarm แจ้งเตือน)
                clear_fails(ck)  # ล้างตัวนับของ IP นี้ (รวมรายการที่หมดเวลาแล้ว)
                return redirect("/", [make_cookie()])
            fails, first = record_fail(ck, fails, first)
            log_event("login_fail", ck, fails)
            left = MAX_FAILS - fails
            msg = ("รหัสไม่ถูกต้อง (เหลืออีก %d ครั้ง)" % left if left > 0
                   else "รหัสไม่ถูกต้อง ลองครบ %d ครั้งแล้ว ถูกล็อก %d นาที" % (MAX_FAILS, LOCK_SECONDS // 60))
            return reply(401, render_login(msg))

        if action == "logout":
            return redirect("/", [clear_cookie()])

        if action == "save":
            if not is_admin(event):
                return reply(401, render_login("กรุณาเข้าสู่ระบบอีกครั้ง"))
            current = {r["room_id"]: r for r in scan_all()}
            changed = 0
            for key, status in form.items():
                if not key.startswith("s_"):
                    continue
                room_id = key[2:]
                item = current.get(room_id)
                if status not in ("vacant", "occupied") or not item or not item.get("is_rentable"):
                    continue
                if str(item.get("status", "")).lower() == status:
                    continue
                table.update_item(
                    Key={"room_id": room_id},
                    UpdateExpression="SET #s = :s",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":s": status})
                changed += 1
            return redirect(f"/?tab=manage&saved={changed}")

        return reply(400, "bad request", "text/plain; charset=utf-8")

    if qs.get("login") == "1":
        return reply(200, render_login())

    admin = is_admin(event)
    floors = build_floors()

    if qs.get("format") == "json":
        data = floors if admin else public_json(floors)
        return reply(200, json.dumps(data, ensure_ascii=False),
                     "application/json; charset=utf-8")
    if qs.get("report") == "1":
        if not admin:
            return reply(401, render_login("กรุณาเข้าสู่ระบบผู้ดูแลเพื่อดูรายงาน"))
        hist = report_history()
        month = qs.get("month")
        if month:
            saved = load_saved(month)
            if saved is None:
                return reply(404, render_saved_missing(hist))
            return reply(200, render_saved(saved, month, hist))
        return reply(200, render_report(floors, hist))

    tab = qs.get("tab", "")
    if tab == "manage":
        if not admin:
            return reply(401, render_login("กรุณาเข้าสู่ระบบผู้ดูแลเพื่อจัดการสถานะ"))
        saved = int(qs["saved"]) if str(qs.get("saved", "")).isdigit() else None
        return reply(200, render_manage(floors, saved))
    if tab == "vacant":
        return reply(200, render_vacant(floors, admin))
    if tab == "plan":
        return reply(200, render_plan(floors, admin))
    return reply(200, render_home(floors, admin))
