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
    ("detachments", "name_en"),         # P7-PR6：完整重印可换分队规则名（BT 祷文升格）
    ("stratagems", "text_zh"),
    ("stratagems", "cp_cost"),          # P7-PR7：完整重印可换 CP（EC 凤凰王庭两战略互换）
    ("abilities", "text_zh"),
    ("enhancements", "description"),    # P7-PR4：FP p3/p4 重印 + p19 勘误波及增强层
}
# 允许补 name_zh 的表白名单（enhancements 无 name_zh 列，不进此单）
_NAME_TABLES = {"detachments", "stratagems", "abilities"}
# 允许打失效标记的表白名单（deactivations：FP 完整重印裁定 11 版已删除的行）；
# 值 = 该表的名字列（enhancements 的名字列是 name，不是 name_en）
_DEACTIVATE_TABLES = {"stratagems": "name_en", "enhancements": "name"}
_DEACTIVATE_STATUSES = {"removed_11e"}
# 允许补录插行的表白名单（inserts：FP 有、Wahapedia/DB 无的 fp_new 条目，
# 如 Advanced Acquisition Cadre 整分队；列名拼进 SQL，白名单外一律拒绝）
_INSERT_COLUMNS = {
    "detachments": ("id", "faction", "name_zh", "name_en", "rule_text"),
    "stratagems": ("id", "faction", "detachment", "name_zh", "name_en",
                   "cp_cost", "phase", "text_zh"),
    "enhancements": ("id", "faction_id", "detachment_id", "detachment_name",
                     "name", "cost", "legend", "description"),
}
# 插行同名去重的（表 → 名字列 + 分组列）——上游（Wahapedia）将来自己补录同名条目时，
# synthetic 行必须让路告警而不是留双胞胎
_INSERT_NAME_COLS = {
    "detachments": ("name_en", "faction"),
    "stratagems": ("name_en", "detachment"),
    "enhancements": ("name", "detachment_name"),
}

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


def _ensure_fp_status_column(conn, table: str) -> None:
    """旧库（建表早于 fp_status 入 DDL）补列；新库 DDL 自带，幂等。"""
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if "fp_status" not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN fp_status TEXT")


def _apply_deactivations(conn, patches: List[dict], report: Dict) -> None:
    """失效标记（2026-07-16 裁定：FP 完整重印即整体替换，未收录的旧条目 11 版已删除）。

    守卫：①表/状态值白名单外拒绝；②行不存在跳过；③name_en 不匹配让路告警
    （防 id 被上游复用指到别的条目）；④已是目标状态幂等。原文不动，只置标记。
    """
    for p in patches:
        table, pid, status = p.get("table"), p.get("id"), p.get("status")
        if table not in _DEACTIVATE_TABLES or not pid or status not in _DEACTIVATE_STATUSES:
            report["deact_invalid"].append(_slim(p))
            continue
        _ensure_fp_status_column(conn, table)
        name_col = _DEACTIVATE_TABLES[table]
        row = conn.execute(
            f"SELECT {name_col}, fp_status FROM {table} WHERE id = ?", (pid,)).fetchone()
        if row is None:
            report["deact_skipped"].append({**_slim(p), "reason": "行不存在"})
            continue
        db_name, cur_status = row
        if _norm_text(db_name) != _norm_text(p.get("name_en")):
            report["deact_mismatch"].append({**_slim(p), "db_name": db_name})
            continue
        if cur_status == status:
            report["deact_already"] += 1
            continue
        conn.execute(
            f"UPDATE {table} SET fp_status = ? WHERE id = ?", (status, pid))
        report["deact_applied"] += 1
        report["deact_changes"].append(
            {**_slim(p), "status": status, "fp_source": p.get("fp_source")})


