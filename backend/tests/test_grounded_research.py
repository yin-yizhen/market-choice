import pytest

from app.services.grounded_research import (
    GroundedResearchError,
    build_grounded_research_prompt,
    parse_dashscope_agent_events,
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


def _dashscope_events_with_sources():
    return [
        {
            "code": "200",
            "output": {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "街区规划：南京西路周边有商业更新和道路优化。",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "web_search",
                                        "arguments": {"query": "上海 南京西路 城市更新 商业 改造"},
                                    }
                                }
                            ],
                        }
                    }
                ]
            },
        },
        {
            "code": "200",
            "output": {
                "choices": [
                    {
                        "message": {
                            "role": "tool",
                            "content": '[{"title":"南京西路街区更新计划","url":"https://example.gov.cn/plan","snippet":"道路提升和商业更新"}]',
                        }
                    }
                ]
            },
        },
        {
            "code": "200",
            "output": {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "\n证照政策：餐饮门店需要核验排烟、环保、食品经营许可。参考：https://example.gov.cn/policy",
                        }
                    }
                ]
            },
        },
    ]


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


def test_parse_dashscope_agent_events_extracts_sources_queries_and_categories():
    bundle = parse_dashscope_agent_events(_dashscope_events_with_sources())

    assert bundle["provider"] == "dashscope"
    assert bundle["source_count"] == 2
    assert bundle["queries"] == ["上海 南京西路 城市更新 商业 改造"]
    assert bundle["sources"][0]["title"] == "南京西路街区更新计划"
    assert bundle["sources"][1]["url"] == "https://example.gov.cn/policy"
    assert bundle["categories"]["街区发展计划"]["status"] == "supported"
    assert bundle["categories"]["业态政策与证照"]["status"] == "supported"


def test_parse_dashscope_agent_events_fails_without_sources():
    events = [{"code": "200", "output": {"choices": [{"message": {"role": "assistant", "content": "只有答案没有来源"}}]}}]

    with pytest.raises(GroundedResearchError, match="没有返回可验证网页来源"):
        parse_dashscope_agent_events(events)


@pytest.mark.asyncio
async def test_run_grounded_research_can_use_dashscope_provider():
    async def fake_dashscope_client(_prompt):
        return _dashscope_events_with_sources()

    bundle = await run_grounded_research(
        payload={"location": {"address": "上海市静安区南京西路", "city": "上海"}, "business": {"business_type": "咖啡店"}},
        poi_rings=[{"radius": 1000, "total": 180, "categories": {"office": 30}}],
        financials={"monthly_fixed_cost": 80000, "break_even_revenue": 160000},
        dashscope_client=fake_dashscope_client,
        provider="dashscope",
    )

    assert bundle["required"] is True
    assert bundle["provider"] == "dashscope"


@pytest.mark.asyncio
async def test_run_grounded_research_can_use_gemini_provider():
    async def fake_gemini_client(_prompt):
        return _gemini_response_with_sources()

    bundle = await run_grounded_research(
        payload={"location": {"address": "上海市静安区南京西路", "city": "上海"}, "business": {"business_type": "咖啡店"}},
        poi_rings=[{"radius": 1000, "total": 180, "categories": {"office": 30}}],
        financials={"monthly_fixed_cost": 80000, "break_even_revenue": 160000},
        gemini_client=fake_gemini_client,
        provider="gemini",
    )

    assert bundle["required"] is True
    assert bundle["provider"] == "gemini"


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
