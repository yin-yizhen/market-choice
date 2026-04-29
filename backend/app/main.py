from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.schemas import AnalyzeRequest, AnalyzeResponse, GeocodeCandidate
from app.services.amap import geocode, search_pois_around_detailed
from app.services.finance import calculate_financials
from app.services.poi import summarize_ring
from app.services.report import generate_report
from app.services.scoring import score_assessment


settings = get_settings()
app = FastAPI(title="店铺选址评估 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/geocode", response_model=list[GeocodeCandidate])
def geocode_endpoint(keyword: str, city: str = "") -> list[dict]:
    try:
        return geocode(keyword, city)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/analyze-location", response_model=AnalyzeResponse)
async def analyze_location(payload: AnalyzeRequest) -> dict:
    request_dict = payload.model_dump()
    rings = []
    errors = []
    for radius in (500, 1000, 3000):
        try:
            poi_result = search_pois_around_detailed(payload.location.latitude, payload.location.longitude, radius)
            pois = poi_result["pois"]
        except Exception as exc:
            pois = []
            poi_result = {"declared_count": 0, "pages_fetched": 0, "truncated": False}
            errors.append(f"{radius} 米 POI 查询失败：{exc}")
        ring_summary = summarize_ring(radius, pois, payload.business.business_type)
        ring_summary.update(
            {
                "declared_count": poi_result["declared_count"],
                "pages_fetched": poi_result["pages_fetched"],
                "truncated": poi_result["truncated"],
            }
        )
        rings.append(ring_summary)

    financials = calculate_financials(request_dict["financial"])
    scoring = score_assessment(rings, financials, request_dict["business"])
    report = await generate_report(request_dict, rings, financials, scoring)
    notes = [
        "POI 数据来自高德地图 Web 服务。",
        "人流、消费能力、规划、夜间/周末热度为规则估算与 AI 研判。",
        "房价、城市更新、外卖价格和政策细则尚未接入真实数据源。",
    ]
    if any(ring.get("truncated") for ring in rings):
        notes.append("部分圈层 POI 达到分页上限，系统已标记 truncated=true，竞品和需求判断需谨慎。")
    notes.extend(errors)
    return {
        "data_notes": notes,
        "poi_rings": rings,
        "financials": financials,
        "scoring": scoring,
        "report": report,
    }
