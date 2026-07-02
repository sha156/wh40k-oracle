# LLM PDF 重构实现计划（llm_refine + 结构化分块 + 钛帝国试点）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 deepseek-chat 将 PDF 规则书逐页重构为结构化 Markdown（一个单位/条目 = 一个 `##` 块），并让 ingest 按条目分块入库，解决兵牌表格被拍扁导致的检索不准。

**Architecture:** 新增离线脚本 `llm_refine.py`（提取→LLM 重排→页级哈希缓存到 `data_refined/<书名>/`），新增轻量模块 `md_chunker.py`（按 `##` 标题分块），`ingest.py` 优先读重构结果、否则回退现有流程。检索链路不动。

**Tech Stack:** Python 3.9（项目 .venv）、PyMuPDF (fitz)、openai SDK 1.x（deepseek 兼容接口）、pytest、langchain_core.documents。

## Global Constraints

- 一律使用项目 venv：`D:\Project\py\RAG\.venv\Scripts\python.exe`（Python 3.9.1，**禁止 `X | Y` 联合类型语法**，用 `Optional[X]`；`list[X]`/`dict[K,V]` 内置泛型可用）
- LLM：`deepseek-chat`，base_url `https://api.deepseek.com`，API key 从环境变量 `DEEPSEEK_API_KEY` 读取，缺失即报错退出，不落盘
- 缓存目录：`data_refined/<pdf文件名去掉.pdf>/page_NNN.md` + `page_NNN.meta.json`（NNN 三位零填充，页号 1-based）
- meta.json 字段固定：`sha256`（页原始文本哈希）、`prompt_version`、`model`、`verify_ok`、`fallback`
- 数值防篡改为**警告**不阻断；LLM 输出禁止改写数值/增删内容/翻译
- 测试命令统一：`.\.venv\Scripts\python.exe -m pytest tests/ -v`（PowerShell）
- 提交信息遵循 `<type>: <描述>` 约定式格式，无归属尾注

---

### Task 1: 环境准备 + 页面提取 `extract_pages`

**Files:**
- Modify: `requirements.txt`（追加 pytest）
- Create: `tests/__init__.py`（空文件）
- Create: `tests/conftest.py`
- Create: `tests/test_llm_refine.py`
- Create: `llm_refine.py`

**Interfaces:**
- Produces: `extract_pages(pdf_path: Path) -> list` — 每元素为 `{"page": int(1-based), "text": str, "sha256": str}`；后续所有任务依赖此结构。

- [ ] **Step 1: 安装 pytest 并登记依赖**

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
Add-Content -Path requirements.txt -Value "pytest" -Encoding utf8
```

- [ ] **Step 2: 写测试夹具与失败测试**

`tests/__init__.py`：空文件。

`tests/conftest.py`：

```python
from pathlib import Path

import fitz
import pytest


def make_pdf(path: Path, texts) -> Path:
    """生成简单多页 PDF，每页一段 ASCII 文本（fitz 默认字体不含中文）。"""
    doc = fitz.open()
    for t in texts:
        page = doc.new_page()
        page.insert_text((72, 72), t)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def tiny_pdf(tmp_path):
    return make_pdf(
        tmp_path / "book.pdf",
        ["UNIT ALPHA M 6 T 4 SV 3+ W 5", "WEAPON TABLE Range 24 A 2 BS 3+"],
    )
```

`tests/test_llm_refine.py`：

```python
from pathlib import Path

from llm_refine import extract_pages


def test_extract_pages_returns_text_and_hash(tiny_pdf):
    pages = extract_pages(tiny_pdf)
    assert [p["page"] for p in pages] == [1, 2]
    assert "UNIT ALPHA" in pages[0]["text"]
    assert "WEAPON TABLE" in pages[1]["text"]
    assert len(pages[0]["sha256"]) == 64
    assert pages[0]["sha256"] != pages[1]["sha256"]
```

- [ ] **Step 3: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v`
Expected: FAIL（`No module named 'llm_refine'`）

- [ ] **Step 4: 实现 `llm_refine.py` 骨架 + `extract_pages`**

```python
"""
llm_refine.py — 用 LLM 将 PDF 页文本重构为结构化 Markdown
==========================================================
用法：
  python llm_refine.py --book 钛帝国十版CODEX-20251112   # 按文件名子串匹配单本
  python llm_refine.py --all                              # 全量
需要环境变量 DEEPSEEK_API_KEY。结果缓存于 data_refined/<书名>/page_NNN.md，
按页文本哈希 + prompt 版本增量，可断点续跑。
"""
import hashlib
from pathlib import Path
from typing import List

import fitz

MIN_TEXT_CHARS = 20


def extract_pages(pdf_path: Path) -> List[dict]:
    """逐页提取文本，附 1-based 页号与 SHA-256。"""
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append({
            "page": i + 1,
            "text": text,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    doc.close()
    return pages
```

