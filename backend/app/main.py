from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ai_client import enrich_article as enrich_article_with_ai
from .collector import (
    absorb_seen_text,
    candidate_from_url,
    collect_candidates,
    fetch_top_tier_openalex,
    load_config,
    relevant,
    save_config,
    score_candidate,
)
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
    upsert_imported_candidate,
    update_ai_content,
    update_status,
    now,
)


class FetchRequest(BaseModel):
    rows: int = Field(default=30, ge=1, le=100)
    days: int = Field(default=1095, ge=1, le=1095)
    min_score: int = Field(default=45, ge=-100, le=200)
    max_age_days: int = Field(default=1095, ge=0, le=1095)
    dry_run: bool = False


class TopTierFetchRequest(BaseModel):
    rows: int = Field(default=30, ge=1, le=100)
    days: int = Field(default=1095, ge=1, le=1095)
    min_score: int = Field(default=45, ge=-100, le=200)
    max_age_days: int = Field(default=1095, ge=0, le=1095)
    dry_run: bool = False


class StatusRequest(BaseModel):
    status: str


class ExportRequest(BaseModel):
    mark_shared: bool = False


class ImportUrlRequest(BaseModel):
    url: str
    status: str = "shared"


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
    translate: bool = True
    recommend: bool = True


class EnrichBatchRequest(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)
    translation: MachineTranslationConfig | None = None
    status: str | None = "candidate"
    limit: int = Field(default=100, ge=1, le=500)
    translate: bool = True
    recommend: bool = True
    latest_fetch_only: bool = False


def has_ai_config(config: AIConfig) -> bool:
    return bool(config.api_key.strip() and config.base_url.strip() and config.model.strip())


def enrich_action_type(translate: bool, recommend: bool) -> str:
    if translate and recommend:
        return "enrich"
    if translate:
        return "translate"
    return "ai"


def enrich_action_label(translate: bool, recommend: bool) -> str:
    if translate and recommend:
        return "\u7ffb\u8bd1\u4e0e AI \u89e3\u8bfb"
    if translate:
        return "\u7ffb\u8bd1"
    return "AI \u89e3\u8bfb"


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"


