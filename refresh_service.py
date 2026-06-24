"""
refresh_service.py

Refresh orchestration for the Agricultural Market Intelligence Dashboard.

Global-only version optimized for Streamlit Community Cloud:
- default refresh is fast, RSS-only, concurrent, and source-limited
- full refresh is still available for manual/admin use
- HTML/report-page sources are excluded by default because they are slow and need custom parsers
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from collectors import collect_sources
from database import (
    finish_refresh_log,
    init_db,
    save_articles,
    start_refresh_log,
    update_last_refresh,
    update_source_health,
    utc_now_iso,
)
from source_registry import (
    DEFAULT_FAST_REFRESH_SOURCE_LIMIT,
    GLOBAL_FULL_MODE,
    get_fast_rss_sources,
    get_refreshable_sources,
    summarize_sources,
)

logger = logging.getLogger(__name__)


def _run_refresh(
    sources,
    max_workers: int = 8,
) -> Dict[str, object]:
    """Shared refresh implementation."""
    init_db()

    log_id = start_refresh_log(mode=GLOBAL_FULL_MODE, total_sources=len(sources))

    articles_collected = 0
    articles_saved = 0
    failed_sources = 0
    successful_sources = 0
    status = "success"
    message = ""
    source_health = []

    try:
        articles, source_health = collect_sources(
            sources=sources,
            deduplicate=True,
            sleep_seconds_between_sources=0.0,
            max_workers=max_workers,
        )
        articles_collected = len(articles)
        articles_saved = save_articles(articles)

        for record in source_health:
            record_status = str(record.get("status", "unknown"))
            if record_status == "failed":
                failed_sources += 1
            else:
                successful_sources += 1
            update_source_health(
                source_name=str(record.get("source_name", "Unknown Source")),
                status=record_status,
                articles_collected=int(record.get("article_count", 0) or 0),
                error_message=str(record.get("error_message", "") or ""),
            )

        if articles_saved > 0:
            update_last_refresh(utc_now_iso())

        if failed_sources and successful_sources:
            status = "partial_success"
            message = f"{failed_sources} sources failed; {successful_sources} sources completed."
        elif failed_sources and not successful_sources:
            status = "failed"
            message = "All sources failed. Check VPN/network and source_health."
        else:
            status = "success"
            message = "Refresh completed."

        if articles_collected == 0 and status != "failed":
            status = "empty"
            message = "Refresh ran successfully, but no articles were collected. Check source access or feed URLs."

    except Exception as exc:
        logger.exception("Refresh failed")
        status = "failed"
        message = str(exc)

    finish_refresh_log(
        log_id=log_id,
        successful_sources=successful_sources,
        failed_sources=failed_sources,
        articles_collected=articles_collected,
        articles_saved=articles_saved,
        status=status,
        message=message,
    )

    return {
        "mode": GLOBAL_FULL_MODE,
        "status": status,
        "message": message,
        "total_sources": len(sources),
        "successful_sources": successful_sources,
        "failed_sources": failed_sources,
        "articles_collected": articles_collected,
        "articles_saved": articles_saved,
        "source_health": source_health,
        "source_summary": summarize_sources(),
    }


def refresh_all_sources(
    mode: Optional[str] = None,
    include_non_rss: bool = False,
    include_custom_parser_sources: bool = False,
    max_sources: Optional[int] = DEFAULT_FAST_REFRESH_SOURCE_LIMIT,
    max_workers: int = 8,
    full_refresh: bool = False,
) -> Dict[str, object]:
    """
    Collect and store articles from the global source universe.

    Default behavior is intentionally fast for interactive app use:
    - RSS-only
    - 24 highest-priority feeds
    - short per-source timeout
    - concurrent fetches

    Set full_refresh=True from an admin/deep-refresh button to attempt all RSS
    MVP sources. HTML/report-page sources are still excluded unless explicitly
    requested because generic HTML parsing is slow/noisy on Community Cloud.
    """
    if full_refresh:
        sources = get_refreshable_sources(
            include_non_rss=include_non_rss,
            include_custom_parser_sources=include_custom_parser_sources,
            max_sources=None,
        )
    else:
        sources = get_fast_rss_sources(max_sources=max_sources or DEFAULT_FAST_REFRESH_SOURCE_LIMIT)

    return _run_refresh(sources=sources, max_workers=max_workers)


def refresh_starter_sources() -> Dict[str, object]:
    """Small startup seed refresh for an empty deployed app."""
    sources = get_fast_rss_sources(max_sources=12)
    return _run_refresh(sources=sources, max_workers=6)
