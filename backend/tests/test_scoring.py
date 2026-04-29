from app.services.finance import calculate_financials
from app.services.scoring import score_assessment


def test_score_assessment_rewards_good_access_and_penalizes_competition():
    rings = [
        {
            "radius": 500,
            "total": 80,
            "categories": {
                "food": 28,
                "retail": 14,
                "office": 12,
                "residential": 8,
                "transport": 6,
                "parking": 5,
            },
            "competitor_count": 18,
            "complementary_count": 37,
        },
        {
            "radius": 1000,
            "total": 180,
            "categories": {
                "food": 55,
                "retail": 30,
                "office": 30,
                "residential": 25,
                "transport": 10,
                "parking": 8,
            },
            "competitor_count": 30,
            "complementary_count": 78,
        },
        {
            "radius": 3000,
            "total": 600,
            "categories": {
                "food": 130,
                "retail": 85,
                "office": 90,
                "residential": 120,
                "transport": 30,
                "parking": 22,
            },
            "competitor_count": 68,
            "complementary_count": 227,
        },
    ]
    financials = calculate_financials(
        {
            "monthly_rent": 30000,
            "property_fee": 2000,
            "labor_cost": 45000,
            "utilities_cost": 6000,
            "raw_material_cost": 50000,
            "marketing_cost": 12000,
            "expected_monthly_revenue": 180000,
            "gross_margin": 0.58,
        }
    )

    result = score_assessment(rings, financials, {"business_type": "咖啡店"})

    assert result["overall_score"] >= 70
    assert result["scores"]["交通便利"] > result["scores"]["竞品压力"]
    assert result["scores"]["租金合理性"] >= 70
    assert len(result["scores"]) == 15
    assert result["risk_factors"]
