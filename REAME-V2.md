# Room Availability & Occupancy Management Dashboard (CS615)

ระบบแสดงห้องว่างและอัตราการเข้าพักของหอพัก 4 ชั้น 44 ห้อง บน AWS Academy Learner Lab
ใช้ Amazon DynamoDB, AWS Lambda (Python) และ Lambda Function URL S3, EventBridge, CloudWatch และ SNS สำหรับรายงานย้อนหลังและการแจ้งเตือน

## ไฟล์ในโปรเจกต์

| ไฟล์ | หน้าที่ |
| --- | --- |
| `data/rooms.json` | ข้อมูลห้อง 44 ห้อง (หมายเลขห้อง ชั้น ราคา ประเภท) |
| `lambda/import_rooms.py` | Lambda `import-rooms` นำเข้าห้องลง DynamoDB (ข้ามห้องที่มีอยู่แล้ว) |
| `lambda/set_room_sizes.py` | Lambda เติมขนาดห้อง (`size_sqm`) จากราคาเช่า |
| `lambda/get_rooms.py` | Lambda `get-rooms` (เวอร์ชัน V2) หน้าเว็บ 3 แท็บ โหมดผู้ดูแล รายงานสรุป และแถบรายงานย้อนหลังจาก S3 (ถ้าตั้งค่า) |
| `lambda/save_monthly_report.py` | (Step 6) Lambda `save-monthly-report` บันทึกสรุปรายเดือนเป็นไฟล์ JSON/HTML ลง S3 ตั้งเวลาทุกวันที่ 28 เวลา 15.00 น. |
| `archive/get_rooms_v3.py` | เวอร์ชันก่อนหน้า (v3) เก็บไว้เป็นตัวสำรอง ไม่ใช้ในคู่มือ |

## การติดตั้งโดยย่อ

1. สร้างตาราง DynamoDB `ApartmentRooms` (partition key `room_id` ชนิด String, On-demand)
2. สร้าง Lambda `import-rooms` (Python 3.13, role `LabRole`, timeout 30 วินาที) แล้วรันนำเข้าห้อง
3. เปลี่ยนโค้ดเป็น `set_room_sizes.py` แล้วรันเติมขนาดห้อง
4. สร้าง Lambda `get-rooms` ด้วยโค้ด `get_rooms.py` และเปิด Function URL (Auth type NONE)
5. สร้างตาราง DynamoDB `LoginAttempts` (partition key `client_key` ชนิด String, On-demand) แล้วเปิด TTL ที่ attribute `expires`
6. ตั้ง environment variable `ADMIN_KEY` เป็นรหัสผู้ดูแลของคุณเอง
7. เติม `size_sqm` ของห้องเจ้าของ P211 (26.3) ด้วยมือใน DynamoDB ตามคู่มือ Step 2 (ถ้าไม่เติม โค้ดใช้ 26.3 เป็นค่าเริ่มต้น)

Step 6 รายงานรายเดือนบน S3:
1. สร้าง S3 bucket ส่วนตัว (เปิด Block all public access)
2. สร้าง Lambda `save-monthly-report` (role `LabRole`, timeout 30 วินาที) ด้วยโค้ด `save_monthly_report.py` ตั้ง environment variable `BUCKET` เป็นชื่อ bucket แล้ว Deploy และกด Test
3. ตั้งเวลาอัตโนมัติด้วย EventBridge ทุกวันที่ 28 เวลา 15.00 น. เวลาไทย: `cron(0 8 28 * ? *)` (08:00 UTC)
4. ให้ Lambda `get-rooms` แสดงแถบรายงานย้อนหลัง: ตั้ง environment variable `REPORT_BUCKET` เป็นชื่อ bucket เดียวกัน (ถ้าไม่ตั้ง แถบนี้จะไม่แสดงและหน้ารายงานทำงานเหมือนเดิม)

รายละเอียดทีละขั้นอยู่ในคู่มือประกอบโครงการ

## หน้าเว็บ

- **ทุกคน:** แท็บ ภาพรวม (ผังห้องกว้างตามขนาดห้อง) · ห้องว่าง (แยกรายชั้น) · แปลนห้อง เห็นห้องว่างเป็นสีเขียว ห้องอื่นเป็นสีเทา ไม่เห็นอัตราการเข้าพัก รายได้ หรือห้องเจ้าของ `?format=json` ให้เฉพาะห้องว่าง
- **ผู้ดูแล (ล็อกอินด้วย `ADMIN_KEY`):** เห็น Occupancy รายได้คาดการณ์ รายงานสรุป (พิมพ์เป็น PDF ได้) และแท็บจัดการสถานะแบบเลือกแล้วกดบันทึก (มีปุ่มยกเลิก) ถ้าตั้ง `REPORT_BUCKET` หน้ารายงานจะมีแถบด้านขวา "รายงานย้อนหลัง" แยกเป็นปี แล้วกดเข้าไปเลือกเดือน (เช่น 2026 → ก.พ. 2026) เปิดดูและพิมพ์รายงานที่บันทึกไว้ได้ (ผู้ดูแลเท่านั้น)

## ความปลอดภัย

- ไม่เก็บ `ADMIN_KEY` และลิงก์ Function URL จริงไว้ใน repository นี้
- ตั้งรหัสผู้ดูแลใน Environment variables ของ Lambda เท่านั้น
- จำกัดการลองรหัสผิด: ผิดครบ 5 ครั้งภายใน 15 นาที ล็อก IP นั้น 15 นาที (HTTP 429) ตัวนับเก็บในตาราง `LoginAttempts` แยกจากตารางห้อง (เก็บค่าแฮชของ IP ไม่เก็บ IP จริง) และใช้ TTL ลบรายการที่หมดอายุเอง ถ้าไม่มีตารางนี้ ล็อกอินยังใช้ได้แต่ไม่จำกัดจำนวนครั้ง
- บันทึกเหตุการณ์ล็อกอินสำเร็จ (`login_ok`), ล็อกอินผิด (`login_fail`) และล็อกอินขณะถูกล็อก (`login_blocked`) ลง CloudWatch Logs เป็น JSON (ไม่มีรหัสและไม่มี IP จริง) ใช้สร้าง metric filter และ alarm ได้

## ข้อจำกัด

- ล็อกอินผู้ดูแลใช้รหัสร่วมกัน (จำกัดการลองผิดแล้ว) กับ cookie ที่หมดอายุใน 1 ชั่วโมง (แผนต่อยอด: Amazon Cognito)
- รายงานหลักแสดงสถานะ ณ เวลาที่เปิดดู ส่วนรายงานย้อนหลังมาจากไฟล์ที่บันทึกอัตโนมัติทุกวันที่ 28 เวลา 15.00 น. จึงมีเฉพาะเดือนที่บันทึกแล้ว และไม่เปลี่ยนตามสถานะห้องที่แก้ภายหลัง
