"""BSData ↔ Wahapedia 英文属性交叉校验（蓝图第二源，保证英文『绝对正确』的门禁）。

英文是唯一权威真值，但单一社区源 + 记忆都不足以担保正确。本模块解析 BSData/wh40k-10e
（BattleScribe .cat XML）的全部 Unit 属性，与 wh40k.sqlite 的 units+models 逐名比对：
两库一致 → 高置信；不一致 → 挑出来供人工对官方（多为某次移动值勘误收录不同步）。

读取型，绝不改库。用法：
  python -m db_compile crosscheck [--bsdata db_sources/bsdata] [--db db/wh40k.sqlite] [--out report.json]
"""
from __future__ import annotations

import glob
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

BS_NS = "{http://www.battlescribe.net/schema/catalogueSchema}"
STAT_KEYS = ("M", "T", "SV", "W")


def norm_text(v: str | None) -> str:
    """统一花引号/空白。"""
    return (v or "").strip().replace("”", '"').replace("’", "'")


def match_key(name: str | None) -> str:
    """名字匹配键：大小写不敏感 + 去首尾空白（BSData 与 Wahapedia 大小写常不一致）。"""
    return norm_text(name).lower()


def cmp_val(v: str | None) -> str:
    """属性比较归一化：去引号/空格，消除纯格式差异。

    让 20+" == 20"+ == 20+，10" == 10，避免把同值不同写法误报成分歧。
    """
    return (v or "").replace('"', "").replace(" ", "").strip()


def stats_agree(a: dict, b: dict) -> bool:
    return all(cmp_val(a.get(k)) == cmp_val(b.get(k)) for k in STAT_KEYS)


@dataclass
class CrossCheckReport:
    wahapedia_total: int
    bsdata_total: int
    matched: int
    agreed: int
    discrepancies: list[dict] = field(default_factory=list)  # {name, field, wahapedia, bsdata}
    unmatched_wahapedia: list[str] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        return round(self.matched / self.wahapedia_total * 100, 1) if self.wahapedia_total else 0.0

    @property
    def agreement_rate(self) -> float:
        return round(self.agreed / self.matched * 100, 1) if self.matched else 0.0


def parse_bsdata_units(bsdata_dir: Path) -> dict[str, dict]:
    """解析 BSData 全部 .cat 的 Unit profile → {match_key: {name, M, T, SV, W}}。"""
    units: dict[str, dict] = {}
    for path in sorted(glob.glob(str(Path(bsdata_dir) / "*.cat"))):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for prof in root.iter(BS_NS + "profile"):
            if prof.get("typeName") != "Unit":
                continue
            name = norm_text(prof.get("name"))
            ch = {c.get("name"): norm_text(c.text)
                  for c in prof.iter(BS_NS + "characteristic")}
            units[match_key(name)] = {"name": name, **{k: ch.get(k, "") for k in STAT_KEYS}}
    return units


def load_wahapedia_units(db_path: Path) -> dict[str, dict]:
    """从 wh40k.sqlite 读单位英文名 + 首个 model 的 M/T/SV/W → {match_key: {...}}。"""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT u.name_en, mo.m, mo.t, mo.sv, mo.w FROM units u "
            "JOIN models mo ON mo.unit_id = u.id GROUP BY u.name_en"
        ).fetchall()
    finally:
        conn.close()
    out: dict[str, dict] = {}
    for name, m, t, sv, w in rows:
        out[match_key(name)] = {"name": norm_text(name), "M": norm_text(m),
                                "T": norm_text(t), "SV": norm_text(sv), "W": norm_text(str(w))}
    return out


def cross_check(wahapedia: dict[str, dict], bsdata: dict[str, dict]) -> CrossCheckReport:
    """逐名比对两库属性，产出一致率与真·不一致清单。纯函数。"""
    rep = CrossCheckReport(wahapedia_total=len(wahapedia), bsdata_total=len(bsdata),
                           matched=0, agreed=0)
    for k, w in wahapedia.items():
        b = bsdata.get(k)
        if b is None:
            rep.unmatched_wahapedia.append(w["name"])
            continue
        rep.matched += 1
        if stats_agree(w, b):
            rep.agreed += 1
        else:
            for f in STAT_KEYS:
                if cmp_val(w.get(f)) != cmp_val(b.get(f)):
                    rep.discrepancies.append(
                        {"name": w["name"], "field": f,
                         "wahapedia": w.get(f), "bsdata": b.get(f)})
    rep.discrepancies.sort(key=lambda d: (d["name"], d["field"]))
    rep.unmatched_wahapedia.sort()
    return rep


def run(bsdata_dir: Path, db_path: Path) -> CrossCheckReport:
    return cross_check(load_wahapedia_units(db_path), parse_bsdata_units(bsdata_dir))
