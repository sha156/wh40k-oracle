"""dsl_apply：把 `dsl_payloads/*.json`（P7 DSL 唯一真源）投影进 DB 的
`effect_dsl_json` + `dsl_status` 列。

**为什么必须有这层**（评审 F1，CRITICAL）：build 重建对 abilities/stratagems 用
INSERT OR REPLACE 且不含 DSL 列——只写 DB 的 DSL 会在下一次 `--rebuild` 被静默清零。
真源落 git 文件、DB 只是投影、挂 restore 链补回（排 fp_rules 之后：DSL 指纹要对着
11 版化后的文本核）。

**指纹守卫**（评审 F12）：每条带 effects 的载荷有 provenance.text_sha256（录入时对
DB 现行文本取 sha256(fp_rules._norm_text(text))）。apply 前重算比对——不匹配说明
原文被后续刷新而 DSL 未重核，让路告警不写，绝不把过期编码投影上去。

校验复用 engines/simulator/dsl.py（白名单/三态判据的唯一真源），坏载荷快速失败。
CLI：`python -m db_compile dsl-apply`。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Dict

from db_compile.fp_rules import _norm_text

# DSL 投影列只存在于这两张表（分队规则条目按 spec D5 落 abilities 新行）
_PROJECTION_TABLES = {"abilities": "text_zh", "stratagems": "text_zh"}
# materialize 白名单（PR3）：分队规则正文源只允许 detachments.rule_text——
# 物化条目 table 必须是 abilities（spec D5：owner_id=NULL 新行），指纹对源文本核
_MATERIALIZE_SOURCES = {("detachments", "rule_text")}


def _fingerprint(text) -> str:
    return hashlib.sha256(_norm_text(text).encode("utf-8")).hexdigest()


def _materialize_row(conn, entry, raw, payload: str, report, slim) -> None:
    """分队规则条目物化（PR3，spec D5）：读源表正文 → 指纹核 → INSERT OR REPLACE
    abilities 新行（owner_id=NULL）。指纹漂移时整行删除——物化行本身就是投影，
    留着旧正文+旧编码就是喂错数据（同 H2 降级语义，且比清列更彻底）。"""
    mat = raw["materialize"]
    if (not isinstance(mat, dict)
            or set(mat) != {"from_table", "from_id", "from_column"}
            or (mat["from_table"], mat["from_column"]) not in _MATERIALIZE_SOURCES
            or entry.table != "abilities"):
        raise ValueError(
            f"dsl_payloads 条目 {slim['id']} 的 materialize 不合法：须恰含 "
            f"from_table/from_id/from_column 且源在白名单 {_MATERIALIZE_SOURCES}、"
            f"table 必须是 abilities（spec D5），收到 {mat!r}")
    src = conn.execute(
        f"SELECT {mat['from_column']} FROM {mat['from_table']} WHERE id = ?",
        (mat["from_id"],)).fetchone()
    if src is None:
        report["skipped"].append(
            {**slim, "reason": f"materialize 源行不存在：{mat['from_table']}:{mat['from_id']}"})
        return
    src_text = src[0]
    want = entry.provenance.get("text_sha256") if entry.provenance else None
    if entry.effects and want and _fingerprint(src_text) != want:
        cleared = conn.execute(
            "DELETE FROM abilities WHERE id = ?", (entry.row_id,)).rowcount > 0
        report["fingerprint_mismatch"].append(
            {**slim, "expected": want[:12], "db_now": _fingerprint(src_text)[:12],
             "stale_projection_cleared": cleared})
        return
    cur = conn.execute(
        "SELECT text_zh, effect_dsl_json, dsl_status FROM abilities WHERE id = ?",
        (entry.row_id,)).fetchone()
    if cur == (src_text, payload, entry.status):
        report["already"] += 1
        report["by_status"][entry.status] += 1
        return
    conn.execute(
        "INSERT OR REPLACE INTO abilities "
        "(id, owner_id, scope, condition_json, name_zh, name_en, text_zh, "
        " effect_dsl_json, dsl_status) VALUES (?, NULL, NULL, NULL, ?, ?, ?, ?, ?)",
        (entry.row_id, entry.name_zh, entry.name_en, src_text, payload, entry.status))
    report["applied"] += 1
    report["by_status"][entry.status] += 1
    report["changes"].append({**slim, "status": entry.status, "materialized": True})


def apply_dsl(db_path, payload_dir) -> Dict:
    """把 payload_dir 下全部 *.json 真源投影进库，返回结构化报告。"""
    from engines.simulator.dsl import parse_entry  # 校验唯一真源，坏载荷 raise

    report = {
        "applied": 0, "already": 0,
        "changes": [], "fingerprint_mismatch": [], "skipped": [],
        "by_status": {"encoded": 0, "partial": 0, "not_modeled": 0},
    }
    files = sorted(Path(payload_dir).glob("*.json"))
    seen: set = set()
    conn = sqlite3.connect(str(db_path))
    try:
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            for raw in data.get("entries", []):
                raw = dict(raw)
                raw.setdefault("dsl_version", data.get("dsl_version"))
                raw.setdefault("faction", data.get("faction"))
                entry = parse_entry(raw)          # 不合法直接炸，不静默跳
                key = (entry.table, entry.row_id)
                if key in seen:
                    # 审查 M2：跨文件重复也拒——静默 last-write 是错 id 的温床
                    raise ValueError(f"dsl_payloads 重复条目 {key}（{f.name}）"
                                     f"——同一 (table, id) 只许一条")
                seen.add(key)
                slim = {"table": entry.table, "id": entry.row_id, "name": entry.name_en}
                if raw.get("materialize") is not None:
                    # 分队规则物化路径（PR3）：payload 序列化与常规路径同款
                    payload = json.dumps(raw, ensure_ascii=False, sort_keys=True)
                    _materialize_row(conn, entry, raw, payload, report, slim)
                    continue
                if entry.table not in _PROJECTION_TABLES:
                    report["skipped"].append(
                        {**slim, "reason": f"{entry.table} 表无 DSL 投影列（spec D5：分队规则落 abilities 新行）"})
                    continue
                text_col = _PROJECTION_TABLES[entry.table]
                row = conn.execute(
                    f"SELECT {text_col}, effect_dsl_json, dsl_status "
                    f"FROM {entry.table} WHERE id = ?", (entry.row_id,)).fetchone()
                if row is None:
                    report["skipped"].append({**slim, "reason": "行不存在"})
                    continue
                cur_text, cur_json, cur_status = row
                want = entry.provenance.get("text_sha256") if entry.provenance else None
                if entry.effects and want and _fingerprint(cur_text) != want:
                    # 原文变了而 DSL 没重核——让路告警，不投影过期编码；
                    # 审查 H2：若库里残留着旧投影，必须同步降级清空——否则模拟层
                    # 会继续把"已不再经文本核验"的旧编码当有效 DSL 消费
                    cleared = False
                    if cur_json is not None or cur_status != "not_modeled":
                        conn.execute(
                            f"UPDATE {entry.table} SET effect_dsl_json = NULL, "
                            f"dsl_status = 'not_modeled' WHERE id = ?", (entry.row_id,))
                        cleared = True
                    report["fingerprint_mismatch"].append(
                        {**slim, "expected": want[:12],
                         "db_now": _fingerprint(cur_text)[:12],
                         "stale_projection_cleared": cleared})
                    continue
                payload = json.dumps(raw, ensure_ascii=False, sort_keys=True)
                if cur_json == payload and cur_status == entry.status:
                    report["already"] += 1
                    report["by_status"][entry.status] += 1
                    continue
                conn.execute(
                    f"UPDATE {entry.table} SET effect_dsl_json = ?, dsl_status = ? "
                    f"WHERE id = ?", (payload, entry.status, entry.row_id))
                report["applied"] += 1
                report["by_status"][entry.status] += 1
                report["changes"].append({**slim, "status": entry.status})
        conn.commit()
    finally:
        conn.close()
    return report
