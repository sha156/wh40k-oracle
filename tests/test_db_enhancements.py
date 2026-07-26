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
    assert chk["match"] is True                          # CSV 每行都在库里
    assert chk["missing_count"] == 0 and chk["db_extra_rows"] == 0
    assert chk["csv_detachments"] == chk["db_detachments"]


@needs_csv
def test_check_tolerates_fp_rules_补录层_but_flags_real_loss(tmp_path):
    """对账口径：库 = 上游 CSV 层 + fp_rules 补录层（FP 新分队，Wahapedia 无源）。

    旧口径拿 CSV 总数直接比库总数，只要补录层存在就恒报「不一致」——真库里
    927 vs 1058 天天红着，于是没人再看它。假警报的代价就是漏掉真丢行，所以
    改判「CSV 的每一行都在库里」，补录层进 db_extra_rows 如实披露。
    """
    import sqlite3
    db = tmp_path / "t.sqlite"
    rows = load_rows(CSV)
    apply_enhancements(db, rows)
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO enhancements (id, faction_id, detachment_id, name, cost)"
                 " VALUES ('fp11e-x-1', 'AC', 'd1', '补录强化', 15)")
    conn.commit()
    conn.close()

    chk = check_enhancements(db, rows)
    assert chk["match"] is True                  # 补录层不算差异
    assert chk["db_extra_rows"] == 1 and chk["db_rows"] == len(rows) + 1

    # 但真丢一行上游数据必须红
    conn = sqlite3.connect(str(db))
    conn.execute("DELETE FROM enhancements WHERE id = ?", (rows[0]["id"],))
    conn.commit()
    conn.close()
    chk = check_enhancements(db, rows)
    assert chk["match"] is False
    assert chk["missing_count"] == 1 and chk["missing_sample"] == [rows[0]["id"]]


def test_apply_reports_the_overlay_columns_it_wipes(tmp_path):
    """INSERT OR REPLACE 是删了再插：官方中文名 / DSL 投影会被一并清空。

    这类丢失极隐蔽——表现是「中文名忽然少了一批」，没人会联想到是重灌强化表干的。
    所以清了多少必须报出来（CLI 据此提示补跑 official-zh --apply 与 dsl-apply）。
    """
    import sqlite3

    db = tmp_path / "t.sqlite"
    rows = [{"id": "e1", "faction_id": "AE", "name": "Archraider", "cost": "20",
             "detachment": "Windrider Host", "detachment_id": "d1",
             "legend": "", "description": "x"}]
    apply_enhancements(db, rows)
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE enhancements SET name_zh = '大劫掠者', "
                 "effect_dsl_json = '{}'")
    conn.commit()
    conn.close()

    rep = apply_enhancements(db, rows)
    assert rep["cleared_overlay"] == {"name_zh": 1, "effect_dsl_json": 1}


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
