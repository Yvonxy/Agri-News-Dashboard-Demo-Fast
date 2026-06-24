"""
collectors.py

Collection engine for the Agricultural Market Intelligence Dashboard.

Main responsibilities:
1. Collect RSS feeds.
2. Provide placeholder/generic support for HTML and report page sources.
3. Classify articles.
4. Score articles.
5. Deduplicate articles by URL and title similarity.
6. Return unified article dictionaries ready for database insertion.

This file is designed to work with:
- source_registry.py
- classifier.py
- scoring.py
- database.py

The first runnable version should use RSS sources only.
HTML and report-page parsers are included as safe placeholders and generic parsers.
"""

import hashlib
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from classifier import clean_text
from classifier import classify_article
from scoring import score_article


try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None


try:
    from source_registry import (
        SOURCE_TYPE_RSS,
        SOURCE_TYPE_HTML,
        SOURCE_TYPE_REPORT_PAGE,
        PARSER_RSS,
        PARSER_GENERIC_HTML,
        PARSER_CONAB,
        PARSER_MPOB,
        PARSER_MPOC,
        PARSER_WASDE,
        PARSER_FAS_GAIN,
        PARSER_EIA,
        GLOBAL_FULL_MODE,
        get_mvp_rss_sources,
        get_tier_1_sources,
        get_refreshable_sources,
    )
except Exception:
    SOURCE_TYPE_RSS = "rss"
    SOURCE_TYPE_HTML = "html"
    SOURCE_TYPE_REPORT_PAGE = "report_page"
    PARSER_RSS = "rss_parser"
    PARSER_GENERIC_HTML = "generic_html_parser"
    PARSER_CONAB = "conab_parser"
    PARSER_MPOB = "mpob_parser"
    PARSER_MPOC = "mpoc_parser"
    PARSER_WASDE = "wasde_parser"
    PARSER_FAS_GAIN = "fas_gain_parser"
    PARSER_EIA = "eia_parser"
    GLOBAL_FULL_MODE = "global_full"
    get_mvp_rss_sources = None
    get_tier_1_sources = None
    get_refreshable_sources = None


# ============================================================
# Logging
# ============================================================

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# ============================================================
# HTTP Settings
# ============================================================

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36 "
        "AgriDashboardBot/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ============================================================
# Utility Functions
# ============================================================

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_url(url: str) -> str:
    if not url:
        return ""

    url = str(url).strip()

    # Remove common tracking fragments
    url = re.sub(r"#.*$", "", url)

    return url


def make_article_id(
    source_name: str,
    title: str,
    url: str,
    publish_date: str = "",
) -> str:
    """
    Generate stable article id.
    Prefer URL if available, otherwise use source/title/date.
    """

    raw = "|".join(
        [
            source_name or "",
            normalize_url(url or ""),
            clean_text(title or ""),
            publish_date or "",
        ]
    )

    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def parse_entry_date(entry) -> str:
    """
    Parse RSS entry date into ISO string when possible.
    """

    candidate_fields = [
        "published",
        "updated",
        "created",
        "pubDate",
    ]

    for field in candidate_fields:

        value = getattr(entry, field, None)

        if value:
            parsed = parse_date_to_iso(value)
            if parsed:
                return parsed

    # Try feedparser structured time
    for field in ["published_parsed", "updated_parsed"]:

        value = getattr(entry, field, None)

        if value:
            try:
                dt = datetime.fromtimestamp(
                    time.mktime(value),
                    tz=timezone.utc,
                )
                return dt.isoformat()
            except Exception:
                pass

    return ""


def parse_date_to_iso(value: object) -> str:
    """
    Parse date value into ISO string.
    """

    if not value:
        return ""

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()

        if not text:
            return ""

        dt = None

        try:
            dt = parsedate_to_datetime(text)
        except Exception:
            dt = None

        if dt is None and date_parser is not None:
            try:
                dt = date_parser.parse(text)
            except Exception:
                dt = None

        if dt is None:
            return text

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc).isoformat()


