import json
import sqlite3

import pytest

from db_compile.update import UpdateConfig, stage_aliases_blackforum


def fixture(tmp_path):
    db = tmp_path / "test.sqlite"
    with sqlite3.connect(str(db)) as conn:
        conn.execute("CREATE TABLE units (id TEXT PRIMARY KEY, name_en TEXT)")
        conn.executemany("INSERT INTO units VALUES (?,?)", [("sm", "Predator"), ("cs", "Chaos Predator")])
        conn.execute("CREATE TABLE aliases (alias TEXT, canonical_id TEXT, lang TEXT, source TEXT, PRIMARY KEY(alias,lang,source))")
    cache = tmp_path / "units.json"
    cache.write_text(json.dumps([{"unitName": "坦克", "unitEnglishName": "Chaos Predator"},
                                 {"unitName": "混沌坦克", "unitEnglishName": "Chaos Predator"}]), encoding="utf-8")
    return UpdateConfig(db=db, blacklibrary_cache=cache, offline=True)


def test_history_restores_old_alias_without_silently_retargeting(tmp_path):
    cfg = fixture(tmp_path)
    (tmp_path / "aliases_history.json").write_text(json.dumps({"pairs": [["坦克", "Predator"], ["旧译名", "Predator"]]}), encoding="utf-8")
    result = stage_aliases_blackforum(cfg)
    with sqlite3.connect(str(cfg.db)) as conn:
        assert dict(conn.execute("SELECT alias,canonical_id FROM aliases")) == {
            "坦克": "sm", "旧译名": "sm", "混沌坦克": "cs"}
    assert result.detail["matched"] == 3 and result.detail["collided"] == 1
    assert stage_aliases_blackforum(cfg).detail == result.detail


def test_malformed_history_fails_before_writing(tmp_path):
    cfg = fixture(tmp_path)
    (tmp_path / "aliases_history.json").write_text('{"pairs": ["not a pair"]}', encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed"):
        stage_aliases_blackforum(cfg)
    with sqlite3.connect(str(cfg.db)) as conn:
        assert conn.execute("SELECT count(*) FROM aliases").fetchone()[0] == 0
