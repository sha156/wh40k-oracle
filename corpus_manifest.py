"""语料层级清单：书名 → edition/layer 元数据（11 版迁移 S1）。

分层语义（docs/superpowers/plans/2026-07-10-edition-11-migration.md §4）：
  rules      —— 现行版本核心规则（规则问题唯一真源）
  overlay    —— Faction Pack（分队/数据表补丁/FAQ，覆盖 codex-base）
  points     —— 现行点数（MFM）
  balance    —— 平衡副本
  event      —— 组织赛文档
  reference  —— 版本弱相关参考（地形尺寸等）
  codex-base —— 十版 codex 兵牌基底（11 版官方仍合法，被 overlay 修补）

清单文件：仓库根 corpus_manifest.json（data/ 不入库，manifest 必须可追踪）。
未列出的书回退 defaults（codex-base / 10）——这是 codex 的设计行为而非错误；
新增**非 codex** 文档入库时应显式补进 manifest，ingest 会按层打印汇总供核对。
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict

_BUILTIN_DEFAULTS = {"edition": "10", "layer": "codex-base"}
SOURCE_METADATA_FIELDS = ("status", "scope", "effective_date")


def _source_metadata(entry: dict) -> dict:
    """Validate optional retrieval declarations without certifying rule bodies.

    Missing fields retain legacy behavior. Scope is a reviewed, nonempty label;
    it is not the structured per-unit source_coverage contract.
    """
    result = {key: entry[key] for key in SOURCE_METADATA_FIELDS if key in entry}
    if "status" in result and result["status"] not in (
        "current", "carry_forward", "historical",
    ):
        raise ValueError("Unknown corpus source status")
    if "scope" in result and (
        not isinstance(result["scope"], str) or not result["scope"].strip()
        or len(result["scope"]) > 500
    ):
        raise ValueError("Corpus source scope must be a nonempty label (up to 500 characters)")
    value = result.get("effective_date")
    if value is not None:
        if not isinstance(value, str):
            raise ValueError("Corpus effective_date must be YYYY-MM-DD or null")
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError()
        except ValueError:
            raise ValueError("Corpus effective_date must be a valid YYYY-MM-DD date") from None
    if result.get("status") == "historical" and not value:
        raise ValueError("Historical corpus sources require an explicit effective_date")
    return result


def load_manifest(path: Path) -> dict:
    """读清单；文件缺失/损坏时回退内置 defaults 并显式告警（不静默）。"""
    if not path.exists():
        print(f"[corpus_manifest] ⚠️ 清单文件不存在: {path}，全部书目将回退 "
              f"{_BUILTIN_DEFAULTS}（edition/layer 元数据不可信）")
        return {"defaults": dict(_BUILTIN_DEFAULTS), "books": {}, "prefixes": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"[corpus_manifest] ⚠️ 清单文件解析失败: {e}，回退内置 defaults")
        return {"defaults": dict(_BUILTIN_DEFAULTS), "books": {}, "prefixes": []}
    data.setdefault("defaults", dict(_BUILTIN_DEFAULTS))
    data.setdefault("books", {})
    data.setdefault("prefixes", [])
    return data


LAYER_LABELS_ZH = {
    "rules": "核心规则",
    "overlay": "阵营补丁",
    "points": "点数",
    "balance": "平衡副本",
    "event": "组织赛",
    "reference": "参考",
    "codex-base": "codex兵牌基底",
}


def edition_layer_tag(edition: str, layer: str) -> str:
    """展示标签：'11版·核心规则'、'十版·codex兵牌基底'。未知层原样透出不吞。"""
    ed = "十版" if str(edition) == "10" else "{}版".format(edition)
    return "{}·{}".format(ed, LAYER_LABELS_ZH.get(layer, layer))


def classify_book_with_origin(book_name: str, manifest: dict):
    """同 `classify_book`，另返回分类**来源**：`"exact"` / `"prefix"` / `"defaults"`。

    `"defaults"` 不等于分错——`data/` 下 27 本未登记 PDF 逐本核对全是真十版 codex，
    defaults 对它们是**正确**的（0 例误分类）。要报的不是分类结果，而是「这本书的层级
    没人拍板过」这个事实（审查 R2-M3）：ingest 的分层汇总是按层聚合的
    （`layer_stats["10版/codex-base"] += n`），未登记书目与显式登记成 codex-base 的书
    在汇总里**完全不可区分**——那份汇总不是这条风险的探测器。

    后果的具体形状：新增一本 11 版规则类 PDF 而忘了登记，会静默拿到 layer=codex-base，
    于是**不被 app.py 的规则层保底选中**（保底按 `layer=rules` 过滤），而没有任何一处会吼。
    """
    entry = manifest["books"].get(book_name)
    origin = "exact"
    if entry is None:
        origin = "prefix"
        for rule in manifest["prefixes"]:
            if book_name.startswith(rule.get("prefix", "\x00")):
                entry = rule
                break
    if entry is None:
        origin = "defaults"
        entry = manifest["defaults"]
    source = _source_metadata(entry)
    if source.get("status") == "historical" and origin != "exact":
        raise ValueError("Historical exclusions must be declared by exact book name")
    return ({"edition": str(entry.get("edition", _BUILTIN_DEFAULTS["edition"])),
             "layer": str(entry.get("layer", _BUILTIN_DEFAULTS["layer"])),
             **source}, origin)


def resolve_book_metadata(metadata: dict, manifest: dict) -> dict:
    """Resolve stored tags with reviewed exact overrides, without mutating docs.

    Exact declarations apply even when an old index already has edition/layer.
    Prefix/default tags only fill missing fields; old codex age alone never
    makes a source historical. Optional source fields remain absent by default.
    """
    declared, origin = classify_book_with_origin(metadata.get("book", ""), manifest)
    stored = _source_metadata(metadata)
    tags = {key: metadata.get(key) or declared[key] for key in ("edition", "layer")}
    if origin == "exact":
        tags.update(declared)
        stored.update({key: declared[key] for key in SOURCE_METADATA_FIELDS if key in declared})
    else:
        stored = {**{key: declared[key] for key in SOURCE_METADATA_FIELDS if key in declared}, **stored}
    tags.update(_source_metadata(stored))
    return tags


def classify_book(book_name: str, manifest: dict) -> Dict[str, str]:
    """书名 → {"edition": ..., "layer": ...}。精确名优先，其次前缀规则，最后 defaults。

    要同时知道分类是不是靠 defaults 兜底的，用 `classify_book_with_origin`。
    """
    return classify_book_with_origin(book_name, manifest)[0]
