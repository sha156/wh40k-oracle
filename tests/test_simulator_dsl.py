# tests/test_simulator_dsl.py
"""P7 DSL：bs_improve 通道 / condition 加固 / 攻方对账 / 载荷校验 / 注入成对语义。

蒙特卡洛比率断言沿用 test_simulator_abilities 范式：N=60000，手算期望值写在断言旁。
"""
from pathlib import Path

import pytest

from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Effect,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.dsl import DslError, inject_attacker, load_payload_file, parse_entry
from engines.simulator.engine import simulate
from engines.simulator.sequence import (
    ATTACKER_CONSUMED,
    KNOWN_CONDITION_TAGS,
    _cond_true,
    run_sequence,
    unconsumed_attacker_effect_notes,
)

N = 60000


def _weapon(bs=4, effects=()):
    return WeaponProfile(name_zh=None, name_en="test gun", range='24"',
                         attacks=DiceExpr(k=1), bs_ws=bs, strength=4, ap=0,
                         damage=DiceExpr(k=1), effects=tuple(effects), count=1)


def _attacker(w):
    return AttackerProfile(canonical_id="a1", name_en="A", name_zh=None,
                           models=1, loadout=(w,))


def _target(effects=()):
    return TargetProfile(canonical_id="t1", name_en="T", name_zh=None, models=5,
                         t=4, sv=6, invuln=None, w=1, oc=1, effects=tuple(effects))


def _hit_ratio(w, stance, target=None):
    raw = run_sequence(_attacker(w), target or _target(), stance, n=N, seed=42)
    return raw.hits.mean() / raw.attacks.mean()


_BS_IMPROVE = Effect("hit", "bs_improve", (1,), ("guided_vs_spotted",), "FTGG")
_HEAVY = Effect("hit", "modify", (1,), ("stationary",), "heavy")
_PSYCHIC = Effect("hit", "ignore_hit_mods", (), (), "psychic")


class TestBsImproveChannel:
    def test_guided_moves_expectation(self):
        # BS4+ 基线 0.5；guided → BS 特征值 3+ → P(hr∈{3..6})=4/6
        base = _hit_ratio(_weapon(effects=[_BS_IMPROVE]), Stance(phase="shooting"))
        on = _hit_ratio(_weapon(effects=[_BS_IMPROVE]),
                        Stance(phase="shooting", guided=True))
        assert base == pytest.approx(0.5, abs=0.02)
        assert on == pytest.approx(4 / 6, abs=0.02)

    def test_stacks_with_heavy_beyond_hit_mod_clamp(self):
        # 陷阱专项（spec 七-2①）：BS4+ + heavy(+1 命中修正) + guided(+1 BS 特征值)
        # 特征值层 BS→3+，修正层 +1（夹取内）→ hr+1≥3 → hr≥2 → 5/6≈0.833。
        # 若 bs_improve 被偷懒折进 hit modify，会被 ±1 夹取吞掉一档 → 只剩 4/6=0.667。
        r = _hit_ratio(_weapon(effects=[_BS_IMPROVE, _HEAVY]),
                       Stance(phase="shooting", guided=True, stationary=True))
        assert r == pytest.approx(5 / 6, abs=0.02)

    def test_psychic_keeps_bs_improve_voids_cover(self):
        # 陷阱专项②：PSYCHIC 只清负修正（两通道），bs_improve 正向保留；
        # 掩体（13.08=恶化 BS 1）被 PSYCHIC 无视（B6）→ 净 BS 3+ → 4/6
        r = _hit_ratio(_weapon(effects=[_BS_IMPROVE, _PSYCHIC]),
                       Stance(phase="shooting", guided=True, target_in_cover=True))
        assert r == pytest.approx(4 / 6, abs=0.02)

    def test_guided_cover_smoke_three_way(self):
        # 陷阱专项③：guided(+1 BS) × 掩体(-1 BS) × 守方减命中(-1 修正)
        # 特征值层净 0 → BS4+；修正层 -1 → hr-1≥4 → hr≥5 → 2/6≈0.333
        smoke_like = Effect("hit", "modify", (-1,), ("phase_shooting",), "debuff")
        r = _hit_ratio(_weapon(effects=[_BS_IMPROVE]),
                       Stance(phase="shooting", guided=True, target_in_cover=True),
                       target=_target(effects=[smoke_like]))
        assert r == pytest.approx(2 / 6, abs=0.02)

    def test_floor_emerges_from_unmodified_one(self):
        # 陷阱专项④：BS2+ + guided → 阈值 1+，由 hr!=1 涌现 5/6 上限（无需钳制）
        r = _hit_ratio(_weapon(bs=2, effects=[_BS_IMPROVE]),
                       Stance(phase="shooting", guided=True))
        assert r == pytest.approx(5 / 6, abs=0.02)

    def test_cover_alone_unchanged_after_channel_migration(self):
        # 掩体迁 BS 通道的回归护栏：单源场景数值与 S7（hit_neg 口径）等价
        r = _hit_ratio(_weapon(), Stance(phase="shooting", target_in_cover=True))
        assert r == pytest.approx(2 / 6, abs=0.02)      # BS4+ 恶化到 5+


