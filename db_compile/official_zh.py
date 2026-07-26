"""db_compile/official_zh.py —— GW **官方简体中文** PDF → 战略/强化/分遣队中文名映射。

为什么要有这一层（2026-07-26）：
warhammer-community 下载页可切「简体中文」，GW 自己发的 34 个官方中文 PDF 已落
`data/官方中文/`（28 个阵营包 v1.1，2026-07-22 生效）。wiki 宪法 §6 定
「GW 官方中文 > 汉化组译名 > 社区译名」，所以这批是**最高权威**的中文源，
用来填三个洞：分遣队中文名（库里一个都没有）、战略中文名、强化中文名。
现有中文名多来自 P7 人工编码，权威级别低于官方，官方有的应当替换。

配对为什么必须用**数值指纹**、绝不按位置或顺序（见 `db_compile/zh_weapons.py` 顶注）：
本仓库为「按位置配对」付过代价——中文武器名曾被贴到错误的数值行上，**数值对、名字错**，
用户没有任何线索能察觉。这里同理：一页 6 条战略，中文顺序和库内顺序不保证一致，
「数量相等」也拦不住错位。故一律用跨语言不变量当指纹：

  · CP 消耗（PDF 里是**浮动文本框**，见下方 _assign_cp 的坑）
  · 时机里出现的阶段集合（指挥/移动/射击/冲锋/近战 ↔ Command/Movement/…）
  · 是不是对手回合触发（中文「对手」↔ 英文 "opponent"）
  · 时机/目标/效果三段各自的**数字多重集**（6" / D6 / 4+ / 1 这些翻译不会改）

Pass A：阵营内 (cp, 对手位, 阶段集, 三段数字多重集) 中英**各自唯一**才算配上；
        同 key 撞车时若两边 type（战斗战术/战略计划/史诗伟业/武器装备）都齐全，
        再按 type 细分，仍唯一才配。
Pass B：先由 Pass A 的结果**多数票**反推「中文分遣队名 ↔ 英文容器名」，
        再在已确认的分遣队对内部，用放宽的 key（去掉最易抽错的 cp）补配残差，
        同样要求两边唯一。
强化：  官方中文 PDF 不印强化点数，所以指纹只有 (分遣队, 描述数字多重集)，
        必须靠 Pass B 定出的分遣队对收窄搜索域才够判别力。

一条也不猜：配不上、有歧义、type 冲突，一律不落——留空计入 `_report`，宁缺毋错。
产物 `db_compile/official_zh_names.json` 是 git 真源；**本模块不写库、不碰 wiki/**
（落库在 `db_compile/official_zh_apply.py`）。

产物里同时给**两种键**，因为它们各自能表达的东西不同：
  · `stratagems` / `enhancements`：英文名 → 中文名。同一英文名在不同包里有不同官方译名时
    （`ARMOUR OF CONTEMPT` → 蔑视战甲 / 蔑视甲胄），这种键**表达不了**，只能整条丢。
  · `stratagems_by_id` / `enhancements_by_id`：库内行 id → 中文名，直接来自配对的那一对，
    上面那类冲突在这里天然不存在（每行认自己那本包的译名）。落库以它为准，
    英文名键只用来给「没配上、但同名条目在别处配上了」的行兜底。
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

_ROOT = Path(__file__).resolve().parent.parent
ZH_PDF_DIR = _ROOT / "data" / "官方中文"
OUT_PATH = Path(__file__).resolve().parent / "official_zh_names.json"

# PDF 文本层残留的控制字符（实测官方中文包里「强化\x08」「▪\x07」）。
# 肉眼不可见，却会让「行尾/整行匹配」整条静默失效——章节切不出来，页面看着完整却少几节。
# 与 wiki_engine.core_rules._CTRL_CHARS 同源，解析前一律先清。
#
# 除 C0 控制符外，还必须清**零宽/格式字符**（2026-07-26 复核逮到）：
# 机械教包的分遣队名抽出来是「启明\u200b自动合唱团」——中间夹着一个零宽空格。
# 它比 \x08 更阴：打印出来、贴进报告、肉眼比对全都一模一样，只有 == 比较为 False。
# 这个名字要当**字典键**用（英文容器名→中文分遣队名），落库后按名字 join 会静默配不上，
# 而报错信息里两个字符串看起来完全相同，根本无从查起。软连字符、BOM、双向控制符
# 在 PDF 文本层同样常见，一并清掉。
#
# 这里一律写 \u 转义而不贴字面量：零宽字符进了源码，这一行在编辑器里看着是空的，
# 谁也没法复核它到底清了哪些码位，被人改坏了也看不出来。
_INVISIBLE = (
    "\u00ad"           # 软连字符
    "\u200b-\u200f"    # 零宽空格/非连接/连接 + 左右向标记
    "\u202a-\u202e"    # 双向嵌入/覆盖
    "\u2060"           # 词连接符
    "\ufeff"           # BOM / 零宽非断空格
)
_CTRL_CHARS = re.compile("[" + "".join(chr(c) for c in
                         list(range(0, 9)) + [11, 12] + list(range(14, 32)) + [127])
                         + _INVISIBLE + "]")

# manifest.json 的 faction_slug → 库内 factions.id。
# 官方文件名里有拼写抖动（imperia_agents 少个 l、orkss 多个 s），照抄不要"修"。
# BT/BA/DA/DW/SW 五个战团在官方是独立包，库里折叠在 SM 下——它们的战略确实挂 faction='SM'。
SLUG_TO_FACTION: Dict[str, str] = {
    "adepta_sororitas": "AS", "adeptus_custodes": "AC", "adeptus_mechanicus": "AdM",
    "aeldari": "AE", "astra_militarum": "AM", "chaos_daemons": "CD",
    "chaos_knights": "QT", "chaos_space_marines": "CSM", "death_guard": "DG",
    "drukhari": "DRU", "emperor_s_children": "EC", "genestealer_cults": "GC",
    "grey_knights": "GK", "imperia_agents": "AoI", "imperia_knights": "QI",
    "leagues_of_votann": "LoV", "necrons": "NEC", "orkss": "ORK",
    "space_marines": "SM", "thousand_sons": "TS", "tyranids": "TYR",
    "tau_empire": "TAU", "world_eaters": "WE",
    "black_templars": "SM", "blood_angels": "SM", "dark_angels": "SM",
    "deathwatch": "SM", "space_wolves": "SM",
}

# 战略类型：中英规范化到同一枚举，用来给撞车的指纹做二次细分 / 一票否决
_TYPE_ZH = {
    "战斗战术": "battle_tactic", "战略计划": "strategic_ploy",
    "史诗伟业": "epic_deed", "武器装备": "wargear",
}
_TYPE_EN = {
    "battle tactic": "battle_tactic", "strategic ploy": "strategic_ploy",
    "epic deed": "epic_deed", "wargear": "wargear",
}

# 阶段：时机段里出现哪些阶段，是翻译改不掉的结构信息
_PHASE_ZH = [("指挥阶段", "command"), ("移动阶段", "movement"), ("射击阶段", "shooting"),
             ("冲锋阶段", "charge"), ("近战阶段", "fight")]
_PHASE_EN = [("command phase", "command"), ("movement phase", "movement"),
             ("shooting phase", "shooting"), ("charge phase", "charge"),
             ("fight phase", "fight")]

_SEC_WHEN, _SEC_TARGET, _SEC_EFFECT, _SEC_RESTRICT = "when", "target", "effect", "restrict"
_SECTION_HEADS = {"时机": _SEC_WHEN, "目标": _SEC_TARGET,
                  "效果": _SEC_EFFECT, "限制": _SEC_RESTRICT}
_SECTION_RE = re.compile(r"^(时机|目标|效果|限制)\s*[:：]")

_DET_RULE_HEAD = "分遣队规则"
_ENH_HEAD = "强化"
# 强化正文的官方定式开头：「仅限太空死灵模型。…」。用它把强化和分遣队规则/军规区分开，
# 比认「强化」小节标题稳——那个标题在不同页会飘到别的栏去（实测太空死灵 p8 在 x=499，
# 条目却在 x=349，按栏找根本对不上）。
_ENH_ONLY = "仅限"
# 「规则更新」「常见问题」两节会**整段引用**计谋原文（连 时机/目标/效果 都在），
# 但那儿的大标题是分遣队名而不是计谋名——照常解析会把「湮灭军团分遣队」当成一条
# 计谋的名字（实测太空死灵 p28）。这两节整页跳过。
_SKIP_SECTION_TITLES = ("规则更新", "常见问题", "问与答", "勘误")
_TITLE_MIN_SIZE = 20.0     # 分遣队大标题字号下界（实测 36-38pt，正文最大 12pt）
# 分遣队对的覆盖率地板：一对分遣队要互指到中文侧至少这么大比例的条目才算数
_DET_MIN_COVERAGE = 0.4
_CP_ABOVE_TOL = 20.0       # CP 框允许比它所属标题高出多少（实测最多 6pt）
_CP_RE = re.compile(r"^(\d+)\s*CP$", re.I)
# 数字 token：D6 / 2D6 / D3 / 纯数字。跨语言不变（6" 的引号、4+ 的加号都不进 token）
_NUM_TOKEN = re.compile(r"(\d*[Dd]\d+|\d+)")
_HTML_TAG = re.compile(r"<[^>]+>")


# ---------------------------------------------------------------- 数据结构

@dataclass(frozen=True)
class ZhStratagem:
    """官方中文包里的一条计谋（＝库里的 stratagem）。"""
    faction: str
    name_zh: str
    detachment_zh: Optional[str]
    type_zh: Optional[str]
    cp: Optional[int]
    when_zh: str
    target_zh: str
    effect_zh: str
    source: str
    page: int


@dataclass(frozen=True)
class ZhEnhancement:
    """官方中文包里的一条强化。中文包不印点数，所以没有 cost 字段。"""
    faction: str
    name_zh: str
    detachment_zh: Optional[str]
    legend_zh: str
    text_zh: str
    source: str
    page: int


@dataclass
class _Line:
    """一行文本 + 版面信息。size/bold 用来区分标题与正文，bbox 用来配 CP 浮动框。"""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    fonts: Tuple[str, ...]

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


# ---------------------------------------------------------------- 文本工具

def clean_text(raw: str) -> str:
    """清控制字符 + 压空白。**故意不做 NFKC**：官方中文名里的（光环）是全角括号，
    NFKC 会把它拉成半角，产出的就不再是 GW 官方写法了。归一只在 number_fingerprint
    里做（那里只关心数字，全角数字要拉成半角才对得上指纹）。"""
    txt = _CTRL_CHARS.sub("", raw or "")
    txt = txt.replace(" ", " ").replace("　", " ")
    return re.sub(r"[ \t]+", " ", txt).strip()


def strip_html(raw: str) -> str:
    """库里的英文正文带 <b>/<span class="kwb"> 标记。标记里没有数字，但仍先剥干净再取数。"""
    txt = _HTML_TAG.sub(" ", raw or "").replace("<br>", " ")
    return clean_text(txt.replace("&nbsp;", " "))


def number_fingerprint(text: str) -> Tuple[str, ...]:
    """正文里的数字多重集（排序后的 tuple）——翻译改不动的量纲。

    D6/2D6 保留骰型（统一大写），纯数字原样。这是配对的主力信号：
    「add 1 to the Wound roll」↔「致伤掷骰结果增加 1 点」两边都只有一个 1。
    """
    norm = unicodedata.normalize("NFKC", clean_text(text))
    toks = [t.upper() for t in _NUM_TOKEN.findall(norm)]
    return tuple(sorted(toks))


def phases_of_zh(when_zh: str) -> Tuple[str, ...]:
    txt = clean_text(when_zh)
    return tuple(sorted({tag for kw, tag in _PHASE_ZH if kw in txt}))


def phases_of_en(when_en: str) -> Tuple[str, ...]:
    txt = strip_html(when_en).lower()
    return tuple(sorted({tag for kw, tag in _PHASE_EN if kw in txt}))


def canon_type_zh(type_zh: Optional[str]) -> Optional[str]:
    if not type_zh:
        return None
    txt = clean_text(type_zh)
    for kw, tag in _TYPE_ZH.items():
        if kw in txt:
            return tag
    return None


def canon_type_en(type_en: Optional[str]) -> Optional[str]:
    if not type_en:
        return None
    txt = clean_text(type_en).lower()
    for kw, tag in _TYPE_EN.items():
        if kw in txt:
            return tag
    return None


# ---------------------------------------------------------------- PDF 解析

def _page_lines(page: Any) -> List[_Line]:
    """把一页拆成带版面信息的行。用 dict 模式而非 blocks：blocks 会把
    「强化 + 第一条强化名 + 正文」粘成一块（实测太空死灵 p6），行级才切得干净。"""
    out: List[_Line] = []
    data = page.get_text("dict")
    for blk in data.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for ln in blk.get("lines", []):
            spans = ln.get("spans", [])
            txt = clean_text("".join(sp.get("text", "") for sp in spans))
            if not txt:
                continue
            x0, y0, x1, y1 = ln["bbox"]
            size = max((sp.get("size", 0.0) for sp in spans), default=0.0)
            fonts = tuple(sorted({sp.get("font", "") for sp in spans}))
            out.append(_Line(txt, x0, y0, x1, y1, round(size, 1), fonts))
    return out


def _cluster_columns(lines: Sequence[_Line], gap: float = 40.0) -> List[List[_Line]]:
    """按 x0 一维聚类分栏。官方包是双栏排版，不分栏的话上下文会串栏错配。

    gap=40 是量出来的：同栏内缩进抖动 ≤ 20pt（项目符号），栏间距 ≥ 150pt。
    """
    if not lines:
        return []
    ordered = sorted(lines, key=lambda l: l.x0)
    cols: List[List[_Line]] = [[ordered[0]]]
    for ln in ordered[1:]:
        if ln.x0 - cols[-1][-1].x0 > gap:
            cols.append([])
        cols[-1].append(ln)
    for col in cols:
        col.sort(key=lambda l: (round(l.y0, 1), l.x0))
    return cols


def _body_size(col: Sequence[_Line]) -> float:
    """本栏正文字号＝长行里最常见的字号。**必须按栏算**：同一页左栏正文 8.5、
    右栏 7.0 是常态（太空死灵 p1），按整页算会把右栏标题算进正文。"""
    cnt = Counter(l.size for l in col if len(l.text) >= 8)
    if not cnt:
        cnt = Counter(l.size for l in col)
    return cnt.most_common(1)[0][0] if cnt else 8.0


def _assign_cp(cp_lines: Sequence[_Line],
               col_heads: Sequence[Sequence[_Line]]) -> Dict[int, Optional[int]]:
    """把「2CP」浮动文本框配到计谋标题上——**必须靠几何**，不能靠阅读顺序，
    也不能靠"最近的标题"。返回 {标题全局序号: CP}。

    坑（记忆里已记过一次：FP PDF 的 CP 是浮动文本框、refine 会错位配对）：
      · CP 框既可能在栏**左**（太空死灵 p5：CP x=161 / 正文 x=188、p9：x=159），
        也可能在栏**右**（p1：CP x=516 / 正文 x=309）；
      · CP 框的 y 既可能远在标题**下方**（p5：CP 150 / 标题 74），
        也可能**略高于**标题（p1：CP 224 / 标题 224 齐平，实测偏上 6pt）。
    所以"框心离哪个标题近就归谁"会翻车：p9 的第一个 CP（cy≈150）离第二条标题
    （y=207）比离第一条（y=72）还近 10pt——照最近原则整栏 CP 会集体后移一位，
    正是"数值对、名字错"那类看不出来的错。

    正确规则是**两段独立**的：横向选栏（离哪一栏的标题横坐标近就属于哪一栏），
    纵向落区间（cy 落在 [本条标题 y - 20, 下条标题 y - 20) 里）。

    对账不能要求"框数＝条数"：实测混沌星际战士 p5 有 7 个框 / 6 条计谋，多出来的
    那个和第一条的框重叠且**数字相同**（版面重复渲染，多半是描边层）；艾达灵族 p8
    则是 5 框 / 6 条（有条计谋的框被压在图里没抽出来）。所以改成逐条对账：
    同一条落多个框、数字一致＝重复渲染，取其一；**数字打架就整页判未知**；
    没框的那条自己判未知，不连累别人。错的 CP 会毒化指纹，宁可不要。
    """
    heads_flat = [h for col in col_heads for h in col]
    assign: Dict[int, Optional[int]] = {i: None for i in range(len(heads_flat))}
    if not heads_flat or not cp_lines:
        return assign
    index_of = {id(h): i for i, h in enumerate(heads_flat)}
    got: Dict[int, Set[int]] = defaultdict(set)
    for cp in cp_lines:
        m = _CP_RE.match(cp.text)
        if not m:
            continue
        col = min((c for c in col_heads if c), default=None,
                  key=lambda c: abs(cp.cx - sum(h.cx for h in c) / len(c)))
        if not col:
            continue
        for k, h in enumerate(col):
            lo = h.y0 - _CP_ABOVE_TOL
            hi = (col[k + 1].y0 - _CP_ABOVE_TOL) if k + 1 < len(col) else float("inf")
            if lo <= cp.cy < hi:
                got[index_of[id(h)]].add(int(m.group(1)))
                break
    if any(len(v) > 1 for v in got.values()):
        return assign          # 同一条计谋收到互相矛盾的 CP：整页作废
    for gi, vals in got.items():
        assign[gi] = next(iter(vals))
    return assign


def _split_sections(body: Sequence[str]) -> Dict[str, str]:
    """把 时机/目标/效果/限制 四段正文切开。行内已经带「时机：」前缀。

    「同一个小节标题连出现两次」要按**顺序**纠回来（2026-07-26 复核逮到）：
    混沌星际战士包把第三段的「效果：」整页错印成「目标：」（p9 六条全中，p7/p15
    各一条）。原样解析的话 target 会把 effect 正文一路吞掉、effect 留空，
    随后被「时机与效果必须都在」的守卫整条丢弃——**整页 6 条静默消失**，
    而报告里只会显示"官方就这么多条"，覆盖率看着天经地义。

    纠法只认一种形状，不做通用猜测：某个标题第二次出现、且它在定式顺序里的
    下一段还是空的，就把这一段判给下一段。定式顺序是 时机→目标→效果→限制，
    小节不会回头，所以「目标出现两次而效果还空着」只可能是第二个目标其实是效果。
    下一段已经有内容就不动——那说明是别的情况（如效果里有以「目标：」起头的列点），
    宁可维持原样也不瞎调。
    """
    order = (_SEC_WHEN, _SEC_TARGET, _SEC_EFFECT, _SEC_RESTRICT)
    out: Dict[str, List[str]] = defaultdict(list)
    cur: Optional[str] = None
    for raw in body:
        m = _SECTION_RE.match(raw)
        if m:
            sec = _SECTION_HEADS[m.group(1)]
            if out.get(sec):                      # 这个标题已经收过正文了
                idx = order.index(sec)
                nxt = order[idx + 1] if idx + 1 < len(order) else None
                if nxt and not out.get(nxt):
                    sec = nxt
            cur = sec
            rest = raw[m.end():].strip()
            if rest:
                out[cur].append(rest)
            continue
        if cur:
            out[cur].append(raw)
    return {k: clean_text("".join(v)) for k, v in out.items()}


def _parse_det_line(text: str) -> Tuple[Optional[str], Optional[str]]:
    """计谋名下面那行 → (分遣队中文名, 类型)。官方包里三种写法都有：

      「碎星宝库 – 战斗战术计谋」  分遣队 + 类型（破折号 – 和 - 在同一本 PDF 里混用，
                                  太空死灵 p5 用 –、p7 用 -，只认一种会丢掉半本的类型）
      「恶魔入侵 – 战斗战术」      「计谋」二字折行折掉了（混沌恶魔 p6/p7）——
                                  按"必须以计谋结尾"去认，分遣队名就会带着
                                  「 – 战斗战术」尾巴落地（产物里出现过一次）
      「王朝之手」                只有分遣队（11 版新分遣队页不印类型）
      「传瘟机械计谋」            分遣队直接粘「计谋」二字（死亡守卫 p1）——
                                  这条最阴：不拆就会把整串当成"类型"，分遣队丢掉，
                                  连带整页强化因为没有分遣队上下文被丢弃
    """
    txt = clean_text(text)
    body = txt[:-len("计谋")].strip() if txt.endswith("计谋") else txt
    m = re.match(r"^(.*?)\s*[–—\-]\s*([^–—\-]+)$", body)
    if m and m.group(2).strip() in _TYPE_ZH:
        return (_trim_det(m.group(1)) or None), m.group(2).strip() + "计谋"
    for kw in _TYPE_ZH:
        if body.endswith(kw):
            return (_trim_det(body[:-len(kw)]) or None), kw + "计谋"
    # 连破折号后面的类型都折到下一行去了（艾达灵族 p5「巨蛇族群 –」），
    # 分遣队名会拖着个破折号落地——它会当成另一个分遣队，跟强化页的标题对不上
    return (_trim_det(body) or None), None


def _trim_det(name: str) -> str:
    return clean_text(name).strip(" –—-")


def _is_head(ln: _Line, body: float) -> bool:
    """标题行：字号明显大于本栏正文。1.15 倍是量出来的下界
    （正文 8.5 / 标题 10 就靠这个分开），再低会把加粗关键词行误判成标题。"""
    return ln.size >= body * 1.15


@dataclass
class _Segment:
    """一栏里「一个标题 + 它下面的正文行」。官方包所有条目都是这个形状：
    计谋 / 强化 / 分遣队规则 都是"大字标题 + 小字正文"，区别只在正文长什么样。"""
    head: _Line
    body: List[_Line] = field(default_factory=list)


def _segments(col: Sequence[_Line], body_sz: float) -> List[_Segment]:
    """按标题行把一栏切成段。栏首没标题的那截（上页续下来的）直接丢。"""
    segs: List[_Segment] = []
    for ln in col:
        if _is_head(ln, body_sz):
            segs.append(_Segment(ln))
        elif segs:
            segs[-1].body.append(ln)
    return segs


def parse_pack(pdf_path: Path, faction: str) -> Tuple[List[ZhStratagem],
                                                      List[ZhEnhancement],
                                                      List[str]]:
    """解析一个官方中文阵营包 → (计谋, 强化, 警告)。

    **两遍**：计谋自带「碎星宝库 – 战斗战术计谋」行，一遍就能定分遣队；强化小节不带，
    只能靠页面标题猜。第一遍先把本包所有分遣队中文名收齐，第二遍拿这份名单去认强化
    所在页的分遣队——死亡守望包的强化页没有大标题，只有页眉「死亡守望 - 黑矛特遣队」，
    不给名单就只能整页丢掉。名单同时是一道闸：认不出名单里的名字就不认，
    免得把页眉里别的词当成分遣队。
    """
    import fitz  # PyMuPDF；只在真解析 PDF 时 import，单测用合成 _Line 走不到这里

    doc = fitz.open(str(pdf_path))
    try:
        pages = [_page_lines(doc[pno]) for pno in range(doc.page_count)]
    finally:
        doc.close()

    strats: List[ZhStratagem] = []
    for pno, lines in enumerate(pages):
        strats.extend(parse_page_lines(lines, faction, pdf_path.name, pno)[0])
    known = {s.detachment_zh for s in strats if s.detachment_zh}

    enhs: List[ZhEnhancement] = []
    warns: List[str] = []
    for pno, lines in enumerate(pages):
        _, e, w = parse_page_lines(lines, faction, pdf_path.name, pno, known)
        enhs.extend(e)
        warns.extend(w)
    return strats, enhs, warns


def parse_page_lines(lines: Sequence[_Line], faction: str, source: str, page: int,
                     known_dets: Optional[Set[str]] = None
                     ) -> Tuple[List[ZhStratagem], List[ZhEnhancement], List[str]]:
    """单页解析。拆出来是为了能用合成的 _Line 列表做单测，不必造 PDF。

    known_dets：本包已知的分遣队中文名（parse_pack 第一遍收的）。给了就用它认强化
    所在页的分遣队，没给就只能靠大标题。
    """
    warns: List[str] = []
    if any(l.size >= 14.0 and l.text.strip() in _SKIP_SECTION_TITLES for l in lines):
        return [], [], warns
    cp_lines = [l for l in lines if _CP_RE.match(l.text)]
    cols = _cluster_columns([l for l in lines if not _CP_RE.match(l.text)])

    # 「分遣队规则」和「强化」两个小节标题都算分遣队页——死亡守望包把强化单开一页，
    # 那页没有「分遣队规则」，只认前者会整页丢掉强化。
    is_det_page = any(l.text.rstrip() in (_DET_RULE_HEAD, _ENH_HEAD) for l in lines)

    col_segs = [(col, _segments(col, _body_size(col))) for col in cols]
    strat_segs: List[Tuple[_Segment, Dict[str, str], Optional[str], Optional[str]]] = []
    col_heads: List[List[_Line]] = []
    enh_raw: List[Tuple[str, str, str]] = []

    for col, segs in col_segs:
        heads_here: List[_Line] = []
        for seg in segs:
            texts = [l.text for l in seg.body]
            if seg.head.text.rstrip() in (_DET_RULE_HEAD, _ENH_HEAD):
                continue  # 小节标题本身不是条目
            if any(_SECTION_RE.match(t) for t in texts):
                sec = _split_sections(texts)
                # 时机与效果必须都在：只有半截的多半是被引用的残片（规则更新页）或跨页截断，
                # 指纹会缺一段，宁可整条不要——半截指纹配出来的名字最难查。
                if not (sec.get(_SEC_WHEN) and sec.get(_SEC_EFFECT)):
                    continue
                det_zh, type_zh = (None, None)
                if texts and not _SECTION_RE.match(texts[0]):
                    det_zh, type_zh = _parse_det_line(texts[0])
                strat_segs.append((seg, sec, det_zh, type_zh))
                heads_here.append(seg.head)
                continue
            # 不是计谋：可能是强化（正文有「仅限…模型/单位。」的官方句式）
            if not is_det_page:
                continue
            cut = next((i for i, t in enumerate(texts) if t.startswith(_ENH_ONLY)), None)
            if cut is None:
                continue  # 分遣队规则、军规之类：不是强化，跳过
            enh_raw.append((_strip_badge(seg.head.text),
                            clean_text("".join(texts[:cut])),
                            clean_text("".join(texts[cut:]))))
        col_heads.append(heads_here)

    cp_map = _assign_cp(cp_lines, col_heads)
    strats: List[ZhStratagem] = []
    for idx, (seg, sec, det_zh, type_zh) in enumerate(strat_segs):
        strats.append(ZhStratagem(
            faction=faction, name_zh=clean_text(seg.head.text),
            detachment_zh=det_zh, type_zh=type_zh, cp=cp_map.get(idx),
            when_zh=sec.get(_SEC_WHEN, ""), target_zh=sec.get(_SEC_TARGET, ""),
            effect_zh=sec.get(_SEC_EFFECT, ""), source=source, page=page))
    if cp_lines and strat_segs and all(v is None for v in cp_map.values()):
        warns.append(f"{source} p{page}: CP 浮动框配不上标题"
                     f"（{len(cp_lines)} 框 / {len(strat_segs)} 条），本页 CP 判未知")

    det_ctx = _detachment_context(lines, strats, known_dets)
    if enh_raw and det_ctx is None:
        warns.append(f"{source} p{page}: 强化找不到分遣队上下文，全部丢弃")
    enhs = [ZhEnhancement(faction=faction, name_zh=n, detachment_zh=det_ctx,
                          legend_zh=lg, text_zh=tx, source=source, page=page)
            for n, lg, tx in enh_raw] if det_ctx else []
    return strats, enhs, warns


def _detachment_context(lines: Sequence[_Line], strats: Sequence[ZhStratagem],
                        known_dets: Optional[Set[str]]) -> Optional[str]:
    """这一页的强化属于哪个分遣队。取不到就返回 None（本页强化整页丢掉，计入报告）。

    ① 本页计谋一致指向的分遣队——最硬，计谋下面那行分遣队名是官方印上去的；
    ② 页面大标题（≥20pt）。**必须允许两行拼接**：长分遣队名会被排成两行大字
       （黑暗天使「莱昂之剑」+「特遣队」、泰伦「地底」+「突袭」、帝国特勤
       「隐藏利刃」+「歼灭部队」），只取第一行就永远对不上名单；
    ③ 页眉/小标题里恰好出现一个已知分遣队名（死亡守望的「死亡守望 - 黑矛特遣队」）。

    给了 known_dets（parse_pack 第一遍收的本包分遣队名单）就必须命中名单，且只认
    唯一命中：命中两个说明这页横跨两个分遣队，猜哪个都可能把强化挂到错的分遣队上。
    """
    dets_here = {s.detachment_zh for s in strats if s.detachment_zh}
    if len(dets_here) == 1:
        return next(iter(dets_here))
    big = sorted((l for l in lines
                  if l.size >= _TITLE_MIN_SIZE and len(l.text) <= 24),
                 key=lambda l: (l.y0, l.x0))
    titles = ([clean_text("".join(l.text for l in big))] +
              [l.text for l in big]) if big else []
    if known_dets is None:
        return titles[0] if titles else None
    hits = [t for t in titles if t in known_dets]
    if hits:
        return hits[0]
    found = {d for d in known_dets
             for l in lines if l.size >= 12.0 and d in l.text}
    return next(iter(found)) if len(found) == 1 else None


def _strip_badge(name: str) -> str:
    """剥掉版面装饰，只留名字本身：

      「活跃哨卫  升级」                         「升级」是徽标
      「诱饵目标...................+40 点」      帝国特勤的「极端技能」印了点数和引导点
    """
    txt = re.sub(r"[.．·]{3,}.*$", "", clean_text(name))
    txt = re.sub(r"\s*[+＋]?\s*\d+\s*点\s*$", "", txt)
    return re.sub(r"\s*升级\s*$", "", txt).strip()


# ---------------------------------------------------------------- 库侧读取

@dataclass(frozen=True)
class EnStratagem:
    sid: str
    faction: str
    detachment: str
    name_en: str
    cp: Optional[int]
    type_en: Optional[str]
    when_en: str
    target_en: str
    effect_en: str


@dataclass(frozen=True)
class EnEnhancement:
    eid: str
    faction: str
    detachment: str
    name_en: str
    description: str


_EN_SEC_RE = re.compile(r"<b>\s*(WHEN|TARGET|EFFECT|RESTRICTIONS)\s*:?\s*</b>", re.I)


def split_en_sections(text: str) -> Dict[str, str]:
    """库里的 stratagems.text_zh（名字是历史误称，内容其实是英文原文）切三段。"""
    if not text:
        return {}
    parts = _EN_SEC_RE.split(text)
    out: Dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        key = parts[i].lower()
        out[{"when": _SEC_WHEN, "target": _SEC_TARGET, "effect": _SEC_EFFECT,
             "restrictions": _SEC_RESTRICT}[key]] = strip_html(parts[i + 1])
    return out


def load_en_stratagems(db_path: Path) -> List[EnStratagem]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, faction, detachment, name_en, cp_cost, type, text_zh "
            "FROM stratagems").fetchall()
    finally:
        conn.close()
    out: List[EnStratagem] = []
    for sid, fac, det, name, cp, typ, text in rows:
        sec = split_en_sections(text or "")
        try:
            cp_i: Optional[int] = int(str(cp).strip())
        except (TypeError, ValueError):
            cp_i = None
        out.append(EnStratagem(sid, fac or "", det or "", name or "", cp_i, typ,
                               sec.get(_SEC_WHEN, ""), sec.get(_SEC_TARGET, ""),
                               sec.get(_SEC_EFFECT, "")))
    return out


def load_en_enhancements(db_path: Path) -> List[EnEnhancement]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, faction_id, detachment_name, name, description "
            "FROM enhancements").fetchall()
    finally:
        conn.close()
    return [EnEnhancement(r[0], r[1] or "", r[2] or "", r[3] or "",
                          strip_html(r[4] or "")) for r in rows]


# ---------------------------------------------------------------- 指纹配对

def strat_key_zh(s: ZhStratagem) -> Tuple[Any, ...]:
    return (s.faction, s.cp, "对手" in s.when_zh, phases_of_zh(s.when_zh),
            number_fingerprint(s.when_zh), number_fingerprint(s.target_zh),
            number_fingerprint(s.effect_zh))


def strat_key_en(s: EnStratagem) -> Tuple[Any, ...]:
    return (s.faction, s.cp, "opponent" in s.when_en.lower(), phases_of_en(s.when_en),
            number_fingerprint(s.when_en), number_fingerprint(s.target_en),
            number_fingerprint(s.effect_en))


def strat_key_loose_zh(s: ZhStratagem) -> Tuple[Any, ...]:
    """Pass B 用的放宽 key：去掉最易抽错的 cp 和最易被译法改写的 时机/目标 数字。"""
    return ("对手" in s.when_zh, phases_of_zh(s.when_zh),
            number_fingerprint(s.effect_zh))


def strat_key_loose_en(s: EnStratagem) -> Tuple[Any, ...]:
    return ("opponent" in s.when_en.lower(), phases_of_en(s.when_en),
            number_fingerprint(s.effect_en))


def _pair_bucket(en_items: Sequence[Any], zh_items: Sequence[Any],
                 type_en_of: Any, type_zh_of: Any) -> List[Tuple[Any, Any]]:
    """一个指纹桶内配对。1对1 直接配；多对多时**只有**两边 type 全齐才敢按 type 细分。

    type 有缺失就整桶放弃：缺 type 的条目可能属于任何一个子桶，按残留细分＝按位置猜。
    """
    if len(en_items) == 1 and len(zh_items) == 1:
        te, tz = type_en_of(en_items[0]), type_zh_of(zh_items[0])
        if te and tz and te != tz:
            return []
        return [(en_items[0], zh_items[0])]
    if not en_items or not zh_items:
        return []
    if not all(type_en_of(x) for x in en_items) or \
            not all(type_zh_of(x) for x in zh_items):
        return []
    by_en: Dict[str, List[Any]] = defaultdict(list)
    by_zh: Dict[str, List[Any]] = defaultdict(list)
    for x in en_items:
        by_en[type_en_of(x)].append(x)
    for x in zh_items:
        by_zh[type_zh_of(x)].append(x)
    out: List[Tuple[Any, Any]] = []
    for tag, ens in by_en.items():
        zhs = by_zh.get(tag, [])
        if len(ens) == 1 and len(zhs) == 1:
            out.append((ens[0], zhs[0]))
    return out


def _match_scoped(en_items: Sequence[Any], zh_items: Sequence[Any],
                  key_en: Any, key_zh: Any, type_en_of: Any, type_zh_of: Any
                  ) -> List[Tuple[Any, Any]]:
    """给定搜索域与 key，按指纹分桶，两边**各自唯一**才配。全部配对都走这一个闸。"""
    by_en: Dict[Any, List[Any]] = defaultdict(list)
    by_zh: Dict[Any, List[Any]] = defaultdict(list)
    for x in en_items:
        by_en[key_en(x)].append(x)
    for x in zh_items:
        by_zh[key_zh(x)].append(x)
    out: List[Tuple[Any, Any]] = []
    for key, zhs in by_zh.items():
        out.extend(_pair_bucket(by_en.get(key, []), zhs, type_en_of, type_zh_of))
    return out


def _strat_type_en(s: EnStratagem) -> Optional[str]:
    return canon_type_en(s.type_en)


def _strat_type_zh(s: ZhStratagem) -> Optional[str]:
    return canon_type_zh(s.type_zh)


def match_stratagems(en: Sequence[EnStratagem], zh: Sequence[ZhStratagem]
                     ) -> Tuple[List[Tuple[EnStratagem, ZhStratagem]],
                                Dict[str, Any]]:
    """Pass A：**整个阵营内**数值指纹唯一命中——最强的一档证据，不依赖任何推断。"""
    pairs = _match_scoped(en, zh, strat_key_en, strat_key_zh,
                          _strat_type_en, _strat_type_zh)
    done_zh = {id(z) for _, z in pairs}
    by_zh: Dict[Any, List[ZhStratagem]] = defaultdict(list)
    for s in zh:
        by_zh[strat_key_zh(s)].append(s)
    by_en: Dict[Any, List[EnStratagem]] = defaultdict(list)
    for s in en:
        by_en[strat_key_en(s)].append(s)
    ambiguous = [
        f"{zhs[0].faction}: {'/'.join(s.name_zh for s in zhs)} ↔ "
        f"{'/'.join(s.name_en for s in by_en[key])}"
        for key, zhs in by_zh.items()
        if by_en.get(key) and any(id(z) not in done_zh for z in zhs)]
    return pairs, {"ambiguous": ambiguous}


def derive_detachment_map(pairs: Sequence[Tuple[EnStratagem, ZhStratagem]],
                          min_votes: int = 2, majority: float = 0.6
                          ) -> Tuple[Dict[str, str], List[str]]:
    """由已配对战略**多数票**反推「英文容器名 → 中文分遣队名」。

    一条战略的分遣队归属在两边都是硬结构（中文印在计谋名下方，库里是 detachment 列），
    所以多条战略同时指向同一对，才敢把分遣队名也认下来。
    单票不落地：一条错配就能立起一个错的分遣队名，而分遣队名会被到处引用。
    """
    votes: Dict[str, Counter] = defaultdict(Counter)
    for e, z in pairs:
        if e.detachment and z.detachment_zh:
            votes[e.detachment][z.detachment_zh] += 1
    out: Dict[str, str] = {}
    rejected: List[str] = []
    for en_det, cnt in votes.items():
        total = sum(cnt.values())
        zh_det, n = cnt.most_common(1)[0]
        tied = [k for k, v in cnt.items() if v == n]
        if n < min_votes or n / total < majority or len(tied) > 1:
            rejected.append(f"{en_det}: {dict(cnt)}")
            continue
        out[en_det] = zh_det
    return out, rejected


def score_detachment_pairs(en: Sequence[EnStratagem], zh: Sequence[ZhStratagem],
                           en_enh: Sequence[EnEnhancement] = (),
                           zh_enh: Sequence[ZhEnhancement] = ()
                           ) -> Dict[Tuple[str, str], Tuple[int, int]]:
    """(中文分遣队, 英文容器) → (能按指纹 1-1 唯一互指的条数, 该中文分遣队的条目数)。

    带上条目数是为了给"覆盖率"设地板：只解释了这个中文分遣队一小半以下的条目，
    多半是巧合撞上的。**注意覆盖率只当地板、不当排序键**——试过拿占比排序，
    钛帝国「辅助核心队」（3 战略+2 强化）与 `Auxiliary Cadre`、`Kroot Hunting Pack`
    各重合 3 条，占比把票投给了后者，直接确认出一个错的分遣队对
    （Kroot Hunting Pack 是库鲁特狩猎队，跟辅助核心队毫无关系）。真平票就该谁都不认。

    为什么还要这一步：库里存着**同一条战略的两份**（Wahapedia 十版那份大写
    `UNLEASH THE LIONS` + Faction Pack 插进来的那份 `Unleash the Lions`，挂在
    不同容器上）。它们的指纹当然一模一样，于是 Pass A 的"全阵营唯一"永远撞车，
    整个帝皇卫队一条都配不上。把搜索域先降到"一个分遣队对"再看重合度，
    就把重复条目分开了——而这依然是指纹证据，不是按位置。

    强化也一起投票：11 版新分遣队只有 3 条战略，其中两条同型（都是"近战阶段 / 己方
    某单位 / +1 某属性"）就会互相撞车，只靠战略可能一条都算不上分（吞世者「恐虐屠夫」
    实测得 0 分）。它的 2 条强化数字指纹各不相同，正好把分数补起来。
    """
    zh_by: Dict[str, List[ZhStratagem]] = defaultdict(list)
    for s in zh:
        if s.detachment_zh:
            zh_by[s.detachment_zh].append(s)
    en_by: Dict[str, List[EnStratagem]] = defaultdict(list)
    for s in en:
        if s.detachment:
            en_by[s.detachment].append(s)
    zh_enh_by: Dict[str, List[ZhEnhancement]] = defaultdict(list)
    for e in zh_enh:
        if e.detachment_zh:
            zh_enh_by[e.detachment_zh].append(e)
    en_enh_by: Dict[str, List[EnEnhancement]] = defaultdict(list)
    for e in en_enh:
        if e.detachment:
            en_enh_by[e.detachment].append(e)
    scores: Dict[Tuple[str, str], Tuple[int, int]] = {}
    for zd, zl in zh_by.items():
        for ed, el in en_by.items():
            n = len(_match_scoped(el, zl, strat_key_en, strat_key_zh,
                                  _strat_type_en, _strat_type_zh))
            n += len(_match_scoped(
                en_enh_by.get(ed, []), zh_enh_by.get(zd, []),
                lambda e: number_fingerprint(e.description),
                lambda z: number_fingerprint(z.text_zh),
                lambda _e: None, lambda _z: None))
            if n:
                scores[(zd, ed)] = (n, len(zl) + len(zh_enh_by.get(zd, [])))
    return scores


def confirm_detachment_pairs(scores: Dict[Tuple[str, str], Tuple[int, int]],
                             min_score: int = 2) -> Dict[str, str]:
    """重合度打分 → 分遣队对。三道闸全过才算数：

      ① 重合 ≥ min_score 条——防单条巧合。单条重合真出过错配：吞世者「恐虐屠夫」
         全阵营只跟 `Boarding Butchers` 有 1 条交集，而那是错的（真对家
         `Butchers of Khorne` 因为 CP 漂移一条都没对上）；
      ② 覆盖这个中文分遣队 ≥ 40% 的条目——只解释了一小半以下多半是撞上的；
      ③ **互为唯一最优**：中文这边最像它、英文那边也最像它，且严格压过第二名。
         并列第一一律谁都不认，不用占比之类的次键去"打破"平局——试过，
         平局里被"打破"选中的恰恰是错的那个。
    """
    best_zh: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    best_en: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for (zd, ed), (n, zh_size) in scores.items():
        if n < min_score or n < _DET_MIN_COVERAGE * max(zh_size, 1):
            continue
        best_zh[zd].append((n, ed))
        best_en[ed].append((n, zd))

    def top(cands: List[Tuple[int, str]]) -> Optional[str]:
        ranked = sorted(cands, reverse=True)
        if not ranked:
            return None
        if len(ranked) > 1 and ranked[1][0] == ranked[0][0]:
            return None          # 并列第一：谁都不认
        return ranked[0][1]

    out: Dict[str, str] = {}
    for zd, cands in best_zh.items():
        ed = top(cands)
        if ed is not None and top(best_en[ed]) == zd:
            out[ed] = zd
    return out


def gate_by_detachment(pairs: Sequence[Tuple[EnStratagem, ZhStratagem]],
                       det_map: Dict[str, str]
                       ) -> Tuple[List[Tuple[EnStratagem, ZhStratagem]],
                                  List[Tuple[EnStratagem, ZhStratagem]]]:
    """分遣队一致性闸：**两侧分遣队必须已确认成对**，否则这对配不算数。

    这条闸是被两个真错逼出来的（2026-07-26 自查，都是 Pass A 全阵营指纹"唯一命中"）：

      · 帝皇之子「傲慢优越感」（凤凰王庭，2CP）被配给 `DEATH ECSTASY`
        （Peerless Bladesmen，2CP）——两条都是 2CP、都只在近战阶段、效果段都没数字。
        真对家 `PRIDEFUL SUPERIORITY` 因为库里还记着 1CP（官方 v1.1 改了 2CP）而落选。
      · 吞世者「失常怒火」（恐虐屠夫，1CP，远程 D-1）被配给 `SAVAGE RESILIENCE`
        （Boarding Butchers，1CP，伤害 -1）。真对家 `WRATH BEYOND REASON` 同样卡在 CP。

    两例都长一个样：**指纹一样不代表是同一条**，尤其"1CP + 某阶段 + 效果里一个 1"
    这种最常见的形状，全阵营几十条里撞车太容易。所以只有"这条中文计谋所属的分遣队
    已经被确认对应这个英文容器"时才认；分遣队没确认＝没证据，一条也不要。
    """
    kept: List[Tuple[EnStratagem, ZhStratagem]] = []
    dropped: List[Tuple[EnStratagem, ZhStratagem]] = []
    for e, z in pairs:
        ok = bool(e.detachment and z.detachment_zh and
                  det_map.get(e.detachment) == z.detachment_zh)
        (kept if ok else dropped).append((e, z))
    return kept, dropped


def match_within_detachments(en: Sequence[EnStratagem], zh: Sequence[ZhStratagem],
                             det_map: Dict[str, str], done_en: Set[str],
                             done_zh: Set[int]
                             ) -> List[Tuple[EnStratagem, ZhStratagem]]:
    """Pass B：在已确认的分遣队对内部补配残差——先完整 key，再放宽 key。

    为什么敢放宽：搜索域已经从"整个阵营"降到"这一个分遣队的 3-6 条"，而且这一对
    本身是靠指纹重合确认过的。放宽只去掉最易抽错的 cp（浮动框）和最易被译法改写的
    时机/目标数字，效果段数字仍要**完全相等**。

    为什么仍不做"残差配对"（两边各剩一条就认为它俩是一对）：官方 v1.1 和库里版本
    不一致时，"官方新增的一条"和"库里多出来的一条"会被残差法硬凑成一对——
    那正是数值对、名字错。
    """
    zh_det_to_en: Dict[str, List[str]] = defaultdict(list)
    for en_det, zh_det in det_map.items():
        zh_det_to_en[zh_det].append(en_det)
    pairs: List[Tuple[EnStratagem, ZhStratagem]] = []
    for en_det, zh_det in det_map.items():
        if len(zh_det_to_en[zh_det]) != 1:
            continue  # 一个中文分遣队名对上多个英文容器：不碰
        rest_en = [s for s in en if s.detachment == en_det and s.sid not in done_en]
        rest_zh = [s for s in zh
                   if s.detachment_zh == zh_det and id(s) not in done_zh]
        for key_en, key_zh in ((strat_key_en, strat_key_zh),
                               (strat_key_loose_en, strat_key_loose_zh)):
            got = _match_scoped(rest_en, rest_zh, key_en, key_zh,
                                _strat_type_en, _strat_type_zh)
            pairs.extend(got)
            taken_en = {e.sid for e, _ in got}
            taken_zh = {id(z) for _, z in got}
            rest_en = [s for s in rest_en if s.sid not in taken_en]
            rest_zh = [s for s in rest_zh if id(s) not in taken_zh]
    return pairs


def match_enhancements(en: Sequence[EnEnhancement], zh: Sequence[ZhEnhancement],
                       det_map: Dict[str, str]
                       ) -> Tuple[List[Tuple[EnEnhancement, ZhEnhancement]],
                                  Dict[str, Any]]:
    """强化配对。官方中文包不印点数，指纹只剩「描述里的数字多重集」，
    所以必须先用 det_map 把搜索域收窄到单个分遣队（一般 2-4 条）才有判别力。"""
    zh_det_to_en: Dict[str, List[str]] = defaultdict(list)
    for en_det, zh_det in det_map.items():
        zh_det_to_en[zh_det].append(en_det)
    pairs: List[Tuple[EnEnhancement, EnEnhancement]] = []
    ambiguous: List[str] = []
    no_det: List[str] = []
    for en_det, zh_det in det_map.items():
        if len(zh_det_to_en[zh_det]) != 1:
            continue
        ens = [e for e in en if e.detachment == en_det]
        zhs = [z for z in zh if z.detachment_zh == zh_det]
        got = _match_scoped(ens, zhs, lambda e: number_fingerprint(e.description),
                            lambda z: number_fingerprint(z.text_zh),
                            lambda _e: None, lambda _z: None)
        pairs.extend(got)
        done = {id(z) for _, z in got}
        by_en: Dict[Any, List[EnEnhancement]] = defaultdict(list)
        for e in ens:
            by_en[number_fingerprint(e.description)].append(e)
        by_zh: Dict[Any, List[ZhEnhancement]] = defaultdict(list)
        for z in zhs:
            by_zh[number_fingerprint(z.text_zh)].append(z)
        ambiguous.extend(
            f"{en_det}: {'/'.join(z.name_zh for z in zl)} ↔ "
            f"{'/'.join(e.name_en for e in by_en[key])}"
            for key, zl in by_zh.items()
            if by_en.get(key) and any(id(z) not in done for z in zl))
    for z in zh:
        if z.detachment_zh is None:
            no_det.append(f"{z.faction}: {z.name_zh}")
    return pairs, {"ambiguous": ambiguous, "no_detachment": no_det}


# ---------------------------------------------------------------- 编译入口

def _unique_or_drop(mapping: List[Tuple[str, str]]) -> Tuple[Dict[str, str],
                                                             List[str]]:
    """落地前的最后一道闸：一个中文名不能配给两个不同英文条目（反之亦然）。

    真出现这种情况说明指纹撞了车或官方包里有同名条目，两边全丢——
    错的中文名一旦落地，用户是看不出来的（数值对、名字错）。
    """
    by_en: Dict[str, Set[str]] = defaultdict(set)
    by_zh: Dict[str, Set[str]] = defaultdict(set)
    for en_name, zh_name in mapping:
        by_en[en_name].add(zh_name)
        by_zh[zh_name].add(en_name)
    out: Dict[str, str] = {}
    conflicts: List[str] = []
    for en_name, zh_names in by_en.items():
        if len(zh_names) > 1:
            conflicts.append(f"{en_name} → {sorted(zh_names)}")
            continue
        zh_name = next(iter(zh_names))
        if len(by_zh[zh_name]) > 1:
            conflicts.append(f"{zh_name} ← {sorted(by_zh[zh_name])}")
            continue
        out[en_name] = zh_name
    return out, sorted(conflicts)


def _row_map(mapping: List[Tuple[str, str]]) -> Tuple[Dict[str, str], List[str]]:
    """行级映射（库内 id → 中文名）。一行认两个不同中文名＝上游配对出了双份，两边都丢。

    与 `_unique_or_drop` 的区别：这里**不管**两行是否同名同中文——
    「同一中文名出现在两行」在行级是常态（同名战略分处两个分遣队），不是撞车。
    """
    by_id: Dict[str, Set[str]] = defaultdict(set)
    for rid, zh_name in mapping:
        by_id[rid].add(zh_name)
    out: Dict[str, str] = {}
    conflicts: List[str] = []
    for rid, zh_names in by_id.items():
        if len(zh_names) > 1:
            conflicts.append(f"{rid} → {sorted(zh_names)}")
            continue
        out[rid] = next(iter(zh_names))
    return out, sorted(conflicts)


def compile_official_zh(pdf_dir: Path = ZH_PDF_DIR,
                        db_path: Optional[Path] = None) -> Dict[str, Any]:
    """跑全流程：解析 28 个官方中文阵营包 → 指纹配对 → 映射 + 报告。"""
    db_path = db_path or (_ROOT / "db" / "wh40k.sqlite")
    manifest = json.loads((pdf_dir / "manifest.json").read_text(encoding="utf-8"))

    zh_strats: List[ZhStratagem] = []
    zh_enhs: List[ZhEnhancement] = []
    warns: List[str] = []
    skipped: List[str] = []
    for item in manifest.get("items", []):
        if item.get("kind") != "faction-pack":
            continue
        slug = item.get("faction_slug") or ""
        faction = SLUG_TO_FACTION.get(slug)
        if not faction:
            skipped.append(slug)
            continue
        s, e, w = parse_pack(pdf_dir / item["file"], faction)
        zh_strats.extend(s)
        zh_enhs.extend(e)
        warns.extend(w)

    en_strats = load_en_stratagems(db_path)
    en_enhs = load_en_enhancements(db_path)

    strat_pairs: List[Tuple[EnStratagem, ZhStratagem]] = []
    diag_amb: List[str] = []
    det_map: Dict[str, str] = {}
    det_rejected: List[str] = []
    det_conflicts: List[str] = []
    pass_a_n = pass_b_n = 0
    by_fac_zh: Dict[str, List[ZhStratagem]] = defaultdict(list)
    for s in zh_strats:
        by_fac_zh[s.faction].append(s)
    by_fac_en: Dict[str, List[EnStratagem]] = defaultdict(list)
    for s in en_strats:
        by_fac_en[s.faction].append(s)
    by_fac_zh_enh: Dict[str, List[ZhEnhancement]] = defaultdict(list)
    for e in zh_enhs:
        by_fac_zh_enh[e.faction].append(e)
    by_fac_en_enh: Dict[str, List[EnEnhancement]] = defaultdict(list)
    for e in en_enhs:
        by_fac_en_enh[e.faction].append(e)

    for fac, zl in by_fac_zh.items():
        el = by_fac_en.get(fac, [])
        pairs, diag = match_stratagems(el, zl)          # Pass A：全阵营唯一
        diag_amb.extend(diag["ambiguous"])
        # 分遣队对两条独立证据链：① 一对分遣队内部能按指纹唯一互指几条（战略+强化）；
        # ② Pass A 的全阵营唯一配对投票。两条都要够票才落地，冲突则两边都记进报告。
        fac_map = confirm_detachment_pairs(score_detachment_pairs(
            el, zl, by_fac_en_enh.get(fac, []), by_fac_zh_enh.get(fac, [])))
        voted, rej = derive_detachment_map(pairs)
        det_rejected.extend(rej)
        det_conflicts.extend(f"分遣队对打架 {k}: 票={voted[k]} vs 重合={fac_map[k]}"
                             for k in set(voted) & set(fac_map)
                             if voted[k] != fac_map[k])
        fac_map.update({k: v for k, v in voted.items() if k not in fac_map})
        det_map.update(fac_map)
        kept, dropped = gate_by_detachment(pairs, fac_map)
        det_conflicts.extend(f"配对跨分遣队 {e.name_en} ↔ {z.name_zh}"
                             f"（{e.detachment} vs {z.detachment_zh}）"
                             for e, z in dropped)
        more = match_within_detachments(el, zl, fac_map,
                                        {e.sid for e, _ in kept},
                                        {id(z) for _, z in kept})
        pass_a_n += len(kept)
        pass_b_n += len(more)
        strat_pairs.extend(kept)
        strat_pairs.extend(more)

    enh_pairs, enh_diag = match_enhancements(en_enhs, zh_enhs, det_map)

    strat_map, strat_conf = _unique_or_drop(
        [(e.name_en.upper(), z.name_zh) for e, z in strat_pairs if e.name_en])
    enh_map, enh_conf = _unique_or_drop(
        [(e.name_en, z.name_zh) for e, z in enh_pairs if e.name_en])
    strat_rows, strat_row_conf = _row_map([(e.sid, z.name_zh)
                                           for e, z in strat_pairs if e.sid])
    enh_rows, enh_row_conf = _row_map([(e.eid, z.name_zh)
                                       for e, z in enh_pairs if e.eid])

    done_s = {id(x) for _, x in strat_pairs}
    done_e = {id(x) for _, x in enh_pairs}
    unmatched_strats = [f"{z.faction}/{z.detachment_zh}: {z.name_zh}"
                        for z in zh_strats if id(z) not in done_s]
    unmatched_enhs = [f"{z.faction}/{z.detachment_zh}: {z.name_zh}"
                      for z in zh_enhs if id(z) not in done_e]
    # 全篇没有数字的条目，指纹是空的——证据只剩「在这个已确认的分遣队对里两边都只有它
    # 一条没数字」。这是整条链上最弱的一档，单独报出来供人工抽查（实测抽查未见错配）。
    weak_s = sum(1 for e, _ in strat_pairs
                 if not (number_fingerprint(e.when_en) +
                         number_fingerprint(e.target_en) +
                         number_fingerprint(e.effect_en)))
    weak_e = sum(1 for e, _ in enh_pairs if not number_fingerprint(e.description))
    by_faction = {
        fac: {"zh_parsed": len(zl),
              "matched": sum(1 for _, z in strat_pairs if z.faction == fac)}
        for fac, zl in sorted(by_fac_zh.items())}

    return {
        "stratagems": dict(sorted(strat_map.items())),
        "stratagems_by_id": dict(sorted(strat_rows.items())),
        "enhancements": dict(sorted(enh_map.items())),
        "enhancements_by_id": dict(sorted(enh_rows.items())),
        "detachments": dict(sorted(det_map.items())),
        "_report": {
            "_comment": "GW 官方中文包 → 库内英文条目的数值指纹配对结果。"
                        "命中＝两边指纹唯一互指；未命中一律留空（宁缺毋错）。",
            "generated_from": str(pdf_dir.name),
            "zh_parsed": {"stratagems": len(zh_strats),
                          "enhancements": len(zh_enhs)},
            "matched": {"stratagems": len(strat_map),
                        "stratagems_pass_a_faction_unique": pass_a_n,
                        "stratagems_pass_b_within_detachment": pass_b_n,
                        "enhancements": len(enh_map),
                        "detachments": len(det_map),
                        # 行级恒 ≥ 名级：名级要为「同名不同译」整条让路，行级不用
                        "stratagems_rows": len(strat_rows),
                        "enhancements_rows": len(enh_rows)},
            "db_totals": {"stratagems": len(en_strats),
                          "enhancements": len(en_enhs)},
            "weak_evidence_no_digits": {"stratagems": weak_s,
                                        "enhancements": weak_e},
            "by_faction_stratagems": by_faction,
            "unmatched_sample": {
                "stratagems": sorted(unmatched_strats)[:40],
                "stratagems_total": len(unmatched_strats),
                "enhancements": sorted(unmatched_enhs)[:40],
                "enhancements_total": len(unmatched_enhs),
            },
            "ambiguous_sample": {
                "stratagems": sorted(diag_amb)[:30],
                "stratagems_total": len(diag_amb),
                "enhancements": sorted(enh_diag["ambiguous"])[:30],
                "enhancements_total": len(enh_diag["ambiguous"]),
            },
            "detachment_votes_rejected": sorted(det_rejected)[:30],
            "detachment_conflicts": sorted(det_conflicts)[:30],
            "detachment_conflicts_total": len(det_conflicts),
            "name_conflicts": {"stratagems": strat_conf[:20],
                               "enhancements": enh_conf[:20]},
            "row_conflicts": {"stratagems": strat_row_conf[:20],
                              "enhancements": enh_row_conf[:20]},
            "parse_warnings": sorted(set(warns))[:30],
            "parse_warnings_total": len(warns),
            "skipped_slugs": skipped,
        },
    }


def write_official_zh(out_path: Path = OUT_PATH, **kwargs: Any) -> Dict[str, Any]:
    """产物写盘：UTF-8 + LF（Windows 下 newline='\\n' 必须显式给，否则写成 CRLF）。"""
    data = compile_official_zh(**kwargs)
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return data