def _apply_inserts(conn, patches: List[dict], report: Dict) -> None:
    """fp_new 补录插行（P7-PR4）：FP 有、Wahapedia/DB 无的整条目（AAC 分队等）。

    守卫：①表白名单外/缺 id/缺名字拒绝；②同 id 已存在——名字匹配则幂等跳过、
    不匹配让路告警（防 id 撞车）；③**同名异 id 已存在**（上游将来自己补录）→
    让路告警不插，synthetic 行绝不与上游行留双胞胎；④stratagems/enhancements
    插入行标 fp_status='added_11e' 便于溯源与将来退役。
    """
    for p in patches:
        table = p.get("table")
        cols = _INSERT_COLUMNS.get(table)
        values = p.get("values") or {}
        name_col, group_col = _INSERT_NAME_COLS.get(table, (None, None))
        pid = values.get("id")
        slim = {"table": table, "id": pid,
                "name": values.get(name_col) if name_col else None}
        if cols is None or not pid or not values.get(name_col):
            report["ins_invalid"].append(slim)
            continue
        extra = set(values) - set(cols)
        if extra:
            report["ins_invalid"].append(
                {**slim, "reason": f"白名单外的列 {sorted(extra)}"})
            continue
        row = conn.execute(
            f"SELECT {name_col} FROM {table} WHERE id = ?", (pid,)).fetchone()
        if row is not None:
            if _norm_text(row[0]) == _norm_text(values.get(name_col)):
                report["ins_already"] += 1
            else:
                report["ins_mismatch"].append(
                    {**slim, "reason": "id 已存在但名字不符（疑 id 撞车）",
                     "db_name": row[0]})
            continue
        dup = conn.execute(
            f"SELECT id FROM {table} WHERE {name_col} = ? COLLATE NOCASE "
            f"AND COALESCE({group_col}, '') = ?",
            (values.get(name_col), values.get(group_col) or "")).fetchone()
        if dup is not None:
            report["ins_mismatch"].append(
                {**slim, "reason": f"同名行已存在（id={dup[0]}，疑上游已补录），"
                                   f"synthetic 插入让路", "db_id": dup[0]})
            continue
        use_cols = [c for c in cols if c in values]
        placeholders = ", ".join("?" for _ in use_cols)
        conn.execute(
            f"INSERT INTO {table} ({', '.join(use_cols)}) VALUES ({placeholders})",
            tuple(values[c] for c in use_cols))
        if table in ("stratagems", "enhancements"):
            _ensure_fp_status_column(conn, table)
            conn.execute(
                f"UPDATE {table} SET fp_status = 'added_11e' WHERE id = ?", (pid,))
        report["ins_applied"] += 1
        report["ins_changes"].append({**slim, "fp_source": p.get("fp_source")})


def apply_fp_rules(db_path, patches: dict) -> Dict:
    """应用 fp_rules 文本/中文名/失效标记/补录插行补丁到库，返回结构化报告。"""
    report = {
        "text_applied": 0, "text_already": 0,
        "text_changes": [], "text_mismatch": [], "text_skipped": [], "text_invalid": [],
        "name_applied": 0, "name_already": 0,
        "name_changes": [], "name_mismatch": [], "name_skipped": [], "name_invalid": [],
        "deact_applied": 0, "deact_already": 0,
        "deact_changes": [], "deact_mismatch": [], "deact_skipped": [], "deact_invalid": [],
        "ins_applied": 0, "ins_already": 0,
        "ins_changes": [], "ins_mismatch": [], "ins_invalid": [],
    }
    conn = sqlite3.connect(str(db_path))
    try:
        # inserts 先于 text/deact：同一批补丁里对补录行的文本/失效引用应立即可见
        _apply_inserts(conn, patches.get("inserts", []), report)
        _apply_text_patches(conn, patches.get("text_patches", []), report)
        _apply_name_patches(conn, patches.get("name_patches", []), report)
        _apply_deactivations(conn, patches.get("deactivations", []), report)
        conn.commit()
    finally:
        conn.close()
    return report


def apply_from_file(db_path, patches_path) -> Dict:
    return apply_fp_rules(db_path, load_patches(patches_path))