- [ ] **Step 5: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```powershell
git add requirements.txt tests/ llm_refine.py
git commit -m "feat: llm_refine 页面提取与测试基建"
```

---

### Task 2: 页级缓存（save/is_cached）

**Files:**
- Modify: `llm_refine.py`
- Modify: `tests/test_llm_refine.py`

**Interfaces:**
- Consumes: Task 1 的页 dict 结构。
- Produces:
  - `page_paths(book_dir: Path, page_no: int) -> Tuple[Path, Path]`（md路径, meta路径）
  - `save_page(book_dir: Path, page_no: int, markdown: str, meta: dict) -> None`
  - `is_cached(book_dir: Path, page_no: int, sha256: str, prompt_version: str) -> bool`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_llm_refine.py`：

```python
from llm_refine import is_cached, page_paths, save_page


def _meta(sha, ver="v1", fallback=False):
    return {"sha256": sha, "prompt_version": ver, "model": "deepseek-chat",
            "verify_ok": True, "fallback": fallback}


def test_cache_roundtrip(tmp_path):
    save_page(tmp_path, 3, "## 单位A\n内容", _meta("abc"))
    md_path, meta_path = page_paths(tmp_path, 3)
    assert md_path.name == "page_003.md"
    assert meta_path.name == "page_003.meta.json"
    assert md_path.read_text(encoding="utf-8") == "## 单位A\n内容"
    assert is_cached(tmp_path, 3, "abc", "v1")


def test_cache_invalidated_by_sha_or_prompt_or_fallback(tmp_path):
    save_page(tmp_path, 1, "x", _meta("abc"))
    assert not is_cached(tmp_path, 1, "CHANGED", "v1")   # 页内容变了
    assert not is_cached(tmp_path, 1, "abc", "v2")       # prompt 升级了
    save_page(tmp_path, 2, "raw", _meta("abc", fallback=True))
    assert not is_cached(tmp_path, 2, "abc", "v1")       # 兜底页需重试
    assert not is_cached(tmp_path, 9, "abc", "v1")       # 不存在
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v -k cache`
Expected: FAIL（ImportError: cannot import name 'is_cached'）

- [ ] **Step 3: 实现缓存函数**

追加到 `llm_refine.py`（顶部补 `import json` 与 `from typing import List, Tuple`）：

```python
def page_paths(book_dir: Path, page_no: int) -> Tuple[Path, Path]:
    stem = "page_{:03d}".format(page_no)
    return book_dir / (stem + ".md"), book_dir / (stem + ".meta.json")


def save_page(book_dir: Path, page_no: int, markdown: str, meta: dict) -> None:
    book_dir.mkdir(parents=True, exist_ok=True)
    md_path, meta_path = page_paths(book_dir, page_no)
    md_path.write_text(markdown, encoding="utf-8")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding="utf-8")


def is_cached(book_dir: Path, page_no: int, sha256: str, prompt_version: str) -> bool:
    md_path, meta_path = page_paths(book_dir, page_no)
    if not (md_path.exists() and meta_path.exists()):
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return (meta.get("sha256") == sha256
            and meta.get("prompt_version") == prompt_version
            and not meta.get("fallback", False))
```

- [ ] **Step 4: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```powershell
git add llm_refine.py tests/test_llm_refine.py
git commit -m "feat: llm_refine 页级缓存与失效判定"
```

---

### Task 3: 数值防篡改校验 `verify_numbers`

**Files:**
- Modify: `llm_refine.py`
- Modify: `tests/test_llm_refine.py`

**Interfaces:**
- Produces: `verify_numbers(source: str, markdown: str) -> List[str]` — 返回生成文本中"多出来"的数字 token（多重集合超出原文的部分），空列表 = 通过。

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_llm_refine.py`：

```python
from llm_refine import verify_numbers


def test_verify_numbers_pass_when_subset():
    src = "箭弹发射器 18” 5 2+ 3 0 1"
    md = "| 箭弹发射器 | 18” | 5 | 2+ | 3 | 0 | 1 |"
    assert verify_numbers(src, md) == []


def test_verify_numbers_flags_invented_tokens():
    src = "M 10 T 4"
    md = "| M | T |\n| 10 | 7 |"          # 7 是原文没有的
    assert verify_numbers(src, md) == ["7"]


def test_verify_numbers_flags_excess_count():
    src = "W 5"
    md = "5 5 5"                            # 5 出现次数超过原文
    assert verify_numbers(src, md) == ["5"]
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v -k verify`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现**

追加到 `llm_refine.py`（顶部补 `import re` 与 `from collections import Counter`）：

```python
def verify_numbers(source: str, markdown: str) -> List[str]:
    """校验生成 Markdown 的数字多重集合 ⊆ 原文，返回超出的 token。"""
    src_counts = Counter(re.findall(r"\d+", source))
    bad = []
    for tok, cnt in Counter(re.findall(r"\d+", markdown)).items():
        if cnt > src_counts.get(tok, 0):
            bad.append(tok)
    return sorted(bad)
```

