"""web_api/contract.py — 结构化回答契约（Pydantic 镜像 web/src/lib/answer.ts）。

前端 TypeScript 契约是唯一真源；本模块逐字段对齐，字段名用 camelCase（alias）与前端一致，
`model_dump(by_alias=True)` 出的 JSON 可被前端 `Answer` 类型零改动消费。

Python 3.9：不用 `X | Y` 联合语法，一律 Optional/List/Union/Literal。
"""
from __future__ import annotations

from typing import List, Literal, Optional, Union

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