class TestCondTrueHardening:
    def test_unknown_tag_raises(self):
        with pytest.raises(ValueError, match="未知 Effect condition tag"):
            _cond_true(("no_such_tag",), Stance(), _target())

    def test_all_registered_tags_evaluate(self):
        # 注册表与 _cond_true 分支不漂移：集合内逐 tag 求值不 raise
        _ARGS = {"target_has_keyword": ("X",),
                 "melee_target_has_keyword": ("monster",),   # P7-PR5 复合关键词 tag
                 "target_models_in_range": (1, 5),   # 带参 tag 用合法参数形状
                 "shooting_target_models_in_range": (1, 5)}
        for tag in KNOWN_CONDITION_TAGS:
            cond = (tag,) + _ARGS.get(tag, ())
            assert _cond_true(cond, Stance(), _target()) in (True, False)

    def test_models_in_range_bad_arity_raises(self):
        # P7-PR4：带参 tag 缺参不许静默 False（与未知 tag 同罪）
        with pytest.raises(ValueError, match="target_models_in_range"):
            _cond_true(("target_models_in_range",), Stance(), _target())


class TestAttackerReconciliation:
    def test_unconsumed_attacker_effect_disclosed(self):
        # op 合法（守方侧有）但攻方侧无消费点 → 强制披露不静默（评审 F4）
        bogus = Effect("fnp", "fnp", (5,), (), "misplaced")
        atk = _attacker(_weapon(effects=[bogus]))
        notes = unconsumed_attacker_effect_notes(atk)
        assert len(notes) == 1 and "misplaced" in notes[0]
        rep = simulate(atk, _target(), Stance(), n=200, seed=1)
        assert any("攻方 Effect 未消费" in x for x in rep.not_modeled)

    def test_registry_matches_engine(self):
        # bs_improve 已登记（白名单唯一真源护栏）
        assert ("hit", "bs_improve") in ATTACKER_CONSUMED


def _raw_entry(**over):
    raw = {
        "dsl_version": 1, "table": "abilities", "id": "000008439",
        "side": "attacker", "faction": "TAU", "detachment": None,
        "name_en": "For the Greater Good", "name_zh": "为了上上善道",
        "status": "partial",
        "effects": [{"phase": "hit", "op": "bs_improve", "params": [1],
                     "condition": ["guided_vs_spotted"], "source": "FTGG"}],
        "requires_toggles": ["guided"],
        "not_modeled_notes_zh": ["观察员机会成本未建模"],
        "provenance": {"text_sha256": "ab" * 32},
        "encoded_by": "test",
    }
    raw.update(over)
    return raw