- [ ] **Step 4: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```powershell
git add llm_refine.py tests/test_llm_refine.py
git commit -m "feat: 数值防篡改校验 verify_numbers"
```

---

### Task 4: 领域 Prompt + 单页 LLM 调用 `refine_page`（带重试）

**Files:**
- Create: `refine_prompt.py`
- Modify: `llm_refine.py`
- Modify: `tests/test_llm_refine.py`

**Interfaces:**
- Produces:
  - `refine_prompt.PROMPT_VERSION: str`（当前 `"v1"`；改 prompt 必须升版本号使缓存失效）
  - `refine_prompt.SYSTEM_PROMPT: str`
  - `refine_prompt.build_user_prompt(page_text: str, prev_tail: str) -> str`
  - `llm_refine.refine_page(client, page_text: str, prev_tail: str) -> str`（client 为 openai.OpenAI 兼容对象；内部重试 3 次、剥除代码围栏；全部失败抛 RuntimeError）

- [ ] **Step 1: 创建 `refine_prompt.py`（完整内容）**

```python
"""refine_prompt.py — 战锤40K规则书重构 Prompt（领域 schema）
改动本文件的任何输出要求后，必须递增 PROMPT_VERSION，使页缓存失效重跑。
"""

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """你是战锤40K规则书的排版修复助手。输入是从 PDF 单页提取的纯文本，\
表格结构在提取时被压成了一维文字流。你的任务是【只恢复结构，绝不改动内容】，输出 Markdown。

## 输出规则（必须严格遵守）
1. 兵牌（单位数据卡）输出为：
   ## <单位名>（若原文附英文名则写成 ## 单位名 ENGLISH NAME）
   | M | T | SV | W | LD | OC |
   |---|---|----|---|----|----|
   |...|...|... |...|... |... |
   ### 远程武器
   | 武器名称 | 射程 | A | BS | S | AP | D |
   |---|---|---|---|---|---|---|
   ### 近战武器
   | 武器名称 | 射程 | A | WS | S | AP | D |
   |---|---|---|---|---|---|---|
   ### 技能
   （核心/阵营/单位技能、装备能力、特殊保护等，用 **技能名**：描述 的列表）
   ### 单位构成
   （构成、装备选项、分数）
   **关键词**：...
   **阵营关键词**：...
   武器自带的技能（如[热熔2]、[手枪]）保留在武器名称栏内。
2. 战略技能输出为：
   ## <技能名>（CP消耗）
   | 技能来源 | 技能分类 | 使用时机 | 使用对象 | 效果 |
   的两行表格，或逐项 **字段**：值 列表（字段较长时）。
3. 强化升级、分队规则等其他条目：## <条目名> 开头，内部用表格或列表恢复结构。
4. 普通规则说明文字：输出干净的 Markdown，恢复标题层级（章节用 ##），段落合并断行。
5. 如果本页开头明显是上一页某条目的延续（没有新标题），第一行输出 <!--CONT-->，\
然后直接输出延续内容，不要虚构标题。
6. 页眉、页脚、页码、水印（如"老湿腐战锤群 52110733"）一律丢弃。

## 禁止事项
- 禁止改写、换算、增删任何数值（"2+"就是"2+"，"D6"就是"D6"）
- 禁止增删、翻译、改写任何名词和规则文字
- 禁止添加原文没有的内容或你自己的解释
- 禁止输出 Markdown 之外的说明文字

直接输出 Markdown 正文，不要用 ``` 代码块包裹。"""


def build_user_prompt(page_text: str, prev_tail: str) -> str:
    parts = []
    if prev_tail:
        parts.append("【上一页结尾（仅供判断延续关系，不要重复输出）】\n" + prev_tail)
    parts.append("【本页原始文本】\n" + page_text)
    return "\n\n".join(parts)
```

- [ ] **Step 2: 写失败测试（假 client，不发真请求）**

追加到 `tests/test_llm_refine.py`：

```python
import pytest

from llm_refine import refine_page


class _FakeChoice:
    def __init__(self, content):
        class _Msg:
            pass
        self.message = _Msg()
        self.message.content = content


class _FakeClient:
    """openai.OpenAI 形状的假客户端：按脚本依次返回/抛错。"""
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

        class _Completions:
            def create(_self, **kwargs):
                self.calls += 1
                item = self._script.pop(0)
                if isinstance(item, Exception):
                    raise item

                class _Resp:
                    choices = [_FakeChoice(item)]
                return _Resp()

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def test_refine_page_returns_content():
    client = _FakeClient(["## 单位A\n| M |"])
    assert refine_page(client, "原文", "") == "## 单位A\n| M |"


def test_refine_page_strips_code_fence():
    client = _FakeClient(["```markdown\n## 单位A\n```"])
    assert refine_page(client, "原文", "") == "## 单位A"


def test_refine_page_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("llm_refine.time.sleep", lambda s: None)
    client = _FakeClient([RuntimeError("boom"), "## OK"])
    assert refine_page(client, "原文", "") == "## OK"
    assert client.calls == 2


def test_refine_page_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr("llm_refine.time.sleep", lambda s: None)
    client = _FakeClient([RuntimeError("a"), RuntimeError("b"), RuntimeError("c")])
    with pytest.raises(RuntimeError):
        refine_page(client, "原文", "")
```

- [ ] **Step 3: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v -k refine_page`
Expected: FAIL（ImportError: cannot import name 'refine_page'）

- [ ] **Step 4: 实现 `refine_page`**

追加到 `llm_refine.py`（顶部补 `import time`，以及 `from refine_prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt`）：

```python
MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"
MAX_RETRIES = 3


def _strip_code_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*\n", "", content)
        content = re.sub(r"\n```\s*$", "", content)
    return content.strip()


def refine_page(client, page_text: str, prev_tail: str) -> str:
    """调用 LLM 重构单页文本，重试 MAX_RETRIES 次，指数退避。"""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(page_text, prev_tail)},
                ],
                temperature=0.0,
                max_tokens=4096,
            )
            content = _strip_code_fence(resp.choices[0].message.content or "")
            if content:
                return content
            raise ValueError("LLM 返回空内容")
        except Exception as e:  # noqa: BLE001 — 网络/限流/空响应统一重试
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError("LLM 处理失败（重试{}次）: {}".format(MAX_RETRIES, last_err))
```

- [ ] **Step 5: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v`
Expected: PASS (10 passed)

- [ ] **Step 6: Commit**

```powershell
git add refine_prompt.py llm_refine.py tests/test_llm_refine.py
git commit -m "feat: 战锤领域 prompt 与单页 LLM 重构（重试+围栏剥除）"
```

---

### Task 5: 整本编排 `process_book` + CLI

**Files:**
- Modify: `llm_refine.py`
- Modify: `tests/test_llm_refine.py`

**Interfaces:**
- Consumes: `extract_pages`、`is_cached`、`save_page`、`refine_page`、`verify_numbers`、`PROMPT_VERSION`。
- Produces:
  - `process_book(client, pdf_path: Path, out_root: Path, workers: int = 4) -> dict`，返回 summary：`{"book","total","done","cached","skipped","failed","verify_warn"}`
  - CLI：`--book <子串>` / `--all` / `--workers` / `--data-dir` / `--out-dir`
  - 无文本页清单写入 `data_refined/<书名>/skipped_pages.json`

- [ ] **Step 1: 写失败测试（monkeypatch 掉 refine_page，不发真请求）**

追加到 `tests/test_llm_refine.py`：

```python
import json as _json

import llm_refine
from llm_refine import process_book


def test_process_book_writes_pages_and_summary(tmp_path, tiny_pdf, monkeypatch):
    monkeypatch.setattr(llm_refine, "refine_page",
                        lambda client, text, tail: "## E\n" + text.strip())
    summary = process_book(client=None, pdf_path=tiny_pdf, out_root=tmp_path)
    assert summary["total"] == 2
    assert summary["done"] == 2
    assert summary["failed"] == 0
    book_dir = tmp_path / "book"
    assert (book_dir / "page_001.md").exists()
    meta = _json.loads((book_dir / "page_001.meta.json").read_text(encoding="utf-8"))
    assert meta["fallback"] is False and meta["verify_ok"] is True


def test_process_book_uses_cache_on_second_run(tmp_path, tiny_pdf, monkeypatch):
    monkeypatch.setattr(llm_refine, "refine_page",
                        lambda client, text, tail: "## E\nok " + text.strip())
    process_book(client=None, pdf_path=tiny_pdf, out_root=tmp_path)
    calls = []
    monkeypatch.setattr(llm_refine, "refine_page",
                        lambda client, text, tail: calls.append(1) or "## X")
    summary = process_book(client=None, pdf_path=tiny_pdf, out_root=tmp_path)
    assert summary["cached"] == 2 and calls == []


def test_process_book_fallback_on_llm_failure(tmp_path, tiny_pdf, monkeypatch):
    def boom(client, text, tail):
        raise RuntimeError("LLM down")
    monkeypatch.setattr(llm_refine, "refine_page", boom)
    summary = process_book(client=None, pdf_path=tiny_pdf, out_root=tmp_path)
    assert summary["failed"] == 2
    md = (tmp_path / "book" / "page_001.md").read_text(encoding="utf-8")
    assert "UNIT ALPHA" in md            # 兜底写入原始文本
    meta = _json.loads((tmp_path / "book" / "page_001.meta.json")
                       .read_text(encoding="utf-8"))
    assert meta["fallback"] is True
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_llm_refine.py -v -k process_book`
Expected: FAIL（ImportError: cannot import name 'process_book'）

- [ ] **Step 3: 实现 `process_book` + `main`**

追加到 `llm_refine.py`（顶部补：`import argparse, os, sys`、`from concurrent.futures import ThreadPoolExecutor, as_completed`、`from tqdm import tqdm`）：

```python
PREV_TAIL_CHARS = 500
DATA_DIR = Path("data")
OUT_DIR = Path("data_refined")


def process_book(client, pdf_path: Path, out_root: Path, workers: int = 4) -> dict:
    """整本处理：提取→过滤→并发 LLM→缓存落盘。返回统计 summary。"""
    pages = extract_pages(pdf_path)
    book_dir = out_root / pdf_path.stem
    book_dir.mkdir(parents=True, exist_ok=True)
    summary = {"book": pdf_path.name, "total": len(pages), "done": 0,
               "cached": 0, "skipped": 0, "failed": 0, "verify_warn": 0}

    raw_by_no = {p["page"]: p["text"] for p in pages}
    jobs, skipped_pages = [], []
    for p in pages:
        if len(p["text"].strip()) < MIN_TEXT_CHARS:
            summary["skipped"] += 1
            skipped_pages.append(p["page"])
        elif is_cached(book_dir, p["page"], p["sha256"], PROMPT_VERSION):
            summary["cached"] += 1
        else:
            jobs.append(p)

    if skipped_pages:
        (book_dir / "skipped_pages.json").write_text(
            json.dumps(skipped_pages), encoding="utf-8")

    def _work(p):
        prev_tail = raw_by_no.get(p["page"] - 1, "")[-PREV_TAIL_CHARS:]
        # 通过模块属性调用，保证测试可 monkeypatch
        md = globals()["refine_page"](client, p["text"], prev_tail)
        bad = verify_numbers(p["text"], md)
        save_page(book_dir, p["page"], md, {
            "sha256": p["sha256"], "prompt_version": PROMPT_VERSION,
            "model": MODEL, "verify_ok": not bad, "fallback": False,
        })
        return p["page"], bad

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_work, p): p for p in jobs}
        for fut in tqdm(as_completed(futures), total=len(futures),
                        desc=pdf_path.stem[:24], unit="页"):
            p = futures[fut]
            try:
                page_no, bad = fut.result()
                summary["done"] += 1
                if bad:
                    summary["verify_warn"] += 1
                    tqdm.write("  数字校验警告 第{}页：出现原文没有的数字 {}".format(page_no, bad))
            except Exception as e:  # noqa: BLE001 — 单页失败兜底，不中断整本
                summary["failed"] += 1
                tqdm.write("  第{}页失败，写入原始文本兜底: {}".format(p["page"], e))
                save_page(book_dir, p["page"], p["text"], {
                    "sha256": p["sha256"], "prompt_version": PROMPT_VERSION,
                    "model": MODEL, "verify_ok": True, "fallback": True,
                })
    return summary


def main():
    parser = argparse.ArgumentParser(description="LLM 重构 PDF 为结构化 Markdown")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--book", type=str, help="按文件名子串匹配单本 PDF")
    group.add_argument("--all", action="store_true", help="处理 data 目录全部 PDF")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--data-dir", type=str, default=str(DATA_DIR))
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误：未设置环境变量 DEEPSEEK_API_KEY")
        sys.exit(1)

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    pdfs = sorted(Path(args.data_dir).glob("*.pdf"))
    if args.book:
        pdfs = [p for p in pdfs if args.book in p.stem]
        if not pdfs:
            print("错误：没有文件名包含「{}」的 PDF".format(args.book))
            sys.exit(1)

    out_root = Path(args.out_dir)
    for pdf in pdfs:
        summary = process_book(client, pdf, out_root, workers=args.workers)
        print("完成 {book}: 新处理{done} 缓存{cached} 跳过{skipped} "
              "失败{failed} 数字警告{verify_warn} / 共{total}页".format(**summary))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行全部测试确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```powershell
git add llm_refine.py tests/test_llm_refine.py
git commit -m "feat: 整本并发编排 process_book 与 CLI（缓存/兜底/统计）"
```

---

### Task 6: Markdown 条目分块 `md_chunker.py`

**Files:**
- Create: `md_chunker.py`
- Create: `tests/test_md_chunker.py`

**Interfaces:**
- Produces:
  - `chunk_markdown(pages: List[Tuple[int, str]], base_meta: dict, max_chunk_chars: int = 2000) -> List[Document]` — pages 为 (页号, 该页Markdown)，跨页条目自动合并；每个 chunk 的 metadata 含 base_meta 全部字段 + `unit`（`##` 标题文本）+ `page`（标题所在页）。
  - `load_refined_book(pdf_path: Path, refined_root: Path, base_meta: dict) -> Optional[List[Document]]` — 无重构目录返回 None（Task 7 使用）。

- [ ] **Step 1: 写失败测试**

`tests/test_md_chunker.py`：

```python
from pathlib import Path

from md_chunker import chunk_markdown, load_refined_book

BASE = {"source": "data/x.pdf", "book": "测试书"}


def test_splits_by_h2_and_tracks_unit_and_page():
    pages = [
        (1, "## 单位A\n| M | T |\n| 6 | 4 |"),
        (2, "## 单位B\n内容B"),
    ]
    chunks = chunk_markdown(pages, BASE)
    assert len(chunks) == 2
    assert chunks[0].metadata["unit"] == "单位A"
    assert chunks[0].metadata["page"] == 1
    assert chunks[1].metadata["unit"] == "单位B"
    assert chunks[1].metadata["page"] == 2
    assert chunks[0].metadata["book"] == "测试书"
    assert "| 6 | 4 |" in chunks[0].page_content


def test_cross_page_entry_merges_and_cont_marker_stripped():
    pages = [
        (1, "## 单位A\n第一页内容"),
        (2, "<!--CONT-->\n第二页延续内容"),
    ]
    chunks = chunk_markdown(pages, BASE)
    assert len(chunks) == 1
    assert "第一页内容" in chunks[0].page_content
    assert "第二页延续内容" in chunks[0].page_content
    assert "<!--CONT-->" not in chunks[0].page_content


def test_preamble_before_first_h2_becomes_own_chunk():
    pages = [(1, "# 书名\n前言文字"), (1, "## 单位A\n内容")]
    chunks = chunk_markdown(pages, BASE)
    assert len(chunks) == 2
    assert chunks[0].metadata["unit"] == "书名"
    assert "前言文字" in chunks[0].page_content


def test_oversize_entry_splits_at_h3_and_repeats_heading():
    body = "## 大单位\n| M |\n### 远程武器\n" + ("x" * 1500) \
           + "\n### 技能\n" + ("y" * 1500)
    chunks = chunk_markdown([(1, body)], BASE, max_chunk_chars=1000)
    assert len(chunks) >= 2
    assert all(c.metadata["unit"] == "大单位" for c in chunks)
    assert chunks[0].page_content.startswith("## 大单位")
    assert chunks[1].page_content.startswith("## 大单位（续）")


def test_load_refined_book_reads_pages_in_order(tmp_path):
    book_dir = tmp_path / "mybook"
    book_dir.mkdir()
    (book_dir / "page_001.md").write_text("## 单位A\n甲", encoding="utf-8")
    (book_dir / "page_002.md").write_text("## 单位B\n乙", encoding="utf-8")
    chunks = load_refined_book(Path("data/mybook.pdf"), tmp_path, BASE)
    assert [c.metadata["unit"] for c in chunks] == ["单位A", "单位B"]
    assert [c.metadata["page"] for c in chunks] == [1, 2]


def test_load_refined_book_returns_none_when_missing(tmp_path):
    assert load_refined_book(Path("data/nothere.pdf"), tmp_path, BASE) is None
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_md_chunker.py -v`
Expected: FAIL（No module named 'md_chunker'）

- [ ] **Step 3: 实现 `md_chunker.py`（完整文件）**

```python
"""
md_chunker.py — 将 LLM 重构后的 Markdown 按条目（## 标题）分块
一个单位/战略技能/升级 = 一个完整 chunk，跨页条目自动合并。
仅依赖 langchain_core，保持可独立测试。
"""
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_core.documents import Document

CONT_MARKER = "<!--CONT-->"


def _split_oversize(heading: str, body_lines: List[str],
                    max_chunk_chars: int) -> List[str]:
    """超长条目按 ### 边界二次切分，后续段落标题加（续）。"""
    text = "\n".join(body_lines)
    if len(text) <= max_chunk_chars or "\n### " not in "\n" + text:
        return ["## {}\n{}".format(heading, text) if text else "## " + heading]

    segments, current = [], []
    for line in body_lines:
        if line.startswith("### ") and current:
            segments.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        segments.append("\n".join(current))

    parts, buf = [], ""
    for seg in segments:
        if buf and len(buf) + len(seg) > max_chunk_chars:
            parts.append(buf)
            buf = seg
        else:
            buf = buf + "\n" + seg if buf else seg
    if buf:
        parts.append(buf)

    out = []
    for i, part in enumerate(parts):
        prefix = "## {}\n" if i == 0 else "## {}（续）\n"
        out.append(prefix.format(heading) + part)
    return out


