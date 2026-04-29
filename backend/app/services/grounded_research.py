from __future__ import annotations

import json
from urllib import request

from app.core.config import get_settings


RESEARCH_CATEGORIES = [
    "街区发展计划",
    "人流与交通",
    "商圈结构",
    "消费能力与人口画像",
    "竞品与价格带",
    "业态政策与证照",
    "线上热度",
    "夜间/周末人气",
]

CATEGORY_KEYWORDS = {
    "街区发展计划": ("规划", "更新", "改造", "施工", "地铁", "道路", "商业升级", "拆迁"),
    "人流与交通": ("人流", "客流", "交通", "地铁", "公交", "通勤", "停车"),
    "商圈结构": ("商圈", "商业", "目的地", "路过", "购物中心", "街区"),
    "消费能力与人口画像": ("消费", "房价", "写字楼", "客单价", "人口", "收入", "商场"),
    "竞品与价格带": ("竞品", "价格", "咖啡", "餐饮", "外卖", "点评", "品牌"),
    "业态政策与证照": ("政策", "证照", "排烟", "环保", "食品经营", "许可", "消防"),
    "线上热度": ("小红书", "大众点评", "抖音", "热度", "评价", "打卡"),
    "夜间/周末人气": ("夜间", "夜经济", "周末", "文旅", "休闲", "夜市"),
}


class GroundedResearchError(RuntimeError):
    pass


def build_grounded_research_prompt(payload: dict, poi_rings: list[dict], financials: dict) -> str:
    location = payload.get("location", {})
    business = payload.get("business", {})
    content = {
        "目标": "为店铺选址生成真实联网调研证据包，不要编造没有来源的结论。",
        "位置": location,
        "业态": business,
        "三圈层POI摘要": poi_rings,
        "财务测算": financials,
        "必须调研的类别": RESEARCH_CATEGORIES,
        "输出要求": [
            "用中文分条总结每个类别。",
            "每个判断都尽量基于公开网页来源。",
            "如果没有证据，明确写证据不足，不要编造。",
            "重点回答需求、人流、竞争、价格带、租金承压、政策证照、未来1-3年街区趋势。",
        ],
    }
    return json.dumps(content, ensure_ascii=False)


def _candidate_text(candidate: dict) -> str:
    parts = candidate.get("content", {}).get("parts", [])
    return "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()


def _extract_sources(metadata: dict) -> list[dict]:
    sources = []
    seen: set[str] = set()
    for index, chunk in enumerate(metadata.get("groundingChunks", []) or []):
        web = chunk.get("web", {}) if isinstance(chunk, dict) else {}
        url = web.get("uri") or web.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append(
            {
                "id": f"S{len(sources) + 1}",
                "title": web.get("title") or url,
                "url": url,
                "score": web.get("score"),
                "index": index,
            }
        )
    return sources


def _support_text_by_source(metadata: dict, source_index: int) -> str:
    texts = []
    for support in metadata.get("groundingSupports", []) or []:
        indices = support.get("groundingChunkIndices", []) if isinstance(support, dict) else []
        if source_index in indices:
            segment = support.get("segment", {})
            if isinstance(segment, dict) and segment.get("text"):
                texts.append(segment["text"])
    return "；".join(texts)


def _build_categories(answer: str, sources: list[dict], metadata: dict) -> dict:
    categories = {}
    lower_answer = answer.lower()
    for name in RESEARCH_CATEGORIES:
        keywords = CATEGORY_KEYWORDS[name]
        matched_sources = []
        for source in sources:
            support = _support_text_by_source(metadata, source["index"])
            haystack = f"{source['title']} {support}".lower()
            if any(keyword.lower() in haystack for keyword in keywords):
                matched_sources.append({key: source[key] for key in ("id", "title", "url")})
        supported = bool(matched_sources) or any(keyword.lower() in lower_answer for keyword in keywords)
        summary = _extract_category_summary(answer, name) if supported else "未找到足够公开资料，需线下核验。"
        confidence = min(0.92, 0.45 + len(matched_sources) * 0.18) if supported else 0.25
        categories[name] = {
            "status": "supported" if supported else "insufficient",
            "summary": summary,
            "confidence": round(confidence, 2),
            "sources": matched_sources,
        }
    return categories


def _extract_category_summary(answer: str, category: str) -> str:
    lines = [line.strip("- 　") for line in answer.splitlines() if line.strip()]
    for line in lines:
        if category[:2] in line or any(keyword in line for keyword in CATEGORY_KEYWORDS[category]):
            return line[:220]
    return lines[0][:220] if lines else "模型返回了联网证据，但未给出该类别的清晰摘要。"


def parse_gemini_grounding_response(response: dict) -> dict:
    candidates = response.get("candidates") or []
    if not candidates:
        raise GroundedResearchError("Gemini grounding 没有返回候选结果")
    candidate = candidates[0]
    metadata = candidate.get("groundingMetadata") or {}
    answer = _candidate_text(candidate)
    queries = metadata.get("webSearchQueries") or []
    sources = _extract_sources(metadata)
    if not sources:
        raise GroundedResearchError("Gemini grounding 没有返回可验证网页来源")

    categories = _build_categories(answer, sources, metadata)
    return {
        "required": True,
        "provider": "gemini",
        "answer": answer,
        "queries": queries,
        "sources": [{key: source[key] for key in ("id", "title", "url", "score")} for source in sources],
        "source_count": len(sources),
        "categories": categories,
    }


async def default_gemini_client(prompt: str) -> dict:
    settings = get_settings()
    if settings.research_mode != "llm_grounding":
        raise GroundedResearchError(f"Unsupported RESEARCH_MODE: {settings.research_mode}")
    if settings.llm_grounding_provider != "gemini":
        raise GroundedResearchError(f"Unsupported LLM_GROUNDING_PROVIDER: {settings.llm_grounding_provider}")
    if not settings.gemini_api_key:
        raise GroundedResearchError("GEMINI_API_KEY is not configured")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_grounding_model}:generateContent?key={settings.gemini_api_key}"
    )
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


async def run_grounded_research(
    payload: dict,
    poi_rings: list[dict],
    financials: dict,
    gemini_client=default_gemini_client,
) -> dict:
    prompt = build_grounded_research_prompt(payload, poi_rings, financials)
    response = await gemini_client(prompt)
    return parse_gemini_grounding_response(response)
