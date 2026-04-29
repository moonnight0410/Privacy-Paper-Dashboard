from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .collector import Candidate, canonical_url, infer_import_source, is_near_duplicate, normalize_title, relevant, score_candidate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "privacy_papers.sqlite3"
VALID_STATUSES = {"candidate", "reading", "selected", "shared", "rejected"}
STATUS_PRIORITY = {
    "candidate": 0,
    "rejected": 1,
    "shared": 2,
    "reading": 3,
    "selected": 4,
}

MOJIBAKE_MARKERS = ("æ", "å", "ç", "é", "ï", "€", "鈥", "鍊", "寰", "鏉", "锛", "銆", "闅", "鐧")
LEGACY_TEXT_REPLACEMENTS = {
    "æ¥æºç±»åï¼š": "来源类型：",
    "鍙傝€冩潵婧愶細": "参考来源：",
    "é¡¶ä¼šç¬¬ä¸€æ¢¯éŸï¼š": "顶会第一梯队：",
    "Manual URL import": "手动链接导入",
    "dry-run锛": "dry-run：",
    "鎶撳彇瀹屾垚锛屽€欓€夊凡鍐欏叆宸ヤ綔鍙般€": "抓取完成，候选已写入工作台。",
    "dry-run top-tier only:": "dry-run：顶会抓取",
    "relevant candidates": "条候选通过基础过滤，未写入数据库。",
    "top-tier-only fetch completed": "顶会抓取完成，候选已写入工作台。",
    "manual top-tier-only fetch via reference sources": "通过参考源手动执行顶会抓取",
    "Top tier fetch failed:": "顶会抓取失败：",
}


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                title_norm TEXT NOT NULL,
                url TEXT NOT NULL,
                url_norm TEXT NOT NULL,
                source TEXT,
                source_type TEXT,
                published TEXT,
                summary TEXT,
                authors TEXT,
                score INTEGER DEFAULT 0,
                reasons_json TEXT DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'candidate',
                fetch_batch TEXT DEFAULT '',
                last_fetch_at TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                shared_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
            CREATE INDEX IF NOT EXISTS idx_articles_title_norm ON articles(title_norm);
            CREATE INDEX IF NOT EXISTS idx_articles_url_norm ON articles(url_norm);

            CREATE TABLE IF NOT EXISTS shared_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                title_norm TEXT,
                url TEXT,
                url_norm TEXT,
                source TEXT,
                added_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_shared_title_norm ON shared_history(title_norm);
            CREATE INDEX IF NOT EXISTS idx_shared_url_norm ON shared_history(url_norm);

            CREATE TABLE IF NOT EXISTS run_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                source_counts_json TEXT DEFAULT '{}',
                failures_json TEXT DEFAULT '[]',
                candidates_total INTEGER DEFAULT 0,
                inserted_count INTEGER DEFAULT 0,
                updated_count INTEGER DEFAULT 0,
                filtered_count INTEGER DEFAULT 0,
                duplicate_count INTEGER DEFAULT 0,
                message TEXT
            );
            """
        )
        ensure_article_columns(conn)
        ensure_run_log_columns(conn)
        normalize_stored_urls(conn)
        normalize_imported_sources(conn)
        collapse_all_duplicate_urls(conn)


def ensure_article_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(articles)").fetchall()}
    if "translated_title" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN translated_title TEXT DEFAULT ''")
    if "translated_summary" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN translated_summary TEXT DEFAULT ''")
    if "ai_recommendation" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN ai_recommendation TEXT DEFAULT ''")
    if "fetch_batch" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN fetch_batch TEXT DEFAULT ''")
        conn.execute("UPDATE articles SET fetch_batch = created_at WHERE fetch_batch = '' OR fetch_batch IS NULL")
    if "last_fetch_at" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN last_fetch_at TEXT DEFAULT ''")
        conn.execute(
            """
            UPDATE articles
            SET last_fetch_at = CASE
                WHEN fetch_batch IS NOT NULL AND fetch_batch != '' THEN fetch_batch
                ELSE created_at
            END
            WHERE last_fetch_at = '' OR last_fetch_at IS NULL
            """
        )


def ensure_run_log_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(run_logs)").fetchall()}
    if "action_type" not in columns:
        conn.execute("ALTER TABLE run_logs ADD COLUMN action_type TEXT DEFAULT 'fetch'")
    if "batch_token" not in columns:
        conn.execute("ALTER TABLE run_logs ADD COLUMN batch_token TEXT DEFAULT ''")


def text_quality(value: str) -> tuple[int, int, int]:
    cjk = sum(1 for char in value if "\u4e00" <= char <= "\u9fff")
    bad = sum(value.count(marker) for marker in MOJIBAKE_MARKERS)
    return (cjk, -bad, len(value))


def normalize_legacy_text(value: str | None) -> str:
    text = str(value or "")
    if not text:
        return ""
    for bad, good in LEGACY_TEXT_REPLACEMENTS.items():
        text = text.replace(bad, good)
    if not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text
    candidates = [text]
    try:
        candidates.append(text.encode("latin1").decode("utf-8"))
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    try:
        candidates.append(text.encode("gbk").decode("utf-8"))
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    normalized = max(candidates, key=text_quality)
    for bad, good in LEGACY_TEXT_REPLACEMENTS.items():
        normalized = normalized.replace(bad, good)
    return normalized


def normalize_stored_urls(conn: sqlite3.Connection) -> None:
    article_rows = conn.execute("SELECT id, url FROM articles").fetchall()
    for row in article_rows:
        conn.execute("UPDATE articles SET url_norm = ? WHERE id = ?", (canonical_url(row["url"]), row["id"]))
    history_rows = conn.execute("SELECT id, url FROM shared_history").fetchall()
    for row in history_rows:
        conn.execute("UPDATE shared_history SET url_norm = ? WHERE id = ?", (canonical_url(row["url"]), row["id"]))


def normalize_imported_sources(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT id, source, source_type, url
        FROM articles
        WHERE source_type = 'imported'
        """
    ).fetchall()
    for row in rows:
        host = ""
        if row["url"]:
            host = row["url"].split("/")[2].lower() if "://" in row["url"] else row["url"].lower()
        source, source_type = infer_import_source(host or (row["source"] or "").lower(), {}, "")
        conn.execute(
            "UPDATE articles SET source = ?, source_type = ? WHERE id = ?",
            (source or row["source"], source_type, row["id"]),
        )