def safe_get(
    url: str,
    timeout: int = 10,
    headers: Dict[str, str] = None,
) -> requests.Response:
    """
    Safe HTTP GET wrapper.

    Streamlit Community Cloud should not wait 20+ seconds per slow feed.
    Use a short connect timeout plus a capped read timeout so failed sources
    degrade quickly instead of blocking the whole refresh.
    """

    headers = headers or DEFAULT_HEADERS

    try:
        timeout = int(timeout or 10)
    except Exception:
        timeout = 10

    timeout = max(3, min(timeout, 12))
    request_timeout = (min(4, timeout), timeout)

    response = requests.get(
        url,
        headers=headers,
        timeout=request_timeout,
    )

    response.raise_for_status()

    return response


def extract_entry_link(entry) -> str:
    """
    Extract best available link from RSS entry.
    """

    link = getattr(entry, "link", "")

    if link:
        return normalize_url(link)

    links = getattr(entry, "links", [])

    if links:
        for item in links:
            href = item.get("href")
            if href:
                return normalize_url(href)

    return ""


def title_similarity(title_a: str, title_b: str) -> float:
    """
    Basic title similarity score using SequenceMatcher.
    """

    a = clean_text(title_a or "").lower()
    b = clean_text(title_b or "").lower()

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def is_valid_article(article: Dict[str, object]) -> bool:
    """
    Basic validation before saving/displaying.
    """

    title = clean_text(article.get("title", ""))

    if len(title) < 5:
        return False

    url = article.get("url", "")

    if not url:
        return False

    return True


# ============================================================
# Article Normalization
# ============================================================

def build_article(
    source: Dict[str, object],
    title: str,
    url: str,
    publish_date: str = "",
    abstract: str = "",
) -> Dict[str, object]:
    """
    Build unified article dictionary, classify and score it.
    """

    source_name = source.get("source_name", "Unknown Source")

    title = clean_text(title)
    abstract = clean_text(abstract)
    url = normalize_url(url)
    publish_date = parse_date_to_iso(publish_date)

    article = {
        "article_id": make_article_id(
            source_name=source_name,
            title=title,
            url=url,
            publish_date=publish_date,
        ),
        "title": title,
        "publish_date": publish_date,
        "source": source_name,
        "abstract": abstract,
        "url": url,
        "commodity_tags": [],
        "region_tags": [],
        "topic_tags": [],
        "macro_or_fundamental": "Unclassified",
        "importance_score": 0,
        "impact_level": "Normal",
        "source_priority": int(source.get("priority_weight", 5)),
        "collected_timestamp": now_utc_iso(),
    }

    article = classify_article(article, source)
    article = score_article(article, source)

    return article


# ============================================================
# RSS Collector
# ============================================================

def collect_rss_source(source: Dict[str, object]) -> List[Dict[str, object]]:
    """
    Collect a single RSS source quickly and safely.

    Important changes for Streamlit Cloud:
    - no feedparser direct-URL fallback, because it has weaker timeout control
    - per-feed entry limit to avoid collecting hundreds of Google News items
    - short per-source timeout inherited from source_registry / refresh_service
    """

    source_name = source.get("source_name", "Unknown Source")
    url = source.get("base_url", "")
    timeout = int(source.get("timeout_seconds", 10) or 10)
    max_entries = int(source.get("max_entries", 25) or 25)

    articles: List[Dict[str, object]] = []

    if not url:
        logger.warning("RSS source has no base_url: %s", source_name)
        return articles

    try:
        response = safe_get(url=url, timeout=timeout)
        feed = feedparser.parse(response.content)
    except Exception as exc:
        logger.warning("RSS request failed for %s: %s", source_name, exc)
        return articles

    entries = list(getattr(feed, "entries", []) or [])

    for entry in entries[:max_entries]:
        try:
            title = getattr(entry, "title", "")
            abstract = getattr(entry, "summary", "") or getattr(entry, "description", "")
            link = extract_entry_link(entry)
            publish_date = parse_entry_date(entry)

            article = build_article(
                source=source,
                title=title,
                url=link,
                publish_date=publish_date,
                abstract=abstract,
            )

            if is_valid_article(article):
                articles.append(article)

        except Exception as exc:
            logger.warning("Failed to parse RSS entry from %s: %s", source_name, exc)

    logger.info("Collected %s articles from RSS source: %s", len(articles), source_name)
    return articles