app = FastAPI(title="Privacy Paper Dashboard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_origin_regex=r"https?://.*",
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
    batch_token = now()
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
        message = f"dry-run\uff1a{relevant_count} \u6761\u5019\u9009\u901a\u8fc7\u57fa\u7840\u8fc7\u6ee4\uff0c\u672a\u5199\u5165\u6570\u636e\u5e93\u3002"
    else:
        stats = save_candidates(candidates, config, payload.min_score, payload.max_age_days, fetch_batch=batch_token)
        message = "\u6293\u53d6\u5b8c\u6210\uff0c\u5019\u9009\u5df2\u5199\u5165\u5de5\u4f5c\u53f0\u3002"
    log = create_log(
        source_counts=source_counts,
        failures=failures,
        candidates_total=len(candidates),
        stats=stats,
        status="partial" if failures else "success",
        message=message,
        batch_token=batch_token,
    )
    return {"candidates_total": len(candidates), "source_counts": source_counts, "failures": failures, "stats": stats, "log": log}


@app.post("/api/fetch/top-tier")
def fetch_top_tier(payload: TopTierFetchRequest) -> dict:
    config = load_config()
    batch_token = now()
    try:
        candidates, source_counts = fetch_top_tier_openalex(payload.rows, payload.days)
        failures: list[str] = []
    except Exception as exc:
        candidates = []
        source_counts = {}
        failures = [f"\u9876\u4f1a\u6293\u53d6\u5931\u8d25\uff1a{exc}"]
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
        message = f"dry-run\uff1a\u9876\u4f1a\u6293\u53d6\u5171 {relevant_count} \u6761\u5019\u9009\u901a\u8fc7\u57fa\u7840\u8fc7\u6ee4\uff0c\u672a\u5199\u5165\u6570\u636e\u5e93\u3002"
    else:
        stats = save_candidates(candidates, config, payload.min_score, payload.max_age_days, fetch_batch=batch_token)
        message = "\u9876\u4f1a\u6293\u53d6\u5b8c\u6210\uff0c\u5019\u9009\u5df2\u5199\u5165\u5de5\u4f5c\u53f0\u3002"
    log = create_log(
        source_counts=source_counts,
        failures=failures,
        candidates_total=len(candidates),
        stats=stats,
        status="partial" if failures else "success",
        message=message,
        batch_token=batch_token,
    )
    return {"candidates_total": len(candidates), "source_counts": source_counts, "failures": failures, "stats": stats, "log": log}


@app.get("/api/articles")
def articles(
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    today_only: bool = Query(default=False),
    latest_fetch_only: bool = Query(default=False),
) -> list[dict]:
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    return list_articles(status, q, today_only=today_only, latest_fetch_only=latest_fetch_only)


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


@app.post("/api/articles/import-url")
def import_article_url(payload: ImportUrlRequest) -> dict:
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    try:
        candidate = candidate_from_url(payload.url, load_config())
        article, created = upsert_imported_candidate(candidate, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"URL import failed: {exc}") from exc
    return {"ok": True, "created": created, "article": article}


@app.post("/api/export")
def export_markdown(payload: ExportRequest) -> dict:
    return export_selected_markdown(payload.mark_shared)


@app.post("/api/ai/enrich")
def enrich_article(payload: EnrichRequest) -> dict:
    article = get_article(payload.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if not payload.translate and not payload.recommend:
        raise HTTPException(status_code=400, detail="At least one of translate or recommend must be true")
    action_type = enrich_action_type(payload.translate, payload.recommend)
    action_label = enrich_action_label(payload.translate, payload.recommend)
    try:
        result = enrich_article_with_ai(
            article,
            payload.ai.dict(),
            payload.translation.dict() if payload.translation else None,
            do_translation=payload.translate,
            do_recommendation=payload.recommend,
        )
    except Exception as exc:
        create_log(
            source_counts={"scope": "single", "article_id": payload.article_id, "latest_fetch_only": False},
            failures=[f"{article['title']}: {exc}"],
            candidates_total=1,
            stats={"inserted": 0, "updated": 0, "filtered": 0, "duplicates": 1},
            status="failed",
            message=f"{action_label}\u5931\u8d25\uff1a{article['title']}",
            action_type=action_type,
        )
        raise HTTPException(status_code=502, detail=f"AI enrich failed: {exc}") from exc
    updated = update_ai_content(
        payload.article_id,
        result["translated_title"],
        result["translated_summary"],
        result["ai_recommendation"],
    )
    create_log(
        source_counts={"scope": "single", "article_id": payload.article_id, "latest_fetch_only": False},
        failures=[],
        candidates_total=1,
        stats={"inserted": 0, "updated": 1 if updated else 0, "filtered": 0, "duplicates": 0},
        status="success",
        message=f"{action_label}\u5b8c\u6210\uff1a{article['title']}",
        action_type=action_type,
    )
    return {"ok": True, "article": updated}


@app.post("/api/ai/enrich-batch")
def enrich_batch(payload: EnrichBatchRequest) -> dict:
    if payload.status and payload.status != "all" and payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if not payload.translate and not payload.recommend:
        raise HTTPException(status_code=400, detail="At least one of translate or recommend must be true")
    action_type = enrich_action_type(payload.translate, payload.recommend)
    action_label = enrich_action_label(payload.translate, payload.recommend)
    articles = list_articles_needing_ai(
        payload.status,
        payload.limit,
        require_title=payload.translate,
        require_summary=payload.translate,
        require_recommendation=payload.recommend,
        latest_fetch_only=payload.latest_fetch_only,
    )
    stats = {"total": len(articles), "processed": 0, "failed": 0, "skipped": 0}
    failures = []
    failure_messages: list[str] = []
    for article in articles:
        try:
            result = enrich_article_with_ai(
                article,
                payload.ai.dict(),
                payload.translation.dict() if payload.translation else None,
                do_translation=payload.translate,
                do_recommendation=payload.recommend,
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
            failure_messages.append(f"{article['title']}: {exc}")
    scope = payload.status or "all"
    if stats["total"] == 0:
        message = f"{action_label}\u5b8c\u6210\uff1a\u5f53\u524d\u8303\u56f4\u5185\u6ca1\u6709\u9700\u8981\u5904\u7406\u7684\u8bba\u6587\u3002"
        log_status = "success"
    elif stats["failed"] == 0:
        message = f"{action_label}\u5b8c\u6210\uff1a\u6210\u529f\u5904\u7406 {stats['processed']} \u6761\u3002"
        log_status = "success"
    elif stats["processed"] == 0:
        message = f"{action_label}\u5931\u8d25\uff1a{stats['failed']} \u6761\u5168\u90e8\u5904\u7406\u5931\u8d25\u3002"
        log_status = "failed"
    else:
        message = f"{action_label}\u90e8\u5206\u5b8c\u6210\uff1a\u6210\u529f {stats['processed']} \u6761\uff0c\u5931\u8d25 {stats['failed']} \u6761\u3002"
        log_status = "partial"
    create_log(
        source_counts={"scope": scope, "latest_fetch_only": payload.latest_fetch_only},
        failures=failure_messages,
        candidates_total=stats["total"],
        stats={
            "inserted": 0,
            "updated": stats["processed"],
            "filtered": stats["skipped"],
            "duplicates": stats["failed"],
        },
        status=log_status,
        message=message,
        action_type=action_type,
    )
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


if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="frontend-assets")


if FRONTEND_DIST.exists():
    @app.get("/")
    def frontend_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")
