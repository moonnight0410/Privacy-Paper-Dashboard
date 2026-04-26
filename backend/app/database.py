from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .collector import Candidate, canonical_url, is_near_duplicate, normalize_title, relevant, score_candidate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "privacy_papers.sqlite3"
VALID_STATUSES = {"candidate", "reading", "selected", "shared", "rejected"}


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


def row_to_article(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["reasons"] = json.loads(data.pop("reasons_json") or "[]")
    return data


def all_seen(conn: sqlite3.Connection) -> tuple[set[str], set[str]]:
    title_rows = conn.execute(
        """
        SELECT title_norm, url_norm FROM shared_history
        UNION
        SELECT title_norm, url_norm FROM articles WHERE status = 'shared'
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


def save_candidates(candidates: Iterable[Candidate], config: dict, min_score: int, max_age_days: int) -> dict:
    stats = {"inserted": 0, "updated": 0, "filtered": 0, "duplicates": 0}
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
                        summary = ?, authors = ?, score = ?, reasons_json = ?, updated_at = ?
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
                        now(),
                        existing["id"],
                    ),
                )
                stats["updated"] += 1
                continue
            if (url_norm and url_norm in current_urls) or is_near_duplicate(title_norm, current_titles):
                stats["duplicates"] += 1
                continue
            conn.execute(
                """
                INSERT INTO articles
                (title, title_norm, url, url_norm, source, source_type, published, summary,
                 authors, score, reasons_json, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', ?, ?)
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
                    now(),
                    now(),
                ),
            )
            stats["inserted"] += 1
            current_titles.add(title_norm)
            if url_norm:
                current_urls.add(url_norm)
    return stats


def list_articles(status: str | None = None, query: str | None = None) -> list[dict]:
    clauses = []
    params: list[str] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if query:
        clauses.append("(title LIKE ? OR summary LIKE ? OR source LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    with connect() as conn:
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


def create_log(source_counts: dict, failures: list[str], candidates_total: int, stats: dict, status: str, message: str) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO run_logs
            (started_at, finished_at, status, source_counts_json, failures_json, candidates_total,
             inserted_count, updated_count, filtered_count, duplicate_count, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        row = conn.execute("SELECT * FROM run_logs WHERE id = ?", (cur.lastrowid,)).fetchone()
        return log_row_to_dict(row)


def log_row_to_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["source_counts"] = json.loads(data.pop("source_counts_json") or "{}")
    data["failures"] = json.loads(data.pop("failures_json") or "[]")
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

