"""Historical deleted-source evidence must never become a current unit or price."""
from __future__ import annotations

import copy
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import pytest

from db_compile.source_archive import find_archived_unit, project_deleted_details


def _record(source_id=6, **changes):
    record = {
        "id": source_id, "faction_zh": "极限战士",
        "name_zh": "马涅乌斯.卡尔加（已删除）", "name_en": "Marneus Calgar",
        "score": 200, "detail": {
            "简介": [{"type": "text", "content": [
                {"text": "马涅乌斯·卡尔加与两名荣胜卫队组成一个单位；200分", "style": ""}
            ]}],
            "能力": [{"name": "Historical ability", "text": "Source text"}],
        },
    }
    record.update(changes)
    return record


def _db(tmp_path):
    path = tmp_path / "archive.sqlite"
    with closing(sqlite3.connect(str(path))) as conn, conn:
        conn.execute("CREATE TABLE units(id TEXT PRIMARY KEY, name_en TEXT, points INTEGER)")
        conn.execute("INSERT INTO units VALUES(?,?,?)",
                     ("000004183", "Marneus Calgar in Armour of Antilochus", 155))
    return path


def _rows(db, table):
    with closing(sqlite3.connect(str(db))) as conn:
        return conn.execute("SELECT * FROM " + table).fetchall()


def test_projection_keeps_old_card_separate_from_current_variant_and_prices(tmp_path):
    db = _db(tmp_path)
    before = _rows(db, "units")
    deleted = _record()
    live = _record(4432, name_zh="身着安提洛库斯之铠的马涅乌斯·卡尔加",
                   name_en="Marneus Calgar in Armour of Antilochus", score=155)
    original = copy.deepcopy(deleted)
    report = project_deleted_details(db, details=[deleted, live])
    assert report["records"] == 2
    assert report["archived"] == report["ignored"] == 1
    result = find_archived_unit(db, "普通卡尔加")
    assert result["archive_id"] == "blacklibrary:6"
    assert result["historical_points"] == 200 and result["is_current"] is False
    assert result["status"] == "historical_source_only"
    assert result["authority"] == "third_party_deleted_record"
    assert result["raw"] == original == deleted
    assert "第三方历史资料" in result["source_scope"]
    assert "不是官方现行兵牌" in result["source_scope"]
    scope = result["identity_scope"]
    assert scope["evidence_kind"] == "retained_source_unit_composition"
    assert "两名荣胜卫队" in scope["composition_evidence"]
    assert scope["model_counts"] == {"calgar": 1, "guard_models": 2}
    assert "不是把安提洛库斯之铠版本混在一起" in scope["variant_boundary"]
    assert "points" not in result and "canonical_id" not in result
    assert find_archived_unit(db, "Marneus Calgar in Armour of Antilochus") is None
    assert _rows(db, "units") == before


@pytest.mark.parametrize("query", [
    "卡尔加", "普通卡尔加", "Marneus Calgar", "ordinary Marneus Calgar",
    "马涅乌斯·卡尔加", "马涅乌斯.卡尔加（已删除）", " MARNEUS  CALGAR ",
])
def test_exact_names_and_verified_aliases_resolve(query, tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record()])
    assert find_archived_unit(db, query)["source_id"] == "6"


@pytest.mark.parametrize("query", [
    "卡尔", "Calgar", "Marneus Calga", "Armour of Antilochus", "重甲卡尔加",
    "Marneus Calgar in Armour of Antilochus", "ordinary Marneus Calgar in Armour",
])
def test_no_substring_or_fuzzy_guessing(query, tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record()])
    assert find_archived_unit(db, query) is None


@pytest.mark.parametrize("changes", [
    {"id": 999}, {"name_en": "Marneus Calgar in Armour of Antilochus"},
    {"name_zh": "安提洛库斯之铠卡尔加（已删除）"}, {"faction_zh": "Different faction"},
])
def test_short_aliases_require_the_verified_source_identity(changes, tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record(**changes)])
    assert find_archived_unit(db, "卡尔加") is None
    assert find_archived_unit(db, "ordinary Marneus Calgar") is None


