"""Reviewed translations must stay consistent across stored projections and consumers."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from db_compile.blacklibrary import (build_blacklibrary_docs, load_zh_detail,
                                     populate_zh_details)
from web_api.entity_card import _abilities
from wiki_engine.from_db import render_unit


def database(tmp_path, units, abilities=()):
    db = tmp_path / "projection.sqlite"
    with sqlite3.connect(db) as c:
        c.executescript(
            "CREATE TABLE units(id TEXT PRIMARY KEY,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT);"
            "CREATE TABLE abilities(owner_id TEXT,scope TEXT,name_en TEXT,name_zh TEXT,text_zh TEXT);"
            "CREATE TABLE models(unit_id TEXT,name TEXT,m TEXT,t TEXT,sv TEXT,invuln TEXT,w TEXT,ld TEXT,oc TEXT);"
            "CREATE TABLE weapons(unit_id TEXT,name_en TEXT,name_zh TEXT,range TEXT,a TEXT,bs_ws TEXT,s TEXT,ap TEXT,d TEXT,keywords_json TEXT);")
        c.executemany("INSERT INTO units VALUES (?,?,?,?,'{}','{}',NULL)", units)
        c.executemany("INSERT INTO abilities VALUES (?,'',?,NULL,?)", abilities)
    return db


@pytest.fixture
def guilliman(tmp_path):
    source = json.loads((Path(__file__).with_name("fixtures") /
                         "reviewed_guilliman_abilities.json").read_text("utf-8"))
    uid = source["unit_id"]
    db = database(tmp_path, [(uid, "SM", "Roboute Guilliman", "罗伯特.基里曼")],
                  [(uid, a["name_en"], a["text"]) for a in source["english_abilities"]])
    populate_zh_details(db, [{"id": 24, "name_en": "ROBOUTE GUILLIMAN",
                            "name_zh": "罗伯特.基里曼", "faction_zh": "极限战士",
                            "detail": {"能力": source["chinese_abilities"]}}])
    return db, source


def test_reviewed_card_agent_and_wiki_preserve_all_seven(guilliman):
    db, source = guilliman
    before = db.read_bytes()
    zh = load_zh_detail(db, source["unit_id"])
    entries = zh["能力"]
    assert len(entries) == 7
    assert [e["canonical_name_en"] for e in entries] == [a["name_en"] for a in source["english_abilities"]]
    card = _abilities(zh, source["english_abilities"])
    assert len(card) == 7 and card[0].name == "圣典权威"
    assert card[3].tag == card[6].tag == "官方英文"
    assert "Once per battle round" in card[6].text
    assert all("".join(s.s if s.t == "text" else s.kw.text for s in a.rich) == a.text for a in card)
    with sqlite3.connect(db) as c:
        page, _ = render_unit(c, source["unit_id"], "星际战士")
    assert "圣典权威" in page.body and "战争之主" in page.body
    assert "SUPREME COMMANDER" in page.body and "Once per battle round" in page.body
    assert "每个回合一次" not in page.body
    assert db.read_bytes() == before


def test_blacklibrary_chunk_contains_only_its_verified_chinese(guilliman):
    db, _ = guilliman
    docs = build_blacklibrary_docs(db)
    assert len(docs) == 1 and docs[0].metadata["book"] == "黑图书馆"
    text = docs[0].page_content
    assert "圣典权威" in text and "战争之主" in text
    assert "每个回合一次" not in text and "体形适中" not in text
    assert "Supreme Strategist" not in text and "SUPREME COMMANDER" not in text


def test_whole_unit_freshness_guard_wins_over_reviewed_mapping(guilliman):
    db, source = guilliman
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE official_rule_revisions(unit_id TEXT,source_date TEXT)")
        c.execute("INSERT INTO official_rule_revisions VALUES (?,'2026-09-30')", (source["unit_id"],))
    assert load_zh_detail(db, source["unit_id"])["能力"] is None
    assert build_blacklibrary_docs(db) == []
    with sqlite3.connect(db) as c:
        page, _ = render_unit(c, source["unit_id"], "星际战士")
    assert "Author of the Codex" in page.body and "圣典权威" not in page.body


def test_new_official_ability_survives_every_display(guilliman):
    db, source = guilliman
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO abilities VALUES (?,'','New official rule',NULL,'New rule body.')", (source["unit_id"],))
    entries = load_zh_detail(db, source["unit_id"])["能力"]
    assert len(entries) == 8 and all(e["source"] == "official-db" for e in entries)
    assert entries[-1]["name"] == "New official rule"
    with sqlite3.connect(db) as c:
        page, _ = render_unit(c, source["unit_id"], "星际战士")
    assert "New rule body." in page.body and "圣典权威" not in page.body
    assert "New rule body." not in build_blacklibrary_docs(db)[0].page_content


@pytest.mark.parametrize("reverse", [False, True])
def test_population_scopes_same_named_factions_before_any_overwrite(tmp_path, reverse):
    specs = [
        (577, "MINISTORUM PRIEST", "修女会", "000001553", "AS"),
        (122, "WATCH CAPTAIN ARTEMIS", "死亡守望", "000003872", "SM"),
        (121, "WATCH MASTER", "死亡守望", "000003871", "SM"),
        (238, "LORD OF CHANGE", "混沌恶魔", "000001120", "CD"),
        (992, "Ministorum Priest", "帝国特勤", "000003812", "AoI"),
        (1001, "Watch Captain Artemis", "帝国特勤", "000003814", "AoI"),
        (1002, "Watch Master", "帝国特勤", "000003815", "AoI"),
        (1094, "LORD OF CHANGE", "闪耀军团", "000004124", "TS"),
    ]
    units = [(uid, fac, en, "中文名" + uid) for _, en, _, uid, fac in specs]
    units.append(("000001394", "AM", "Ministorum Priest", "AM Priest"))
    db = database(tmp_path, units)
    records = [{"id": sid, "name_en": en, "name_zh": "中文名" + uid,
                "faction_zh": faction, "detail": {"能力": [{"name": faction + " rule"}]},
                "provenance": {"status": "retained_previous_cache" if sid in {992, 1001, 1002, 1094} else "verified_capture"}}
               for sid, en, faction, uid, _ in specs]
    if reverse:
        records.reverse()
    before = records.copy()
    report = populate_zh_details(db, records)
    assert report["matched"] == 4 and report["identity_rejected"] == 4
    with sqlite3.connect(db) as c:
        assert dict(c.execute("SELECT canonical_id,faction_zh FROM unit_zh_detail")) == {
            uid: faction for _, _, faction, uid, _ in specs[:4]}
        assert c.execute("SELECT COUNT(*) FROM units").fetchone()[0] == 9
    assert records == before
