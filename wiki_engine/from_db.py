"""wiki_engine/from_db.py — 从官方结构库 db/wh40k.sqlite 渲染单位 wiki 页。

与 synthesize（LLM 从 PDF 合成）互补：本模块**所有游戏数值取自官方结构表**
（units/models/weapons/abilities/points_json，已同步官方 MFM + 11 版），
数值与官网一致 by construction；中文名称/技能文本/武器中文名取自 unit_zh_detail
（黑图书馆中文层，仅作翻译层，其数值不覆盖官方——有漂移时官方值胜出并记日志）。

识别到的 USR/关键词输出成裸 [[label]]，交给 crosslinks.canonicalize_known_terms
落成 [[core-rules/…|label]] 可点链接；表格单元格内的 wikilink 竖线转义成 \\|
避免与表格列分隔符冲突。无 unit_zh_detail 的单位退回官方英文数据卡（数值仍准）。

CLI：python -m wiki_engine.from_db [--faction ORK] [--db …] [--wiki wiki]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from wiki_engine._io import atomic_write_text
from wiki_engine.crosslinks import _resolve_known_alias, escape_table_pipes
from wiki_engine.models import FACTION_NAMES, WikiPage, WikiPageFrontmatter, slugify

# 官方 faction_id → wiki 中文目录名。补齐 FACTION_NAMES 未覆盖的 4 个；
# ORK 覆写为社区惯用「兽人」（与既有 wiki 目录一致，FACTION_NAMES 作「欧克蛮人」）。
FACTION_DIRS: Dict[str, str] = {
    **FACTION_NAMES,
    "ORK": "兽人",
    "AM": "星界军", "LoV": "灰暗联盟", "TYR": "泰伦虫族", "UN": "无阵营工事",
}

_EMPTY_INVULN = {None, "", "-", "—", "N/A", "n/a"}


# ── unit_zh_detail 解析（中文翻译层）────────────────────────────────────

def _wkey(a, s, ap, d) -> Tuple[str, str, str, str]:
    return (str(a), str(s), str(ap), str(d))


def _zh_weapons_indices(zh_weapons: Optional[dict]
                        ) -> Tuple[Dict, Dict]:
    """zh weapons_json → (射击 idx, 近战 idx)，各 {(a,s,ap,d):(name,[skills])}。
    分组避免同侧写跨类碰撞（双联手铳 vs 咬人跳跳 同 2/4/0/1）。"""
    ranged: Dict = {}
    melee: Dict = {}
    for gname, group in (zh_weapons or {}).items():
        tgt = melee if "近战" in gname else ranged
        for w in group or []:
            tgt[_wkey(w.get("攻击次数"), w.get("造伤"), w.get("破甲"),
                      w.get("伤害"))] = (w.get("name"), w.get("skill") or [])
    return ranged, melee


def _zh_keywords(intro: Optional[list]) -> Tuple[List[str], List[str]]:
    """intro_json → (阵营关键词, 普通关键词)。标签项后一项的文本即对应关键词组。"""
    def texts(item):
        if not isinstance(item, dict):
            return []
        return [c.get("text", "").strip()
                for c in (item.get("content") or [])
                if isinstance(c, dict) and c.get("text", "").strip()]
    fac: List[str] = []
    kws: List[str] = []
    intro = intro or []
    for i, item in enumerate(intro):
        joined = "".join(texts(item))
        if joined == "阵营关键词" and i + 1 < len(intro):
            fac = texts(intro[i + 1])
        elif joined == "关键词" and i + 1 < len(intro):
            kws = texts(intro[i + 1])
    return fac, kws


def _flatten_zh_ability(ab: dict) -> Tuple[str, str]:
    """zh abilities_json 单条 → (显示名, 正文)。"""
    prefix = ab.get("name", "") if isinstance(ab, dict) else ""
    texts: List[str] = []
    for blk in (ab.get("content") if isinstance(ab, dict) else None) or []:
        if not isinstance(blk, dict):
            continue
        for c in blk.get("content") or []:
            t = (c.get("text") or "").strip() if isinstance(c, dict) else ""
            if t:
                texts.append(t)
    return prefix, "".join(texts)


def _zh_model_desc(desc: str) -> str:
    """'3 models' → '3个模型'。"""
    m = re.match(r"(\d+)\s*models?", (desc or "").strip())
    return "{}个模型".format(m.group(1)) if m else desc


def _wrap(label: str) -> str:
    """已知 USR/核心术语 → 裸 [[label]]（交 canonicalize 落 core-rules 链接）；
    无法解析的保持纯文本，避免制造断链。"""
    label = (label or "").strip()
    return "[[{}]]".format(label) if label and _resolve_known_alias(label) else label


# ── 一致性护栏 ─────────────────────────────────────────────────────────

def check_drift(models, weapons, zstats, zw_ranged, zw_melee) -> List[Dict]:
    """官方结构表 vs 黑图书馆中文层的数值漂移检测（官方值渲染，漂移仅记录披露）。"""
    drift: List[Dict] = []
    for i, m in enumerate(models):
        if i >= len(zstats):
            continue
        z = zstats[i]
        for off_k, z_k in [("m", "m"), ("t", "t"), ("sv", "sv"),
                           ("w", "w"), ("ld", "ld"), ("oc", "oc")]:
            ov = re.sub(r'["+\s]', "", str(m[off_k] or ""))
            zv = re.sub(r'["+\s]', "", str(z.get(z_k) or ""))
            if ov and zv and ov != zv:
                drift.append({"kind": "stat", "model": m["name"], "field": off_k,
                              "official": m[off_k], "zh": z.get(z_k)})
    return drift


# ── 渲染 ───────────────────────────────────────────────────────────────

def _fetch_unit(conn, uid):
    conn.row_factory = sqlite3.Row
    u = conn.execute("SELECT * FROM units WHERE id=?", (uid,)).fetchone()
    models = conn.execute("SELECT * FROM models WHERE unit_id=?", (uid,)).fetchall()
    weapons = conn.execute("SELECT * FROM weapons WHERE unit_id=?", (uid,)).fetchall()
    abils = conn.execute(
        "SELECT scope,name_zh,name_en,text_zh FROM abilities WHERE owner_id=?",
        (uid,)).fetchall()
    zd = conn.execute(
        "SELECT stats_json,abilities_json,weapons_json,intro_json "
        "FROM unit_zh_detail WHERE canonical_id=?", (uid,)).fetchone()
    return u, models, weapons, abils, zd


def render_unit(conn, uid: str, faction_zh: str) -> Tuple[WikiPage, List[Dict]]:
    """渲染单个单位为 WikiPage（数值官方、中文黑图书馆、USR/关键词裸链）。"""
    u, models, weapons, abils, zd = _fetch_unit(conn, uid)
    zstats = json.loads(zd["stats_json"]) if zd and zd["stats_json"] else []
    zabils = json.loads(zd["abilities_json"]) if zd and zd["abilities_json"] else []
    zw_ranged, zw_melee = _zh_weapons_indices(
        json.loads(zd["weapons_json"]) if zd and zd["weapons_json"] else {})
    zintro = json.loads(zd["intro_json"]) if zd and zd["intro_json"] else []
    zfac_kw, zkw = _zh_keywords(zintro)

    pj = json.loads(u["points_json"] or "{}")
    kw = json.loads(u["keywords_json"] or "{}")
    fetched = (pj.get("mfm") or {}).get("fetched_at", "")
    drift = check_drift(models, weapons, zstats, zw_ranged, zw_melee)

    L: List[str] = []
    # 属性表（官方数值 + 中文模型名兜底）
    L += ["## 属性表", "| 模型 | M | T | SV | W | LD | OC |",
          "|---|---|---|---|---|---|---|"]
    for i, m in enumerate(models):
        z = zstats[i] if i < len(zstats) else {}
        mname = (z.get("unitName") if isinstance(z, dict) else None) or m["name"]

        def cell(off_val, z_key, unit=""):
            # 官方值优先；官方缺失（-/空，多为 Wahapedia 抽取遗漏）时退回中文层
            if str(off_val).strip() in _EMPTY_INVULN and isinstance(z, dict) and z.get(z_key):
                zv = str(z[z_key])
                return zv + unit if unit and not zv.endswith(unit) else zv
            return off_val
        L.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            mname, cell(m["m"], "m", "\""), cell(m["t"], "t"), cell(m["sv"], "sv"),
            cell(m["w"], "w"), cell(m["ld"], "ld"), cell(m["oc"], "oc")))
    invulns = [m["invuln"] for m in models if m["invuln"] not in _EMPTY_INVULN]
    if invulns:
        L += ["", "### 特殊保护", "- {}+".format(str(invulns[0]).rstrip("+"))]

    # 武器（官方侧写 + 中文名/技能兜底，USR 裸链）
    def wrows(rows, melee):
        hdr = "WS" if melee else "BS"
        zidx = zw_melee if melee else zw_ranged
        out = ["| 武器 | 射程 | A | {} | S | AP | D | 技能 |".format(hdr),
               "|---|---|---|---|---|---|---|---|"]
        for w in rows:
            zname, zskill = zidx.get(_wkey(w["a"], w["s"], w["ap"], w["d"]),
                                    (None, None))
            name = zname or w["name_zh"] or w["name_en"]
            rng = "近战" if melee else "{}\"".format(w["range"])
            bs = "{}+".format(w["bs_ws"]) if str(w["bs_ws"]).isdigit() else w["bs_ws"]
            if zskill:
                skills = "，".join(_wrap(s) for s in zskill)
            else:
                kj = json.loads(w["keywords_json"]) if w["keywords_json"] else []
                # keywords_json 常是 ["a, b, c"] 单串——拆开逐个包链
                flat = []
                for item in kj:
                    flat += [p.strip() for p in str(item).split(",") if p.strip()]
                skills = "，".join(_wrap(s) for s in flat) if flat else "—"
            out.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                name, rng, w["a"], bs, w["s"], w["ap"], w["d"], skills))
        return out
    ranged = [w for w in weapons if str(w["range"]).lower() != "melee"]
    melee = [w for w in weapons if str(w["range"]).lower() == "melee"]
    if ranged:
        L += ["", "## 射击武器"] + wrows(ranged, False)
    if melee:
        L += ["", "## 近战武器"] + wrows(melee, True)

    # 技能（中文优先黑图书馆，无则官方 abilities 表）
    if zabils:
        L += ["", "## 技能"]
        for ab in zabils:
            prefix, text = _flatten_zh_ability(ab)
            L.append("- **{}**：{}".format(prefix, text) if text
                     else "- **{}**".format(prefix))
    elif abils:
        L += ["", "## 技能"]
        for a in abils:
            nm = a["name_zh"] or a["name_en"] or ""
            tx = a["text_zh"] or ""
            L.append("- **{}**：{}".format(nm, tx) if tx else "- **{}**".format(nm))

    # 单位构成/点数（官方 MFM）
    if pj.get("items"):
        L += ["", "## 单位构成"]
        for it in pj["items"]:
            L.append("- **{}** — {} 分".format(
                _zh_model_desc(it.get("desc", "")), it.get("cost")))

    # 关键词（中文优先黑图书馆，无则官方英文；可解析的裸链）
    fac_src = zfac_kw or kw.get("faction_keywords", [])
    kw_src = zkw or kw.get("keywords", [])
    L += ["", "## 关键词",
          "- **阵营关键词**：{}".format("，".join(_wrap(k) for k in fac_src)),
          "- **普通关键词**：{}".format("，".join(_wrap(k) for k in kw_src))]

    points_fm = {it["desc"]: it["cost"] for it in (pj.get("items") or [])
                 if isinstance(it.get("cost"), int)}
    fm = WikiPageFrontmatter(
        id=str(u["id"]), name_zh=u["name_zh"], name_en=u["name_en"],
        faction=faction_zh, type="unit", points=points_fm or None,
        version={k: v for k, v in {
            "points": "MFM {}".format(fetched) if fetched else "",
            "source": "official-db",
        }.items() if v},
        sources=[{"book": "官方结构库 db/wh40k.sqlite（Wahapedia 11版镜像 + MFM 官方点数）"}],
        updated="2026-07-23",
    )
    fm.generate_tags()
    body = escape_table_pipes("\n".join(L) + "\n")
    return WikiPage(fm=fm, body=body), drift


# ── 批量生成 ───────────────────────────────────────────────────────────

def generate_faction(conn, fid: str, wiki_root: Path) -> Dict:
    """生成一个阵营的全部单位页 → wiki/factions/<中文名>/units/。"""
    faction_zh = FACTION_DIRS.get(fid, fid)
    out_dir = wiki_root / "factions" / faction_zh / "units"
    out_dir.mkdir(parents=True, exist_ok=True)
    conn.row_factory = sqlite3.Row
    uids = [r["id"] for r in conn.execute(
        "SELECT id FROM units WHERE faction_id=? ORDER BY name_en", (fid,))]
    written = 0
    zh_pages = 0
    drift_log: List[Dict] = []
    used_slugs: Dict[str, int] = {}
    for uid in uids:
        page, drift = render_unit(conn, uid, faction_zh)
        base = slugify(page.fm.name_en or page.fm.name_zh or uid)
        used_slugs[base] = used_slugs.get(base, 0) + 1
        slug = base if used_slugs[base] == 1 else "{}-{}".format(base, used_slugs[base])
        atomic_write_text(out_dir / "{}.md".format(slug), page.to_markdown())
        written += 1
        if page.fm.name_zh:
            zh_pages += 1
        for d in drift:
            drift_log.append({"unit": page.fm.name_en, **d})
    return {"faction": faction_zh, "fid": fid, "written": written,
            "zh_pages": zh_pages, "drift": drift_log}


def generate_all(db_path: Path, wiki_root: Path,
                 only: Optional[str] = None) -> List[Dict]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        fids = [only] if only else [
            r["faction_id"] for r in conn.execute(
                "SELECT DISTINCT faction_id FROM units "
                "WHERE faction_id IS NOT NULL ORDER BY faction_id")]
        return [generate_faction(conn, fid, wiki_root) for fid in fids]
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(prog="wiki_engine.from_db")
    ap.add_argument("--db", default="db/wh40k.sqlite")
    ap.add_argument("--wiki", default="wiki")
    ap.add_argument("--faction", default=None, help="只生成指定 faction_id（默认全部）")
    args = ap.parse_args()
    reps = generate_all(Path(args.db), Path(args.wiki), only=args.faction)
    total = sum(r["written"] for r in reps)
    total_zh = sum(r["zh_pages"] for r in reps)
    total_drift = sum(len(r["drift"]) for r in reps)
    for r in reps:
        print("  {:12}({}) 写 {:>3} 页，中文 {:>3}，数值漂移 {}".format(
            r["faction"], r["fid"], r["written"], r["zh_pages"], len(r["drift"])))
    print("\n合计 {} 阵营 / {} 页（中文 {} / 英文兜底 {}），官方↔中文漂移 {} 处".format(
        len(reps), total, total_zh, total - total_zh, total_drift))
    # 持久化漂移清单（官方值已渲染，仅披露供人工核对官网↔黑图书馆分歧）
    if total_drift:
        lines = ["# from_db 数值漂移报告（官方结构库 ↔ 黑图书馆中文层）", "",
                 "> 渲染一律用官方值。以下为两源不一致处，供人工核对官网真值。", ""]
        for r in reps:
            if not r["drift"]:
                continue
            lines.append("## {}（{}）".format(r["faction"], r["fid"]))
            for d in r["drift"]:
                lines.append("- {} · {}/{}：官方 `{}` ≠ 中文 `{}`".format(
                    d.get("unit"), d.get("model", ""), d.get("field"),
                    d.get("official"), d.get("zh")))
            lines.append("")
        report = Path(args.wiki) / "factions" / "_from_db_drift.md"
        report.write_text("\n".join(lines), encoding="utf-8")
        print("  ⚠️ 漂移处官方值已胜出（渲染用官方）；清单写入 {}".format(report))


if __name__ == "__main__":
    main()
