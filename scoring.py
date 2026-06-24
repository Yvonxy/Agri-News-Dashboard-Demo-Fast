"""
scoring.py

Importance scoring engine for the Agricultural Market Intelligence Dashboard.

Scoring logic:
1. Source weight
2. Keyword impact weight
3. Recency weight
4. Multi-dimensional relevance
5. Strategic relevance

Final score is normalized to 0-100.

Impact levels:
- Critical: 90-100
- High Impact: 75-89
- Medium Impact: 60-74
- Normal: <60
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional

try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None


# ============================================================
# Impact Keyword Weights
# ============================================================

HIGH_IMPACT_KEYWORDS = {
    # Trade / policy shocks
    "export ban": 22,
    "export restriction": 20,
    "import restriction": 18,
    "tariff": 18,
    "tariffs": 18,
    "sanction": 18,
    "sanctions": 18,
    "trade war": 18,
    "anti-dumping": 15,
    "countervailing": 15,

    # Weather / production shocks
    "drought": 20,
    "flood": 18,
    "flooding": 18,
    "heatwave": 16,
    "frost": 16,
    "crop failure": 22,
    "production cut": 20,
    "crop estimate": 15,
    "yield forecast": 15,
    "acreage": 12,
    "planting area": 12,

    # Key reports / balance sheet
    "wasde": 22,
    "grain stocks": 18,
    "ending stocks": 16,
    "carryout": 14,
    "nass": 12,
    "conab": 16,

    # Biofuel / SAF
    "biodiesel mandate": 18,
    "biofuel mandate": 18,
    "renewable diesel": 15,
    "sustainable aviation fuel": 15,
    "saf": 12,
    "ethanol mandate": 12,

    # Macro
    "rate hike": 15,
    "rate cut": 15,
    "interest rate": 12,
    "inflation": 10,
    "recession": 12,
    "currency": 8,

    # Logistics
    "port disruption": 18,
    "strike": 16,
    "freight disruption": 16,
    "black sea": 16,
    "red sea": 14,
    "shipping disruption": 14,
}


STRATEGIC_RELEVANCE_KEYWORDS = {
    "supply-demand": 10,
    "supply and demand": 10,
    "trade flow": 10,
    "trade flows": 10,
    "margin": 8,
    "crush margin": 10,
    "crushing": 8,
    "stocks": 8,
    "inventory": 8,
    "import demand": 10,
    "export demand": 10,
    "policy change": 12,
    "mandate": 10,
    "regulation": 8,
}


# ============================================================
# Date Parsing Utilities
# ============================================================

def parse_datetime(value: object) -> Optional[datetime]:
    """
    Parse RSS/HTML date into timezone-aware datetime.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()

        if not text:
            return None

        dt = None

        # Try email/RSS date format first
        try:
            dt = parsedate_to_datetime(text)
        except Exception:
            dt = None

        # Try dateutil if available
        if dt is None and date_parser is not None:
            try:
                dt = date_parser.parse(text)
            except Exception:
                dt = None

        if dt is None:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def get_age_hours(publish_date: object) -> Optional[float]:
    """
    Return article age in hours.
    """

    dt = parse_datetime(publish_date)

    if dt is None:
        return None

    now = datetime.now(timezone.utc)
    diff = now - dt

    return max(diff.total_seconds() / 3600, 0)


# ============================================================
# Score Components
# ============================================================

def source_score(source_priority: int = 5) -> float:
    """
    Convert source priority_weight into score component.
    Max contribution: 30.
    """

    try:
        source_priority = int(source_priority)
    except Exception:
        source_priority = 5

    source_priority = max(0, min(source_priority, 10))

    return source_priority * 3.0


def keyword_score(title: str = "", abstract: str = "") -> float:
    """
    Score based on high-impact keywords.
    Max contribution: 30.
    """

    text = f"{title or ''} {abstract or ''}".lower()

    score = 0

    for keyword, weight in HIGH_IMPACT_KEYWORDS.items():
        if keyword in text:
            score += weight

    return min(score, 30)


def strategic_relevance_score(title: str = "", abstract: str = "") -> float:
    """
    Additional score for strategy-relevant language.
    Max contribution: 10.
    """

    text = f"{title or ''} {abstract or ''}".lower()

    score = 0

    for keyword, weight in STRATEGIC_RELEVANCE_KEYWORDS.items():
        if keyword in text:
            score += weight

    return min(score, 10)


