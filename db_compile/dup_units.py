"""dup_units：库内疑似重复单位排查。**只出报告，一行数据都不改。**

起因：中文层对账逮到一对 —— `000001144 Hellflayers/地狱剥皮机` 与
`000004101 Hellflayer/地狱剥皮机` 同属 CD 阵营。黑图源里只有单数那条，中文名桥
按「只认一对一」正确拒绝了复数那条（硬接会把单数版的中文技能贴到复数版上）。
桥的拒绝是对的，真正要查的是上游：**库里为什么同时存在这两个单位**。

判据（写死在这里，改判据要连测试与报告一起改）：
    两条 units 行进同一「疑似重复组」当且仅当 `faction_id` 相同，且下面任一成立：
      (a) 英文名归一化后相同——小写、去标点、压空白、**逐词去复数**
          （Hellflayers ≡ Hellflayer）；
      (b) 中文名去空白后非空且完全相同（catch「英文名差个头衔前缀、中文名一样」）。
    两条判据用并查集合并，所以同时满足 (a)(b) 的 Hellflayer(s) 只出一组、不重复计数。

判据是**宽的**：宁可多报几组让人去看，也不要漏。所以报告只给证据和一个带标签的
倾向性建议（`likely_current` / `likely_legacy` / `undecided`），**哪条该留是用户的事**。

「现役」沿用全库既有口径：`points_json` 里带 `mfm` 块 = 出现在官方现行 MFM 点数表里
（见 `zh_weapons.coverage_report` / `wiki_engine.keyword_index`）。

CLI：`.\\.venv\\Scripts\\python.exe -m db_compile zh-coverage --dup [--json 路径]`
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

# 倾向性标签。likely_* 只是建议，不构成裁决——组内证据全列在报告里
VERDICTS = ("likely_current", "likely_legacy", "undecided")


def _norm_word(word: str) -> str:
    """单词去复数。规则刻意保守，只处理英文名里真会出现的三种词尾。"""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("sses", "shes", "ches", "xes", "zes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def normalize_en(name: str) -> str:
    """英文名归一化：小写 → 去标点 → 压空白 → 逐词去复数。"""
    text = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    return " ".join(_norm_word(w) for w in text.split())


def normalize_zh(name: str) -> str:
    """中文名归一化：去掉全部空白（中文名里空白无语义）。"""
    return re.sub(r"\s+", "", name or "")


class _Union:
    """并查集：把 (a)(b) 两条判据连出来的边并成组。"""

    def __init__(self) -> None:
        self.parent: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _connect_readonly(db_path) -> sqlite3.Connection:
    """只读连接。本模块的红线是"一行都不改"，用 mode=ro 让越界当场报错而不是靠自觉。"""
    uri = "file:{}?mode=ro".format(Path(db_path).as_posix())
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _count(conn: sqlite3.Connection, sql: str, uid: str) -> int:
    try:
        return conn.execute(sql, (uid,)).fetchone()[0]
    except sqlite3.OperationalError:
        return -1


def _link_suffix(link: str) -> str:
    """Wahapedia 对「同名第二张兵牌」的自带消歧后缀（.../Gladiator-Lancer-1）。"""
    m = re.search(r"-(\d+)$", (link or "").rstrip("/"))
    return m.group(1) if m else ""


def audit(db_path) -> Dict[str, Any]:
    """扫全表找疑似重复组。返回 {total_units, groups, counts}。

    groups 里每组是 {"key": ..., "members": [证据 dict, ...], ...}，
    members 按「疑似现役优先」排序，方便一眼看出哪条像正主。
    """
    conn = _connect_readonly(db_path)
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, faction_id, name_en, name_zh, points_json FROM units")]

        uf = _Union()
        by_en: Dict[Tuple[str, str], List[str]] = {}
        by_zh: Dict[Tuple[str, str], List[str]] = {}
        for r in rows:
            fid = r["faction_id"] or ""
            by_en.setdefault((fid, normalize_en(r["name_en"])), []).append(r["id"])
            zk = normalize_zh(r["name_zh"])
            if zk:
                by_zh.setdefault((fid, zk), []).append(r["id"])
        for bucket in (by_en, by_zh):
            for ids in bucket.values():
                for other in ids[1:]:
                    uf.union(ids[0], other)

        members: Dict[str, List[str]] = {}
        for r in rows:
            members.setdefault(uf.find(r["id"]), []).append(r["id"])
        dup_ids = {i for ids in members.values() if len(ids) > 1 for i in ids}

        info: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            if r["id"] not in dup_ids:
                continue
            uid = r["id"]
            pj = json.loads(r["points_json"] or "{}") or {}
            ds = conn.execute(
                "SELECT source_id, role, link FROM datasheets WHERE id=?", (uid,)).fetchone()
            zh_row = conn.execute(
                "SELECT abilities_json FROM unit_zh_detail WHERE canonical_id=?", (uid,)).fetchone()
            zh_abilities = 0
            if zh_row is not None and zh_row["abilities_json"]:
                zh_abilities = len(json.loads(zh_row["abilities_json"]) or [])
            info[uid] = {
                "id": uid,
                "faction_id": r["faction_id"] or "",
                "name_en": r["name_en"] or "",
                "name_zh": r["name_zh"] or "",
                "current": bool(pj.get("mfm")),
                "points_tiers": [
                    "{}={}".format(it.get("desc"), it.get("cost"))
                    for it in (pj.get("items") or [])],
                "has_zh_row": zh_row is not None,
                "zh_abilities": zh_abilities,
                "n_abilities": _count(conn, "SELECT COUNT(*) FROM abilities WHERE owner_id=?", uid),
                "n_weapons": _count(conn, "SELECT COUNT(*) FROM weapons WHERE unit_id=?", uid),
                "n_models": _count(conn, "SELECT COUNT(*) FROM models WHERE unit_id=?", uid),
                "source_id": (ds["source_id"] if ds else "") or "",
                "role": (ds["role"] if ds else "") or "",
                "link": (ds["link"] if ds else "") or "",
                "link_dup_suffix": _link_suffix(ds["link"] if ds else ""),
                "verdict": "undecided",
            }

        # 源书画像：重复行往往成对落在「大书 vs 小书」上，小书就是重印的那本。
        # Wahapedia 没给我们 Source.csv，只能用兵牌张数 + 举例来刻画它是什么书
        sources: Dict[str, Dict[str, Any]] = {}
        for sid in sorted({m["source_id"] for m in info.values() if m["source_id"]}):
            names = [r["name"] for r in conn.execute(
                "SELECT name FROM datasheets WHERE source_id=? ORDER BY name", (sid,))]
            facs = sorted({r["faction_id"] for r in conn.execute(
                "SELECT DISTINCT faction_id FROM datasheets WHERE source_id=?", (sid,))
                if r["faction_id"]})
            sources[sid] = {"datasheets": len(names), "factions": facs,
                            "sample": names[:6]}
    finally:
        conn.close()

    groups: List[Dict[str, Any]] = []
    for ids in members.values():
        if len(ids) < 2:
            continue
        mem = [info[i] for i in sorted(ids)]
        currents = [m for m in mem if m["current"]]
        # 组内恰好一条在现行 MFM 表里 → 它像正主，其余像遗留。多于一条或一条没有
        # 都判 undecided：两条都现役多半是官方真有两张同名兵牌（Wahapedia 用 -1
        # 后缀消歧），不是数据重复，别替用户拍板
        if len(currents) == 1:
            for m in mem:
                m["verdict"] = "likely_current" if m["current"] else "likely_legacy"
        mem.sort(key=lambda m: (not m["current"], m["id"]))
        groups.append({
            "faction_id": mem[0]["faction_id"],
            "key_en": normalize_en(mem[0]["name_en"]),
            "size": len(mem),
            "decided": len(currents) == 1,
            "members": mem,
        })
    groups.sort(key=lambda g: (g["faction_id"], g["key_en"]))

    counts = {
        "groups": len(groups),
        "units_involved": sum(g["size"] for g in groups),
        "groups_decided": sum(1 for g in groups if g["decided"]),
        "groups_undecided": sum(1 for g in groups if not g["decided"]),
    }
    return {"total_units": len(rows), "counts": counts, "groups": groups,
            "sources": sources}


def format_report(rep: Dict[str, Any]) -> str:
    """人读报告：组数 + 完整名单 + 逐条证据。"""
    c = rep["counts"]
    lines = [
        "===== 库内疑似重复单位排查（只读，未改任何数据）=====",
        "判据：同阵营 且（英文名归一化后相同 ∨ 中文名相同）；归一化 = 小写/去标点/逐词去复数",
        "现役口径：points_json 带 mfm 块（在官方现行 MFM 点数表里）",
        "",
        f"库内 units：{rep['total_units']}",
        f"疑似重复组：{c['groups']}（涉及 {c['units_involved']} 行）"
        f"，其中可判 {c['groups_decided']} 组 / 需人工 {c['groups_undecided']} 组",
    ]
    for g in rep["groups"]:
        lines.append("")
        lines.append("[{}] {}（{} 行，{}）".format(
            g["faction_id"], g["key_en"], g["size"],
            "可判" if g["decided"] else "需人工"))
        for m in g["members"]:
            lines.append(
                "  {id}  {name_en} / {name_zh}".format(**m))
            lines.append(
                "      现役={cur} 点数档={pts} 中文层={zh} 技能={ab} 武器={w} 模型={mo}"
                " 源书={src}{suf}".format(
                    cur="是" if m["current"] else "否",
                    pts=("/".join(m["points_tiers"]) or "—"),
                    zh=("有({} 条技能)".format(m["zh_abilities"]) if m["has_zh_row"] else "无"),
                    ab=m["n_abilities"], w=m["n_weapons"], mo=m["n_models"],
                    src=m["source_id"] or "—",
                    suf="（Wahapedia 同名消歧后缀 -{}）".format(m["link_dup_suffix"])
                        if m["link_dup_suffix"] else ""))
            lines.append("      倾向：{}".format(m["verdict"]))
    if rep.get("sources"):
        lines.append("")
        lines.append("--- 涉事源书画像（Wahapedia source_id；我们手上没有 Source.csv，"
                     "只能用兵牌张数+举例刻画）---")
        for sid, s in sorted(rep["sources"].items()):
            lines.append("  {}  兵牌 {} 张  阵营 {}  例：{}".format(
                sid, s["datasheets"], "/".join(s["factions"]) or "—",
                "、".join(s["sample"])))
    lines.append("")
    lines.append("  本命令只排查不修改——留哪条、删哪条由人裁决")
    return "\n".join(lines)
