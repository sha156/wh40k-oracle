"""词条 → Effect 映射（P4-c，spec 第四节那张表的代码化）。

输入是 parse.tokenize_keywords 产出的 ParsedKeyword（已归一：小写、连字符→下划线、
带参解析）。输出三样：
  · effects：进 sequence.py 各阶段生效的 Effect 元组
  · modeled：本武器实际计入模拟的词条名（诚实声明用）
  · annotations：识别到但**本期不做数值**的词条（precision/pistol/… → 报告标注，不静默丢）
未识别词条（recognized=False）由上游 tokenize 收进 unparsed，不在此处理。

一次写好映射即全库生效；正确性靠 sequence.py 的每词条单测（test_simulator_keywords）。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from engines.simulator.contracts import DiceExpr, Effect
from engines.simulator.parse import ParsedKeyword

# 识别但本期只标注、不改数值的词条（spec 第四节：态势/点名/一次性/自伤）
_ANNOTATE = {
    "precision": "precision（点名附着角色未建模，会低估斩首，留 P5）",
    "pistol": "pistol（交战中可射击，单阶段模拟不体现；11版起并入 [CLOSE-QUARTERS]（24.07/10.06））",
    "close_quarters": "close quarters（11版24.07/10.06：交战中可射击，语义同 pistol，单阶段模拟不体现）",
    "assault": "assault（前进后可射击，态势标注）",
    "one_shot": "one shot（每局一次，单次激活不影响期望）",
    "extra_attacks": "extra attacks（作为 loadout 内独立武器已计入其攻击）",
    "hazardous": "hazardous（用后自伤未计入，会略高估攻方净收益）",
    "psychic": "psychic（标签透传，供 anti-psyker 交互）",
}


def _as_int(param) -> Optional[int]:
    if isinstance(param, int):
        return param
    if isinstance(param, DiceExpr) and param.is_constant:
        return param.k
    return None


def _dice_param(param, default_k: int) -> DiceExpr:
    """把词条参数统一成 DiceExpr（骰子式如 D3/D6+3 原样保留，供向量化采样）。

    rapid fire / melta / sustained 的 X 都可能是骰子（实测 rapid fire d6+3 等 13 把武器）——
    不能塌成常量，否则严重低估攻击/伤害。
    """
    if isinstance(param, DiceExpr):
        return param
    if isinstance(param, int):
        return DiceExpr(n=0, faces=0, k=param)
    return DiceExpr(n=0, faces=0, k=default_k)


def _dice_label(expr: DiceExpr) -> str:
    if expr.is_constant:
        return str(expr.k)
    core = f"{expr.n if expr.n > 1 else ''}D{expr.faces}"
    return core + (f"+{expr.k}" if expr.k else "")


def _sustained_param(param) -> Tuple:
    """sustained hits X：X 可为整数或骰子（如 d3）。统一存 DiceExpr 供向量化采样。"""
    return (_dice_param(param, 1),)


def keyword_to_effects(pk: ParsedKeyword) -> Tuple[List[Effect], List[str], List[str]]:
    """单个 ParsedKeyword → (effects, modeled, annotations)。"""
    name = pk.name
    src = pk.raw or name

    if name in _ANNOTATE:
        return [], [], [_ANNOTATE[name]]

    # ---- 攻击数 ----
    if name == "rapid_fire":
        x = _dice_param(pk.params[0] if pk.params else 1, 1)
        return ([Effect("attacks", "modify", (x,), ("half_range",), src)],
                [f"rapid fire {_dice_label(x)}"], [])
    if name == "blast":
        # 11版 24.05 [BLAST X]：每满 5 个目标模型 +X 攻击骰；
        # 无参写法（十版 [BLAST] / 既有 loadout）向后兼容为 X=1。
        x = _as_int(pk.params[0]) if pk.params else 1
        x = x if x and x > 0 else 1
        return ([Effect("attacks", "blast", (x,), (), src)],
                ["blast" if x == 1 else f"blast {x}"], [])
    if name == "cleave":
        # 11版 24.06 [CLEAVE X]（近战版 blast）：该单位全部近战攻击只选一个目标时，
        # 每满 5 个目标模型 +X 攻击骰。1v1 模拟天然满足「单目标」前提——效果说明如实注明。
        x = _as_int(pk.params[0]) if pk.params else 1
        x = x if x and x > 0 else 1
        return ([Effect("attacks", "blast", (x,), ("phase_melee",), src)],
                [f"cleave {x}（11版24.06；按 1v1 单目标前提计入）"], [])

    # ---- 命中 ----
    if name == "sustained_hits":
        p = pk.params[0] if pk.params else 1
        return ([Effect("hit", "extra_hits", _sustained_param(p), (), src)],
                ["sustained hits"], [])
    if name == "lethal_hits":
        return ([Effect("hit", "auto_wound", (), (), src)], ["lethal hits"], [])
    if name == "torrent":
        return ([Effect("hit", "auto_hit", (), (), src)], ["torrent"], [])
    if name == "heavy":
        # 11版 24.16 [HEAVY]：命中 +1 数值不变；触发条件放宽为「未交战 + 本回合未上场 +
        # 全员移动 ≤3"」。Stance.stationary 字段名沿用十版，但语义即上述 Heavy 条件
        #（见 contracts.Stance 注释与 CLI --stationary 帮助文案）。
        return ([Effect("hit", "modify", (1,), ("stationary",), src)], ["heavy"], [])
    if name == "conversion":
        return ([Effect("hit", "crit_threshold", (4,), ("long_range",), src)],
                ["conversion"], [])
    if name == "indirect_fire":
        # 11版 24.19 + 10.07：间接开火时目标获掩体（保留）；命中判定与 BS 无关——
        # 未修正 1-5 失败（仅 6 命中），命中修正与 ±1 夹紧均不适用；
        # 「本回合驻停 + 有友军可见目标」时改善为未修正 1-3 失败（4+ 命中）。
        # 模拟以 stance.stationary 作该复合条件的代理（效果说明里如实披露该假设）。
        # 11版另禁止间接开火重掷命中——引擎本就不建模命中重掷，无需处理。
        return ([Effect("hit", "indirect_fixed", (), ("indirect",), src),
                 Effect("save", "cover", (), ("indirect",), src)],
                ["indirect fire（11版24.19/10.07：未修正6+命中；"
                 "驻停开关=『驻停+有友军可见目标』代理→4+）"], [])

    # ---- 致伤 ----
    if name == "devastating_wounds":
        return ([Effect("wound", "mortal_pool", (), (), src)], ["devastating wounds"], [])
    if name == "twin_linked":
        return ([Effect("wound", "reroll", ("fail",), (), src)], ["twin-linked"], [])
    if name == "lance":
        return ([Effect("wound", "modify", (1,), ("charging",), src)], ["lance"], [])
    if name == "anti":
        # params = (keyword, N)：对含该 keyword 的目标，未修正 N+ 即暴击造伤
        if len(pk.params) >= 2:
            kw = str(pk.params[0]).strip().lower()
            n = _as_int(pk.params[1]) or 4
            return ([Effect("wound", "crit_threshold", (n,),
                            ("target_has_keyword", kw), src)],
                    [f"anti-{kw} {n}+"], [])
        return [], [], []

    # ---- 伤害 ----
    if name == "melta":
        x = _dice_param(pk.params[0] if pk.params else 0, 0)
        return ([Effect("damage", "modify", (x,), ("half_range",), src)],
                [f"melta {_dice_label(x)}"], [])

    # ---- 保存 ----
    if name == "ignores_cover":
        return ([Effect("save", "ignores_cover", (), (), src)], ["ignores cover"], [])

    # 已归一但未在上表的低频带参词条——标注不静默丢
    return [], [], [f"{src}（已识别未建模）"]


def build_weapon_effects(
    raw_keywords: Tuple[ParsedKeyword, ...],
) -> Tuple[Tuple[Effect, ...], List[str], List[str], List[str]]:
    """一把武器全部 raw_keywords → (effects, modeled, annotations, unparsed)。"""
    effects: List[Effect] = []
    modeled: List[str] = []
    annotations: List[str] = []
    unparsed: List[str] = []
    for pk in raw_keywords:
        if not pk.recognized:
            unparsed.append(pk.raw or pk.name)
            continue
        es, mod, ann = keyword_to_effects(pk)
        effects.extend(es)
        modeled.extend(mod)
        annotations.extend(ann)
    # B4（11版 24.23）披露：LETHAL HITS 已由强制改为可选——可放弃自动致伤，
    # 去搏 [DEVASTATING WOUNDS]/anti 的暴击致伤。本期不建模择优分支，仍按强制
    # 自动致伤口径结算；组合出现时如实披露偏差方向（低估）。
    names = {pk.name for pk in raw_keywords if pk.recognized}
    if "lethal_hits" in names and ({"devastating_wounds", "anti"} & names):
        annotations.append(
            "11版 LETHAL HITS（24.23）可选放弃自动致伤以搏暴击致伤：本模拟按强制"
            "自动致伤口径，lethal+dev/anti 组合可能低估伤害")
    return tuple(effects), modeled, annotations, unparsed
