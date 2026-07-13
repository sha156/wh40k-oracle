"""tests/test_db_enhancements.py — 强化数据层（P6 验表 PR1a）。

覆盖：cost 收敛（空/非数字→None 不猜 0）、CSV 解析、apply→check 对账一致、
按 detachment_id 查询排序。用临时 DB，不碰真 db/wh40k.sqlite。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from db_compile.enhancements import (_cost_to_int, apply_enhancements,
                                     check_enhancements, list_for_detachment,
                                     load_rows)

CSV = Path("db_sources/wahapedia/Enhancements.csv")
needs_csv = pytest.mark.skipif(not CSV.exists(), reason="Enhancements.csv 未下载")


def test_cost_to_int():
    assert _cost_to_int("20") == 20
    assert _cost_to_int("0") == 0        # 0 分是合法值，不能当缺失
    assert _cost_to_int("") is None      # 空 → None（诚实标注，不猜 0）
    assert _cost_to_int("  ") is None
    assert _cost_to_int("abc") is None
    assert _cost_to_int(None) is None


@needs_csv
def test_load_rows_schema():
    rows = load_rows(CSV)
    assert len(rows) > 800          # 实测 927
    cols = set(rows[0].keys())
    assert {"id", "name", "cost", "detachment_id", "faction_id"} <= cols


@needs_csv
def test_apply_and_check_reconcile(tmp_path):
    db = tmp_path / "t.sqlite"
    rows = load_rows(CSV)
    rep = apply_enhancements(db, rows)
    assert rep["inserted"] == rep["table_total"]         # 全部落库
    assert rep["detachments"] > 200                      # 实测 261
    chk = check_enhancements(db, rows)
    assert chk["match"] is True                          # CSV 行数 == 库行数
    assert chk["csv_detachments"] == chk["db_detachments"]


@needs_csv
def test_apply_idempotent(tmp_path):
    """INSERT OR REPLACE：重复 apply 不翻倍。"""
    db = tmp_path / "t.sqlite"
    rows = load_rows(CSV)
    r1 = apply_enhancements(db, rows)
    r2 = apply_enhancements(db, rows)
    assert r1["table_total"] == r2["table_total"]


@needs_csv
def test_list_for_detachment_sorted(tmp_path):
    db = tmp_path / "t.sqlite"
    apply_enhancements(db, load_rows(CSV))
    # Shield Host（Adeptus Custodes）：detachment_id 稳定
    out = list_for_detachment(db, "000000765")
    assert out and all("name" in e and "cost" in e for e in out)
    names = {e["name"] for e in out}
    assert "Auric Mantle" in names
    costs = [e["cost"] for e in out]
    assert costs == sorted(costs)                        # 按点数升序


@needs_csv
def test_list_for_detachment_unknown_empty(tmp_path):
    db = tmp_path / "t.sqlite"
    apply_enhancements(db, load_rows(CSV))
    assert list_for_detachment(db, "nonexistent") == []
