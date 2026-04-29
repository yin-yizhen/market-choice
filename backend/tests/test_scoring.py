from app.services.finance import calculate_financials
from app.services.scoring import score_assessment


def _rings():
    return [
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
            "truncated": False,
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
            "truncated": False,
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
            "truncated": False,
        },
    ]


def test_score_assessment_uses_business_inputs_for_metrics_and_scores():
    financials = calculate_financials(
        {
            "monthly_rent": 30000,
            "property_fee": 2000,
            "labor_cost": 45000,
            "utilities_cost": 6000,
            "raw_material_cost": 50000,
            "marketing_cost": 12000,
            "working_capital": 90000,
            "expected_monthly_revenue": 180000,
            "gross_margin": 0.58,
        }
    )

    result = score_assessment(
        _rings(),
        financials,
        {
            "business_type": "咖啡店",
            "average_ticket": 32,
            "store_area": 80,
            "employee_count": 4,
            "target_customer": "周边白领、办公楼人群",
            "opening_hours": "08:00-22:00",
            "differentiation": "精品咖啡、轻食、外带效率高",
        },
    )

    assert result["overall_score"] >= 65
    assert result["scores"]["交通便利"] > result["scores"]["竞品压力"]
    assert result["scores"]["租金合理性"] < 70
    assert result["business_metrics"]["break_even_daily_orders"] == 171
    assert result["business_metrics"]["monthly_revenue_per_sqm"] == 2250
    assert result["business_metrics"]["monthly_revenue_per_employee"] == 45000
    assert len(result["scores"]) == 15
    assert "未来规划" in result["verification_required"]


def test_score_assessment_flags_truncated_poi_results():
    rings = _rings()
    rings[2]["truncated"] = True
    financials = calculate_financials({"monthly_rent": 10000, "working_capital": 50000})

    result = score_assessment(rings, financials, {"business_type": "咖啡店", "average_ticket": 30})

    assert any("分页上限" in risk for risk in result["risk_factors"])


def test_score_assessment_uses_research_evidence_for_planning_policy_and_heat():
    financials = calculate_financials({"monthly_rent": 10000, "other_investment_total": 120000})
    research_bundle = {
        "categories": {
            "街区发展计划": {"status": "supported", "confidence": 0.86, "summary": "有商业更新和慢行优化"},
            "业态政策与证照": {"status": "supported", "confidence": 0.82, "summary": "餐饮需核验排烟和食品许可"},
            "线上热度": {"status": "supported", "confidence": 0.78, "summary": "社交平台讨论和店铺评价活跃"},
            "夜间/周末人气": {"status": "supported", "confidence": 0.75, "summary": "夜间商业和周末消费活跃"},
        }
    }

    result = score_assessment(_rings(), financials, {"business_type": "咖啡店", "average_ticket": 32}, research_bundle)

    assert result["scores"]["未来规划"] > 55
    assert result["scores"]["证照可行性"] >= 65
    assert result["scores"]["线上热度"] >= 60
    assert "联网证据" in result["method_note"]
