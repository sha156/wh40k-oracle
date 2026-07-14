"""fp_rules：Faction Pack 规则**文本**级真漂移外科补丁层（P7-PR1）。

与 fp_errata（兵牌数值层）同族、同守卫哲学，但对象是规则正文：
`detachments.rule_text` / `stratagems.text_zh` / `abilities.text_zh`（列名带 _zh
是历史遗留，实存 Wahapedia 英文 HTML）。

**为什么需要这层**：P7 要把阵营规则逐条译成 Effect DSL，而 DSL 必须对着 11 版现行
文本编码。逐行 A/B 核对（2026-07-14 工作单）发现库是混合态——Wahapedia 已滚入部分
6 月 Faction Pack 勘误（如 For the Greater Good 已逐字 11 版），但另一部分仍是十版
旧文（如 Auxiliary Cadre 分队规则整段旧版、Photon Grenades 的 When 段）。所以与
fp_errata 同理**不做整表覆盖**，只补 A/B 坐实的真漂移条目。

**防误覆盖守卫**（三态，与 fp_errata 一致）：每条补丁带落账时的库现文本 `from_text`。
apply 前归一化比对：库现值==to 幂等跳过；==from 才应用；两者都不是（上游改过）→
跳过并告警让路。将来 Wahapedia 自己滚入这些勘误时，本层自动让路而非制造冲突。

**name_zh 补齐**（附带职责）：detachments/stratagems 的 name_zh 全 NULL，从十版中文
codex refine 缓存配对 + FP 新增条目自译（标 zh_source）。守卫：现值为空才写，已有
不同值让路告警——中文名一旦被上游/人工改过就不盲覆盖。

build 重建整库会清掉本层，须在 build 之后重跑（挂 update._RESTORE_STAGES，
排在 fp_errata 之后）。只改结构表文本列，不动检索层。CLI：`python -m db_compile fp-rules`。
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, List

# 允许打文本补丁的 (表, 列) 白名单——表/列名会拼进 SQL，白名单外一律拒绝
_TEXT_TARGETS = {
    ("detachments", "rule_text"),
    ("stratagems", "text_zh"),
    ("abilities", "text_zh"),
}
# 允许补 name_zh 的表白名单
_NAME_TABLES = {"detachments", "stratagems", "abilities"}

_TAG_RE = re.compile(r"<[^>]+>")


def _norm_text(v) -> str:
    """守卫用归一化：去 HTML 标签、统一弯撇号/弯引号、压平空白。

    目的：同一段规则文本在 Wahapedia HTML 与 refine 缓存 Markdown 里的
    非语义差异（标签、’ vs '、换行）不该触发假漂移/假让路；语义措辞差异
    （declared a charge vs selected its charge target）必须保留区分。
    """
    if v is None:
        return ""
    s = _TAG_RE.sub("", str(v))
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("‑", "-"), ("–", "-"), ("—", "-")):
        s = s.replace(a, b)
    return " ".join(s.split()).strip().lower()


def load_patches(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _slim(p: dict) -> dict:
    return {"table": p.get("table"), "id": p.get("id"), "name": p.get("name_en")}


def _apply_text_patches(conn, patches: List[dict], report: Dict) -> None:
    for p in patches:
        table, column, pid = p.get("table"), p.get("column"), p.get("id")
        if (table, column) not in _TEXT_TARGETS or not pid:
            report["text_invalid"].append(_slim(p))
            continue
        row = conn.execute(
            f"SELECT {column} FROM {table} WHERE id = ?", (pid,)).fetchone()
        if row is None:
            report["text_skipped"].append({**_slim(p), "reason": "行不存在"})
            continue
        cur = row[0]
        gc, gf, gt = _norm_text(cur), _norm_text(p.get("from_text")), _norm_text(p.get("to_text"))
        if gc == gt:
            report["text_already"] += 1            # 幂等：已是 11 版文本
            continue
        if gc != gf:
            # 库现文本既非 from 也非 to：上游动过，让路不盲覆盖
            report["text_mismatch"].append(
                {**_slim(p), "db_now_head": str(cur)[:120]})
            continue
        conn.execute(
            f"UPDATE {table} SET {column} = ? WHERE id = ?", (p["to_text"], pid))
        report["text_applied"] += 1
        report["text_changes"].append(
            {**_slim(p), "fp_source": p.get("fp_source"),
             "synthesis": p.get("synthesis")})


def _apply_name_patches(conn, patches: List[dict], report: Dict) -> None:
    for p in patches:
        table, pid, name_zh = p.get("table"), p.get("id"), p.get("name_zh")
        if table not in _NAME_TABLES or not pid or not name_zh:
            report["name_invalid"].append(_slim(p))
            continue
        row = conn.execute(
            f"SELECT name_zh FROM {table} WHERE id = ?", (pid,)).fetchone()
        if row is None:
            report["name_skipped"].append({**_slim(p), "reason": "行不存在"})
            continue
        cur = (row[0] or "").strip()
        if cur == name_zh.strip():
            report["name_already"] += 1
            continue
        if cur:
            # 已有不同中文名（上游/人工改过）：让路告警
            report["name_mismatch"].append({**_slim(p), "db_now": cur})
            continue
        conn.execute(
            f"UPDATE {table} SET name_zh = ? WHERE id = ?", (name_zh, pid))
        report["name_applied"] += 1
        report["name_changes"].append(
            {**_slim(p), "name_zh": name_zh, "zh_source": p.get("zh_source")})


def apply_fp_rules(db_path, patches: dict) -> Dict:
    """应用 fp_rules 文本/中文名补丁到库，返回结构化报告（含逐条改动与告警）。"""
    report = {
        "text_applied": 0, "text_already": 0,
        "text_changes": [], "text_mismatch": [], "text_skipped": [], "text_invalid": [],
        "name_applied": 0, "name_already": 0,
        "name_changes": [], "name_mismatch": [], "name_skipped": [], "name_invalid": [],
    }
    conn = sqlite3.connect(str(db_path))
    try:
        _apply_text_patches(conn, patches.get("text_patches", []), report)
        _apply_name_patches(conn, patches.get("name_patches", []), report)
        conn.commit()
    finally:
        conn.close()
    return report


def apply_from_file(db_path, patches_path) -> Dict:
    return apply_fp_rules(db_path, load_patches(patches_path))