# ============================================================
# Generic HTML Collector
# ============================================================

def collect_generic_html_source(source: Dict[str, object]) -> List[Dict[str, object]]:
    """
    Generic HTML parser.

    This is intentionally conservative.
    It extracts links that look like article/news links.
    Specific sources such as MPOB/CONAB/MPOC can later receive custom parsers.
    """

    source_name = source.get("source_name", "Unknown Source")
    base_url = source.get("base_url", "")
    timeout = int(source.get("timeout_seconds", 25))

    articles = []

    if not base_url:
        logger.warning("HTML source has no base_url: %s", source_name)
        return articles

    try:
        response = safe_get(
            url=base_url,
            timeout=timeout,
        )

        soup = BeautifulSoup(response.text, "html.parser")

    except Exception as exc:
        logger.error(
            "Failed to fetch HTML source %s: %s",
            source_name,
            exc,
        )
        return articles

    candidate_links = []

    for a in soup.find_all("a", href=True):

        title = clean_text(a.get_text(" ", strip=True))
        href = a.get("href", "")

        if not title or len(title) < 15:
            continue

        full_url = urljoin(base_url, href)

        href_lower = full_url.lower()
        text_lower = title.lower()

        looks_like_article = any(
            token in href_lower or token in text_lower
            for token in [
                "news",
                "press",
                "release",
                "article",
                "report",
                "market",
                "crop",
                "grain",
                "palm",
                "soy",
                "corn",
                "wheat",
            ]
        )

        if not looks_like_article:
            continue

        candidate_links.append(
            {
                "title": title,
                "url": full_url,
            }
        )

    seen_urls = set()

    for item in candidate_links[:50]:

        url = normalize_url(item["url"])

        if url in seen_urls:
            continue

        seen_urls.add(url)

        article = build_article(
            source=source,
            title=item["title"],
            url=url,
            publish_date="",
            abstract="",
        )

        if is_valid_article(article):
            articles.append(article)

    logger.info(
        "Collected %s generic HTML articles from: %s",
        len(articles),
        source_name,
    )

    return articles


# ============================================================
# Custom Parser Placeholders
# ============================================================

def collect_conab_source(source: Dict[str, object]) -> List[Dict[str, object]]:
    """
    CONAB parser placeholder.

    For now, use generic HTML parser.
    Later this can be replaced by a page-specific parser.
    """

    return collect_generic_html_source(source)


def collect_mpob_source(source: Dict[str, object]) -> List[Dict[str, object]]:
    """
    MPOB parser placeholder.

    For now, use generic HTML parser.
    Later this can be replaced by a page-specific parser.
    """

    return collect_generic_html_source(source)


def collect_mpoc_source(source: Dict[str, object]) -> List[Dict[str, object]]:
    """
    MPOC parser placeholder.

    For now, use generic HTML parser.
    Later this can be replaced by a page-specific parser.
    """

    return collect_generic_html_source(source)


def collect_report_page_source(source: Dict[str, object]) -> List[Dict[str, object]]:
    """
    Generic report page parser.

    This is a safe placeholder for WASDE / FAS report pages.
    It extracts report links but does not download PDF files.
    """

    return collect_generic_html_source(source)


# ============================================================
# Dispatcher
# ============================================================