def chunk_markdown(pages: List[Tuple[int, str]], base_meta: dict,
                   max_chunk_chars: int = 2000) -> List[Document]:
    """按 ## 标题切分为条目 chunk；返回带 unit/page 元数据的 Document 列表。"""
    entries = []          # (heading, page_no, body_lines)
    heading, heading_page, body = None, None, []

    def _flush():
        if heading is None and not any(l.strip() for l in body):
            return
        entries.append((heading, heading_page, list(body)))

    for page_no, md_text in pages:
        for line in md_text.splitlines():
            if line.strip() == CONT_MARKER:
                continue
            if line.startswith("## "):
                _flush()
                heading, heading_page, body = line[3:].strip(), page_no, []
            else:
                if heading is None and heading_page is None:
                    heading_page = page_no
                body.append(line)
    _flush()

    docs = []
    for h, pg, body_lines in entries:
        if h is None:
            # 前言：取首个 "# " 一级标题作条目名
            h = "前言"
            for line in body_lines:
                if line.startswith("# "):
                    h = line[2:].strip()
                    break
        for text in _split_oversize(h, body_lines, max_chunk_chars):
            meta = dict(base_meta)
            meta["unit"] = h
            meta["page"] = pg
            docs.append(Document(page_content=text.strip(), metadata=meta))
    return docs


