# tests/test_db_compile_fp_errata.py
"""db_compile.fp_errata：Faction Pack 真漂移外科补丁（内存 DB，不联网）。"""
import json
import sqlite3

import pytest

from db_compile.fp_errata import apply_fp_errata, _guard_norm
from db_compile.schema import ALL_DDL


def _db_with(models):
    conn = sqlite3.connect(":memory:")
    for ddl in ALL_DDL:
        conn.execute(ddl)
    for uid, fac, name, m in models:
        conn.execute("INSERT INTO units (id,faction_id,name_en) VALUES (?,?,?)",
                     (uid, fac, name))
        conn.execute("INSERT INTO models (unit_id,name,m,t,sv,invuln,w,ld,oc) "
                     "VALUES (?,?,?,?,?,?,?,?,?)",
                     (uid, name, m, "12", "3+", None, "28", "7+", "-"))
    conn.commit()
    return conn


class TestGuardNorm:
    def test_keeps_plus_so_aircraft_from_to_distinguishable(self):
        # 关键回归：'20+"'(十版) 与 '20"'(11版) 必须可区分，否则守卫失效
        assert _guard_norm('20+"') != _guard_norm('20"')
        assert _guard_norm('20+"') == "20+"
        assert _guard_norm('20"') == "20"

    def test_strips_quotes_and_space(self):
        assert _guard_norm(' 14" ') == "14"
        assert _guard_norm("6") == "6"


class TestStatPatch:
    def _patches(self, **over):
        p = {"unit_id": "u1", "faction": "TAU", "unit": "Orca Dropship",
             "field": "m", "from": '20+"', "to": '20"'}
        p.update(over)
        return {"stat_patches": [p], "new_units": []}

    def test_applies_when_db_matches_from(self, tmp_path):
        db = tmp_path / "t.sqlite"
        conn = _db_with([("u1", "TAU", "Orca Dropship", '20+"')])
        conn.execute("VACUUM INTO ?", (str(db),)); conn.close()
        rep = apply_fp_errata(db, self._patches())
        assert rep["stat_applied"] == 1
        after = sqlite3.connect(db).execute(
            "SELECT m FROM models WHERE unit_id='u1'").fetchone()[0]
        assert after == '20"'

    def test_idempotent_second_run_skips(self, tmp_path):
        db = tmp_path / "t.sqlite"
        conn = _db_with([("u1", "TAU", "Orca Dropship", '20+"')])
        conn.execute("VACUUM INTO ?", (str(db),)); conn.close()
        apply_fp_errata(db, self._patches())
        rep2 = apply_fp_errata(db, self._patches())
        assert rep2["stat_applied"] == 0
        assert rep2["stat_already"] == 1

    def test_mismatch_does_not_clobber(self, tmp_path):
        db = tmp_path / "t.sqlite"
        # 库现值既非 from 也非 to（上游改过）→ 让路
        conn = _db_with([("u1", "TAU", "Orca Dropship", '15"')])
        conn.execute("VACUUM INTO ?", (str(db),)); conn.close()
        rep = apply_fp_errata(db, self._patches())
        assert rep["stat_applied"] == 0
        assert len(rep["stat_mismatch"]) == 1
        after = sqlite3.connect(db).execute(
            "SELECT m FROM models WHERE unit_id='u1'").fetchone()[0]
        assert after == '15"'                    # 未被覆盖

    def test_invalid_field_rejected(self, tmp_path):
        db = tmp_path / "t.sqlite"
        conn = _db_with([("u1", "TAU", "Orca Dropship", '20+"')])
        conn.execute("VACUUM INTO ?", (str(db),)); conn.close()
        rep = apply_fp_errata(db, self._patches(field="name"))
        assert rep["stat_applied"] == 0
        assert len(rep["stat_invalid"]) == 1


class TestNewUnits:
    def _unit(self):
        return {"unit_id": "fpe_bigboss", "faction": "ORK", "name": "Bigboss",
                "version": "11e-fp", "keywords": ["INFANTRY", "CHARACTER"],
                "faction_keywords": ["ORKS"],
                "models": [{"name": "Bigboss", "m": '6"', "t": "5", "sv": "4+",
                            "invuln": "", "w": "5", "ld": "7+", "oc": "1"}],
                "weapons": [{"name": "Slugga", "range": '12"', "a": "1",
                             "bs_ws": "5+", "s": "4", "ap": "0", "d": "1",
                             "keywords": ["CLOSE-QUARTERS"]}]}

    def test_inserts_full_datasheet(self, tmp_path):
        db = tmp_path / "t.sqlite"
        conn = _db_with([]); conn.execute("VACUUM INTO ?", (str(db),)); conn.close()
        rep = apply_fp_errata(db, {"stat_patches": [], "new_units": [self._unit()]})
        assert rep["units_inserted"] == ["ORK:Bigboss"]
        c = sqlite3.connect(db)
        assert c.execute("SELECT version FROM units WHERE id='fpe_bigboss'").fetchone()[0] == "11e-fp"
        assert c.execute("SELECT w FROM models WHERE unit_id='fpe_bigboss'").fetchone()[0] == "5"
        wk = c.execute("SELECT keywords_json FROM weapons WHERE unit_id='fpe_bigboss'").fetchone()[0]
        assert "CLOSE-QUARTERS" in wk
        kw = json.loads(c.execute("SELECT keywords_json FROM units WHERE id='fpe_bigboss'").fetchone()[0])
        assert "INFANTRY" in kw["keywords"] and kw["faction_keywords"] == ["ORKS"]

    def test_skips_when_already_exists(self, tmp_path):
        db = tmp_path / "t.sqlite"
        conn = _db_with([("x", "ORK", "Bigboss", '6"')])
        conn.execute("VACUUM INTO ?", (str(db),)); conn.close()
        rep = apply_fp_errata(db, {"stat_patches": [], "new_units": [self._unit()]})
        assert rep["units_inserted"] == []
        assert rep["units_exist"] == ["ORK:Bigboss"]
