"""L3 核心表 DDL（spec 第四节）。

只有 factions / datasheets / units 有对应的本地 CSV 源（db_sources/wahapedia/
Factions.csv、Datasheets.csv）；models/weapons/abilities/stratagems/detachments
的 CSV（Datasheets_models*.csv、Wargear.csv、Abilities.csv、Stratagems.csv、
Detachment_abilities.csv 等）尚未下载，表结构先建、暂为空，见 build.py 的
EXPECTED_TABLES 缺口报告。
"""
from __future__ import annotations

from typing import Dict, List, Tuple

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

# 待 Stratagems.csv，当前无源数据，仅建表。
# type/turn：CSV 原生列，分队页要用 type（"Eradication Cohort – Wargear Stratagem"）
# 给战略分类分组，用 turn（"Your turn"/"Either player's turn"）标可用时机。
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
    type TEXT,
    turn TEXT,
    effect_dsl_json TEXT,
    dsl_status TEXT DEFAULT 'not_modeled',
    fp_status TEXT
);
"""
# fp_status：NULL=现行；'removed_11e'=经 FP 完整重印裁定 11 版已删除（fp_rules
# deactivations 层写入，2026-07-16 裁 A）。原文保留可回滚；消费/对账应排除该标记行。

# 待 Detachment_abilities.csv，当前无源数据，仅建表。
# ⚠️ name_en 存的是**分队规则名**（Martial Mastery），detachment_name 才是玩家口中
# 的**分队容器名**（Shield Host）——CSV 本来两列都有，旧实现只取了规则名，容器名
# 整列丢失。detachment_id 是容器的官方 id，与 enhancements.detachment_id 同一口径。
DETACHMENTS_DDL = """
CREATE TABLE IF NOT EXISTS detachments (
    id TEXT PRIMARY KEY,
    faction TEXT,
    name_zh TEXT,
    name_en TEXT,
    rule_text TEXT,
    enhancements_json TEXT,
    detachment_name TEXT,
    detachment_id TEXT
);
"""

# Enhancements.csv → enhancements（P6 军表验表用：按 detachment_id 查合法强化+点数）
# P7-PR4：补 DSL 投影列（effect_dsl_json/dsl_status，真源在 dsl_payloads/*.json）与
# fp_status（NULL=现行；'removed_11e'=FP 完整重印裁定 11 版已删除；'added_11e'=FP 新增
# 补录行，Wahapedia 无源）。旧库缺列由 fp_rules/dsl_apply 的 ensure-column 幂等补齐。
ENHANCEMENTS_DDL = """
CREATE TABLE IF NOT EXISTS enhancements (
    id TEXT PRIMARY KEY,
    faction_id TEXT,
    detachment_id TEXT,
    detachment_name TEXT,
    name TEXT,
    cost INTEGER,
    legend TEXT,
    description TEXT,
    effect_dsl_json TEXT,
    dsl_status TEXT DEFAULT 'not_modeled',
    fp_status TEXT
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
    ABILITIES_DDL, STRATAGEMS_DDL, DETACHMENTS_DDL, ENHANCEMENTS_DDL, ALIASES_DDL,
)

# 晚于建表加进 DDL 的列。新库由 ALL_DDL 自带，旧库（已在跑、没重建过的
# db/wh40k.sqlite）靠 ensure_columns 幂等 ALTER 补上——`CREATE TABLE IF NOT EXISTS`
# 对已存在的表是空跑，光改 DDL 补不到旧库。fp_status / effect_dsl_json 这类由
# fp_rules._ensure_fp_status_column、dsl_apply._ensure_dsl_columns 各自就地补齐
# （它们要在自己的写路径上先于 UPDATE 生效），不重复列在这里。
LATE_COLUMNS: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "detachments": (("detachment_name", "TEXT"), ("detachment_id", "TEXT")),
    "stratagems": (("type", "TEXT"), ("turn", "TEXT")),
}


def ensure_columns(conn) -> List[str]:
    """旧库补齐 LATE_COLUMNS（幂等），返回本次真加上的 "表.列" 清单。

    conn 可以是 Connection 也可以是 Cursor（两者都有 execute）。表不存在时跳过，
    不越权造表——建表是 ALL_DDL 的职责，这里只管补列。
    """
    added: List[str] = []
    for table, cols in LATE_COLUMNS.items():
        info = list(conn.execute("PRAGMA table_info({})".format(table)))
        if not info:
            continue
        have = {r[1] for r in info}
        for name, decl in cols:
            if name not in have:
                conn.execute("ALTER TABLE {} ADD COLUMN {} {}".format(table, name, decl))
                added.append("{}.{}".format(table, name))
    return added