def load_refined_book(pdf_path: Path, refined_root: Path,
                      base_meta: dict) -> Optional[List[Document]]:
    """读取 data_refined/<书名>/page_*.md 并分块；目录不存在或为空返回 None。"""
    book_dir = refined_root / pdf_path.stem
    md_files = sorted(book_dir.glob("page_*.md"))
    if not md_files:
        return None
    pages = [(int(f.stem.split("_")[1]), f.read_text(encoding="utf-8"))
             for f in md_files]
    return chunk_markdown(pages, base_meta)
```

注意实现细节：`chunk_markdown` 中前言块的 heading 处理——`_flush` 里 heading 为 None 时 entries 仍带 None，由后处理赋名"前言"或首个 `# ` 标题。**前言块的 page 取其首行所在页**（代码中 `heading is None and heading_page is None` 分支负责记录）。

- [ ] **Step 4: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_md_chunker.py -v`
Expected: PASS (6 passed)。若 `test_preamble_before_first_h2_becomes_own_chunk` 或标题（续）断言失败，按测试为准修实现，测试即规格。

- [ ] **Step 5: 全量回归**

Run: `.\.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS (19 passed)

- [ ] **Step 6: Commit**

```powershell
git add md_chunker.py tests/test_md_chunker.py
git commit -m "feat: Markdown 条目分块器（按##切分/跨页合并/超长二切）"
```

