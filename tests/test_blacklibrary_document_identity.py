"""New retrieval documents retain the actual projection's source identity."""
from contextlib import closing
from copy import deepcopy
import sqlite3

import pytest

from db_compile.blacklibrary import build_blacklibrary_docs, populate_zh_details
from tests.test_blacklibrary_rebuild_bindings import CASES, rebuilt, content


def test_real_five_sources_render_exact_identities_once_without_adm(rebuilt):
    db, _ = rebuilt
    records = [deepcopy(c["record"]) for c in CASES]
    populate_zh_details(db, records)
    before = content(db)
    docs = build_blacklibrary_docs(db)
    assert len(docs) == 5
    by_id = {d.metadata["canonical_id"]: d for d in docs}
    assert "000000847" not in by_id
    for case in CASES:
        canonical, source = case["canonical"], case["record"]
        doc = by_id[canonical["id"]]
        assert doc.metadata["source_id"] == str(source["id"])
        assert doc.metadata["source_name_en"] == source["name_en"]
        assert doc.metadata["source_faction_zh"] == source["faction_zh"]
        assert doc.metadata["canonical_name_en"] == canonical["name_en"]
        assert doc.metadata["faction_id"] == canonical["faction_id"]
        assert doc.metadata["source"] == "blacklibrary"
    gk = by_id["000000397"]
    assert "所属：灰骑士" in gk.page_content
    assert gk.metadata["source_id"] == "2863" and gk.metadata["faction_id"] == "GK"
    assert content(db) == before
    assert build_blacklibrary_docs(db) == docs
    renamed = db.with_name("rendered.sqlite")
    db.rename(renamed)
    renamed.rename(db)


@pytest.mark.parametrize("field,value", [("name_en", "Wrong identity"), ("faction_id", "AdM")])
def test_canonical_drift_after_projection_refuses_document(rebuilt, field, value):
    db, _ = rebuilt
    populate_zh_details(db, [c["record"] for c in CASES])
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute(f"UPDATE units SET {field}=? WHERE id='000000397'", (value,))
    before = content(db)
    with pytest.raises(ValueError, match="Black Library document identity"):
        build_blacklibrary_docs(db)
    assert content(db) == before
    renamed = db.with_name("rejected.sqlite")
    db.rename(renamed)
    renamed.rename(db)


def test_legacy_projection_requires_repopulation_without_guessing_source_id(rebuilt):
    db, _ = rebuilt
    populate_zh_details(db, [c["record"] for c in CASES])
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("DROP TABLE blacklibrary_detail_identity")
    before = db.read_bytes()
    with pytest.raises(ValueError, match="repopulate"):
        build_blacklibrary_docs(db)
    assert db.read_bytes() == before
    populate_zh_details(db, [c["record"] for c in CASES])
    assert len(build_blacklibrary_docs(db)) == 5


def test_identity_writes_rollback_with_projection_failure(rebuilt):
    db, _ = rebuilt
    records = [c["record"] for c in CASES]
    populate_zh_details(db, records)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TRIGGER deny_identity BEFORE INSERT ON blacklibrary_detail_identity "
                     "BEGIN SELECT RAISE(ABORT, 'identity failure'); END")
    before = content(db)
    with pytest.raises(sqlite3.IntegrityError, match="identity failure"):
        populate_zh_details(db, records)
    assert content(db) == before


@pytest.mark.parametrize("source_id", [None, True, ""])
def test_unattributed_new_record_does_not_invent_source_identity(rebuilt, source_id):
    db, _ = rebuilt
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("INSERT INTO units (id,name_en,faction_id,keywords_json) "
                     "VALUES ('other','Other unit','GK','{}')")
    populate_zh_details(db, [{"id": source_id, "name_en": "Other unit", "name_zh": "Other",
                             "faction_zh": "GK", "detail": {"能力": [{"name": "Rule"}]}}])
    with pytest.raises(ValueError, match="Black Library document identity"):
        build_blacklibrary_docs(db)


def test_first_identity_schema_creation_rolls_back_on_projection_failure(rebuilt):
    db, _ = rebuilt
    records = [c["record"] for c in CASES]
    populate_zh_details(db, records)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("DROP TABLE blacklibrary_detail_identity")
        conn.execute("CREATE TRIGGER deny_details BEFORE INSERT ON unit_zh_detail "
                     "BEGIN SELECT RAISE(ABORT, 'detail failure'); END")
    before = content(db)
    with pytest.raises(sqlite3.IntegrityError, match="detail failure"):
        populate_zh_details(db, records)
    assert content(db) == before


def test_empty_projection_clears_identity_rows_idempotently(rebuilt):
    db, _ = rebuilt
    populate_zh_details(db, [c["record"] for c in CASES])
    populate_zh_details(db, [])
    before = content(db)
    assert before["blacklibrary_detail_identity"] == []
    assert build_blacklibrary_docs(db) == []
    populate_zh_details(db, [])
    assert content(db) == before
