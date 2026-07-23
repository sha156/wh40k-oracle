"""web_api/contract.py — 结构化回答契约（Pydantic 镜像 web/src/lib/answer.ts）。

前端 TypeScript 契约是唯一真源；本模块逐字段对齐，字段名用 camelCase（alias）与前端一致，
`model_dump(by_alias=True)` 出的 JSON 可被前端 `Answer` 类型零改动消费。

Python 3.9：不用 `X | Y` 联合语法，一律 Optional/List/Union/Literal。
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# ── 行内富文本（Inline union，对齐 answer.ts 的 discriminated union）──────

InlineKind = Literal["text", "num", "kw", "strong", "cite"]


class InlineText(BaseModel):
    t: Literal["text", "num", "kw", "strong"]
    s: str


class InlineCite(BaseModel):
    t: Literal["cite"] = "cite"
    n: int


Inline = Union[InlineText, InlineCite]
RichText = List[Inline]


class _CamelModel(BaseModel):
    """camelCase 别名 + 同时接受蛇形/驼峰入参。"""

    model_config = ConfigDict(populate_by_name=True)


# ── E3 机魂运转记录 ───────────────────────────────────────────────

class TraceStep(BaseModel):
    fn: str
    args: str
    result: Optional[str] = None
    status: Literal["ok", "degraded"] = "ok"
    note: Optional[str] = None


# ── E4 判定 ───────────────────────────────────────────────────────

class Verdict(_CamelModel):
    label: str
    label_en: str = Field(alias="labelEn")
    lede: RichText


# ── E5 计算依据 ───────────────────────────────────────────────────

class CalcStep(BaseModel):
    n: int
    text: RichText


# ── E6 兵牌 ───────────────────────────────────────────────────────

class WeaponRow(BaseModel):
    name: str
    kw: Optional[str] = None
    range: str
    a: str
    skill: str
    s: str
    ap: str
    d: str
    hot: bool = False


class Ability(BaseModel):
    tag: Optional[str] = None
    name: str
    text: Optional[str] = None


class Stat(BaseModel):
    lab: str
    val: str


class DamagedProfile(BaseModel):
    w: str
    text: str


class EntityCard(_CamelModel):
    name_zh: str = Field(alias="nameZh")
    name_en: str = Field(alias="nameEn")
    pts: str
    role: Optional[str] = None
    stats: List[Stat]
    invuln: Optional[str] = None
    ranged: List[WeaponRow]
    melee: List[WeaponRow]
    abilities: List[Ability]
    loadout: Optional[str] = None
    damaged: Optional[DamagedProfile] = None
    leads: Optional[str] = None
    composition: List[RichText]
    keywords: str
    faction_keywords: Optional[str] = Field(default=None, alias="factionKeywords")
    legend: Optional[str] = None
    faction: str
    src: str
    wiki: str


# ── E7 封蜡引用 ───────────────────────────────────────────────────

class Cite(BaseModel):
    n: int
    book: str
    page: Optional[int] = None
    section: Optional[str] = None
    term: Optional[str] = None
    wiki: str = ""


# ── E8 CTA / 敏感性 ───────────────────────────────────────────────

class Cta(BaseModel):
    kind: Literal["simulator", "roster", "wiki"]
    ready: bool
    label: str
    mini: Optional[str] = None


class Sensitivity(BaseModel):
    title: str
    text: RichText


# ── 一次完整回答（E3-E9）─────────────────────────────────────────

class Answer(_CamelModel):
    summary: str
    trace: List[TraceStep]
    trace_warn: Optional[str] = Field(default=None, alias="traceWarn")
    verdict: Verdict
    calc: List[CalcStep]
    entity_card: Optional[EntityCard] = Field(default=None, alias="entityCard")
    cites: List[Cite]
    sensitivity: Optional[Sensitivity] = None
    cta: Optional[Cta] = None
    followups: List[str]
    degraded: bool = False


class Exchange(BaseModel):
    question: str
    context: str
    answer: Answer


# ── 模拟器页签（Stage 4，镜像 web/src/lib/sim.ts）─────────────────

class SimToggle(BaseModel):
    """守方可 opt-in 的防守开关（surface-don't-fake：只披露，不自动施加）。"""
    name: str
    note: str = ""
    parsed: Optional[Any] = None


class SimFactionOptions(_CamelModel):
    """守方阵营分队清单（诚实披露未建模的分队/军队规则）。"""
    faction_id: Optional[str] = Field(default=None, alias="factionId")
    faction_name: Optional[str] = Field(default=None, alias="factionName")
    detachments: List[str] = []


