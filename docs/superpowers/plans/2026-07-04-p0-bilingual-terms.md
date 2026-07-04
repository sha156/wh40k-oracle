# P0 双语术语表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扫描 `data_refined/` 产出实体清单，以 Wahapedia canonical 英文名为锚做中英配对，生成 `wiki/terms.md` / `wiki/terms.json`，并接入 `app.py` 的查询扩展，立即提升现有检索链。

**Architecture:** 新建 `wiki_compile/` 包（spec 第三节流水线①②）：`extract.py` 解析页级 md 的 `##` 标题（中文书标题自带英文原名，实测格式 `## 克鲁特狂兽小队 KROOTOX RAMPAGERS`）；`canonical.py` 下载并解析 Wahapedia CSV（`|` 分隔）；`pair.py` 先精确匹配、按书多数票推断阵营后模糊匹配、LLM 只兜底残余；`terms.py` 产出双语术语表。`app.py` 加载 terms.json 扩展查询（与现有 UNIT_ALIASES 同机制）。

**Tech Stack:** Python 3.9（项目 venv `.venv\Scripts\python.exe`）、stdlib（re/json/difflib/urllib）、openai 客户端（deepseek，仅 LLM 兜底步）、pytest。

## Global Constraints

- 一律用项目 venv：`.\.venv\Scripts\python.exe`（系统 python 是 3.9 但缺依赖；venv 也是 3.9.1 → **禁用 `str | None` 语法，每个新文件首行 `from __future__ import annotations`，注解用 `Optional[...]`**）
- API key 走环境变量 `DEEPSEEK_API_KEY`，不落盘（spec 约定）
- 下载 Wahapedia 需代理：PowerShell 里 `$env:HTTPS_PROXY = "http://127.0.0.1:7897"`（urllib 自动读取环境代理）
- LLM 调用必须带内容哈希缓存（spec：全流程内容哈希缓存），缓存放 `wiki_build/llm_cache/`
- 产物提交规则：`wiki/terms.md`、`wiki/terms.json` **提交**；`wiki_build/`、`db_sources/` **不提交**（Task 6 加 .gitignore）
- 配对权威源 = Wahapedia canonical 英文名（spec 第一节决策4）
- 不要 import `llm_refine`（其模块顶部有设置代理环境变量的副作用）；LLM 常量在本包内自定义
- 提交信息遵循项目惯例：中文、`feat:`/`fix:`/`docs:` 前缀

## 文件结构（本计划新建/修改的全部文件）

```
wiki_compile/
├── __init__.py          空包标记
├── extract.py           流水线①：页面扫描 + 标题解析 → EntityCandidate
├── canonical.py         Wahapedia CSV 下载/解析 → CanonicalEntry
├── pair.py              流水线②：精确/模糊配对 → Pair / PairingResult
├── pair_llm.py          LLM 兜底配对（deepseek，带哈希缓存）
├── terms.py             terms.md / terms.json / review_needed.md 生成 + load_term_aliases
└── __main__.py          CLI：python -m wiki_compile extract|fetch-canonical|pair|terms
tests/
├── test_wiki_extract.py
├── test_wiki_canonical.py
├── test_wiki_pair.py
└── test_wiki_terms.py
app.py                   修改：加载 wiki/terms.json 进查询扩展
.gitignore               修改：忽略 wiki_build/ db_sources/
CLAUDE.md                修改：运行方式补 wiki_compile 命令
```

---

### Task 1: 标题解析器（extract.py 的 parse_heading）

**Files:**
- Create: `wiki_compile/__init__.py`
- Create: `wiki_compile/extract.py`
- Test: `tests/test_wiki_extract.py`

**Interfaces:**
- Consumes: 无（纯函数）
- Produces: `parse_heading(heading: str) -> Tuple[Optional[str], Optional[str]]` 返回 `(name_zh, name_en)`；`EntityCandidate` dataclass（字段：`book: str, raw_heading: str, name_zh: Optional[str], name_en: Optional[str], pages: List[int]`）。Task 2/3/4 依赖这两个名字。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_wiki_extract.py
"""标题解析与实体抽取测试。样本取自 data_refined 实测格式。"""
from wiki_compile.extract import parse_heading


