"""
app.py

Streamlit entry point for the Agricultural Market Intelligence Dashboard.

Global-only version:
- China-safe / deployment mode selector removed from UI
- refresh button always runs the Global Full / VPN source universe
- filter state changes use Streamlit callbacks, avoiding post-widget state errors
- summary cards are safe quick-filter callbacks
- favorites are safe callbacks and work with Favorites-only mode
- pagination is clamped by database.fetch_news after filters change

Run:
    streamlit run app.py
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, Dict, Iterable, List, Optional

import streamlit as st

from database import (
    fetch_news,
    get_all_articles_count,
    get_distinct_sources,
    get_last_refresh,
    get_summary_counts,
    init_db,
    should_auto_refresh,
    toggle_favorite,
)
from refresh_service import refresh_all_sources, refresh_starter_sources
from source_registry import (
    COMMODITY_TAGS,
    FUNDAMENTAL_TOPIC_TAGS,
    MACRO_TOPIC_TAGS,
    REGION_TAGS,
    summarize_sources,
)


# ============================================================
# Page Config
# ============================================================

st.set_page_config(
    page_title="Agricultural Market Intelligence Dashboard",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Constants
# ============================================================

PAGE_SIZE = 20
DATE_WINDOW_OPTIONS = ["Today", "7D", "30D", "All"]
SORT_OPTIONS = ["Most Important", "Most Recent"]
IMPACT_OPTIONS = ["Critical", "High Impact", "Medium Impact", "Normal"]
MACRO_FUNDAMENTAL_OPTIONS = ["Macro", "Fundamental"]

SUMMARY_LABELS = {
    "critical": "Critical News Today",
    "high": "High Impact News Today",
    "macro": "Macro Alerts Today",
    "fundamental": "Fundamental Alerts Today",
}


# ============================================================
# CSS
# ============================================================


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-main: #0b0f14;
            --bg-card: rgba(255,255,255,0.055);
            --bg-card-hover: rgba(255,255,255,0.085);
            --border-soft: rgba(255,255,255,0.12);
            --text-main: #e8edf2;
            --text-muted: #9aa7b2;
            --accent-teal: #2dd4bf;
            --accent-amber: #f59e0b;
        }
        .stApp {
            background: radial-gradient(circle at top left, #16202b 0%, #0b0f14 36%, #080b0f 100%);
            color: var(--text-main);
        }
        section[data-testid="stSidebar"] {
            background: rgba(10, 15, 22, 0.92);
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        .main-title {
            font-size: 1.65rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.1rem;
        }
        .sub-title {
            color: var(--text-muted);
            font-size: 0.88rem;
            margin-bottom: 1.2rem;
        }
        .summary-card {
            background: var(--bg-card);
            border: 1px solid var(--border-soft);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: 0 8px 28px rgba(0,0,0,0.20);
            backdrop-filter: blur(10px);
            min-height: 104px;
        }
        .summary-card:hover {
            background: var(--bg-card-hover);
            border-color: rgba(45,212,191,0.35);
        }
        .summary-label {
            color: var(--text-muted);
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 8px;
        }
        .summary-value {
            font-size: 1.95rem;
            line-height: 1;
            font-weight: 780;
        }
        .summary-hint {
            color: var(--text-muted);
            font-size: 0.76rem;
            margin-top: 8px;
        }
        .feed-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-top: 18px;
            margin-bottom: 10px;
        }
        .feed-title {
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }
        .feed-meta {
            color: var(--text-muted);
            font-size: 0.82rem;
        }
        .news-card {
            background: rgba(255,255,255,0.052);
            border: 1px solid rgba(255,255,255,0.11);
            border-radius: 14px;
            padding: 13px 15px 12px 15px;
            margin-bottom: 10px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.16);
        }
        .news-card:hover {
            background: rgba(255,255,255,0.075);
            border-color: rgba(45,212,191,0.28);
        }
        .news-title {
            color: #f4f7fb;
            font-size: 0.99rem;
            font-weight: 650;
            line-height: 1.35;
            margin-bottom: 6px;
        }
        .news-meta {
            color: var(--text-muted);
            font-size: 0.76rem;
            margin-bottom: 8px;
        }
        .news-abstract {
            color: #c7d0da;
            font-size: 0.82rem;
            line-height: 1.42;
            margin-bottom: 9px;
        }
        .tag-row {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 5px;
        }
        .tag-chip {
            display: inline-block;
            padding: 2px 7px;
            border-radius: 999px;
            background: rgba(148,163,184,0.16);
            border: 1px solid rgba(148,163,184,0.22);
            color: #cbd5e1;
            font-size: 0.68rem;
            line-height: 1.45;
        }
        .impact-badge {
            display: inline-block;
            min-width: 92px;
            text-align: center;
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 0.67rem;
            font-weight: 760;
            letter-spacing: 0.055em;
            margin-right: 6px;
        }
        .impact-critical {
            background: rgba(239,68,68,0.16);
            color: #fecaca;
            border: 1px solid rgba(239,68,68,0.42);
        }
        .impact-high {
            background: rgba(249,115,22,0.15);
            color: #fed7aa;
            border: 1px solid rgba(249,115,22,0.42);
        }
        .impact-medium {
            background: rgba(234,179,8,0.15);
            color: #fef08a;
            border: 1px solid rgba(234,179,8,0.42);
        }
        .impact-normal {
            background: rgba(148,163,184,0.13);
            color: #cbd5e1;
            border: 1px solid rgba(148,163,184,0.32);
        }
        .score-text {
            color: var(--accent-amber);
            font-weight: 750;
            font-size: 0.75rem;
        }
        .small-muted {
            color: var(--text-muted);
            font-size: 0.76rem;
        }
        .active-filter {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 999px;
            background: rgba(45,212,191,0.11);
            border: 1px solid rgba(45,212,191,0.25);
            color: #ccfbf1;
            font-size: 0.72rem;
            margin-right: 5px;
            margin-bottom: 5px;
        }
        .stButton>button {
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.12);
        }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.10);
            padding: 12px;
            border-radius: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Session State / Callbacks
# ============================================================


def default_state() -> Dict[str, Any]:
    return {
        "date_window": "30D",
        "commodity_filter": [],
        "region_filter": [],
        "macro_topic_filter": [],
        "fundamental_topic_filter": [],
        "macro_fundamental_filter": [],
        "impact_filter": [],
        "source_filter": [],
        "sort_by": "Most Important",
        "favorites_only": False,
        "page": 1,
        "summary_preset": None,
        "auto_refresh_checked": False,
        "startup_seed_checked": False,
        "last_refresh_result": None,
    }


def init_session_state() -> None:
    for key, value in default_state().items():
        if key not in st.session_state:
            st.session_state[key] = value
    # Remove legacy mode state from older runs. It is no longer used by UI or refresh.
    if "deployment_mode" in st.session_state:
        del st.session_state["deployment_mode"]


def ensure_list_state(key: str, valid_options: Optional[Iterable[str]] = None) -> None:
    value = st.session_state.get(key, [])
    if value is None:
        value = []
    if not isinstance(value, list):
        value = [value]
    value = [str(item) for item in value if str(item).strip()]
    if valid_options is not None:
        valid = set(valid_options)
        value = [item for item in value if item in valid]
    st.session_state[key] = value


def sanitize_filter_state(source_options: Optional[List[str]] = None) -> None:
    ensure_list_state("commodity_filter", COMMODITY_TAGS)
    ensure_list_state("region_filter", REGION_TAGS)
    ensure_list_state("macro_topic_filter", MACRO_TOPIC_TAGS)
    ensure_list_state("fundamental_topic_filter", FUNDAMENTAL_TOPIC_TAGS)
    ensure_list_state("macro_fundamental_filter", MACRO_FUNDAMENTAL_OPTIONS)
    ensure_list_state("impact_filter", IMPACT_OPTIONS)
    ensure_list_state("source_filter", source_options or [])
    if st.session_state.get("date_window") not in DATE_WINDOW_OPTIONS:
        st.session_state.date_window = "30D"
    if st.session_state.get("sort_by") not in SORT_OPTIONS:
        st.session_state.sort_by = "Most Important"
    st.session_state.page = max(int(st.session_state.get("page", 1) or 1), 1)


def manual_filter_changed() -> None:
    st.session_state.page = 1
    st.session_state.summary_preset = None


def page_previous() -> None:
    st.session_state.page = max(1, int(st.session_state.get("page", 1) or 1) - 1)


def page_next(max_page: int) -> None:
    st.session_state.page = min(max_page, int(st.session_state.get("page", 1) or 1) + 1)


def clear_all_filters() -> None:
    """Clear user-selected filters but keep sort preference."""
    st.session_state.date_window = "30D"
    st.session_state.commodity_filter = []
    st.session_state.region_filter = []
    st.session_state.macro_topic_filter = []
    st.session_state.fundamental_topic_filter = []
    st.session_state.macro_fundamental_filter = []
    st.session_state.impact_filter = []
    st.session_state.source_filter = []
    st.session_state.favorites_only = False
    st.session_state.summary_preset = None
    st.session_state.page = 1


def apply_summary_preset(preset: str) -> None:
    """Summary-card quick filters. Safe callback: runs before widgets are rebuilt."""
    clear_all_filters()
    st.session_state.date_window = "Today"
    st.session_state.sort_by = "Most Important"
    st.session_state.summary_preset = preset

    if preset == "critical":
        st.session_state.impact_filter = ["Critical"]
    elif preset == "high":
        st.session_state.impact_filter = ["High Impact"]
    elif preset == "macro":
        st.session_state.impact_filter = ["Critical", "High Impact"]
        st.session_state.macro_fundamental_filter = ["Macro"]
    elif preset == "fundamental":
        st.session_state.impact_filter = ["Critical", "High Impact"]
        st.session_state.macro_fundamental_filter = ["Fundamental"]


def favorite_clicked(article_id: str) -> None:
    toggle_favorite(article_id)


# ============================================================
# Formatting Helpers
# ============================================================


def safe_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return []


def format_datetime(value: Optional[str]) -> str:
    if not value:
        return "Unknown time"
    raw = str(value).strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw[:22]


def impact_class(level: str) -> str:
    level = (level or "Normal").lower()
    if "critical" in level:
        return "impact-critical"
    if "high" in level:
        return "impact-high"
    if "medium" in level:
        return "impact-medium"
    return "impact-normal"


def trim_text(text: Optional[str], max_chars: int = 280) -> str:
    if not text:
        return ""
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def render_tags(tags: List[str]) -> str:
    tags = safe_list(tags)
    if not tags:
        return ""
    return "".join([f'<span class="tag-chip">{escape(tag)}</span>' for tag in tags])


# ============================================================
# Refresh Logic
# ============================================================


def run_refresh(full_refresh: bool = False) -> Dict[str, object]:
    """Run global refresh and return its result."""
    status_box = st.empty()
    progress = st.progress(0)
    try:
        if full_refresh:
            status_box.info("Running full RSS refresh across all configured sources...")
        else:
            status_box.info("Refreshing latest news from high-priority RSS sources...")
        progress.progress(15)

        result = refresh_all_sources(full_refresh=full_refresh)
        progress.progress(100)

        saved = int(result.get("articles_saved", 0) or 0)
        collected = int(result.get("articles_collected", 0) or 0)
        failed = int(result.get("failed_sources", 0) or 0)
        total_sources = int(result.get("total_sources", 0) or 0)
        status = str(result.get("status", "success"))

        if status == "failed":
            status_box.error(f"Refresh failed. Sources: {failed}/{total_sources} failed. {result.get('message', '')}")
        elif status == "empty":
            status_box.warning(
                "Refresh completed but collected zero articles. This usually means the cloud runtime cannot access feeds, "
                "or the selected feeds are temporarily unavailable."
            )
        elif failed:
            status_box.warning(
                f"Refresh partially completed. Collected {collected}, saved {saved}; "
                f"failed sources: {failed}/{total_sources}."
            )
        else:
            status_box.success(f"Refresh completed. Collected {collected} articles, saved {saved}.")
        return result
    except Exception as exc:
        status_box.error(f"Refresh failed: {exc}")
        return {"status": "failed", "message": str(exc)}


# ============================================================
# UI Components
# ============================================================


def render_header() -> None:
    source_summary = summarize_sources()
    st.markdown(
        f"""
        <div class="main-title">🌾 Agricultural Market Intelligence Dashboard</div>
        <div class="sub-title">
            {source_summary.get('total_sources', 0)} registered sources ·
            {source_summary.get('rss_ready_sources', 0)} RSS-ready feeds · ranked by market impact
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    available_sources = get_distinct_sources()
    sanitize_filter_state(source_options=available_sources)

    st.sidebar.markdown("### Controls")

    st.sidebar.selectbox(
        "Date Window",
        DATE_WINDOW_OPTIONS,
        key="date_window",
        on_change=manual_filter_changed,
    )

    st.sidebar.multiselect(
        "Commodity",
        COMMODITY_TAGS,
        key="commodity_filter",
        on_change=manual_filter_changed,
    )

    st.sidebar.multiselect(
        "Region",
        REGION_TAGS,
        key="region_filter",
        on_change=manual_filter_changed,
    )

    st.sidebar.markdown("#### Topic Filters")
    st.sidebar.multiselect(
        "Macro / Fundamental",
        MACRO_FUNDAMENTAL_OPTIONS,
        key="macro_fundamental_filter",
        on_change=manual_filter_changed,
    )

    st.sidebar.multiselect(
        "Macro Topics",
        MACRO_TOPIC_TAGS,
        key="macro_topic_filter",
        on_change=manual_filter_changed,
    )

    st.sidebar.multiselect(
        "Fundamental Topics",
        FUNDAMENTAL_TOPIC_TAGS,
        key="fundamental_topic_filter",
        on_change=manual_filter_changed,
    )

    st.sidebar.multiselect(
        "Importance Level",
        IMPACT_OPTIONS,
        key="impact_filter",
        on_change=manual_filter_changed,
    )

    if available_sources:
        st.sidebar.multiselect(
            "Source",
            available_sources,
            key="source_filter",
            on_change=manual_filter_changed,
        )
    else:
        st.sidebar.caption("Source filter will appear after data is collected.")

    st.sidebar.radio(
        "Sort By",
        SORT_OPTIONS,
        key="sort_by",
        on_change=manual_filter_changed,
    )

    st.sidebar.toggle(
        "Favorites only",
        key="favorites_only",
        on_change=manual_filter_changed,
    )

    c1, c2 = st.sidebar.columns(2)
    with c1:
        st.button("Clear filters", use_container_width=True, on_click=clear_all_filters)
    with c2:
        if st.button("Refresh", use_container_width=True):
            st.session_state.last_refresh_result = run_refresh(full_refresh=False)

    with st.sidebar.expander("Advanced refresh", expanded=False):
        st.caption("Use full refresh only when you have time. It checks every RSS-ready source.")
        if st.button("Full RSS refresh", use_container_width=True):
            st.session_state.last_refresh_result = run_refresh(full_refresh=True)

    st.sidebar.markdown("---")
    last_refresh = get_last_refresh()
    st.sidebar.caption(f"Last successful refresh: {format_datetime(last_refresh)}")
    st.sidebar.caption(f"Stored articles: {get_all_articles_count()}")

    summary = summarize_sources()
    st.sidebar.caption(
        f"Registered sources: {summary['total_sources']} · RSS-ready: {summary['rss_ready_sources']}"
    )


