"""2026-07-10 代码审查修复回归（docs/reviews/2026-07-10-full-code-review.md）。

覆盖：H9 n<=0 入口校验（engine + CLI）、H10 0==False 参数过滤陷阱（CLI + 面板）、
H11 loadout 畸形输入友好报错、M profile 显式 0 不被 or 1 改写、
M 守方非 hit 阶段 Effect 显式披露不静默丢。
"""
from __future__ import annotations

import sqlite3

import pytest

from engines.simulator.cli import (
    LoadoutParseError,
    _clean_options,
    _parse_loadout,
    main as cli_main,
)
from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Effect,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.engine import simulate, simulate_matchup


# ── 公共脚手架：脱库最小攻守 profile ─────────────────────────────
def _atk(models: int = 5) -> AttackerProfile:
    w = WeaponProfile(
        name_zh=None, name_en="probe", range='24"',
        attacks=DiceExpr(k=1), bs_ws=3, strength=4, ap=0,
        damage=DiceExpr(k=1), count=models)
    return AttackerProfile(canonical_id="a", name_en="A", name_zh=None,
                           models=models, loadout=(w,))


def _tgt(effects=()) -> TargetProfile:
    return TargetProfile(canonical_id="t", name_en="T", name_zh=None, models=5,
                         t=4, sv=4, invuln=None, w=2, oc=1, effects=effects)


# ═══ H9：n<=0 未校验（实测 n=0 → numpy zero-size 裸错，n=-5 → negative dimensions）═══
@pytest.mark.parametrize("bad_n", [0, -5])
def test_simulate_rejects_nonpositive_n(bad_n):
    with pytest.raises(ValueError) as ei:
        simulate(_atk(), _tgt(), Stance(), n=bad_n)
    msg = str(ei.value)
    assert "迭代次数" in msg and str(bad_n) in msg          # 中文可读 + 带收到的值


@pytest.mark.parametrize("bad_n", [0, -5])
def test_simulate_matchup_rejects_nonpositive_n(bad_n):
    with pytest.raises(ValueError) as ei:
        simulate_matchup(_atk(), _tgt(), _atk(), _tgt(),
                         Stance(), Stance(), n=bad_n)
    assert "迭代次数" in str(ei.value)


def test_cli_rejects_nonpositive_n_with_readable_error(capsys):
    # argparse type 校验：-n 0 → exit 2 + 中文提示（不进引擎）
    with pytest.raises(SystemExit) as ei:
        cli_main(["A", "B", "-n", "0"])
    assert ei.value.code == 2
    assert "正整数" in capsys.readouterr().err


# ═══ H10：0 == False 参数过滤陷阱（seed=0/n=0 等合法显式 0 被静默丢弃回默认）═══
def test_clean_options_keeps_explicit_zero_drops_none_false():
    out = _clean_options({"n": 0, "seed": 0, "cover": False,
                          "fnp": None, "phase": "melee"})
    # n=0 保留（随后被 H9 校验拦截并报可读错误——显式非法值应报错而非静默改写）
    assert out == {"n": 0, "seed": 0, "phase": "melee"}


class _FakeSt:
    """带 session_state dict 的假 Streamlit 命名空间（够 _options_from_inputs 用）。"""

    def __init__(self, state):
        self.session_state = state


def test_options_from_inputs_preserves_seed_zero():
    from ui.simulator_panel import _options_from_inputs
    opts = _options_from_inputs(_FakeSt({"sim_seed": 0, "sim_n": 2000}))
    assert opts["seed"] == 0          # H10：seed=0 不再被静默丢回默认 1234
    assert opts["n"] == 2000


# ═══ H11：loadout 畸形输入 → LoadoutParseError（可读消息），不再裸 traceback ═══
@pytest.mark.parametrize("bad", ["Shoota:", "Shoota:abc", ":3"])
def test_parse_loadout_malformed_raises_readable(bad):
    with pytest.raises(LoadoutParseError) as ei:
        _parse_loadout(bad)
    msg = str(ei.value)
    assert bad in msg                  # 指名哪个 token 坏了
    assert "武器名:数量" in msg        # 给期望格式示例


