import pytest

from app.services.grounded_research import (
    GroundedResearchError,
    build_grounded_research_prompt,
    parse_gemini_grounding_response,
    run_grounded_research,
)


def _gemini_response_with_sources():
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                "街区规划：公开资料显示周边有道路提升和商业更新。\n"
                                "消费能力：写字楼和商业设施密集，客单价可中高端。\n"
                                "证照政策：餐饮需重点核验排烟、环保和食品经营许可。"
                            )
                        }
                    ]
                },
                "groundingMetadata": {
                    "webSearchQueries": ["上海 南京西路 城市更新 商业 改造", "上海 静安区 餐饮 排烟 环保 许可"],
                    "groundingChunks": [
                        {"web": {"uri": "https://example.gov.cn/plan", "title": "南京西路街区更新计划"}},
                        {"web": {"uri": "https://example.gov.cn/policy", "title": "餐饮环保许可办事指南"}},
                    ],
                    "groundingSupports": [
                        {"segment": {"text": "周边有道路提升和商业更新"}, "groundingChunkIndices": [0]},
                        {"segment": {"text": "餐饮需重点核验排烟、环保和食品经营许可"}, "groundingChunkIndices": [1]},
                    ],
                },
            }
        ]
    }


def test_parse_gemini_grounding_response_extracts_queries_sources_and_categories():
    bundle = parse_gemini_grounding_response(_gemini_response_with_sources())

    assert bundle["provider"] == "gemini"
    assert bundle["source_count"] == 2
    assert bundle["queries"] == ["上海 南京西路 城市更新 商业 改造", "上海 静安区 餐饮 排烟 环保 许可"]
    assert bundle["sources"][0]["url"] == "https://example.gov.cn/plan"
    assert bundle["categories"]["街区发展计划"]["confidence"] >= 0.6
    assert "道路提升" in bundle["categories"]["街区发展计划"]["summary"]
    assert bundle["categories"]["业态政策与证照"]["sources"][0]["title"] == "餐饮环保许可办事指南"


def test_parse_gemini_grounding_response_fails_without_sources():
    response = {"candidates": [{"content": {"parts": [{"text": "只有模型回答，没有来源。"}]}, "groundingMetadata": {}}]}

    with pytest.raises(GroundedResearchError, match="没有返回可验证网页来源"):
        parse_gemini_grounding_response(response)


@pytest.mark.asyncio
async def test_run_grounded_research_uses_client_and_returns_bundle():
    async def fake_client(_prompt):
        return _gemini_response_with_sources()

    bundle = await run_grounded_research(
        payload={"location": {"address": "上海市静安区南京西路", "city": "上海"}, "business": {"business_type": "咖啡店"}},
        poi_rings=[{"radius": 1000, "total": 180, "categories": {"office": 30}}],
        financials={"monthly_fixed_cost": 80000, "break_even_revenue": 160000},
        gemini_client=fake_client,
    )

    assert bundle["required"] is True
    assert bundle["categories"]["消费能力与人口画像"]["status"] == "supported"


def test_build_grounded_research_prompt_contains_required_research_questions():
    prompt = build_grounded_research_prompt(
        payload={"location": {"address": "上海市静安区南京西路", "city": "上海"}, "business": {"business_type": "咖啡店"}},
        poi_rings=[{"radius": 500, "total": 42}],
        financials={"break_even_revenue": 100000},
    )

    assert "街区发展计划" in prompt
    assert "消费能力与人口画像" in prompt
    assert "证照" in prompt
    assert "不要编造" in prompt
