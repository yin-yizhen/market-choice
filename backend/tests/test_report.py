import pytest

from app.services.report import build_report_prompt, generate_report


RESEARCH_BUNDLE = {
    "sources": [
        {
            "id": "S1",
            "title": "南京西路街区城市更新规划",
            "url": "https://example.gov.cn/plan",
            "search_query": "上海 南京西路 城市更新 商业 改造",
            "confidence": 0.66,
            "category": "街区发展计划",
            "snippet": "道路提升和商业更新",
        }
    ],
    "categories": {
        "街区发展计划": {
            "status": "supported",
            "summary": "有商业更新",
            "confidence": 0.8,
            "sources": [
                {
                    "id": "S1",
                    "title": "南京西路街区城市更新规划",
                    "url": "https://example.gov.cn/plan",
                    "search_query": "上海 南京西路 城市更新 商业 改造",
                    "confidence": 0.66,
                    "category": "街区发展计划",
                    "snippet": "道路提升和商业更新",
                }
            ],
        }
    },
}


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
        research_bundle=RESEARCH_BUNDLE,
        llm_client=failing_client,
    )

    assert result["source"] == "fallback"
    assert result["ai_error"] == "network down"
    assert "关键结论" in result["markdown"]
    assert "竞品密度偏高" in result["markdown"]
    assert "联网调研证据" in result["markdown"]
    assert "https://example.gov.cn/plan" in result["markdown"]
    assert "上海 南京西路 城市更新 商业 改造" in result["markdown"]


@pytest.mark.asyncio
async def test_generate_report_appends_research_section_when_llm_omits_it():
    async def weak_client(_messages):
        return "## 关键结论\n模型只写了结论。"

    result = await generate_report(
        payload={"location": {"address": "上海市静安区南京西路"}, "business": {"business_type": "咖啡店"}},
        poi_rings=[],
        financials={},
        scoring={},
        research_bundle=RESEARCH_BUNDLE,
        llm_client=weak_client,
    )

    assert result["source"] == "llm"
    assert "联网调研证据" in result["markdown"]
    assert "https://example.gov.cn/plan" in result["markdown"]


def test_build_report_prompt_includes_research_sources():
    messages = build_report_prompt(
        payload={"location": {"address": "上海市静安区南京西路"}, "business": {"business_type": "咖啡店"}},
        poi_rings=[],
        financials={},
        scoring={},
        research_bundle=RESEARCH_BUNDLE,
    )

    assert "https://example.gov.cn/plan" in messages[1]["content"]
    assert "联网证据" in messages[1]["content"]
