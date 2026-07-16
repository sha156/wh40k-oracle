# tests/test_db_compile_fp_rules.py
"""db_compile.fp_rules：Faction Pack 规则文本真漂移补丁（内存 DB，不联网）。"""
import sqlite3

from db_compile.fp_rules import apply_fp_rules, _norm_text
from db_compile.schema import ALL_DDL

_OLD = ('<b>WHEN:</b> Your opponent’s Charge phase, just after an enemy unit '
        'has declared a charge.')
_NEW = ('<b>WHEN:</b> Your opponent’s Charge phase, just after an enemy unit '
        'has selected its charge target.')


def _db(tmp_path, strat_text=_OLD, name_zh=None):
    db = tmp_path / "t.sqlite"
    conn = sqlite3.connect(str(db))
    for ddl in ALL_DDL:
        conn.execute(ddl)
    conn.execute(
        "INSERT INTO stratagems (id, faction, detachment, name_zh, name_en, "
        "cp_cost, phase, text_zh) VALUES (?,?,?,?,?,?,?,?)",
        ("s1", "TAU", "Kauyon", name_zh, "PHOTON GRENADES", "1", "Charge", strat_text))
    conn.execute(
        "INSERT INTO detachments (id, faction, name_zh, name_en, rule_text) "
        "VALUES (?,?,?,?,?)",
        ("d1", "TAU", None, "Integrated Command Structure", "old 10e text"))
    conn.commit()
    conn.close()
    return db


def _text_patch(**over):
    p = {"table": "stratagems", "id": "s1", "name_en": "PHOTON GRENADES",
         "column": "text_zh", "from_text": _OLD, "to_text": _NEW,
         "fp_source": "page_019.md", "synthesis": "change-list应用"}
    p.update(over)
    return {"text_patches": [p]}


class TestNormText:
    def test_semantic_diff_preserved(self):
        # 真漂移（措辞不同）归一化后必须仍可区分
        assert _norm_text(_OLD) != _norm_text(_NEW)

    def test_html_and_apostrophe_are_not_drift(self):
        # 标签/弯撇号/空白差异不构成漂移
        a = '<b>WHEN:</b> Your opponent’s   Charge phase.'
        b = "WHEN: Your opponent's Charge phase."
        assert _norm_text(a) == _norm_text(b)


class TestTextPatch:
    def test_applies_when_db_matches_from(self, tmp_path):
        db = _db(tmp_path)
        rep = apply_fp_rules(db, _text_patch())
        assert rep["text_applied"] == 1
        after = sqlite3.connect(str(db)).execute(
            "SELECT text_zh FROM stratagems WHERE id='s1'").fetchone()[0]
        assert after == _NEW

    def test_idempotent_second_run_skips(self, tmp_path):
        db = _db(tmp_path)
        apply_fp_rules(db, _text_patch())
        rep2 = apply_fp_rules(db, _text_patch())
        assert rep2["text_applied"] == 0
        assert rep2["text_already"] == 1

    def test_mismatch_does_not_clobber(self, tmp_path):
        # 库现文本既非 from 也非 to（上游滚更过）→ 让路告警，绝不盲覆盖
        db = _db(tmp_path, strat_text="some upstream-rolled 11e text")
        rep = apply_fp_rules(db, _text_patch())
        assert rep["text_applied"] == 0
        assert len(rep["text_mismatch"]) == 1
        after = sqlite3.connect(str(db)).execute(
            "SELECT text_zh FROM stratagems WHERE id='s1'").fetchone()[0]
        assert after == "some upstream-rolled 11e text"

    def test_table_column_whitelist(self, tmp_path):
        # 表/列名拼进 SQL，白名单外必须拒绝（哪怕行存在）
        db = _db(tmp_path)
        rep = apply_fp_rules(db, _text_patch(table="units", column="name_en"))
        assert rep["text_applied"] == 0
        assert len(rep["text_invalid"]) == 1
        rep2 = apply_fp_rules(db, _text_patch(column="name_en"))
        assert len(rep2["text_invalid"]) == 1

    def test_missing_row_skipped(self, tmp_path):
        db = _db(tmp_path)
        rep = apply_fp_rules(db, _text_patch(id="nope"))
        assert rep["text_applied"] == 0
        assert len(rep["text_skipped"]) == 1


