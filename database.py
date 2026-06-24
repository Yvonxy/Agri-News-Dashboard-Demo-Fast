"""
database.py

SQLite persistence layer for the Agricultural Market Intelligence Dashboard.

This version focuses on robust UI behavior:
- exact JSON-tag filtering instead of loose LIKE %tag% matching
- safe page clamping after filters change
- stable favorite toggling
- refresh metadata, refresh logs, and source health tracking
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ============================================================
# Database Path
# ============================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "news.db"


# ============================================================
# Utility Helpers
# ============================================================


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dumps(value: Any) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        value = [value]
    if isinstance(value, (list, tuple, set)):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return json.dumps(cleaned, ensure_ascii=False)
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return "[]"


def json_loads(value: Optional[str]) -> List[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return []
    if isinstance(parsed, list):
        return [str(x) for x in parsed if str(x).strip()]
    if isinstance(parsed, str):
        return [parsed]
    return []


def clean_filter_values(values: Optional[Iterable[Any]]) -> List[str]:
    if not values:
        return []
    output: List[str] = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def article_to_dict(article: Any) -> Dict[str, Any]:
    if isinstance(article, dict):
        return article
    return {
        "article_id": getattr(article, "article_id", ""),
        "title": getattr(article, "title", ""),
        "publish_date": getattr(article, "publish_date", ""),
        "source": getattr(article, "source", ""),
        "abstract": getattr(article, "abstract", ""),
        "url": getattr(article, "url", ""),
        "commodity_tags": getattr(article, "commodity_tags", []),
        "region_tags": getattr(article, "region_tags", []),
        "topic_tags": getattr(article, "topic_tags", []),
        "macro_or_fundamental": getattr(article, "macro_or_fundamental", "Unclassified"),
        "importance_score": getattr(article, "importance_score", 0),
        "impact_level": getattr(article, "impact_level", "Normal"),
        "source_priority": getattr(article, "source_priority", 0),
        "collected_timestamp": getattr(article, "collected_timestamp", utc_now_iso()),
    }


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    item = dict(row)
    item["commodity_tags"] = json_loads(item.get("commodity_tags"))
    item["region_tags"] = json_loads(item.get("region_tags"))
    item["topic_tags"] = json_loads(item.get("topic_tags"))
    item["is_favorite"] = bool(item.get("is_favorite", 0))
    return item


# ============================================================
# Connection / Initialization
# ============================================================


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS news (
            article_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            publish_date TEXT,
            source TEXT,
            abstract TEXT,
            url TEXT,
            commodity_tags TEXT,
            region_tags TEXT,
            topic_tags TEXT,
            macro_or_fundamental TEXT,
            importance_score REAL DEFAULT 0,
            impact_level TEXT DEFAULT 'Normal',
            source_priority INTEGER DEFAULT 0,
            collected_timestamp TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            article_id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(article_id) REFERENCES news(article_id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            refresh_started_at TEXT,
            refresh_finished_at TEXT,
            mode TEXT,
            total_sources INTEGER DEFAULT 0,
            successful_sources INTEGER DEFAULT 0,
            failed_sources INTEGER DEFAULT 0,
            articles_collected INTEGER DEFAULT 0,
            articles_saved INTEGER DEFAULT 0,
            status TEXT,
            message TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS source_health (
            source_name TEXT PRIMARY KEY,
            last_attempt_at TEXT,
            last_success_at TEXT,
            last_error_at TEXT,
            status TEXT,
            articles_collected INTEGER DEFAULT 0,
            error_message TEXT
        )
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_publish_date ON news(publish_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_collected_timestamp ON news(collected_timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_source ON news(source)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_importance ON news(importance_score)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_impact_level ON news(impact_level)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_news_macro_fundamental ON news(macro_or_fundamental)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_favorites_article_id ON favorites(article_id)")

    conn.commit()
    conn.close()


# ============================================================
# Metadata
# ============================================================


def get_metadata(key: str) -> Optional[str]:
    conn = get_connection()
    row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_metadata(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO metadata (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (key, value, utc_now_iso()),
    )
    conn.commit()
    conn.close()


def get_last_refresh() -> Optional[str]:
    return get_metadata("last_successful_refresh")


def update_last_refresh(timestamp: Optional[str] = None) -> None:
    set_metadata("last_successful_refresh", timestamp or utc_now_iso())


def should_auto_refresh(hours: int = 24) -> bool:
    last_refresh = get_last_refresh()
    if not last_refresh:
        return True
    try:
        last_dt = datetime.fromisoformat(str(last_refresh).replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_dt > timedelta(hours=hours)
    except Exception:
        return True


# ============================================================
# Save Articles
# ============================================================


def save_article(article: Any) -> bool:
    data = article_to_dict(article)
    article_id = str(data.get("article_id", "")).strip()
    title = str(data.get("title", "")).strip()
    if not article_id or not title:
        return False

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO news (
                article_id,
                title,
                publish_date,
                source,
                abstract,
                url,
                commodity_tags,
                region_tags,
                topic_tags,
                macro_or_fundamental,
                importance_score,
                impact_level,
                source_priority,
                collected_timestamp,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(article_id) DO UPDATE SET
                title = excluded.title,
                publish_date = excluded.publish_date,
                source = excluded.source,
                abstract = excluded.abstract,
                url = excluded.url,
                commodity_tags = excluded.commodity_tags,
                region_tags = excluded.region_tags,
                topic_tags = excluded.topic_tags,
                macro_or_fundamental = excluded.macro_or_fundamental,
                importance_score = excluded.importance_score,
                impact_level = excluded.impact_level,
                source_priority = excluded.source_priority,
                collected_timestamp = excluded.collected_timestamp,
                updated_at = excluded.updated_at
            """,
            (
                article_id,
                title,
                str(data.get("publish_date", "") or ""),
                str(data.get("source", "") or ""),
                str(data.get("abstract", "") or ""),
                str(data.get("url", "") or ""),
                json_dumps(data.get("commodity_tags", [])),
                json_dumps(data.get("region_tags", [])),
                json_dumps(data.get("topic_tags", [])),
                str(data.get("macro_or_fundamental", "Unclassified") or "Unclassified"),
                float(data.get("importance_score", 0) or 0),
                str(data.get("impact_level", "Normal") or "Normal"),
                int(data.get("source_priority", 0) or 0),
                str(data.get("collected_timestamp", "") or utc_now_iso()),
                utc_now_iso(),
            ),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def save_articles(articles: Iterable[Any]) -> int:
    return sum(1 for article in articles if save_article(article))


