from app.services.finance import calculate_financials


def test_calculate_financials_separates_opening_costs_from_runway_cash():
    result = calculate_financials(
        {
            "monthly_rent": 30000,
            "property_fee": 2000,
            "transfer_fee": 120000,
            "deposit": 60000,
            "renovation_cost": 180000,
            "equipment_cost": 80000,
            "labor_cost": 45000,
            "utilities_cost": 6000,
            "raw_material_cost": 50000,
            "platform_commission": 8000,
            "marketing_cost": 12000,
            "license_cost": 10000,
            "working_capital": 90000,
            "expected_monthly_revenue": 180000,
            "gross_margin": 0.58,
        }
    )

    assert result["monthly_fixed_cost"] == 95000
    assert result["monthly_variable_cost"] == 58000
    assert result["one_time_opening_cost"] == 450000
    assert result["available_cash_reserve"] == 90000
    assert result["startup_cost"] == 540000
    assert result["break_even_revenue"] == 163794
    assert result["rent_to_revenue_ratio"] == 0.1667
    assert result["monthly_cash_burn_worst_case"] == 95000
    assert result["monthly_loss_at_expected_revenue"] == 0
    assert result["survival_months_worst_case"] == 0.95
    assert result["cash_pressure_level"] == "high"


def test_calculate_financials_handles_missing_revenue():
    result = calculate_financials(
        {
            "monthly_rent": 18000,
            "property_fee": 1000,
            "labor_cost": 26000,
            "utilities_cost": 4000,
            "raw_material_cost": 20000,
            "gross_margin": 0.5,
        }
    )

    assert result["marketing_cost"] == 4500
    assert result["monthly_fixed_cost"] == 53500
    assert result["break_even_revenue"] == 107000
    assert result["expected_monthly_revenue"] > 0
    assert result["rent_to_revenue_ratio"] is not None
    assert result["available_cash_reserve"] == 0
    assert result["survival_months_worst_case"] == 0


def test_calculate_financials_estimates_missing_costs_from_business_and_poi():
    result = calculate_financials(
        {"monthly_rent": 28000, "other_investment_total": 200000},
        business={"business_type": "咖啡店", "average_ticket": 32, "store_area": 80, "employee_count": 4},
        poi_rings=[
            {"radius": 500, "total": 80, "categories": {"office": 12, "retail": 14, "transport": 6}},
            {"radius": 1000, "total": 180, "categories": {"office": 30, "residential": 25, "retail": 30}},
            {"radius": 3000, "total": 600, "categories": {}},
        ],
    )

    assert result["property_fee"] == 1600
    assert result["labor_cost"] == 40000
    assert result["one_time_opening_cost"] == 140000
    assert result["available_cash_reserve"] == 60000
    assert result["expected_monthly_revenue"] > 0
    assert result["gross_margin"] == 0.58
    assert "预计月营收由点位 POI、客单价和业态规则估算" in result["assumption_notes"]
