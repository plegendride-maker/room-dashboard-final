import json, boto3
from decimal import Decimal

table = boto3.resource("dynamodb").Table("ApartmentRooms")

# ข้อมูลห้อง 44 ห้อง (เนื้อหาเดียวกับ data/rooms.json)
ROOMS_JSON = r"""
[
{"room_id":"P101","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P102","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P103","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P104","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P105","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P106","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P107","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P108","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P109","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P110","floor":1,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P201","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P202","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P203","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P204","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P205","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P206","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P207","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P208","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P209","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P210","floor":2,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P211","floor":2,"is_rentable":false,"room_type":"owner"},
{"room_id":"P212","floor":2,"price":4500,"is_rentable":true,"room_type":"rental"},
{"room_id":"P301","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P302","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P303","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P304","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P305","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P306","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P307","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P308","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P309","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P310","floor":3,"price":4000,"is_rentable":true,"room_type":"rental"},
{"room_id":"P311","floor":3,"price":4500,"is_rentable":true,"room_type":"rental"},
{"room_id":"P312","floor":3,"price":4500,"is_rentable":true,"room_type":"rental"},
{"room_id":"P401","floor":4,"price":3800,"is_rentable":true,"room_type":"rental"},
{"room_id":"P402","floor":4,"price":3800,"is_rentable":true,"room_type":"rental"},
{"room_id":"P403","floor":4,"price":3800,"is_rentable":true,"room_type":"rental"},
{"room_id":"P404","floor":4,"price":3800,"is_rentable":true,"room_type":"rental"},
{"room_id":"P405","floor":4,"price":3800,"is_rentable":true,"room_type":"rental"},
{"room_id":"P406","floor":4,"price":3800,"is_rentable":true,"room_type":"rental"},
{"room_id":"P407","floor":4,"price":3800,"is_rentable":true,"room_type":"rental"},
{"room_id":"P408","floor":4,"price":3800,"is_rentable":true,"room_type":"rental"},
{"room_id":"P409","floor":4,"price":4500,"is_rentable":true,"room_type":"rental"},
{"room_id":"P410","floor":4,"price":4500,"is_rentable":true,"room_type":"rental"}
]
"""


def lambda_handler(event, context):
    rooms = json.loads(ROOMS_JSON, parse_float=Decimal)
    ids = [r["room_id"] for r in rooms]
    if len(rooms) != 44 or len(set(ids)) != 44:
        raise ValueError("Expected exactly 44 distinct rooms")

    existing = {i["room_id"] for i in table.scan(ProjectionExpression="room_id")["Items"]}
    new_rooms = [r for r in rooms if r["room_id"] not in existing]

    with table.batch_writer() as batch:
        for r in new_rooms:
            batch.put_item(Item=r)

    return {"imported": len(new_rooms),
            "skipped_existing": sorted(existing & set(ids))}