class TestParseHeading:
    def test_bilingual_heading(self):
        assert parse_heading("克鲁特狂兽小队 KROOTOX RAMPAGERS") == (
            "克鲁特狂兽小队", "KROOTOX RAMPAGERS")

    def test_numbered_prefix_stripped(self):
        assert parse_heading("(TX4)水虎鱼 PIRANHAS") == ("水虎鱼", "PIRANHAS")
        assert parse_heading("(XV88)炮击战斗服小队 BROADSIDE BATTLESUITS") == (
            "炮击战斗服小队", "BROADSIDE BATTLESUITS")

    def test_pure_english_heading(self):
        assert parse_heading("TA’UNAR SUPREMACY ARMOUR") == (
            None, "TA’UNAR SUPREMACY ARMOUR")

    def test_pure_chinese_heading(self):
        assert parse_heading("冲锋阶段") == ("冲锋阶段", None)

    def test_inline_model_code_not_english_name(self):
        # 型号码在中文名里、真正英文名在结尾
        assert parse_heading("XV104暴风谍影战斗服 RIPTIDE BATTLESUITS")[1] == (
            "RIPTIDE BATTLESUITS")

    def test_short_english_tail_ignored(self):
        # 结尾孤立大写字母不算英文名（长度<3）
        zh, en = parse_heading("战术目标 A")
        assert en is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_extract.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'wiki_compile'`

- [ ] **Step 3: Write minimal implementation**

`wiki_compile/__init__.py` 内容为空文件。

```python
# wiki_compile/extract.py
"""extract_entities —— 扫描 data_refined 页级 md，产出实体候选清单（wiki_compile 流水线①）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

CONT_MARKER = "<!--CONT-->"

# 形如 (TX4) / （XV104） 的编号前缀
_PREFIX_RE = re.compile(r"^[\(（][^\)）]{1,10}[\)）]\s*")
# 标题结尾的英文名：大写开头、由大写/数字/常见标点组成、一直到行尾
_EN_TAIL_RE = re.compile(r"[A-Z][A-Z0-9'’\-\.,&/\(\) ]*$")
# 解说性子标题后缀：并入同名实体页码，不单独成实体
NOISE_SUFFIXES = ("能力详解", "武器详解", "技能详解", "详解")


@dataclass
class EntityCandidate:
    book: str
    raw_heading: str
    name_zh: Optional[str]
    name_en: Optional[str]
    pages: List[int] = field(default_factory=list)


def parse_heading(heading: str) -> Tuple[Optional[str], Optional[str]]:
    """'克鲁特狂兽小队 KROOTOX RAMPAGERS' → (中文名, 英文名)；缺失侧为 None。"""
    text = _PREFIX_RE.sub("", heading.strip())
    m = _EN_TAIL_RE.search(text)
    if m and len(m.group(0).strip()) >= 3:
        en = m.group(0).strip()
        zh = text[: m.start()].strip() or None
        return zh, en
    return (text or None), None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_extract.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```powershell
git add wiki_compile tests\test_wiki_extract.py
git commit -m "feat: wiki_compile 标题解析器（中英双语标题拆分）"
```

---

### Task 2: 页面扫描 extract_entities

**Files:**
- Modify: `wiki_compile/extract.py`（追加函数）
- Test: `tests/test_wiki_extract.py`（追加测试类）

**Interfaces:**
- Consumes: Task 1 的 `parse_heading`、`EntityCandidate`、`CONT_MARKER`、`NOISE_SUFFIXES`
- Produces: `extract_book(book_dir: Path) -> List[EntityCandidate]`；`extract_entities(data_refined_dir: Path) -> List[EntityCandidate]`。Task 4 消费 `List[EntityCandidate]`；Task 6 CLI 将其序列化为 `wiki_build/entities.json`（`[{book, raw_heading, name_zh, name_en, pages}, ...]`）。

- [ ] **Step 1: Write the failing test**

追加到 `tests/test_wiki_extract.py`：

```python
from pathlib import Path

from wiki_compile.extract import extract_book, extract_entities


def _write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8")


class TestExtractBook:
    def _make_book(self, tmp_path: Path) -> Path:
        book = tmp_path / "测试书"
        book.mkdir()
        _write(book / "page_001.md",
               "## 火战士队 FIRE WARRIORS\n| M | T |\n### 远程武器\n...")
        # 续页：CONT 标记 → 页码并入前一实体
        _write(book / "page_002.md",
               "<!--CONT-->\n### 技能\n...")
        # 解说标题 → 并入同名实体，不新建
        _write(book / "page_003.md",
               "## 火战士队 FIRE WARRIORS 能力详解\n...\n## 冷言 COLDSTAR\n...")
        # meta 文件不应干扰扫描
        _write(book / "page_001.meta.json", "{}")
        return book

    def test_extracts_and_merges(self, tmp_path):
        cands = extract_book(self._make_book(tmp_path))
        assert [c.name_zh for c in cands] == ["火战士队", "冷言"]
        fw = cands[0]
        assert fw.name_en == "FIRE WARRIORS"
        assert fw.pages == [1, 2, 3]      # 首页 + CONT续页 + 详解页
        assert cands[1].pages == [3]

    def test_pure_noise_heading_skipped(self, tmp_path):
        book = tmp_path / "b"
        book.mkdir()
        _write(book / "page_001.md", "## 能力详解\n...")
        assert extract_book(book) == []

    def test_extract_entities_walks_all_books(self, tmp_path):
        b1 = tmp_path / "书一"; b1.mkdir()
        _write(b1 / "page_001.md", "## 单位甲 UNIT ALPHA\n...")
        b2 = tmp_path / "书二"; b2.mkdir()
        _write(b2 / "page_001.md", "## 单位乙 UNIT BETA\n...")
        cands = extract_entities(tmp_path)
        assert {(c.book, c.name_zh) for c in cands} == {
            ("书一", "单位甲"), ("书二", "单位乙")}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_extract.py -v`
Expected: 新增测试 FAIL，`ImportError: cannot import name 'extract_book'`

- [ ] **Step 3: Write minimal implementation**

追加到 `wiki_compile/extract.py`（顶部补 `from pathlib import Path`）：

```python
def extract_book(book_dir: Path) -> List[EntityCandidate]:
    """单本书：扫 page_*.md 的 ## 标题；CONT 续页与'详解'页并入实体页码。"""
    out: List[EntityCandidate] = []
    by_key = {}
    current: Optional[EntityCandidate] = None
    for md in sorted(book_dir.glob("page_*.md")):
        page_no = int(md.stem.split("_")[1])
        lines = md.read_text(encoding="utf-8").splitlines()
        if lines and lines[0].strip() == CONT_MARKER and current is not None \
                and page_no not in current.pages:
            current.pages.append(page_no)
        for line in lines:
            if not line.startswith("## "):
                continue
            heading = line[3:].strip()
            base, noise = heading, False
            for suf in NOISE_SUFFIXES:
                if base.endswith(suf):
                    base = base[: -len(suf)].strip()
                    noise = True
                    break
            if not base:
                continue  # 纯解说标题（## 能力详解）
            zh, en = parse_heading(base)
            key = (zh, en)
            if noise:
                cand = by_key.get(key)
                if cand is not None and page_no not in cand.pages:
                    cand.pages.append(page_no)
                continue
            cand = by_key.get(key)
            if cand is None:
                cand = EntityCandidate(book=book_dir.name, raw_heading=heading,
                                       name_zh=zh, name_en=en, pages=[page_no])
                by_key[key] = cand
                out.append(cand)
            elif page_no not in cand.pages:
                cand.pages.append(page_no)
            current = cand
    return out


