"""
source_registry.py

Global-only source registry for the Agricultural Market Intelligence Dashboard.

This version intentionally removes China-safe mode from runtime behavior.  The app
and refresh service always use the full global/VPN source universe.  A few legacy
constants are kept as aliases so older imports do not break, but they no longer
create a separate UI or refresh path.

Design notes:
- RSS sources are preferred because they work with the generic collector.
- HTML/report sources are still registered and can be attempted by the generic
  parser, but RSS sources should be the first reliability baseline.
- Broad feeds should not carry "all commodity" default tags; otherwise commodity
  filters become noisy.  Source-level tags are kept mainly for specialized feeds.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional


# ============================================================
# Global-only deployment constants
# ============================================================

GLOBAL_FULL_MODE = "global_full"
GLOBAL_MODE = GLOBAL_FULL_MODE
DEFAULT_DEPLOYMENT_MODE = GLOBAL_FULL_MODE

# Backward-compatible aliases.  Do not expose these in the UI.
LOCAL_CN_MODE = GLOBAL_FULL_MODE
VALID_DEPLOYMENT_MODES = [GLOBAL_FULL_MODE]

# Cloud refresh defaults. Keep these conservative so the app feels responsive.
DEFAULT_RSS_TIMEOUT_SECONDS = 8
DEFAULT_MAX_ENTRIES_PER_SOURCE = 25
DEFAULT_FAST_REFRESH_SOURCE_LIMIT = 24


def normalize_deployment_mode(deployment_mode: str | None = None) -> str:
    """Return the single supported runtime mode: global_full."""
    return GLOBAL_FULL_MODE


# ============================================================
# Source Types / Parser Names
# ============================================================

SOURCE_TYPE_RSS = "rss"
SOURCE_TYPE_HTML = "html"
SOURCE_TYPE_REPORT_PAGE = "report_page"
SOURCE_TYPE_API = "api"

PARSER_RSS = "rss_parser"
PARSER_GENERIC_HTML = "generic_html_parser"
PARSER_USDA_RSS_DIRECTORY = "usda_rss_directory_parser"
PARSER_CONAB = "conab_parser"
PARSER_MPOB = "mpob_parser"
PARSER_MPOC = "mpoc_parser"
PARSER_WASDE = "wasde_parser"
PARSER_FAS_GAIN = "fas_gain_parser"
PARSER_EIA = "eia_parser"


# ============================================================
# Standard Tag Universe
# Keep aligned with classifier.py and app.py filters.
# ============================================================

COMMODITY_TAGS = ['Soybean', 'SBM', 'SBO', 'RSO', 'SFO', 'Palm Oil', 'Corn', 'Wheat', 'Coffee', 'Sugar', 'Cotton']
REGION_TAGS = ['Global',
 'Brazil',
 'Argentina',
 'United States',
 'Canada',
 'China',
 'Malaysia',
 'Indonesia',
 'Southeast Asia',
 'India',
 'Australia',
 'Russia',
 'Ukraine',
 'Romania',
 'European Union']
MACRO_TOPIC_TAGS = ['Interest Rates',
 'FX Rates',
 'Inflation',
 'Economic Growth',
 'Elections',
 'Geopolitical Conflicts',
 'Biofuel Policies',
 'Sustainability Policies',
 'Tariffs']
FUNDAMENTAL_TOPIC_TAGS = ['Weather',
 'Inland Logistics',
 'Ports',
 'Ocean Freight',
 'Planting Area',
 'Production',
 'Consumption',
 'Import',
 'Export',
 'Stocks',
 'Crushing']
TOPIC_TAGS = MACRO_TOPIC_TAGS + FUNDAMENTAL_TOPIC_TAGS


# ============================================================
# Global Source Registry
# ============================================================

SOURCE_REGISTRY: List[Dict[str, object]] = [{'source_name': 'USDA Latest News',
  'source_type': 'rss',
  'base_url': 'https://www.usda.gov/rss/latest-releases.xml',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States', 'Global'],
  'topic_tags': [],
  'parser_name': 'rss_parser',
  'priority_weight': 10,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Official Government Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'USDA官方Latest News RSS，覆盖农业政策、贸易、出口、补贴、生物燃料等高可信信息。'},
 {'source_name': 'USDA Blog',
  'source_type': 'rss',
  'base_url': 'https://www.usda.gov/rss/latest-blogs.xml',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States', 'Global'],
  'topic_tags': [],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 1B',
  'category': 'Official Government Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'USDA官方博客RSS，适合补充政策解释、农业实践和长期趋势内容。'},
 {'source_name': "USDA NASS - Today's Reports",
  'source_type': 'rss',
  'base_url': 'http://www.nass.usda.gov/rss/reports.xml',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Planting Area', 'Production', 'Stocks', 'Weather'],
  'parser_name': 'rss_parser',
  'priority_weight': 10,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Official Government Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': "USDA NASS Today's Reports RSS；包含作物产量、种植面积、库存等对市场高度敏感的数据发布。"},
 {'source_name': 'USDA NASS - News Events',
  'source_type': 'rss',
  'base_url': 'http://www.nass.usda.gov/rss/news.xml',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Production', 'Planting Area', 'Stocks'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Official Government Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'USDA NASS新闻事件RSS；适合捕捉统计调查、报告发布时间变化和重要公告。'},
 {'source_name': 'USDA NASS - ASB Notices',
  'source_type': 'rss',
  'base_url': 'http://www.nass.usda.gov/rss/asb.xml',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Production', 'Stocks', 'Planting Area'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Official Government Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Agricultural Statistics Board公告RSS；可捕捉NASS重要统计发布和调整。'},
 {'source_name': 'Federal Reserve',
  'source_type': 'rss',
  'base_url': 'https://www.federalreserve.gov/feeds/press_all.xml',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States', 'Global'],
  'topic_tags': ['Interest Rates', 'Inflation', 'Economic Growth', 'FX Rates'],
  'parser_name': 'rss_parser',
  'priority_weight': 10,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Macro Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': '美联储官方RSS，覆盖利率、通胀、宏观政策，对美元和大宗商品风险偏好重要。'},
 {'source_name': 'ECB',
  'source_type': 'rss',
  'base_url': 'https://www.ecb.europa.eu/rss/press.html',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['European Union', 'Global'],
  'topic_tags': ['Interest Rates', 'Inflation', 'Economic Growth', 'FX Rates'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Macro Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': '欧洲央行RSS，覆盖欧元区利率、通胀和宏观金融动态。'},
 {'source_name': 'EIA Today in Energy',
  'source_type': 'rss',
  'base_url': 'https://www.eia.gov/rss/todayinenergy.xml',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'SBO', 'Palm Oil', 'Corn'],
  'region_tags': ['United States', 'Global'],
  'topic_tags': ['Biofuel Policies', 'Consumption', 'Economic Growth'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Energy and Biofuel Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'EIA Today in Energy RSS；追踪能源、生物燃料、可再生柴油、SAF与油脂需求联动。'},
 {'source_name': 'World Grain - Corn',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1338-corn',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Corn'],
  'region_tags': ['Global'],
  'topic_tags': ['Production', 'Consumption', 'Export', 'Import', 'Stocks'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain玉米专题RSS；比全站RSS更适合作为玉米市场源。'},
 {'source_name': 'World Grain - Wheat',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1351-wheat',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Wheat'],
  'region_tags': ['Global', 'United States', 'Russia', 'Ukraine', 'European Union', 'Australia'],
  'topic_tags': ['Production', 'Export', 'Import', 'Stocks', 'Ocean Freight'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain小麦专题RSS；覆盖全球小麦供需、贸易、加工和地缘扰动。'},
 {'source_name': 'World Grain - Soybean',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1350-soybean',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'SBM', 'SBO'],
  'region_tags': ['Global', 'United States', 'Brazil', 'Argentina', 'China'],
  'topic_tags': ['Production', 'Export', 'Import', 'Stocks', 'Crushing'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain大豆专题RSS；覆盖大豆、豆粕、豆油相关产业链动态。'},
 {'source_name': 'World Grain - Oilseeds',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1344-oilseeds',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'RSO', 'SFO', 'Palm Oil'],
  'region_tags': ['Global', 'Brazil', 'Argentina', 'Canada', 'European Union', 'Ukraine'],
  'topic_tags': ['Production', 'Crushing', 'Export', 'Import', 'Stocks'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain油籽专题RSS；适合补充大豆、菜籽、葵籽等油籽产业链。'},
 {'source_name': 'World Grain - Rapeseed',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1346-rapeseed',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['RSO'],
  'region_tags': ['Global', 'Canada', 'European Union', 'Ukraine', 'Australia'],
  'topic_tags': ['Production', 'Crushing', 'Export', 'Import', 'Stocks'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain菜籽专题RSS；用于跟踪菜籽/菜油相关供需。'},
 {'source_name': 'World Grain - Sunflower Seed',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1923-sunflower-seed',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['SFO'],
  'region_tags': ['Global', 'Ukraine', 'Russia', 'European Union', 'Argentina'],
  'topic_tags': ['Production', 'Crushing', 'Export', 'Import', 'Stocks'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain葵籽专题RSS；用于跟踪葵油链条和黑海地区供应。'},
 {'source_name': 'World Grain - Trade',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1034-trade',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': ['Export', 'Import', 'Tariffs', 'Ocean Freight'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain贸易专题RSS；重点关注贸易流、关税、运输瓶颈和政策冲击。'},
 {'source_name': 'World Grain - Tariffs',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1969-tariffs',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global', 'United States', 'China', 'European Union'],
  'topic_tags': ['Tariffs', 'Export', 'Import'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain关税专题RSS；适合跟踪贸易战和农产品关税扰动。'},
 {'source_name': 'World Grain - Shipping',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1371-shipping',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': ['Ocean Freight', 'Ports', 'Export', 'Import'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain航运专题RSS；关注谷物和油籽海运、运费和供应链变化。'},
 {'source_name': 'World Grain - Ports',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1372-ports',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global', 'Brazil', 'Argentina', 'United States', 'Romania', 'Ukraine'],
  'topic_tags': ['Ports', 'Ocean Freight', 'Export', 'Import'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain港口专题RSS；适合监测出口港、装船、港口拥堵和基础设施。'},
 {'source_name': 'World Grain - Drought',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1894-drought',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global', 'Brazil', 'Argentina', 'United States', 'India', 'Australia', 'European Union'],
  'topic_tags': ['Weather', 'Production', 'Planting Area'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain干旱专题RSS；适合捕捉产量和单产风险。'},
 {'source_name': 'World Grain - Flooding',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1895-flooding',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global', 'Brazil', 'Argentina', 'United States', 'India', 'Australia', 'European Union'],
  'topic_tags': ['Weather', 'Production', 'Planting Area', 'Inland Logistics'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain洪水专题RSS；适合捕捉天气、物流和收割影响。'},
 {'source_name': 'World Grain - Ukraine Conflict',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1920-ukraine-conflict',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Corn', 'Wheat', 'SFO'],
  'region_tags': ['Ukraine', 'Russia', 'Romania', 'European Union', 'Global'],
  'topic_tags': ['Geopolitical Conflicts', 'Export', 'Ocean Freight', 'Ports'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1A',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain乌克兰冲突专题RSS；对黑海谷物和葵油出口风险很重要。'},
 {'source_name': 'World Grain - Financial Performance',
  'source_type': 'rss',
  'base_url': 'https://www.world-grain.com/rss/topic/1025-financial-performance',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': ['Economic Growth', 'Consumption', 'Crushing'],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 1B',
  'category': 'Industry Media Sources - World Grain',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'World Grain企业财务表现专题RSS；用于观察粮油加工、贸易和食品链企业景气度。'},
 {'source_name': 'Agri-Pulse - News',
  'source_type': 'rss',
  'base_url': 'https://www.agri-pulse.com/rss/topic/71-news',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States', 'Global'],
  'topic_tags': ['Tariffs', 'Biofuel Policies', 'Sustainability Policies', 'Export', 'Import'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 1B',
  'category': 'Policy and Trade Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Agri-Pulse综合新闻RSS；美国农业政策、贸易、生物燃料和监管动态较强。'},
 {'source_name': 'Agri-Pulse - Trade',
  'source_type': 'rss',
  'base_url': 'https://www.agri-pulse.com/rss/topic/106',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States', 'China', 'European Union', 'Global'],
  'topic_tags': ['Tariffs', 'Export', 'Import'],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 1B',
  'category': 'Policy and Trade Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Agri-Pulse贸易专题RSS；适合跟踪美国农业出口、关税和贸易谈判。'},
 {'source_name': 'Agri-Pulse - Energy',
  'source_type': 'rss',
  'base_url': 'https://www.agri-pulse.com/rss/topic/88',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Corn', 'Soybean', 'SBO', 'Palm Oil'],
  'region_tags': ['United States', 'Global'],
  'topic_tags': ['Biofuel Policies', 'Consumption', 'Economic Growth'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 1B',
  'category': 'Policy and Biofuel Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Agri-Pulse能源专题RSS；对乙醇、可再生柴油、SAF和45Z等政策较敏感。'},
 {'source_name': 'Agri-Pulse - Farm Bill',
  'source_type': 'rss',
  'base_url': 'https://www.agri-pulse.com/rss/topic/21768',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States'],
  'topic_tags': ['Biofuel Policies', 'Sustainability Policies', 'Tariffs', 'Production'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 1B',
  'category': 'Policy and Trade Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Agri-Pulse Farm Bill专题RSS；跟踪美国农业补贴、作物保险、乙醇和农政变化。'},
 {'source_name': 'IFPRI - Blogs',
  'source_type': 'rss',
  'base_url': 'https://www.ifpri.org/rss/?post_type=blog',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global', 'China', 'India', 'Southeast Asia', 'Brazil', 'Argentina'],
  'topic_tags': [],
  'parser_name': 'rss_parser',
  'priority_weight': 6,
  'timeout_seconds': 20,
  'tier': 'Tier 1C',
  'category': 'Research and Food Policy Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'IFPRI博客RSS；偏政策和研究视角，适合作为低频、深度背景源。'},
 {'source_name': 'IFPRI - News',
  'source_type': 'rss',
  'base_url': 'https://www.ifpri.org/rss/?post_type=news',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': [],
  'parser_name': 'rss_parser',
  'priority_weight': 6,
  'timeout_seconds': 20,
  'tier': 'Tier 1C',
  'category': 'Research and Food Policy Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'IFPRI新闻RSS；补充全球粮食安全、农业政策和发展经济学内容。'},
 {'source_name': 'Hellenic Shipping - Dry Bulk Market',
  'source_type': 'rss',
  'base_url': 'https://www.hellenicshippingnews.com/category/shipping-news/dry-bulk-market/feed/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global', 'China', 'Brazil', 'Argentina', 'United States', 'Australia', 'Ukraine', 'Russia'],
  'topic_tags': ['Ocean Freight', 'Export', 'Import', 'Ports'],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 1C',
  'category': 'Logistics and Freight Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Hellenic Shipping干散货市场RSS；谷物、煤炭、矿石共振下的Panamax/Supramax运费线索。'},
 {'source_name': 'Hellenic Shipping - Port News',
  'source_type': 'rss',
  'base_url': 'https://www.hellenicshippingnews.com/category/shipping-news/port-news/feed/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': ['Ports', 'Ocean Freight', 'Export', 'Import'],
  'parser_name': 'rss_parser',
  'priority_weight': 6,
  'timeout_seconds': 20,
  'tier': 'Tier 1C',
  'category': 'Logistics and Freight Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Hellenic Shipping港口新闻RSS；补充港口拥堵、装卸和基础设施信息。'},
 {'source_name': 'Hellenic Shipping - Commodity News',
  'source_type': 'rss',
  'base_url': 'https://www.hellenicshippingnews.com/category/commodities/commodity-news/feed/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': ['Ocean Freight', 'Export', 'Import', 'Economic Growth'],
  'parser_name': 'rss_parser',
  'priority_weight': 6,
  'timeout_seconds': 20,
  'tier': 'Tier 1C',
  'category': 'Logistics and Freight Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Hellenic Shipping商品新闻RSS；补充商品贸易和航运需求信息。'},
 {'source_name': 'Hellenic Shipping - Freight News',
  'source_type': 'rss',
  'base_url': 'https://www.hellenicshippingnews.com/category/commodities/freight-news/feed/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': ['Ocean Freight', 'Export', 'Import'],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 1C',
  'category': 'Logistics and Freight Sources',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Hellenic Shipping运费新闻RSS；适合监测海运成本变化。'},
 {'source_name': 'CONAB News',
  'source_type': 'html',
  'base_url': 'https://www.gov.br/conab/pt-br/assuntos/noticias',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Coffee', 'Sugar', 'Cotton'],
  'region_tags': ['Brazil'],
  'topic_tags': ['Production', 'Planting Area', 'Stocks', 'Export', 'Weather'],
  'parser_name': 'conab_parser',
  'priority_weight': 10,
  'timeout_seconds': 25,
  'tier': 'Tier 1B',
  'category': 'Official Government Sources',
  'is_mvp_source': False,
  'requires_custom_parser': True,
  'notes_in_chinese': '巴西CONAB新闻页；对巴西大豆、玉米、咖啡、糖和棉花基本面很重要，建议后续开发专门HTML parser。'},
 {'source_name': 'MPOB Press Release',
  'source_type': 'html',
  'base_url': 'https://mpob.gov.my/category/press-release/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Palm Oil'],
  'region_tags': ['Malaysia', 'Southeast Asia'],
  'topic_tags': ['Production', 'Stocks', 'Export', 'Biofuel Policies', 'Sustainability Policies'],
  'parser_name': 'mpob_parser',
  'priority_weight': 10,
  'timeout_seconds': 25,
  'tier': 'Tier 1B',
  'category': 'Official Government Sources',
  'is_mvp_source': False,
  'requires_custom_parser': True,
  'notes_in_chinese': '马来西亚棕榈油局新闻/公告页；棕榈油基本面核心来源，建议后续开发专门parser。'},
 {'source_name': 'MPOC',
  'source_type': 'html',
  'base_url': 'https://mpoc.org.my/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Palm Oil'],
  'region_tags': ['Malaysia', 'Southeast Asia', 'Global'],
  'topic_tags': ['Export', 'Import', 'Consumption', 'Sustainability Policies', 'Biofuel Policies'],
  'parser_name': 'mpoc_parser',
  'priority_weight': 8,
  'timeout_seconds': 25,
  'tier': 'Tier 1B',
  'category': 'Industry Organization Sources',
  'is_mvp_source': False,
  'requires_custom_parser': True,
  'notes_in_chinese': '马来西亚棕榈油委员会网站；适合后续抓市场评论、贸易和可持续性相关内容。'},
 {'source_name': 'AgWeb',
  'source_type': 'html',
  'base_url': 'https://www.agweb.com/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Weather', 'Planting Area', 'Production', 'Export', 'Stocks'],
  'parser_name': 'generic_html_parser',
  'priority_weight': 7,
  'timeout_seconds': 25,
  'tier': 'Tier 1C',
  'category': 'Industry Media Sources',
  'is_mvp_source': False,
  'requires_custom_parser': False,
  'notes_in_chinese': '美国农业媒体；通用HTML parser可试运行，但后续建议改为RSS/专用parser。'},
 {'source_name': 'Successful Farming',
  'source_type': 'html',
  'base_url': 'https://www.agriculture.com/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Weather', 'Planting Area', 'Production', 'Stocks'],
  'parser_name': 'generic_html_parser',
  'priority_weight': 7,
  'timeout_seconds': 25,
  'tier': 'Tier 1C',
  'category': 'Industry Media Sources',
  'is_mvp_source': False,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Successful Farming；适合补充美国农场层面、作物和天气信息。'},
 {'source_name': 'Farm Progress',
  'source_type': 'html',
  'base_url': 'https://www.farmprogress.com/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Weather', 'Planting Area', 'Production', 'Inland Logistics'],
  'parser_name': 'generic_html_parser',
  'priority_weight': 7,
  'timeout_seconds': 25,
  'tier': 'Tier 1C',
  'category': 'Industry Media Sources',
  'is_mvp_source': False,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Farm Progress；可补充美国区域农情、技术和市场动态。'},
 {'source_name': 'Feedstuffs',
  'source_type': 'html',
  'base_url': 'https://www.feedstuffs.com/',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Corn', 'Wheat', 'Soybean', 'SBM'],
  'region_tags': ['United States', 'Global'],
  'topic_tags': ['Consumption', 'Crushing', 'Production'],
  'parser_name': 'generic_html_parser',
  'priority_weight': 6,
  'timeout_seconds': 25,
  'tier': 'Tier 1C',
  'category': 'Feed and Livestock-linked Sources',
  'is_mvp_source': False,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Feedstuffs；用于饲料消费、畜牧链条和谷物需求侧补充。'},
 {'source_name': 'FreightWaves Maritime',
  'source_type': 'html',
  'base_url': 'https://www.freightwaves.com/news/category/news/maritime/shipping',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States', 'Global'],
  'topic_tags': ['Ocean Freight', 'Ports', 'Inland Logistics'],
  'parser_name': 'generic_html_parser',
  'priority_weight': 6,
  'timeout_seconds': 25,
  'tier': 'Tier 1C',
  'category': 'Logistics and Freight Sources',
  'is_mvp_source': False,
  'requires_custom_parser': False,
  'notes_in_chinese': 'FreightWaves海运频道；补充供应链、港口、海运和物流信息。'},
 {'source_name': 'International Grains Council Press',
  'source_type': 'html',
  'base_url': 'https://www.igc.int/public-site/press.aspx',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Corn', 'Wheat', 'Soybean'],
  'region_tags': ['Global'],
  'topic_tags': ['Production', 'Consumption', 'Export', 'Import', 'Stocks'],
  'parser_name': 'generic_html_parser',
  'priority_weight': 9,
  'timeout_seconds': 25,
  'tier': 'Tier 1B',
  'category': 'Official / Intergovernmental Sources',
  'is_mvp_source': False,
  'requires_custom_parser': False,
  'notes_in_chinese': 'IGC新闻/公告页；全球谷物供需和贸易权威度高，通用HTML parser可先试。'},
 {'source_name': 'USDA ERS Publications',
  'source_type': 'html',
  'base_url': 'https://www.ers.usda.gov/publications',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States', 'Global'],
  'topic_tags': ['Production', 'Consumption', 'Export', 'Import', 'Stocks', 'Economic Growth'],
  'parser_name': 'generic_html_parser',
  'priority_weight': 9,
  'timeout_seconds': 25,
  'tier': 'Tier 1B',
  'category': 'Official Government Report Sources',
  'is_mvp_source': False,
  'requires_custom_parser': False,
  'notes_in_chinese': 'USDA ERS出版物页；含Feed/Oil Crops/Wheat/Sugar/Cotton等Outlook报告，建议后续专门parser。'},
 {'source_name': 'USDA WASDE',
  'source_type': 'report_page',
  'base_url': 'https://www.usda.gov/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'SBM', 'SBO', 'Corn', 'Wheat', 'Cotton', 'Sugar'],
  'region_tags': ['United States', 'Global', 'Brazil', 'Argentina', 'China', 'European Union'],
  'topic_tags': ['Production', 'Consumption', 'Import', 'Export', 'Stocks', 'Crushing'],
  'parser_name': 'wasde_parser',
  'priority_weight': 10,
  'timeout_seconds': 30,
  'tier': 'Tier 1A',
  'category': 'Scheduled Critical Report Sources',
  'is_mvp_source': False,
  'requires_custom_parser': True,
  'notes_in_chinese': 'WASDE月报属于关键市场事件源；后续建议单独parser，并将新报告默认设为高优先级。',
  'default_impact_level': 'Critical'},
 {'source_name': 'USDA FAS GAIN',
  'source_type': 'report_page',
  'base_url': 'https://gain.fas.usda.gov/#/search',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global',
                  'Brazil',
                  'Argentina',
                  'United States',
                  'Canada',
                  'China',
                  'Malaysia',
                  'Indonesia',
                  'Southeast Asia',
                  'India',
                  'Australia',
                  'Russia',
                  'Ukraine',
                  'Romania',
                  'European Union'],
  'topic_tags': ['Production', 'Consumption', 'Import', 'Export', 'Stocks', 'Tariffs', 'Sustainability Policies'],
  'parser_name': 'fas_gain_parser',
  'priority_weight': 10,
  'timeout_seconds': 30,
  'tier': 'Tier 1A',
  'category': 'Official Government Report Sources',
  'is_mvp_source': False,
  'requires_custom_parser': True,
  'notes_in_chinese': 'USDA FAS GAIN报告价值高，但页面为动态应用，建议后续单独实现parser/API。'},
 {'source_name': 'Google News RSS - Global Ag Commodities',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28%22soybean%22+OR+%22corn%22+OR+%22wheat%22+OR+%22palm+oil%22+OR+%22sugar%22+OR+%22cotton%22%29+%28crop+OR+harvest+OR+export+OR+import+OR+stocks+OR+drought%29+when%3A7d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': [],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Reuters Agriculture Commodities',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=site%3Areuters.com+%28soybean+OR+corn+OR+wheat+OR+palm+oil+OR+sugar+OR+cotton+OR+agriculture%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': [],
  'parser_name': 'rss_parser',
  'priority_weight': 9,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': '通过Google News聚合Reuters农业和大宗商品新闻；仅Global Full/VPN模式。'},
 {'source_name': 'Google News RSS - Bloomberg Agriculture Commodities',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=site%3Abloomberg.com+%28soybean+OR+corn+OR+wheat+OR+palm+oil+OR+sugar+OR+cotton+OR+agriculture%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global'],
  'topic_tags': [],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': '通过Google News聚合Bloomberg农业和商品新闻；可能存在付费墙，但标题和摘要仍可用于信号捕捉。'},
 {'source_name': 'Google News RSS - AgWeb Site Search',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=site%3Aagweb.com+%28soybean+OR+corn+OR+wheat+OR+cotton+OR+crop+OR+USDA+OR+export%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Weather', 'Planting Area', 'Production', 'Export', 'Stocks'],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Successful Farming Site Search',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=site%3Aagriculture.com+%28soybean+OR+corn+OR+wheat+OR+cotton+OR+crop+OR+USDA+OR+harvest%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Weather', 'Planting Area', 'Production', 'Stocks'],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Farm Progress Site Search',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=site%3Afarmprogress.com+%28soybean+OR+corn+OR+wheat+OR+cotton+OR+crop+OR+USDA+OR+harvest%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'Cotton'],
  'region_tags': ['United States'],
  'topic_tags': ['Weather', 'Planting Area', 'Production', 'Stocks'],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Feedstuffs Site Search',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=site%3Afeedstuffs.com+%28feed+OR+grain+OR+corn+OR+soybean+meal+OR+wheat+OR+livestock%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Corn', 'Wheat', 'Soybean', 'SBM'],
  'region_tags': ['United States', 'Global'],
  'topic_tags': ['Consumption', 'Crushing', 'Production'],
  'parser_name': 'rss_parser',
  'priority_weight': 6,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Brazil Soy Corn CONAB',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28Brazil+OR+CONAB+OR+Mato+Grosso+OR+Parana%29+%28soybean+OR+soybeans+OR+corn+OR+safrinha+OR+harvest+OR+export%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn'],
  'region_tags': ['Brazil', 'Global'],
  'topic_tags': ['Production', 'Export', 'Weather', 'Planting Area'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Argentina Soy Corn Wheat',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28Argentina+OR+Rosario+OR+Buenos+Aires%29+%28soybean+OR+corn+OR+wheat+OR+harvest+OR+export+OR+drought%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'SBM', 'SBO'],
  'region_tags': ['Argentina', 'Global'],
  'topic_tags': ['Production', 'Export', 'Weather', 'Crushing'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Palm Oil Malaysia Indonesia',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28%22palm+oil%22+OR+CPO+OR+%22crude+palm+oil%22%29+%28Malaysia+OR+Indonesia+OR+MPOB+OR+GAPKI+OR+export+OR+stocks+OR+biodiesel%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Palm Oil'],
  'region_tags': ['Malaysia', 'Indonesia', 'Southeast Asia', 'Global'],
  'topic_tags': ['Production', 'Stocks', 'Export', 'Biofuel Policies', 'Sustainability Policies'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Black Sea Grain',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28%22Black+Sea%22+OR+Ukraine+OR+Russia+OR+Romania%29+%28grain+OR+wheat+OR+corn+OR+sunflower+OR+export+OR+port+OR+shipping%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Wheat', 'Corn', 'SFO'],
  'region_tags': ['Ukraine', 'Russia', 'Romania', 'European Union', 'Global'],
  'topic_tags': ['Geopolitical Conflicts', 'Export', 'Ocean Freight', 'Ports'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Biofuel Renewable Diesel SAF',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28%22renewable+diesel%22+OR+biodiesel+OR+ethanol+OR+SAF+OR+%22sustainable+aviation+fuel%22+OR+%22biofuel+mandate%22+OR+45Z%29+%28soybean+OR+corn+OR+palm+OR+agriculture%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Corn', 'Soybean', 'SBO', 'Palm Oil'],
  'region_tags': ['United States', 'European Union', 'Brazil', 'Indonesia', 'Global'],
  'topic_tags': ['Biofuel Policies', 'Consumption', 'Tariffs'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Ag Trade Tariffs',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28agriculture+OR+soybean+OR+corn+OR+wheat+OR+palm+oil+OR+cotton+OR+sugar%29+%28tariff+OR+tariffs+OR+sanction+OR+export+ban+OR+trade+war+OR+import+restriction%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['United States', 'China', 'European Union', 'Global'],
  'topic_tags': ['Tariffs', 'Export', 'Import', 'Geopolitical Conflicts'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Grain Freight Ports',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28grain+OR+soybean+OR+corn+OR+wheat+OR+oilseed%29+%28port+OR+ports+OR+shipping+OR+freight+OR+Panamax+OR+dry+bulk+OR+vessel+lineup%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Soybean', 'Corn', 'Wheat', 'RSO', 'SFO'],
  'region_tags': ['Global', 'Brazil', 'Argentina', 'United States', 'Ukraine', 'Romania'],
  'topic_tags': ['Ocean Freight', 'Ports', 'Export', 'Import'],
  'parser_name': 'rss_parser',
  'priority_weight': 7,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Weather Crop Risk',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28soybean+OR+corn+OR+wheat+OR+cotton+OR+sugar+OR+coffee+OR+palm+oil%29+%28drought+OR+flood+OR+flooding+OR+frost+OR+heatwave+OR+El+Nino+OR+La+Nina%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': [],
  'region_tags': ['Global', 'Brazil', 'Argentina', 'United States', 'India', 'Australia', 'European Union'],
  'topic_tags': ['Weather', 'Production', 'Planting Area'],
  'parser_name': 'rss_parser',
  'priority_weight': 8,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'},
 {'source_name': 'Google News RSS - Fertilizer Crop Input',
  'source_type': 'rss',
  'base_url': 'https://news.google.com/rss/search?q=%28fertilizer+OR+potash+OR+urea+OR+phosphate%29+%28corn+OR+wheat+OR+soybean+OR+Brazil+OR+India+OR+China+OR+Russia%29+when%3A14d&hl=en-US&gl=US&ceid=US:en',
  'enabled_in_local_cn_mode': False,
  'enabled_in_global_mode': True,
  'commodity_tags': ['Corn', 'Wheat', 'Soybean'],
  'region_tags': ['Global', 'Brazil', 'India', 'China', 'Russia', 'United States'],
  'topic_tags': ['Production', 'Economic Growth', 'Geopolitical Conflicts'],
  'parser_name': 'rss_parser',
  'priority_weight': 6,
  'timeout_seconds': 20,
  'tier': 'Tier 3',
  'category': 'Global Full Mode Aggregator',
  'is_mvp_source': True,
  'requires_custom_parser': False,
  'notes_in_chinese': 'Google News RSS聚合源，仅建议在Global Full/VPN模式使用。'}]


# ============================================================
# Helper Functions
# ============================================================


def _dedupe_sources(items: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    """Deduplicate sources by source_name while preserving order."""
    seen = set()
    output: List[Dict[str, object]] = []
    for item in items:
        name = str(item.get("source_name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        output.append(item)
    return output


def get_all_sources() -> List[Dict[str, object]]:
    """Return all registered global sources."""
    return list(SOURCE_REGISTRY)


def get_sources(
    deployment_mode: str | None = None,
    source_types: Optional[List[str]] = None,
    tiers: Optional[List[str]] = None,
    mvp_only: bool = False,
    include_custom_parser_sources: bool = True,
) -> List[Dict[str, object]]:
    """
    Return global sources filtered by source type / tier / parser readiness.

    deployment_mode is accepted only for backward compatibility and is ignored.
    """
    normalize_deployment_mode(deployment_mode)

    filtered: List[Dict[str, object]] = []
    for source in SOURCE_REGISTRY:
        if source_types is not None and source.get("source_type") not in source_types:
            continue
        if tiers is not None and source.get("tier") not in tiers:
            continue
        if mvp_only and not source.get("is_mvp_source", False):
            continue
        if not include_custom_parser_sources and source.get("requires_custom_parser", False):
            continue
        filtered.append(source)

    return _dedupe_sources(filtered)


def _source_sort_key(source: Dict[str, object]) -> tuple:
    tier_rank = {"Tier 1A": 0, "Tier 1B": 1, "Tier 1C": 2, "Tier 2": 3, "Tier 3": 4}
    return (
        -int(source.get("priority_weight", 0) or 0),
        tier_rank.get(str(source.get("tier", "")), 9),
        str(source.get("source_name", "")),
    )


def _prepare_runtime_sources(
    sources: Iterable[Dict[str, object]],
    timeout_seconds: int = DEFAULT_RSS_TIMEOUT_SECONDS,
    max_entries_per_source: int = DEFAULT_MAX_ENTRIES_PER_SOURCE,
) -> List[Dict[str, object]]:
    """Return copied source dicts with Streamlit-Cloud-friendly runtime limits."""
    prepared: List[Dict[str, object]] = []
    for source in sources:
        item = dict(source)
        item["timeout_seconds"] = min(int(item.get("timeout_seconds", timeout_seconds) or timeout_seconds), timeout_seconds)
        item.setdefault("max_entries", max_entries_per_source)
        prepared.append(item)
    return prepared


def get_mvp_rss_sources(
    deployment_mode: str | None = None,
    max_sources: Optional[int] = None,
) -> List[Dict[str, object]]:
    """Return RSS-ready global sources that can run through the generic RSS parser."""
    sources = get_sources(
        deployment_mode=deployment_mode,
        source_types=[SOURCE_TYPE_RSS],
        mvp_only=True,
        include_custom_parser_sources=False,
    )
    sources = sorted(sources, key=_source_sort_key)
    if max_sources is not None:
        sources = sources[: max(int(max_sources), 0)]
    return _prepare_runtime_sources(sources)


def get_fast_rss_sources(max_sources: int = DEFAULT_FAST_REFRESH_SOURCE_LIMIT) -> List[Dict[str, object]]:
    """Return the best high-priority RSS sources for an interactive refresh button."""
    return get_mvp_rss_sources(max_sources=max_sources)


def get_global_rss_sources() -> List[Dict[str, object]]:
    """Explicit global RSS helper used by refresh_service/tests."""
    return get_mvp_rss_sources(max_sources=None)


def get_refreshable_sources(
    include_non_rss: bool = False,
    include_custom_parser_sources: bool = False,
    max_sources: Optional[int] = None,
) -> List[Dict[str, object]]:
    """
    Sources attempted by refresh.

    Default is RSS-only because HTML/report pages are slower and require custom
    parsers. This is much better for Streamlit Community Cloud demos.
    """
    if not include_non_rss:
        return get_mvp_rss_sources(max_sources=max_sources)

    sources = get_sources(
        mvp_only=True,
        include_custom_parser_sources=include_custom_parser_sources,
    )
    sources = sorted(sources, key=_source_sort_key)
    if max_sources is not None:
        sources = sources[: max(int(max_sources), 0)]
    return _prepare_runtime_sources(sources)


def get_tier_1_sources(deployment_mode: str | None = None) -> List[Dict[str, object]]:
    """Return Tier 1A/1B/1C sources. deployment_mode is ignored."""
    return get_sources(
        deployment_mode=deployment_mode,
        tiers=["Tier 1A", "Tier 1B", "Tier 1C"],
        mvp_only=False,
        include_custom_parser_sources=True,
    )


def get_source_by_name(source_name: str) -> Optional[Dict[str, object]]:
    """Return one source definition by source_name."""
    for source in SOURCE_REGISTRY:
        if source.get("source_name") == source_name:
            return source
    return None


def get_source_names(deployment_mode: str | None = None, mvp_only: bool = False) -> List[str]:
    """Return source names for UI or debugging. deployment_mode is ignored."""
    return [str(source["source_name"]) for source in get_sources(deployment_mode=deployment_mode, mvp_only=mvp_only)]


def validate_source_registry(strict_tags: bool = False) -> List[str]:
    """Validate required fields, duplicate names, parser flags, and optional tag universe."""
    required_fields = [
        "source_name",
        "source_type",
        "base_url",
        "commodity_tags",
        "region_tags",
        "topic_tags",
        "parser_name",
        "priority_weight",
        "timeout_seconds",
        "tier",
        "category",
        "is_mvp_source",
        "requires_custom_parser",
        "notes_in_chinese",
    ]
    errors: List[str] = []
    seen = set()
    valid_source_types = {SOURCE_TYPE_RSS, SOURCE_TYPE_HTML, SOURCE_TYPE_REPORT_PAGE, SOURCE_TYPE_API}
    valid_commodities = set(COMMODITY_TAGS)
    valid_regions = set(REGION_TAGS)
    valid_topics = set(TOPIC_TAGS)

    for idx, source in enumerate(SOURCE_REGISTRY):
        name = str(source.get("source_name", f"source_index_{idx}"))
        for field in required_fields:
            if field not in source:
                errors.append(f"{name} missing field: {field}")
        if not source.get("source_name"):
            errors.append(f"Source index {idx} has empty source_name")
        elif source["source_name"] in seen:
            errors.append(f"Duplicate source_name: {source['source_name']}")
        else:
            seen.add(source["source_name"])
        if not source.get("base_url"):
            errors.append(f"{name} has empty base_url")
        if source.get("source_type") not in valid_source_types:
            errors.append(f"{name} has invalid source_type: {source.get('source_type')}")
        try:
            priority = int(source.get("priority_weight", 0))
            if not 0 <= priority <= 10:
                errors.append(f"{name} priority_weight should be 0-10, got {priority}")
        except Exception:
            errors.append(f"{name} has invalid priority_weight: {source.get('priority_weight')}")
        try:
            timeout = int(source.get("timeout_seconds", 0))
            if timeout <= 0:
                errors.append(f"{name} timeout_seconds should be > 0, got {timeout}")
        except Exception:
            errors.append(f"{name} has invalid timeout_seconds: {source.get('timeout_seconds')}")

        if strict_tags:
            for tag in source.get("commodity_tags", []):
                if tag not in valid_commodities:
                    errors.append(f"{name} has non-standard commodity tag: {tag}")
            for tag in source.get("region_tags", []):
                if tag not in valid_regions:
                    errors.append(f"{name} has non-standard region tag: {tag}")
            for tag in source.get("topic_tags", []):
                if tag not in valid_topics:
                    errors.append(f"{name} has non-standard topic tag: {tag}")
    return errors


def summarize_sources() -> Dict[str, int]:
    """Small helper for debugging / UI display."""
    sources = get_sources()
    rss_ready = get_mvp_rss_sources()
    return {
        "total_sources": len(sources),
        "rss_ready_sources": len(rss_ready),
        "tier_1_sources": len(get_tier_1_sources()),
        "custom_parser_sources": len([s for s in sources if s.get("requires_custom_parser")]),
    }


if __name__ == "__main__":
    print(summarize_sources())
    errors = validate_source_registry(strict_tags=True)
    if errors:
        print("Validation errors:")
        for error in errors:
            print("-", error)
    else:
        print("Source registry validation passed.")
