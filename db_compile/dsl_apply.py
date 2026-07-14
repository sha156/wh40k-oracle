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


def _fingerprint(text) -> str:
    return hashlib.sha256(_norm_text(text).encode("utf-8")).hexdigest()


def apply_dsl(db_path, payload_dir) -> Dict:
    """把 payload_dir 下全部 *.json 真源投影进库，返回结构化报告。"""
    from engines.simulator.dsl import parse_entry  # 校验唯一真源，坏载荷 raise

    report = {
        "applied": 0, "already": 0,
        "changes": [], "fingerprint_mismatch": [], "skipped": [],
        "by_status": {"encoded": 0, "partial": 0, "not_modeled": 0},
    }
    files = sorted(Path(payload_dir).glob("*.json"))
    conn = sqlite3.connect(str(db_path))
    try:
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            for raw in data.get("entries", []):
                raw = dict(raw)
                raw.setdefault("dsl_version", data.get("dsl_version"))
                raw.setdefault("faction", data.get("faction"))
                entry = parse_entry(raw)          # 不合法直接炸，不静默跳
                slim = {"table": entry.table, "id": entry.row_id, "name": entry.name_en}
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
                    # 原文变了而 DSL 没重核——让路告警，不投影过期编码
                    report["fingerprint_mismatch"].append(
                        {**slim, "expected": want[:12], "db_now": _fingerprint(cur_text)[:12]})
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
