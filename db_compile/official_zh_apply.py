"""db_compile/official_zh_apply.py —— 把 GW 官方中文名映射**落进库**（投影层）。

真源是 `db_compile/official_zh_names.json`（git 追踪，由 `official_zh.py` 从 34 个官方
中文 PDF 编译）。本模块只做投影：读 JSON → 写三处库内中文名列。整层可随时重跑，
每次重建库后由 `update.restore_authority_layers` 自动补回。

权威级别（wiki 宪法 §6）：**GW 官方中文 > 汉化组译名 > 社区译名**。
所以官方有的条目一律覆盖既有中文名（多数来自 P7 人工编码），官方没有的一个不动。
被覆盖的旧译名不算丢——它仍在 `dsl_payloads/*.json` 里，wiki 渲染时降为页面 alias
（沿用 2026-07-25「旧译名一条不删，全部降为 alias」的处置）。

落库前踩过的三个坑，都写死在这里：

1. **分队容器名不能挂在 `detachments` 表上**。映射的 123 个容器名撞
   `stratagems.detachment` / `enhancements.detachment_name` 是 123/123，撞
   `detachments.detachment_name` 只有 63/123——走那张表会**静默丢掉 60 个**。
   故容器中文名进独立的 `detachment_names_zh` 表（键就是容器英文名本身）。
   顺带：`detachments.name_zh` 存的是**分队规则名**的中文，不是容器名，不许借用。
2. **`enhancements` 表原本没有 `name_zh` 列**，先 ALTER 再写（幂等，见 `_ensure_targets`）。
3. **同一英文名在不同包里有不同官方译名**（`ARMOUR OF CONTEMPT` → 蔑视战甲 /
   蔑视甲胄，死亡守望 v1.0 vs 各阵营 v1.1）。按英文名做键表达不了这种差异，
   映射里那几条被整条丢弃。所以这里**以行级 `*_by_id` 为准**（每行认自己那本包的
   译名），英文名映射只用来给「本行没配上、但同名条目在别处配上了」的行兜底。

CLI：python -m db_compile official-zh --apply [--dry-run]
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from db_compile.official_zh import _CTRL_CHARS
from db_compile.schema import DETACHMENT_NAMES_ZH_DDL

MAP_PATH = Path(__file__).resolve().parent / "official_zh_names.json"
SOURCE = "official_zh"

# 映射文件必须有的顶层键。缺任何一个都直接报错：少一段就是少落一层中文名，
# 而落库报告只会显示「这一类 0 条」，看着像官方本来就没有。
_REQUIRED_KEYS = ("stratagems", "stratagems_by_id",
                  "enhancements", "enhancements_by_id", "detachments")


def load_mapping(map_path: Path = MAP_PATH) -> Dict[str, Dict[str, str]]:
    """读映射并做结构 + 不可见字符校验（宁可炸，不可静默落个配不上的名字）。"""
    data = json.loads(Path(map_path).read_text(encoding="utf-8"))
    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        raise RuntimeError(
            "映射文件 {} 缺顶层键 {}——先跑 `python -m db_compile official-zh` 重新编译"
            .format(map_path, "、".join(missing)))
    out: Dict[str, Dict[str, str]] = {}
    for key in _REQUIRED_KEYS:
        section = data[key]
        for name_key, zh in section.items():
            # 上游 official_zh 解析时已清过零宽/控制字符。这里再拦一道是因为漏网的后果
            # 极隐蔽：带零宽空格的名字打印、贴报告、肉眼比对全都一模一样，只有 == 为 False。
            for label, text in (("键", name_key), ("值", zh)):
                if _CTRL_CHARS.search(text):
                    bad = [hex(ord(c)) for c in text if _CTRL_CHARS.search(c)]
                    raise RuntimeError(
                        "{} 的{} {!r} 混进不可见字符 {}——上游解析清洗失效了"
                        .format(key, label, text, bad))
            if not name_key.strip() or not zh.strip():
                raise RuntimeError("{} 有空键/空值：{!r} → {!r}".format(key, name_key, zh))
        out[key] = dict(section)
    return out


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute(
        "PRAGMA table_info({})".format(table)))


def _ensure_targets(conn: sqlite3.Connection) -> List[str]:
    """幂等补齐写入目标：enhancements.name_zh 列 + detachment_names_zh 表。"""
    made: List[str] = []
    if not _has_column(conn, "enhancements", "name_zh"):
        conn.execute("ALTER TABLE enhancements ADD COLUMN name_zh TEXT")
        made.append("enhancements.name_zh")
    before = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
        "AND name='detachment_names_zh'").fetchone()[0]
    conn.execute(DETACHMENT_NAMES_ZH_DDL)
    if not before:
        made.append("detachment_names_zh")
    return made


def _has_chinese(text: Optional[str]) -> bool:
    return bool(text) and any("一" <= c <= "鿿" for c in str(text))


def _plan(rows: List[Tuple[str, str, Optional[str]]],
          by_id: Dict[str, str], by_name: Dict[str, str],
          fold_case: bool) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """算出每行该写的中文名。行级映射优先，同名兜底其次。

    rows: [(id, name_en, 现有 name_zh)]
    """
    targets: Dict[str, str] = {}
    stat = {"by_id": 0, "by_name": 0, "already": 0, "superseded": [],
            "superseded_total": 0}
    for rid, name_en, cur in rows:
        zh = by_id.get(rid)
        if zh:
            stat["by_id"] += 1
        else:
            key = (name_en or "").strip()
            zh = by_name.get(key.upper() if fold_case else key)
            if zh:
                stat["by_name"] += 1
        if not zh:
            continue
        targets[rid] = zh
        cur_s = (cur or "").strip()
        if cur_s == zh:
            stat["already"] += 1
        elif _has_chinese(cur_s):
            # 官方译名顶掉了一个既有中文名——这是权威升级，不是数据丢失，但必须报出来
            stat["superseded_total"] += 1
            if len(stat["superseded"]) < 40:
                stat["superseded"].append(
                    {"id": rid, "name_en": name_en, "old": cur_s, "new": zh})
    return targets, stat


def apply_official_zh(db_path, map_path: Path = MAP_PATH,
                      dry_run: bool = False) -> Dict[str, Any]:
    """把官方中文名投影进库。返回对账报告；写完当场回查核对，差额非 0 直接炸。

    `dry_run` 连表结构都不动（sqlite 的 DDL 不吃 rollback，补了就是补了），
    所以缺列的旧库上跑 dry-run 也不会留下半截 schema。
    """
    data = load_mapping(map_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        has_enh_zh = _has_column(conn, "enhancements", "name_zh")
        made = [] if dry_run else _ensure_targets(conn)

        strat_rows = [(r[0], r[1] or "", r[2]) for r in conn.execute(
            "SELECT id, name_en, name_zh FROM stratagems")]
        enh_sql = ("SELECT id, name, name_zh FROM enhancements" if has_enh_zh
                   else "SELECT id, name, NULL FROM enhancements")
        enh_rows = [(r[0], r[1] or "", r[2]) for r in conn.execute(enh_sql)]
        strat_targets, strat_stat = _plan(
            strat_rows, data["stratagems_by_id"], data["stratagems"], fold_case=True)
        enh_targets, enh_stat = _plan(
            enh_rows, data["enhancements_by_id"], data["enhancements"], fold_case=False)

        # 行级映射里指向库中不存在的 id ＝ 库换过一轮 id，映射该重编译了。
        # 不报出来的话表现是「命中数悄悄变少」，和官方本来就没收录长得一模一样。
        db_sids = {r[0] for r in strat_rows}
        db_eids = {r[0] for r in enh_rows}
        missing = {
            "stratagems": sorted(set(data["stratagems_by_id"]) - db_sids),
            "enhancements": sorted(set(data["enhancements_by_id"]) - db_eids),
        }

        # 容器中文名：键是容器**英文名**，与 stratagems.detachment /
        # enhancements.detachment_name 同口径（123/123 可 join）
        containers = {r[0] for r in conn.execute(
            "SELECT DISTINCT detachment FROM stratagems WHERE detachment IS NOT NULL")}
        containers |= {r[0] for r in conn.execute(
            "SELECT DISTINCT detachment_name FROM enhancements "
            "WHERE detachment_name IS NOT NULL")}
        det_map = data["detachments"]
        det_orphans = sorted(set(det_map) - containers)

        report: Dict[str, Any] = {
            "schema_added": made,
            "stratagems": {**strat_stat, "targeted": len(strat_targets),
                           "db_rows": len(strat_rows)},
            "enhancements": {**enh_stat, "targeted": len(enh_targets),
                             "db_rows": len(enh_rows)},
            "detachments": {"targeted": len(det_map),
                            "db_containers": len(containers),
                            "orphans": det_orphans},
            "missing_ids": {k: v[:20] for k, v in missing.items()},
            "missing_ids_total": {k: len(v) for k, v in missing.items()},
            "dry_run": dry_run,
        }
        if dry_run:
            conn.rollback()
            report["schema_pending"] = (
                [] if has_enh_zh else ["enhancements.name_zh"])
            return report

        conn.executemany("UPDATE stratagems SET name_zh = ? WHERE id = ?",
                         [(zh, rid) for rid, zh in sorted(strat_targets.items())])
        conn.executemany("UPDATE enhancements SET name_zh = ? WHERE id = ?",
                         [(zh, rid) for rid, zh in sorted(enh_targets.items())])
        # 整表重灌而不是增量 upsert：映射是这一层的唯一真源，上一轮多出来的行
        # （官方改译名/撤条目）留在表里就成了幽灵译名，没人会发现。
        conn.execute("DELETE FROM detachment_names_zh WHERE source = ?", (SOURCE,))
        conn.executemany(
            "INSERT OR REPLACE INTO detachment_names_zh (name_en, name_zh, source) "
            "VALUES (?, ?, ?)",
            [(en, zh, SOURCE) for en, zh in sorted(det_map.items())])
        conn.commit()

        # 回查对账：写了 N 行就该有 N 行读回来是那个值（宁可炸也不报「已完成」）
        got_s = sum(1 for rid, zh in strat_targets.items()
                    if (conn.execute("SELECT name_zh FROM stratagems WHERE id = ?",
                                     (rid,)).fetchone() or [None])[0] == zh)
        got_e = sum(1 for rid, zh in enh_targets.items()
                    if (conn.execute("SELECT name_zh FROM enhancements WHERE id = ?",
                                     (rid,)).fetchone() or [None])[0] == zh)
        got_d = conn.execute("SELECT COUNT(*) FROM detachment_names_zh "
                             "WHERE source = ?", (SOURCE,)).fetchone()[0]
        report["verified"] = {"stratagems": got_s, "enhancements": got_e,
                              "detachments": got_d}
        gaps = {k: (want, got) for k, want, got in
                (("stratagems", len(strat_targets), got_s),
                 ("enhancements", len(enh_targets), got_e),
                 ("detachments", len(det_map), got_d)) if want != got}
        if gaps:
            raise RuntimeError("落库对账不平（应写 vs 读回）：{}".format(gaps))
        return report
    finally:
        conn.close()


def coverage(db_path) -> Dict[str, Tuple[int, int]]:
    """当前库内中文名覆盖率（含中文的行 / 总行），供 CLI 与测试做地板检查。"""
    conn = sqlite3.connect(str(db_path))
    try:
        out: Dict[str, Tuple[int, int]] = {}
        for table, col in (("stratagems", "name_zh"), ("enhancements", "name_zh")):
            if not _has_column(conn, table, col):
                out[table] = (0, conn.execute(
                    "SELECT COUNT(*) FROM {}".format(table)).fetchone()[0])
                continue
            rows = [r[0] for r in conn.execute(
                "SELECT {} FROM {}".format(col, table))]
            out[table] = (sum(1 for v in rows if _has_chinese(v)), len(rows))
        has_tbl = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
            "AND name='detachment_names_zh'").fetchone()[0]
        named = conn.execute(
            "SELECT COUNT(*) FROM detachment_names_zh").fetchone()[0] if has_tbl else 0
        containers = {r[0] for r in conn.execute(
            "SELECT DISTINCT detachment FROM stratagems WHERE detachment IS NOT NULL")}
        containers |= {r[0] for r in conn.execute(
            "SELECT DISTINCT detachment_name FROM enhancements "
            "WHERE detachment_name IS NOT NULL")}
        out["detachments"] = (named, len(containers))
        return out
    finally:
        conn.close()


def load_detachment_names_zh(db_path) -> Dict[str, str]:
    """容器英文名 → 官方中文名。表不存在时返回空字典（旧库可读，不炸）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        if not conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
                "AND name='detachment_names_zh'").fetchone()[0]:
            return {}
        return {r[0]: r[1] for r in conn.execute(
            "SELECT name_en, name_zh FROM detachment_names_zh")}
    finally:
        conn.close()
