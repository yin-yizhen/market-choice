from __future__ import annotations

import json
from urllib import parse, request

from app.core.config import get_settings


AMAP_BASE = "https://restapi.amap.com/v3"


def _get_json(path: str, params: dict) -> dict:
    settings = get_settings()
    if not settings.amap_web_service_key:
        raise RuntimeError("AMAP_WEB_SERVICE_KEY is not configured")
    query = parse.urlencode({**params, "key": settings.amap_web_service_key})
    url = f"{AMAP_BASE}/{path}?{query}"
    with request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def geocode(keyword: str, city: str = "") -> list[dict]:
    data = _get_json("geocode/geo", {"address": keyword, "city": city})
    candidates = []
    for item in data.get("geocodes", []):
        location = item.get("location", "")
        if "," not in location:
            continue
        longitude, latitude = [float(part) for part in location.split(",", 1)]
        candidates.append(
            {
                "name": item.get("formatted_address", keyword),
                "address": item.get("formatted_address", keyword),
                "city": item.get("city", city) if isinstance(item.get("city"), str) else city,
                "district": item.get("district", ""),
                "latitude": latitude,
                "longitude": longitude,
            }
        )
    return candidates


def search_pois_around(latitude: float, longitude: float, radius: int) -> list[dict]:
    data = _get_json(
        "place/around",
        {
            "location": f"{longitude},{latitude}",
            "radius": radius,
            "offset": 50,
            "page": 1,
            "extensions": "base",
        },
    )
    return data.get("pois", [])
