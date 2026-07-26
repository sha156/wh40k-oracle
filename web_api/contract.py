"""web_api/contract.py — 结构化回答契约（Pydantic 镜像 web/src/lib/answer.ts）。

前端 TypeScript 契约是唯一真源；本模块逐字段对齐，字段名用 camelCase（alias）与前端一致，
`model_dump(by_alias=True)` 出的 JSON 可被前端 `Answer` 类型零改动消费。

Python 3.9：不用 `X | Y` 联合语法，一律 Optional/List/Union/Literal。
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# ── 行内富文本（Inline union，对齐 answer.ts 的 discriminated union）──────

InlineKind = Literal["text", "num", "kw", "strong", "em", "cite"]


class InlineText(BaseModel):
    # em = 源里的 *斜体*。只由 wiki 块编译器产出（`web_api/wiki_blocks.py` 里
    # 整行成对的单星号），LLM 回答那条链路不产出它——`richtext.to_richtext` 只认
    # **粗体**，不做单星号配对：库里存在 `5*` 这类脚注标记和 PDF 残留的落单星号，
    # 通用配对会把它们之间的正文整段变斜体。
    t: Literal["text", "num", "kw", "strong", "em"]
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

class KeywordRef(_CamelModel):
    """兵牌上的一个规则词条（武器 USR，或技能正文里内嵌的【致命一击】）。

    `text` 是页面上**原样显示**的那串字（含档位、随语言而变）；其余字段是在真源里
    查到了才有。查不到就**只有 text**——前端据此渲染成不可交互的纯文本。
    绝不为查不到的词条编一句解释：`brief` 只允许是官方中文规则正文的逐字摘录
    （`wiki/core-rules/sections/`），不允许概括、不允许改写、不允许凭 40K 常识补。

    `section` 与 `ruleSlug` 成对出现或成对缺失：拿得到节号就一定拿得到那节所在的
    章节页，反之链接无处可去。速查表漏印节号的词条（实测 PISTOL / SUSTAINED HITS）
    靠官方英文名与核心规则章节配对补回，**不按顺序推断编号**。
    """
    text: str
    slug: Optional[str] = None
    base: Optional[str] = None                  # 官方英文基名（不含档位）
    name_zh: Optional[str] = Field(default=None, alias="nameZh")
    brief: Optional[str] = None                 # 官方中文规则正文摘录
    section: Optional[str] = None               # 官方节号 24.03
    rule_slug: Optional[str] = Field(default=None, alias="ruleSlug")
    group: Optional[str] = None                 # universal / transitional / unit-specific


class WeaponRow(BaseModel):
    name: str
    # 结构化词条数组（不是拼好的一串）：兵牌上每条 USR 都要能单独悬停看解释。
    # 空数组 = 这把武器没有词条；数组里只有 text 的元素 = 有词条但查不到真源。
    kw: List[KeywordRef] = []
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


# ── 武器词条索引（图鉴 · 词条页，镜像 web/src/lib/keywords.ts）─────────

# 三档分类：通用（11 版速查表在册）/ 十版遗留（库里还有但已被取代）/ 单位特有。
# 用 Literal 而非 str：载荷冒出第四档时要当场 500 炸出来，别让前端拿到它没有分支
# 可渲染的 group 值，静默掉进 default 分支显示成「通用」。
KeywordGroup = Literal["universal", "transitional", "unit-specific"]


class KeywordSummary(_CamelModel):
    """词条索引一行。数量四件套是「现役 / 全库」双口径，与图鉴列表口径一致。"""
    slug: str
    base: str                       # 英文基础词条（大写，已剥掉档位参数）
    name_zh: str = Field(alias="nameZh")
    group: KeywordGroup
    # 速查表确有条目漏印节号（实测「连击 SUSTAINED HITS」），此时为 null——
    # 不按顺序推断补全：推出来的号码看着像真的，其实是我们编的
    section: Optional[str] = None
    quickref_zh: Optional[str] = Field(default=None, alias="quickrefZh")
    params: List[str] = []          # 档位变体（"2" / "4+" / "D6+3"），无参为 []
    engine: str                     # 数值建模 / 仅标注 / 未纳入（诚实披露，不吹）
    rule_page: Optional[str] = Field(default=None, alias="rulePage")
    current_weapons: int = Field(alias="currentWeapons")
    total_weapons: int = Field(alias="totalWeapons")
    current_units: int = Field(alias="currentUnits")
    total_units: int = Field(alias="totalUnits")


class KeywordWeapon(BaseModel):
    """反查表一行：带该词条的武器，及携带它的现役单位。"""
    name: str
    units: List[str] = []


class KeywordDetail(KeywordSummary):
    """详情页 = 索引行 + 反查表（哪些武器带这个词条）。"""
    weapons: List[KeywordWeapon] = []


class KeywordIndexResponse(_CamelModel):
    """GET /codex/keywords 响应。items 刻意**不带** weapons：反查表占载荷九成体积。"""
    items: List[KeywordSummary] = []


# ── 图鉴 · 分队浏览（镜像 web/src/lib/wiki.ts）─────────────────────────
#
# 正文以**块数组**下发，前端零解析：它没有 markdown 渲染器，也不该为了几页规则引一个。
# 块的形态由 `web_api/wiki_blocks.py` 从 wiki/ 下的 .md 确定性编译而来。

class WikiParagraph(BaseModel):
    t: Literal["p"] = "p"
    inline: RichText = []


class WikiListBlock(BaseModel):
    """无序/有序列表。两种只差 t，共用一个模型——出参 JSON 与契约里的两个变体一致。"""
    t: Literal["ul", "ol"]
    items: List[RichText] = []


class WikiTable(BaseModel):
    """表格。单元格是**纯字符串**（不是 RichText）：库里的表全是「战斗规模 → 可选
    单位数」这类档位表，格子里没有引用编号，上 RichText 只是徒增前端分支。"""
    t: Literal["table"] = "table"
    head: List[str] = []
    rows: List[List[str]] = []


class WikiHeading(BaseModel):
    """小节内标题（实际只出现 level 3）。level 照实给，不钳到 3——钳了就看不出源页异常。"""
    t: Literal["h"] = "h"
    level: int
    text: str


class WikiQuote(BaseModel):
    """`> ` 引用块。页面里的诚实披露（「本分队名下有 2 条规则，以下全部列出」）走它。"""
    t: Literal["quote"] = "quote"
    inline: RichText = []


class WikiDetails(BaseModel):
    """`<details>` 折叠块（**块可嵌套**：里面还是一串 WikiBlock）。

    只有核心规则页用它——每节「中文正文 + 官方英文原文折叠」。为什么做成通用块型
    而不是给核心规则单开一对 `zhBlocks/enBlocks` 字段：折叠里装的就是普通正文
    （段落/列表/表格/引用都出现过），拆成两套字段等于把同一个块渲染器在契约层复制一遍，
    以后哪一页多一个折叠又要再加一对字段。

    `summary` 是折叠标签，**它本身携带信息**：实测 142 节写「官方英文原文」、14 节写
    「官方英文原文（英文由 PDF 直提）」——后者是 refine 产物丢了节号、改用英文 PDF
    兜底的那 13+1 节。这行字是页面上唯一能看出英文来源的地方，不许在传输中丢掉或归一化。
    """
    t: Literal["details"] = "details"
    summary: str
    blocks: List["WikiBlock"] = []


# 判别式联合：t 是标签。不用裸 Union——裸 Union 校验时按顺序试，
# 一个少了 head 的表格会被悄悄当成别的块型收下，错误要到前端才显形。
WikiBlock = Annotated[
    Union[WikiParagraph, WikiListBlock, WikiTable, WikiHeading, WikiQuote,
          WikiDetails],
    Field(discriminator="t"),
]

# WikiDetails.blocks 里那个 "WikiBlock" 是前向引用，要等联合体定义完才能解析。
# 不 rebuild 的话它一直是未解析的 ForwardRef，校验到嵌套块时直接抛
# PydanticUserError——而且只在**有折叠的页**上炸，分队页全绿，最容易漏掉。
WikiDetails.model_rebuild()


class WikiSection(BaseModel):
    """一个 `## 小节`。title 就是页面上的小节名（使用时机 / 效果 / 分队规则…）。"""
    title: str
    blocks: List[WikiBlock] = []


class StratagemBrief(_CamelModel):
    """分队详情里内联的一条战略。

    cp 用 Optional[int]：**0 CP 是真值**（核心战略里有），null 才是"库里没这项数据"
    （艾达灵族 6 条挂在 Army Rules 下的战略就没有 cp）。前端两者不能混着显示成「未知」。
    """
    id: str
    slug: str
    name_en: str = Field(alias="nameEn")
    name_zh: Optional[str] = Field(default=None, alias="nameZh")
    cp: Optional[int] = None
    phase: str = ""
    stratagem_type: str = Field(default="", alias="stratagemType")
    sections: List[WikiSection] = []


class EnhancementBrief(_CamelModel):
    """分队详情里内联的一条增强。cost 同 cp：0 分是真值（实测 117 条），null 是未知。"""
    id: str
    slug: str
    name_en: str = Field(alias="nameEn")
    name_zh: Optional[str] = Field(default=None, alias="nameZh")
    cost: Optional[int] = None
    sections: List[WikiSection] = []


class DetachmentSummary(_CamelModel):
    """分队列表一行。

    `ruleName` 是**分队规则名**，与分队名不是一回事：Awakened Dynasty（分队/容器名）
    名下的规则叫 Command Protocols。库里 `detachments` 表存的是规则名、容器名的真源
    是 enhancements/stratagems 的 detachment 列——搞反了整页都在说另一件事。
    没有绑定规则行的分队（实测 64 个）为 null，不拿分队名顶替。
    """
    slug: str
    name_en: str = Field(alias="nameEn")
    name_zh: Optional[str] = Field(default=None, alias="nameZh")
    rule_name: Optional[str] = Field(default=None, alias="ruleName")
    stratagem_count: int = Field(default=0, alias="stratagemCount")
    enhancement_count: int = Field(default=0, alias="enhancementCount")


class DetachmentDetail(DetachmentSummary):
    """分队详情：增强与战略**内联**返回。

    为什么内联而不是让前端按 id 逐个拉：容器只有 324 个，挂在它们下面的战略有 1653 条、
    增强 1058 条，一个分队平均 5 战略 + 3 增强——不内联就是开一页打八次请求。
    """
    faction_id: str = Field(alias="factionId")
    faction_zh: Optional[str] = Field(default=None, alias="factionZh")
    rule_sections: List[WikiSection] = Field(default=[], alias="ruleSections")
    enhancements: List[EnhancementBrief] = []
    stratagems: List[StratagemBrief] = []


class DetachmentListResponse(_CamelModel):
    """GET /codex/factions/{faction_id}/detachments 响应。"""
    items: List[DetachmentSummary] = []


# ── 图鉴 · 核心规则全文（镜像 web/src/lib/wiki.ts）─────────────────────
#
# 正文是 **GW 官方简体中文**，每节挂一个 `details` 折叠块装官方英文原文。
# 章节页由 `wiki_engine/core_rules{,_zh}.py` 离线生成，这里只读不算。

class CoreRuleChapterSummary(_CamelModel):
    """章节目录一行。

    `number` 是官方章号（"01".."24"，**保留前导零**）：它同时是文件名前缀与排序键，
    转成 int 再格式化回去只是给自己找一次错的机会。
    """
    slug: str                                   # 文件名（01-core-concepts）
    number: str
    name_zh: str = Field(alias="nameZh")
    name_en: str = Field(alias="nameEn")
    section_count: int = Field(alias="sectionCount")


class CoreRuleChapter(CoreRuleChapterSummary):
    """章节详情：导语 + 各节。

    `intro` 是第一个 `##` 之前那几块，**必须带上**。分队页那边导语是 frontmatter 的
    重复展示、按设计丢弃；核心规则页的导语里是「正文为官方简体中文版；中文由 PDF 文本层
    直提，表格与版式会有失真——判定规则以英文原文为准」这条诚实披露。把它丢了，
    页面就变成一份看着像官方定稿的中文规则书，正是这个项目最该避免的那种自信错误。
    """
    intro: List[WikiBlock] = []
    sections: List[WikiSection] = []


class CoreRuleChapterListResponse(_CamelModel):
    """GET /codex/rules 响应。"""
    items: List[CoreRuleChapterSummary] = []


# ── 图鉴 · 规则变更清单（镜像 web/src/lib/wiki.ts）─────────────────────

class ChangelogFactionSummary(_CamelModel):
    """变更清单目录一行（一个阵营包）。

    `total`/`newCount` 取自 `wiki/changelog/index.md` 的一览表，并与阵营页里实际的
    `###` 条目数逐条对账过（对不上走 503，见 `changelog_browse._reconcile`）。
    `slug` 为 null 的两行是真没有明细页可点：deathwatch 是首版无更新章节、
    混沌恶魔是官方本次未列改动——这两行 `detail` 里写的就是原因，照实显示，
    不许伪造一个空页面让人点进去看「本包 0 条改动」。
    """
    slug: Optional[str] = None
    name: str                                   # 阵营包显示名（官方中文名，缺则英文 slug）
    version: str                                # v1.0 / v1.1
    total: int
    new_count: int = Field(alias="newCount")
    detail: str                                 # 明细列的原文（无链接行的原因说明）


class ChangelogIndex(_CamelModel):
    """GET /codex/changelog 响应：导语 + 通用规则更新 + 各阵营一览。

    `generalSections` 是《通用规则更新》那几节（跨全部阵营，不属于任何阵营包），
    与阵营明细分开放：混在一起会让人以为它只对某个阵营生效。
    """
    intro: List[WikiBlock] = []
    general_sections: List[WikiSection] = Field(default=[], alias="generalSections")
    # 兜底桶：index 里既不是一览表、也不是《通用规则更新》的其余节。此刻装的是
    # 「数值层的 10 版 → 11 版漂移」那条口径说明（本页只收文字改动，数值漂移在
    # fp_errata/fp_rules 补丁里，两条线不要混读）。做成兜底桶而不是硬编码那一节的标题：
    # 生成器哪天多写一节，也要出现在页面上，而不是被静默丢掉。
    note_sections: List[WikiSection] = Field(default=[], alias="noteSections")
    factions: List[ChangelogFactionSummary] = []
    total: int = 0                              # 阵营改动合计（对账后的真数）
    new_count: int = Field(default=0, alias="newCount")


class ChangelogFactionPage(_CamelModel):
    """GET /codex/changelog/{slug} 响应：某阵营包的官方「规则更新」全文。

    `sections` 的小节名是官方自己的分组（数据表 / 军队规则 / 各分遣队名），
    每个 `###` 条目是一条改动；标题里带 🆕 的是 v1.1 增量（判据是 PDF 红色高亮）。
    """
    slug: str
    name_zh: str = Field(alias="nameZh")
    name_en: str = Field(alias="nameEn")
    version: str
    total: int
    new_count: int = Field(default=0, alias="newCount")
    intro: List[WikiBlock] = []
    sections: List[WikiSection] = []