def row_to_article(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["reasons"] = [normalize_legacy_text(item) for item in json.loads(data.pop("reasons_json") or "[]")]
    for key in ("title", "source", "summary", "authors", "translated_title", "translated_summary"):
        if key in data:
            data[key] = normalize_legacy_text(data[key])
    recommendation = data.get("ai_recommendation") or "[]"
    try:
        data["ai_recommendation"] = [normalize_legacy_text(item) for item in json.loads(recommendation)]
    except json.JSONDecodeError:
        data["ai_recommendation"] = [normalize_legacy_text(recommendation)] if recommendation else []
    return data


def status_rank(status: str | None) -> int:
    return STATUS_PRIORITY.get(status or "", -1)


def source_quality(source: str | None, source_type: str | None) -> tuple[int, int]:
    text = (source or "").strip()
    is_domain = bool(text) and "." in text and " " not in text
    return (
        1 if (source_type or "") and source_type != "search" else 0,
        0 if is_domain else 1,
    )


def parse_reason_list(raw: str | None) -> list[str]:
    try:
        values = json.loads(raw or "[]")
        if isinstance(values, list):
            return [normalize_legacy_text(str(item).strip()) for item in values if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return []


def parse_ai_list(raw: str | None) -> list[str]:
    try:
        values = json.loads(raw or "[]")
        if isinstance(values, list):
            return [normalize_legacy_text(str(item).strip()) for item in values if str(item).strip()]
    except json.JSONDecodeError:
        pass
    text = normalize_legacy_text((raw or "").strip())
    return [text] if text else []


def prefer_longer(*values: str | None) -> str:
    candidates = [str(value).strip() for value in values if str(value or "").strip()]
    if not candidates:
        return ""
    return max(candidates, key=lambda item: (len(item), item))


def merge_unique_text(*groups: list[str]) -> list[str]:
    results: list[str] = []
    seen = set()
    for group in groups:
        for value in group:
            text = str(value).strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            results.append(text)
    return results


def collapse_duplicate_rows(conn: sqlite3.Connection, preferred_id: int | None, url_norm: str) -> int:
    if not url_norm:
        return 0
    rows = conn.execute("SELECT * FROM articles WHERE url_norm = ? ORDER BY id", (url_norm,)).fetchall()
    if len(rows) <= 1:
        return 0
    keeper = next((row for row in rows if row["id"] == preferred_id), None)
    if keeper is None:
        keeper = max(
            rows,
            key=lambda row: (
                status_rank(row["status"]),
                row["score"] or 0,
                len((row["summary"] or "").strip()),
                len((row["authors"] or "").strip()),
                row["updated_at"] or "",
                row["id"],
            ),
        )
    others = [row for row in rows if row["id"] != keeper["id"]]
    source_row = max(
        rows,
        key=lambda row: (
            source_quality(row["source"], row["source_type"]),
            len((row["source"] or "").strip()),
            row["updated_at"] or "",
            row["id"],
        ),
    )
    merged_status = max((row["status"] for row in rows), key=status_rank)
    shared_at = max((row["shared_at"] or "" for row in rows), default="") or None
    merged_reasons = merge_unique_text(*[parse_reason_list(row["reasons_json"]) for row in rows])
    merged_ai = merge_unique_text(*[parse_ai_list(row["ai_recommendation"]) for row in rows])
    merged_title = keeper["title"] or prefer_longer(*[row["title"] for row in rows])
    merged_title_norm = normalize_title(merged_title)
    merged_summary = keeper["summary"] or prefer_longer(*[row["summary"] for row in rows])
    merged_authors = keeper["authors"] or prefer_longer(*[row["authors"] for row in rows])
    merged_published = keeper["published"] or prefer_longer(*[row["published"] for row in rows])
    merged_translated_title = keeper["translated_title"] or prefer_longer(*[row["translated_title"] for row in rows])
    merged_translated_summary = keeper["translated_summary"] or prefer_longer(*[row["translated_summary"] for row in rows])
    merged_fetch_batch = keeper["fetch_batch"] or prefer_longer(*[row["fetch_batch"] for row in rows])
    merged_score = max(int(row["score"] or 0) for row in rows)
    conn.execute(
        """
        UPDATE articles
        SET title = ?, title_norm = ?, source = ?, source_type = ?, published = ?, summary = ?, authors = ?,
            score = ?, reasons_json = ?, status = ?, fetch_batch = ?, shared_at = ?, translated_title = ?, translated_summary = ?,
            ai_recommendation = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            merged_title,
            merged_title_norm,
            source_row["source"],
            source_row["source_type"],
            merged_published,
            merged_summary,
            merged_authors,
            merged_score,
            json.dumps(merged_reasons, ensure_ascii=False),
            merged_status,
            merged_fetch_batch,
            shared_at,
            merged_translated_title,
            merged_translated_summary,
            json.dumps(merged_ai, ensure_ascii=False),
            now(),
            keeper["id"],
        ),
    )
    if merged_status == "shared":
        add_shared_row(conn, merged_title, keeper["url"], source_row["source"])
    delete_ids = [row["id"] for row in others]
    conn.executemany("DELETE FROM articles WHERE id = ?", [(row_id,) for row_id in delete_ids])
    return len(delete_ids)


def collapse_all_duplicate_urls(conn: sqlite3.Connection) -> int:
    duplicate_urls = conn.execute(
        """
        SELECT url_norm
        FROM articles
        WHERE url_norm != ''
        GROUP BY url_norm
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    removed = 0
    for row in duplicate_urls:
        removed += collapse_duplicate_rows(conn, None, row["url_norm"])
    return removed


def update_ai_content(article_id: int, translated_title: str, translated_summary: str, ai_recommendation: list[str]) -> dict | None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE articles
            SET translated_title = ?, translated_summary = ?, ai_recommendation = ?, updated_at = ?
            WHERE id = ?
            """,
            (translated_title, translated_summary, json.dumps(ai_recommendation, ensure_ascii=False), now(), article_id),
        )
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return row_to_article(row) if row else None


def list_articles_needing_ai(
    status: str | None = "candidate",
    limit: int = 100,
    require_title: bool = True,
    require_summary: bool = True,
    require_recommendation: bool = True,
    latest_fetch_only: bool = False,
) -> list[dict]:
    needs = []
    if require_title:
        needs.append("(translated_title IS NULL OR translated_title = '')")
    if require_summary:
        needs.append("(translated_summary IS NULL OR translated_summary = '')")
    if require_recommendation:
        needs.append("(ai_recommendation IS NULL OR ai_recommendation = '' OR ai_recommendation = '[]')")
    clauses = [f"({' OR '.join(needs)})"] if needs else ["1 = 1"]
    params: list[str | int] = []
    if status and status != "all":
        clauses.insert(0, "status = ?")
        params.append(status)
    with connect() as conn:
        if latest_fetch_only:
            batch_token = latest_fetch_batch_token(conn)
            if batch_token:
                clauses.insert(0, "fetch_batch = ?")
                params.insert(0, batch_token)
        params.append(limit)
        where = " AND ".join(clauses)
        rows = conn.execute(
            f"""
            SELECT * FROM articles
            WHERE {where}
            ORDER BY score DESC, published DESC, updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [row_to_article(row) for row in rows]


def all_seen(conn: sqlite3.Connection) -> tuple[set[str], set[str]]:
    title_rows = conn.execute(
        """
        SELECT title_norm, url_norm FROM shared_history
        UNION
        SELECT title_norm, url_norm FROM articles WHERE status = 'shared'
        UNION
        SELECT title_norm, url_norm FROM articles WHERE status = 'rejected'
        """
    ).fetchall()
    return {r["title_norm"] for r in title_rows if r["title_norm"]}, {r["url_norm"] for r in title_rows if r["url_norm"]}


def active_seen(conn: sqlite3.Connection) -> tuple[set[str], set[str]]:
    rows = conn.execute("SELECT title_norm, url_norm FROM articles WHERE status != 'shared'").fetchall()
    return {r["title_norm"] for r in rows if r["title_norm"]}, {r["url_norm"] for r in rows if r["url_norm"]}


def find_existing(conn: sqlite3.Connection, title_norm: str, url_norm: str) -> sqlite3.Row | None:
    if url_norm:
        row = conn.execute("SELECT * FROM articles WHERE url_norm = ? LIMIT 1", (url_norm,)).fetchone()
        if row:
            return row
    return conn.execute("SELECT * FROM articles WHERE title_norm = ? LIMIT 1", (title_norm,)).fetchone()


def save_candidates(
    candidates: Iterable[Candidate],
    config: dict,
    min_score: int,
    max_age_days: int,
    fetch_batch: str | None = None,
) -> dict:
    stats = {"inserted": 0, "updated": 0, "filtered": 0, "duplicates": 0}
    batch_token = fetch_batch or now()
    ranked: list[Candidate] = []
    for candidate in candidates:
        score_candidate(candidate, config)
        if relevant(candidate, config, min_score, max_age_days):
            ranked.append(candidate)
        else:
            stats["filtered"] += 1
    ranked.sort(key=lambda item: (item.score, item.published), reverse=True)

    with connect() as conn:
        shared_titles, shared_urls = all_seen(conn)
        current_titles, current_urls = active_seen(conn)
        for item in ranked:
            title_norm = normalize_title(item.title)
            url_norm = canonical_url(item.url)
            if (url_norm and url_norm in shared_urls) or is_near_duplicate(title_norm, shared_titles):
                stats["duplicates"] += 1
                continue
            existing = find_existing(conn, title_norm, url_norm)
            if existing:
                conn.execute(
                    """
                    UPDATE articles
                    SET title = ?, url = ?, source = ?, source_type = ?, published = ?,
                        summary = ?, authors = ?, score = ?, reasons_json = ?, last_fetch_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        item.title,
                        item.url,
                        item.source,
                        item.source_type,
                        item.published,
                        item.summary,
                        item.authors,
                        item.score,
                        json.dumps(item.reasons, ensure_ascii=False),
                        batch_token,
                        now(),
                        existing["id"],
                    ),
                )
                collapse_duplicate_rows(conn, existing["id"], url_norm)
                stats["updated"] += 1
                continue
            if (url_norm and url_norm in current_urls) or is_near_duplicate(title_norm, current_titles):
                stats["duplicates"] += 1
                continue
            cur = conn.execute(
                """
                INSERT INTO articles
                (title, title_norm, url, url_norm, source, source_type, published, summary,
                 authors, score, reasons_json, status, fetch_batch, last_fetch_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', ?, ?, ?, ?)
                """,
                (
                    item.title,
                    title_norm,
                    item.url,
                    url_norm,
                    item.source,
                    item.source_type,
                    item.published,
                    item.summary,
                    item.authors,
                    item.score,
                    json.dumps(item.reasons, ensure_ascii=False),
                    batch_token,
                    batch_token,
                    now(),
                    now(),
                ),
            )
            stats["inserted"] += 1
            collapse_duplicate_rows(conn, cur.lastrowid, url_norm)
            current_titles.add(title_norm)
            if url_norm:
                current_urls.add(url_norm)
    return stats


def upsert_imported_candidate(candidate: Candidate, status: str = "shared") -> tuple[dict, bool]:
    if status not in VALID_STATUSES:
        raise ValueError("Invalid status")
    title_norm = normalize_title(candidate.title)
    url_norm = canonical_url(candidate.url)
    if not title_norm:
        raise ValueError("Imported article must have a title")

    timestamp = now()
    with connect() as conn:
        existing = find_existing(conn, title_norm, url_norm)
        shared_at = timestamp if status == "shared" else None
        if existing:
            shared_at = timestamp if status == "shared" else existing["shared_at"]
            conn.execute(
                """
                UPDATE articles
                SET title = ?, title_norm = ?, url = ?, url_norm = ?, source = ?, source_type = ?,
                    published = ?, summary = ?, authors = ?, score = ?, reasons_json = ?,
                    status = ?, last_fetch_at = ?, shared_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    candidate.title,
                    title_norm,
                    candidate.url,
                    url_norm,
                    candidate.source,
                    candidate.source_type,
                    candidate.published,
                    candidate.summary,
                    candidate.authors,
                    candidate.score,
                    json.dumps(candidate.reasons, ensure_ascii=False),
                    status,
                    existing["last_fetch_at"] or timestamp,
                    shared_at,
                    timestamp,
                    existing["id"],
                ),
            )
            created = False
            article_id = existing["id"]
        else:
            cur = conn.execute(
                """
                INSERT INTO articles
                (title, title_norm, url, url_norm, source, source_type, published, summary,
                 authors, score, reasons_json, status, last_fetch_at, created_at, updated_at, shared_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.title,
                    title_norm,
                    candidate.url,
                    url_norm,
                    candidate.source,
                    candidate.source_type,
                    candidate.published,
                    candidate.summary,
                    candidate.authors,
                    candidate.score,
                    json.dumps(candidate.reasons, ensure_ascii=False),
                    status,
                    timestamp,
                    timestamp,
                    timestamp,
                    shared_at,
                ),
            )
            created = True
            article_id = cur.lastrowid
        if status == "shared":
            add_shared_row(conn, candidate.title, candidate.url, candidate.source)
        collapse_duplicate_rows(conn, article_id, url_norm)
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return row_to_article(row), created


def latest_fetch_batch_token(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT batch_token
        FROM run_logs
        WHERE action_type = 'fetch' AND batch_token != '' AND status IN ('success', 'partial')
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    return (row["batch_token"] or "").strip() if row else ""


def list_articles(
    status: str | None = None,
    query: str | None = None,
    today_only: bool = False,
    latest_fetch_only: bool = False,
) -> list[dict]:
    clauses = []
    params: list[str] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if query:
        clauses.append("(title LIKE ? OR translated_title LIKE ? OR summary LIKE ? OR source LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
    with connect() as conn:
        if latest_fetch_only or today_only:
            batch_token = latest_fetch_batch_token(conn)
            if batch_token:
                clauses.append("fetch_batch = ?")
                params.append(batch_token)
            else:
                clauses.append("created_at LIKE ?")
                params.append(f"{dt.date.today().isoformat()}%")
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM articles {where} ORDER BY score DESC, published DESC, updated_at DESC",
            params,
        ).fetchall()
        return [row_to_article(row) for row in rows]


def get_article(article_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return row_to_article(row) if row else None


def update_status(article_id: int, status: str) -> dict | None:
    if status not in VALID_STATUSES:
        raise ValueError("Invalid status")
    with connect() as conn:
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        if not row:
            return None
        shared_at = now() if status == "shared" else row["shared_at"]
        conn.execute(
            "UPDATE articles SET status = ?, shared_at = ?, updated_at = ? WHERE id = ?",
            (status, shared_at, now(), article_id),
        )
        if status == "shared":
            add_shared_row(conn, row["title"], row["url"], row["source"])
        collapse_duplicate_rows(conn, article_id, row["url_norm"])
        updated = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return row_to_article(updated)


def add_shared_row(conn: sqlite3.Connection, title: str, url: str, source: str) -> None:
    title_norm = normalize_title(title)
    url_norm = canonical_url(url)
    existing = conn.execute(
        "SELECT id FROM shared_history WHERE (url_norm != '' AND url_norm = ?) OR title_norm = ? LIMIT 1",
        (url_norm, title_norm),
    ).fetchone()
    if existing:
        return
    conn.execute(
        "INSERT INTO shared_history (title, title_norm, url, url_norm, source, added_at) VALUES (?, ?, ?, ?, ?, ?)",
        (title, title_norm, url, url_norm, source, now()),
    )


def add_seen_titles_urls(titles: Iterable[str], urls: Iterable[str], source: str) -> int:
    count = 0
    with connect() as conn:
        for title in titles:
            if not title:
                continue
            existing = conn.execute("SELECT id FROM shared_history WHERE title_norm = ? LIMIT 1", (title,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO shared_history (title, title_norm, url, url_norm, source, added_at) VALUES (?, ?, '', '', ?, ?)",
                    (title, title, source, now()),
                )
                count += 1
        for url in urls:
            if not url:
                continue
            existing = conn.execute("SELECT id FROM shared_history WHERE url_norm = ? LIMIT 1", (url,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO shared_history (title, title_norm, url, url_norm, source, added_at) VALUES ('', '', ?, ?, ?, ?)",
                    (url, url, source, now()),
                )
                count += 1
    return count


def create_log(
    source_counts: dict,
    failures: list[str],
    candidates_total: int,
    stats: dict,
    status: str,
    message: str,
    action_type: str = "fetch",
    batch_token: str = "",
) -> dict:
    with connect() as conn:
        ensure_run_log_columns(conn)
        cur = conn.execute(
            """
            INSERT INTO run_logs
            (started_at, finished_at, status, source_counts_json, failures_json, candidates_total,
             inserted_count, updated_count, filtered_count, duplicate_count, message, action_type, batch_token)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now(),
                now(),
                status,
                json.dumps(source_counts, ensure_ascii=False),
                json.dumps(failures, ensure_ascii=False),
                candidates_total,
                stats.get("inserted", 0),
                stats.get("updated", 0),
                stats.get("filtered", 0),
                stats.get("duplicates", 0),
                message,
                action_type,
                batch_token,
            ),
        )
        row = conn.execute("SELECT * FROM run_logs WHERE id = ?", (cur.lastrowid,)).fetchone()
        return log_row_to_dict(row)


def log_row_to_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["source_counts"] = json.loads(data.pop("source_counts_json") or "{}")
    data["failures"] = [normalize_legacy_text(item) for item in json.loads(data.pop("failures_json") or "[]")]
    data["message"] = normalize_legacy_text(data.get("message"))
    data["action_type"] = data.get("action_type") or "fetch"
    return data


def list_logs() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM run_logs ORDER BY id DESC LIMIT 80").fetchall()
        return [log_row_to_dict(row) for row in rows]


def export_selected_markdown(mark_shared: bool) -> dict:
    articles = list_articles("selected")
    today = dt.date.today().isoformat()
    lines = [
        f"# 数据安全与隐私保护入选文章（{today}）",
        "",
        "| 序号 | 标题 | 来源 | 日期 | 推荐理由 | 链接 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for idx, item in enumerate(articles, 1):
        reason = "；".join(item["reasons"][:3]) or f"综合评分 {item['score']}"
        title = item["title"].replace("|", "\\|")
        source = (item["source"] or "").replace("|", "\\|")
        lines.append(
            f"| {idx} | {title} | {source} | {item['published'] or '-'} | {reason.replace('|', '/')} | {item['url']} |"
        )
    lines.append("")
    markdown = "\n".join(lines)
    if mark_shared:
        for item in articles:
            update_status(item["id"], "shared")
    return {"filename": f"privacy-paper-selected-{today}.md", "markdown": markdown, "count": len(articles)}
