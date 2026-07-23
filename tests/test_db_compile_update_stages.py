"""tests/test_db_compile_update_stages.py — update 管线层序与 mfm_check 诚实性。

gnhf 审查模块 4 的两条 HIGH 回归钉：
- H1：fp_errata 必须先于 mfm_apply（否则 fpe_* 新单位每次重建后点数归 NULL 且三道
  校验全静默——DB 副本已复现）。
- H2：mfm_check 在「可比 0 / 有 NULL 行」时不许报「已完全对齐官方」。
"""
from __future__ import annotations

import json
import sqlite3

from db_compile.update import (_MFM_MIN_COMPARED, _PIPELINE, _RESTORE_STAGES,
                               UpdateConfig, stage_fp_errata, stage_mfm_apply,
                               stage_mfm_check)


# ── H1：层序 ──────────────────────────────────────────────────────

def test_fp_errata_before_mfm_apply_in_pipeline():
    fns = [entry[1] for entry in _PIPELINE]
    assert fns.index(stage_fp_errata) < fns.index(stage_mfm_apply)


def test_fp_errata_before_mfm_apply_in_restore():
    fns = [entry[1] for entry in _RESTORE_STAGES]
    assert fns.index(stage_fp_errata) < fns.index(stage_mfm_apply)


# ── H2：mfm_check 诚实性 ─────────────────────────────────────────

def _cfg(tmp_path, factions):
    mfm_json = tmp_path / "mfm.json"
    mfm_json.write_text(json.dumps({"factions": factions}), encoding="utf-8")
    db = tmp_path / "wh40k.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
        "points_json TEXT,keywords_json TEXT,version TEXT)")
    conn.commit(); conn.close()
    return UpdateConfig(db=db, mfm_json=mfm_json)


def test_zero_compared_is_not_reported_aligned(tmp_path):
    # 全空缓存 → 可比 0：diffs 为空是「没得比」不是「已对齐」，必须带告警
    res = stage_mfm_check(_cfg(tmp_path, {"orks": []}))
    assert res.warning and "可比条数异常低" in res.warning
    assert "已完全对齐官方" not in res.summary


def test_unparsed_rows_surface_in_warning(tmp_path, monkeypatch):
    import db_compile.mfm as mfm
    monkeypatch.setattr(mfm, "check_points", lambda db, factions: {
        "compared": _MFM_MIN_COMPARED + 300, "agree": _MFM_MIN_COMPARED + 300,
        "diffs": [], "mfm_only": [], "tiered_units": [],
        "db_unparsed": ["Bigboss", "Bannernob"]})
    res = stage_mfm_check(_cfg(tmp_path, {}))
    assert res.warning and "points_json" in res.warning and "Bigboss" in res.warning
    assert "已完全对齐官方" not in res.summary


def test_healthy_check_reports_aligned(tmp_path, monkeypatch):
    # 负向成对：可比充足、零 diffs、零 unparsed → 才允许报「已完全对齐官方」
    import db_compile.mfm as mfm
    monkeypatch.setattr(mfm, "check_points", lambda db, factions: {
        "compared": _MFM_MIN_COMPARED + 300, "agree": _MFM_MIN_COMPARED + 300,
        "diffs": [], "mfm_only": [], "tiered_units": [], "db_unparsed": []})
    res = stage_mfm_check(_cfg(tmp_path, {}))
    assert res.warning is None
    assert "已完全对齐官方" in res.summary
