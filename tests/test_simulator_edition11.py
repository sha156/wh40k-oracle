"""11 版词条语义修正回归（S3，2026-07-10）。

对照 docs/superpowers/specs/2026-07-10-edition-11-usr-audit.md 的 B/C 类结论：
  B1 Stealth（24.33）掩体化——见 test_simulator_abilities.py 的端到端组；
  B2 Indirect Fire（24.19+10.07）固定未修正阈值（6+/驻停代理 4+），修正不适用、6 仍暴击；
  B3 Heavy（24.16）数值不变、条件语义放宽（文案级，既有 heavy 测试仍有效）；
  B5 Blast X（24.05）带参形态 + 无参向后兼容；
  C  Cleave X（24.06）近战版 blast（1v1 单目标前提）；
  B4 Lethal Hits（24.23）改可选——不建模择优，lethal+dev/anti 组合必须披露口径；
  B6 Psychic（24.29）无视不利命中修正——11 版新增（十版原文明言"没有直接的效果"）；
  B7 close_quarters 词库识别 + pistol 注解并入说明；
  A 类保留项收口：dev 致命池不吃「受伤-1」减伤（24.10 暴击致伤即结束攻击序列 +
  06.02 致命伤逐点直接施加，从未进入伤害分配步骤）；
  核心战略：Smokescreen=纯掩体、Go to Ground 已移除（端到端见 test_simulator_wiring）。
"""
from __future__ import annotations

import pytest

from engines.simulator.contracts import (
    AttackerProfile,
    DiceExpr,
    Effect,
    Stance,
    TargetProfile,
    WeaponProfile,
)
from engines.simulator.engine import simulate
from engines.simulator.keywords import build_weapon_effects, keyword_to_effects
from engines.simulator.parse import tokenize_keywords
from engines.simulator.sequence import run_sequence

N = 120_000
SEED = 20260710


def const(k):
    return DiceExpr(n=0, faces=0, k=k)


def kw(s):
    """词条串 → effects（走真实 parse+mapping 链）。"""
    parsed, _ = tokenize_keywords('["' + s + '"]')
    effects, _mod, _ann, _unp = build_weapon_effects(tuple(parsed))
    return effects


def weapon(attacks, bs_ws, strength, ap, damage, effects=(), melee=False,
           count=1, raw_keywords=()):
    return WeaponProfile(
        name_zh=None, name_en="W", range="Melee" if melee else "24",
        attacks=attacks, bs_ws=bs_ws, strength=strength, ap=ap,
        damage=damage, effects=tuple(effects), count=count,
        raw_keywords=tuple(raw_keywords))


def atk(w):
    return AttackerProfile(canonical_id="A", name_en="A", name_zh=None,
                           models=1, loadout=(w,), keywords=frozenset())


def tgt(t, sv, w, models, invuln=None, keywords=(), effects=()):
    return TargetProfile(canonical_id="T", name_en="T", name_zh=None,
                         models=models, t=t, sv=sv, invuln=invuln, w=w, oc=1,
                         keywords=frozenset(keywords), effects=tuple(effects))


def st(phase="shooting", cover=False, stationary=False, indirect=False):
    return Stance(phase=phase, stationary=stationary,
                  target_in_cover=cover, indirect=indirect)


def run(w, t, s):
    return run_sequence(atk(w), t, s, n=N, seed=SEED)


def close(got, exp, rel=0.02, absol=0.03):
    return abs(got - exp) <= max(absol, abs(exp) * rel)


# ===================== B2 Indirect Fire（24.19 + 10.07）=====================
def test_indirect_mapping_no_more_minus1():
    # 旧十版口径（命中 -1 modify）必须已删除，改为固定阈值 op + 掩体
    pk = tokenize_keywords('["indirect fire"]')[0][0]
    effects, mod, _ann = keyword_to_effects(pk)
    ops = {(e.phase, e.op) for e in effects}
    assert ("hit", "indirect_fixed") in ops
    assert ("save", "cover") in ops
    assert ("hit", "modify") not in ops


