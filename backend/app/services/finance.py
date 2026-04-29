from __future__ import annotations


def _money(value: float | int | None) -> float:
    return float(value or 0)


def _category_total(ring: dict, *names: str) -> int:
    categories = ring.get("categories", {})
    return sum(int(categories.get(name, 0)) for name in names)


def _ring(poi_rings: list[dict], radius: int) -> dict:
    return next((item for item in poi_rings if item.get("radius") == radius), poi_rings[0] if poi_rings else {})


def _default_gross_margin(business_type: str) -> float:
    if any(word in business_type for word in ("咖啡", "茶", "饮品")):
        return 0.58
    if any(word in business_type for word in ("餐", "食", "小吃")):
        return 0.55
    if "零售" in business_type or "便利" in business_type:
        return 0.35
    return 0.5


def _estimated_monthly_revenue(business: dict, poi_rings: list[dict]) -> int:
    ring1000 = _ring(poi_rings, 1000)
    average_ticket = max(_money(business.get("average_ticket")) or 30, 1)
    office = _category_total(ring1000, "office")
    residential = _category_total(ring1000, "residential")
    transport = _category_total(ring1000, "transport")
    retail = _category_total(ring1000, "retail", "leisure")
    daily_orders = 35 + office * 1.5 + residential * 0.45 + transport * 2.0 + retail * 0.8
    return round(daily_orders * average_ticket * 30)


def calculate_financials(financial: dict, business: dict | None = None, poi_rings: list[dict] | None = None) -> dict:
    business = business or {}
    poi_rings = poi_rings or []
    assumption_notes: list[str] = []
    monthly_rent = _money(financial.get("monthly_rent"))
    store_area = max(_money(business.get("store_area")) or 80, 1)
    employee_count = max(int(_money(business.get("employee_count")) or 3), 1)
    business_type = business.get("business_type", "")

    property_fee = _money(financial.get("property_fee"))
    if not property_fee:
        property_fee = round(store_area * 20)
        assumption_notes.append("物业费按店铺面积估算")

    labor_cost = _money(financial.get("labor_cost"))
    if not labor_cost:
        wage = 10000 if any(word in business_type for word in ("咖啡", "茶", "餐", "饮", "食")) else 8500
        labor_cost = employee_count * wage
        assumption_notes.append("人工成本按员工数和本地业态工资估算")

    utilities_cost = _money(financial.get("utilities_cost"))
    if not utilities_cost:
        utilities_cost = round(store_area * (75 if any(word in business_type for word in ("咖啡", "餐", "饮", "食")) else 45))
        assumption_notes.append("水电燃气按面积和业态估算")

    marketing_cost = _money(financial.get("marketing_cost"))
    if not marketing_cost:
        marketing_cost = round(max(monthly_rent * 0.25, 3000))
        assumption_notes.append("营销费用按租金比例估算")

    expected_revenue = financial.get("expected_monthly_revenue")
    if not expected_revenue:
        expected_revenue = _estimated_monthly_revenue(business, poi_rings)
        assumption_notes.append("预计月营收由点位 POI、客单价和业态规则估算")

    explicit_gross_margin = _money(financial.get("gross_margin"))
    gross_margin = max(min(explicit_gross_margin or _default_gross_margin(business_type), 1), 0.01)
    if not explicit_gross_margin:
        assumption_notes.append("毛利率按业态默认值估算")

    raw_material_cost = _money(financial.get("raw_material_cost"))
    if not raw_material_cost:
        raw_material_cost = round(float(expected_revenue or 0) * max(1 - gross_margin, 0))
        assumption_notes.append("原材料成本按预计营收和毛利率反推")

    platform_commission = _money(financial.get("platform_commission"))
    if not platform_commission:
        platform_commission = round(float(expected_revenue or 0) * 0.04)
        assumption_notes.append("平台抽佣按预计营收 4% 估算")

    monthly_fixed_cost = monthly_rent + property_fee + labor_cost + utilities_cost + marketing_cost
    monthly_variable_cost = raw_material_cost + platform_commission
    explicit_one_time = (
        _money(financial.get("transfer_fee"))
        + _money(financial.get("deposit"))
        + _money(financial.get("renovation_cost"))
        + _money(financial.get("equipment_cost"))
        + _money(financial.get("license_cost"))
    )
    available_cash_reserve = _money(financial.get("working_capital"))
    other_investment_total = _money(financial.get("other_investment_total"))
    if other_investment_total and not explicit_one_time and not available_cash_reserve:
        one_time_opening_cost = round(other_investment_total * 0.7)
        available_cash_reserve = round(other_investment_total * 0.3)
        assumption_notes.append("其余投资总计按 70% 开办成本、30% 备用资金拆分")
    else:
        one_time_opening_cost = explicit_one_time
    startup_cost = one_time_opening_cost + available_cash_reserve
    break_even_revenue = int(-(-monthly_fixed_cost // gross_margin))
    rent_to_revenue_ratio = None
    if expected_revenue:
        rent_to_revenue_ratio = round(monthly_rent / float(expected_revenue), 4)

    monthly_loss_at_expected_revenue = 0
    if expected_revenue:
        expected_gross_profit = float(expected_revenue) * gross_margin
        monthly_loss_at_expected_revenue = max(monthly_fixed_cost - expected_gross_profit, 0)
    monthly_cash_burn_worst_case = monthly_fixed_cost
    survival_months = round(available_cash_reserve / monthly_cash_burn_worst_case, 2) if monthly_cash_burn_worst_case else 0
    pressure_ratio = rent_to_revenue_ratio if rent_to_revenue_ratio is not None else monthly_rent / max(break_even_revenue, 1)
    if pressure_ratio <= 0.12 and survival_months >= 4:
        pressure = "low"
    elif pressure_ratio <= 0.22 and survival_months >= 2:
        pressure = "medium"
    else:
        pressure = "high"

    return {
        "property_fee": round(property_fee),
        "labor_cost": round(labor_cost),
        "utilities_cost": round(utilities_cost),
        "raw_material_cost": round(raw_material_cost),
        "platform_commission": round(platform_commission),
        "marketing_cost": round(marketing_cost),
        "monthly_fixed_cost": round(monthly_fixed_cost),
        "monthly_variable_cost": round(monthly_variable_cost),
        "one_time_opening_cost": round(one_time_opening_cost),
        "available_cash_reserve": round(available_cash_reserve),
        "monthly_cash_burn_worst_case": round(monthly_cash_burn_worst_case),
        "monthly_loss_at_expected_revenue": round(monthly_loss_at_expected_revenue),
        "startup_cost": round(startup_cost),
        "break_even_revenue": break_even_revenue,
        "expected_monthly_revenue": round(float(expected_revenue)) if expected_revenue else None,
        "rent_to_revenue_ratio": rent_to_revenue_ratio,
        "survival_months_worst_case": survival_months,
        "cash_pressure_level": pressure,
        "gross_margin": gross_margin,
        "assumption_notes": assumption_notes,
    }
