"""Faction ownership checks use temporary data and do not invent ally permissions."""
import json
import sqlite3

import pytest

from engines.roster import Roster, RosterUnit, validate
from engines.roster.contracts import ERROR, WARN


@pytest.fixture
def faction_db(tmp_path):
    db = tmp_path / "roster.sqlite"
    with sqlite3.connect(str(db)) as conn:
        conn.executescript("""
            CREATE TABLE factions(id TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE units(id TEXT PRIMARY KEY, faction_id TEXT, name_en TEXT,
                               points_json TEXT, keywords_json TEXT);
            CREATE TABLE enhancements(id TEXT, faction_id TEXT, detachment_id TEXT,
                                      detachment_name TEXT, name TEXT, cost INTEGER);
            INSERT INTO factions VALUES('SM','Space Marines'),('ORK','Orks');
            INSERT INTO enhancements VALUES('e1','SM','sm-det','SM Detachment','SM Enhancement',10);
            INSERT INTO enhancements VALUES('e2','ORK','ork-det','Ork Detachment','Ork Enhancement',10);
        """)
        for uid, faction, name, keywords in [
            ("captain", "SM", "Captain", ["CHARACTER"]),
            ("boy", "ORK", "Boy", []),
            ("shared-copy", "SM", "Faction-specific allied copy", []),
            ("missing-owner", None, "Missing owner", []),
        ]:
            conn.execute("INSERT INTO units VALUES(?,?,?,?,?)", (
                uid, faction, name,
                json.dumps({"items": [{"desc": "1 model", "cost": 100}]}),
                json.dumps({"keywords": keywords}),
            ))
    return db


def roster(faction="SM", detachment="sm-det", extra=()):
    return Roster(faction, detachment, "strike_force", (
        RosterUnit("captain", "Captain", 1, is_warlord=True), *extra))


def test_unknown_faction_is_an_error(faction_db):
    report = validate(faction_db, roster(faction="unrecognized", detachment=None))
    assert not report.legal
    issue = next(i for i in report.issues if i.code == "unknown_faction")
    assert issue.severity == ERROR


def test_known_detachment_must_belong_to_selected_faction(faction_db):
    report = validate(faction_db, roster(detachment="ork-det"))
    assert not report.legal
    assert any(i.code == "detachment_wrong_faction" and i.severity == ERROR
               for i in report.issues)


def test_unknown_detachment_is_unverified_not_silently_accepted(faction_db):
    report = validate(faction_db, roster(detachment="missing"))
    issue = next(i for i in report.issues if i.code == "detachment_unverified")
    assert issue.severity == WARN and issue.surfaced_only


@pytest.mark.parametrize("uid", ["boy", "missing-owner"])
def test_cross_faction_or_missing_ownership_requires_compatibility_review(faction_db, uid):
    report = validate(faction_db, roster(extra=(RosterUnit(uid, "Untrusted label", 1),)))
    issue = next(i for i in report.issues if i.code == "faction_compatibility_unverified")
    assert issue.severity == WARN and issue.surfaced_only
    assert "未校验" in issue.message
    assert "Untrusted label" not in issue.message
    # Existing contract: legal means no proven errors, not complete verification.
    assert report.legal and not report.errors


def test_same_faction_records_and_canonical_allied_copies_remain_valid(faction_db):
    report = validate(faction_db, roster(extra=(RosterUnit("shared-copy", "Shared", 1),)))
    assert report.legal and report.issues == ()
    assert report.total_points == 200


def test_unknown_unit_keeps_existing_missing_unit_disclosure(faction_db):
    report = validate(faction_db, roster(extra=(RosterUnit("unknown", "Unknown", 1),)))
    assert any(i.code == "unit_not_found" for i in report.issues)
    assert not any(i.code == "faction_compatibility_unverified" for i in report.issues)


@pytest.mark.parametrize("has_current_enhancement", [False, True])
def test_removed_enhancement_is_not_offered_or_priced_as_current(
        faction_db, has_current_enhancement):
    from db_compile.enhancements import list_for_detachment
    from web_api.roster import list_enhancements

    with sqlite3.connect(str(faction_db)) as conn:
        conn.execute("ALTER TABLE enhancements ADD COLUMN fp_status TEXT")
        conn.execute("UPDATE enhancements SET fp_status='removed_11e' WHERE id='e1'")
        if has_current_enhancement:
            conn.execute("INSERT INTO enhancements VALUES"
                         "('e3','SM','sm-det','SM Detachment','Current Enhancement',20,NULL)")

    expected = ([{"id": "e3", "name": "Current Enhancement", "cost": 20}]
                if has_current_enhancement else [])
    assert list_for_detachment(faction_db, "sm-det") == expected
    assert list_enhancements(faction_db, "sm-det") == expected
    enhanced = Roster("SM", "sm-det", "strike_force", (
        RosterUnit("captain", "Captain", 1, is_warlord=True,
                   enhancement="SM Enhancement"),))
    report = validate(faction_db, enhanced)
    assert not report.legal
    assert report.total_points == 100  # Retired prices must not count as current.
    assert any(i.code == "enh_wrong_detachment" and i.severity == ERROR
               for i in report.issues)
    assert any(i.code == "enh_unpriced" and i.surfaced_only for i in report.issues)
    assert not any(i.code == "enh_unverified" for i in report.issues)


def test_legacy_enhancement_schema_keeps_known_selection_and_price(faction_db):
    from db_compile.enhancements import list_for_detachment

    assert list_for_detachment(faction_db, "sm-det") == [
        {"id": "e1", "name": "SM Enhancement", "cost": 10}]
    report = validate(faction_db, Roster("SM", "sm-det", "strike_force", (
        RosterUnit("captain", "Captain", 1, is_warlord=True,
                   enhancement="SM Enhancement"),)))
    assert report.legal and report.total_points == 110