---

### Task 7: ingest.py 接入重构结果

**Files:**
- Modify: `ingest.py`（约 56-61 行 import 区、约 266-294 行主循环）

**Interfaces:**
- Consumes: `md_chunker.load_refined_book(pdf_path, refined_root, base_meta)`。
- Produces: ingest 行为变更——有 `data_refined/<书名>/` 时用条目分块，否则回退原语义分块；增量日志值格式变为 `"<pdf_mtime>|<refined_fingerprint>"`。

- [ ] **Step 1: 修改 import 与常量**

在 `ingest.py` 的 `from hf_embeddings_compat import ...`（61 行）之后追加：

```python
from md_chunker import load_refined_book
```

在配置区 `PROCESSED_LOG = ...`（68 行）之后追加：

```python
REFINED_DIR = Path("data_refined")   # llm_refine.py 输出目录，存在则优先使用
```

- [ ] **Step 2: 增加指纹函数**

在 `get_book_name`（109-119 行）之后追加：

```python
def refined_fingerprint(pdf_path: Path) -> str:
    """重构目录指纹：所有 page_*.md 的 (文件名, mtime) 哈希；无目录返回 'none'。"""
    book_dir = REFINED_DIR / pdf_path.stem
    md_files = sorted(book_dir.glob("*.md"))
    if not md_files:
        return "none"
    import hashlib
    h = hashlib.sha256()
    for f in md_files:
        h.update("{}:{}".format(f.name, os.path.getmtime(f)).encode("utf-8"))
    return h.hexdigest()[:16]
```

