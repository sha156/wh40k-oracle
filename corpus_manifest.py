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
from pathlib import Path
from typing import Dict

_BUILTIN_DEFAULTS = {"edition": "10", "layer": "codex-base"}


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


def classify_book(book_name: str, manifest: dict) -> Dict[str, str]:
    """书名 → {"edition": ..., "layer": ...}。精确名优先，其次前缀规则，最后 defaults。"""
    entry = manifest["books"].get(book_name)
    if entry is None:
        for rule in manifest["prefixes"]:
            if book_name.startswith(rule.get("prefix", "\x00")):
                entry = rule
                break
    if entry is None:
        entry = manifest["defaults"]
    return {"edition": str(entry.get("edition", _BUILTIN_DEFAULTS["edition"])),
            "layer": str(entry.get("layer", _BUILTIN_DEFAULTS["layer"]))}
