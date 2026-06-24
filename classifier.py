"""
classifier.py

Keyword-based classification engine for the Agricultural Market Intelligence Dashboard.

Main responsibilities:
1. Detect commodity tags.
2. Detect region tags.
3. Detect topic tags.
4. Determine macro_or_fundamental category.
5. Provide clean helper functions for collectors.py and scoring.py.

This version is rule-based and does not require any external API.
"""

import re
from html import unescape
from typing import Dict, List, Set


# ============================================================
# Text Cleaning Utilities
# ============================================================

def clean_text(text: str) -> str:
    """
    Clean raw text from RSS/HTML sources.
    """

    if text is None:
        return ""

    text = str(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode HTML entities
    text = unescape(text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_text(text: str) -> str:
    """
    Normalize text for keyword matching.
    """

    text = clean_text(text)
    text = text.lower()

    # Normalize punctuation into spaces
    text = re.sub(r"[^a-z0-9%$./+-]+", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def contains_keyword(text: str, keyword: str) -> bool:
    """
    Match keyword with basic word-boundary logic.

    For multi-word phrases, direct substring match is used.
    For short abbreviations such as SBM/SBO, exact-ish matching is used.
    """

    if not text or not keyword:
        return False

    text_norm = normalize_text(text)
    keyword_norm = normalize_text(keyword)

    if not keyword_norm:
        return False

    if " " in keyword_norm:
        return keyword_norm in text_norm

    pattern = r"(^|[^a-z0-9])" + re.escape(keyword_norm) + r"([^a-z0-9]|$)"
    return re.search(pattern, text_norm) is not None


# ============================================================
# Commodity Keyword Dictionary
# ============================================================

COMMODITY_KEYWORDS = {
    "Soybean": [
        "soybean",
        "soybeans",
        "soyabean",
        "soyabeans",
        "soya bean",
        "soya beans",
        "oilseed",
        "oilseeds",
    ],

    "SBM": [
        "soybean meal",
        "soymeal",
        "soy meal",
        "sbm",
    ],

    "SBO": [
        "soybean oil",
        "soyoil",
        "soy oil",
        "sbo",
    ],

    "RSO": [
        "rapeseed oil",
        "canola oil",
        "rapeseed",
        "canola",
        "rso",
    ],

    "SFO": [
        "sunflower oil",
        "sunflower seed oil",
        "sunseed oil",
        "sfo",
    ],

    "Palm Oil": [
        "palm oil",
        "crude palm oil",
        "cpo",
        "palm kernel oil",
        "pko",
        "olein",
        "stearin",
    ],

    "Corn": [
        "corn",
        "maize",
    ],

    "Wheat": [
        "wheat",
    ],

    "Coffee": [
        "coffee",
        "arabica",
        "robusta",
    ],

    "Sugar": [
        "sugar",
        "raw sugar",
        "white sugar",
        "cane sugar",
        "sugarcane",
    ],

    "Cotton": [
        "cotton",
    ],
}


# ============================================================
# Region Keyword Dictionary
# ============================================================

REGION_KEYWORDS = {
    "Global": [
        "global",
        "world",
        "worldwide",
        "international",
    ],

    "Brazil": [
        "brazil",
        "brazilian",
        "conab",
        "mato grosso",
        "parana",
        "rio grande do sul",
    ],

    "Argentina": [
        "argentina",
        "argentine",
        "rosario",
        "buenos aires",
    ],

    "United States": [
        "united states",
        "u.s.",
        "us ",
        "usa",
        "american",
        "usda",
        "nass",
        "federal reserve",
        "fed",
    ],

    "Canada": [
        "canada",
        "canadian",
        "aaFC".lower(),
    ],

    "China": [
        "china",
        "chinese",
        "beijing",
        "dalian",
        "zhengzhou",
    ],

    "Malaysia": [
        "malaysia",
        "malaysian",
        "mpob",
        "mpoc",
        "kuala lumpur",
        "sabah",
        "sarawak",
    ],

    "Indonesia": [
        "indonesia",
        "indonesian",
        "jakarta",
        "gapki",
    ],

    "Southeast Asia": [
        "southeast asia",
        "south-east asia",
        "asean",
    ],

    "India": [
        "india",
        "indian",
        "new delhi",
    ],

    "Australia": [
        "australia",
        "australian",
        "abares",
    ],

    "Russia": [
        "russia",
        "russian",
        "moscow",
    ],

    "Ukraine": [
        "ukraine",
        "ukrainian",
        "kyiv",
        "black sea",
    ],

    "Romania": [
        "romania",
        "romanian",
        "constanta",
    ],

    "European Union": [
        "european union",
        "eurozone",
        "euro area",
        "eu ",
        "europe",
        "european",
        "ecb",
        "brussels",
    ],
}


# ============================================================
# Topic Keyword Dictionaries
# ============================================================

MACRO_TOPIC_KEYWORDS = {
    "Interest Rates": [
        "interest rate",
        "interest rates",
        "rate hike",
        "rate cut",
        "monetary policy",
        "policy rate",
        "fomc",
        "federal reserve",
        "fed",
        "ecb",
        "central bank",
    ],

    "FX Rates": [
        "foreign exchange",
        "fx",
        "currency",
        "dollar",
        "usd",
        "real",
        "brl",
        "yuan",
        "cny",
        "ringgit",
        "myr",
        "euro",
    ],

    "Inflation": [
        "inflation",
        "cpi",
        "pce",
        "price pressure",
        "consumer prices",
    ],

    "Economic Growth": [
        "economic growth",
        "gdp",
        "recession",
        "growth outlook",
        "slowdown",
        "economic activity",
    ],

    "Elections": [
        "election",
        "elections",
        "vote",
        "voting",
        "presidential",
        "parliamentary",
    ],

    "Geopolitical Conflicts": [
        "war",
        "conflict",
        "geopolitical",
        "black sea",
        "red sea",
        "sanction",
        "sanctions",
        "military",
    ],

    "Biofuel Policies": [
        "biofuel",
        "biodiesel",
        "renewable diesel",
        "saf",
        "sustainable aviation fuel",
        "ethanol",
        "mandate",
        "blending",
        "rfs",
        "low carbon fuel standard",
        "lcfs",
    ],

    "Sustainability Policies": [
        "sustainability",
        "sustainable",
        "deforestation",
        "eudr",
        "carbon",
        "emissions",
        "certification",
        "traceability",
        "mspo",
        "rsPO".lower(),
    ],

    "Tariffs": [
        "tariff",
        "tariffs",
        "duty",
        "duties",
        "anti-dumping",
        "countervailing",
        "trade war",
    ],
}


FUNDAMENTAL_TOPIC_KEYWORDS = {
    "Weather": [
        "weather",
        "drought",
        "rain",
        "rainfall",
        "flood",
        "flooding",
        "heatwave",
        "frost",
        "el nino",
        "la nina",
        "dryness",
        "temperature",
    ],

    "Inland Logistics": [
        "truck",
        "trucking",
        "rail",
        "railway",
        "barge",
        "river",
        "inland logistics",
        "transport",
        "transportation",
        "road",
    ],

    "Ports": [
        "port",
        "ports",
        "terminal",
        "loading",
        "shipment",
        "berth",
        "vessel lineup",
    ],

    "Ocean Freight": [
        "ocean freight",
        "freight",
        "shipping",
        "dry bulk",
        "panamax",
        "handysize",
        "supramax",
        "vessel",
        "sea freight",
    ],

    "Planting Area": [
        "planting",
        "planted area",
        "acreage",
        "area estimate",
        "sown area",
        "seeding",
    ],

    "Production": [
        "production",
        "output",
        "harvest",
        "crop",
        "yield",
        "crop estimate",
        "forecast",
        "estimate",
        "production cut",
    ],

    "Consumption": [
        "consumption",
        "demand",
        "use",
        "usage",
        "food use",
        "feed use",
        "industrial use",
    ],

    "Import": [
        "import",
        "imports",
        "imported",
        "buying",
        "purchase",
        "purchases",
    ],

    "Export": [
        "export",
        "exports",
        "exported",
        "shipment",
        "shipments",
        "sales",
        "export sales",
    ],

    "Stocks": [
        "stock",
        "stocks",
        "inventory",
        "inventories",
        "ending stocks",
        "carryout",
    ],

    "Crushing": [
        "crush",
        "crushing",
        "crusher",
        "oilseed processing",
        "processing margin",
    ],
}


TOPIC_KEYWORDS = {}
TOPIC_KEYWORDS.update(MACRO_TOPIC_KEYWORDS)
TOPIC_KEYWORDS.update(FUNDAMENTAL_TOPIC_KEYWORDS)


# ============================================================
# Classification Functions
# ============================================================

def _detect_tags(text: str, keyword_map: Dict[str, List[str]]) -> List[str]:
    """
    Generic tag detection based on a keyword map.
    """

    detected: Set[str] = set()

    for tag, keywords in keyword_map.items():

        for keyword in keywords:

            if contains_keyword(text, keyword):
                detected.add(tag)
                break

    return sorted(detected)


def detect_commodity_tags(text: str) -> List[str]:
    return _detect_tags(text, COMMODITY_KEYWORDS)


def detect_region_tags(text: str) -> List[str]:
    return _detect_tags(text, REGION_KEYWORDS)


def detect_topic_tags(text: str) -> List[str]:
    return _detect_tags(text, TOPIC_KEYWORDS)


def detect_macro_or_fundamental(topic_tags: List[str]) -> str:
    """
    Determine whether an article is Macro, Fundamental, Mixed or Unclassified.
    """

    macro_tags = set(MACRO_TOPIC_KEYWORDS.keys())
    fundamental_tags = set(FUNDAMENTAL_TOPIC_KEYWORDS.keys())

    topic_set = set(topic_tags or [])

    has_macro = len(topic_set.intersection(macro_tags)) > 0
    has_fundamental = len(topic_set.intersection(fundamental_tags)) > 0

    if has_macro and has_fundamental:
        return "Mixed"

    if has_macro:
        return "Macro"

    if has_fundamental:
        return "Fundamental"

    return "Unclassified"


def merge_static_and_detected_tags(
    detected_tags: List[str],
    static_tags: List[str],
) -> List[str]:
    """
    Merge tags detected from text with source-level tags.
    """

    result = set()

    for tag in detected_tags or []:
        if tag:
            result.add(tag)

    for tag in static_tags or []:
        if tag:
            result.add(tag)

    return sorted(result)


def classify_text(
    title: str = "",
    abstract: str = "",
    source_default_commodity_tags: List[str] = None,
    source_default_region_tags: List[str] = None,
    source_default_topic_tags: List[str] = None,
) -> Dict[str, object]:
    """
    Classify article text into commodity, region, topic and macro/fundamental tags.
    """

    source_default_commodity_tags = source_default_commodity_tags or []
    source_default_region_tags = source_default_region_tags or []
    source_default_topic_tags = source_default_topic_tags or []

    combined_text = f"{title or ''} {abstract or ''}"

    detected_commodity_tags = detect_commodity_tags(combined_text)
    detected_region_tags = detect_region_tags(combined_text)
    detected_topic_tags = detect_topic_tags(combined_text)

    commodity_tags = merge_static_and_detected_tags(
        detected_commodity_tags,
        source_default_commodity_tags,
    )

    region_tags = merge_static_and_detected_tags(
        detected_region_tags,
        source_default_region_tags,
    )

    topic_tags = merge_static_and_detected_tags(
        detected_topic_tags,
        source_default_topic_tags,
    )

    macro_or_fundamental = detect_macro_or_fundamental(topic_tags)

    return {
        "commodity_tags": commodity_tags,
        "region_tags": region_tags,
        "topic_tags": topic_tags,
        "macro_or_fundamental": macro_or_fundamental,
    }


def classify_article(article: Dict[str, object], source: Dict[str, object] = None) -> Dict[str, object]:
    """
    Classify an article dictionary and return the updated article.
    """

    source = source or {}

    result = classify_text(
        title=article.get("title", ""),
        abstract=article.get("abstract", ""),
        source_default_commodity_tags=source.get("commodity_tags", []),
        source_default_region_tags=source.get("region_tags", []),
        source_default_topic_tags=source.get("topic_tags", []),
    )

    article["commodity_tags"] = result["commodity_tags"]
    article["region_tags"] = result["region_tags"]
    article["topic_tags"] = result["topic_tags"]
    article["macro_or_fundamental"] = result["macro_or_fundamental"]

    return article


# ============================================================
# Backward Compatibility
# ============================================================

def classify(text: str) -> Dict[str, List[str]]:
    """
    Backward-compatible wrapper used by earlier collectors.py versions.
    """

    result = classify_text(
        title=text,
        abstract="",
    )

    return {
        "commodity_tags": result["commodity_tags"],
        "region_tags": result["region_tags"],
        "topic_tags": result["topic_tags"],
    }


# ============================================================
# Manual Test
# ============================================================

if __name__ == "__main__":

    sample_title = "Brazil soybean crop estimate cut after drought affects Mato Grosso"
    sample_summary = "Export outlook may tighten global oilseed balance."

    output = classify_text(
        title=sample_title,
        abstract=sample_summary,
    )

    print(output)