def collect_source(source: Dict[str, object]) -> List[Dict[str, object]]:
    """
    Dispatch a source to the correct parser.
    """

    source_type = source.get("source_type")
    parser_name = source.get("parser_name")
    source_name = source.get("source_name", "Unknown Source")

    try:
        if source_type == SOURCE_TYPE_RSS or parser_name == PARSER_RSS:
            return collect_rss_source(source)

        if parser_name == PARSER_CONAB:
            return collect_conab_source(source)

        if parser_name == PARSER_MPOB:
            return collect_mpob_source(source)

        if parser_name == PARSER_MPOC:
            return collect_mpoc_source(source)

        if source_type == SOURCE_TYPE_HTML:
            return collect_generic_html_source(source)

        if source_type == SOURCE_TYPE_REPORT_PAGE:
            return collect_report_page_source(source)

        if parser_name in [PARSER_WASDE, PARSER_FAS_GAIN, PARSER_EIA]:
            return collect_report_page_source(source)

        logger.warning(
            "No parser available for source %s. source_type=%s, parser_name=%s",
            source_name,
            source_type,
            parser_name,
        )

        return []

    except Exception as exc:
        logger.error(
            "Failed to collect source %s: %s",
            source_name,
            exc,
        )
        return []


# ============================================================
# Deduplication
# ============================================================

def _title_signature(title: str) -> str:
    """Return a compact normalized title signature for fast deduplication."""
    title = clean_text(title or "").lower()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    stopwords = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "as", "by"}
    tokens = [t for t in title.split() if t not in stopwords]
    return " ".join(tokens[:14])


def deduplicate_articles(
    articles: List[Dict[str, object]],
    similarity_threshold: float = 0.92,
) -> List[Dict[str, object]]:
    """
    Fast deduplication for cloud refresh.

    The old implementation compared every title with every kept title using
    SequenceMatcher. That becomes slow when Google News/RSS sources return many
    items. This version keeps the highest-scored article for each URL or compact
    title signature in O(n).
    """

    if not articles:
        return []

    articles_sorted = sorted(
        articles,
        key=lambda x: (x.get("importance_score", 0), x.get("publish_date", "")),
        reverse=True,
    )

    kept: List[Dict[str, object]] = []
    seen_urls = set()
    seen_titles = set()

    for article in articles_sorted:
        url = normalize_url(article.get("url", ""))
        if url and url in seen_urls:
            continue

        title_sig = _title_signature(str(article.get("title", "")))
        if title_sig and title_sig in seen_titles:
            continue

        if url:
            seen_urls.add(url)
        if title_sig:
            seen_titles.add(title_sig)

        kept.append(article)

    return kept


# ============================================================
# Multi-source Collection
# ============================================================

def _collect_one_source(source: Dict[str, object]) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """Collect one source and return articles plus a health record."""
    source_name = source.get("source_name", "Unknown Source")
    start_time = time.time()

    try:
        articles = collect_source(source)
        elapsed = round(time.time() - start_time, 2)
        return articles, {
            "source_name": source_name,
            "status": "success",
            "article_count": len(articles),
            "error_message": "",
            "elapsed_seconds": elapsed,
            "checked_at": now_utc_iso(),
        }
    except Exception as exc:
        elapsed = round(time.time() - start_time, 2)
        logger.error("Failed to collect source %s: %s", source_name, exc)
        return [], {
            "source_name": source_name,
            "status": "failed",
            "article_count": 0,
            "error_message": str(exc),
            "elapsed_seconds": elapsed,
            "checked_at": now_utc_iso(),
        }