def extract_entities(data_refined_dir: Path) -> List[EntityCandidate]:
    result: List[EntityCandidate] = []
    for book_dir in sorted(p for p in data_refined_dir.iterdir() if p.is_dir()):
        result.extend(extract_book(book_dir))
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_extract.py -v`
Expected: 全部 passed（Task 1 的 6 个 + 本任务 3 个）

- [ ] **Step 5: 冒烟验证真实数据（不提交产物）**

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from wiki_compile.extract import extract_book; c=extract_book(Path('data_refined/钛帝国十版CODEX-20251112')); print(len(c)); [print(x.name_zh, '|', x.name_en, x.pages) for x in c[:8]]"
```
Expected: 数十个实体；抽查中英文名与 PDF 一致、无"能力详解"独立实体。若发现新的噪声标题形态，把后缀加进 `NOISE_SUFFIXES` 并补一条对应测试。

- [ ] **Step 6: Commit**

```powershell
git add wiki_compile\extract.py tests\test_wiki_extract.py
git commit -m "feat: extract_entities 扫描 data_refined 产出实体候选（CONT续页/详解页合并）"
```

---

### Task 3: Wahapedia canonical 数据源（canonical.py）

**Files:**
- Create: `wiki_compile/canonical.py`
- Test: `tests/test_wiki_canonical.py`

**Interfaces:**
- Consumes: 无
- Produces: `parse_wahapedia_csv(text: str) -> List[Dict[str, str]]`；`CanonicalEntry`（frozen dataclass，字段 `id: str, name: str, faction_id: str`）；`load_canonical(csv_dir: Path) -> List[CanonicalEntry]`；`fetch_tables(dest: Path) -> None`（下载 `Factions.csv` + `Datasheets.csv`）。Task 4 消费 `List[CanonicalEntry]`。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_wiki_canonical.py
"""Wahapedia CSV 解析测试（离线 fixture，不联网）。"""
from pathlib import Path

from wiki_compile.canonical import CanonicalEntry, load_canonical, parse_wahapedia_csv

# Wahapedia 导出格式：| 分隔，行尾多一个 |，可能带 BOM
FIXTURE = "﻿id|name|faction_id|role|\n" \
          "000001|Fire Warriors|TAU|Battleline|\n" \
          "000002|Commander Farsight|TAU|Character|\n" \
          "000003||TAU|Character|\n"          # 空名行应被 load_canonical 丢弃


class TestParseCsv:
    def test_parses_pipe_delimited_with_bom(self):
        rows = parse_wahapedia_csv(FIXTURE)
        assert rows[0]["name"] == "Fire Warriors"
        assert rows[0]["faction_id"] == "TAU"
        assert len(rows) == 3

    def test_trailing_pipe_ignored(self):
        rows = parse_wahapedia_csv(FIXTURE)
        assert "" not in rows[0]  # 行尾空字段不产生空键


