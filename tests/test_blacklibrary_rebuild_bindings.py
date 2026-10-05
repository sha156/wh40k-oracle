"""Frozen real source identities survive CSV rebuilds without old Chinese bridges."""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from db_compile.blacklibrary import populate_zh_details
from db_compile.build import build_database
from db_compile.update import UpdateConfig, stage_zh_details


CASES = json.loads((Path(__file__).parent / "fixtures/blacklibrary_rebuild_bindings.json")
                  .read_text("utf-8"))
IDS = [case["canonical"]["id"] for case in CASES]


@pytest.fixture
def rebuilt(tmp_path):
    csv = tmp_path / "csv"
    csv.mkdir()
    (csv / "Datasheets.csv").write_text(
        "id|name|faction_id|\n" + "".join(
            f"{c['id']}|{c['name_en']}|{c['faction_id']}|\n"
            for c in (case["canonical"] for case in CASES))
        + "000000847|Servitors|AdM|\n", encoding="utf-8")
    (csv / "Datasheets_keywords.csv").write_text(
        "datasheet_id|keyword|is_faction_keyword|\n" + "".join(
            f"{case['canonical']['id']}|{kw}|{str(group == 'faction_keywords').lower()}|\n"
            for case in CASES
            for group, keywords in case["canonical"]["canonical_keywords"].items()
            for kw in keywords), encoding="utf-8")
    db = tmp_path / "trial.sqlite"
    build_database(csv, db, terms_path=None)
    return db, csv


def content(db):
    with closing(sqlite3.connect(db)) as conn:
        return {name: conn.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
                for (name,) in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}


def projected(db):
    with closing(sqlite3.connect(db)) as conn:
        return dict(conn.execute("SELECT canonical_id, name_zh FROM unit_zh_detail"))


def test_exact_five_restore_on_clean_repeated_csv_build_and_real_update_stage(rebuilt, tmp_path):
    db, csv = rebuilt
    records = [deepcopy(case["record"]) for case in CASES]
    source_before = deepcopy(records)
    details = tmp_path / "details.json"
    details.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    inventory = tmp_path / "units.json"
    inventory.write_text("[]", encoding="utf-8")
    cfg = UpdateConfig(db=db, offline=True, blacklibrary_cache=inventory,
                       blacklibrary_details=details)
    for _ in range(2):
        build_database(csv, db, terms_path=None)
        before = content(db)
        assert all(row[3] is None for row in before["units"])
        assert stage_zh_details(cfg).ok
        expected = {case["canonical"]["id"]: case["record"]["name_zh"] for case in CASES}
        assert projected(db) == expected
        after = content(db)
        assert {row[0]: row[3] for row in after["units"] if row[3]} == expected
        # All canonical columns except the five language cells and every other
        # original table remain exact. The archive stage adds an empty table.
        assert [r[:3] + r[4:] for r in before["units"]] == [
            r[:3] + r[4:] for r in after["units"]]
        assert all(after[table] == rows for table, rows in before.items() if table != "units")
        once = content(db)
        populate_zh_details(db, records)
        assert content(db) == once
        # Real Windows replacement/rename requires the projection handles closed.
        renamed = db.with_name("renamed.sqlite")
        db.rename(renamed)
        renamed.rename(db)
    assert records == source_before


@pytest.mark.parametrize("case", CASES, ids=IDS)
@pytest.mark.parametrize("field,value", [
    ("id", 999999), ("id", True), ("name_en", "Drifted source"),
    ("name_zh", "Changed Chinese text"), ("faction_zh", "机械修会"),
    ("score", -1), ("detail", {"能力": [{"name": "Changed source"}]}),
    ("provenance", {"status": "verified_capture"}),
])
def test_source_drift_cannot_bypass_binding_through_old_name(rebuilt, case, field, value):
    db, _ = rebuilt
    changed = deepcopy(case["record"])
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET name_zh=? WHERE id=?",
                     (changed["name_zh"], case["canonical"]["id"]))
    changed[field] = value
    populate_zh_details(db, [changed])
    assert projected(db) == {}


@pytest.mark.parametrize("case", CASES, ids=IDS)
@pytest.mark.parametrize("field,value", [
    ("id", "wrong-id"), ("name_en", "Wrong canonical family"),
    ("faction_id", "AdM"), ("keywords_json", '{"faction_keywords":["Other chapter"]}'),
])
def test_canonical_drift_cannot_bypass_binding_through_old_name(rebuilt, case, field, value):
    db, _ = rebuilt
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET name_zh=? WHERE id=?",
                     (case["record"]["name_zh"], case["canonical"]["id"]))
        conn.execute(f"UPDATE units SET {field}=? WHERE id=?",
                     (value, case["canonical"]["id"]))
    populate_zh_details(db, [case["record"]])
    assert projected(db) == {}


@pytest.mark.parametrize("case", CASES, ids=IDS)
@pytest.mark.parametrize("field", ["manifest_sha256", "capture", "status", "authority", "fetched_at"])
def test_capture_provenance_drift_is_final_denial(rebuilt, case, field):
    db, _ = rebuilt
    changed = deepcopy(case["record"])
    changed["provenance"][field] = "changed"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET name_zh=? WHERE id=?",
                     (changed["name_zh"], case["canonical"]["id"]))
    populate_zh_details(db, [changed])
    assert projected(db) == {}


def test_gk_source_never_fans_out_to_adm_even_with_shared_chinese_name(rebuilt):
    db, _ = rebuilt
    case = next(c for c in CASES if c["record"]["id"] == 2863)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET name_zh=? WHERE id IN ('000000397','000000847')",
                     (case["record"]["name_zh"],))
    populate_zh_details(db, [case["record"]])
    assert projected(db) == {"000000397": case["record"]["name_zh"]}


def test_failed_projection_rolls_back_language_and_previous_detail_rows(rebuilt):
    db, _ = rebuilt
    records = [case["record"] for case in CASES]
    populate_zh_details(db, records)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET name_zh=NULL")
        conn.execute("CREATE TRIGGER deny_projection BEFORE INSERT ON unit_zh_detail "
                     "BEGIN SELECT RAISE(ABORT, 'injected projection failure'); END")
    before = content(db)
    with pytest.raises(sqlite3.IntegrityError, match="injected projection failure"):
        populate_zh_details(db, records)
    assert content(db) == before
    # The failure path also closes the actual connection.
    renamed = db.with_name("failed.sqlite")
    db.rename(renamed)
    renamed.rename(db)


def test_no_details_preserves_unrelated_language_and_tables(rebuilt):
    db, _ = rebuilt
    before = content(db)
    assert populate_zh_details(db, [])["matched"] == 0
    after = content(db)
    assert all(after[table] == rows for table, rows in before.items())