def collect_sources(
    sources: List[Dict[str, object]],
    deduplicate: bool = True,
    sleep_seconds_between_sources: float = 0.0,
    max_workers: int = 8,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    """
    Collect multiple sources.

    Uses concurrent collection by default. RSS/news refresh is network-bound,
    so parallel requests greatly reduce waiting time on Streamlit Cloud.
    """

    if not sources:
        return [], []

    all_articles: List[Dict[str, object]] = []
    source_health: List[Dict[str, object]] = []
    max_workers = max(1, min(int(max_workers or 1), 12, len(sources)))

    if max_workers == 1:
        for source in sources:
            articles, health = _collect_one_source(source)
            all_articles.extend(articles)
            source_health.append(health)
            if sleep_seconds_between_sources > 0:
                time.sleep(sleep_seconds_between_sources)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_source = {executor.submit(_collect_one_source, source): source for source in sources}
            for future in as_completed(future_to_source):
                articles, health = future.result()
                all_articles.extend(articles)
                source_health.append(health)

    if deduplicate:
        all_articles = deduplicate_articles(all_articles)

    source_health.sort(key=lambda x: str(x.get("source_name", "")))
    return all_articles, source_health


def collect_all_sources(
    deployment_mode: str = GLOBAL_FULL_MODE,
    mvp_rss_only: bool = False,
    include_custom_parser_sources: bool = True,
    include_non_rss: bool = True,
    deduplicate: bool = True,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    """
    Collect configured global sources.

    deployment_mode is accepted for backward compatibility but ignored by the
    global-only source registry.

    Defaults are intentionally global/full:
    - mvp_rss_only=False
    - include_non_rss=True
    - include_custom_parser_sources=True

    This means the refresh button tries the full VPN/global source universe.
    Set mvp_rss_only=True for a faster RSS-only reliability test.
    """

    if mvp_rss_only and get_mvp_rss_sources is not None:
        sources = get_mvp_rss_sources()
    elif get_refreshable_sources is not None:
        sources = get_refreshable_sources(
            include_non_rss=include_non_rss,
            include_custom_parser_sources=include_custom_parser_sources,
        )
    elif get_tier_1_sources is not None:
        sources = get_tier_1_sources()
        if not include_custom_parser_sources:
            sources = [s for s in sources if not s.get("requires_custom_parser", False)]
        if not include_non_rss:
            sources = [s for s in sources if s.get("source_type") == SOURCE_TYPE_RSS]
    else:
        sources = []

    return collect_sources(
        sources=sources,
        deduplicate=deduplicate,
    )


# ============================================================
# Optional Database Integration
# ============================================================

def refresh_and_store(
    deployment_mode: str = GLOBAL_FULL_MODE,
    mvp_rss_only: bool = False,
    include_non_rss: bool = True,
) -> Dict[str, object]:
    """
    Collect global sources and store them in SQLite.

    Kept as a convenience wrapper.  The Streamlit app uses refresh_service.py,
    which adds refresh logs around this same collection path.
    """

    articles, source_health = collect_all_sources(
        deployment_mode=deployment_mode,
        mvp_rss_only=mvp_rss_only,
        include_custom_parser_sources=True,
        include_non_rss=include_non_rss,
        deduplicate=True,
    )

    saved_count = 0
    try:
        import database

        for article in articles:
            try:
                if database.save_article(article):
                    saved_count += 1
            except Exception as exc:
                logger.warning("Failed to save article %s: %s", article.get("title", ""), exc)

        timestamp = now_utc_iso()
        if hasattr(database, "update_last_refresh"):
            database.update_last_refresh(timestamp)

        if hasattr(database, "update_source_health"):
            for record in source_health:
                database.update_source_health(
                    source_name=record.get("source_name", "Unknown Source"),
                    status=record.get("status", "unknown"),
                    articles_collected=int(record.get("article_count", 0) or 0),
                    error_message=record.get("error_message", ""),
                )

    except Exception as exc:
        logger.error("Database integration failed: %s", exc)

    failed_sources = len([r for r in source_health if r.get("status") == "failed"])
    successful_sources = len(source_health) - failed_sources

    return {
        "articles_collected": len(articles),
        "articles_saved": saved_count,
        "failed_sources": failed_sources,
        "successful_sources": successful_sources,
        "total_sources": len(source_health),
        "source_health": source_health,
        "refreshed_at": now_utc_iso(),
    }


# ============================================================
# Manual Test
# ============================================================

if __name__ == "__main__":

    result = refresh_and_store(
        deployment_mode=GLOBAL_FULL_MODE,
        mvp_rss_only=True,
    )

    print("Refresh result:")
    print(result)