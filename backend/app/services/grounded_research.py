from __future__ import annotations

import json
import re
from urllib import error, request

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
    "街区发展计划": ("规划", "更新", "改造", "施工", "地铁", "道路", "商业升级", "拆迁", "城市更新"),
    "人流与交通": ("人流", "客流", "交通", "地铁", "公交", "通勤", "停车"),
    "商圈结构": ("商圈", "商业", "目的地", "路过", "购物中心", "街区"),
    "消费能力与人口画像": ("消费", "房价", "写字楼", "客单价", "人口", "收入", "商场"),
    "竞品与价格带": ("竞品", "价格", "咖啡", "餐饮", "外卖", "点评", "品牌"),
    "业态政策与证照": ("政策", "证照", "排烟", "环保", "食品经营", "许可", "消防"),
    "线上热度": ("小红书", "大众点评", "抖音", "热度", "评价", "打卡"),
    "夜间/周末人气": ("夜间", "夜经济", "周末", "文旅", "休闲", "夜市"),
}

URL_RE = re.compile(r"https?://[^\s\]\)>\"'，。；、]+")


class GroundedResearchError(RuntimeError):
    pass


def _format_http_error(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        body = ""
    message = f"HTTP {exc.code} {exc.reason}"
    if body:
        message = f"{message}: {body[:500]}"
    return message


def build_grounded_research_prompt(payload: dict, poi_rings: list[dict], financials: dict) -> str:
    location = payload.get("location", {})
    business = payload.get("business", {})
    content = {
        "目标": "为店铺选址生成真实联网调研证据包。不要编造没有来源的结论。",
        "位置": location,
        "业态": business,
        "三圈层POI摘要": poi_rings,
        "财务测算": financials,
        "必须调研的类别": RESEARCH_CATEGORIES,
        "输出要求": [
            "用中文分条总结每个类别。",
            "每个判断都必须尽量基于公开网页来源。",
            "如果没有证据，明确写证据不足，不要编造。",
            "重点回答需求、人流、竞争、价格带、租金承压、政策证照、未来1-3年街区趋势。",
            "尽量在回答末尾列出参考来源标题和URL。",
        ],
    }
    return json.dumps(content, ensure_ascii=False)


def _candidate_text(candidate: dict) -> str:
    parts = candidate.get("content", {}).get("parts", [])
    return "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()


def _support_text_by_source(metadata: dict, source_index: int) -> str:
    texts = []
    for support in metadata.get("groundingSupports", []) or []:
        indices = support.get("groundingChunkIndices", []) if isinstance(support, dict) else []
        if source_index in indices:
            segment = support.get("segment", {})
            if isinstance(segment, dict) and segment.get("text"):
                texts.append(segment["text"])
    return "；".join(texts)


def _extract_gemini_sources(metadata: dict) -> list[dict]:
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


def _best_search_query(queries: list[str], category: str, source: dict, snippet: str) -> str:
    if not queries:
        return ""
    keywords = CATEGORY_KEYWORDS.get(category, ())
    best_query = queries[0]
    best_score = -1
    for query in queries:
        haystack = f"{query} {source.get('title', '')} {snippet}".lower()
        score = sum(1 for keyword in keywords if keyword.lower() in haystack)
        if score > best_score:
            best_query = query
            best_score = score
    return best_query


def _evidence_from_source(source: dict, category: str, snippet: str, queries: list[str], confidence: float) -> dict:
    return {
        "id": source.get("id", ""),
        "title": source.get("title") or source.get("url") or "",
        "url": source.get("url", ""),
        "search_query": source.get("search_query") or _best_search_query(queries, category, source, snippet),
        "confidence": round(confidence, 2),
        "category": category,
        "snippet": snippet[:260],
    }


def _build_categories(answer: str, sources: list[dict], queries: list[str], metadata: dict | None = None) -> dict:
    categories = {}
    metadata = metadata or {}
    for name in RESEARCH_CATEGORIES:
        keywords = CATEGORY_KEYWORDS[name]
        matched_sources = []
        for source in sources:
            support = _support_text_by_source(metadata, source.get("index", -1))
            snippet = source.get("snippet") or support
            haystack = f"{source.get('title', '')} {snippet}".lower()
            if any(keyword.lower() in haystack for keyword in keywords):
                confidence = min(0.92, 0.58 + len(matched_sources) * 0.12)
                matched_sources.append(_evidence_from_source(source, name, snippet, queries, confidence))

        if matched_sources:
            categories[name] = {
                "status": "supported",
                "summary": _extract_category_summary(answer, name),
                "confidence": round(min(0.92, 0.5 + len(matched_sources) * 0.16), 2),
                "sources": matched_sources,
            }
        else:
            categories[name] = {
                "status": "insufficient",
                "summary": "未找到可追溯到该类别的公开网页证据，需线下核验。",
                "confidence": 0.2,
                "sources": [],
            }
    return categories


def _flatten_evidence(categories: dict) -> list[dict]:
    evidence = []
    seen: set[tuple[str, str]] = set()
    for category in categories.values():
        for source in category.get("sources", []):
            key = (source.get("category", ""), source.get("url", ""))
            if key in seen:
                continue
            seen.add(key)
            evidence.append(source)
    return evidence


def _extract_category_summary(answer: str, category: str) -> str:
    lines = [line.strip("- 、") for line in answer.splitlines() if line.strip()]
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
    raw_sources = _extract_gemini_sources(metadata)
    if not raw_sources:
        raise GroundedResearchError("Gemini grounding 没有返回可验证网页来源")

    categories = _build_categories(answer, raw_sources, queries, metadata)
    evidence_sources = _flatten_evidence(categories)
    return {
        "required": True,
        "provider": "gemini",
        "answer": answer,
        "queries": queries,
        "sources": evidence_sources,
        "source_count": len(raw_sources),
        "categories": categories,
    }


def _iter_values(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_values(child)
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                yield from _iter_values(json.loads(stripped))
                return
            except json.JSONDecodeError:
                pass
        yield value


def _extract_dashscope_sources(events: list[dict]) -> list[dict]:
    sources = []
    seen: set[str] = set()
    for value in _iter_values(events):
        if isinstance(value, dict):
            url = value.get("url") or value.get("link") or value.get("href")
            if isinstance(url, str) and url.startswith(("http://", "https://")) and url not in seen:
                seen.add(url)
                sources.append(
                    {
                        "id": f"S{len(sources) + 1}",
                        "title": value.get("title") or value.get("name") or url,
                        "url": url,
                        "snippet": value.get("snippet") or value.get("summary") or value.get("content") or "",
                        "search_query": value.get("query") or value.get("search_query") or "",
                    }
                )
        elif isinstance(value, str):
            for match in URL_RE.finditer(value):
                url = match.group(0)
                if url not in seen:
                    seen.add(url)
                    start = max(0, match.start() - 120)
                    end = min(len(value), match.end() + 40)
                    sources.append(
                        {
                            "id": f"S{len(sources) + 1}",
                            "title": url,
                            "url": url,
                            "snippet": value[start:end],
                            "search_query": "",
                        }
                    )
    return sources


def _extract_dashscope_queries(events: list[dict]) -> list[str]:
    queries = []
    seen: set[str] = set()
    for value in _iter_values(events):
        if not isinstance(value, dict):
            continue
        for key in ("query", "search_query", "keyword", "keywords"):
            item = value.get(key)
            if isinstance(item, str) and item and item not in seen:
                seen.add(item)
                queries.append(item)
            elif isinstance(item, list):
                for text in item:
                    if isinstance(text, str) and text and text not in seen:
                        seen.add(text)
                        queries.append(text)
    return queries


def _append_stream_text(current: str, piece: str) -> str:
    if not piece:
        return current
    if piece == current or current.endswith(piece):
        return current
    if piece.startswith(current):
        return piece
    return current + piece


def _message_content_as_text(content) -> str:
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return json.dumps(content, ensure_ascii=False)


def parse_dashscope_agent_events(events: list[dict]) -> dict:
    answer = ""
    tool_texts = []
    for event in events:
        msg = event.get("output", {}).get("choices", [{}])[0].get("message", {})
        content = _message_content_as_text(msg.get("content") or msg.get("reasoning_content"))
        if msg.get("role") == "tool":
            tool_texts.append(content)
        else:
            answer = _append_stream_text(answer, content)

    raw_sources = _extract_dashscope_sources(events)
    if not raw_sources:
        raise GroundedResearchError("DashScope 联网检索 Agent 没有返回可验证网页来源")
    queries = _extract_dashscope_queries(events)
    full_answer = answer.strip() or "\n".join(tool_texts).strip()
    categories = _build_categories(full_answer, raw_sources, queries)
    return {
        "required": True,
        "provider": "dashscope",
        "answer": full_answer,
        "queries": queries,
        "sources": _flatten_evidence(categories),
        "source_count": len(raw_sources),
        "categories": categories,
    }


async def default_gemini_client(prompt: str) -> dict:
    settings = get_settings()
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
    try:
        with request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise GroundedResearchError(f"Gemini grounding HTTP failed: {_format_http_error(exc)}") from exc
    except error.URLError as exc:
        raise GroundedResearchError(f"Gemini grounding network failed: {exc.reason}") from exc


async def default_dashscope_client(prompt: str) -> list[dict]:
    settings = get_settings()
    if not settings.dashscope_api_key:
        raise GroundedResearchError("DASHSCOPE_API_KEY is not configured")
    if not settings.dashscope_web_search_agent_id:
        raise GroundedResearchError("DASHSCOPE_WEB_SEARCH_AGENT_ID is not configured")

    body = json.dumps(
        {
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {
                "agent_options": {
                    "agent_id": settings.dashscope_web_search_agent_id,
                    "agent_version": settings.dashscope_web_search_agent_version,
                }
            },
            "stream": True,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(
        settings.dashscope_web_search_api_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.dashscope_api_key}",
            "Content-Type": "application/json",
        },
    )

    events = []
    try:
        with request.urlopen(req, timeout=90) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                if event.get("code") and event.get("code") != "200":
                    raise GroundedResearchError(f"DashScope 联网检索 Agent 服务异常：{event}")
                events.append(event)
        return events
    except error.HTTPError as exc:
        raise GroundedResearchError(f"DashScope web-search agent HTTP failed: {_format_http_error(exc)}") from exc
    except error.URLError as exc:
        raise GroundedResearchError(f"DashScope web-search agent network failed: {exc.reason}") from exc


async def run_grounded_research(
    payload: dict,
    poi_rings: list[dict],
    financials: dict,
    gemini_client=default_gemini_client,
    dashscope_client=default_dashscope_client,
    provider: str | None = None,
) -> dict:
    settings = get_settings()
    if settings.research_mode != "llm_grounding":
        raise GroundedResearchError(f"Unsupported RESEARCH_MODE: {settings.research_mode}")

    selected_provider = (provider or settings.llm_grounding_provider).lower()
    prompt = build_grounded_research_prompt(payload, poi_rings, financials)
    if selected_provider == "gemini":
        response = await gemini_client(prompt)
        return parse_gemini_grounding_response(response)
    if selected_provider == "dashscope":
        events = await dashscope_client(prompt)
        return parse_dashscope_agent_events(events)
    raise GroundedResearchError(f"Unsupported LLM_GROUNDING_PROVIDER: {selected_provider}")