class TestPayloadValidation:
    def test_valid_entry_parses(self):
        e = parse_entry(_raw_entry())
        assert e.status == "partial" and len(e.effects) == 1
        assert e.effects[0].op == "bs_improve"

    def test_unconsumed_op_rejected(self):
        raw = _raw_entry(effects=[{"phase": "wound", "op": "bs_improve",
                                   "params": [1], "condition": [], "source": "x"}])
        with pytest.raises(DslError, match="消费点白名单"):
            parse_entry(raw)

    def test_conjunction_condition_rejected(self):
        # 评审 F2：引擎只读 condition[0]，合取列表照录会静默丢第二条件
        raw = _raw_entry(effects=[{"phase": "hit", "op": "bs_improve", "params": [1],
                                   "condition": ["phase_shooting", "guided_vs_spotted"],
                                   "source": "x"}])
        with pytest.raises(DslError, match="合取"):
            parse_entry(raw)

    def test_unknown_version_rejected(self):
        with pytest.raises(DslError, match="dsl_version"):
            parse_entry(_raw_entry(dsl_version=2))

    def test_encoded_requires_effects(self):
        with pytest.raises(DslError, match="encoded"):
            parse_entry(_raw_entry(status="encoded", effects=[]))

    def test_partial_requires_notes(self):
        with pytest.raises(DslError, match="partial"):
            parse_entry(_raw_entry(not_modeled_notes_zh=[]))

    def test_effects_require_fingerprint(self):
        with pytest.raises(DslError, match="text_sha256"):
            parse_entry(_raw_entry(provenance={}))

    def test_target_side_with_effects_accepted_since_pr4(self):
        # 审查 H1 的 target 侧拒载已随 P7-PR4 inject_target 落地解除：
        # 守方向条目经 TARGET_CONSUMED 白名单校验后合法入载
        raw = _raw_entry(side="target",
                         effects=[{"phase": "fnp", "op": "fnp", "params": [5],
                                   "condition": [], "source": "x"}])
        entry = parse_entry(raw)
        assert entry.side == "target" and len(entry.effects) == 1

    def test_target_side_op_not_in_whitelist_rejected(self):
        # 守方侧消费点白名单仍然生效：攻方专属 op（wound+s_improve）出现在 target 侧 → 拒载
        raw = _raw_entry(side="target",
                         effects=[{"phase": "wound", "op": "s_improve", "params": [1],
                                   "condition": [], "source": "x"}])
        with pytest.raises(DslError, match="白名单"):
            parse_entry(raw)

    def test_dice_param_int_shorthand(self):
        # PR3 DiceExpr 约定：非负 int → 常量 DiceExpr（SUSTAINED HITS 1）
        raw = _raw_entry(effects=[{"phase": "hit", "op": "extra_hits", "params": [1],
                                   "condition": [], "source": "sustained"}])
        entry = parse_entry(raw)
        (eff,) = entry.effects
        assert eff.params == (DiceExpr(n=0, faces=0, k=1),)
        assert eff.params[0].is_constant

    def test_dice_param_object_form(self):
        # PR3 DiceExpr 约定：{"n","faces","k"} → NdM+K（如 D3）
        raw = _raw_entry(effects=[{"phase": "hit", "op": "extra_hits",
                                   "params": [{"n": 1, "faces": 3, "k": 0}],
                                   "condition": [], "source": "sustained d3"}])
        (eff,) = parse_entry(raw).effects
        assert eff.params == (DiceExpr(n=1, faces=3, k=0),)

    def test_dice_param_bad_shapes_rejected(self):
        # 负常量 / 键不齐 / bool / 有骰但 faces<2 —— 全拒载
        bads = [-1, True, {"n": 1, "faces": 3}, {"n": 1, "faces": 1, "k": 0},
                {"n": 1, "faces": 3, "k": 0, "extra": 1}, "d3"]
        for bad in bads:
            raw = _raw_entry(effects=[{"phase": "hit", "op": "extra_hits", "params": [bad],
                                       "condition": [], "source": "x"}])
            with pytest.raises(DslError):
                parse_entry(raw)

    def test_hit_reroll_params_fixed(self):
        # ("hit","reroll") 参数固定 ["fail"]（引擎=只重骰失败的最优策略）
        raw = _raw_entry(effects=[{"phase": "hit", "op": "reroll", "params": ["all"],
                                   "condition": [], "source": "x"}])
        with pytest.raises(DslError, match="fail"):
            parse_entry(raw)

    def test_string_int_param_rejected(self):
        # 审查 M3：params 形状校验——"1"（字符串）不是 int
        raw = _raw_entry(effects=[{"phase": "hit", "op": "bs_improve", "params": ["1"],
                                   "condition": ["guided_vs_spotted"], "source": "x"}])
        with pytest.raises(DslError, match="整数参数"):
            parse_entry(raw)

    def test_real_payload_file_parses(self):
        entries = load_payload_file(Path("dsl_payloads/tau.json"))
        assert len(entries) >= 1
        ftgg = next(e for e in entries if e.row_id == "000008439")
        assert ftgg.status == "partial" and ftgg.requires_toggles == ("guided",)


class TestInjection:
    def test_toggle_off_no_change_but_disclosed(self):
        entry = parse_entry(_raw_entry())
        atk, modeled, notes = inject_attacker(_attacker(_weapon()), [entry], frozenset())
        assert atk.loadout[0].effects == ()          # 未注入
        assert not modeled
        assert any("未启用" in x for x in notes)

    def test_toggle_on_injects_and_expectation_moves(self):
        # 评审 F7：encoded/partial 条目差分期望值必须动（0.5 → 4/6）
        entry = parse_entry(_raw_entry())
        atk, modeled, notes = inject_attacker(
            _attacker(_weapon()), [entry], frozenset({"guided"}))
        assert any("已施加" in x for x in modeled)
        assert any("未建模残量" in x for x in notes)
        stance = Stance(phase="shooting", guided=True)
        base = run_sequence(_attacker(_weapon()), _target(), stance, n=N, seed=7)
        on = run_sequence(atk, _target(), stance, n=N, seed=7)
        assert base.hits.mean() / base.attacks.mean() == pytest.approx(0.5, abs=0.02)
        assert on.hits.mean() / on.attacks.mean() == pytest.approx(4 / 6, abs=0.02)