- [ ] **Step 3: 修改增量判断（约 248-255 行）**

把主循环里的：

```python
    for pdf in pdf_files:
        mtime = str(os.path.getmtime(pdf))
        if processed_log.get(str(pdf)) == mtime:
```

改为：

```python
    for pdf in pdf_files:
        mtime = "{}|{}".format(os.path.getmtime(pdf), refined_fingerprint(pdf))
        if processed_log.get(str(pdf)) == mtime:
```

同时把该循环之后处理成功时的记录（约 290 行）`processed_log[str(pdf_path)] = str(os.path.getmtime(pdf_path))` 改为：

```python
            processed_log[str(pdf_path)] = "{}|{}".format(
                os.path.getmtime(pdf_path), refined_fingerprint(pdf_path))
```

- [ ] **Step 4: 主循环接入条目分块（约 275-287 行）**

把 try 块内：

```python
            pages = load_pdf(pdf_path)
            pages = [p for p in pages if len(p.page_content.strip()) > 20]

            if not pages:
                tqdm.write(f"  ⚠️  {pdf_path.name}: 无可提取文本（扫描版），已跳过")
                failed_files.append((pdf_path.name, "无文本层"))
                continue

            tqdm.write(f"  📄 {pdf_path.name}: {len(pages)} 页")

            chunks = semantic_chunk(pages, embeddings)
            tqdm.write(f"  ✂️  分块完成: {len(chunks)} chunks  ({time.time()-t0:.1f}s)")
```