def recency_score(publish_date: object) -> float:
    """
    Score based on article recency.
    Max contribution: 25.
    """

    age_hours = get_age_hours(publish_date)

    if age_hours is None:
        return 5

    if age_hours <= 24:
        return 25

    if age_hours <= 72:
        return 20

    if age_hours <= 7 * 24:
        return 15

    if age_hours <= 30 * 24:
        return 8

    return 0


def relevance_score(
    commodity_tags: List[str] = None,
    region_tags: List[str] = None,
    topic_tags: List[str] = None,
) -> float:
    """
    Score based on multi-dimensional relevance.
    Max contribution: 15.
    """

    commodity_tags = commodity_tags or []
    region_tags = region_tags or []
    topic_tags = topic_tags or []

    score = 0

    if commodity_tags:
        score += 4

    if region_tags:
        score += 4

    if topic_tags:
        score += 4

    if len(commodity_tags) >= 2:
        score += 1.5

    if len(region_tags) >= 2:
        score += 1.5

    if len(topic_tags) >= 2:
        score += 1.5

    return min(score, 15)


# ============================================================
# Final Score and Impact Level
# ============================================================

def normalize_score(score: float) -> int:
    """
    Normalize and round final score.
    """

    try:
        score = float(score)
    except Exception:
        score = 0

    return int(round(max(0, min(score, 100))))


def get_impact_level(score: float) -> str:
    """
    Convert numeric score to impact level.
    """

    score = normalize_score(score)

    if score >= 90:
        return "Critical"

    if score >= 75:
        return "High Impact"

    if score >= 60:
        return "Medium Impact"

    return "Normal"


def calculate_importance_score(
    article: Dict[str, object],
    source: Dict[str, object] = None,
) -> int:
    """
    Calculate final 0-100 importance score for an article.
    """

    source = source or {}

    title = article.get("title", "")
    abstract = article.get("abstract", "")
    publish_date = article.get("publish_date", "")

    source_priority = article.get(
        "source_priority",
        source.get("priority_weight", 5),
    )

    commodity_tags = article.get("commodity_tags", [])
    region_tags = article.get("region_tags", [])
    topic_tags = article.get("topic_tags", [])

    score = 0

    score += source_score(source_priority)
    score += keyword_score(title, abstract)
    score += strategic_relevance_score(title, abstract)
    score += recency_score(publish_date)
    score += relevance_score(
        commodity_tags=commodity_tags,
        region_tags=region_tags,
        topic_tags=topic_tags,
    )

    # Scheduled critical report override
    default_impact_level = source.get("default_impact_level")

    if default_impact_level == "Critical":
        score = max(score, 90)

    return normalize_score(score)


def score_article(
    article: Dict[str, object],
    source: Dict[str, object] = None,
) -> Dict[str, object]:
    """
    Add importance_score and impact_level to article dict.
    """

    score = calculate_importance_score(article, source)

    article["importance_score"] = score
    article["impact_level"] = get_impact_level(score)

    if "source_priority" not in article:
        article["source_priority"] = int((source or {}).get("priority_weight", 5))

    return article


# ============================================================
# Backward Compatibility
# ============================================================

SOURCE_WEIGHTS = {
    "USDA News": 30,
    "USDA NASS": 30,
    "USDA WASDE": 30,
    "USDA FAS GAIN": 30,
    "CONAB": 30,
    "MPOB": 30,
    "Federal Reserve": 30,
    "ECB": 27,
    "EIA": 27,
    "World Grain": 24,
}


def calculate_score(source: str, title: str) -> int:
    """
    Backward-compatible wrapper used by earlier collectors.py versions.
    """

    article = {
        "source": source,
        "title": title,
        "abstract": "",
        "publish_date": "",
        "commodity_tags": [],
        "region_tags": [],
        "topic_tags": [],
        "source_priority": 5,
    }

    if source in SOURCE_WEIGHTS:
        article["source_priority"] = min(int(SOURCE_WEIGHTS[source] / 3), 10)

    return calculate_importance_score(article)


# ============================================================
# Manual Test
# ============================================================

if __name__ == "__main__":

    sample_article = {
        "title": "Brazil soybean crop estimate cut after drought",
        "abstract": "Lower production may affect export flows and global stocks.",
        "publish_date": datetime.now(timezone.utc).isoformat(),
        "commodity_tags": ["Soybean"],
        "region_tags": ["Brazil"],
        "topic_tags": ["Production", "Export", "Weather"],
        "source_priority": 10,
    }

    print(score_article(sample_article))