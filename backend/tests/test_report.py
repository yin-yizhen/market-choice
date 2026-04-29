import pytest

from app.services.report import generate_report


@pytest.mark.asyncio
async def test_generate_report_falls_back_when_llm_fails():
    async def failing_client(_messages):
        raise RuntimeError("network down")

    result = await generate_report(
        payload={
            "location": {"address": "上海市静安区南京西路", "city": "上海"},
            "business": {"business_type": "咖啡店", "average_ticket": 32},
        },
        poi_rings=[{"radius": 500, "total": 42, "categories": {}, "competitor_count": 8}],
        financials={"break_even_revenue": 100000, "survival_months_worst_case": 4.5},
        scoring={"overall_score": 68, "scores": {"目标人流": 72}, "risk_factors": ["竞品密度偏高"]},
        llm_client=failing_client,
    )

    assert result["source"] == "fallback"
    assert result["ai_error"] == "network down"
    assert "关键结论" in result["markdown"]
    assert "竞品密度偏高" in result["markdown"]