def test_parse_loadout_valid_forms_unchanged():
    assert _parse_loadout("Shoota:9,Slugga:1") == [("Shoota", 9), ("Slugga", 1)]
    assert _parse_loadout("Choppa") == [("Choppa", 1)]     # 无冒号 → 数量默认 1
    assert _parse_loadout(None) is None
    assert _parse_loadout("") is None


def test_cli_main_catches_loadout_error_exit_2(capsys):
    rc = cli_main(["A", "B", "--loadout", "Shoota:abc"])
    assert rc == 2
    assert "Shoota:abc" in capsys.readouterr().err


def test_options_from_inputs_propagates_loadout_error():
    # 面板侧：_options_from_inputs 抛出 → render_simulator_panel 捕获走 st.error
    from ui.simulator_panel import _options_from_inputs
    with pytest.raises(LoadoutParseError):
        _options_from_inputs(_FakeSt({"sim_loadout": "Shoota:abc"}))


# ═══ M：profile.load_target 显式 models=0 不被 `or 1` 改写 ═══
def _mk_mini_db(tmp_path):
    db = tmp_path / "mini.sqlite"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE units (id TEXT PRIMARY KEY, name_en TEXT, name_zh TEXT,
                            points_json TEXT, keywords_json TEXT);
        CREATE TABLE models (id INTEGER PRIMARY KEY, unit_id TEXT, name TEXT,
                             m TEXT, t TEXT, sv TEXT, invuln TEXT,
                             w TEXT, ld TEXT, oc TEXT);
        CREATE TABLE abilities (id INTEGER PRIMARY KEY, owner_id TEXT,
                                name_en TEXT, text_zh TEXT);
        INSERT INTO units VALUES ('u1', 'Probe Unit', NULL, NULL, NULL);
        INSERT INTO models (unit_id, name, m, t, sv, invuln, w, ld, oc)
        VALUES ('u1', 'Probe', '6"', '4', '3+', '-', '2', '6+', '1');
    """)
    conn.commit()
    conn.close()
    return db


def test_load_target_explicit_zero_models_not_rewritten(tmp_path):
    from engines.simulator.profile import load_target
    t = load_target(_mk_mini_db(tmp_path), "u1", models=0)
    assert t is not None
    assert t.models == 0               # 显式 0 保留 → sequence 退化目标语义（全零）


def test_load_target_none_models_falls_back_to_1(tmp_path):
    from engines.simulator.profile import load_target
    t = load_target(_mk_mini_db(tmp_path), "u1", models=None)
    assert t.models == 1               # 解析不出满编数才回退 1（原语义不变）


def test_explicit_zero_models_target_yields_all_zero_report():
    # 显式 0 模型守方 → 全零，不打幽灵模型（sequence 退化目标语义端到端）
    zero_tgt = TargetProfile(canonical_id="t", name_en="T", name_zh=None,
                             models=0, t=4, sv=4, invuln=None, w=2, oc=1)
    rep = simulate(_atk(), zero_tgt, Stance(), n=500, seed=3)
    assert rep.expected_damage == 0.0 and rep.expected_kills == 0.0


# ═══ M：守方非 hit 阶段 Effect 显式披露（不静默丢、不影响数值）═══
def test_unconsumed_defender_effect_surfaces_and_keeps_numbers():
    wound_eff = Effect("wound", "modify", (-1,), (), "某防守词条")
    base = simulate(_atk(), _tgt(), Stance(), n=2000, seed=7)
    with_eff = simulate(_atk(), _tgt(effects=(wound_eff,)), Stance(), n=2000, seed=7)
    joined = "；".join(with_eff.not_modeled + with_eff.bias_notes)
    assert "未消费" in joined and "wound" in joined       # 显式出现在报告注解
    assert with_eff.expected_damage == base.expected_damage   # 但不影响数值
    assert with_eff.funnel == base.funnel


def test_consumed_defender_effects_not_flagged():
    # fnp / damage_reduction / hit+modify 是被消费的三类，不得误报"未消费"
    effs = (Effect("fnp", "fnp", (5,), (), "feel no pain 5+"),
            Effect("damage", "damage_reduction", (1,), (), "damage reduction"),
            Effect("hit", "modify", (-1,), ("phase_shooting",), "stealth"))
    rep = simulate(_atk(), _tgt(effects=effs), Stance(), n=500, seed=11)
    assert not any("未消费" in nm for nm in rep.not_modeled + rep.bias_notes)
