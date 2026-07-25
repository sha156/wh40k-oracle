"""db_compile/zh_weapons：中文武器名投影（数值指纹配对）。

回归的是 2026-07-25 那个「数值对、名字错」的线上 bug：旧渲染层按位置把黑图中文武器名
贴到英文行上，战斗修女小队因此把「爆弹手枪」贴到了 Ministorum hand flamer 的数值行。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from db_compile.zh_weapons import (build_keyword_glossary, build_zh_weapon_names,
                                   clean_zh_name, coverage_report,
                                   leftover_radicals, missing_terms)

DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")


# ── 纯函数 ────────────────────────────────────────────────────────

def test_clean_zh_name_folds_radical_and_parens():
    # ⻛ 是 U+2EDB 部首形，不是 U+98CE 风；NFKC 折不动，得靠显式对照表
    assert clean_zh_name("⻛暴爆弹枪") == "风暴爆弹枪"
    assert clean_zh_name("等离子手枪(标准)") == "等离子手枪（标准）"
    assert clean_zh_name(" 速射 2 ") == "速射2"


def _mini_db(tmp_path: Path) -> Path:
    """两把数值不同的武器 + 一份**顺序相反**的黑图中文层——按位置配就会错。"""
    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE units (id TEXT PRIMARY KEY, faction_id TEXT, "
                 "points_json TEXT)")
    conn.execute("CREATE TABLE weapons (id TEXT, unit_id TEXT, name_en TEXT, "
                 "name_zh TEXT, range TEXT, a TEXT, bs_ws TEXT, s TEXT, ap TEXT, "
                 "d TEXT, keywords_json TEXT)")
    conn.execute("CREATE TABLE unit_zh_detail (canonical_id TEXT PRIMARY KEY, "
                 "weapons_json TEXT)")
    conn.execute("INSERT INTO units VALUES ('U1','AS',NULL)")
    conn.execute("INSERT INTO weapons VALUES ('w1','U1','Hand flamer',NULL,'12','D6',"
                 "'N/A','4','0','1','[\"pistol\"]')")
    conn.execute("INSERT INTO weapons VALUES ('w2','U1','Bolt pistol',NULL,'12','1',"
                 "'3','4','0','1','[\"pistol\"]')")
    zh = {"射击武器": [
        {"name": "爆弹手枪", "射程": "12", "攻击次数": "1", "命中": "3+",
         "造伤": "4", "破甲": "0", "伤害": "1", "skill": ["手枪"]},
        {"name": "喷火手枪", "射程": "12", "攻击次数": "D6", "命中": "N/A",
         "造伤": "4", "破甲": "0", "伤害": "1", "skill": ["手枪"]},
    ]}
    conn.execute("INSERT INTO unit_zh_detail VALUES ('U1', ?)",
                 (json.dumps(zh, ensure_ascii=False),))
    conn.commit()
    conn.close()
    return db


def test_stat_fingerprint_beats_position(tmp_path):
    """中英顺序相反、数量相等——位置法必错，指纹法必对。"""
    db = _mini_db(tmp_path)
    build_zh_weapon_names(db)
    conn = sqlite3.connect(str(db))
    got = dict(conn.execute("SELECT name_en, name_zh FROM weapons"))
    conn.close()
    assert got["Bolt pistol"] == "爆弹手枪"      # A=1/BS=3+ 那行
    assert got["Hand flamer"] == "喷火手枪"      # A=D6/BS=N/A 那行


def test_rebuild_is_idempotent(tmp_path):
    db = _mini_db(tmp_path)
    first = build_zh_weapon_names(db)
    second = build_zh_weapon_names(db)
    assert first["paired_direct"] == second["paired_direct"]
    conn = sqlite3.connect(str(db))
    assert conn.execute(
        "SELECT COUNT(*) FROM weapons WHERE name_zh IS NOT NULL").fetchone()[0] == 2
    conn.close()


def test_keyword_glossary_learns_single_to_single(tmp_path):
    db = _mini_db(tmp_path)
    build_zh_weapon_names(db)
    rep = build_keyword_glossary(db)
    conn = sqlite3.connect(str(db))
    gloss = dict(conn.execute("SELECT term_en, term_zh FROM zh_keyword_glossary"))
    conn.close()
    assert rep["terms"] >= 1
    assert gloss.get("PISTOL") == "手枪"


# ── 真库端到端 ────────────────────────────────────────────────────

@needs_db
def test_battle_sisters_no_longer_misaligned():
    """线上 bug 的定点回归：中文名必须落在对应数值的那一行。"""
    conn = sqlite3.connect(str(DB))
    rows = dict(conn.execute(
        "SELECT name_en, name_zh FROM weapons WHERE unit_id = '000000903'"))
    stats = {n: (a, bs) for n, a, bs in conn.execute(
        "SELECT name_en, a, bs_ws FROM weapons WHERE unit_id = '000000903'")}
    conn.close()
    assert rows.get("Bolt pistol") == "爆弹手枪"
    assert stats["Bolt pistol"] == ("1", "3")            # 不是 D6/N/A 那行
    assert rows.get("Ministorum hand flamer") == "教廷喷火手枪"
    assert stats["Ministorum hand flamer"] == ("D6", "N/A")


@needs_db
def test_no_intra_unit_duplicate_translations():
    """同一单位内不许两把不同英文武器共用一个中文名（撞名＝必有一错）。"""
    conn = sqlite3.connect(str(DB))
    bad = []
    for (uid,) in conn.execute("SELECT DISTINCT unit_id FROM weapons"):
        rows = conn.execute(
            "SELECT name_en, name_zh FROM weapons WHERE unit_id = ? "
            "AND name_zh IS NOT NULL AND name_zh <> ''", (uid,)).fetchall()
        by_zh = {}
        for en, zh in rows:
            # 与 _dedupe_within_unit 同口径：忽略大小写——库里存在同一把武器两行只差
            # 大小写的情况（Toxinjector Harpoon / harpoon），它们同名是对的
            by_zh.setdefault(zh, set()).add((en or "").strip().lower())
        bad += [(uid, zh, ens) for zh, ens in by_zh.items() if len(ens) > 1]
    conn.close()
    assert not bad, f"撞名：{bad[:5]}"


@needs_db
def test_no_leftover_radicals_and_coverage_floor():
    assert leftover_radicals(DB) == {}
    cov = coverage_report(DB)
    cur_zh, cur_tot = cov["current"]
    assert cur_tot > 0 and cur_zh / cur_tot > 0.7   # 现役武器中文覆盖不得低于 70%


@needs_db
def test_missing_terms_is_a_worklist():
    terms = missing_terms(DB)
    assert isinstance(terms, list)
    if terms:
        en, n, sample = terms[0]
        assert isinstance(en, str) and n >= 1


# ── 人工译名真源（overrides）────────────────────────────────────

def test_weapon_overrides_file_is_wellformed():
    """人工译名真源：键值都非空、中文里不残留拉丁字母、同名不撞（同一中文对多英文）。"""
    import json as _json
    from db_compile.zh_weapons import OVERRIDES_PATH

    data = _json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    terms = data["weapons"]
    assert len(terms) > 400
    by_zh = {}
    for en, zh in terms.items():
        assert en.strip() and zh.strip(), f"空条目 {en!r}→{zh!r}"
        assert not __import__("re").search(r"[A-Za-z]", zh), f"{en} 的译名残留英文：{zh}"
        by_zh.setdefault(zh, []).append(en)
    # 允许的撞名：同一把武器的不同英文写法（大小写/词序），逐条列白名单
    allowed = {"动力爪", "大砍刀", "搞哥巨爪（重击）", "搞哥巨爪（横扫）"}
    dup = {zh: ens for zh, ens in by_zh.items() if len(ens) > 1 and zh not in allowed}
    assert not dup, f"未登记的撞名：{list(dup.items())[:5]}"


def test_unit_overrides_file_is_wellformed():
    import json as _json
    from db_compile.blacklibrary import UNIT_OVERRIDES_PATH

    data = _json.loads(UNIT_OVERRIDES_PATH.read_text(encoding="utf-8"))
    units = data["units"]
    assert len(units) >= 25
    for en, zh in units.items():
        assert en.strip() and zh.strip()
        assert not __import__("re").search(r"[A-Za-z]", zh), f"{en} 的译名残留英文：{zh}"


@needs_db
def test_current_units_fully_localized():
    """现役单位（图鉴默认列的那批）的单位名与武器名都该有中文——这是本轮补译的验收线。"""
    import json as _json

    conn = sqlite3.connect(str(DB))
    cur = set()
    for uid, pj in conn.execute("SELECT id, points_json FROM units"):
        try:
            if pj and (_json.loads(pj) or {}).get("mfm"):
                cur.add(uid)
        except _json.JSONDecodeError:
            continue
    for (uid,) in conn.execute("SELECT canonical_id FROM unit_zh_detail"):
        cur.add(uid)
    miss_units = [n for uid, n, zh in conn.execute("SELECT id, name_en, name_zh FROM units")
                  if uid in cur and not (zh or "").strip()]
    miss_weapons = [n for uid, n, zh in conn.execute(
        "SELECT unit_id, name_en, name_zh FROM weapons") if uid in cur and not (zh or "").strip()]
    conn.close()
    assert not miss_units, f"现役单位缺中文名：{miss_units[:5]}"
    assert not miss_weapons, f"现役武器缺中文名：{miss_weapons[:5]}"


@needs_db
def test_all_current_weapon_keywords_localized():
    """现役武器的 USR 关键词也要全有中文——中英混排（[IGNORES COVER，手枪]）是半成品。"""
    import json as _json

    conn = sqlite3.connect(str(DB))
    cur = set()
    for uid, pj in conn.execute("SELECT id, points_json FROM units"):
        try:
            if pj and (_json.loads(pj) or {}).get("mfm"):
                cur.add(uid)
        except _json.JSONDecodeError:
            continue
    for (uid,) in conn.execute("SELECT canonical_id FROM unit_zh_detail"):
        cur.add(uid)
    gloss = {en for (en,) in conn.execute("SELECT term_en FROM zh_keyword_glossary")}
    missing = set()
    for uid, kj in conn.execute("SELECT unit_id, keywords_json FROM weapons"):
        if uid not in cur or not kj:
            continue
        try:
            for k in _json.loads(kj) or []:
                for tok in str(k).split(","):
                    t = tok.strip().upper()
                    if t and t not in gloss:
                        missing.add(t)
        except _json.JSONDecodeError:
            continue
    conn.close()
    assert not missing, f"未翻译的关键词：{sorted(missing)[:10]}"


def test_keyword_rules_are_consistent_within_family():
    """同族 USR 必须整齐：ANTI-X N+ 一律「反X N+」，不能混「针对X」。"""
    from db_compile.zh_weapons import _rule_translate

    assert _rule_translate("ANTI-INFANTRY 2+") == "反步兵2+"
    assert _rule_translate("ANTI-VEHICLE 4+") == "反载具4+"
    assert _rule_translate("RAPID FIRE D6+3") == "速射D6+3"
    assert _rule_translate("MELTA 6") == "热熔6"
    assert _rule_translate("SUSTAINED HITS 3") == "连击3"
    assert _rule_translate("PISTOL") is None          # 非参数化的走学习/人工层