改为：

```python
            base_meta = {"source": str(pdf_path), "book": get_book_name(pdf_path)}
            refined = load_refined_book(pdf_path, REFINED_DIR, base_meta)

            if refined is not None:
                chunks = refined
                tqdm.write(f"  🧩 {pdf_path.name}: 使用 LLM 重构结果，"
                           f"{len(chunks)} 个条目 chunk")
            else:
                pages = load_pdf(pdf_path)
                pages = [p for p in pages if len(p.page_content.strip()) > 20]

                if not pages:
                    tqdm.write(f"  ⚠️  {pdf_path.name}: 无可提取文本（扫描版），已跳过")
                    failed_files.append((pdf_path.name, "无文本层"))
                    continue

                tqdm.write(f"  📄 {pdf_path.name}: {len(pages)} 页")
                chunks = semantic_chunk(pages, embeddings)
                tqdm.write(f"  ✂️  分块完成: {len(chunks)} chunks  ({time.time()-t0:.1f}s)")
```

- [ ] **Step 5: 冒烟验证（不跑真嵌入）**

Run: `.\.venv\Scripts\python.exe -c "import ast; ast.parse(open('ingest.py', encoding='utf-8').read()); print('语法 OK')"`
Expected: `语法 OK`

Run: `.\.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS（19 passed，确认无回归）

- [ ] **Step 6: Commit**

```powershell
git add ingest.py
git commit -m "feat: ingest 优先使用 LLM 重构结果并按条目分块"
```

---

### Task 8: 钛帝国试点（需要用户提供 DEEPSEEK_API_KEY）

**Files:**
- 产出: `data_refined/钛帝国十版CODEX-20251112/page_*.md`（78 页）

**Interfaces:**
- Consumes: Task 5 CLI、Task 7 ingest 改造。

- [ ] **Step 1: 确认 API key**

```powershell
if ($env:DEEPSEEK_API_KEY) { "key 已设置" } else { "缺少 DEEPSEEK_API_KEY，向用户索要" }
```

缺失则暂停，请用户执行 `$env:DEEPSEEK_API_KEY = "sk-..."` 后继续。

- [ ] **Step 2: 跑单本重构**

```powershell
.\.venv\Scripts\python.exe llm_refine.py --book "钛帝国十版CODEX-20251112" --workers 4
```

Expected: 进度条走完，输出形如 `完成 钛帝国十版CODEX-20251112.pdf: 新处理77 缓存0 跳过1 失败0 数字警告≤5 / 共78页`。失败数 >5 或警告 >15 则停下检查 prompt。

- [ ] **Step 3: 自动抽查**

```powershell
.\.venv\Scripts\python.exe -c "
from pathlib import Path
import random
files = sorted(Path('data_refined/钛帝国十版CODEX-20251112').glob('page_*.md'))
print('总页数:', len(files))
for f in random.sample(files, 3):
    print('='*30, f.name, '='*30)
    print(f.read_text(encoding='utf-8')[:1200])
"
```

检查点：兵牌页有 `## 单位名` + `| M | T | SV | W | LD | OC |` 属性表 + 武器表；水印"老湿腐战锤群"已被丢弃。第 17 页（影阳指挥官）必查：属性 M10"/T4/SV3+/W6/LD6+/OC1，武器表数值与会话早期提取的原文一致。

- [ ] **Step 4: 用户人工抽查（检查点，暂停等确认）**

请用户对照原 PDF 抽查 ≥5 个兵牌页的 Markdown。不满意 → 改 `refine_prompt.py`（升 PROMPT_VERSION）重跑本书。满意 → 继续。

- [ ] **Step 5: 提交重构结果**

```powershell
git add data_refined/
git commit -m "feat: 钛帝国 codex LLM 重构结果（试点）"
```

- [ ] **Step 6: 重建索引并验证问答**

```powershell
.\.venv\Scripts\python.exe ingest.py --rebuild
```

说明：--rebuild 全量重嵌入（CPU 需较长时间，可挂机）；仅钛帝国走条目分块，其余书回退语义分块，行为不变。完成后启动 `.\run_streamlit.ps1`，用 ~10 个已知答案问题（影阳指挥官的 T/W、高能融合炮的 S/AP/D、某战略技能 CP 消耗等）验证，与旧索引的历史回答对比。

- [ ] **Step 7: 试点结论**

记录准确率对比到 `docs/superpowers/specs/2026-07-02-llm-pdf-refine-design.md` 末尾（新增"试点结果"小节），提交。通过 → 后续迭代跑全量 49 本 + 旧版归档 + VLM 兜底。