def test_indirect_stationary_proxy_hits_4up():
    # 「本回合驻停 + 有友军可见目标」以 stance.stationary 为代理 → 未修正 4+ 命中
    w = weapon(const(60), 3, 8, 0, const(1), effects=kw("indirect fire"))
    t = tgt(4, 7, 1, 800)
    assert close(run(w, t, st(indirect=True, stationary=True)).hits.mean(),
                 60 * 3 / 6, rel=0.02)
    assert close(run(w, t, st(indirect=True, stationary=False)).hits.mean(),
                 60 * 1 / 6, rel=0.03)


def test_indirect_unmodified_6_still_crit():
    # 未修正 6 仍是暴击命中：sustained hits 2 在间接开火下照常触发额外命中
    w = weapon(const(60), 3, 4, 0, const(1),
               effects=kw("indirect fire, sustained hits 2"))
    t = tgt(4, 7, 1, 800)
    hits = run(w, t, st(indirect=True)).hits.mean()
    assert close(hits, 60 * (1 / 6) + 60 * (1 / 6) * 2, rel=0.03)   # 10 + 20


def test_indirect_immune_to_hit_modifiers():
    # 命中修正对 indirect 攻击不适用：守方 -1 减命中不改变 6+ 固定阈值
    minus1 = Effect("hit", "modify", (-1,), ("phase_shooting",), "smokescreen")
    w = weapon(const(60), 3, 8, 0, const(1), effects=kw("indirect fire"))
    t = tgt(4, 7, 1, 800, effects=(minus1,))
    assert close(run(w, t, st(indirect=True)).hits.mean(), 60 * 1 / 6, rel=0.03)


def test_indirect_heavy_bonus_not_applied_to_threshold():
    # heavy 的 +1 属命中修正 → 对 indirect 固定阈值同样不适用（驻停时仍是 4+ 而非 3+）
    w = weapon(const(60), 3, 8, 0, const(1), effects=kw("indirect fire, heavy"))
    t = tgt(4, 7, 1, 800)
    assert close(run(w, t, st(indirect=True, stationary=True)).hits.mean(),
                 60 * 3 / 6, rel=0.02)


# ===================== B5 Blast X（24.05）=====================
def test_blast_x_param_scales_per_5_models():
    # [BLAST 2]：每满 5 个目标模型 +2 攻击骰
    w = weapon(const(2), 3, 4, 0, const(1), effects=kw("blast 2"))
    assert close(run(w, tgt(4, 7, 1, 20), st()).attacks.mean(), 2 + 2 * 4)
    assert close(run(w, tgt(4, 7, 1, 4), st()).attacks.mean(), 2)   # <5 模型无加成


def test_blast_bare_defaults_to_x1():
    # 无参写法（十版 [BLAST] / 既有 loadout）向后兼容为 X=1
    pk = tokenize_keywords('["blast"]')[0][0]
    (e,), mod, _ann = keyword_to_effects(pk)
    assert e.op == "blast" and e.params == (1,)
    assert mod == ["blast"]
    w = weapon(const(2), 3, 4, 0, const(1), effects=kw("blast"))
    assert close(run(w, tgt(4, 7, 1, 12), st()).attacks.mean(), 2 + 2)


# ===================== C Cleave X（24.06）=====================
def test_mapping_cleave_is_melee_conditioned_blast():
    pk = tokenize_keywords('["cleave 2"]')[0][0]
    (e,), mod, _ann = keyword_to_effects(pk)
    assert e.phase == "attacks" and e.op == "blast"
    assert e.params == (2,) and e.condition == ("phase_melee",)
    assert any("cleave 2" in m for m in mod)
    assert any("单目标" in m for m in mod)          # 1v1 前提如实注明


