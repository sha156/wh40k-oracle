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

    def test_drift_after_apply_clears_stale_projection(self, tmp_path):
        # 审查 H2 真实运营场景：曾 apply 成功 → 上游刷新文本 → 再 apply。
        # 旧投影必须被降级清空，不许让"不再经文本核验"的旧编码继续喂模拟层
        db = _db(tmp_path)
        pd = _payload_dir(tmp_path)
        apply_dsl(db, pd)
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE abilities SET text_zh='upstream refreshed 11e text' "
                     "WHERE id='000008439'")
        conn.commit()
        conn.close()
        rep = apply_dsl(db, pd)
        assert len(rep["fingerprint_mismatch"]) == 1
        assert rep["fingerprint_mismatch"][0]["stale_projection_cleared"] is True
        row = sqlite3.connect(str(db)).execute(
            "SELECT effect_dsl_json, dsl_status FROM abilities "
            "WHERE id='000008439'").fetchone()
        assert row[0] is None and row[1] == "not_modeled"

    def test_duplicate_entry_rejected(self, tmp_path):
        # 审查 M2：重复 (table,id) 静默 last-write 是错 id 温床 → 拒载
        import pytest
        db = _db(tmp_path)
        d = tmp_path / "payloads"
        d.mkdir(exist_ok=True)
        entry = json.loads((_payload_dir(tmp_path) / "tau.json").read_text(
            encoding="utf-8"))["entries"][0]
        (d / "tau.json").write_text(json.dumps(
            {"dsl_version": 1, "faction": "TAU", "entries": [entry, entry]},
            ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ValueError, match="重复条目"):
            apply_dsl(db, d)

    def test_stage_wired_into_restore(self):
        from db_compile.update import _RESTORE_STAGES
        names = [fn.__name__ for _, fn in _RESTORE_STAGES]
        # dsl_apply 必须在 fp_rules 之后（指纹要对 11 版化后的文本核）
        assert "stage_dsl_apply" in names
        assert names.index("stage_dsl_apply") > names.index("stage_fp_rules")


_RULE_TEXT = "During the third battle round, ranged weapons have [SUSTAINED HITS 1]."
_RULE_FP = hashlib.sha256(_norm_text(_RULE_TEXT).encode("utf-8")).hexdigest()


def _mat_db(tmp_path):
    """detachments 源行 + 空 abilities（物化目标行由 dsl_apply 创建）。"""
    db = tmp_path / "m.sqlite"
    conn = sqlite3.connect(str(db))
    for ddl in ALL_DDL:
        conn.execute(ddl)
    conn.execute(
        "INSERT INTO detachments (id, faction, name_zh, name_en, rule_text) "
        "VALUES (?,?,?,?,?)",
        ("000008441", "TAU", "耐心猎手", "Patient Hunter", _RULE_TEXT))
    conn.commit()
    conn.close()
    return db


def _mat_payload_dir(tmp_path, sha=_RULE_FP):
    d = tmp_path / "payloads"
    d.mkdir(exist_ok=True)
    (d / "tau.json").write_text(json.dumps({
        "dsl_version": 1, "faction": "TAU",
        "entries": [{
            "table": "abilities", "id": "det000008441",
            "materialize": {"from_table": "detachments", "from_id": "000008441",
                            "from_column": "rule_text"},
            "side": "attacker", "detachment": "Kauyon",
            "name_en": "Patient Hunter", "name_zh": "耐心猎手", "status": "partial",
            "effects": [{"phase": "hit", "op": "extra_hits", "params": [1],
                         "condition": ["detachment_rounds_shooting"], "source": "PH"}],
            "requires_toggles": ["detachment_rounds"],
            "not_modeled_notes_zh": ["战轮门控用开关近似"],
            "provenance": {"text_sha256": sha},
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return d


class TestMaterialize:
    """PR3 spec D5：分队规则条目物化到 abilities 新行（owner_id=NULL），指纹对源文本核。"""

    def test_materializes_new_ability_row(self, tmp_path):
        db = _mat_db(tmp_path)
        rep = apply_dsl(db, _mat_payload_dir(tmp_path))
        assert rep["applied"] == 1
        assert rep["changes"][0].get("materialized") is True
        row = sqlite3.connect(str(db)).execute(
            "SELECT owner_id, name_en, text_zh, dsl_status FROM abilities "
            "WHERE id='det000008441'").fetchone()
        assert row == (None, "Patient Hunter", _RULE_TEXT, "partial")

    def test_materialize_idempotent(self, tmp_path):
        db = _mat_db(tmp_path)
        pd = _mat_payload_dir(tmp_path)
        apply_dsl(db, pd)
        rep2 = apply_dsl(db, pd)
        assert rep2["applied"] == 0 and rep2["already"] == 1

    def test_materialize_fingerprint_mismatch_deletes_row(self, tmp_path):
        # 源文本刷新而 DSL 未重核 → 物化行整行删除（行本身就是投影，残留=喂错数据）
        db = _mat_db(tmp_path)
        apply_dsl(db, _mat_payload_dir(tmp_path))
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE detachments SET rule_text='upstream refreshed' "
                     "WHERE id='000008441'")
        conn.commit()
        conn.close()
        rep = apply_dsl(db, _mat_payload_dir(tmp_path))
        assert len(rep["fingerprint_mismatch"]) == 1
        assert rep["fingerprint_mismatch"][0]["stale_projection_cleared"] is True
        row = sqlite3.connect(str(db)).execute(
            "SELECT count(*) FROM abilities WHERE id='det000008441'").fetchone()
        assert row[0] == 0

    def test_materialize_source_missing_skipped(self, tmp_path):
        db = _mat_db(tmp_path)
        conn = sqlite3.connect(str(db))
        conn.execute("DELETE FROM detachments")
        conn.commit()
        conn.close()
        rep = apply_dsl(db, _mat_payload_dir(tmp_path))
        assert rep["applied"] == 0
        assert any("源行不存在" in s["reason"] for s in rep["skipped"])

    def test_materialize_source_whitelist(self, tmp_path):
        # 源只许 detachments.rule_text；乱指源表/列 → 快速失败
        import pytest
        db = _mat_db(tmp_path)
        d = tmp_path / "payloads"
        d.mkdir(exist_ok=True)
        raw = json.loads((_mat_payload_dir(tmp_path) / "tau.json").read_text(
            encoding="utf-8"))
        raw["entries"][0]["materialize"]["from_table"] = "units"
        (d / "tau.json").write_text(json.dumps(raw, ensure_ascii=False),
                                    encoding="utf-8")
        with pytest.raises(ValueError, match="materialize"):
            apply_dsl(db, d)

    def test_real_payload_projection_counts(self, tmp_path):
        # 真源全量对账（P7-PR5 起多文件：tau + worldeaters + …）：payload 三态计数
        # == 投影结果计数（applied+already）。物化目标库：detachments 源行按真实
        # id/文本造行，其余行照 payload id 造壳
        import pathlib
        all_entries = []
        for f in sorted(pathlib.Path("dsl_payloads").glob("*.json")):
            payload = json.loads(f.read_text(encoding="utf-8"))
            fac = payload.get("faction", "TAU")
            all_entries += [(fac, e) for e in payload["entries"]]
        db = tmp_path / "r.sqlite"
        conn = sqlite3.connect(str(db))
        for ddl in ALL_DDL:
            conn.execute(ddl)
        # 用真库的源文本造行（指纹必须能对上真源 payload 里录的 sha）
        real = sqlite3.connect("db/wh40k.sqlite")
        for fac, e in all_entries:
            mat = e.get("materialize")
            if mat:
                src = real.execute(
                    "SELECT faction, name_zh, name_en, rule_text FROM detachments "
                    "WHERE id=?", (mat["from_id"],)).fetchone()
                conn.execute("INSERT INTO detachments (id, faction, name_zh, name_en, "
                             "rule_text) VALUES (?,?,?,?,?)", (mat["from_id"], *src))
            elif e["table"] == "abilities":
                txt = real.execute("SELECT text_zh FROM abilities WHERE id=?",
                                   (e["id"],)).fetchone()
                conn.execute("INSERT INTO abilities (id, name_en, text_zh) "
                             "VALUES (?,?,?)", (e["id"], e["name_en"], txt[0]))
            elif e["table"] == "enhancements":     # P7-PR4：增强层投影（指纹列=description）
                txt = real.execute("SELECT description FROM enhancements WHERE id=?",
                                   (e["id"],)).fetchone()
                conn.execute("INSERT INTO enhancements (id, faction_id, name, "
                             "description) VALUES (?,?,?,?)",
                             (e["id"], fac, e["name_en"], txt[0]))
            else:
                txt = real.execute("SELECT text_zh FROM stratagems WHERE id=?",
                                   (e["id"],)).fetchone()
                conn.execute("INSERT INTO stratagems (id, faction, name_en, text_zh) "
                             "VALUES (?,?,?,?)", (e["id"], fac, e["name_en"], txt[0]))
        real.close()
        conn.commit()
        conn.close()
        rep = apply_dsl(db, "dsl_payloads")
        # 77（钛）+ 88（吞世者）+ 48（黑色圣堂）+ 104（帝皇之子 PR7）
        # + 106（死亡守卫 PR8）+ 73（圣血天使 PR9）+ 105（千子 PR10）
        # + 98（卡斯托迪斯 PR11）+ 112（德鲁卡里 PR12）+ 145（死灵 PR13）
        # + 142（兽人 PR14）+ 83（圣血修女 PR15）+ 98（灰骑士 PR16）
<<<<<<< HEAD
        # + 12（死亡守望 PR17）+ 73（黑暗天使 PR19）+ 158（Space Marines PR20）
        # + 79（帝国骑士 PR21）+ 69（帝国代理 PR23）+ 109（钢铁联盟 PR24）= 1779
        assert rep["applied"] + rep["already"] == len(all_entries) == 1779
        assert not rep["fingerprint_mismatch"] and not rep["skipped"]
        assert rep["by_status"] == {"encoded": 113, "partial": 385, "not_modeled": 1281}
=======
        # + 12（死亡守望 PR17）+ 64（太空野狼 PR18）= 1355
        assert rep["applied"] + rep["already"] == len(all_entries) == 1355
        assert not rep["fingerprint_mismatch"] and not rep["skipped"]
        assert rep["by_status"] == {"encoded": 108, "partial": 285, "not_modeled": 962}
>>>>>>> feat/p7-pr18-spacewolves
