from __future__ import annotations


def _money(value: float | int | None) -> float:
    return float(value or 0)


def calculate_financials(financial: dict) -> dict:
    monthly_rent = _money(financial.get("monthly_rent"))
    property_fee = _money(financial.get("property_fee"))
    labor_cost = _money(financial.get("labor_cost"))
    utilities_cost = _money(financial.get("utilities_cost"))
    marketing_cost = _money(financial.get("marketing_cost"))
    raw_material_cost = _money(financial.get("raw_material_cost"))
    platform_commission = _money(financial.get("platform_commission"))
    expected_revenue = financial.get("expected_monthly_revenue")
    gross_margin = max(min(_money(financial.get("gross_margin")) or 0.55, 1), 0.01)

    monthly_fixed_cost = monthly_rent + property_fee + labor_cost + utilities_cost + marketing_cost
    monthly_variable_cost = raw_material_cost + platform_commission
    startup_cost = (
        _money(financial.get("transfer_fee"))
        + _money(financial.get("deposit"))
        + _money(financial.get("renovation_cost"))
        + _money(financial.get("equipment_cost"))
        + _money(financial.get("license_cost"))
        + _money(financial.get("working_capital"))
    )
    break_even_revenue = int(-(-monthly_fixed_cost // gross_margin))
    rent_to_revenue_ratio = None
    if expected_revenue:
        rent_to_revenue_ratio = round(monthly_rent / float(expected_revenue), 4)

    survival_months = round(startup_cost / monthly_fixed_cost, 2) if monthly_fixed_cost else 0
    pressure_ratio = rent_to_revenue_ratio if rent_to_revenue_ratio is not None else monthly_rent / max(break_even_revenue, 1)
    if pressure_ratio <= 0.12 and survival_months >= 4:
        pressure = "low"
    elif pressure_ratio <= 0.22 and survival_months >= 2:
        pressure = "medium"
    else:
        pressure = "high"

    return {
        "monthly_fixed_cost": round(monthly_fixed_cost),
        "monthly_variable_cost": round(monthly_variable_cost),
        "startup_cost": round(startup_cost),
        "break_even_revenue": break_even_revenue,
        "rent_to_revenue_ratio": rent_to_revenue_ratio,
        "survival_months_worst_case": survival_months,
        "cash_pressure_level": pressure,
        "gross_margin": gross_margin,
    }
