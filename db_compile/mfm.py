"""mfm：官方 Munitorum Field Manual（mfm.warhammer-community.com）抓取与点数比对。

用户拍板的数据权威层级：**官方 GW 是最高真源，所有分数以 MFM 为准**；
Wahapedia/BSData 是它的结构化镜像（可能滞后），中文 PDF 只是翻译风格参考。
本模块把 MFM 的每单位分数抓下来，与 units.points_json 比对，产出「过期分数」报告——
这是『定期爬取官方源保数据新鲜』流水线的核心一环。

页面机制（Next.js RSC 流式渲染，无需浏览器）：
  单位分数先以 <template id="P:x"> 占位，页尾 <div hidden id="S:x">…pts…</div>
  配 $RS("S:x","P:x") 回填。parse_mfm_html 先做回填再解析，纯函数可离线测试。
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MFM_BASE = "https://mfm.warhammer-community.com"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# (unit_name_upper, tier_header, models_desc, points)
# tier_header 是 2026 梯度点数机制的档位：'YOUR UNIT COSTS'（无梯度）/
# 'YOUR 1ST UNIT COSTS' / 'YOUR 3RD + UNIT COSTS' 等——同一单位买第几个价格不同。
MfmRow = Tuple[str, str, str, int]


# 隐藏段：<div hidden id="S:x">内容</div><script>…$RS("S:x","P:x")</script>
# script 前缀允许任意 JS（首个段的 script 是 `$RS=function(…)…;$RS("S:x","P:x")`，
# 只匹配纯 $RS( 开头会漏掉它）；\1 反向引用保证内容里的 </div> 不会截断错段。
_SEG_RE = re.compile(
    r'<div hidden id="S:([0-9a-f]+)">([\s\S]*?)</div>'
    r'<script>[^<]*?\$RS\("S:\1","P:\1"\)</script>')


def _resolve_rsc_placeholders(html: str) -> str:
    """把 <div hidden id="S:x"> 段回填进 <template id="P:x"> 占位符（迭代至不动点）。

    浏览器的 $RS 是**搬运**节点：填进占位符的同时移除源块。这里必须同样删掉源块——
    否则隐藏段残留在流末尾，会被解析成它前面那个单位（通常是页面最后一个单位）的档位。
    """
    seg = {m.group(1): m.group(2) for m in _SEG_RE.finditer(html)}
    doc = _SEG_RE.sub("", html)
    for _ in range(10):
        new = re.sub(r'<template id="P:([0-9a-f]+)"></template>',
                     lambda m: seg.get(m.group(1), ""), doc)
        if new == doc:
            break
        doc = new
    return doc


# 只收这些 h3 小节里的单位价（自军现行价）。其余小节一律排除：
# 'EVERY MODEL HAS THE IMPERIUM KEYWORD' 等是**借调进别家军队**的另一套价，
# 混进来会把同一单位拆成两个矛盾价（Inquisitor 自军 55 / 借调 65）。
_KEEP_SECTIONS = {"UNITS", "FORTIFICATIONS"}


def _slice_kept_sections(doc: str) -> str:
    """取 h3 标题在 _KEEP_SECTIONS 里的小节内容（到下一个 h3 为止），拼接返回。

    找不到任何 h3 时返回整个文档（向后兼容异常版式，宁多勿漏——多出的重复
    由去重收敛，真正危险的借调价小节只在有 h3 结构的页面出现）。
    """
    heads = [(m.start(), m.end(),
              re.sub(r"<[^>]+>", "", m.group(1)).strip().upper())
             for m in re.finditer(r"<h3[^>]*>([\s\S]{1,150}?)</h3>", doc)]
    if not heads:
        return doc
    kept = []
    for i, (start, end, title) in enumerate(heads):
        if title not in _KEEP_SECTIONS:
            continue
        nxt = heads[i + 1][0] if i + 1 < len(heads) else len(doc)
        kept.append(doc[end:nxt])
    return "".join(kept)


# 单位名表头：2026-07 MFM 改版后有两种渲染。
#   旧式（本版未变价单位）：<div class="…bg-slate-500…font-bold text-xl…">NAME</div>
#   新式（本版变价单位，加涨/降价色块）：
#     <div class="…bg-{emerald|red|amber}-…font-bold text-white">
#         <span class="text-xl keep-all">NAME</span>…</div>
#   稳定信号是 text-xl（slate 直排文本）或 text-xl keep-all（色块内 span），与配色脱钩——
#   只匹配旧式会漏掉本版所有变价单位（正是 fetch 最该抓到的那批，如降价 20 的 ANGRON）。
_UNIT_HEADER_RE = re.compile(
    r'<div class="[^"]*bg-slate-500[^"]*font-bold text-xl[^"]*">([^<]+)</div>'
    r'|<span class="text-xl keep-all">([^<]+)</span>')

# 分数行：改版给变价档加了 class 着色与 ▲/▼ (±N) 变动标记前缀。
#   旧式：<li><span>N models</span><span>N pts</span></li>
#   新式：<li><span>N models</span><span class="text-emerald-600…">▼ (-20) N pts</span></li>
#   放宽第二个 span 允许任意属性 + 可选箭头前缀，只抓末尾的数字，兼容新旧。
_LI_PTS_RE = re.compile(
    r"<li><span>([^<]+)</span>"
    r'<span[^>]*>(?:[▲▼]\s*\([+\-]?\d+\)\s*)?(\d+) pts</span></li>')


def parse_mfm_html(html: str) -> List[MfmRow]:
    """MFM 阵营页 HTML → 去重的 (单位名, 梯度表头, 模型数描述, 分数) 列表。纯函数。

    只解析 UNITS/FORTIFICATIONS 小节（自军现行价），排除借调价小节与页面重复渲染。
    按单位表头（新旧两式）切块，块内按梯度分组解析分数行（新旧两式）。
    """
    doc = _slice_kept_sections(_resolve_rsc_placeholders(html))
    heads = [(m.start(), (m.group(1) or m.group(2)).strip())
             for m in _UNIT_HEADER_RE.finditer(doc)]
    rows: List[MfmRow] = []
    for i, (start, unit) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(doc)
        block = doc[start:end]
        # 单位块内按梯度分组：<div ...font-bold...>TIER 表头</div><ul>...li...</ul>
        for tier, ul in re.findall(
                r'<div class="bg-slate-200[^"]*font-bold[^"]*">([^<]+)</div>'
                r"<ul[^>]*>([\s\S]*?)</ul>", block):
            for models, pts in _LI_PTS_RE.findall(ul):
                rows.append((unit, tier.strip(), models.strip(), int(pts)))
    return list(dict.fromkeys(rows))


def is_base_tier(tier: str) -> bool:
    """是否基准梯度（第一份的价格）——与 Wahapedia/库内单一点数可比的档。

    'YOUR UNIT COSTS'（无梯度）与 'YOUR 1ST ... COSTS'（首份/前几份）算基准；
    'YOUR 2ND/3RD + ...' 是重复单位加价档，不与库内单值比。
    """
    t = tier.strip().upper()
    if t == "YOUR UNIT COSTS":
        return True
    return bool(re.match(r"YOUR 1ST\b", t))


def list_faction_slugs(html: str) -> List[str]:
    """MFM 首页 HTML → 阵营 slug 列表（/en/<slug> 链接）。"""
    slugs = re.findall(r'href="/en/([a-z0-9-]+)"', html)
    return list(dict.fromkeys(slugs))


def _fetch(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                               "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # 走环境代理
        return resp.read().decode("utf-8", errors="replace")


def fetch_faction(slug: str, max_retries: int = 4,
                  retry_sleep: float = 3.0) -> List[MfmRow]:
    """抓单个阵营页（带重试——Clash 代理偶发 SSL EOF 抖动）。"""
    last: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            return parse_mfm_html(_fetch(f"{MFM_BASE}/en/{slug}"))
        except Exception as e:  # 网络瞬断/SSL EOF：等一拍重试
            last = e
            time.sleep(retry_sleep)
    raise RuntimeError(f"抓取 {slug} 连续 {max_retries} 次失败: {last}")


def fetch_all(out_path: Path, sleep_s: float = 1.0,
              max_retries: int = 3) -> Dict[str, List[MfmRow]]:
    """抓全部阵营页 → {slug: rows}，写 JSON 到 out_path。需环境代理（HTTPS_PROXY）。

    单页抓取复用 fetch_faction（同一套重试逻辑，不再内联第二份参数不一致的循环）；
    单阵营抓不下来记入 failed 继续，不拖垮整轮。
    """
    home = _fetch(MFM_BASE + "/en")
    slugs = list_faction_slugs(home)
    if not slugs:
        raise RuntimeError("MFM 首页未解析到阵营链接——页面结构可能已变，需更新解析器")
    data: Dict[str, List[MfmRow]] = {}
    failed: List[str] = []
    for slug in slugs:
        try:
            rows = fetch_faction(slug, max_retries=max_retries)
        except RuntimeError:
            failed.append(slug)
            rows = []
        data[slug] = rows
        print(f"  {slug}: {len(rows)} 条", flush=True)
        time.sleep(sleep_s)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"source": MFM_BASE, "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
                    "failed": failed, "factions": data},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    if failed:
        print(f"  ⚠️ 抓取失败的阵营: {failed}")
    return data


# MFM 阵营页 slug → 库内 factions.id。
# 战锤各战团（BT/BA/DA/DW/SW）在 MFM 有独立页面独立定价，但库内折叠在 SM 下：
# 同名单位以通用 space-marines 页优先，战团页只补通用页没有的单位（如 Sword Brethren）。
# 战团差异价完整保留在 mfm json，等 schema 支持战团维度后再用。
MFM_SLUG_TO_FACTION: Dict[str, str] = {
    "adepta-sororitas": "AS", "adeptus-custodes": "AC", "adeptus-mechanicus": "AdM",
    "aeldari": "AE", "astra-militarum": "AM", "chaos-daemons": "CD",
    "chaos-knights": "QT", "chaos-space-marines": "CSM", "death-guard": "DG",
    "drukhari": "DRU", "emperors-children": "EC", "genestealer-cults": "GC",
    "grey-knights": "GK", "imperial-agents": "AoI", "imperial-knights": "QI",
    "leagues-of-votann": "LoV", "necrons": "NEC", "orks": "ORK",
    "space-marines": "SM", "thousand-sons": "TS", "tyranids": "TYR",
    "tau-empire": "TAU", "world-eaters": "WE",
    "titan-legions": "TL", "chaos-titan-legions": "TL",
    # SM 战团页（优先级低于 space-marines，见 _rows_by_faction）
    "black-templars": "SM", "blood-angels": "SM", "dark-angels": "SM",
    "deathwatch": "SM", "space-wolves": "SM",
}
_SM_GENERIC_SLUG = "space-marines"

FactionRows = Dict[str, List[MfmRow]]  # slug → rows


def _rows_by_faction(factions: FactionRows) -> Dict[Tuple[str, str],
                                                    List[Tuple[str, str, int]]]:
    """{slug: rows} → {(faction_id, unit_lower): [(tier, models, pts)]}，
    同 faction 同单位以先处理的 slug 为准（space-marines 通用页排最前）。"""
    slugs = sorted(factions.keys(),
                   key=lambda s: (0 if s == _SM_GENERIC_SLUG else 1, s))
    out: Dict[Tuple[str, str], List[Tuple[str, str, int]]] = {}
    for slug in slugs:
        fid = MFM_SLUG_TO_FACTION.get(slug)
        if fid is None:
            continue
        this_page: Dict[Tuple[str, str], List[Tuple[str, str, int]]] = {}
        for unit_u, tier, models, pts in factions[slug]:
            this_page.setdefault((fid, unit_u.strip().lower()),
                                 []).append((tier, models, pts))
        for key, rows in this_page.items():
            out.setdefault(key, rows)  # 先到先得：通用页优先于战团页
    return out


def _load_db_units(conn) -> Dict[Tuple[str, str], List[Tuple[str, str, Optional[str]]]]:
    """{(faction_id, name_lower): [(unit_id, name_en, points_json), ...]}

    list 值保留同阵营同名重复行（Wahapedia 跨战团重复收录，如 SM Impulsor×2），
    与 apply_points 的 units_map 同构。旧的 dict 推导 last-write-wins 会把重复行
    折叠掉——apply 更新了全部行而 check 只看最后一行，任何一行残留旧值都漏检。
    """
    out: Dict[Tuple[str, str], List[Tuple[str, str, Optional[str]]]] = {}
    for uid, fid, name, pj in conn.execute(
            "SELECT id, faction_id, name_en, points_json FROM units "
            "WHERE name_en IS NOT NULL"):
        out.setdefault((fid or "", name.strip().lower()), []).append((uid, name, pj))
    return out


def check_points(db_path, factions: FactionRows) -> Dict:
    """MFM 分数 vs units.points_json 按（阵营+单位+模型数）比对。

    只比**基准梯度**（is_base_tier）——库内是单值，与重复单位加价档不可比。
    返回 {compared, agree, diffs[{unit,models,db,mfm}], mfm_only[], tiered_units}。
    """
    by_faction = _rows_by_faction(factions)
    conn = sqlite3.connect(str(db_path))
    try:
        db_units = _load_db_units(conn)
    finally:
        conn.close()

    compared = agree = 0
    diffs: List[Dict] = []
    mfm_only: List[str] = []
    tiered_units = set()
    for (fid, unit_l), rows in by_faction.items():
        for tier, _m, _p in rows:
            if not is_base_tier(tier):
                tiered_units.add(unit_l.upper())
                break
        hits = db_units.get((fid, unit_l))
        if hits is None:
            mfm_only.append(unit_l.upper())
            continue
        # 遍历同 (阵营, 名字) 的全部重复行逐一比对——任何一行残留旧值都要报
        for _uid, name, pj_raw in hits:
            try:
                items = (json.loads(pj_raw) or {}).get("items") or []
            except (json.JSONDecodeError, TypeError):
                continue
            costs = {(it.get("desc") or "").strip().lower(): it.get("cost")
                     for it in items if isinstance(it.get("cost"), int)}
            for tier, models, pts in rows:
                if not is_base_tier(tier):
                    continue
                db_cost = costs.get(models.strip().lower())
                if db_cost is None:
                    continue  # 模型档位描述不一致，不强行比
                compared += 1
                if db_cost == pts:
                    agree += 1
                else:
                    diffs.append({"unit": name, "models": models,
                                  "db": db_cost, "mfm": pts})
    return {"compared": compared, "agree": agree, "diffs": diffs,
            "mfm_only": sorted(set(mfm_only)), "tiered_units": sorted(tiered_units)}


def apply_points(db_path, factions: FactionRows,
                 fetched_at: Optional[str] = None) -> Dict:
    """把官方 MFM 分数应用进 units.points_json（官方为最高真源），按阵营匹配。

    - 基准梯度：更新 items[].cost（按模型数描述匹配），库里没有的档位补进 items
    - 顶层 points 修正为基准档最小值（Wahapedia 导入的各档累加和是错误语义）
    - 全部梯度（含加价档）存入 points_json["mfm"]["tiers"]，带 fetched_at 溯源
    - 只动 MFM 里有的单位；注意 `db_compile build` 重建会覆盖，重建后需重跑本命令
    """
    by_faction = _rows_by_faction(factions)
    conn = sqlite3.connect(str(db_path))
    updated = matched = 0
    try:
        # Python 侧建匹配表：SQLite lower() 只降 ASCII（Ûthar 匹配不上），
        # 必须与 check 同用 Python .lower()；list 值保留同阵营同名重复行
        # （Wahapedia 跨战团重复收录，如 SM Impulsor×2）——全部更新，漏一行
        # 就会在 check 里读到旧值。
        units_map: Dict[Tuple[str, str], List[Tuple[str, Optional[str]]]] = {}
        for uid, ufid, name, pj_raw in conn.execute(
                "SELECT id, faction_id, name_en, points_json FROM units "
                "WHERE name_en IS NOT NULL"):
            units_map.setdefault(
                (ufid or "", name.strip().lower()), []).append((uid, pj_raw))
        for (fid, unit_l), rows in by_faction.items():
            hits = units_map.get((fid, unit_l))
            if not hits:
                continue
            matched += 1
            base = {models.strip().lower(): pts
                    for tier, models, pts in rows if is_base_tier(tier)}
            any_changed = False
            for uid, pj_raw in hits:
                try:
                    pj = json.loads(pj_raw) if pj_raw else {}
                except (json.JSONDecodeError, TypeError):
                    pj = {}
                items = pj.get("items") or []
                changed = False
                seen_descs = set()
                for it in items:
                    d = (it.get("desc") or "").strip().lower()
                    seen_descs.add(d)
                    if d in base and it.get("cost") != base[d]:
                        it["cost"] = base[d]
                        changed = True
                for d, pts in base.items():
                    if d not in seen_descs:
                        items.append({"line": None, "desc": d, "cost": pts})
                        changed = True
                new_points = min(base.values()) if base else pj.get("points")
                if new_points != pj.get("points"):
                    changed = True
                pj["items"] = items
                pj["points"] = new_points
                pj["mfm"] = {
                    "fetched_at": fetched_at,
                    "tiers": [{"tier": t, "models": m, "cost": p}
                              for t, m, p in rows],
                }
                conn.execute("UPDATE units SET points_json = ? WHERE id = ?",
                             (json.dumps(pj, ensure_ascii=False), uid))
                any_changed = any_changed or changed
            if any_changed:
                updated += 1
        conn.commit()
    finally:
        conn.close()
    return {"units_matched": matched, "units_updated": updated}
