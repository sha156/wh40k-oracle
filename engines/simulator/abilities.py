"""P5-a：单位技能分类器（纯逻辑，只依赖 stdlib + contracts）。

数据现实（开工二次实测，见 spec 零节 T1）：
  · 核心 USR（Feel No Pain/Stealth/Lone Operative…）只以词典行存在，不按单位挂载；
  · 每个单位的防守技能是自由 HTML 文本，高度条件化（"While the Waaagh! active…"/
    "…against Psychic attacks"/光环授予他人）。
  · 唯一干净可自动的防守数值是 invuln（models 表结构化，P4 已读）。

据此本模块**不自动施加任何技能**——它把每条技能分到桶里：
  · toggle_defensive：可建模的防守 USR（FNP X / Stealth / 减伤），解析出参数 + 条件标注，
    产出一个"若启用则施加"的 Effect；**默认不施加**，由 options/面板 opt-in。
  · nm_*：精确的未建模分类（选取/部署/士气/死亡爆炸/光环依附/其它），取代 P4 那句
    笼统的"abilities 全表未建模"。

铁律（spec 二节 + 评审 N3）：宁漏不错；FNP 不叠加（每点伤害只掷一次，取最优阈值）。
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from engines.simulator.contracts import AbilityRecord, Effect

# ── 分类桶常量 ───────────────────────────────────────────────
CAT_TOGGLE_DEF = "toggle_defensive"
CAT_NM_TARGETING = "nm_targeting"
CAT_NM_DEPLOYMENT = "nm_deployment"
CAT_NM_MORALE = "nm_morale"
CAT_NM_ONDEATH = "nm_ondeath"
CAT_NM_AURA_LEADER = "nm_aura_leader"
CAT_NM_OTHER = "nm_other"

# not_modeled 桶 → 中文披露标签
_NM_LABEL = {
    CAT_NM_TARGETING: "选取规则",
    CAT_NM_DEPLOYMENT: "部署/移动",
    CAT_NM_MORALE: "士气/Battle-shock",
    CAT_NM_ONDEATH: "死亡触发",
    CAT_NM_AURA_LEADER: "光环/依附",
    CAT_NM_OTHER: "其它",
}

# 条件词：命中任一则该防守技能视为"条件式/光环式"，不能无脑全局施加
# （"whilst" 是 "while" 的英式变体，不含子串 "while"，必须单列——评审 M#4）
_CONDITION_TOKENS = ("while", "whilst", "against", "aura", "within", "each time",
                     "if ", "psychic", "mortal", "once per", "contains")

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_FNP_RE = re.compile(r"feel\s+no\s+pain\s*(\d)\s*\+", re.IGNORECASE)


def clean_text(raw: Optional[str]) -> str:
    """Wahapedia HTML → 纯文本（去标签 + 反转义 + 压空白）。"""
    if not raw:
        return ""
    return _WS_RE.sub(" ", html.unescape(_HTML_TAG_RE.sub(" ", raw))).strip()


@dataclass(frozen=True)
class ClassifiedAbility:
    """一条技能的分类结果。"""
    name: str
    category: str                    # CAT_* 之一
    detail: str                      # 中文披露说明
    effect: Optional[Effect] = None  # toggle_defensive：若启用则施加的 Effect（默认不施加）
    conditional: bool = False        # 防守技能是否带条件（against/aura/while…）
    params: Tuple = ()               # 解析出的参数（如 FNP 阈值 X）


@dataclass
class AbilityClassification:
    """一个单位全部技能的分类。total 用于对账（各桶之和必须 == 原始条数）。"""
    total: int = 0
    toggle_defensive: List[ClassifiedAbility] = field(default_factory=list)
    not_modeled: List[ClassifiedAbility] = field(default_factory=list)

    def bucket_count(self) -> int:
        return len(self.toggle_defensive) + len(self.not_modeled)

    def not_modeled_by_category(self) -> List[str]:
        """精确 not_modeled 披露行：'未建模·<类别>：技能A、技能B'。"""
        groups: dict = {}
        for ca in self.not_modeled:
            groups.setdefault(ca.category, []).append(ca.name)
        out: List[str] = []
        for cat, names in groups.items():
            label = _NM_LABEL.get(cat, cat)
            uniq = list(dict.fromkeys(n for n in names if n))
            if uniq:
                out.append(f"未建模·{label}：" + "、".join(uniq[:12])
                           + ("…" if len(uniq) > 12 else ""))
        return out

    def toggle_summaries(self) -> List[Tuple[str, str, bool]]:
        """surface 用：(技能名, 一句话, 是否已解析出参数)。"""
        out: List[Tuple[str, str, bool]] = []
        for ca in self.toggle_defensive:
            out.append((ca.name, ca.detail, bool(ca.params)))
        return out


# ── 单条技能分类（首个匹配的桶生效）─────────────────────────────
def _is_conditional(text_lower: str) -> bool:
    return any(tok in text_lower for tok in _CONDITION_TOKENS)


def _condition_hint(low: str) -> str:
    """把条件式防守技能的条件类型讲清楚（评审 M#5：模拟器只算普通射击/近战，
    "仅对灵能/致命伤"的 FNP 若被启用会错误地对普通攻击减伤，须明示）。"""
    if "against" in low and ("psychic" in low or "mortal" in low):
        return "仅对灵能/致命伤等特定攻击——本模拟为普通攻击，多半不适用"
    if "against" in low:
        return "仅对特定攻击类型，需确认适用"
    if "aura" in low or "within" in low or ("friendly" in low and "within" in low):
        return "光环/范围授予他人，持有者未必自带"
    if any(t in low for t in ("whilst", "while", "contains", "once per")):
        return "限定条件（回合/编成/每场一次），需确认适用"
    return "条件式，需确认适用"


def classify_ability(rec: AbilityRecord) -> ClassifiedAbility:
    name = (rec.name_en or "").strip()
    text = rec.text or ""
    low = text.lower()
    nlow = name.lower()

    # ── ① Feel No Pain（可建模防守，一律 toggle）────────────────
    m = _FNP_RE.search(text)
    if m or "feel no pain" in low:
        x = int(m.group(1)) if m else None
        cond = _is_conditional(low)
        eff = Effect("fnp", "fnp", (x,), (), f"feel no pain {x}+") if x else None
        detail = (f"无痛 {x}+" if x else "无痛（未解析出阈值）")
        detail += f"（{_condition_hint(low)}）" if cond else "（可开关启用）"
        return ClassifiedAbility(name or "Feel No Pain", CAT_TOGGLE_DEF, detail,
                                 effect=eff, conditional=cond,
                                 params=((x,) if x else ()))

    # ── ② Stealth / 掩蔽类（守方 → 攻方射击命中 -1，仅射击）──────
    #   核心 USR「Stealth」（name 精确命中）= 无条件；文本模式必须是【守方防守】框架：
    #   -1 施加在"对【本单位】发起的攻击"上，而非本单位对敌方施加的压制（评审 HIGH#3：
    #   "Rivetin' Dakka" 是压制敌方的进攻技能，含 "enemy"，绝不能当成本单位的 Stealth）。
    #   判别（实测 230 条 "subtract 1" 挂载技能的措辞得来）：
    #   防守型 = "attack targets this unit/model / that unit" 或 "made against it"（-1 施加在
    #   打【本单位】的攻击上）；进攻型压制 = "makes an attack, subtract 1"（-1 施加在被压制敌方
    #   发起的攻击上）——后者不含"targets this/that unit"框架，靠正向措辞即可精确区分。
    #   进攻型压制签名："…makes an attack, subtract 1 from the Hit roll"（-1 施加在被压制敌方
    #   身上）——即便同一技能别处出现"targets that unit"（如 Psychological Saboteur 的增益句），
    #   只要含此签名就不是本单位的防守 Stealth，直接排除。
    _is_core_stealth = nlow == "stealth"
    _defensive_frame = any(s in low for s in (
        "targets this unit", "targets this model", "targets that unit",
        "made against it", "made against this"))
    _offensive_minus = ("makes an attack, subtract 1" in low
                        or "makes a ranged attack, subtract 1" in low)
    _text_minus_hit = ("subtract 1 from" in low and "hit roll" in low
                       and _defensive_frame and not _offensive_minus)
    if _is_core_stealth or _text_minus_hit:
        eff = Effect("hit", "modify", (-1,), ("phase_shooting",), "stealth")
        cond = (not _is_core_stealth) and _is_conditional(low)
        detail = ("潜行：守方全员具备时，攻方射击命中 -1（近战不生效）"
                  if _is_core_stealth else
                  "射击命中 -1（掩蔽/潜行类）" + ("（条件式，需确认适用）" if cond else "（可开关启用）"))
        return ClassifiedAbility(name or "Stealth", CAT_TOGGLE_DEF, detail,
                                 effect=eff, conditional=cond, params=(-1,))

    # ── ③a 伤害减半（乘法/向上取整）——引擎的加法减伤无法表示，绝不塌成 -1（评审 HIGH#2）
    if "halve" in low and "damage" in low:
        return ClassifiedAbility(name or "Halve Damage", CAT_NM_OTHER,
                                 "伤害减半（乘法/向上取整，引擎的加法减伤无法表示，未建模）")

    # ── ③b 加法减伤（reduce … Damage … by 1）——收紧到显式 "by 1/one"，不用裸 " 1"（评审 LOW#8）
    if "damage" in low and "reduc" in low and ("by 1" in low or "by one" in low):
        eff = Effect("damage", "damage_reduction", (1,), (), "damage reduction")
        cond = _is_conditional(low)
        return ClassifiedAbility(name or "Damage Reduction", CAT_TOGGLE_DEF,
                                 "受到伤害 -1" + ("（条件式，需确认适用）" if cond else "（可开关启用）"),
                                 effect=eff, conditional=cond, params=(1,))

    # ── not_modeled 精确分桶（按优先级）─────────────────────────
    if ("lone operative" in nlow or "lone operative" in low
            or "can only be selected as the target" in low
            or "cannot be selected as the target" in low):
        return ClassifiedAbility(name or "Lone Operative", CAT_NM_TARGETING,
                                 "选取限制（单场景对战不涉及目标选取）")

    if any(t in nlow for t in ("scouts", "infiltrators", "deep strike")) or \
       any(t in low for t in ("deep strike", "set up ", "reinforcements",
                              "at the end of your deployment")):
        return ClassifiedAbility(name or "Deployment", CAT_NM_DEPLOYMENT,
                                 "部署/移动技能（不影响单次攻击序列）")

    if any(t in nlow for t in ("synapse", "shadow in the warp")) or \
       any(t in low for t in ("battle-shock", "leadership test",
                              "shadow in the warp")):
        return ClassifiedAbility(name or "Morale", CAT_NM_MORALE,
                                 "士气/Battle-shock（P4 起明确不建模）")

    if "deadly demise" in nlow or "deadly demise" in low or \
       "when this" in low and "is destroyed" in low:
        return ClassifiedAbility(name or "Deadly Demise", CAT_NM_ONDEATH,
                                 "死亡触发（需多单位战场，单场景不建模）")

    if ("leader" == nlow or "aura" in nlow or "aura" in low
            or "while within" in low or "friendly" in low and "within" in low):
        return ClassifiedAbility(name or "Aura/Leader", CAT_NM_AURA_LEADER,
                                 "光环/依附（范围与附着建模留 P6+）")

    return ClassifiedAbility(name or "(unnamed)", CAT_NM_OTHER,
                             "未归类技能（未建模，原名保留披露）")


def classify_records(records: Tuple[AbilityRecord, ...]) -> AbilityClassification:
    """一个单位全部技能 → 分类。保证各桶之和 == len(records)（不静默丢）。"""
    result = AbilityClassification(total=len(records))
    for rec in records:
        ca = classify_ability(rec)
        if ca.category == CAT_TOGGLE_DEF:
            result.toggle_defensive.append(ca)
        else:
            result.not_modeled.append(ca)
    return result
