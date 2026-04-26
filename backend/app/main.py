from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .ai_client import enrich_article as enrich_article_with_ai
from .collector import absorb_seen_text, collect_candidates, load_config, relevant, save_config, score_candidate
from .database import (
    VALID_STATUSES,
    add_seen_titles_urls,
    create_log,
    export_selected_markdown,
    get_article,
    init_db,
    list_articles,
    list_articles_needing_ai,
    list_logs,
    save_candidates,
    update_ai_content,
    update_status,
)


class FetchRequest(BaseModel):
    rows: int = Field(default=30, ge=1, le=100)
    days: int = Field(default=30, ge=1, le=365)
    min_score: int = Field(default=45, ge=-100, le=200)
    max_age_days: int = Field(default=90, ge=0, le=3650)
    dry_run: bool = False


class StatusRequest(BaseModel):
    status: str


class ExportRequest(BaseModel):
    mark_shared: bool = False


class AIConfig(BaseModel):
    provider: str = ""
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    max_input_chars: int = Field(default=6000, ge=1000, le=30000)


class MachineTranslationConfig(BaseModel):
    enabled: bool = False
    provider: str = "baidu"
    base_url: str = ""
    app_id: str = ""
    secret_key: str = ""
    api_key: str = ""
    source_lang: str = "en"
    target_lang: str = "zh"


class EnrichRequest(BaseModel):
    article_id: int
    ai: AIConfig = Field(default_factory=AIConfig)
    translation: MachineTranslationConfig | None = None


class EnrichBatchRequest(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)
    translation: MachineTranslationConfig | None = None
    status: str | None = "candidate"
    limit: int = Field(default=100, ge=1, le=500)


def has_ai_config(config: AIConfig) -> bool:
    return bool(config.api_key.strip() and config.base_url.strip() and config.model.strip())


app = FastAPI(title="Privacy Paper Dashboard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/fetch")
def fetch_today(payload: FetchRequest) -> dict:
    config = load_config()
    candidates, source_counts, failures = collect_candidates(config, payload.rows, payload.days)
    if payload.dry_run:
        filtered = 0
        relevant_count = 0
        for candidate in candidates:
            score_candidate(candidate, config)
            if relevant(candidate, config, payload.min_score, payload.max_age_days):
                relevant_count += 1
            else:
                filtered += 1
        stats = {"inserted": 0, "updated": 0, "filtered": filtered, "duplicates": 0}
        message = f"dry-run：{relevant_count} 条候选通过基础过滤，未写入数据库。"
    else:
        stats = save_candidates(candidates, config, payload.min_score, payload.max_age_days)
        message = "抓取完成，候选已写入工作台。"
    log = create_log(
        source_counts=source_counts,
        failures=failures,
        candidates_total=len(candidates),
        stats=stats,
        status="partial" if failures else "success",
        message=message,
    )
    return {"candidates_total": len(candidates), "source_counts": source_counts, "failures": failures, "stats": stats, "log": log}


@app.get("/api/articles")
def articles(status: str | None = Query(default=None), q: str | None = Query(default=None)) -> list[dict]:
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    return list_articles(status, q)


@app.get("/api/articles/{article_id}")
def article_detail(article_id: int) -> dict:
    article = get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@app.patch("/api/articles/{article_id}/status")
def set_article_status(article_id: int, payload: StatusRequest) -> dict:
    try:
        article = update_status(article_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@app.post("/api/upload-seen")
async def upload_seen(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    text = raw.decode("utf-8-sig", errors="replace")
    titles, urls = absorb_seen_text(text)
    inserted = add_seen_titles_urls(titles, urls, f"upload:{file.filename}")
    return {"filename": file.filename, "titles": len(titles), "urls": len(urls), "inserted": inserted}


@app.post("/api/export")
def export_markdown(payload: ExportRequest) -> dict:
    return export_selected_markdown(payload.mark_shared)


@app.post("/api/ai/enrich")
def enrich_article(payload: EnrichRequest) -> dict:
    article = get_article(payload.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    try:
        result = enrich_article_with_ai(
            article,
            payload.ai.dict(),
            payload.translation.dict() if payload.translation else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI enrich failed: {exc}") from exc
    updated = update_ai_content(
        payload.article_id,
        result["translated_title"],
        result["translated_summary"],
        result["ai_recommendation"],
    )
    return {"ok": True, "article": updated}


@app.post("/api/ai/enrich-batch")
def enrich_batch(payload: EnrichBatchRequest) -> dict:
    if payload.status and payload.status != "all" and payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    articles = list_articles_needing_ai(
        payload.status,
        payload.limit,
        require_title=True,
        require_summary=True,
        require_recommendation=has_ai_config(payload.ai),
    )
    stats = {"total": len(articles), "processed": 0, "failed": 0, "skipped": 0}
    failures = []
    for article in articles:
        try:
            result = enrich_article_with_ai(
                article,
                payload.ai.dict(),
                payload.translation.dict() if payload.translation else None,
            )
            update_ai_content(
                article["id"],
                result["translated_title"],
                result["translated_summary"],
                result["ai_recommendation"],
            )
            stats["processed"] += 1
        except Exception as exc:
            stats["failed"] += 1
            failures.append({"id": article["id"], "title": article["title"], "error": str(exc)})
    return {"ok": stats["failed"] == 0, "stats": stats, "failures": failures}


@app.get("/api/logs")
def logs() -> list[dict]:
    return list_logs()


@app.get("/api/config")
def get_config() -> dict:
    return load_config()


@app.put("/api/config")
def put_config(config: dict) -> dict:
    save_config(config)
    return {"ok": True, "config": load_config()}
