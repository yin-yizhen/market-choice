from __future__ import annotations

import json
from urllib import request

from app.core.config import get_settings


def build_report_prompt(payload: dict, poi_rings: list[dict], financials: dict, scoring: dict) -> list[dict]:
    content = {
        "task": "生成中国大陆店铺选址预测报告",
        "requirements": [
            "回答需求、季节/时段稳定性、竞争、差异化、价格匹配、租金承压、最坏支撑月数、未来1-3年趋势、铺位硬伤、数据证明。",
            "明确区分真实POI数据与估算/AI研判。",
            "输出中文，直接给经营者可执行建议。",
        ],
        "input": payload,
        "poi_rings": poi_rings,
        "financials": financials,
        "scoring": scoring,
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


def _fallback_markdown(payload: dict, poi_rings: list[dict], financials: dict, scoring: dict) -> str:
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
    return "\n".join(
        [
            "## 关键结论",
            f"{location.get('address', '当前点位')} 的 {business.get('business_type', '目标业态')} 选址综合得分为 {scoring.get('overall_score', 0)} 分。",
            "第一版结论基于真实 POI、用户财务输入和规则估算生成；规划、房价、外卖价格等仍需人工复核。",
            "",
            "## 三圈层业态",
            *ring_lines,
            "",
            "## 财务承压",
            f"- 保本月营业额约 {financials.get('break_even_revenue', 0)} 元",
            f"- 保本日单量约 {metrics.get('break_even_daily_orders', 0)} 单",
            f"- 最坏情况资金可支撑 {financials.get('survival_months_worst_case', 0)} 个月",
            f"- 一次性开办成本约 {financials.get('one_time_opening_cost', 0)} 元",
            f"- 可用备用资金约 {financials.get('available_cash_reserve', 0)} 元",
            f"- 现金压力等级：{financials.get('cash_pressure_level', 'unknown')}",
            *(f"- {note}" for note in financials.get("assumption_notes", [])),
            "",
            "## 调研评分",
            *score_lines,
            "",
            "## 风险与建议",
            *(risk_lines or ["- 暂未发现高风险，但需要实地蹲点验证客流。"]),
            "",
            "## 待线下核验",
            *(f"- {item}" for item in verification),
        ]
    )


async def generate_report(
    payload: dict,
    poi_rings: list[dict],
    financials: dict,
    scoring: dict,
    llm_client=default_llm_client,
) -> dict:
    messages = build_report_prompt(payload, poi_rings, financials, scoring)
    try:
        markdown = await llm_client(messages)
        return {"source": "llm", "markdown": markdown, "ai_error": None}
    except Exception as exc:
        return {
            "source": "fallback",
            "markdown": _fallback_markdown(payload, poi_rings, financials, scoring),
            "ai_error": str(exc),
        }
