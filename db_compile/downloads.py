"""downloads：官方下载页版本监控（三源链最后一块——rules PDF 版本变化提醒）。

用户拍板的数据权威层级里，官方 warhammer-community 下载页与 MFM 并列最高真源。
本模块盯官方每个游戏系统的下载分类页（如 /downloads/warhammer-40000/），把「现在挂着
哪些 PDF、各自文件名是什么」抓成清单（manifest），下次再抓时 diff，报出：
新增文档 / 版本更替 / 文档下架。

**版本信号 = 文件名哈希**：GW 的资产是内容寻址、不可变的
（`Cache-Control: immutable`，文件名带哈希后缀，如 `..._core_rules-was6fbu1ix-hfewhmxyiy.pdf`）。
一份文档更新时 GW **换新文件名**发布、分类页指向新链接，旧链接仍长期 200。
所以「HEAD 一个固定 URL」只能抓到删除（403），抓不到改版——必须重读分类页比文件名。

**为什么要渲染**：分类页是 Next.js 客户端渲染，PDF 链接不在服务端 HTML 里
（urllib/curl 抓到的原始 HTML 里 0 个 .pdf），必须跑 JS 才能拿到。渲染用 scrapling
（需 Python 3.11），本项目 venv 是 3.9，故渲染这一步 shell out 到独立 3.11 解释器；
HEAD 补元数据 + diff 全部纯 3.9 stdlib。缺 3.11/scrapling 时优雅降级（告警跳过）。
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ASSET_HOST = "https://assets.warhammer-community.com/"
CAT_URL = "https://www.warhammer-community.com/en-gb/downloads/{slug}/"
DEFAULT_CATEGORIES = ("warhammer-40000",)

# 独立 3.11 解释器（装了 scrapling）——全局 CLAUDE.md 记录的本机路径，可被环境变量覆盖。
DEFAULT_PY311 = (r"C:\Users\Administrator\AppData\Local\Programs"
                 r"\Python\Python311\python.exe")
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 传给 3.11 的渲染脚本：scrapling 无头渲染分类页 → 输出 [{title, url}] 的 JSON。
# 只依赖 scrapling + stdlib，保持自包含（用 -c 传入，不落临时文件）。
_RENDER_SRC = r"""
import json, sys
from scrapling.fetchers import StealthyFetcher
url = sys.argv[1]
page = StealthyFetcher.fetch(url, headless=True, network_idle=True, timeout=90000)
seen, out = set(), []
for a in page.css("a"):
    href = a.attrib.get("href", "") or ""
    if ".pdf" not in href.lower():
        continue
    if href in seen:
        continue
    seen.add(href)
    out.append({"title": (a.text or "").strip(), "url": href})
