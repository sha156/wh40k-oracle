"""脏数据 → 干净数值的解析层（P4-a 核心）。

三解析器，全部基于实测数据形态（见 spec 第三节）：
  1. 骰子解析器  parse_dice：`5` / `D6` / `4D6` / `D6+3` / `2D3+3` / `D6+8` → DiceExpr
  2. 属性归一器  norm_stat_int / parse_ap：`6"` `4+` `20+"` `4*` `-` `N/A` `-0` → int|None
  3. 词条分词器  tokenize_keywords：`["anti-infantry 4+, devastating wounds, rapid fire d3"]`
                → [ParsedKeyword(...)]（词条→Effect 的语义映射是 P4-c 的 keywords.py）

parse.py 可 import numpy（采样是引擎数学，不碰 DB）；contracts.py 保持零依赖。
不静默丢：无法解析的骰子抛 ParseError，未识别的词条标 recognized=False，由调用方收集上报。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import numpy as np

from engines.simulator.contracts import DiceExpr


class ParseError(ValueError):
    """无法解析的数值/骰子表达式（调用方应捕获并计入 unparsed，禁止静默吞掉）。"""


# ---------------------------------------------------------------------------
# 1. 骰子解析器
# ---------------------------------------------------------------------------
_DICE_RE = re.compile(r"^(\d*)[dD](\d+)([+-]\d+)?$")
_INT_RE = re.compile(r"^[+-]?\d+$")


def parse_dice(value: Optional[str]) -> DiceExpr:
    """`NdM+K` / 常量 → DiceExpr。无法解析抛 ParseError。"""
    if value is None:
        raise ParseError("dice value is None")
    text = str(value).strip()
    if _INT_RE.match(text):
        return DiceExpr(n=0, faces=0, k=int(text))
    m = _DICE_RE.match(text)
    if m:
        n = int(m.group(1)) if m.group(1) else 1
        faces = int(m.group(2))
        k = int(m.group(3)) if m.group(3) else 0
        return DiceExpr(n=n, faces=faces, k=k)
    raise ParseError(f"cannot parse dice: {value!r}")


def expected_dice(expr: DiceExpr) -> float:
    """DiceExpr 的期望值（校验/报告用）。"""
    if expr.is_constant:
        return float(expr.k)
    return expr.n * (expr.faces + 1) / 2.0 + expr.k


def sample_dice(expr: DiceExpr, rng: np.random.Generator,
                size: Union[int, Tuple[int, ...]]) -> np.ndarray:
    """向量化采样：返回形状 size 的整型数组（P4-b 掷骰引擎用）。"""
    size_t: Tuple[int, ...] = size if isinstance(size, tuple) else (size,)
    if expr.is_constant:
        return np.full(size_t, expr.k, dtype=np.int64)
    rolls = rng.integers(1, expr.faces + 1, size=(expr.n,) + size_t, dtype=np.int64)
    return rolls.sum(axis=0) + expr.k


# ---------------------------------------------------------------------------
# 2. 属性归一器
# ---------------------------------------------------------------------------
_NULL_STATS = {"-", "n/a", "?", "", "–", "—", "n/a."}
_STAT_STRIP = ('"', "”", "“", "″", "′", "'", "寸", "吋", "+", "*", " ", "\t")


def norm_stat_int(value) -> Optional[int]:
    """M/T/SV/W/OC/invuln/BS-WS 归一到 int：去 `"` `+` `*` 单位；`-`/`N/A`/空 → None。

    例：`6"`→6、`4+`→4、`20+"`→20、`4*`→4、`5*`→5、`-`→None、`N/A`→None。
    """
    if value is None:
        return None
    s = str(value).strip().lower()
    for ch in _STAT_STRIP:
        s = s.replace(ch, "")
    if s in _NULL_STATS or s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_ap(value) -> int:
    """AP 归一：负值保留（-1/-2），`-`/`-0`/空 → 0。"""
    if value is None:
        return 0
    s = str(value).strip()
    if s in ("-", "–", "—", "", "-0", "+0"):
        return 0
    try:
        return int(s)
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# 3. 词条分词器
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ParsedKeyword:
    """一个归一化词条 token。语义映射（→ Effect）在 P4-c 的 keywords.py。"""
    name: str                # canonical：小写、空格/连字符→下划线（rapid_fire / twin_linked / anti）
    params: Tuple = ()       # 数值参数：int（rapid_fire 1）/ DiceExpr（sustained_hits d3）/ ("infantry", 4)（anti）
    raw: str = ""            # 原始 token（诊断用）
    recognized: bool = True  # False = 未纳入 P4 建模词库（低频专属），调用方收集为 unparsed/not_modeled


# P4 建模的无参 flag 词条（语义在 keywords.py）
KNOWN_FLAG = frozenset({
    "pistol", "twin_linked", "devastating_wounds", "ignores_cover", "torrent",
    "heavy", "hazardous", "assault", "psychic", "lethal_hits", "precision",
    "one_shot", "extra_attacks", "indirect_fire", "lance", "conversion",
})
# P4 建模的带参词条
KNOWN_PARAM = frozenset({"rapid_fire", "sustained_hits", "melta", "blast", "anti", "cleave"})

_ANTI_RE = re.compile(r"^anti-(.+?)\s+(\d)\+?$")


def _canon(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def _try_param(word: str):
    """把末词解析成 int / DiceExpr；不是参数则返回 None。"""
    w = word.strip()
    if re.fullmatch(r"\d+", w):
        return int(w)
    if re.fullmatch(r"\d+\+", w):
        return int(w[:-1])
    if _DICE_RE.match(w):
        return parse_dice(w)
    return None


def parse_keyword_token(token: str) -> ParsedKeyword:
    """单个 token（已按逗号拆分）→ ParsedKeyword。"""
    t = token.strip().lower()
    if not t:
        return ParsedKeyword(name="", raw=token, recognized=False)

    # anti-X N+（目标可多词，如 "epic hero"）
    m = _ANTI_RE.match(t)
    if m:
        return ParsedKeyword(name="anti", params=(m.group(1).strip(), int(m.group(2))),
                             raw=token, recognized=True)

    # 带参词条：末词是数值/骰子
    if " " in t:
        head, _, last = t.rpartition(" ")
        param = _try_param(last)
        if param is not None:
            name = _canon(head)
            return ParsedKeyword(name=name, params=(param,), raw=token,
                                 recognized=name in KNOWN_PARAM)

    # flag 词条 / 未识别专属词条
    name = _canon(t)
    return ParsedKeyword(name=name, params=(), raw=token,
                         recognized=name in KNOWN_FLAG or name in KNOWN_PARAM)


def tokenize_keywords(keywords_json: Optional[str]) -> Tuple[List[ParsedKeyword], List[str]]:
    """weapons.keywords_json（单元素数组里逗号拼一坨）→ (ParsedKeyword 列表, 未识别原始 token 列表)。

    实测格式：`["anti-infantry 4+, devastating wounds, rapid fire 1"]`（大小写混乱、可含骰子参数）。
    """
    if not keywords_json:
        return [], []
    try:
        raw = json.loads(keywords_json)
    except (json.JSONDecodeError, TypeError):
        return [], [str(keywords_json)]
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], [str(raw)]

    parsed: List[ParsedKeyword] = []
    unknown: List[str] = []
    for elem in raw:
        for chunk in str(elem).split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            pk = parse_keyword_token(chunk)
            parsed.append(pk)
            if not pk.recognized:
                unknown.append(chunk)
    return parsed, unknown
