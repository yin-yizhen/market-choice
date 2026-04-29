from __future__ import annotations

from collections import Counter


CATEGORIES = {
    "food": ("餐饮", "咖啡", "快餐", "中餐", "西餐", "饮品", "甜品", "小吃"),
    "retail": ("购物", "商场", "超市", "便利店", "专卖", "零售"),
    "office": ("写字楼", "商务", "公司", "产业园", "办公"),
    "residential": ("住宅", "小区", "公寓", "宿舍"),
    "parking": ("停车", "停车场", "车库"),
    "transport": ("地铁", "公交", "交通", "火车", "客运"),
    "education": ("学校", "培训", "大学", "中学", "小学", "教育"),
    "leisure": ("景点", "公园", "影院", "健身", "娱乐", "文旅"),
}

COMPETITOR_KEYWORDS = {
    "咖啡": ("咖啡", "瑞幸", "星巴克", "manner", "库迪", "幸运咖"),
    "餐饮": ("餐饮", "饭店", "小吃", "快餐", "火锅", "烧烤", "面馆"),
    "奶茶": ("奶茶", "茶饮", "喜茶", "奈雪", "霸王茶姬", "蜜雪"),
    "便利店": ("便利店", "超市", "罗森", "全家", "711", "7-eleven"),
    "美容": ("美容", "美甲", "美睫", "皮肤管理"),
}


def _poi_text(poi: dict) -> str:
    return " ".join(str(poi.get(key, "")) for key in ("name", "type", "typecode")).lower()


def classify_poi(poi: dict, business_type: str) -> dict:
    text = _poi_text(poi)
    category = "other"
    for candidate, keywords in CATEGORIES.items():
        if any(keyword.lower() in text for keyword in keywords):
            category = candidate
            break

    business_key = business_type.lower()
    competitor_words = []
    for key, words in COMPETITOR_KEYWORDS.items():
        if key in business_key:
            competitor_words.extend(words)
    if not competitor_words and category == "food" and any(word in business_key for word in ("餐", "咖啡", "茶", "饮")):
        competitor_words.extend(COMPETITOR_KEYWORDS["餐饮"])

    is_competitor = any(word.lower() in text for word in competitor_words)
    is_complementary = category in {"office", "residential", "transport", "parking", "education", "leisure", "retail"}
    return {
        "category": category,
        "is_competitor": is_competitor,
        "is_complementary": is_complementary,
    }


def summarize_ring(radius: int, pois: list[dict], business_type: str) -> dict:
    categories: Counter[str] = Counter()
    competitor_count = 0
    complementary_count = 0
    samples: list[dict] = []

    for poi in pois:
        result = classify_poi(poi, business_type)
        categories[result["category"]] += 1
        competitor_count += int(result["is_competitor"])
        complementary_count += int(result["is_complementary"])
        if len(samples) < 8:
            samples.append(
                {
                    "name": poi.get("name", ""),
                    "type": poi.get("type", ""),
                    "category": result["category"],
                }
            )

    return {
        "radius": radius,
        "total": len(pois),
        "categories": dict(categories),
        "competitor_count": competitor_count,
        "complementary_count": complementary_count,
        "sample_pois": samples,
    }
