# wiki_compile/canonical.py
"""Wahapedia CSV 下载与解析 —— 中英配对的 canonical 英文名锚点（spec 决策4）。"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

WAHAPEDIA_BASE = "https://wahapedia.ru/wh40k10ed"
TABLES = ("Factions.csv", "Datasheets.csv")


@dataclass(frozen=True)
class CanonicalEntry:
    id: str
    name: str
    faction_id: str


def _split_lines(text: str) -> List[str]:
    return [ln for ln in text.replace("﻿", "").splitlines() if ln.strip()]


def _to_row(header: List[str], record: str) -> Dict[str, str]:
    fields = record.split("|")
    return {h: (fields[i].strip() if i < len(fields) else "")
            for i, h in enumerate(header) if h}


def parse_wahapedia_csv(text: str) -> List[Dict[str, str]]:
    """Wahapedia 导出：| 分隔、行尾多一个 |、首行表头、可能带 BOM。

    **裸换行续行**：legend/description 里允许出现不加引号的换行——Wahapedia 导出
    不做 CSV 引号转义。按物理行读会把这样一条记录劈成两截：前半截字段不足（后面
    的列全空），后半截整体左移一格（第 1 列变成正文残句、第 3 列变成 phase 之类）。
    实测 Stratagems.csv 的 THREAT‑COGITATION TARGETERS 就这样在库里留下一条
    id='Shooting phase' 的垃圾行，同时那条真战略的正文/分队/阶段三列全空。

    所以按「字段数补满表头」判断记录边界：不足就把下一物理行接上（换行原样留在
    字段里，它本来就是原文的一部分），补满才收一条。字段数超出表头（正文里出现
    裸 `|`）时照旧只取前 N 列，且绝不吞掉下一行。
    """
    lines = _split_lines(text)
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split("|")]
    width = len(header)
    rows: List[Dict[str, str]] = []
    buf: Optional[str] = None
    for ln in lines[1:]:
        buf = ln if buf is None else buf + "\n" + ln
        if len(buf.split("|")) < width:
            continue                      # 字段没补满：这条被裸换行劈开了，接下一行
        rows.append(_to_row(header, buf))
        buf = None
    if buf is not None:
        # 文件末尾截断（下载中断等）：如实产出这条残行，缺的列留空——静默吞掉
        # 才是真正的坑，行数对账会把它显出来
        rows.append(_to_row(header, buf))
    return rows


def audit_wahapedia_csv(text: str) -> Dict[str, Optional[int]]:
    """解析对账：解析出的记录数 vs 文件里的真实条目数，差额应恒为 0。

    真实条目数用**与按行读无关**的口径推算：每条完整记录恰含 `len(表头)-1` 个
    分隔符（行尾多一个 `|` 也算在表头里），裸换行把一条劈成两截时两截的分隔符
    数相加守恒，所以「数据区 `|` 总数 ÷ 每条分隔符数」不受续行影响。
    整除不了说明正文里混入了裸 `|`，此口径失效——如实报 None 而不是猜一个数。

    reconciled=False 必须当故障处理：别用 `if delta:` 判，delta 为 None（口径失效）
    时那是假的通过。
    """
    lines = _split_lines(text)
    if not lines:
        return {"physical_lines": 0, "parsed_rows": 0, "expected_rows": 0,
                "delta": 0, "reconciled": True}
    seps = len(lines[0].split("|")) - 1
    body = lines[1:]
    total_seps = sum(ln.count("|") for ln in body)
    expected = (total_seps // seps) if seps > 0 and total_seps % seps == 0 else None
    parsed = len(parse_wahapedia_csv(text))
    return {
        "physical_lines": len(body),
        "parsed_rows": parsed,
        "expected_rows": expected,
        "delta": None if expected is None else parsed - expected,
        "reconciled": expected is not None and parsed == expected,
    }


def fetch_tables(dest: Path) -> None:
    """下载 canonical 表。需环境代理（HTTPS_PROXY），urllib 自动读取。"""
    dest.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        url = "{}/{}".format(WAHAPEDIA_BASE, table)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            (dest / table).write_bytes(resp.read())
        print("已下载", table)


def load_canonical(csv_dir: Path) -> List[CanonicalEntry]:
    rows = parse_wahapedia_csv(
        (csv_dir / "Datasheets.csv").read_text(encoding="utf-8"))
    return [CanonicalEntry(id=r.get("id", ""), name=r.get("name", ""),
                           faction_id=r.get("faction_id", ""))
            for r in rows if r.get("name")]
