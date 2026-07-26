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
                               UpdateConfig, stage_build, stage_fp_errata,
                               stage_fp_rules, stage_mfm_apply, stage_mfm_check,
                               stage_official_zh)


# ── H1：层序 ──────────────────────────────────────────────────────

def test_fp_errata_before_mfm_apply_in_pipeline():
    fns = [entry[1] for entry in _PIPELINE]
    assert fns.index(stage_fp_errata) < fns.index(stage_mfm_apply)


def test_fp_errata_before_mfm_apply_in_restore():
    fns = [entry[1] for entry in _RESTORE_STAGES]
    assert fns.index(stage_fp_errata) < fns.index(stage_mfm_apply)


def test_official_zh_lands_after_fp_rules():
    """官方中文名要盖在 fp_rules 的 P7 人工译名之上（宪法 §6：官方 > 人工）。

    顺序反了就是低权威覆盖高权威，而两边都是中文名，页面上看不出任何差别。
    """
    for stages in (_PIPELINE, _RESTORE_STAGES):
        fns = [entry[1] for entry in stages]
        assert fns.index(stage_fp_rules) < fns.index(stage_official_zh)


def test_official_zh_is_in_restore_stages():
    """build 会清库：这一层不进 restore，重建后中文名会悄悄退回上一档。"""
    assert stage_official_zh in [entry[1] for entry in _RESTORE_STAGES]


def test_official_zh_missing_map_warns_instead_of_silent_skip(tmp_path):
    cfg = UpdateConfig(db=tmp_path / "x.sqlite",
                       official_zh_map=tmp_path / "nope.json")
    res = stage_official_zh(cfg)
    assert res.ok and res.warning and "中文名" in res.warning


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


# ── CSV 解析对账必须走 warning ──────────────────────────────────

def _build_report(**kw):
    from db_compile.build import BuildReport
    rep = BuildReport()
    rep.row_counts.update(kw.pop("row_counts", {"units": 3}))
    rep.csv_audit.update(kw.pop("csv_audit", {}))
    return rep


def _patch_build(monkeypatch, rep):
    import db_compile.build as build_mod
    monkeypatch.setattr(build_mod, "build_database", lambda *a, **k: rep)


def test_csv_unreconciled_surfaces_in_stage_warning(tmp_path, monkeypatch):
    """对账不平必须进 warning。

    `build` 子命令自己会打印对账，但整条 `db_compile update` 管线只显示
    summary + warning——不吼就等于这道门在主刷新路径上不存在，而上游换版式
    （MFM 改版那次）正是从主路径进来的。
    """
    _patch_build(monkeypatch, _build_report(csv_audit={
        "Stratagems.csv": {"physical_lines": 1482, "parsed_rows": 1480,
                           "expected_rows": 1481, "delta": -1, "reconciled": False},
        "Enhancements.csv": {"physical_lines": 927, "parsed_rows": 927,
                             "expected_rows": 927, "delta": 0, "reconciled": True},
    }))
    res = stage_build(UpdateConfig(db=tmp_path / "d.sqlite"))
    assert res.ok
    assert res.warning and "解析对账不平" in res.warning
    assert "Stratagems.csv" in res.warning and "1480" in res.warning
    assert "Enhancements.csv" not in res.warning      # 平的不刷屏
    assert list(res.detail["csv_unreconciled"]) == ["Stratagems.csv"]


def test_all_reconciled_produces_no_warning(tmp_path, monkeypatch):
    # 负向成对：全平时不许有告警，否则告警贬值成噪音
    _patch_build(monkeypatch, _build_report(csv_audit={
        "Stratagems.csv": {"physical_lines": 1482, "parsed_rows": 1481,
                           "expected_rows": 1481, "delta": 0, "reconciled": True},
    }))
    res = stage_build(UpdateConfig(db=tmp_path / "d.sqlite"))
    assert res.ok and res.warning is None
    assert res.detail["csv_unreconciled"] == {}