def render_refresh_result() -> None:
    result = st.session_state.get("last_refresh_result")
    if not result:
        return
    status = result.get("status", "")
    collected = int(result.get("articles_collected", 0) or 0)
    saved = int(result.get("articles_saved", 0) or 0)
    failed = int(result.get("failed_sources", 0) or 0)
    total = int(result.get("total_sources", 0) or 0)
    text = f"Last refresh: {status} · collected {collected}, saved {saved}, failed sources {failed}/{total}."
    if status == "failed":
        st.error(text)
    elif status == "empty" or failed:
        st.warning(text)
    else:
        st.success(text)


def render_summary_cards() -> None:
    counts = get_summary_counts(date_window="Today")
    cards = [
        {
            "label": "Critical News Today",
            "value": counts.get("critical_count", 0),
            "hint": "Impact level = Critical",
            "preset": "critical",
        },
        {
            "label": "High Impact Today",
            "value": counts.get("high_impact_count", 0),
            "hint": "Impact level = High Impact",
            "preset": "high",
        },
        {
            "label": "Macro Alerts Today",
            "value": counts.get("macro_alert_count", 0),
            "hint": "Critical / High macro stories",
            "preset": "macro",
        },
        {
            "label": "Fundamental Alerts Today",
            "value": counts.get("fundamental_alert_count", 0),
            "hint": "Critical / High fundamental stories",
            "preset": "fundamental",
        },
    ]

    cols = st.columns(4)
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="summary-card">
                    <div class="summary-label">{escape(card['label'])}</div>
                    <div class="summary-value">{int(card['value'])}</div>
                    <div class="summary-hint">{escape(card['hint'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.button(
                "View",
                key=f"summary_{card['preset']}",
                use_container_width=True,
                on_click=apply_summary_preset,
                args=(card["preset"],),
            )


def active_filter_items() -> List[str]:
    items: List[str] = []
    if st.session_state.date_window != "30D":
        items.append(f"Date: {st.session_state.date_window}")
    for label, key in [
        ("Commodity", "commodity_filter"),
        ("Region", "region_filter"),
        ("Macro/Fundamental", "macro_fundamental_filter"),
        ("Macro Topic", "macro_topic_filter"),
        ("Fundamental Topic", "fundamental_topic_filter"),
        ("Impact", "impact_filter"),
        ("Source", "source_filter"),
    ]:
        values = safe_list(st.session_state.get(key))
        if values:
            items.append(f"{label}: {', '.join(values)}")
    if st.session_state.favorites_only:
        items.append("Favorites only")
    return items


def render_active_filters() -> None:
    items = active_filter_items()
    if not items:
        return
    chips = "".join([f'<span class="active-filter">{escape(item)}</span>' for item in items])
    st.markdown(chips, unsafe_allow_html=True)


def render_news_card(article: Dict[str, Any]) -> None:
    article_id = str(article.get("article_id", ""))
    title = escape(str(article.get("title", "Untitled")))
    source = escape(str(article.get("source", "Unknown source")))
    publish_time = escape(format_datetime(article.get("publish_date") or article.get("collected_timestamp")))
    abstract = escape(trim_text(article.get("abstract"), 280))
    url = str(article.get("url", "") or "")
    score = int(round(float(article.get("importance_score") or 0)))
    level = str(article.get("impact_level", "Normal") or "Normal")
    favorite = bool(article.get("is_favorite"))

    commodity_tags = render_tags(article.get("commodity_tags", []))
    region_tags = render_tags(article.get("region_tags", []))
    topic_tags = render_tags(article.get("topic_tags", []))

    st.markdown(
        f"""
        <div class="news-card">
            <div>
                <span class="impact-badge {impact_class(level)}">{escape(level.upper())}</span>
                <span class="score-text">Score {score}</span>
            </div>
            <div class="news-title">{title}</div>
            <div class="news-meta">{source} · {publish_time}</div>
            <div class="news-abstract">{abstract}</div>
            <div class="tag-row">{commodity_tags}{region_tags}{topic_tags}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_cols = st.columns([1.1, 1.1, 7.8])
    with action_cols[0]:
        fav_label = "★ Saved" if favorite else "☆ Save"
        st.button(
            fav_label,
            key=f"fav_{article_id}",
            use_container_width=True,
            on_click=favorite_clicked,
            args=(article_id,),
            disabled=not bool(article_id),
        )
    with action_cols[1]:
        if url:
            st.link_button("Open", url, use_container_width=True)
        else:
            st.button("Open", key=f"open_disabled_{article_id}", disabled=True, use_container_width=True)


def render_feed() -> None:
    topic_filter = safe_list(st.session_state.macro_topic_filter) + safe_list(
        st.session_state.fundamental_topic_filter
    )

    result = fetch_news(
        date_window=st.session_state.date_window,
        commodity_filter=st.session_state.commodity_filter,
        region_filter=st.session_state.region_filter,
        topic_filter=topic_filter,
        impact_filter=st.session_state.impact_filter,
        macro_filter=st.session_state.macro_fundamental_filter,
        source_filter=st.session_state.source_filter,
        favorites_only=st.session_state.favorites_only,
        sort_by=st.session_state.sort_by,
        page=st.session_state.page,
        page_size=PAGE_SIZE,
    )

    total = int(result.get("total", 0) or 0)
    total_pages = int(result.get("total_pages", 1) or 1)
    page = int(result.get("page", 1) or 1)
    items = result.get("items", [])
    st.session_state.page = page

    st.markdown(
        f"""
        <div class="feed-header">
            <div class="feed-title">News Feed</div>
            <div class="feed-meta">{total} articles · page {page} / {total_pages}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.summary_preset:
        label = SUMMARY_LABELS.get(st.session_state.summary_preset, st.session_state.summary_preset)
        st.info(f"Quick filter applied: {label}. Use Clear filters to return to the full feed.")

    render_active_filters()

    if not items:
        st.warning("No articles match the current filters. Try clearing filters or refreshing data.")
        return

    for article in items:
        render_news_card(article)

    st.markdown("---")
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        st.button(
            "← Previous",
            disabled=page <= 1,
            use_container_width=True,
            on_click=page_previous,
        )
    with p2:
        st.markdown(
            f"<div class='small-muted' style='text-align:center;'>Page {page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with p3:
        st.button(
            "Next →",
            disabled=page >= total_pages,
            use_container_width=True,
            on_click=page_next,
            args=(total_pages,),
        )


# ============================================================
# Startup
# ============================================================


def maybe_seed_empty_database() -> None:
    """
    On Streamlit Community Cloud the SQLite file starts empty after first deploy.
    Run a small RSS-only starter refresh once per session so the first viewer
    does not see a completely blank dashboard.
    """
    if st.session_state.startup_seed_checked:
        return

    st.session_state.startup_seed_checked = True

    try:
        if get_all_articles_count() > 0:
            return
    except Exception:
        return

    with st.spinner("No stored news yet. Running a quick starter refresh..."):
        result = refresh_starter_sources()
        st.session_state.last_refresh_result = result

    if int(result.get("articles_saved", 0) or 0) == 0:
        st.warning(
            "Starter refresh did not save any articles. Try the sidebar Refresh button once, "
            "and check Streamlit logs if it still stays empty."
        )


def maybe_auto_refresh_notice() -> None:
    """
    In global mode, a full refresh may touch many sources.  Do not auto-refresh
    on startup; just tell the user when data is stale.
    """
    if st.session_state.auto_refresh_checked:
        return
    st.session_state.auto_refresh_checked = True
    if should_auto_refresh(hours=24):
        st.caption("Data is older than 24 hours or empty. Use Refresh in the sidebar to update the news feeds.")


def main() -> None:
    init_db()
    init_session_state()
    inject_css()
    maybe_seed_empty_database()
    maybe_auto_refresh_notice()

    render_header()
    render_sidebar()
    render_refresh_result()
    render_summary_cards()
    render_feed()


if __name__ == "__main__":
    main()