class TestNamePatch:
    def _patch(self, **over):
        p = {"table": "stratagems", "id": "s1", "name_en": "PHOTON GRENADES",
             "name_zh": "光子手雷", "zh_source": "codex-10e"}
        p.update(over)
        return {"name_patches": [p]}

    def test_fills_null_name(self, tmp_path):
        db = _db(tmp_path)
        rep = apply_fp_rules(db, self._patch())
        assert rep["name_applied"] == 1
        after = sqlite3.connect(str(db)).execute(
            "SELECT name_zh FROM stratagems WHERE id='s1'").fetchone()[0]
        assert after == "光子手雷"

    def test_idempotent(self, tmp_path):
        db = _db(tmp_path)
        apply_fp_rules(db, self._patch())
        rep2 = apply_fp_rules(db, self._patch())
        assert rep2["name_applied"] == 0
        assert rep2["name_already"] == 1

    def test_existing_different_name_not_clobbered(self, tmp_path):
        # 上游/人工已填过不同中文名 → 让路
        db = _db(tmp_path, name_zh="人工校订名")
        rep = apply_fp_rules(db, self._patch())
        assert rep["name_applied"] == 0
        assert len(rep["name_mismatch"]) == 1
        after = sqlite3.connect(str(db)).execute(
            "SELECT name_zh FROM stratagems WHERE id='s1'").fetchone()[0]
        assert after == "人工校订名"

    def test_table_whitelist(self, tmp_path):
        db = _db(tmp_path)
        rep = apply_fp_rules(db, self._patch(table="units"))
        assert len(rep["name_invalid"]) == 1


def _deact_patch(**over):
    p = {"table": "stratagems", "id": "s1", "name_en": "PHOTON GRENADES",
         "status": "removed_11e", "fp_source": "page_003.md（完整重印未收录）"}
    p.update(over)
    return {"deactivations": [p]}


class TestDeactivations:
    """2026-07-16 裁定：FP 完整重印即整体替换——未收录旧战略标 fp_status='removed_11e'。"""

    def test_marks_removed_keeps_text(self, tmp_path):
        db = _db(tmp_path)
        rep = apply_fp_rules(db, _deact_patch())
        assert rep["deact_applied"] == 1
        row = sqlite3.connect(str(db)).execute(
            "SELECT fp_status, text_zh FROM stratagems WHERE id='s1'").fetchone()
        assert row[0] == "removed_11e"
        assert row[1] == _OLD          # 原文保留可回滚，只置标记

    def test_idempotent(self, tmp_path):
        db = _db(tmp_path)
        apply_fp_rules(db, _deact_patch())
        rep2 = apply_fp_rules(db, _deact_patch())
        assert rep2["deact_applied"] == 0 and rep2["deact_already"] == 1

    def test_name_mismatch_lets_pass(self, tmp_path):
        # id 对应行 name_en 不符（疑上游复用 id）→ 让路告警不盲标
        db = _db(tmp_path)
        rep = apply_fp_rules(db, _deact_patch(name_en="SOME OTHER STRATAGEM"))
        assert rep["deact_applied"] == 0
        assert len(rep["deact_mismatch"]) == 1
        row = sqlite3.connect(str(db)).execute(
            "SELECT fp_status FROM stratagems WHERE id='s1'").fetchone()
        assert row[0] is None

    def test_whitelists(self, tmp_path):
        db = _db(tmp_path)
        rep = apply_fp_rules(db, _deact_patch(table="units"))
        assert len(rep["deact_invalid"]) == 1
        rep2 = apply_fp_rules(db, _deact_patch(status="deleted"))
        assert len(rep2["deact_invalid"]) == 1

    def test_legacy_db_without_column(self, tmp_path):
        # 旧库无 fp_status 列（建表早于 DDL 加列）→ ALTER 补列后照常标记
        db = tmp_path / "legacy.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE stratagems (id TEXT PRIMARY KEY, faction TEXT, "
                     "detachment TEXT, name_zh TEXT, name_en TEXT, cp_cost TEXT, "
                     "phase TEXT, text_zh TEXT, effect_dsl_json TEXT, "
                     "dsl_status TEXT DEFAULT 'not_modeled')")
        conn.execute("INSERT INTO stratagems (id, name_en, text_zh) "
                     "VALUES ('s1', 'PHOTON GRENADES', 'x')")
        conn.commit()
        conn.close()
        rep = apply_fp_rules(db, _deact_patch())
        assert rep["deact_applied"] == 1

    def test_real_patches_file_deactivations_shape(self):
        # 真源补丁文件：9 条裁定项形状齐全（表/状态白名单内、带 fp_source）
        import json
        from pathlib import Path
        data = json.loads(Path("db_compile/fp_rules_patches.json").read_text(
            encoding="utf-8"))
        deacts = data.get("deactivations", [])
        assert len(deacts) == 9
        assert {d["id"] for d in deacts} == {
            "000009840003", "000009840004", "000009840005", "000009840007",
            "000009984002", "000009984003", "000009984004", "000009984006",
            "000009984007"}
        for d in deacts:
            assert d["table"] == "stratagems"
            assert d["status"] == "removed_11e"
            assert d.get("fp_source")