print("__WH40K_JSON__" + json.dumps({"status": page.status, "items": out}))
"""


def resolve_py311() -> str:
    return os.environ.get("SCRAPLING_PYTHON", DEFAULT_PY311)


@dataclass
class DocEntry:
    title: str
    filename: str            # 版本信号：资产文件名（带哈希后缀）
    url: str
    last_modified: Optional[str] = None
    size: Optional[int] = None
    etag: Optional[str] = None


@dataclass
class CategoryDiff:
    slug: str
    added: List[DocEntry] = field(default_factory=list)     # 新文档
    changed: List[Tuple[str, str, str]] = field(default_factory=list)  # (title, 旧文件名, 新文件名)
    removed: List[str] = field(default_factory=list)        # 下架文档标题
    unchanged: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.changed or self.removed)


def _filename_of(url: str) -> str:
    return url.rstrip("/").split("/")[-1].split("?")[0]


def render_category(slug: str, py311: Optional[str] = None,
                    timeout: int = 150) -> List[DocEntry]:
    """shell out 到 3.11+scrapling 渲染分类页，返回 [DocEntry]（未含 HEAD 元数据）。

    抛 RuntimeError（附清晰原因）当：解释器不存在 / scrapling 缺失 / 渲染无输出。
    """
    py = py311 or resolve_py311()
    if not Path(py).exists():
        raise RuntimeError(
            f"渲染需要 Python 3.11+scrapling，未找到解释器 {py}；"
            f"可设环境变量 SCRAPLING_PYTHON 指向正确路径")
    url = CAT_URL.format(slug=slug)
    try:
        proc = subprocess.run([py, "-c", _RENDER_SRC, url],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"渲染 {slug} 超时（{timeout}s）") from e
    marker = "__WH40K_JSON__"
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith(marker)), None)
    if line is None:
        tail = (proc.stderr or proc.stdout)[-300:]
        if "No module named 'scrapling'" in (proc.stderr or ""):
            raise RuntimeError(f"{py} 未安装 scrapling")
        raise RuntimeError(f"渲染 {slug} 无有效输出：{tail}")
    payload = json.loads(line[len(marker):])
    items = payload.get("items") or []
    if not items:
        # 渲染跑通但 0 个 PDF 链接：官方页不可能一份文档都没有，几乎必是
        # 反爬拦截/页面结构变化。不能返回空列表——否则 diff_category 会把
        # 旧 manifest 全部误判为「下架」。抛错走既有优雅降级路径。
        raise RuntimeError(
            f"渲染 {slug} 成功但结果为空（status={payload.get('status')}）——"
            f"疑似被反爬拦截或页面结构已变，不视为全部下架")
    return [DocEntry(title=it["title"] or _filename_of(it["url"]),
                     filename=_filename_of(it["url"]), url=it["url"])
            for it in items]


def head_meta(url: str, timeout: int = 20) -> Dict[str, Optional[str]]:
    """HEAD 一个资产 URL → {last_modified, size, etag, status}。失败不抛，回缺省。"""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # 走环境代理
            return {"status": resp.status,
                    "last_modified": resp.headers.get("Last-Modified"),
                    "size": int(resp.headers["Content-Length"])
                    if resp.headers.get("Content-Length") else None,
                    "etag": (resp.headers.get("ETag") or "").strip('"') or None}
    except Exception as e:  # 网络/403：记状态，交由上层判断
        code = getattr(e, "code", None)
        return {"status": code, "last_modified": None, "size": None, "etag": None}


def harvest(categories=DEFAULT_CATEGORIES, py311: Optional[str] = None,
            enrich: bool = True) -> Dict:
    """渲染各分类页 + HEAD 补元数据 → manifest dict。enrich=False 跳过 HEAD（快，仅文件名）。

    HEAD 单个失败不中断（元数据字段留空），但结束时聚合披露失败总数——不静默漏。
    """
    cats: Dict[str, Dict] = {}
    head_failed = 0
    for slug in categories:
        entries = render_category(slug, py311)
        docs: Dict[str, Dict] = {}
        for e in entries:
            if enrich:
                meta = head_meta(e.url)
                if meta.get("status") != 200:
                    head_failed += 1
                e.last_modified, e.size, e.etag = (
                    meta["last_modified"], meta["size"], meta["etag"])
            docs[e.title] = {"filename": e.filename, "url": e.url,
                             "last_modified": e.last_modified,
                             "size": e.size, "etag": e.etag}
        cats[slug] = docs
    if head_failed:
        print(f"  ⚠️ {head_failed} 个文档 HEAD 元数据抓取失败"
              f"（manifest 相应字段为空，文件名 diff 不受影响）", flush=True)
    return {"source": "warhammer-community/downloads",
            "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
            "categories": cats}


def diff_category(slug: str, old: Dict[str, Dict],
                  new: List[DocEntry]) -> CategoryDiff:
    """比对某分类的旧 manifest 段 vs 新渲染结果（按标题配对，文件名判改版）。纯函数。"""
    d = CategoryDiff(slug=slug)
    new_by_title = {e.title: e for e in new}
    for title, e in new_by_title.items():
        prev = old.get(title)
        if prev is None:
            d.added.append(e)
        elif prev.get("filename") != e.filename:
            d.changed.append((title, prev.get("filename", "?"), e.filename))
        else:
            d.unchanged += 1
    for title in old:
        if title not in new_by_title:
            d.removed.append(title)
    return d


def check(manifest_path, categories=DEFAULT_CATEGORIES,
          py311: Optional[str] = None) -> Dict:
    """重渲染各分类页，与存量 manifest diff。返回 {diffs:[CategoryDiff], no_baseline}。

    无存量 manifest 时视为首次建基线（全部记为 added），提示先 harvest。
    """
    mpath = Path(manifest_path)
    baseline = (json.loads(mpath.read_text(encoding="utf-8")).get("categories", {})
                if mpath.exists() else {})
    diffs: List[CategoryDiff] = []
    for slug in categories:
        new = render_category(slug, py311)
        diffs.append(diff_category(slug, baseline.get(slug, {}), new))
    return {"diffs": diffs, "no_baseline": not mpath.exists()}


def write_manifest(manifest: Dict, manifest_path) -> None:
    mpath = Path(manifest_path)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                     encoding="utf-8")


def summarize(rep: Dict) -> Dict[str, int]:
    """check 报告 → 计数汇总 {added, changed, removed, unchanged}。"""
    diffs = rep["diffs"]
    return {"added": sum(len(d.added) for d in diffs),
            "changed": sum(len(d.changed) for d in diffs),
            "removed": sum(len(d.removed) for d in diffs),
            "unchanged": sum(d.unchanged for d in diffs)}


def print_diffs(rep: Dict) -> None:
    """把 check 报告打成人读清单。"""
    if rep.get("no_baseline"):
        print("无基线 manifest——先跑 `downloads --harvest` 建基线，之后 --check 才有对照")
        return
    total = summarize(rep)
    if not any(total[k] for k in ("added", "changed", "removed")):
        print(f"官方下载页无变化（{total['unchanged']} 文档全部对齐）✅")
        return
    for d in rep["diffs"]:
        if not d.has_changes:
            continue
        print(f"[{d.slug}]")
        for e in d.added:
            print(f"  🆕 新增：{e.title}  ({e.filename})")
        for title, old_f, new_f in d.changed:
            print(f"  🔄 改版：{title}\n        {old_f}\n     →  {new_f}")
        for title in d.removed:
            print(f"  ❌ 下架：{title}")
    print(f"\n合计 新增 {total['added']} / 改版 {total['changed']} / "
          f"下架 {total['removed']} / 未变 {total['unchanged']}")
    print("确认后跑 `downloads --harvest` 刷新基线（否则每次 --check 仍会报这些变化）")
