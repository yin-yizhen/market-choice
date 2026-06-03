import json

import pytest

from app.core.config import get_settings
from app.services.grounded_research import (
    RESEARCH_CATEGORIES,
    _clean_search_query,
    _extract_dashscope_sources,
    _source_url_is_reachable,
    build_category_grounded_research_prompt,
    build_grounded_research_prompt,
    run_grounded_research,
)


def test_build_grounded_research_prompt_uses_readable_chinese():
    prompt = build_grounded_research_prompt(
        payload={"location": {"address": "上海市静安区南京西路", "city": "上海"}, "business": {"business_type": "咖啡店"}},
        poi_rings=[{"radius": 500, "total": 42}],
        financials={"break_even_revenue": 100000},
    )

    assert "店铺选址" in prompt
    assert "街区发展规划" in prompt
    assert "消费能力与人口画像" in prompt
    assert "证照" in prompt
    assert "不要编造" in prompt


def test_category_prompt_adds_business_specific_game_keywords():
    prompt = build_category_grounded_research_prompt(
        payload={
            "location": {"address": "西安市长安区西北大学长安校区", "city": "西安"},
            "business": {"business_type": "主机游戏体验店"},
        },
        poi_rings=[{"radius": 500, "total": 42}],
        financials={"break_even_revenue": 100000},
        category="业态政策与证照",
    )

    assert "游戏游艺" in prompt
    assert "文化经营许可证" in prompt
    assert "未成年人保护" in prompt
    assert "消防验收" in prompt
    assert "必须调用联网搜索工具" in prompt
    assert "不要直接回答" in prompt


def test_dashscope_source_extraction_ignores_truncated_urls_and_keeps_markdown_links():
    events = [
        {
            "code": "200",
            "output": {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                "无效片段：http://www 和 http://sfj 不应展示。\n"
                                "有效来源：[西安市市场监督管理局](https://scjg.xa.gov.cn/ztzl/spaq/123.html)"
                            ),
                        }
                    }
                ]
            },
        }
    ]

    sources = _extract_dashscope_sources(events)

    assert [source["url"] for source in sources] == ["https://scjg.xa.gov.cn/ztzl/spaq/123.html"]
    assert sources[0]["title"] == "西安市市场监督管理局"


def test_dashscope_source_extraction_ignores_static_asset_urls():
    events = [
        {
            "code": "200",
            "output": {
                "choices": [
                    {
                        "message": {
                            "role": "tool",
                            "content": json.dumps(
                                [
                                    {
                                        "title": "站点图标",
                                        "url": "https://img.alicdn.com/logo.svg",
                                        "snippet": "图标资源",
                                    },
                                    {
                                        "title": "行政处罚决定书",
                                        "url": "https://www.changanqu.gov.cn/zwgk/xzzf/example.html",
                                        "snippet": "公开网页",
                                    },
                                ],
                                ensure_ascii=False,
                            ),
                        }
                    }
                ]
            },
        }
    ]

    sources = _extract_dashscope_sources(events)

    assert [source["url"] for source in sources] == ["https://www.changanqu.gov.cn/zwgk/xzzf/example.html"]


def test_source_url_reachability_accepts_real_response_and_rejects_network_failure(monkeypatch):
    class Response:
        status = 403

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def reachable(*_args, **_kwargs):
        return Response()

    def unreachable(*_args, **_kwargs):
        raise OSError("cannot connect")

    monkeypatch.setattr("app.services.grounded_research.request.urlopen", reachable)
    assert _source_url_is_reachable("https://example.com/page") is True

    monkeypatch.setattr("app.services.grounded_research.request.urlopen", unreachable)
    assert _source_url_is_reachable("https://map.baidu") is False


def test_search_query_cleanup_removes_prompt_payload():
    query = (
        "必须调用联网搜索工具，不要直接回答，不要仅凭模型知识回答。 "
        "请搜索：西安市 西北大学长安校区 桌游店 线上热度 小红书 大众点评 "
        "本次只调研类别：线上热度 位置：{\"address\":\"x\"} 三圈层POI摘要：[] 财务测算：{}"
    )

    cleaned = _clean_search_query(query)

    assert cleaned == "西安市 西北大学长安校区 桌游店 线上热度 小红书 大众点评"
    assert "财务测算" not in cleaned
    assert "三圈层" not in cleaned


@pytest.mark.asyncio
async def test_dashscope_research_runs_one_search_per_category(monkeypatch):
    monkeypatch.setenv("RESEARCH_MODE", "llm_grounding")
    monkeypatch.setattr("app.services.grounded_research._source_url_is_reachable", lambda _url: True)
    get_settings.cache_clear()
    calls = []

    async def fake_dashscope_client(prompt):
        category = RESEARCH_CATEGORIES[len(calls)]
        calls.append(prompt)
        return [
            {
                "code": "200",
                "output": {
                    "choices": [
                        {
                            "message": {
                                "role": "tool",
                                "content": json.dumps(
                                    [
                                        {
                                            "title": f"{category} 来源",
                                            "url": f"https://example.com/{len(calls)}",
                                            "snippet": "这条摘要不包含分类关键词，但来自该分类的独立检索。",
                                            "query": category,
                                        }
                                    ],
                                    ensure_ascii=False,
                                ),
                            }
                        }
                    ]
                },
            }
        ]

    bundle = await run_grounded_research(
        payload={"location": {"address": "上海市静安区南京西路", "city": "上海"}, "business": {"business_type": "咖啡店"}},
        poi_rings=[{"radius": 1000, "total": 180, "categories": {"office": 30}}],
        financials={"monthly_fixed_cost": 80000, "break_even_revenue": 160000},
        dashscope_client=fake_dashscope_client,
        provider="dashscope",
    )

    assert len(calls) == len(RESEARCH_CATEGORIES)
    assert all(category in calls[index] for index, category in enumerate(RESEARCH_CATEGORIES))
    assert all(bundle["categories"][category]["status"] == "supported" for category in RESEARCH_CATEGORIES)

    get_settings.cache_clear()