@pytest.mark.parametrize("detail", [
    {},
    {"简介": [{"type": "text", "content": [{"text": "卡尔加是一名传奇英雄"}]}]},
    {"简介": [{"type": "text", "content": [{"text": "卡尔加与常胜护卫组成单位"}]}]},
    {"简介": [{"type": "text", "content": [{"text": "卡尔加不能与两名常胜护卫组成一个单位。"}]}]},
    {"简介": [{"type": "text", "content": [{"text": "卡尔加与两名常胜护卫不能组成一个单位。"}]}]},
    {"简介": [{"type": "text", "content": [{"text": "不允许卡尔加与两名常胜护卫组成一个单位。"}]}]},
    {"简介": [{"type": "text", "content": [{"text": "卡尔加发动攻击，摧毁两名常胜护卫后可以继续移动。"}]}]},
    {"简介": [{"type": "text", "content": [{"text": "卡尔加与12名常胜护卫组成一个单位。"}]}]},
])
def test_identity_scope_requires_explicit_two_guard_composition(detail, tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record(detail=detail)])
    result = find_archived_unit(db, "普通卡尔加")
    assert result["historical_points"] == 200
    assert "identity_scope" not in result


def test_english_composition_field_must_be_affirmative(tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record(
        detail={},
        composition="Marneus Calgar cannot be fielded with two Victrix Honour Guard",
    )])
    assert "identity_scope" not in find_archived_unit(db, "普通卡尔加")


def test_identity_scope_returns_the_matched_sentence_from_long_source_text(tmp_path):
    db = _db(tmp_path)
    sentence = "卡尔加与两名常胜护卫组成一个单位"
    detail = {"简介": [{"type": "text", "content": [{"text": "背景" * 200 + sentence}]}]}
    project_deleted_details(db, details=[_record(detail=detail)])
    evidence = find_archived_unit(db, "普通卡尔加")["identity_scope"]["composition_evidence"]
    assert evidence == sentence


def test_identity_scope_requires_the_verified_archive_identity(tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record(source_id=7)])
    result = find_archived_unit(db, "马涅乌斯·卡尔加")
    assert result["historical_points"] == 200
    assert "identity_scope" not in result


def test_normalized_name_collisions_return_no_guess(tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record(), _record(7)])
    assert find_archived_unit(db, "Marneus Calgar") is None


def test_only_explicit_deleted_markers_are_archived(tmp_path):
    db = _db(tmp_path)
    report = project_deleted_details(db, details=[
        _record(name_zh="马涅乌斯.卡尔加"),
        _record(7, name_zh="已删除单位的规则说明"),
        _record(8, name_zh="Not a deletion annotation"),
    ])
    assert report["archived"] == 0
    assert find_archived_unit(db, "卡尔加") is None


def test_missing_cache_or_database_does_not_create_files_or_erase_archive(tmp_path):
    missing_db = tmp_path / "absent.sqlite"
    assert find_archived_unit(missing_db, "卡尔加") is None
    assert project_deleted_details(missing_db, details=[_record()])["status"] == "missing_database"
    assert not missing_db.exists()
    db = _db(tmp_path)
    assert find_archived_unit(db, "卡尔加") is None  # Missing table is normal on older DBs.
    project_deleted_details(db, details=[_record()])
    before = _rows(db, "source_archived_units")
    report = project_deleted_details(db, cache_path=tmp_path / "missing.json")
    assert report["status"] == "missing_cache"
    assert _rows(db, "source_archived_units") == before


def test_repeated_projection_is_idempotent_and_cache_time_is_not_a_rule_date(tmp_path):
    db = _db(tmp_path)
    cache = tmp_path / "details.json"
    cache.write_text(json.dumps([_record()], ensure_ascii=False), encoding="utf-8")
    stamp = 1_700_000_000
    os.utime(cache, (stamp, stamp))
    first = project_deleted_details(db, cache_path=cache)
    before = _rows(db, "source_archived_units")
    second = project_deleted_details(db, cache_path=cache)
    assert first == second and _rows(db, "source_archived_units") == before
    found = find_archived_unit(db, "卡尔加")
    assert found["cached_at"] == datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat()
    assert found["cache_timestamp_kind"] == "file_mtime"
    assert "不是规则发布日期" in found["source_scope"]
    # A later listing no longer containing a deleted card is not evidence to erase it.
    assert project_deleted_details(db, details=[])["total_archived"] == 1
    assert _rows(db, "source_archived_units") == before


