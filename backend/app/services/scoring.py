from __future__ import annotations

from math import ceil


SCORE_NAMES = [
    "位置曝光",
    "目标人流",
    "消费能力",
    "竞品压力",
    "互补业态",
    "交通便利",
    "停车条件",
    "未来规划",
    "租金合理性",
    "证照可行性",
    "铺位硬件",
    "线上热度",
    "夜间人气",
    "周末人气",
    "风险因素",
]


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, round(value)))


def _category_total(ring: dict, *names: str) -> int:
    categories = ring.get("categories", {})
    return sum(int(categories.get(name, 0)) for name in names)


def _business_metrics(financials: dict, business: dict) -> dict:
    average_ticket = max(float(business.get("average_ticket") or 0), 1)
    store_area = max(float(business.get("store_area") or 0), 1)
    employee_count = max(int(business.get("employee_count") or 0), 1)
    expected_revenue = float(financials.get("expected_monthly_revenue") or 0)
    break_even_revenue = float(financials.get("break_even_revenue") or 0)
    return {
        "break_even_daily_orders": ceil(break_even_revenue / average_ticket / 30),
        "monthly_revenue_per_sqm": round(expected_revenue / store_area, 2) if expected_revenue else None,
        "monthly_revenue_per_employee": round(expected_revenue / employee_count, 2) if expected_revenue else None,
    }


def _target_customer_bonus(target_customer: str, ring1000: dict) -> float:
    target = target_customer.lower()
    bonus = 0.0
    if any(word in target for word in ("白领", "办公", "写字楼", "office")):
        bonus += min(_category_total(ring1000, "office") * 0.8, 12)
    if any(word in target for word in ("社区", "居民", "家庭", "住宅")):
        bonus += min(_category_total(ring1000, "residential") * 0.5, 10)
    if any(word in target for word in ("学生", "学校", "教育")):
        bonus += min(_category_total(ring1000, "education") * 1.2, 8)
    return bonus


def _hours_bonus(opening_hours: str, ring1000: dict) -> float:
    hours = opening_hours.lower()
    food_leisure = _category_total(ring1000, "food", "leisure")
    if any(token in hours for token in ("22", "23", "24", "夜", "晚")):
        return min(food_leisure * 0.6, 12)
    if any(token in hours for token in ("08", "7", "早")):
        return min(_category_total(ring1000, "office", "transport") * 0.5, 8)
    return 0


def score_assessment(poi_rings: list[dict], financials: dict, business: dict) -> dict:
    ring500 = next((ring for ring in poi_rings if ring.get("radius") == 500), poi_rings[0] if poi_rings else {})
    ring1000 = next((ring for ring in poi_rings if ring.get("radius") == 1000), ring500)
    ring3000 = next((ring for ring in poi_rings if ring.get("radius") == 3000), ring1000)

    total500 = int(ring500.get("total", 0))
    total1000 = int(ring1000.get("total", 0))
    competitors500 = int(ring500.get("competitor_count", 0))
    competitors1000 = int(ring1000.get("competitor_count", 0))
    complements500 = int(ring500.get("complementary_count", 0))

    transport = _category_total(ring1000, "transport")
    parking = _category_total(ring1000, "parking")
    office_residential = _category_total(ring1000, "office", "residential")
    retail_leisure = _category_total(ring3000, "retail", "leisure")
    business_metrics = _business_metrics(financials, business)
    target_bonus = _target_customer_bonus(business.get("target_customer", ""), ring1000)
    hours_bonus = _hours_bonus(business.get("opening_hours", ""), ring1000)
    differentiation = business.get("differentiation", "").strip()
    differentiation_bonus = min(len(differentiation) / 12, 10) if differentiation else 0

    rent_ratio = financials.get("rent_to_revenue_ratio")
    if rent_ratio is None:
        rent_ratio = financials.get("monthly_fixed_cost", 0) / max(financials.get("break_even_revenue", 1), 1)
    survival = float(financials.get("survival_months_worst_case", 0))
    runway_penalty = max(2 - survival, 0) * 6
    daily_orders = business_metrics["break_even_daily_orders"]

    scores = {
        "位置曝光": _clamp(45 + total500 * 0.45 + transport * 2),
        "目标人流": _clamp(40 + office_residential * 0.8 + transport * 2 + retail_leisure * 0.15 + target_bonus),
        "消费能力": _clamp(48 + _category_total(ring1000, "office", "retail") * 0.65 + parking * 1.5 - max(daily_orders - 180, 0) * 0.08),
        "竞品压力": _clamp(88 - competitors500 * 2.3 - competitors1000 * 0.35 + differentiation_bonus),
        "互补业态": _clamp(35 + complements500 * 1.3),
        "交通便利": _clamp(45 + transport * 5 + parking * 1.5),
        "停车条件": _clamp(38 + parking * 5),
        "未来规划": 55,
        "租金合理性": _clamp(95 - rent_ratio * 135 + survival * 2.5 - runway_penalty - max(daily_orders - 220, 0) * 0.06),
        "证照可行性": 62 if any(word in business.get("business_type", "") for word in ("餐", "咖啡", "茶", "食")) else 72,
        "铺位硬件": 58,
        "线上热度": _clamp(45 + total1000 * 0.12 + competitors1000 * 0.3),
        "夜间人气": _clamp(42 + _category_total(ring1000, "food", "leisure") * 0.75 + transport * 1.2 + hours_bonus),
        "周末人气": _clamp(42 + _category_total(ring3000, "retail", "leisure", "residential") * 0.22),
        "风险因素": _clamp(88 - max(competitors500 - 10, 0) * 2 - max(rent_ratio - 0.18, 0) * 140 - max(daily_orders - 260, 0) * 0.05),
    }

    risk_factors: list[str] = []
    if any(ring.get("truncated") for ring in poi_rings):
        risk_factors.append("POI 查询达到分页上限，竞品和互补业态可能仍被低估。")
    if scores["竞品压力"] < 60:
        risk_factors.append("500 米和 1 公里圈层竞品密度偏高，需要明确差异化和价格带。")
    if scores["租金合理性"] < 65:
        risk_factors.append("租金或固定成本压力偏高，建议重新核算保本营业额。")
    if scores["停车条件"] < 55:
        risk_factors.append("停车条件不足，可能影响目的型消费和周末客流。")
    if scores["目标人流"] < 60:
        risk_factors.append("目标客群 POI 支撑不足，需要线下蹲点验证真实人流。")
    if daily_orders >= 220:
        risk_factors.append(f"按当前客单价测算，保本需要约 {daily_orders} 单/日，需验证门店产能和时段客流。")
    if not risk_factors:
        risk_factors.append("第一版未接入规划、房价和外卖价格数据，需线下复核关键假设。")

    weights = {
        "目标人流": 1.2,
        "消费能力": 1.1,
        "竞品压力": 1.0,
        "租金合理性": 1.15,
        "风险因素": 1.1,
    }
    weighted_total = 0.0
    weight_sum = 0.0
    for name, score in scores.items():
        weight = weights.get(name, 1.0)
        weighted_total += score * weight
        weight_sum += weight

    return {
        "overall_score": _clamp(weighted_total / weight_sum),
        "scores": scores,
        "risk_factors": risk_factors,
        "business_metrics": business_metrics,
        "verification_required": ["未来规划", "证照可行性", "铺位硬件", "线上热度", "夜间人气", "周末人气"],
        "method_note": "POI 为真实地图数据；人流、消费能力、规划、夜间/周末热度为规则估算和 AI 研判。",
    }
