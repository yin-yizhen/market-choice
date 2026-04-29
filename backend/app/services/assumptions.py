from __future__ import annotations


def _ring(poi_rings: list[dict], radius: int) -> dict:
    return next((item for item in poi_rings if item.get("radius") == radius), poi_rings[0] if poi_rings else {})


def _category_total(ring: dict, *names: str) -> int:
    categories = ring.get("categories", {})
    return sum(int(categories.get(name, 0)) for name in names)


def infer_target_customer(poi_rings: list[dict], business_type: str) -> str:
    ring1000 = _ring(poi_rings, 1000)
    segments: list[str] = []
    if _category_total(ring1000, "office") >= 8:
        segments.append("办公白领")
    if _category_total(ring1000, "residential") >= 8:
        segments.append("周边社区居民")
    if _category_total(ring1000, "transport") >= 4:
        segments.append("通勤人群")
    if _category_total(ring1000, "retail", "leisure") >= 10:
        segments.append("购物休闲客群")
    if _category_total(ring1000, "education") >= 3:
        segments.append("学生和家长")
    if not segments:
        segments.append("周边自然客流")

    suffix = "，需结合线上评价和线下踩点复核"
    if any(word in business_type for word in ("咖啡", "茶", "餐", "饮", "食")):
        suffix = "，重点验证早晚高峰、午间和周末复购"
    return "、".join(segments) + suffix