def test_failed_batch_rolls_back_prior_upsert(tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record()])
    before = _rows(db, "source_archived_units")
    with closing(sqlite3.connect(str(db))) as conn, conn:
        conn.execute("""CREATE TRIGGER reject_source_8 BEFORE INSERT ON source_archived_units
                        WHEN NEW.source_id='8' BEGIN SELECT RAISE(ABORT, 'test rejection'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="test rejection"):
        project_deleted_details(db, details=[_record(score=999), _record(8, name_en="Captain Sicarius")])
    assert _rows(db, "source_archived_units") == before
    assert _rows(db, "units")[0][2] == 155


def test_malformed_duplicate_cache_is_rejected_before_any_changes(tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record()])
    before = _rows(db, "source_archived_units")
    with pytest.raises(ValueError, match="Duplicate"):
        project_deleted_details(db, details=[_record(score=333), _record()])
    with pytest.raises(ValueError, match="stable source id"):
        project_deleted_details(db, details=[_record(id=None)])
    assert _rows(db, "source_archived_units") == before


def test_non_numeric_score_is_not_promoted_to_a_price(tmp_path):
    db = _db(tmp_path)
    project_deleted_details(db, details=[_record(score="200 including options")])
    found = find_archived_unit(db, "卡尔加")
    assert found["historical_points"] is None
    assert found["raw"]["score"] == "200 including options"


def test_stage_zh_details_restores_the_archive_from_cache(tmp_path, monkeypatch):
    from db_compile import blacklibrary
    from db_compile.update import UpdateConfig, _RESTORE_STAGES, stage_zh_details

    db = _db(tmp_path)
    cache = tmp_path / "details.json"
    cache.write_text(json.dumps([_record()], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(blacklibrary, "load_or_fetch_units", lambda *args, **kwargs: ([], "offline"))
    monkeypatch.setattr(blacklibrary, "apply_unit_name_overrides", lambda *args: {"filled": 0})
    monkeypatch.setattr(blacklibrary, "populate_zh_details", lambda *args: {"matched": 0, "unmatched": 1})
    result = stage_zh_details(UpdateConfig(db=db, blacklibrary_details=cache, offline=True))
    assert result.detail["source_archive"]["archived"] == 1
    assert "非现行兵牌/点数" in result.summary
    assert stage_zh_details in [stage[1] for stage in _RESTORE_STAGES]
    assert find_archived_unit(db, "卡尔加")["historical_points"] == 200
    assert _rows(db, "units")[0][2] == 155


def _rebuild_csv(tmp_path):
    source = tmp_path / "csv"
    source.mkdir()
    (source / "Factions.csv").write_text("id|name|link|\nSM|Space Marines||\n", encoding="utf-8")
    fields = ("id", "name", "faction_id", "source_id", "legend", "role", "loadout",
              "transport", "virtual", "leader_head", "leader_footer", "damaged_w",
              "damaged_description", "link")
    values = ("000004183", "Marneus Calgar in Armour of Antilochus", "SM", "1") + ("",) * 10
    (source / "Datasheets.csv").write_text(
        "|".join(fields) + "|\n" + "|".join(values) + "|\n", encoding="utf-8")
    return source


def test_atomic_rebuild_preserves_archive_even_when_later_cache_omits_it(tmp_path):
    from db_compile.build import build_database

    db = _db(tmp_path)
    cache = tmp_path / "details.json"
    cache.write_text(json.dumps([_record()], ensure_ascii=False), encoding="utf-8")
    os.utime(cache, (1_700_000_000, 1_700_000_000))
    project_deleted_details(db, cache_path=cache)
    before = _rows(db, "source_archived_units")
    with closing(sqlite3.connect(str(db))) as conn, conn:
        conn.execute("CREATE TABLE unrelated_local_data(value TEXT)")
        conn.execute("INSERT INTO unrelated_local_data VALUES('do not copy')")
    source = _rebuild_csv(tmp_path)
    report = build_database(source, db)
    assert report.unreconciled() == {}
    assert report.row_counts["source_archived_units"] == 1
    cache.write_text("[]", encoding="utf-8")
    project_deleted_details(db, cache_path=cache)
    assert find_archived_unit(db, "普通卡尔加")["historical_points"] == 200
    assert _rows(db, "source_archived_units") == before
    with closing(sqlite3.connect(str(db))) as conn:
        assert conn.execute("SELECT COUNT(*) FROM units").fetchone()[0] == 1
        assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='unrelated_local_data'").fetchone() is None


@pytest.mark.parametrize("column,value", [
    ("historical_points", 999),
    ("name_zh", "马涅乌斯.卡尔加"),
    ("raw_json", "not valid json"),
])
def test_invalid_archive_aborts_rebuild_without_replacing_original_database(tmp_path, column, value):
    from db_compile.build import build_database

    db = _db(tmp_path)
    project_deleted_details(db, details=[_record()])
    with closing(sqlite3.connect(str(db))) as conn, conn:
        conn.execute("UPDATE source_archived_units SET " + column + "=?", (value,))
    before = db.read_bytes()
    with pytest.raises(ValueError, match="Archived source record"):
        build_database(_rebuild_csv(tmp_path), db)
    assert db.read_bytes() == before
    assert not db.with_suffix(".tmp.sqlite").exists()
