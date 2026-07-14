# tests/test_db_compile_dsl_apply.py
"""db_compile.dsl_apply：DSL 真源投影 + 指纹守卫 + rebuild 幸存语义（临时库，不联网）。"""
import hashlib
import json
import sqlite3

from db_compile.dsl_apply import apply_dsl
from db_compile.fp_rules import _norm_text
from db_compile.schema import ALL_DDL

_TEXT = "If your Army Faction is T'AU EMPIRE, improve BS by 1 when guided."
_FP = hashlib.sha256(_norm_text(_TEXT).encode("utf-8")).hexdigest()


def _db(tmp_path):
    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(str(db))
    for ddl in ALL_DDL:
        conn.execute(ddl)
    conn.execute(
        "INSERT INTO abilities (id, owner_id, name_en, text_zh) VALUES (?,?,?,?)",
        ("000008439", None, "For the Greater Good", _TEXT))
    conn.commit()
    conn.close()
    return db


def _payload_dir(tmp_path, sha=_FP):
    d = tmp_path / "payloads"
    d.mkdir(exist_ok=True)
    (d / "tau.json").write_text(json.dumps({
        "dsl_version": 1, "faction": "TAU",
        "entries": [{
            "table": "abilities", "id": "000008439", "side": "attacker",
            "name_en": "For the Greater Good", "status": "partial",
            "effects": [{"phase": "hit", "op": "bs_improve", "params": [1],
                         "condition": ["guided_vs_spotted"], "source": "FTGG"}],
            "requires_toggles": ["guided"],
            "not_modeled_notes_zh": ["观察员机会成本未建模"],
            "provenance": {"text_sha256": sha},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return d


class TestDslApply:
    def test_projects_payload_into_db(self, tmp_path):
        db = _db(tmp_path)
        rep = apply_dsl(db, _payload_dir(tmp_path))
        assert rep["applied"] == 1 and rep["by_status"]["partial"] == 1
        row = sqlite3.connect(str(db)).execute(
            "SELECT effect_dsl_json, dsl_status FROM abilities "
            "WHERE id='000008439'").fetchone()
        assert row[1] == "partial"
        assert json.loads(row[0])["effects"][0]["op"] == "bs_improve"

    def test_idempotent(self, tmp_path):
        db = _db(tmp_path)
        pd = _payload_dir(tmp_path)
        apply_dsl(db, pd)
        rep2 = apply_dsl(db, pd)
        assert rep2["applied"] == 0 and rep2["already"] == 1

    def test_fingerprint_mismatch_lets_pass(self, tmp_path):
        # 原文被后续刷新而 DSL 未重核 → 让路告警，不投影过期编码（评审 F12）
        db = _db(tmp_path)
        rep = apply_dsl(db, _payload_dir(tmp_path, sha="00" * 32))
        assert rep["applied"] == 0
        assert len(rep["fingerprint_mismatch"]) == 1
        row = sqlite3.connect(str(db)).execute(
            "SELECT effect_dsl_json, dsl_status FROM abilities "
            "WHERE id='000008439'").fetchone()
        assert row[0] is None and row[1] == "not_modeled"    # 未被污染

    def test_rebuild_survival_semantics(self, tmp_path):
        # rebuild 清零投影列（评审 F1 场景）→ restore 阶段重跑即补回
        db = _db(tmp_path)
        pd = _payload_dir(tmp_path)
        apply_dsl(db, pd)
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE abilities SET effect_dsl_json=NULL, "
                     "dsl_status='not_modeled'")          # 模拟 INSERT OR REPLACE 清零
        conn.commit()
        conn.close()
        rep = apply_dsl(db, pd)
        assert rep["applied"] == 1                         # 补回
        row = sqlite3.connect(str(db)).execute(
            "SELECT dsl_status FROM abilities WHERE id='000008439'").fetchone()
        assert row[0] == "partial"

    def test_stage_wired_into_restore(self):
        from db_compile.update import _RESTORE_STAGES
        names = [fn.__name__ for _, fn in _RESTORE_STAGES]
        # dsl_apply 必须在 fp_rules 之后（指纹要对 11 版化后的文本核）
        assert "stage_dsl_apply" in names
        assert names.index("stage_dsl_apply") > names.index("stage_fp_rules")
