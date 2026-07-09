"""L4-1 模拟引擎的零依赖数据契约。

本模块**只有数据类，没有逻辑，不 import sqlite3 / app / streamlit / numpy**。
这样 sequence.py / report.py 只依赖它即可脱库单测，P8 FastAPI 也能直接复用（见
docs/superpowers/specs/2026-07-09-p4-monte-carlo-simulator-design.md 第五/六节）。

装载在 profile.py、组装在 assembly.py、词条→Effect 映射在 keywords.py（P4-c）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class DiceExpr:
    """声明式骰子表达式 NdM+K（非采样闭包，故可哈希、可作缓存 key）。

    常量（如 A=3、AP=-1）记为 n=0, faces=0, k=常量。
    随机（如 A=D6+3）记为 n=1, faces=6, k=3；2D6 记为 n=2, faces=6, k=0。
    向量化采样与期望值由 parse.py 的 sample_dice / expected_dice 解释。
    """
    n: int = 0
    faces: int = 0
    k: int = 0

    @property
    def is_constant(self) -> bool:
        return self.n == 0 or self.faces <= 1


@dataclass(frozen=True)
class Effect:
    """武器词条与防守开关的统一表示（P5 的技能/CP/光环也产出同型 Effect）。

    op 语义在 keywords.py（P4-c）与 sequence.py（P4-b/c）里解释；本契约只承载数据。
    """
    phase: str                       # attacks|hit|wound|save|damage|fnp
    op: str                          # modify|reroll|crit_threshold|extra_hits|auto_wound|skip_save|mortal_pool|fnp|damage_reduction|...
    params: Tuple = ()               # 声明式参数（可含 DiceExpr）
    condition: Tuple = ()            # 生效条件（("target_has_keyword","vehicle") / ("half_range",) / ("stationary",) / ("charging",) / ("ap0",) …）
    source: str = ""                 # 来源标签（词条名/开关名），用于报告的 modeled_effects


@dataclass(frozen=True)
class AbilityRecord:
    """单位挂载的一条技能原料（P5-a）：英文名 + 已清洗正文。

    纯数据，零逻辑——分类语义在 abilities.py（保持 contracts 零依赖）。
    """
    name_en: str
    text: str = ""


@dataclass(frozen=True)
class WeaponProfile:
    """单把武器 profile。同名多 profile（远近双模式）按 range + phase 区分。"""
    name_zh: Optional[str]
    name_en: str
    range: str                       # 'Melee' 或数字射程字符串
    attacks: DiceExpr
    bs_ws: Optional[int]             # None = 自动命中（torrent，源值 N/A）
    strength: int
    ap: int                          # 存负值（-1/-2），方向：越负穿甲越强
    damage: DiceExpr
    effects: Tuple = ()              # tuple[Effect]，P4-c 由 raw_keywords 映射填充
    count: int = 1                   # 该 loadout 中持此武器的模型/武器数（装配层填）
    raw_keywords: Tuple = ()         # tuple[ParsedKeyword]，P4-a 分词产物；P4-c 映射成 effects

    @property
    def is_melee(self) -> bool:
        return self.range.strip().lower() == "melee"


@dataclass(frozen=True)
class AttackerProfile:
    """可开火单位 = 模型数 + loadout（C1：武器表是选项池，装配层负责组装）。"""
    canonical_id: str
    name_en: str
    name_zh: Optional[str]
    models: int
    loadout: Tuple                   # tuple[WeaponProfile]（每把带 count）
    keywords: frozenset = frozenset()  # 单位关键词（lance/conversion 等态势判定用）


@dataclass(frozen=True)
class TargetProfile:
    """守方单位。94 个混编单位有多 model 行，用 model_rows 承载。"""
    canonical_id: str
    name_en: str
    name_zh: Optional[str]
    models: int                      # 满编模型数（装配层从 points desc 解析）
    t: int
    sv: int
    invuln: Optional[int]            # 存优；None 表示无无效保护
    w: int
    oc: int
    keywords: frozenset = frozenset()  # 供 anti-X / blast 判定
    model_rows: Tuple = ()           # tuple[dict]：混编单位的多 model 行（单一时为空）
    effects: Tuple = ()              # options 手动防守开关（FNP/减伤/掩体/Stealth）→ Effect
    abilities: Tuple = ()            # tuple[AbilityRecord]：P5-a 挂载技能原料，供分类披露（不自动施加）


@dataclass(frozen=True)
class Stance:
    """一次对战的态势开关（渲染成面板可调项）。"""
    phase: str = "shooting"          # shooting|melee
    charging: bool = False
    stationary: bool = False
    half_range: bool = False         # 距离档：是否在半射程内（rapid fire / melta 触发）
    target_in_cover: bool = False
    long_range: bool = False         # 目标完全在 12"/24" 外（conversion 暴击命中阈值下调触发）
    indirect: bool = False           # 以间接火力开火（indirect fire：命中 -1 且目标获掩体）


@dataclass(frozen=True)
class SimContext:
    attacker: AttackerProfile
    target: TargetProfile
    stance: Stance
    effects: Tuple = ()              # 【通用通道】按 phase 分桶的全部生效 Effect（词条+防守+态势）；P5 只往这里加生产者
    toggles_available: Tuple = ()    # 【纯 UI 提示】未挂载的可选增益，不承担效果挂载
    not_modeled: Tuple = ()          # 已知但未建模的技能/机制名清单


@dataclass
class SimReport:
    expected_damage: float = 0.0
    expected_kills: float = 0.0
    wipe_probability: float = 0.0
    distribution: dict = field(default_factory=dict)   # {p10,p50,p90,histogram}
    funnel: dict = field(default_factory=dict)          # attacks→hits→wounds→unsaved→final
    efficiency: dict = field(default_factory=dict)      # 每100点期望伤害/击杀（按模拟模型数选档）
    reverse: Optional["SimReport"] = None               # 反向视角（守方按幸存模型数反打）
    modeled_effects: List[str] = field(default_factory=list)
    not_modeled: List[str] = field(default_factory=list)
    bias_notes: List[str] = field(default_factory=list)
    sensitivity_hint: List[str] = field(default_factory=list)
    seed: int = 0
    iterations: int = 0