def test_cleave_adds_attacks_in_melee():
    # 近战全部攻击只打一个目标时每满5模型+X——1v1 模拟天然满足单目标前提
    w = weapon(const(2), 3, 4, 0, const(1), effects=kw("cleave 2"), melee=True)
    assert close(run(w, tgt(4, 7, 1, 20), st(phase="melee")).attacks.mean(),
                 2 + 2 * 4)


def test_cleave_not_applied_outside_melee():
    # 条件 phase_melee：射击阶段不生效
    w = weapon(const(2), 3, 4, 0, const(1), effects=kw("cleave 2"))
    assert close(run(w, tgt(4, 7, 1, 20), st()).attacks.mean(), 2)


# ===================== B4 Lethal Hits 改可选 → 组合披露（24.23）=====================
_LETHAL_NOTE_KEY = "LETHAL HITS"


def test_lethal_plus_dev_discloses_forced_autowound_bias():
    parsed, _ = tokenize_keywords('["lethal hits, devastating wounds"]')
    _e, _m, ann, _u = build_weapon_effects(tuple(parsed))
    assert any(_LETHAL_NOTE_KEY in a and "低估" in a for a in ann)


def test_lethal_plus_anti_discloses_forced_autowound_bias():
    parsed, _ = tokenize_keywords('["lethal hits, anti-vehicle 4+"]')
    _e, _m, ann, _u = build_weapon_effects(tuple(parsed))
    assert any(_LETHAL_NOTE_KEY in a for a in ann)


def test_lethal_alone_or_dev_alone_no_disclosure():
    for s in ('["lethal hits"]', '["devastating wounds"]'):
        parsed, _ = tokenize_keywords(s)
        _e, _m, ann, _u = build_weapon_effects(tuple(parsed))
        assert not any(_LETHAL_NOTE_KEY in a for a in ann), s


def test_simulate_report_carries_lethal_dev_disclosure():
    # 端到端：披露经 context.build_not_modeled 进 SimReport.not_modeled
    parsed, _ = tokenize_keywords('["lethal hits, devastating wounds"]')
    effects, _m, _a, _u = build_weapon_effects(tuple(parsed))
    w = weapon(const(4), 3, 4, 0, const(1), effects=effects, raw_keywords=parsed)
    rep = simulate(atk(w), tgt(4, 4, 1, 5), st(), n=500, seed=1)
    assert any(_LETHAL_NOTE_KEY in s for s in rep.not_modeled)


# ===================== B6 Psychic（24.29）=====================
def test_psychic_mapping_is_ignore_hit_mods():
    pk = tokenize_keywords('["psychic"]')[0][0]
    (e,), mod, ann = keyword_to_effects(pk)
    assert e.phase == "hit" and e.op == "ignore_hit_mods"
    assert any("24.29" in m for m in mod)
    assert ann == []                      # 不再是纯注解词条


def test_psychic_cancels_negative_hit_modifier():
    # 守方 -1 减命中：psychic 武器无视之（BS3+ 从 3/6 回到 4/6）
    minus1 = Effect("hit", "modify", (-1,), ("phase_shooting",), "hit penalty")
    w_plain = weapon(const(60), 3, 4, 0, const(1))
    w_psy = weapon(const(60), 3, 4, 0, const(1), effects=kw("psychic"))
    t = tgt(4, 7, 1, 800, effects=(minus1,))
    assert close(run(w_plain, t, st()).hits.mean(), 60 * 3 / 6, rel=0.02)
    assert close(run(w_psy, t, st()).hits.mean(), 60 * 4 / 6, rel=0.02)


def test_psychic_keeps_positive_hit_modifier():
    # 按有利方向：忽略守方 -1、保留 heavy +1 → BS3+ 驻停 = 5/6 命中
    minus1 = Effect("hit", "modify", (-1,), ("phase_shooting",), "hit penalty")
    w = weapon(const(60), 3, 4, 0, const(1), effects=kw("psychic, heavy"))
    t = tgt(4, 7, 1, 800, effects=(minus1,))
    assert close(run(w, t, st(stationary=True)).hits.mean(), 60 * 5 / 6, rel=0.02)


