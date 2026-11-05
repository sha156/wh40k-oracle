"""Accepted detail identities without a source-bound inventory name (Decision C pending).

Decision C (restore empty units.name_zh from an already accepted detail) is
unanswered, so populate_zh_details keeps its source-bound-only name rule.
The saved guard patch is under host/finish/R4/decision-C-guard.patch.
"""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from db_compile.blacklibrary import populate_zh_details
from db_compile.update import UpdateConfig, stage_zh_details


FROZEN = json.loads((Path(__file__).parent / "fixtures/chinese_name_recovery.json")
                    .read_text("utf-8"))["recovery"]
CID = FROZEN["canonical"]["id"]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "copy.sqlite"
    row = FROZEN["canonical"]
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE units (id TEXT PRIMARY KEY, faction_id TEXT, "
                     "name_en TEXT, name_zh TEXT, points_json TEXT, keywords_json TEXT, version TEXT)")
        conn.execute("INSERT INTO units VALUES (?,?,?,?,?,?,?)", tuple(row.values()))
        conn.execute("CREATE TABLE official_sentinel (value TEXT)")
        conn.execute("INSERT INTO official_sentinel VALUES ('unchanged official evidence')")
    return path


def contents(path):
    with closing(sqlite3.connect(path)) as conn:
        return {name: conn.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
                for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


@pytest.mark.parametrize("old_name", [None, "", "Supplied Chinese name", " "])
def test_accepted_detail_without_bound_inventory_leaves_name_unchanged(db, old_name):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET name_zh=?", (old_name,))
    before = contents(db)
    records = [deepcopy(FROZEN["record"])]
    original = deepcopy(records)
    assert populate_zh_details(db, records)["matched"] == 1
    after = contents(db)
    assert after["units"][0][3] == old_name  # Decision C pending: no empty-cell restore
    assert after["unit_zh_detail"][0][0:2] == (CID, records[0]["name_zh"])
    assert after["blacklibrary_detail_identity"] == [
        (CID, "464", "RUKKATRUKK SQUIGBUGGY", "欧克蛮人", "Rukkatrukk Squigbuggy", "ORK")]
    assert before["units"][0][:3] + before["units"][0][4:] == (
        after["units"][0][:3] + after["units"][0][4:])
    assert before["official_sentinel"] == after["official_sentinel"]
    populate_zh_details(db, records)
    assert contents(db) == after
    assert records == original


def test_normal_stage_uses_retained_detail_when_plural_inventory_cannot_fill_name(db, tmp_path):
    inventory, details = tmp_path / "units.json", tmp_path / "details.json"
    inventory.write_text(json.dumps([FROZEN["new_inventory"]], ensure_ascii=False), "utf-8")
    details.write_text(json.dumps([FROZEN["record"]], ensure_ascii=False), "utf-8")
    cfg = UpdateConfig(db=db, offline=True, blacklibrary_cache=inventory,
                       blacklibrary_details=details)
    result = stage_zh_details(cfg)
    assert result.ok
    assert result.detail["name_zh_filled"] == 0  # The inventory matcher remains unchanged.
    assert result.detail["matched"] == 1
    assert contents(db)["units"][0][3] is None  # Decision C pending; registered fallback


@pytest.mark.parametrize("change", ["no_body", "wrong_english", "plural_english"])
def test_unaccepted_detail_cannot_restore_name(db, change):
    record = deepcopy(FROZEN["record"])
    if change == "no_body":
        record["detail"] = None
    else:
        record["name_en"] = "Another unit" if change == "wrong_english" else "RUKKATRUKK SQUIGBUGGIES"
    before = contents(db)
    populate_zh_details(db, [record])
    after = contents(db)
    assert after["units"] == before["units"]
    assert after["unit_zh_detail"] == []


@pytest.mark.parametrize("source_name", [None, "", "   "])
def test_accepted_detail_without_display_name_does_not_fill_empty_cell(db, source_name):
    record = deepcopy(FROZEN["record"])
    record["name_zh"] = source_name
    assert populate_zh_details(db, [record])["matched"] == 1
    assert contents(db)["units"][0][3] is None


def test_projection_failure_rolls_back_restored_name_and_existing_details(db):
    populate_zh_details(db, [FROZEN["record"]])
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET name_zh=NULL")
        conn.execute("CREATE TRIGGER reject_detail BEFORE INSERT ON unit_zh_detail "
                     "BEGIN SELECT RAISE(ABORT, 'name projection rollback'); END")
    before = contents(db)
    with pytest.raises(sqlite3.IntegrityError, match="name projection rollback"):
        populate_zh_details(db, [FROZEN["record"]])
    assert contents(db) == before
    renamed = db.with_name("closed.sqlite")
    db.rename(renamed)  # Verify Windows handles are closed on the failure path.
    renamed.rename(db)
