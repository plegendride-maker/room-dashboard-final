import boto3
from decimal import Decimal

table = boto3.resource("dynamodb").Table("ApartmentRooms")

# ขนาดห้อง (ตร.ม.) ตามราคาเช่า (บาท/เดือน)
SIZE_BY_PRICE = {4500: Decimal("32"), 4000: Decimal("26.3"), 3800: Decimal("26.3")}


def lambda_handler(event, context):
    items, kwargs = [], {}
    while True:
        r = table.scan(**kwargs)
        items += r["Items"]
        if "LastEvaluatedKey" not in r:
            break
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]

    updated, skipped = 0, []
    for it in items:
        price = it.get("price")
        if not it.get("is_rentable") or price is None or int(price) not in SIZE_BY_PRICE:
            skipped.append(it["room_id"])
            continue
        table.update_item(
            Key={"room_id": it["room_id"]},
            UpdateExpression="SET size_sqm = :s",
            ExpressionAttributeValues={":s": SIZE_BY_PRICE[int(price)]})
        updated += 1
    return {"updated": updated, "skipped": sorted(skipped)}