def test_psychic_noop_without_modifiers():
    # 无任何修正时 psychic 不改变数学（BS3+ 仍 4/6）
    w = weapon(const(60), 3, 4, 0, const(1), effects=kw("psychic"))
    assert close(run(w, tgt(4, 7, 1, 800), st()).hits.mean(), 60 * 4 / 6, rel=0.02)


# ===================== Benefit of Cover（13.08）+ B6 掩体×灵能 =====================
def test_cover_worsens_bs_by_one():
    # 11版 13.08：掩体收益 = 恶化攻方 BS 1（射击）。BS3+ 进掩体 → 4+（4/6 → 3/6）
    w = weapon(const(60), 3, 4, 0, const(1))
    t = tgt(4, 7, 1, 800)                        # sv=7 无保存，隔离命中效果
    assert close(run(w, t, st()).hits.mean(), 60 * 4 / 6, rel=0.02)
    assert close(run(w, t, st(cover=True)).hits.mean(), 60 * 3 / 6, rel=0.02)


def test_cover_bs_penalty_ignored_by_ignores_cover():
    # 武器带 [IGNORES COVER]（24.18）→ 掩体的 BS 惩罚被整体抵消，命中回到 BS3+（4/6）
    w = weapon(const(60), 3, 4, 0, const(1), effects=kw("ignores cover"))
    t = tgt(4, 7, 1, 800)
    assert close(run(w, t, st(cover=True)).hits.mean(), 60 * 4 / 6, rel=0.02)


def test_psychic_ignores_cover_bs_penalty():
    # B6（24.29 × 13.08）：掩体在 11 版是 BS 修正 → [PSYCHIC] 武器可无视该惩罚
    w_plain = weapon(const(60), 3, 4, 0, const(1))
    w_psy = weapon(const(60), 3, 4, 0, const(1), effects=kw("psychic"))
    t = tgt(4, 7, 1, 800)
    # 普通武器进掩体：BS3+ → 4+（3/6）
    assert close(run(w_plain, t, st(cover=True)).hits.mean(), 60 * 3 / 6, rel=0.02)
    # psychic 武器进掩体：无视掩体 BS 惩罚 → 回到 BS3+（4/6）
    assert close(run(w_psy, t, st(cover=True)).hits.mean(), 60 * 4 / 6, rel=0.02)


# ===================== A 类收口：dev 致命池不吃减伤（24.10 + 06.02）=====================
def test_dev_mortal_pool_ignores_damage_reduction():
    # 「受伤-1」只作用于正常伤害（3→2）；dev 暴击致伤的致命伤仍按 D=3
    #（24.10：暴击致伤即结束攻击序列、直接施加致命伤，从未进入伤害分配步骤）
    import numpy as np

    from engines.simulator.sequence import _wound_save_damage

    rng = np.random.default_rng(7)
    mask = np.ones((2000, 8), dtype=bool)
    normal_dmg, mortal_dmg, *_ = _wound_save_damage(
        mask, rng, 2000, 4, 6, 0, False, True,   # wt=4, crit=6, has_dev=True
        7, const(3), None, 1)                    # sv 7=无保存, D=3, 减伤 1
    assert set(np.unique(normal_dmg[normal_dmg > 0])) == {2}
    assert set(np.unique(mortal_dmg[mortal_dmg > 0])) == {3}


# ===================== B7 close_quarters / pistol 注解（24.07 + 10.06）=====================
def test_close_quarters_recognized_as_annotation():
    pk = tokenize_keywords('["close quarters"]')[0][0]
    assert pk.recognized and pk.name == "close_quarters"
    e, mod, ann = keyword_to_effects(pk)
    assert e == [] and mod == []
    assert ann and "close quarters" in ann[0]


def test_pistol_annotation_mentions_close_quarters_merge():
    e, mod, ann = keyword_to_effects(tokenize_keywords('["pistol"]')[0][0])
    assert ann and "CLOSE-QUARTERS" in ann[0]
