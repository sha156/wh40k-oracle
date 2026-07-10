"""L3 核心表 DDL（spec 第四节）。

只有 factions / datasheets / units 有对应的本地 CSV 源（db_sources/wahapedia/
Factions.csv、Datasheets.csv）；models/weapons/abilities/stratagems/detachments
的 CSV（Datasheets_models*.csv、Wargear.csv、Abilities.csv、Stratagems.csv、
Detachment_abilities.csv 等）尚未下载，表结构先建、暂为空，见 build.py 的
EXPECTED_TABLES 缺口报告。
"""
from __future__ import annotations

FACTIONS_DDL = """
CREATE TABLE IF NOT EXISTS factions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    link TEXT
);
"""

# 与 Wahapedia Datasheets.csv 列一一对应，保真原始导出，不做语义加工
DATASHEETS_DDL = """
CREATE TABLE IF NOT EXISTS datasheets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    faction_id TEXT REFERENCES factions(id),
    source_id TEXT,
    legend TEXT,
    role TEXT,
    loadout TEXT,
    transport TEXT,
    virtual TEXT,
    leader_head TEXT,
    leader_footer TEXT,
    damaged_w TEXT,
    damaged_description TEXT,
    link TEXT
);
"""

# spec 第四节 units 表：datasheets 的语义化视图。
# points_json/keywords_json 恒为 NULL（待 Datasheets_models_cost.csv / Wargear.csv）。
UNITS_DDL = """
CREATE TABLE IF NOT EXISTS units (
    id TEXT PRIMARY KEY REFERENCES datasheets(id),
    faction_id TEXT REFERENCES factions(id),
    name_en TEXT NOT NULL,
    name_zh TEXT,
    points_json TEXT,
    keywords_json TEXT,
    version TEXT
);
"""

# 待 Datasheets_models.csv，当前无源数据，仅建表
MODELS_DDL = """
CREATE TABLE IF NOT EXISTS models (
    unit_id TEXT REFERENCES units(id),
    name TEXT,
    m TEXT,
    t TEXT,
    sv TEXT,
    invuln TEXT,
    w TEXT,
    ld TEXT,
    oc TEXT,
    base TEXT,
    count_options_json TEXT
);
"""

# 待 Datasheets_wargear.csv / Wargear.csv，当前无源数据，仅建表
WEAPONS_DDL = """
CREATE TABLE IF NOT EXISTS weapons (
    id TEXT PRIMARY KEY,
    unit_id TEXT REFERENCES units(id),
    name_zh TEXT,
    name_en TEXT,
    range TEXT,
    a TEXT,
    bs_ws TEXT,
    s TEXT,
    ap TEXT,
    d TEXT,
    keywords_json TEXT
);
"""

# 待 Abilities.csv / Datasheets_abilities.csv，当前无源数据，仅建表。
# dsl_status 诚实标记：encoded / partial / not_modeled（spec 第四节）。
ABILITIES_DDL = """
CREATE TABLE IF NOT EXISTS abilities (
    id TEXT PRIMARY KEY,
    owner_id TEXT,
    scope TEXT,
    condition_json TEXT,
    name_zh TEXT,
    name_en TEXT,
    text_zh TEXT,
    effect_dsl_json TEXT,
    dsl_status TEXT DEFAULT 'not_modeled'
);
"""

# 待 Stratagems.csv，当前无源数据，仅建表
STRATAGEMS_DDL = """
CREATE TABLE IF NOT EXISTS stratagems (
    id TEXT PRIMARY KEY,
    faction TEXT,
    detachment TEXT,
    name_zh TEXT,
    name_en TEXT,
    cp_cost TEXT,
    phase TEXT,
    text_zh TEXT,
    effect_dsl_json TEXT,
    dsl_status TEXT DEFAULT 'not_modeled'
);
"""

# 待 Detachment_abilities.csv，当前无源数据，仅建表
DETACHMENTS_DDL = """
CREATE TABLE IF NOT EXISTS detachments (
    id TEXT PRIMARY KEY,
    faction TEXT,
    name_zh TEXT,
    name_en TEXT,
    rule_text TEXT,
    enhancements_json TEXT
);
"""

# 实体解析查找表：wiki/terms.json（中文名）+ UNIT_ALIASES（社区俗名）汇入
ALIASES_DDL = """
CREATE TABLE IF NOT EXISTS aliases (
    alias TEXT NOT NULL,
    canonical_id TEXT NOT NULL,
    lang TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (alias, lang, source)
);
"""

ALL_DDL = (
    FACTIONS_DDL, DATASHEETS_DDL, UNITS_DDL, MODELS_DDL, WEAPONS_DDL,
    ABILITIES_DDL, STRATAGEMS_DDL, DETACHMENTS_DDL, ALIASES_DDL,
)
