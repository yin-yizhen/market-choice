from __future__ import annotations

import json
from urllib import parse, request

from app.core.config import get_settings


AMAP_BASE = "https://restapi.amap.com/v3"
PAGE_SIZE = 25
MAX_PAGES = 20


def _get_json(path: str, params: dict) -> dict:
    settings = get_settings()
    if not settings.amap_web_service_key:
        raise RuntimeError("AMAP_WEB_SERVICE_KEY is not configured")
    query = parse.urlencode({**params, "key": settings.amap_web_service_key})
    url = f"{AMAP_BASE}/{path}?{query}"
    with request.urlopen(url, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    if data.get("status") != "1":
        info = data.get("info") or data.get("infocode") or "unknown error"
        raise RuntimeError(f"AMap API error: {info}")
    return data


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


def search_pois_around_detailed(latitude: float, longitude: float, radius: int) -> dict:
    pois: list[dict] = []
    declared_count = 0
    pages_fetched = 0
    for page in range(1, MAX_PAGES + 1):
        data = _get_json(
            "place/around",
            {
                "location": f"{longitude},{latitude}",
                "radius": radius,
                "offset": PAGE_SIZE,
                "page": page,
                "extensions": "base",
            },
        )
        declared_count = max(declared_count, int(data.get("count") or 0))
        page_pois = data.get("pois", [])
        pois.extend(page_pois)
        pages_fetched = page
        if len(page_pois) < PAGE_SIZE or len(pois) >= declared_count:
            break

    return {
        "pois": pois,
        "declared_count": declared_count,
        "pages_fetched": pages_fetched,
        "truncated": declared_count > len(pois),
    }


def search_pois_around(latitude: float, longitude: float, radius: int) -> list[dict]:
    return search_pois_around_detailed(latitude, longitude, radius)["pois"]
