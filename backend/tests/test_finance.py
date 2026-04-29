from app.services.finance import calculate_financials


def test_calculate_financials_rolls_up_costs_and_runway():
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
    assert result["startup_cost"] == 540000
    assert result["break_even_revenue"] == 163794
    assert result["rent_to_revenue_ratio"] == 0.1667
    assert result["survival_months_worst_case"] == 5.68
    assert result["cash_pressure_level"] == "medium"


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

    assert result["monthly_fixed_cost"] == 49000
    assert result["break_even_revenue"] == 98000
    assert result["rent_to_revenue_ratio"] is None
    assert result["survival_months_worst_case"] == 0
