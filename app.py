import csv
import math
from pathlib import Path
from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.ensure_ascii = False

CSV_PATH = Path(__file__).parent / "data" / "aed.csv"


def load_aed_data():
    aed_list = []

    with CSV_PATH.open(
        mode="r",
        encoding="cp950",
        errors="replace",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for index, row in enumerate(reader, start=1):
            aed = {
                "id": index,
                "placeName": row["場所名稱"].strip(),
                "address": row["場所地址"].strip(),
                "districtCode": row["區域代碼"].strip(),
                "latitude": float(row["緯度"]),
                "longitude": float(row["經度"]),
                "placeCategory": row["場所分類"].strip(),
                "placeType": row["場所類型"].strip(),
                "aedLocation": row["AED放置地點"].strip(),
                "aedDescription": row["AED地點描述"].strip(),
            }

            aed_list.append(aed)

    return aed_list


AED_DATA = load_aed_data()

def calculate_distance(lat1, lng1, lat2, lng2):
    """
    使用Haversine公式計算兩個經緯度之間的距離。
    回傳單位：公里
    """

    earth_radius_km = 6371

    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    lat_difference = lat2_rad - lat1_rad
    lng_difference = lng2_rad - lng1_rad

    a = (
        math.sin(lat_difference / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(lng_difference / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius_km * c


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "recordCount": len(AED_DATA)
    })


@app.get("/api/aeds")
def search_aeds():
    keyword = request.args.get("keyword", "").strip().lower()
    district_code = request.args.get("districtCode", "").strip()
    category = request.args.get("category", "").strip()
    limit = request.args.get("limit", default=20, type=int)

    # 避免一次回傳太多資料
    limit = max(1, min(limit, 100))

    results = []

    for aed in AED_DATA:
        searchable_text = " ".join([
            aed["placeName"],
            aed["address"],
            aed["aedLocation"],
            aed["aedDescription"],
        ]).lower()

        if keyword and keyword not in searchable_text:
            continue

        if district_code and aed["districtCode"] != district_code:
            continue

        if category and aed["placeCategory"] != category:
            continue

        results.append(aed)

    return jsonify({
        "success": True,
        "count": len(results),
        "data": results[:limit]
    })

@app.get("/api/aeds/nearby")
def get_nearby_aeds():
    user_lat = request.args.get("lat", type=float)
    user_lng = request.args.get("lng", type=float)
    limit = request.args.get("limit", default=5, type=int)

    if user_lat is None or user_lng is None:
        return jsonify({
            "success": False,
            "message": "請提供lat與lng參數"
        }), 400

    if not (-90 <= user_lat <= 90):
        return jsonify({
            "success": False,
            "message": "lat必須介於-90到90之間"
        }), 400

    if not (-180 <= user_lng <= 180):
        return jsonify({
            "success": False,
            "message": "lng必須介於-180到180之間"
        }), 400

    limit = max(1, min(limit, 20))

    results = []

    for aed in AED_DATA:
        distance = calculate_distance(
            user_lat,
            user_lng,
            aed["latitude"],
            aed["longitude"]
        )

        # 複製AED資料，避免修改原始AED_DATA
        result = aed.copy()
        result["distanceKm"] = round(distance, 3)

        results.append(result)

    results.sort(key=lambda item: item["distanceKm"])

    nearest_results = results[:limit]

    return jsonify({
        "success": True,
        "userLocation": {
            "latitude": user_lat,
            "longitude": user_lng
        },
        "count": len(nearest_results),
        "data": nearest_results
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)