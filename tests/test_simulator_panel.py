"""P5-d 面板纯函数单测（不依赖 Streamlit script run context）。

面板是引擎薄壳——这里断言：分布/漏斗数据提取正确、且「面板取的数字」与
simulate_combat 返回的 report 完全一致（面板不改数）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.simulator_panel import (
    funnel_rows,
    kill_distribution_series,
    percentile_caption,
)

DB = Path("db/wh40k.sqlite")


def test_kill_distribution_series_sorted_and_int_keys():
    rep = {"distribution": {"histogram": {"2": 0.3, "0": 0.5, "1": 0.2},
                            "p10": 0, "p50": 1, "p90": 2}}
    s = kill_distribution_series(rep)
    assert [k for k, _ in s] == [0, 1, 2]                 # 升序 + str 键归一 int
    assert sum(p for _, p in s) == pytest.approx(1.0)


def test_kill_distribution_series_int_keys():
    rep = {"distribution": {"histogram": {0: 0.7, 3: 0.3}}}
    assert kill_distribution_series(rep) == [(0, 0.7), (3, 0.3)]


def test_funnel_rows_order_and_labels():
    rep = {"funnel": {"attacks": 20, "hits": 10, "wounds": 6,
                      "unsaved": 4, "damage": 5, "kills": 2}}
    rows = funnel_rows(rep)
    assert [r[0] for r in rows] == ["攻击数", "命中", "致伤", "过保/致命", "有效伤害", "击杀"]
    assert rows[0][1] == 20.0 and rows[-1][1] == 2.0


def test_percentile_caption_has_values():
    rep = {"distribution": {"p10": 1, "p50": 3, "p90": 5}}
    cap = percentile_caption(rep)
    assert "1" in cap and "3" in cap and "5" in cap


def test_empty_report_no_crash():
    assert kill_distribution_series({}) == []
    assert len(funnel_rows({})) == 6
    assert "P10" in percentile_caption({})


@pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")
def test_streamlit_app_simulator_view_end_to_end():
    """AppTest headless 驱动整个 app：切到模拟器视图 → 填表 → 提交 → 断言无异常 + 出数。

    这是面板 UI 接线的回归护栏（Streamlit 1.35 的 chat_input 门槛、tab/侧边栏切换、
    表单提交、simulate_combat 接线一次性覆盖）。
    """
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        pytest.skip("streamlit.testing 不可用")

    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"),
                           default_timeout=90)
    at.run()
    assert not at.exception
    at.sidebar.radio[0].set_value("⚔️ 模拟器").run()
    assert not at.exception
    at.text_input(key="sim_attacker").set_value("Boyz")
    at.text_input(key="sim_defender").set_value("Intercessor Squad")
    at.text_input(key="sim_loadout").set_value("Shoota:10")
    at.number_input(key="sim_n").set_value(2000)
    at.button[0].click().run()
    assert not at.exception
    labels = {m.label for m in at.metric}
    assert {"期望伤害", "期望击杀", "团灭率"} <= labels
    assert any("Boyz" in s.value for s in at.success)


@pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")
def test_panel_numbers_equal_tool_numbers():
    """面板取的分布/漏斗数字 == simulate_combat 原始 report（面板只是壳，不改数）。"""
    from agent.tools import simulate_combat
    res = simulate_combat("Boyz", "Intercessor Squad",
                          {"loadout": [["Shoota", 10]], "n": 4000, "seed": 3})
    assert res["ok"]
    rep = res["report"]
    # 面板漏斗与 report.funnel 逐项一致
    fr = dict(funnel_rows(rep))
    assert fr["攻击数"] == rep["funnel"]["attacks"]
    assert fr["击杀"] == rep["funnel"]["kills"]
    # 面板分布概率和 == report.histogram 概率和（≈1）
    s = kill_distribution_series(rep)
    assert sum(p for _, p in s) == pytest.approx(1.0, abs=0.02)
