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
    discrepancies: list[dict] = field(default_factory=list)  # {name, faction, field, wahapedia, bsdata}
    unmatched_wahapedia: list[str] = field(default_factory=list)
    # 同一 match_key 下有多个 Wahapedia 单位（跨阵营同名）——全部参与比对，此处披露
    duplicated_names: list[str] = field(default_factory=list)
    # 解析失败被跳过的 .cat（这些文件里的单位没进比对池）：[{path, error}]
    skipped_files: list[dict] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        return round(self.matched / self.wahapedia_total * 100, 1) if self.wahapedia_total else 0.0

    @property
    def agreement_rate(self) -> float:
        return round(self.agreed / self.matched * 100, 1) if self.matched else 0.0


def parse_bsdata_units(bsdata_dir: Path) -> tuple[dict[str, dict], list[dict]]:
    """解析 BSData 全部 .cat 的 Unit profile。

    返回 ({match_key: {name, M, T, SV, W}}, [{path, error}])：
    解析失败的 .cat 不再静默跳过，记录进第二个返回值供上层显眼披露——
    静默跳过意味着整个阵营悄悄退出比对池，交叉校验假阴性。
    BSData 侧无 faction 维度，同名 profile（多为跨 catalogue 重复收录同一单位）
    以 match_key 归一保留最后一条。
    """
    units: dict[str, dict] = {}
    skipped: list[dict] = []
    for path in sorted(glob.glob(str(Path(bsdata_dir) / "*.cat"))):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as e:
            skipped.append({"path": str(path), "error": str(e)})
            continue
        for prof in root.iter(BS_NS + "profile"):
            if prof.get("typeName") != "Unit":
                continue
            name = norm_text(prof.get("name"))
            ch = {c.get("name"): norm_text(c.text)
                  for c in prof.iter(BS_NS + "characteristic")}
            units[match_key(name)] = {"name": name, **{k: ch.get(k, "") for k in STAT_KEYS}}
    return units, skipped


def load_wahapedia_units(db_path: Path) -> dict[str, list[dict]]:
    """从 wh40k.sqlite 读每个单位的首个 model 档位 → {match_key: [{...}, ...]}。

    - 「首个档位」用 MIN(rowid) 子查询确定（rowid 即 CSV 导入顺序，Wahapedia 首行
      是基准模型）；旧实现 `GROUP BY u.name_en` 裸列取值是 SQLite 未定义行为。
    - 不按 name_en 折叠：跨阵营同名单位（如 Ministorum Priest）各自成条全部返回，
      value 是 list；折叠会让另一条永不进比对池（假阴性）。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT u.name_en, u.faction_id, mo.m, mo.t, mo.sv, mo.w "
            "FROM units u JOIN models mo ON mo.unit_id = u.id "
            "WHERE mo.rowid = (SELECT MIN(m2.rowid) FROM models m2 "
            "                  WHERE m2.unit_id = u.id)"
        ).fetchall()
    finally:
        conn.close()
    out: dict[str, list[dict]] = {}
    for name, faction_id, m, t, sv, w in rows:
        out.setdefault(match_key(name), []).append(
            {"name": norm_text(name), "faction_id": faction_id,
             "M": norm_text(m), "T": norm_text(t),
             "SV": norm_text(sv), "W": norm_text(str(w))})
    return out


def cross_check(wahapedia: dict[str, list[dict]],
                bsdata: dict[str, dict]) -> CrossCheckReport:
    """逐名比对两库属性，产出一致率与真·不一致清单。纯函数。

    match_key 语义两侧一致：小写英文名（BSData 无 faction，无法引入阵营维度）。
    Wahapedia 侧同 key 多条（跨阵营同名）全部与同一条 BSData 记录比对，
    并记入 duplicated_names 披露——绝不静默折叠。
    """
    total = sum(len(v) for v in wahapedia.values())
    rep = CrossCheckReport(wahapedia_total=total, bsdata_total=len(bsdata),
                           matched=0, agreed=0)
    for k, w_list in wahapedia.items():
        if len(w_list) > 1:
            rep.duplicated_names.append(w_list[0]["name"])
        b = bsdata.get(k)
        for w in w_list:
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
                            {"name": w["name"], "faction": w.get("faction_id"),
                             "field": f,
                             "wahapedia": w.get(f), "bsdata": b.get(f)})
    rep.discrepancies.sort(key=lambda d: (d["name"], d["field"]))
    rep.unmatched_wahapedia.sort()
    rep.duplicated_names.sort()
    return rep


def run(bsdata_dir: Path, db_path: Path) -> CrossCheckReport:
    bs_units, skipped = parse_bsdata_units(bsdata_dir)
    rep = cross_check(load_wahapedia_units(db_path), bs_units)
    rep.skipped_files = skipped
    return rep
