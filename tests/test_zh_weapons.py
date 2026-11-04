"""db_compile/zh_weapons：中文武器名投影（数值指纹配对）。

回归的是 2026-07-25 那个「数值对、名字错」的线上 bug：旧渲染层按位置把黑图中文武器名
贴到英文行上，战斗修女小队因此把「爆弹手枪」贴到了 Ministorum hand flamer 的数值行。
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from db_compile.zh_weapons import (build_keyword_glossary, build_zh_weapon_names,
                                   clean_zh_name, coverage_report,
                                   leftover_radicals, missing_terms)

DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")
LANGUAGE_ACCEPTANCE = json.loads(
    (Path(__file__).parent / "fixtures/chinese_name_recovery.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def normal_language_db(tmp_path_factory):
    """Normal offline projection on a private copy, with frozen source evidence."""
    from db_compile.update import UpdateConfig, stage_zh_details, stage_zh_weapons

    sources = {Path(rel): digest for rel, digest in LANGUAGE_ACCEPTANCE["source_sha256"].items()}
    assert all(path.exists() for path in sources), "Required localization source evidence missing"
    assert {str(p).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sources} == LANGUAGE_ACCEPTANCE["source_sha256"], "Source drift requires review"
    original_db_hash = hashlib.sha256(DB.read_bytes()).hexdigest()
    trial = tmp_path_factory.mktemp("normal-language")
    db = trial / "copy.sqlite"
    shutil.copy2(DB, db)
    for path in sources:
        shutil.copy2(path, trial / path.name)
    cfg = UpdateConfig(db=db, offline=True, blacklibrary_cache=trial / "units.json",
                       blacklibrary_details=trial / "details.json")
    assert stage_zh_details(cfg).ok
    assert stage_zh_weapons(cfg).ok
    yield db
    assert hashlib.sha256(DB.read_bytes()).hexdigest() == original_db_hash
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in sources.items())


def _assert_current_name_coverage(conn):
    """Every current name gap must equal an exact reviewed weapon identity/profile."""
    from db_compile.active_units import active_unit_ids

    current = active_unit_ids(conn)
    assert current, "No current membership to reconcile"
    missing_units = [dict(zip(("id", "faction_id", "name_en", "name_zh"), r)) for r in conn.execute(
        "SELECT id,faction_id,name_en,name_zh FROM units ORDER BY id")
                     if r[0] in current and not (r[3] or "").strip()]
    assert missing_units == LANGUAGE_ACCEPTANCE["fallback_units"], (
        f"Unregistered missing unit names: {missing_units}")
    columns = [r[1] for r in conn.execute("PRAGMA table_info(weapons)")]
    missing_weapons = []
    for row in conn.execute("SELECT * FROM weapons ORDER BY id"):
        weapon = dict(zip(columns, row))
        if weapon["unit_id"] not in current or (weapon["name_zh"] or "").strip():
            continue
        faction, en, zh = conn.execute(
            "SELECT faction_id,name_en,name_zh FROM units WHERE id=?", (weapon["unit_id"],)).fetchone()
        weapon.update(faction_id=faction, unit_name_en=en, unit_name_zh=zh)
        missing_weapons.append(weapon)
    assert missing_weapons == LANGUAGE_ACCEPTANCE["fallback_weapons"], (
        f"Unregistered or drifted English fallback slots: {missing_weapons}")
    guard = LANGUAGE_ACCEPTANCE["fallback_unit"]
    assert conn.execute("SELECT id,faction_id,name_en,name_zh,keywords_json FROM units WHERE id=?",
                        (guard["id"],)).fetchone() == tuple(guard.values()), "Fallback unit identity drift"
    assert not conn.execute("SELECT 1 FROM unit_zh_detail WHERE canonical_id=?",
                            (guard["id"],)).fetchone(), "Accepted source body changed; reopen fallback review"


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


def _melee_db(tmp_path: Path) -> Path:
    """三把数值互不相同的**近战**武器。库里射程写 'Melee'、黑图写 '近战'。

    回归的是：两个写法不归一时近战数值指纹首位永远对不上，Pass A 对近战全盘失效，
    只剩「两边各只剩一把」的 Pass B 兜底——一个单位有两把以上近战武器就整组留英文
    （实测「地狱之末」3 把近战全是英文）。
    """
    db = tmp_path / "melee.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE units (id TEXT PRIMARY KEY, faction_id TEXT, "
                 "points_json TEXT)")
    conn.execute("CREATE TABLE weapons (id TEXT, unit_id TEXT, name_en TEXT, "
                 "name_zh TEXT, range TEXT, a TEXT, bs_ws TEXT, s TEXT, ap TEXT, "
                 "d TEXT, keywords_json TEXT)")
    conn.execute("CREATE TABLE unit_zh_detail (canonical_id TEXT PRIMARY KEY, "
                 "weapons_json TEXT)")
    conn.execute("INSERT INTO units VALUES ('U1','AM',NULL)")
    conn.execute("INSERT INTO weapons VALUES ('w1','U1','Close combat weapon',NULL,"
                 "'Melee','2','4','3','0','1','[]')")
    conn.execute("INSERT INTO weapons VALUES ('w2','U1','Dirk',NULL,"
                 "'Melee','3','3','3','-1','1','[]')")
    conn.execute("INSERT INTO weapons VALUES ('w3','U1','Power weapon',NULL,"
                 "'Melee','4','3','4','-2','1','[]')")
    zh = {"近战武器": [   # 顺序与库里不同，只能靠数值认
        {"name": "动力武器", "射程": "近战", "攻击次数": "4", "命中": "3+",
         "造伤": "4", "破甲": "-2", "伤害": "1", "skill": []},
        {"name": "格斗武器", "射程": "近战", "攻击次数": "2", "命中": "4+",
         "造伤": "3", "破甲": "0", "伤害": "1", "skill": []},
        {"name": "短剑", "射程": "近战", "攻击次数": "3", "命中": "3+",
         "造伤": "3", "破甲": "-1", "伤害": "1", "skill": ["精准"]},
    ]}
    conn.execute("INSERT INTO unit_zh_detail VALUES ('U1', ?)",
                 (json.dumps(zh, ensure_ascii=False),))
    conn.commit()
    conn.close()
    return db


def test_melee_range_token_is_normalized_across_languages(tmp_path):
    """三把近战全部按数值配上——不归一 'Melee'/'近战' 时这里一把都配不出来。"""
    db = _melee_db(tmp_path)
    rep = build_zh_weapon_names(db)
    conn = sqlite3.connect(str(db))
    got = dict(conn.execute("SELECT name_en, name_zh FROM weapons"))
    conn.close()
    assert rep["paired_direct"] == 3
    assert got["Close combat weapon"] == "格斗武器"
    assert got["Dirk"] == "短剑"
    assert got["Power weapon"] == "动力武器"


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
def test_current_units_fully_localized(normal_language_db):
    """All current names reconcile; exactly proven absent Chinese slots stay English."""
    with closing(sqlite3.connect(normal_language_db)) as conn:
        _assert_current_name_coverage(conn)


@needs_db
def test_active_db_current_names_reconcile():
    """The published active DB itself (not a staged copy) meets the same coverage.

    Guards against the active DB drifting from the reviewed projection, e.g. a
    scheduled online `db_compile update` replacing the release baseline
    (R5 receipt: db_sources/release-check-20260930/host/finish/R5/RECEIPT.json).
    """
    with closing(sqlite3.connect(f"file:{DB.resolve().as_posix()}?mode=ro", uri=True)) as conn:
        _assert_current_name_coverage(conn)


@needs_db
@pytest.mark.parametrize("guard", LANGUAGE_ACCEPTANCE["pending_name_recoveries"],
                         ids=lambda r: r["canonical_id"])
def test_pending_name_recoveries_keep_accepted_sources_and_unchanged_names(normal_language_db, guard):
    # Decision C (empty-cell name restore) is unanswered: the source identity
    # stays accepted and evidenced, but units.name_zh must remain 'before'.
    from db_compile.blacklibrary import _norm_en, load_details

    records = [r for r in load_details(Path("db_sources/blacklibrary/details.json"))
               if str(r.get("id")) == guard["source_id"]]
    assert len(records) == 1
    record = records[0]
    assert hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest() == (
        guard["source_record_sha256"])
    assert record["detail"]
    assert _norm_en(record["name_en"]) == _norm_en(guard["canonical_name_en"])
    assert record["name_zh"] == guard["after"]
    with closing(sqlite3.connect(normal_language_db)) as conn:
        assert conn.execute("SELECT faction_id,name_en,name_zh FROM units WHERE id=?",
                            (guard["canonical_id"],)).fetchone() == (
            guard["faction_id"], guard["canonical_name_en"], guard["before"])
        assert conn.execute("SELECT * FROM blacklibrary_detail_identity WHERE canonical_id=?",
                            (guard["canonical_id"],)).fetchone() == (
            guard["canonical_id"], guard["source_id"], guard["source_name_en"],
            guard["source_faction_zh"], guard["canonical_name_en"], guard["faction_id"])
        assert conn.execute("SELECT name_zh FROM unit_zh_detail WHERE canonical_id=?",
                            (guard["canonical_id"],)).fetchone() == (guard["after"],)


@needs_db
def test_fallback_source_absence_and_ambiguity_remain_exact(normal_language_db):
    from db_compile.blacklibrary import _norm_en, load_details
    from db_compile.blacklibrary_scope import POLICY, reviewed_empty_listing

    evidence = LANGUAGE_ACCEPTANCE["source_evidence"]
    assert hashlib.sha256(POLICY.read_bytes()).hexdigest() == evidence["listing_policy_sha256"]
    details = load_details(Path("db_sources/blacklibrary/details.json"))
    assert [r["id"] for r in details if _norm_en(r.get("name_en")) == "captainonbike"] == evidence["details_ids"]
    assert [r["id"] for r in details if any(
        w.get("name") == "双联爆弹枪" for kind in ("射击武器", "近战武器")
        for w in ((r.get("detail") or {}).get(kind) or []))] == (
        evidence["literal_twin_boltgun_details_ids"])
    assert [r["id"] for r in details if "双联爆弹枪" in json.dumps(r, ensure_ascii=False)] == [1265]
    inventory = json.loads(Path("db_sources/blacklibrary/units.json").read_text("utf-8"))
    bike = [r for r in inventory if _norm_en(r.get("unitEnglishName")) == "captainonbike"]
    assert bike == [evidence["inventory"]]
    # The named inventory listing exists, but is not an accepted full detail or
    # a reviewed empty-listing exclusion. A source gap is not proof of legality.
    assert reviewed_empty_listing(bike[0]) is None
    history = json.loads(Path("db_sources/blacklibrary/weapon_names_history.json").read_text("utf-8"))
    assert [r["guard"][0] for r in history["records"] if r["guard"][1] == "000002702"] == (
        evidence["history_weapon_ids"])
    with closing(sqlite3.connect(normal_language_db)) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(
            "SELECT w.*,u.faction_id,u.name_en AS unit_name_en FROM weapons w JOIN units u ON u.id=w.unit_id "
            "WHERE w.name_en='Hand flamer' AND w.name_zh IS NOT NULL ORDER BY w.id")]
        assert rows == evidence["hand_flame_rows"], "Changed source-backed ambiguity requires review"
        assert sorted({r["name_zh"] for r in rows}) == evidence["hand_flame_names"]


@needs_db
def test_real_card_api_keeps_exact_english_fallback_and_official_profiles(normal_language_db, monkeypatch):
    from fastapi.testclient import TestClient
    from web_api import main

    monkeypatch.setattr(main, "DB_PATH", normal_language_db)
    # No lifespan startup/model warmup or external server is needed for this
    # actual read-only route; close the client explicitly after paired requests.
    client = TestClient(main.app)
    try:
        responses = {lang: client.get("/codex/units/000002702", params={"lang": lang})
                     for lang in ("en", "zh")}
        assert all(r.status_code == 200 for r in responses.values())
        cards = {lang: response.json()["card"] for lang, response in responses.items()}
        for guard in LANGUAGE_ACCEPTANCE["fallback_weapons"]:
            en = next(w for w in cards["en"]["ranged"] if w["name"] == guard["name_en"])
            zh = next(w for w in cards["zh"]["ranged"] if w["name"] == guard["name_en"])
            assert {k: en[k] for k in ("range", "a", "skill", "s", "ap", "d")} == {
                k: zh[k] for k in ("range", "a", "skill", "s", "ap", "d")}
            assert [k["slug"] for k in en["kw"]] == [k["slug"] for k in zh["kw"]]
        assert cards["zh"]["nameZh"] == LANGUAGE_ACCEPTANCE["fallback_unit"]["name_zh"]
    finally:
        client.close()


@needs_db
@pytest.mark.parametrize("table,field,value", [
    ("units", "name_zh", None), ("units", "faction_id", "AoI"),
    ("units", "name_en", "Another Captain"), ("units", "keywords_json", "{}"),
    ("weapons", "id", "new-weapon-id"), ("weapons", "unit_id", "000001542"),
    ("weapons", "name_en", "Another flamer"), ("weapons", "range", "18"),
    ("weapons", "a", "D3"), ("weapons", "bs_ws", "2"), ("weapons", "s", "4"),
    ("weapons", "ap", "-1"), ("weapons", "d", "2"), ("weapons", "keywords_json", "[]"),
    ("weapons", "name_zh", "Guessed translation"),
])
def test_any_fallback_identity_or_profile_drift_reopens_review(
        normal_language_db, tmp_path, table, field, value):
    with closing(sqlite3.connect(normal_language_db)) as conn:
        _assert_current_name_coverage(conn)
    trial = tmp_path / "drift.sqlite"
    shutil.copy2(normal_language_db, trial)
    with closing(sqlite3.connect(trial)) as conn, conn:
        conn.execute(f"UPDATE {table} SET {field}=? WHERE id=?",
                     (value, "000002702" if table == "units" else "000002702_w4"))
        with pytest.raises(AssertionError):
            _assert_current_name_coverage(conn)


@needs_db
@pytest.mark.parametrize("table", ["units", "weapons"])
def test_every_unregistered_current_name_gap_fails(normal_language_db, tmp_path, table):
    with closing(sqlite3.connect(normal_language_db)) as conn:
        _assert_current_name_coverage(conn)
    trial = tmp_path / "new-gap.sqlite"
    shutil.copy2(normal_language_db, trial)
    with closing(sqlite3.connect(trial)) as conn, conn:
        # Blank a current unit that has an accepted name after normal stages.
        # 000001542 is a registered English fallback (Decision C unanswered),
        # so pick the first other current named unit by id.
        from db_compile.active_units import active_unit_ids
        current = active_unit_ids(conn)
        registered = {u["id"] for u in LANGUAGE_ACCEPTANCE["fallback_units"]}
        unit_id = next(r[0] for r in conn.execute(
            "SELECT id,name_zh FROM units WHERE trim(coalesce(name_zh,''))<>'' ORDER BY id")
            if r[0] in current and r[0] not in registered)
        conn.execute(f"UPDATE {table} SET name_zh=NULL WHERE id=?",
                     (unit_id if table == "units" else "000002702_w1",))
        with pytest.raises(AssertionError, match="Unregistered"):
            _assert_current_name_coverage(conn)


@needs_db
def test_all_current_weapon_keywords_localized():
    """现役武器的 USR 关键词也要全有中文——中英混排（[IGNORES COVER，手枪]）是半成品。"""
    import json as _json

    conn = sqlite3.connect(str(DB))
    from db_compile.active_units import active_unit_ids
    cur = active_unit_ids(conn)
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

    # 2026-07-26 起以 GW 官方简体中文为准：官方核心规则 24.03 写作「[针对载具 4+]」，
    # 此前按黑图多数派取的「反X」降为检索别名（宪法 §6 官方 > 汉化组）
    assert _rule_translate("ANTI-INFANTRY 2+") == "针对步兵2+"
    assert _rule_translate("ANTI-VEHICLE 4+") == "针对载具4+"
    assert _rule_translate("RAPID FIRE D6+3") == "速射D6+3"
    assert _rule_translate("MELTA 6") == "热熔6"
    assert _rule_translate("SUSTAINED HITS 3") == "连击3"
    # CLEAVE 走规则，译名取**官方**核心规则 24.06「[劈砍]」。
    # 曾按汉化组速查表定成「横扫」——官方与汉化组在这条上不一致，官方优先。
    assert _rule_translate("CLEAVE 1") == "劈砍1"
    assert _rule_translate("CLEAVE 2") == "劈砍2"
    assert _rule_translate("PISTOL") is None          # 非参数化的走学习/人工层


# ── 撞名护栏（防「看起来是中文的错译」）────────────────────────────

def _collision_db(tmp_path: Path) -> Path:
    """一把武器带自造关键词 TESTKW，黑图中文层却写「手枪」——
    学出来会与 PISTOL 的人工真源撞名，正是 HARPOONED→额外攻击 那类错配的形状。"""
    db = tmp_path / "c.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE units (id TEXT PRIMARY KEY, faction_id TEXT, "
                 "points_json TEXT)")
    conn.execute("CREATE TABLE weapons (id TEXT, unit_id TEXT, name_en TEXT, "
                 "name_zh TEXT, range TEXT, a TEXT, bs_ws TEXT, s TEXT, ap TEXT, "
                 "d TEXT, keywords_json TEXT)")
    conn.execute("CREATE TABLE unit_zh_detail (canonical_id TEXT PRIMARY KEY, "
                 "weapons_json TEXT)")
    conn.execute("INSERT INTO units VALUES ('U1','AS',NULL)")
    conn.execute("INSERT INTO weapons VALUES ('w1','U1','Odd gun',NULL,'12','1',"
                 "'3','4','0','1','[\"testkw\"]')")
    zh = {"射击武器": [
        {"name": "怪枪", "射程": "12", "攻击次数": "1", "命中": "3+",
         "造伤": "4", "破甲": "0", "伤害": "1", "skill": ["手枪"]},
    ]}
    conn.execute("INSERT INTO unit_zh_detail VALUES ('U1', ?)",
                 (json.dumps(zh, ensure_ascii=False),))
    conn.commit()
    conn.close()
    return db


def test_learned_value_colliding_with_authoritative_is_dropped(tmp_path):
    """单次观测学出的译名撞上人工真源 → 丢弃学习值，宁可显英文。

    留着它的后果比缺译更糟：用户看到一个**像模像样的中文词**，不会起疑。
    """
    db = _collision_db(tmp_path)
    build_zh_weapon_names(db)
    rep = build_keyword_glossary(db)
    assert ("TESTKW", "手枪") in rep["dropped_collisions"]
    conn = sqlite3.connect(str(db))
    gloss = dict(conn.execute("SELECT term_en, term_zh FROM zh_keyword_glossary"))
    conn.close()
    assert "TESTKW" not in gloss
    assert gloss["PISTOL"] == "手枪"          # 权威值留下


@needs_db
def test_glossary_has_no_duplicate_chinese_names():
    """一个中文名只能属于一个词条——重名意味着至少有一边是错的。"""
    conn = sqlite3.connect(str(DB))
    dupes = conn.execute(
        "SELECT term_zh, GROUP_CONCAT(term_en) FROM zh_keyword_glossary "
        "GROUP BY term_zh HAVING COUNT(*) > 1").fetchall()
    conn.close()
    assert not dupes, f"中文名撞车：{dupes}"


@needs_db
def test_keyword_names_follow_official_chinese():
    """译名以 **GW 官方简体中文**为准（data/官方中文/ 核心规则第 24 章）。

    宪法 §6：GW 官方中文 > 汉化组译名 > 社区译名。2026-07-26 拿到官方中文版后
    逐条核对：20 条与库内一致、1 条冲突——**CLEAVE 官方是「劈砍」不是「横扫」**
    （此前只有汉化组速查表可依据，取了「横扫」）。旧译名一律降为检索别名，
    不删除，所以搜哪个都找得到。
    """
    conn = sqlite3.connect(str(DB))
    gloss = dict(conn.execute("SELECT term_en, term_zh FROM zh_keyword_glossary"))
    conn.close()
    assert gloss.get("CLEAVE 1") == "劈砍1"            # 官方 24.06
    assert gloss.get("ANTI-VEHICLE 4+") == "针对载具4+"  # 官方 24.03
    assert gloss.get("CLOSE-QUARTERS") == "近距离"     # 官方 24.07
    assert gloss.get("EXTRA ATTACKS") == "额外攻击"    # 官方 24.11
    # 这三条曾被汉化组速查表判为「忽视掩体 / 迅猛冲锋 / 喷射」，
    # 官方核对下来**库内原值才是对的**——留成断言防止有人照速查表改回去
    assert gloss.get("IGNORES COVER") == "无视掩体"    # 官方 24.18
    assert gloss.get("LANCE") == "骑枪"               # 官方 24.21
    assert gloss.get("TORRENT") == "洪流"             # 官方 24.37
    assert gloss.get("HARPOONED") not in (None, "额外攻击")
