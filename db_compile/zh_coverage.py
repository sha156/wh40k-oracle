"""zh_coverage：兵牌中文技能覆盖对账。

技能中文正文的唯一来源是黑图书馆（`unit_zh_detail.abilities_json`）——`abilities`
表的 `text_zh` 全库无一个中文字符。所以「某单位页上的技能为什么还是英文」只有三种
可能，本模块把 units 全表**无遗漏地**归进这几类并报绝对数：

1. `zh_ok`          —— 有中文层且技能非空，页面显示中文
2. `zh_row_empty`   —— 有中文层但 `abilities_json` 是 []：**源里就是空的**，
                       黑图作者只填了属性/武器没填技能，抓多少次都一样
3. `absent_*`       —— 库里这个单位在黑图侧根本没有（或有条目但没 detail 正文）

红线：查不到就是查不到。本模块只做对账与点名，**不生成任何中文正文**——
补不齐的单位在页面上逐字退回英文（`entity_card._abilities` 的既有行为）。

CLI：`.\\.venv\\Scripts\\python.exe -m db_compile zh-coverage [--json 路径]`
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from db_compile.blacklibrary import (DEFAULT_CACHE, DEFAULT_DETAILS_CACHE,
                                     _norm_en, _norm_zh)

# 归因类别（顺序即报告顺序）。名字直接进报告，改名要连测试与文档一起改。
CATEGORIES = (
    "zh_ok",
    "zh_row_empty_abilities",
    "absent_source_has_no_entry",
    "absent_source_entry_without_detail",
    "absent_source_entry_not_fetched",
)


def _load_json(path: Path) -> List[dict]:
    if not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def audit(db_path,
          list_cache: Optional[Path] = None,
          details_cache: Optional[Path] = None) -> Dict[str, Any]:
    """逐单位归因中文技能覆盖。返回 {total, counts, units, source}。

    `units` 是 [{id, name_en, name_zh, category}]，每个 units 行**恰好**一条，
    所以 sum(counts.values()) == total 是可断言的守恒式——分类漏项会当场露馅。
    """
    list_units = _load_json(Path(list_cache) if list_cache else DEFAULT_CACHE)
    details = _load_json(Path(details_cache) if details_cache else DEFAULT_DETAILS_CACHE)

    list_en = {_norm_en(u.get("unitEnglishName")) for u in list_units
               if (u.get("unitEnglishName") or "").strip()}
    list_zh = {_norm_zh(u.get("unitName")) for u in list_units if u.get("unitName")}
    list_en.discard("")
    list_zh.discard("")
    det_en, det_zh_with_detail = {}, set()
    for r in details:
        det_en[_norm_en(r.get("name_en"))] = r
        if r.get("detail"):
            det_zh_with_detail.add(_norm_zh(r.get("name_zh")))
    det_en.pop("", None)
    det_zh_with_detail.discard("")

    conn = sqlite3.connect(str(db_path))
    try:
        zh_rows = {}
        try:
            for cid, ab in conn.execute(
                    "SELECT canonical_id, abilities_json FROM unit_zh_detail"):
                zh_rows[cid] = ab
        except sqlite3.OperationalError:
            zh_rows = {}
        rows = conn.execute("SELECT id, name_en, name_zh FROM units").fetchall()
    finally:
        conn.close()

    out: List[Dict[str, str]] = []
    for cid, name_en, name_zh in rows:
        if cid in zh_rows:
            parsed = json.loads(zh_rows[cid]) if zh_rows[cid] else None
            cat = "zh_ok" if parsed else "zh_row_empty_abilities"
        else:
            ek, zk = _norm_en(name_en), _norm_zh(name_zh)
            rec = det_en.get(ek)
            if rec is not None or zk in det_zh_with_detail:
                # 源里抓到了正文却没进库＝匹配层漏了，是缺陷不是数据缺口
                cat = ("absent_source_entry_without_detail"
                       if rec is not None and not rec.get("detail")
                       else "absent_source_entry_not_fetched")
            elif ek in list_en or zk in list_zh:
                cat = "absent_source_entry_not_fetched"
            else:
                cat = "absent_source_has_no_entry"
        out.append({"id": cid, "name_en": name_en or "",
                    "name_zh": name_zh or "", "category": cat})

    counts = {c: 0 for c in CATEGORIES}
    for u in out:
        counts[u["category"]] += 1
    return {"total": len(rows), "counts": counts, "units": out,
            "source": {"list_entries": len(list_units), "detail_records": len(details),
                       "detail_records_with_payload": sum(
                           1 for r in details if r.get("detail"))}}


def format_report(rep: Dict[str, Any], name_limit: int = 40) -> str:
    """人读对账报告：绝对数 + 补不到的单位点名。"""
    c, s = rep["counts"], rep["source"]
    lines = [
        "===== 兵牌中文技能覆盖对账 =====",
        f"黑图书馆源：list {s['list_entries']} 条 / detail {s['detail_records']} 条"
        f"（含正文 {s['detail_records_with_payload']}）",
        f"库内 units：{rep['total']}",
        f"  ① 有中文技能（页面显示中文）        : {c['zh_ok']}",
        f"  ② 有中文层但技能为空（源里就是空的）: {c['zh_row_empty_abilities']}",
        f"  ③ 源里有条目但无正文               : {c['absent_source_entry_without_detail']}",
        f"  ④ 源里有条目但未抓到/未入库         : {c['absent_source_entry_not_fetched']}",
        f"  ⑤ 源里根本没有这个单位             : {c['absent_source_has_no_entry']}",
        f"  合计校验：{sum(c.values())} == {rep['total']}"
        f" {'OK' if sum(c.values()) == rep['total'] else '❌ 分类漏项'}",
    ]
    for cat, title in (("zh_row_empty_abilities", "② 源里技能为空（补不到，页面退英文）"),
                       ("absent_source_entry_without_detail", "③ 源里条目无正文（补不到）"),
                       ("absent_source_entry_not_fetched", "④ 源里有条目却没入库（可查）")):
        names = [f"{u['name_zh'] or u['name_en']}({u['id']})"
                 for u in rep["units"] if u["category"] == cat]
        if not names:
            continue
        lines.append(f"\n{title}：{len(names)} 个")
        shown = names[:name_limit]
        lines.append("  " + "、".join(shown)
                     + (f" …（另 {len(names) - len(shown)} 个见 --json）"
                        if len(names) > len(shown) else ""))
    return "\n".join(lines)