class TestLoadCanonical:
    def test_load_skips_empty_names(self, tmp_path):
        (tmp_path / "Datasheets.csv").write_text(FIXTURE, encoding="utf-8")
        entries = load_canonical(tmp_path)
        assert entries == [
            CanonicalEntry(id="000001", name="Fire Warriors", faction_id="TAU"),
            CanonicalEntry(id="000002", name="Commander Farsight", faction_id="TAU"),
        ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_canonical.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'wiki_compile.canonical'`

- [ ] **Step 3: Write minimal implementation**

```python
# wiki_compile/canonical.py
"""Wahapedia CSV 下载与解析 —— 中英配对的 canonical 英文名锚点（spec 决策4）。"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

WAHAPEDIA_BASE = "https://wahapedia.ru/wh40k10ed"
TABLES = ("Factions.csv", "Datasheets.csv")


@dataclass(frozen=True)
class CanonicalEntry:
    id: str
    name: str
    faction_id: str


def parse_wahapedia_csv(text: str) -> List[Dict[str, str]]:
    """Wahapedia 导出：| 分隔、行尾多一个 |、首行表头、可能带 BOM。"""
    lines = [ln for ln in text.replace("﻿", "").splitlines() if ln.strip()]
    header = [h.strip() for h in lines[0].split("|")]
    rows: List[Dict[str, str]] = []
    for ln in lines[1:]:
        fields = ln.split("|")
        rows.append({h: (fields[i].strip() if i < len(fields) else "")
                     for i, h in enumerate(header) if h})
    return rows


def fetch_tables(dest: Path) -> None:
    """下载 canonical 表。需环境代理（HTTPS_PROXY），urllib 自动读取。"""
    dest.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        url = "{}/{}".format(WAHAPEDIA_BASE, table)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            (dest / table).write_bytes(resp.read())
        print("已下载", table)


def load_canonical(csv_dir: Path) -> List[CanonicalEntry]:
    rows = parse_wahapedia_csv(
        (csv_dir / "Datasheets.csv").read_text(encoding="utf-8"))
    return [CanonicalEntry(id=r.get("id", ""), name=r.get("name", ""),
                           faction_id=r.get("faction_id", ""))
            for r in rows if r.get("name")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_canonical.py -v`
Expected: 3 passed

- [ ] **Step 5: 真实下载验证（联网，需代理）**

```powershell
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
.\.venv\Scripts\python.exe -c "from pathlib import Path; from wiki_compile.canonical import fetch_tables, load_canonical; fetch_tables(Path('db_sources/wahapedia')); c=load_canonical(Path('db_sources/wahapedia')); print(len(c), c[0])"
```
Expected: 打印条目数（约 1300+）和首条 `CanonicalEntry`。若实际表头列名与 `id/name/faction_id` 不符，打开 `db_sources/wahapedia/Datasheets.csv` 首行核对并修正 `load_canonical` 的键名，同步更新测试 fixture 的表头。

- [ ] **Step 6: Commit**

```powershell
git add wiki_compile\canonical.py tests\test_wiki_canonical.py
git commit -m "feat: Wahapedia CSV 下载与 canonical 名录解析"
```

---

### Task 4: 确定性配对 pair_entities（精确 + 阵营内模糊）

**Files:**
- Create: `wiki_compile/pair.py`
- Test: `tests/test_wiki_pair.py`

**Interfaces:**
- Consumes: `EntityCandidate`（Task 2）、`CanonicalEntry`（Task 3）
- Produces: `normalize_name(name: str) -> str`；`Pair`（dataclass：`zh: Optional[str], en: str, canonical_id: str, faction_id: str, book: str, pages: List[int], confidence: str`，confidence ∈ `"exact"|"fuzzy"|"llm"`）；`PairingResult`（dataclass：`pairs: List[Pair], unmatched: List[EntityCandidate]`）；`pair_entities(entities: List[EntityCandidate], canonical: List[CanonicalEntry]) -> PairingResult`。Task 5 消费 `PairingResult.unmatched`，Task 6 消费 `PairingResult`。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_wiki_pair.py
"""中英配对测试：精确匹配 → 阵营推断 → 阵营内模糊匹配。"""
from wiki_compile.canonical import CanonicalEntry
from wiki_compile.extract import EntityCandidate
from wiki_compile.pair import Pair, PairingResult, normalize_name, pair_entities

CANONICAL = [
    CanonicalEntry("1", "Fire Warriors", "TAU"),
    CanonicalEntry("2", "Commander Farsight", "TAU"),
    CanonicalEntry("3", "Ta'unar Supremacy Armour", "TAU"),
    CanonicalEntry("4", "Hormagaunts", "TYR"),
]


def _cand(zh, en, book="钛书"):
    return EntityCandidate(book=book, raw_heading=(zh or "") + " " + (en or ""),
                           name_zh=zh, name_en=en, pages=[1])


class TestNormalize:
    def test_case_and_typographic_apostrophe(self):
        # 弯引号（PDF提取常见）与直引号归一
        assert normalize_name("TA’UNAR SUPREMACY ARMOUR") == \
               normalize_name("Ta'unar Supremacy Armour")

    def test_extra_spaces_collapsed(self):
        assert normalize_name("FIRE  WARRIORS ") == "FIRE WARRIORS"


class TestPairEntities:
    def test_exact_match(self):
        r = pair_entities([_cand("火战士队", "FIRE WARRIORS")], CANONICAL)
        p = r.pairs[0]
        assert (p.zh, p.en, p.canonical_id, p.confidence) == (
            "火战士队", "Fire Warriors", "1", "exact")
        assert r.unmatched == []

    def test_fuzzy_restricted_to_book_faction(self):
        # 同书先有精确命中 TAU → 推断书=TAU → 模糊匹配只在 TAU 内找
        ents = [_cand("火战士队", "FIRE WARRIORS"),
                _cand("风暴烈阳指挥官", "COMMANDER FARSIGHT.")]  # 结尾多个句点
        r = pair_entities(ents, CANONICAL)
        confs = {p.en: p.confidence for p in r.pairs}
        assert confs["Commander Farsight"] == "fuzzy"

    def test_no_english_name_goes_unmatched(self):
        r = pair_entities([_cand("某中文条目", None)], CANONICAL)
        assert r.pairs == []
        assert r.unmatched[0].name_zh == "某中文条目"

    def test_no_close_match_goes_unmatched(self):
        r = pair_entities([_cand("完全无关", "TOTALLY UNRELATED THING")], CANONICAL)
        assert r.unmatched != []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_pair.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'wiki_compile.pair'`

- [ ] **Step 3: Write minimal implementation**

```python
# wiki_compile/pair.py
"""流水线②：中英配对。先精确匹配，再按书多数票推断阵营、在阵营内模糊匹配。"""
from __future__ import annotations

import difflib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from wiki_compile.canonical import CanonicalEntry
from wiki_compile.extract import EntityCandidate

_PUNCT_MAP = str.maketrans({"’": "'", "‘": "'", "–": "-", "—": "-"})
FUZZY_CUTOFF = 0.85


def normalize_name(name: str) -> str:
    s = name.translate(_PUNCT_MAP).upper()
    s = re.sub(r"[^A-Z0-9' \-]", " ", s)
    return " ".join(s.split())


@dataclass
class Pair:
    zh: Optional[str]
    en: str
    canonical_id: str
    faction_id: str
    book: str
    pages: List[int]
    confidence: str  # exact / fuzzy / llm


@dataclass
class PairingResult:
    pairs: List[Pair] = field(default_factory=list)
    unmatched: List[EntityCandidate] = field(default_factory=list)


def _to_pair(e: EntityCandidate, c: CanonicalEntry, confidence: str) -> Pair:
    return Pair(zh=e.name_zh, en=c.name, canonical_id=c.id,
                faction_id=c.faction_id, book=e.book, pages=list(e.pages),
                confidence=confidence)


def pair_entities(entities: List[EntityCandidate],
                  canonical: List[CanonicalEntry]) -> PairingResult:
    by_norm: Dict[str, CanonicalEntry] = {
        normalize_name(c.name): c for c in canonical}
    result = PairingResult()
    votes: Dict[str, Counter] = {}
    leftovers: List[EntityCandidate] = []

    # 第一轮：精确匹配，同时为每本书累计阵营票
    for e in entities:
        c = by_norm.get(normalize_name(e.name_en)) if e.name_en else None
        if c is not None:
            result.pairs.append(_to_pair(e, c, "exact"))
            votes.setdefault(e.book, Counter())[c.faction_id] += 1
        else:
            leftovers.append(e)

    # 每本书的阵营 = 精确命中的多数票；模糊匹配限定在本阵营内减少误配
    book_faction = {b: v.most_common(1)[0][0] for b, v in votes.items()}
    for e in leftovers:
        if not e.name_en:
            result.unmatched.append(e)
            continue
        fid = book_faction.get(e.book)
        pool = [n for n, c in by_norm.items()
                if fid is None or c.faction_id == fid]
        hit = difflib.get_close_matches(
            normalize_name(e.name_en), pool, n=1, cutoff=FUZZY_CUTOFF)
        if hit:
            result.pairs.append(_to_pair(e, by_norm[hit[0]], "fuzzy"))
        else:
            result.unmatched.append(e)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_pair.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```powershell
git add wiki_compile\pair.py tests\test_wiki_pair.py
git commit -m "feat: 中英配对（canonical精确匹配+书级阵营推断+阵营内模糊匹配）"
```

---

### Task 5: LLM 兜底配对（pair_llm.py，带哈希缓存）

**Files:**
- Create: `wiki_compile/pair_llm.py`
- Test: `tests/test_wiki_pair.py`（追加测试类）

**Interfaces:**
- Consumes: `Pair`、`PairingResult`（Task 4）、`CanonicalEntry`（Task 3）、`EntityCandidate`（Task 2）
- Produces: `llm_pair_book(book: str, unmatched: List[EntityCandidate], candidates: List[CanonicalEntry], cache_dir: Path, client=None) -> List[Pair]`（`client` 注入便于测试；返回 confidence="llm" 的 Pair）；`run_llm_fallback(result: PairingResult, canonical: List[CanonicalEntry], cache_dir: Path) -> PairingResult`（无 `DEEPSEEK_API_KEY` 时原样返回并打印提示）。Task 6 的 CLI `pair --llm` 调用后者。

- [ ] **Step 1: Write the failing test**

追加到 `tests/test_wiki_pair.py`：

```python
import json

from wiki_compile.pair_llm import llm_pair_book


class FakeCompletion:
    def __init__(self, content):
        class _Msg:  # 模拟 openai 响应结构 choices[0].message.content
            pass
        m = _Msg(); m.content = content
        class _Choice: pass
        ch = _Choice(); ch.message = m
        self.choices = [ch]


class FakeClient:
    """记录调用次数；返回固定 JSON。"""
    def __init__(self, mapping):
        self.calls = 0
        self._content = json.dumps(
            {"配对": [{"zh": k, "en": v} for k, v in mapping.items()]},
            ensure_ascii=False)
        class _Completions:
            def __init__(self, outer): self._o = outer
            def create(self, **kw):
                self._o.calls += 1
                return FakeCompletion(self._o._content)
        class _Chat:
            def __init__(self, outer): self.completions = _Completions(outer)
        self.chat = _Chat(self)


class TestLlmPairBook:
    def test_pairs_from_llm_json(self, tmp_path):
        client = FakeClient({"死亡之雨战机": "Sun Shark Bomber"})
        pairs = llm_pair_book(
            "钛书", [_cand("死亡之雨战机", None)],
            [CanonicalEntry("9", "Sun Shark Bomber", "TAU")],
            cache_dir=tmp_path, client=client)
        assert pairs[0].en == "Sun Shark Bomber"
        assert pairs[0].confidence == "llm"

    def test_null_answer_skipped(self, tmp_path):
        client = FakeClient({"神秘单位": None})
        pairs = llm_pair_book("钛书", [_cand("神秘单位", None)],
                              [CanonicalEntry("9", "Sun Shark Bomber", "TAU")],
                              cache_dir=tmp_path, client=client)
        assert pairs == []

    def test_cache_hit_skips_second_call(self, tmp_path):
        client = FakeClient({"死亡之雨战机": "Sun Shark Bomber"})
        args = ("钛书", [_cand("死亡之雨战机", None)],
                [CanonicalEntry("9", "Sun Shark Bomber", "TAU")])
        llm_pair_book(*args, cache_dir=tmp_path, client=client)
        llm_pair_book(*args, cache_dir=tmp_path, client=client)
        assert client.calls == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_pair.py -v`
Expected: 新增测试 FAIL，`ModuleNotFoundError: No module named 'wiki_compile.pair_llm'`

- [ ] **Step 3: Write minimal implementation**

```python
# wiki_compile/pair_llm.py
"""LLM 兜底配对：确定性匹配剩下的残余交给 deepseek，按书批量、内容哈希缓存。
不 import llm_refine（其模块顶部有环境变量副作用），常量在此自定义。"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import List, Optional

from wiki_compile.canonical import CanonicalEntry
from wiki_compile.extract import EntityCandidate
from wiki_compile.pair import Pair, PairingResult

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-pro"
PROMPT_VERSION = "pair-v1"

_PROMPT = """你是战锤40K双语术语专家。以下中文条目名来自规则书《{book}》，候选英文官方名来自同阵营 datasheet 清单。
为每个中文名从候选中选出对应的英文名；不确定、或候选中不存在对应项时填 null。禁止编造候选之外的名字。
只输出 JSON，格式：{{"配对": [{{"zh": "中文名", "en": "英文名或null"}}]}}

中文条目名：
{zh_list}

候选英文名：
{en_list}
"""


def _cache_key(book: str, zh_names: List[str], en_names: List[str]) -> str:
    payload = json.dumps([PROMPT_VERSION, book, sorted(zh_names),
                          sorted(en_names)], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def llm_pair_book(book: str, unmatched: List[EntityCandidate],
                  candidates: List[CanonicalEntry], cache_dir: Path,
                  client=None) -> List[Pair]:
    todo = [e for e in unmatched if e.name_zh]
    if not todo or not candidates:
        return []
    zh_names = [e.name_zh for e in todo]
    en_names = [c.name for c in candidates]
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / (_cache_key(book, zh_names, en_names) + ".json")
    if cache_file.exists():
        answer = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        prompt = _PROMPT.format(book=book, zh_list="\n".join(zh_names),
                                en_list="\n".join(en_names))
        resp = client.chat.completions.create(
            model=MODEL, temperature=0,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"})
        answer = json.loads(resp.choices[0].message.content)
        cache_file.write_text(json.dumps(answer, ensure_ascii=False),
                              encoding="utf-8")

    by_name = {c.name: c for c in candidates}
    by_zh = {e.name_zh: e for e in todo}
    pairs: List[Pair] = []
    for item in answer.get("配对", []):
        en = item.get("en")
        e = by_zh.get(item.get("zh"))
        if not en or e is None or en not in by_name:
            continue
        c = by_name[en]
        pairs.append(Pair(zh=e.name_zh, en=c.name, canonical_id=c.id,
                          faction_id=c.faction_id, book=e.book,
                          pages=list(e.pages), confidence="llm"))
    return pairs


def run_llm_fallback(result: PairingResult, canonical: List[CanonicalEntry],
                     cache_dir: Path) -> PairingResult:
    """对每本已知阵营的书，把残余条目交给 LLM 在该阵营候选内配对。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("未设置 DEEPSEEK_API_KEY，跳过 LLM 兜底；残余留在 review_needed。")
        return result
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    votes: dict = {}
    for p in result.pairs:
        votes.setdefault(p.book, Counter())[p.faction_id] += 1
    book_faction = {b: v.most_common(1)[0][0] for b, v in votes.items()}
    paired_ids = {p.canonical_id for p in result.pairs}

    still_unmatched: List[EntityCandidate] = []
    new_pairs: List[Pair] = []
    by_book: dict = {}
    for e in result.unmatched:
        by_book.setdefault(e.book, []).append(e)
    for book, ents in by_book.items():
        fid = book_faction.get(book)
        if fid is None:
            still_unmatched.extend(ents)   # 无阵营锚（如核心规则书）→ 留人工
            continue
        candidates = [c for c in canonical
                      if c.faction_id == fid and c.id not in paired_ids]
        got = llm_pair_book(book, ents, candidates, cache_dir, client=client)
        new_pairs.extend(got)
        got_zh = {p.zh for p in got}
        still_unmatched.extend(e for e in ents if e.name_zh not in got_zh)
    return PairingResult(pairs=result.pairs + new_pairs,
                         unmatched=still_unmatched)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_pair.py -v`
Expected: 全部 passed（Task 4 的 6 个 + 本任务 3 个）

- [ ] **Step 5: Commit**

```powershell
git add wiki_compile\pair_llm.py tests\test_wiki_pair.py
git commit -m "feat: LLM 兜底配对（按书批量、阵营内候选、内容哈希缓存）"
```

---

### Task 6: 术语表产出 + CLI + 全量真实跑

**Files:**
- Create: `wiki_compile/terms.py`
- Create: `wiki_compile/__main__.py`
- Modify: `.gitignore`
- Test: `tests/test_wiki_terms.py`

**Interfaces:**
- Consumes: `PairingResult`、`Pair`（Task 4）
- Produces: `write_terms(result: PairingResult, wiki_dir: Path) -> None`（生成 `wiki_dir/terms.json`、`wiki_dir/terms.md`、`wiki_dir/review_needed.md`）；`load_term_aliases(path: Path) -> Dict[str, str]`（terms.json → `{中文名: 英文名}`，文件缺失/损坏返回 `{}`）。Task 7 的 app.py 消费 `load_term_aliases`。terms.json 结构：`{"source": "wahapedia wh40k10ed", "pairs": [{zh, en, canonical_id, faction_id, book, pages, confidence}, ...]}`。

- [ ] **Step 1: Write the failing test**

```python
# tests/test_wiki_terms.py
"""terms.json / terms.md / review_needed.md 生成与读取测试。"""
import json

from wiki_compile.extract import EntityCandidate
from wiki_compile.pair import Pair, PairingResult
from wiki_compile.terms import load_term_aliases, write_terms

RESULT = PairingResult(
    pairs=[Pair(zh="火战士队", en="Fire Warriors", canonical_id="1",
                faction_id="TAU", book="钛书", pages=[42], confidence="exact"),
           Pair(zh=None, en="Tiger Shark", canonical_id="7",
                faction_id="TAU", book="Faction Pack Tau Empire",
                pages=[13], confidence="exact")],
    unmatched=[EntityCandidate(book="钛书", raw_heading="谜之单位",
                               name_zh="谜之单位", name_en=None, pages=[99])])


class TestWriteTerms:
    def test_writes_three_files(self, tmp_path):
        write_terms(RESULT, tmp_path)
        data = json.loads((tmp_path / "terms.json").read_text(encoding="utf-8"))
        assert data["pairs"][0]["zh"] == "火战士队"
        assert "火战士队" in (tmp_path / "terms.md").read_text(encoding="utf-8")
        assert "谜之单位" in (tmp_path / "review_needed.md").read_text(encoding="utf-8")


class TestLoadTermAliases:
    def test_roundtrip(self, tmp_path):
        write_terms(RESULT, tmp_path)
        aliases = load_term_aliases(tmp_path / "terms.json")
        assert aliases == {"火战士队": "Fire Warriors"}  # zh 为 None 的不入别名

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_term_aliases(tmp_path / "nope.json") == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_wiki_terms.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'wiki_compile.terms'`

- [ ] **Step 3: Write minimal implementation**

```python
# wiki_compile/terms.py
"""双语术语表产出（P0 最终交付物）与读取。"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from wiki_compile.pair import PairingResult


def write_terms(result: PairingResult, wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    data = {"source": "wahapedia wh40k10ed",
            "pairs": [asdict(p) for p in result.pairs]}
    (wiki_dir / "terms.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 双语术语总表", "",
             "| 中文名 | 英文名 | 置信 | 来源书 | 页 |",
             "|--------|--------|------|--------|----|"]
    for p in sorted(result.pairs, key=lambda p: (p.book, p.en)):
        lines.append("| {} | {} | {} | {} | {} |".format(
            p.zh or "—", p.en, p.confidence, p.book,
            ",".join(str(n) for n in p.pages)))
    (wiki_dir / "terms.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rl = ["# 待人工校对（未配对实体）", ""]
    for e in result.unmatched:
        rl.append("- 《{}》 p{}：{}".format(
            e.book, ",".join(str(n) for n in e.pages), e.raw_heading))
    (wiki_dir / "review_needed.md").write_text("\n".join(rl) + "\n",
                                               encoding="utf-8")


def load_term_aliases(path: Path) -> Dict[str, str]:
    """terms.json → {中文名: canonical英文名}。缺失/损坏返回空表（检索层可安全降级）。"""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {p["zh"]: p["en"] for p in data.get("pairs", [])
            if p.get("zh") and p.get("en")}
```

```python
# wiki_compile/__main__.py
"""CLI：python -m wiki_compile <extract|fetch-canonical|pair|terms>"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from wiki_compile.canonical import fetch_tables, load_canonical
from wiki_compile.extract import EntityCandidate, extract_entities
from wiki_compile.pair import PairingResult, pair_entities
from wiki_compile.pair_llm import run_llm_fallback
from wiki_compile.terms import write_terms


def main() -> None:
    ap = argparse.ArgumentParser(prog="wiki_compile")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract", help="扫描 data_refined 产出实体清单")
    p.add_argument("--data", default="data_refined")
    p.add_argument("--out", default="wiki_build/entities.json")

    p = sub.add_parser("fetch-canonical", help="下载 Wahapedia CSV（需代理）")
    p.add_argument("--dest", default="db_sources/wahapedia")

    p = sub.add_parser("pair", help="中英配对")
    p.add_argument("--entities", default="wiki_build/entities.json")
    p.add_argument("--canonical", default="db_sources/wahapedia")
    p.add_argument("--out", default="wiki_build/pairing.json")
    p.add_argument("--llm", action="store_true", help="启用 LLM 兜底")

    p = sub.add_parser("terms", help="生成 wiki/terms.*")
    p.add_argument("--pairing", default="wiki_build/pairing.json")
    p.add_argument("--wiki", default="wiki")

    args = ap.parse_args()
    if args.cmd == "extract":
        ents = extract_entities(Path(args.data))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([asdict(e) for e in ents],
                                  ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print("实体数:", len(ents))
    elif args.cmd == "fetch-canonical":
        fetch_tables(Path(args.dest))
    elif args.cmd == "pair":
        raw = json.loads(Path(args.entities).read_text(encoding="utf-8"))
        ents = [EntityCandidate(**e) for e in raw]
        canonical = load_canonical(Path(args.canonical))
        result = pair_entities(ents, canonical)
        if args.llm:
            result = run_llm_fallback(result, canonical,
                                      Path("wiki_build/llm_cache"))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {"pairs": [asdict(p) for p in result.pairs],
             "unmatched": [asdict(e) for e in result.unmatched]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("配对:", len(result.pairs), "未配对:", len(result.unmatched))
    elif args.cmd == "terms":
        from wiki_compile.pair import Pair
        raw = json.loads(Path(args.pairing).read_text(encoding="utf-8"))
        result = PairingResult(
            pairs=[Pair(**p) for p in raw["pairs"]],
            unmatched=[EntityCandidate(**e) for e in raw["unmatched"]])
        write_terms(result, Path(args.wiki))
        print("已生成", args.wiki, "/terms.json terms.md review_needed.md")


if __name__ == "__main__":
    main()
```

`.gitignore` 追加两行：

```
wiki_build/
db_sources/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests\ -v`
Expected: 全部 passed（含此前所有任务的测试，回归无红）

- [ ] **Step 5: 全量真实跑（P0 验收）**

```powershell
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
.\.venv\Scripts\python.exe -m wiki_compile extract
.\.venv\Scripts\python.exe -m wiki_compile fetch-canonical   # 已下载过可跳过
$env:DEEPSEEK_API_KEY = "<你的key>"                           # 不设则跳过LLM兜底
.\.venv\Scripts\python.exe -m wiki_compile pair --llm
.\.venv\Scripts\python.exe -m wiki_compile terms
```
Expected 验收标准：
- `pair` 输出配对数应达数百以上（79 本书中单位类实体的大多数）
- 打开 `wiki/terms.md` 抽查钛帝国 10 行：中英对应与 PDF 一致
- `wiki/review_needed.md` 里主要是核心规则概念与非单位条目（正常，P1 处理），若出现明显该配上的单位名，记录问题但不阻塞
- 若 Wahapedia 列名或格式与假设不符已在 Task 3 Step 5 修正

- [ ] **Step 6: Commit（产物一并提交）**

```powershell
git add wiki_compile tests\test_wiki_terms.py .gitignore wiki\terms.md wiki\terms.json wiki\review_needed.md
git commit -m "feat: P0 双语术语表流水线（extract→pair→terms）与首版 wiki/terms"
```

---

### Task 7: 接入 app.py 查询扩展 + 文档更新

**Files:**
- Modify: `app.py`（UNIT_ALIASES 区块之后、`expand_query` 函数，约 92-117 行）
- Modify: `CLAUDE.md`（运行方式小节）

**Interfaces:**
- Consumes: `wiki_compile.terms.load_term_aliases(path: Path) -> Dict[str, str]`（Task 6）
- Produces: app.py 模块级 `TERM_ALIASES: Dict[str, str]`；`expand_query(query: str) -> str` 行为扩展（命中术语表中文名时追加英文 canonical 名）。无下游任务。

- [ ] **Step 1: 修改 app.py**

在 `UNIT_ALIASES` 的 jieba 注册循环（`for _k, _v in UNIT_ALIASES.items(): ...`）之后追加：

```python
# ══════════════════════════════════════════════
#  wiki/terms.json：P0 双语术语表 → 查询扩展
#  中文单位名命中时追加英文 canonical 名，让 BM25/向量能召回英文 Faction Pack 页
# ══════════════════════════════════════════════
from wiki_compile.terms import load_term_aliases

TERM_ALIASES = load_term_aliases(Path(__file__).parent / "wiki" / "terms.json")
for _zh in TERM_ALIASES:
    jieba.add_word(_zh)
```

注意：确认 app.py 顶部已有 `from pathlib import Path`，没有则补。

把 `expand_query` 改为（原函数在约 112-117 行）：

```python
def expand_query(query: str) -> str:
    """查询扩展：命中社区译名/术语表时，追加库内译名与英文名（保留原词）。"""
    extras = [v for k, v in UNIT_ALIASES.items() if k in query]
    extras += [v for k, v in TERM_ALIASES.items() if k in query]
    if not extras:
        return query
    return query + "（" + "，".join(dict.fromkeys(extras)) + "）"
```

- [ ] **Step 2: 冒烟验证（不启动 Streamlit，直接验证纯函数）**

```powershell
.\.venv\Scripts\python.exe -c "from wiki_compile.terms import load_term_aliases; from pathlib import Path; a = load_term_aliases(Path('wiki/terms.json')); print(len(a)); q = '火战士队的脉冲步枪射程'; extras = [v for k, v in a.items() if k in q]; print(extras)"
```
Expected: 打印术语条数（数百）和 `['Fire Warriors']`。
再验证 app 可正常 import（会加载模型，较慢属正常）：
```powershell
.\.venv\Scripts\python.exe -c "import app; print(app.expand_query('火战士队怎么打'))"
```
Expected: 输出包含"Fire Warriors"的扩展查询，无异常。

- [ ] **Step 3: 更新 CLAUDE.md 运行方式**

在 CLAUDE.md「运行方式」代码块内追加：

```powershell
.\.venv\Scripts\python.exe -m wiki_compile extract          # 扫描实体清单
.\.venv\Scripts\python.exe -m wiki_compile fetch-canonical  # 下载 Wahapedia CSV（需代理）
.\.venv\Scripts\python.exe -m wiki_compile pair --llm       # 中英配对（LLM兜底需 DEEPSEEK_API_KEY）
.\.venv\Scripts\python.exe -m wiki_compile terms            # 生成 wiki/terms.*
```

- [ ] **Step 4: Run all tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\ -v`
Expected: 全部 passed（app.py 改动不影响既有测试）

- [ ] **Step 5: Commit**

```powershell
git add app.py CLAUDE.md
git commit -m "feat: 检索查询扩展接入 wiki/terms 双语术语表"
```

---

## Self-Review 记录

1. **Spec 覆盖**：spec 流水线①（extract_entities）→ Task 1/2；②（pair_entities，canonical 锚定）→ Task 3/4/5；terms.md 产出与"接入 UNIT_ALIASES 逻辑"→ Task 6/7。P0 范围内无缺口（terms.md 手动校对入口 = review_needed.md）。
2. **占位符扫描**：无 TBD/TODO；所有代码步骤含完整代码。
3. **类型一致性**：`EntityCandidate`/`CanonicalEntry`/`Pair`/`PairingResult` 字段名在 Task 2-7 间一致；`load_term_aliases` 在 Task 6 定义、Task 7 消费，签名一致。
4. **已知风险**：Wahapedia CSV 实际列名可能与假设不同 → Task 3 Step 5 安排了核对修正点；中文标题格式仍可能有未见形态 → Task 2 Step 5 冒烟安排了补 NOISE_SUFFIXES 的回路。