class SimDslEntry(_CamelModel):
    """阵营 DSL 可用条目（P7-PR3 回显，PR4 补 side）：军规/分队规则/战略/增强——
    surface 供前端分攻/守两栏渲染与点名回传（stratagems/enhancements 表条目须经
    options.stratagems/enhancements（守方 defender_*）点名才注入）。"""
    table: str
    id: str
    side: str = "attacker"          # attacker|target：条目施加侧（守方栏渲染用）
    name_en: str = Field(alias="nameEn")
    name_zh: Optional[str] = Field(default=None, alias="nameZh")
    status: str
    detachment: Optional[str] = None
    requires_toggles: List[str] = Field(default=[], alias="requiresToggles")


class SimReportOut(_CamelModel):
    """SimReport 镜像。distribution={p10,p50,p90,histogram,damage}；
    funnel=attacks→hits→wounds→unsaved→damage→kills；efficiency=每100点。"""
    expected_damage: float = Field(alias="expectedDamage")
    expected_kills: float = Field(alias="expectedKills")
    wipe_probability: float = Field(alias="wipeProbability")
    distribution: Dict[str, Any] = {}
    funnel: Dict[str, float] = {}
    efficiency: Dict[str, Any] = {}
    modeled_effects: List[str] = Field(default=[], alias="modeledEffects")
    not_modeled: List[str] = Field(default=[], alias="notModeled")
    bias_notes: List[str] = Field(default=[], alias="biasNotes")
    iterations: int = 0
    seed: int = 0
    reverse: Optional["SimReportOut"] = None


class SimResponse(_CamelModel):
    """POST /simulate 响应。ok=False 时 reason 区分 not_found / loadout_required /
    error；loadout_required 附 weaponPool + modelTiers 供前端装配面板。"""
    ok: bool
    reason: Optional[str] = None
    note: Optional[str] = None
    warning: Optional[str] = None
    attacker: Optional[str] = None
    defender: Optional[str] = None
    phase: Optional[str] = None
    report: Optional[SimReportOut] = None
    defender_toggles: List[SimToggle] = Field(default=[], alias="defenderToggles")
    faction_options: Optional[SimFactionOptions] = Field(
        default=None, alias="factionOptions")
    weapon_pool: Optional[List[str]] = Field(default=None, alias="weaponPool")
    model_tiers: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="modelTiers")
    dsl_available: List[SimDslEntry] = Field(default=[], alias="dslAvailable")
    errors: List[str] = []


# ── 军表实验室页签（Stage 4 / P6，镜像 web/src/lib/roster.ts）─────────

class RosterUnitIn(_CamelModel):
    """军表单位入参。loadout=[[武器名,数量],...]（点评用；验表可空）。"""
    canonical_id: str = Field(alias="canonicalId")
    name_en: str = Field(default="", alias="nameEn")
    # 边界拒收 <1 与超上限（不静默钳）；上限防蒙特卡洛数组宽度被拉爆（DoS 面）
    models: int = Field(default=1, ge=1, le=100)
    is_warlord: bool = Field(default=False, alias="isWarlord")
    enhancement: Optional[str] = None
    loadout: List[List[Any]] = Field(default=[], max_length=40)


class RosterIn(_CamelModel):
    """POST /roster/* 请求体。units 上限防点评端点持并发闸跑数百次蒙特卡洛。"""
    faction_id: str = Field(alias="factionId")
    detachment_id: Optional[str] = Field(default=None, alias="detachmentId")
    size: str = "strike_force"
    units: List[RosterUnitIn] = Field(default=[], max_length=60)


class ValidationIssueOut(_CamelModel):
    code: str
    severity: str
    message: str
    anchor: str = ""
    surfaced_only: bool = Field(default=False, alias="surfacedOnly")


class ValidationReportOut(_CamelModel):
    """POST /roster/validate 响应（实时重算：点数+编制合法性）。"""
    total_points: int = Field(alias="totalPoints")
    limit: int
    legal: bool
    issues: List[ValidationIssueOut] = []


class TargetScoreOut(_CamelModel):
    key: str
    label: str
    expected_damage: float = Field(alias="expectedDamage")
    damage_per_100: Optional[float] = Field(default=None, alias="damagePer100")


class UnitAssessmentOut(_CamelModel):
    canonical_id: str = Field(alias="canonicalId")
    name_en: str = Field(alias="nameEn")
    points: Optional[int] = None
    assessed: bool = False
    phase: Optional[str] = None
    scores: List[TargetScoreOut] = []
    note: str = ""


class CritiqueReportOut(_CamelModel):
    """POST /roster/critique 响应（强度点评：每单位打典型目标）。"""
    total_points: int = Field(alias="totalPoints")
    assessments: List[UnitAssessmentOut] = []
    summary: List[str] = []
    not_modeled: List[str] = Field(default=[], alias="notModeled")
