from __future__ import annotations

import json
from urllib import request

from app.core.config import get_settings


def build_report_prompt(
    payload: dict,
    poi_rings: list[dict],
    financials: dict,
    scoring: dict,
    research_bundle: dict | None = None,
) -> list[dict]:
    content = {
        "task": "生成中国大陆店铺选址预测报告",
        "requirements": [
            "回答需求、季节/时段稳定性、竞争、差异化、价格匹配、租金承压、最坏支撑月数、未来1-3年趋势、铺位硬伤、数据证明。",
            "明确区分真实 POI 数据、联网证据、规则估算和 AI 研判。",
            "输出中文，直接给经营者可执行建议。",
            "引用联网证据时保留来源标题和 URL；证据不足时必须标注待线下核验。",
        ],
        "input": payload,
        "poi_rings": poi_rings,
        "financials": financials,
        "scoring": scoring,
        "联网证据": research_bundle or {},
    }
    return [
        {"role": "system", "content": "你是谨慎、数据导向的商业选址顾问。"},
        {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
    ]


async def default_llm_client(messages: list[dict]) -> str:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not configured")

    body = json.dumps(
        {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0.2,
        }
    ).encode("utf-8")
    req = request.Request(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _research_lines(research_bundle: dict | None) -> list[str]:
    if not research_bundle:
        return ["- 未提供联网证据，相关结论需线下核验。"]
    lines = []
    for name, category in research_bundle.get("categories", {}).items():
        status = "有来源" if category.get("status") == "supported" and category.get("sources") else "证据不足"
        lines.append(f"- {name}: {status}；置信度 {category.get('confidence', 0)}；{category.get('summary', '')}")
        for source in category.get("sources", []):
            lines.append(
                "- 证据："
                f"{source.get('title') or source.get('url')} | "
                f"{source.get('url')} | "
                f"查询：{source.get('search_query', '')} | "
                f"置信度：{source.get('confidence', 0)}"
            )
    return lines or ["- 未提供联网证据，相关结论需线下核验。"]


def _research_markdown_section(research_bundle: dict | None) -> str:
    return "\n".join(["", "## 联网调研证据", *_research_lines(research_bundle), ""])


def _ensure_research_section(markdown: str, research_bundle: dict | None) -> str:
    if "联网调研证据" in markdown:
        return markdown
    return f"{markdown.rstrip()}{_research_markdown_section(research_bundle)}"


def _fallback_markdown(
    payload: dict,
    poi_rings: list[dict],
    financials: dict,
    scoring: dict,
    research_bundle: dict | None = None,
) -> str:
    location = payload.get("location", {})
    business = payload.get("business", {})
    risks = scoring.get("risk_factors", [])
    scores = scoring.get("scores", {})
    ring_lines = [
        f"- {ring.get('radius')} 米：POI {ring.get('total', 0)} 个，竞品 {ring.get('competitor_count', 0)} 个，互补业态 {ring.get('complementary_count', 0)} 个"
        for ring in poi_rings
    ]
    risk_lines = [f"- {risk}" for risk in risks]
    score_lines = [f"- {name}: {score} 分" for name, score in scores.items()]
    metrics = scoring.get("business_metrics", {})
    verification = scoring.get("verification_required", [])
    markdown = "\n".join(
        [
            "## 关键结论",
            f"{location.get('address', '当前点位')} 的 {business.get('business_type', '目标业态')} 选址综合得分为 {scoring.get('overall_score', 0)} 分。",
            "该降级报告基于真实 POI、联网证据、用户财务输入和规则估算生成；规划、房价、外卖价格等仍需人工复核。",
            "",
            "## 三圈层业态",
            *ring_lines,
            "",
            "## 财务承压",
            f"- 保本月营业额约 {financials.get('break_even_revenue', 0)} 元",
            f"- 保本日单量约 {metrics.get('break_even_daily_orders', 0)} 单",
            f"- 最坏情况下资金可支撑 {financials.get('survival_months_worst_case', 0)} 个月",
            f"- 一次性开办成本约 {financials.get('one_time_opening_cost', 0)} 元",
            f"- 可用备用资金约 {financials.get('available_cash_reserve', 0)} 元",
            f"- 现金压力等级：{financials.get('cash_pressure_level', 'unknown')}",
            *(f"- {note}" for note in financials.get("assumption_notes", [])),
            "",
            "## 调研评分",
            *score_lines,
            "",
            "## 风险与建议",
            *(risk_lines or ["- 暂未发现高风险，但需要实地踏点验证客流。"]),
            "",
            "## 待线下核验",
            *(f"- {item}" for item in verification),
        ]
    )
    return _ensure_research_section(markdown, research_bundle)


async def generate_report(
    payload: dict,
    poi_rings: list[dict],
    financials: dict,
    scoring: dict,
    research_bundle: dict | None = None,
    llm_client=default_llm_client,
) -> dict:
    messages = build_report_prompt(payload, poi_rings, financials, scoring, research_bundle)
    try:
        markdown = await llm_client(messages)
        return {"source": "llm", "markdown": _ensure_research_section(markdown, research_bundle), "ai_error": None}
    except Exception as exc:
        return {
            "source": "fallback",
            "markdown": _fallback_markdown(payload, poi_rings, financials, scoring, research_bundle),
            "ai_error": str(exc),
        }