# ============================================================
# Favorites
# ============================================================


def add_favorite(article_id: str) -> bool:
    article_id = str(article_id or "").strip()
    if not article_id:
        return False
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (article_id, created_at) VALUES (?, ?)",
            (article_id, utc_now_iso()),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def remove_favorite(article_id: str) -> bool:
    article_id = str(article_id or "").strip()
    if not article_id:
        return False
    conn = get_connection()
    try:
        conn.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def toggle_favorite(article_id: str) -> bool:
    """Toggle favorite status. Return True when now favorite, False otherwise."""
    article_id = str(article_id or "").strip()
    if not article_id:
        return False
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT article_id FROM favorites WHERE article_id = ?",
            (article_id,),
        ).fetchone()
        if row:
            conn.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,))
            conn.commit()
            return False
        conn.execute(
            "INSERT INTO favorites (article_id, created_at) VALUES (?, ?)",
            (article_id, utc_now_iso()),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def is_favorite(article_id: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT article_id FROM favorites WHERE article_id = ?",
        (str(article_id or ""),),
    ).fetchone()
    conn.close()
    return row is not None


# ============================================================
# Query Builder
# ============================================================


def _date_expr(alias: str = "n") -> str:
    prefix = f"{alias}." if alias else ""
    return (
        f"COALESCE("
        f"datetime(NULLIF({prefix}publish_date, '')), "
        f"datetime(NULLIF({prefix}collected_timestamp, '')), "
        f"datetime({prefix}created_at)"
        f")"
    )


def _date_window_clause(date_window: str, alias: str = "n") -> str:
    value = str(date_window or "30D").strip()
    date_expr = _date_expr(alias)
    if value == "Today":
        return f"date({date_expr}) = date('now')"
    if value == "7D":
        return f"{date_expr} >= datetime('now', '-7 days')"
    if value == "30D":
        return f"{date_expr} >= datetime('now', '-30 days')"
    return ""


def _json_tag_clause(column_sql: str, values: Optional[Iterable[Any]]) -> Tuple[str, List[Any]]:
    """Return an exact JSON-string tag membership clause using LIKE on quoted values."""
    cleaned = clean_filter_values(values)
    if not cleaned:
        return "", []
    parts: List[str] = []
    params: List[Any] = []
    for value in cleaned:
        # Stored tags are json.dumps(list[str]), so exact tag membership appears as "Tag".
        quoted = json.dumps(value, ensure_ascii=False)
        parts.append(f"COALESCE({column_sql}, '[]') LIKE ?")
        params.append(f"%{quoted}%")
    return "(" + " OR ".join(parts) + ")", params


def _in_clause(column_sql: str, values: Optional[Iterable[Any]]) -> Tuple[str, List[Any]]:
    cleaned = clean_filter_values(values)
    if not cleaned:
        return "", []
    placeholders = ",".join(["?"] * len(cleaned))
    return f"{column_sql} IN ({placeholders})", cleaned


def build_where_clause(
    date_window: str = "30D",
    commodity_filter: Optional[List[str]] = None,
    region_filter: Optional[List[str]] = None,
    topic_filter: Optional[List[str]] = None,
    impact_filter: Optional[List[str]] = None,
    macro_filter: Optional[List[str]] = None,
    source_filter: Optional[List[str]] = None,
    favorites_only: bool = False,
) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    date_clause = _date_window_clause(date_window, alias="n")
    if date_clause:
        clauses.append(date_clause)

    for column, values in [
        ("n.commodity_tags", commodity_filter),
        ("n.region_tags", region_filter),
        ("n.topic_tags", topic_filter),
    ]:
        clause, clause_params = _json_tag_clause(column, values)
        if clause:
            clauses.append(clause)
            params.extend(clause_params)

    for column, values in [
        ("n.impact_level", impact_filter),
        ("n.macro_or_fundamental", macro_filter),
        ("n.source", source_filter),
    ]:
        clause, clause_params = _in_clause(column, values)
        if clause:
            clauses.append(clause)
            params.extend(clause_params)

    if favorites_only:
        clauses.append("f.article_id IS NOT NULL")

    if not clauses:
        return "", params
    return " WHERE " + " AND ".join(clauses), params


def build_news_query(
    date_window: str = "30D",
    commodity_filter: Optional[List[str]] = None,
    region_filter: Optional[List[str]] = None,
    topic_filter: Optional[List[str]] = None,
    impact_filter: Optional[List[str]] = None,
    macro_filter: Optional[List[str]] = None,
    source_filter: Optional[List[str]] = None,
    favorites_only: bool = False,
    sort_by: str = "Most Important",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[str, List[Any], str, List[Any]]:
    where_sql, params = build_where_clause(
        date_window=date_window,
        commodity_filter=commodity_filter,
        region_filter=region_filter,
        topic_filter=topic_filter,
        impact_filter=impact_filter,
        macro_filter=macro_filter,
        source_filter=source_filter,
        favorites_only=favorites_only,
    )

    date_expr = _date_expr("n")
    order_sql = (
        f"ORDER BY {date_expr} DESC, n.importance_score DESC"
        if sort_by == "Most Recent"
        else f"ORDER BY n.importance_score DESC, {date_expr} DESC"
    )

    page = max(int(page or 1), 1)
    page_size = max(int(page_size or 20), 1)
    offset = (page - 1) * page_size

    query_sql = f"""
        SELECT
            n.*,
            CASE WHEN f.article_id IS NULL THEN 0 ELSE 1 END AS is_favorite
        FROM news n
        LEFT JOIN favorites f ON n.article_id = f.article_id
        {where_sql}
        {order_sql}
        LIMIT ? OFFSET ?
    """
    query_params = list(params) + [page_size, offset]

    total_sql = f"""
        SELECT COUNT(*) AS total
        FROM news n
        LEFT JOIN favorites f ON n.article_id = f.article_id
        {where_sql}
    """
    return query_sql, query_params, total_sql, list(params)


def fetch_news(
    date_window: str = "30D",
    commodity_filter: Optional[List[str]] = None,
    region_filter: Optional[List[str]] = None,
    topic_filter: Optional[List[str]] = None,
    impact_filter: Optional[List[str]] = None,
    macro_filter: Optional[List[str]] = None,
    source_filter: Optional[List[str]] = None,
    favorites_only: bool = False,
    sort_by: str = "Most Important",
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    # First count with current filters, then clamp page so stale page state never returns false-empty results.
    where_sql, params = build_where_clause(
        date_window=date_window,
        commodity_filter=commodity_filter,
        region_filter=region_filter,
        topic_filter=topic_filter,
        impact_filter=impact_filter,
        macro_filter=macro_filter,
        source_filter=source_filter,
        favorites_only=favorites_only,
    )

    page_size = max(int(page_size or 20), 1)
    conn = get_connection()
    total_row = conn.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM news n
        LEFT JOIN favorites f ON n.article_id = f.article_id
        {where_sql}
        """,
        params,
    ).fetchone()
    total = int(total_row["total"] if total_row else 0)
    total_pages = max((total + page_size - 1) // page_size, 1)
    page = min(max(int(page or 1), 1), total_pages)

    query_sql, query_params, _, _ = build_news_query(
        date_window=date_window,
        commodity_filter=commodity_filter,
        region_filter=region_filter,
        topic_filter=topic_filter,
        impact_filter=impact_filter,
        macro_filter=macro_filter,
        source_filter=source_filter,
        favorites_only=favorites_only,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    rows = conn.execute(query_sql, query_params).fetchall()
    conn.close()

    return {
        "items": [row_to_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# ============================================================
# Summary Cards
# ============================================================


def get_summary_counts(date_window: str = "Today") -> Dict[str, int]:
    date_clause = _date_window_clause(date_window, alias="")
    where_sql = f"WHERE {date_clause}" if date_clause else ""
    date_expr = _date_expr("")

    sql = f"""
        SELECT
            SUM(CASE WHEN impact_level = 'Critical' THEN 1 ELSE 0 END) AS critical_count,
            SUM(CASE WHEN impact_level = 'High Impact' THEN 1 ELSE 0 END) AS high_impact_count,
            SUM(CASE WHEN impact_level IN ('Critical', 'High Impact') AND macro_or_fundamental = 'Macro' THEN 1 ELSE 0 END) AS macro_alert_count,
            SUM(CASE WHEN impact_level IN ('Critical', 'High Impact') AND macro_or_fundamental = 'Fundamental' THEN 1 ELSE 0 END) AS fundamental_alert_count,
            COUNT(*) AS total_count,
            MAX({date_expr}) AS latest_article_time
        FROM news
        {where_sql}
    """
    conn = get_connection()
    row = conn.execute(sql).fetchone()
    conn.close()

    if not row:
        return {
            "critical_count": 0,
            "high_impact_count": 0,
            "macro_alert_count": 0,
            "fundamental_alert_count": 0,
            "total_count": 0,
        }
    return {
        "critical_count": int(row["critical_count"] or 0),
        "high_impact_count": int(row["high_impact_count"] or 0),
        "macro_alert_count": int(row["macro_alert_count"] or 0),
        "fundamental_alert_count": int(row["fundamental_alert_count"] or 0),
        "total_count": int(row["total_count"] or 0),
    }


# ============================================================
# Source Health / Refresh Logs
# ============================================================


def update_source_health(
    source_name: str,
    status: str,
    articles_collected: int = 0,
    error_message: str = "",
) -> None:
    now = utc_now_iso()
    last_success_at = now if status == "success" else None
    last_error_at = now if status == "failed" else None
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO source_health (
            source_name,
            last_attempt_at,
            last_success_at,
            last_error_at,
            status,
            articles_collected,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_name) DO UPDATE SET
            last_attempt_at = excluded.last_attempt_at,
            last_success_at = COALESCE(excluded.last_success_at, source_health.last_success_at),
            last_error_at = COALESCE(excluded.last_error_at, source_health.last_error_at),
            status = excluded.status,
            articles_collected = excluded.articles_collected,
            error_message = excluded.error_message
        """,
        (source_name, now, last_success_at, last_error_at, status, int(articles_collected or 0), error_message or ""),
    )
    conn.commit()
    conn.close()


def get_source_health() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM source_health ORDER BY source_name ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def start_refresh_log(mode: str, total_sources: int) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO refresh_logs (refresh_started_at, mode, total_sources, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (utc_now_iso(), mode, int(total_sources or 0), "running", ""),
    )
    log_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return log_id


def finish_refresh_log(
    log_id: int,
    successful_sources: int,
    failed_sources: int,
    articles_collected: int,
    articles_saved: int,
    status: str = "success",
    message: str = "",
) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE refresh_logs
        SET refresh_finished_at = ?,
            successful_sources = ?,
            failed_sources = ?,
            articles_collected = ?,
            articles_saved = ?,
            status = ?,
            message = ?
        WHERE id = ?
        """,
        (
            utc_now_iso(),
            int(successful_sources or 0),
            int(failed_sources or 0),
            int(articles_collected or 0),
            int(articles_saved or 0),
            status,
            message or "",
            int(log_id),
        ),
    )
    conn.commit()
    conn.close()


def get_recent_refresh_logs(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM refresh_logs ORDER BY id DESC LIMIT ?",
        (int(limit or 10),),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============================================================
# Filter Options / Maintenance
# ============================================================


def get_distinct_sources() -> List[str]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT DISTINCT source
        FROM news
        WHERE source IS NOT NULL AND source != ''
        ORDER BY source ASC
        """
    ).fetchall()
    conn.close()
    return [str(row["source"]) for row in rows]


def get_all_articles_count() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS total FROM news").fetchone()
    conn.close()
    return int(row["total"] if row else 0)


def delete_old_news(days: int = 90) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        DELETE FROM news
        WHERE COALESCE(datetime(NULLIF(publish_date, '')), datetime(NULLIF(collected_timestamp, '')), datetime(created_at))
              < datetime('now', ?)
        """,
        (f"-{int(days or 90)} days",),
    )
    deleted = int(cur.rowcount or 0)
    conn.commit()
    conn.close()
    return deleted


def clear_all_news() -> None:
    conn = get_connection()
    conn.execute("DELETE FROM favorites")
    conn.execute("DELETE FROM news")
    conn.commit()
    conn.close()
