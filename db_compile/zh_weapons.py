"""db_compile/zh_weapons.py —— 把黑图书馆的中文武器名**确定性地**落到 weapons.name_zh。

为什么要有这一层（2026-07-25）：
图鉴原先在渲染时把黑图的中文武器列表按**位置**贴到英文武器行上，只用"数量相等"当守卫。
实测这个守卫拦不住——黑图的武器顺序与库内顺序不同，数量却常常恰好相等。战斗修女小队
就因此在中文模式下把「爆弹手枪」贴到了 A=D6/BS=N/A/S=4 这一行上（那是 Ministorum
hand flamer 的数值）。**数值对、名字错**是最坏的一种错：用户没有任何线索能察觉。

改成离线、可复核、可回归的三遍配对，结果落库（weapons.name_zh），渲染层只读不猜：

  Pass A 数值指纹：同一单位、同一 kind 内，(射程,A,命中,S,AP,D) 六元组唯一命中才配。
         黑图是十版素材、11 版改过数值的武器自然配不上——配不上就不配，保英文。
  Pass B 残差唯一：A 之后某 kind 内英文与中文各只剩一个未配对 → 它俩必然是一对。
  Pass C 术语表：A/B 攒出的 (阵营, 英文名) → 中文名 多数派，回填**其它单位**的同名武器
         （爆弹手枪/爆矢手枪/瘟疫爆弹手枪 这类阵营风格差异靠阵营键区分；跨阵营只在
         全库译名唯一时才敢用）。

一条也不猜：歧义、冲突、配不上，一律留空 → 图鉴显示英文（诚实）。幂等：只填空值。
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Pass C 的把关阈值：阵营内多数派要够压倒；跨阵营要样本够多且多数派同样压倒
# （少数派多是同义风格差异——格斗武器/近战武器、爆弹/爆矢——不是错译；但样本太少时
#  一次错配就能当选，所以跨阵营额外要求 ≥3 次观测）
_FACTION_MAJORITY = 0.8
_GLOBAL_MAJORITY = 0.8
_GLOBAL_MIN_OBS = 3

# 人工译名真源（黑图没有的词，人工按黑图风格补译）——git 跟踪，DB 里只是投影
OVERRIDES_PATH = Path(__file__).resolve().parent / "zh_weapon_overrides.json"
KEYWORD_OVERRIDES_PATH = Path(__file__).resolve().parent / "zh_keyword_overrides.json"

# 参数化 USR：同一族的写法必须整齐（黑图自己混用"反步兵/针对步兵"，我们统一取多数派"反X"）
_ANTI_TARGET = {
    "INFANTRY": "步兵", "VEHICLE": "载具", "MONSTER": "怪物", "FLY": "飞行",
    "PSYKER": "灵能者", "CHARACTER": "角色", "TITANIC": "泰坦", "DAEMON": "恶魔",
    "CHAOS": "混沌", "WALKER": "步行者", "EPIC HERO": "史诗英雄", "XENOS": "异形",
    "IMPERIUM": "帝国", "GRENADES": "手雷", "MOUNTED": "骑乘", "SWARM": "虫群",
    "TYRANIDS": "泰伦虫族",
}
_PARAM_RULES = [
    (re.compile(r"^ANTI-(.+?)\s+(\d\+)$"), lambda m: (
        "反" + _ANTI_TARGET[m.group(1).strip()] + m.group(2)
        if m.group(1).strip() in _ANTI_TARGET else None)),
    (re.compile(r"^RAPID FIRE (.+)$"), lambda m: "速射" + m.group(1).replace(" ", "")),
    (re.compile(r"^MELTA (.+)$"), lambda m: "热熔" + m.group(1).replace(" ", "")),
    (re.compile(r"^SUSTAINED HITS (.+)$"), lambda m: "连击" + m.group(1).replace(" ", "")),
    # CLEAVE 是 11 版新增（近战版爆炸），黑图十版语料没有它——学习值必然错配，
    # 只能走规则 + 人工真源（译名据 data/11版40K通用技能速查表.pdf 24.06「横扫」）
    (re.compile(r"^CLEAVE (.+)$"), lambda m: "横扫" + m.group(1).replace(" ", "")),
]


def _rule_translate(term_en: str) -> Optional[str]:
    """参数化 USR（ANTI-X N+ / RAPID FIRE X / MELTA X / SUSTAINED HITS X）→ 中文。"""
    for pat, fn in _PARAM_RULES:
        m = pat.match(term_en.strip().upper())
        if m:
            got = fn(m)
            if got:
                return got
    return None


def _load_keyword_overrides() -> Dict[str, str]:
    if not KEYWORD_OVERRIDES_PATH.exists():
        return {}
    try:
        data = json.loads(KEYWORD_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    terms = data.get("keywords") if isinstance(data, dict) else None
    return {str(k).upper(): str(v) for k, v in (terms or {}).items() if k and v}


# CJK Radicals Supplement（U+2E80–U+2EF3）没有 NFKC 分解，只能显式对照。
# 康熙部首区（U+2F00–U+2FD5）走 NFKC 即可，不必列。列表按语料实测扩充，
# 未收录的残留由 build 报告 leftover_radicals 吼出来，不静默放行。
_RADICAL_FALLBACK = {
    "⻛": "风",   # CJK RADICAL C-SIMPLIFIED WIND，实测语料里 21 处「⻛暴爆弹枪」
    "⻆": "角",   # CJK RADICAL SIMPLIFIED HORN
    # 只收**逐个用 unicodedata.name 核对过**的；凭印象猜映射＝制造新的错译，
    # 未收录的会进 leftover_radicals 报告，见到再核对补。
}


def clean_zh_name(s: str) -> str:
    """黑图原文里的脏字符归一：CJK 部首兼容字（⻛≠风）、半角括号、多余空格。

    实测黑图有 21 处「⻛暴爆弹枪」——那个 ⻛ 是 U+2EDB 部首形，不是 U+98CE 风，
    搜索、去重、对账全会把它当成另一个词。
    """
    out = []
    for ch in s:
        cp = ord(ch)
        if ch in _RADICAL_FALLBACK:
            out.append(_RADICAL_FALLBACK[ch])
        elif 0x2E80 <= cp <= 0x2FDF:
            out.append(unicodedata.normalize("NFKC", ch))   # 康熙部首区可折
        else:
            out.append(ch)
    txt = "".join(out).replace("(", "（").replace(")", "）")
    return re.sub(r"\s+", "", txt).strip()


def leftover_radicals(db_path) -> Dict[str, int]:
    """归一后仍残留的部首兼容字（正常应为空）——出现就说明对照表要补。"""
    conn = sqlite3.connect(str(db_path))
    try:
        found: Counter = Counter()
        for (nz,) in conn.execute(
                "SELECT name_zh FROM weapons WHERE name_zh IS NOT NULL"):
            for ch in nz or "":
                if 0x2E80 <= ord(ch) <= 0x2FDF:
                    found[ch] += 1
        return dict(found)
    finally:
        conn.close()


def _norm_stat(v: Any) -> str:
    """'D6' / '2' / '-1' / 'N/A' / '3+' / '24"' → 可比较的规范串。

    库里命中存 '3'、黑图存 '3+'；射程库里可能带引号——都归一掉。
    """
    s = str(v if v is not None else "").strip().upper().replace(" ", "")
    s = s.replace("－", "-").replace("＋", "+").replace('"', "").replace("”", "")
    if s in ("", "N/A", "NA", "-", "—", "无"):
        return ""
    if s.endswith("+"):
        s = s[:-1]
    return s


def _sig_en(row: Tuple) -> Tuple[str, ...]:
    rng, a, bs, s, ap, d = row
    return tuple(_norm_stat(x) for x in (rng, a, bs, s, ap, d))


def _sig_zh(w: Dict[str, Any]) -> Tuple[str, ...]:
    return tuple(_norm_stat(w.get(k)) for k in
                 ("射程", "攻击次数", "命中", "造伤", "破甲", "伤害"))


def _kind(range_txt: Optional[str]) -> str:
    return "melee" if (range_txt or "").strip().lower() == "melee" else "ranged"


def _load_zh_weapons(raw: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    try:
        data = json.loads(raw) if raw else None
    except (json.JSONDecodeError, TypeError):
        return {"ranged": [], "melee": []}
    if not isinstance(data, dict):
        return {"ranged": [], "melee": []}
    return {"ranged": data.get("射击武器") or [], "melee": data.get("近战武器") or []}


def _ensure_column(conn: sqlite3.Connection) -> None:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(weapons)")]
    if "name_zh" not in cols:      # 老库兜底；现行 schema 已有此列
        conn.execute("ALTER TABLE weapons ADD COLUMN name_zh TEXT")


def _pair_unit(
    en_rows: List[Tuple[int, str, str, Tuple[str, ...]]],
    zh_rows: List[Dict[str, Any]],
) -> List[Tuple[int, str]]:
    """单个单位内配对，返回 [(weapon_rowid, 中文名)]。只产出可确信的配对。"""
    out: List[Tuple[int, str]] = []
    for kind in ("ranged", "melee"):
        ens = [r for r in en_rows if r[2] == kind]
        zhs = [w for w in zh_rows if isinstance(w, dict)]
        zhs = [w for w in zhs if w.get("_kind") == kind]
        if not ens or not zhs:
            continue
        # Pass A：数值指纹唯一命中
        by_sig: Dict[Tuple[str, ...], List[Tuple[int, str, str, Tuple]]] = defaultdict(list)
        for r in ens:
            by_sig[r[3]].append(r)
        used_en, used_zh = set(), set()
        for zi, zw in enumerate(zhs):
            nm = str(zw.get("name") or "").strip()
            if not nm:
                continue
            cands = [r for r in by_sig.get(_sig_zh(zw), []) if r[0] not in used_en]
            # 同签名多个英文行 → 无法确信是哪一把，跳过（宁缺毋错）
            if len(cands) == 1:
                out.append((cands[0][0], nm))
                used_en.add(cands[0][0])
                used_zh.add(zi)
        # Pass B：两边各只剩一个 → 必然成对
        rest_en = [r for r in ens if r[0] not in used_en]
        rest_zh = [(i, w) for i, w in enumerate(zhs)
                   if i not in used_zh and str(w.get("name") or "").strip()]
        if len(rest_en) == 1 and len(rest_zh) == 1:
            out.append((rest_en[0][0], str(rest_zh[0][1]["name"]).strip()))
    return out


def _dedupe_within_unit(
    assign: List[Tuple[int, str]], en_of: Dict[int, str],
) -> List[Tuple[int, str]]:
    """同一单位里不许两把**不同**英文武器共用一个中文名——必有一个是错配，两个都撤。

    实测逮到 Ministorum flamer / Ministorum hand flamer 双双译成「教廷火焰喷射器」。
    宁可两行都留英文，也不能让用户看到两把同名武器却是不同数值。
    """
    by_zh: Dict[str, set] = defaultdict(set)
    for rid, zh in assign:
        by_zh[zh].add((en_of.get(rid) or "").strip().lower())
    bad = {zh for zh, ens in by_zh.items() if len(ens) > 1}
    return [(rid, zh) for rid, zh in assign if zh not in bad]


def build_zh_weapon_names(db_path, apply: bool = True) -> Dict[str, Any]:
    """三遍配对 + 人工译名叠加，重建 weapons.name_zh。apply=False 只统计不写库。

    **整列是投影**：每次先清空再重建（人工译名存 zh_weapon_overrides.json，git 真源），
    所以重跑幂等、改判据后不会留下上一版的残留。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_column(conn)
        if apply:
            conn.execute("UPDATE weapons SET name_zh = NULL")
        conn.row_factory = None
        details = conn.execute(
            "SELECT canonical_id, weapons_json FROM unit_zh_detail").fetchall()
        fac_of = {u: f for u, f in conn.execute(
            "SELECT id, faction_id FROM units")}

        direct: List[Tuple[int, str]] = []
        gloss: Dict[Tuple[str, str], Counter] = defaultdict(Counter)   # (faction, en) -> zh
        gloss_all: Dict[str, Counter] = defaultdict(Counter)           # en -> zh（跨阵营）

        for cid, wj in details:
            zh = _load_zh_weapons(wj)
            zh_rows: List[Dict[str, Any]] = []
            for kind in ("ranged", "melee"):
                for w in zh[kind]:
                    if isinstance(w, dict):
                        w = dict(w)
                        w["_kind"] = kind
                        zh_rows.append(w)
            en_rows = [
                (rid, nen, _kind(rng), _sig_en((rng, a, bs, s, ap, d)))
                for rid, nen, rng, a, bs, s, ap, d in conn.execute(
                    "SELECT rowid, name_en, range, a, bs_ws, s, ap, d "
                    "FROM weapons WHERE unit_id = ? ORDER BY id", (cid,))
            ]
            if not en_rows or not zh_rows:
                continue
            en_name_of = {r[0]: r[1] for r in en_rows}
            paired = [(rid, clean_zh_name(nm)) for rid, nm in _pair_unit(en_rows, zh_rows)]
            for rid, nm in _dedupe_within_unit(paired, en_name_of):
                direct.append((rid, nm))
                en = (en_name_of.get(rid) or "").strip()
                if en:
                    gloss[(fac_of.get(cid) or "", en)][nm] += 1
                    gloss_all[en][nm] += 1

        # Pass C：术语表回填其它单位的同名武器（阵营内多数派；跨阵营须全库压倒性唯一）
        fac_pick = {}
        for (fac, en), cnt in gloss.items():
            zh, n = cnt.most_common(1)[0]
            if n / sum(cnt.values()) >= _FACTION_MAJORITY:
                fac_pick[(fac, en)] = zh
        all_pick = {}
        for en, cnt in gloss_all.items():
            zh, n = cnt.most_common(1)[0]
            tot = sum(cnt.values())
            # 全库只见过一种译法 → 哪怕只观测到 1 次也可用（没有竞争者可选错）；
            # 见过多种译法 → 要样本 ≥3 且多数派 ≥80%，防一次错配当选
            if len(cnt) == 1 or (tot >= _GLOBAL_MIN_OBS and n / tot >= _GLOBAL_MAJORITY):
                all_pick[en] = zh

        direct_ids = {rid for rid, _ in direct}
        by_gloss: List[Tuple[int, str]] = []
        for rid, uid, nen in conn.execute(
                "SELECT rowid, unit_id, name_en FROM weapons"):
            if rid in direct_ids or not nen:
                continue
            en = nen.strip()
            zh = fac_pick.get((fac_of.get(uid) or "", en)) or all_pick.get(en)
            if zh:
                by_gloss.append((rid, zh))

        # 全量再过一次「同单位内不许两把不同武器同名」——术语表回填也可能撞车
        unit_of, en_of = {}, {}
        for rid, uid, nen in conn.execute("SELECT rowid, unit_id, name_en FROM weapons"):
            unit_of[rid], en_of[rid] = uid, nen
        per_unit: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        for rid, zh in direct + by_gloss:
            per_unit[unit_of.get(rid)].append((rid, zh))
        final: List[Tuple[int, str]] = []
        dropped = 0
        for uid, items in per_unit.items():
            kept = _dedupe_within_unit(items, en_of)
            dropped += len(items) - len(kept)
            final.extend(kept)

        # 人工译名真源叠加（黑图没有的词），最后写、优先级最高
        overrides = _load_overrides()
        ov_applied = 0
        if overrides:
            for rid, nen in conn.execute("SELECT rowid, name_en FROM weapons"):
                zh = overrides.get((nen or "").strip())
                if zh:
                    final.append((rid, clean_zh_name(zh)))
                    ov_applied += 1

        if apply:
            conn.executemany(
                "UPDATE weapons SET name_zh = ? WHERE rowid = ?",
                [(zh, rid) for rid, zh in final])
            conn.commit()

        total = conn.execute("SELECT COUNT(*) FROM weapons").fetchone()[0]
        filled = conn.execute(
            "SELECT COUNT(*) FROM weapons WHERE name_zh IS NOT NULL AND name_zh <> ''"
        ).fetchone()[0]
        return {
            "weapons_total": total,
            "paired_direct": len(direct),
            "paired_glossary": len(by_gloss),
            "dropped_by_dedupe": dropped,
            "overrides_applied": ov_applied,
            "glossary_terms": len(fac_pick) + len(all_pick),
            "filled_now": filled if apply else None,
        }
    finally:
        conn.close()


def build_keyword_glossary(db_path, apply: bool = True) -> Dict[str, Any]:
    """武器关键词（USR）中英对照表：只从**单对单**的行学，避免又一次位置错配。

    一行英文关键词恰好 1 个、对应的黑图 skill 也恰好 1 个 → 这对关系无歧义。
    多关键词行（1503 行）一律不用：那需要在列表内部再对齐一次，正是错位的老路。
    实测单对单能覆盖 53 个 USR（PISTOL→手枪 377 次、BLAST→爆炸 231 次…），
    而 USR 本就是封闭小词表，够用。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS zh_keyword_glossary (
                term_en TEXT PRIMARY KEY,
                term_zh TEXT NOT NULL,
                obs     INTEGER DEFAULT 0
            )""")
        pairs: Dict[str, Counter] = defaultdict(Counter)
        for cid, wj in conn.execute(
                "SELECT canonical_id, weapons_json FROM unit_zh_detail"):
            zh = _load_zh_weapons(wj)
            zh_rows: List[Dict[str, Any]] = []
            for kind in ("ranged", "melee"):
                for w in zh[kind]:
                    if isinstance(w, dict):
                        w = dict(w)
                        w["_kind"] = kind
                        zh_rows.append(w)
            en_rows = [
                (rid, nen, _kind(rng), _sig_en((rng, a, bs, s, ap, d)))
                for rid, nen, rng, a, bs, s, ap, d in conn.execute(
                    "SELECT rowid, name_en, range, a, bs_ws, s, ap, d FROM weapons "
                    "WHERE unit_id = ? ORDER BY id", (cid,))
            ]
            if not en_rows or not zh_rows:
                continue
            kw_of = {rid: kj for rid, kj in conn.execute(
                "SELECT rowid, keywords_json FROM weapons WHERE unit_id = ?", (cid,))}
            zh_by_name = {clean_zh_name(str(w.get("name") or "")): w for w in zh_rows}
            for rid, nm in _pair_unit(en_rows, zh_rows):
                try:
                    en_kw = json.loads(kw_of.get(rid) or "[]") or []
                except (json.JSONDecodeError, TypeError):
                    en_kw = []
                zw = zh_by_name.get(clean_zh_name(nm)) or {}
                # 英文一格常是「heavy, devastating wounds」逗号串，先拆平
                en_flat = [t.strip() for k in en_kw for t in str(k).split(",") if t.strip()]
                zh_flat = [t.strip() for k in (zw.get("skill") or [])
                           for t in str(k).split(",") if t.strip()]
                if len(en_flat) == 1 and len(zh_flat) == 1:
                    pairs[en_flat[0].upper()][clean_zh_name(zh_flat[0])] += 1

        picked: Dict[str, Tuple[str, int]] = {}
        for en, cnt in pairs.items():
            zh, n = cnt.most_common(1)[0]
            tot = sum(cnt.values())
            if len(cnt) == 1 or n / tot >= _GLOBAL_MAJORITY:
                picked[en] = (zh, tot)
        # 库里出现过的全部关键词都要有着落：先规则、再人工层（都盖过学习值，保证同族整齐）
        seen: set = set()
        for (kj,) in conn.execute("SELECT keywords_json FROM weapons"):
            try:
                for k in json.loads(kj or "[]") or []:
                    for t in str(k).split(","):
                        if t.strip():
                            seen.add(t.strip().upper())
            except (json.JSONDecodeError, TypeError):
                continue
        n_rule = 0
        for term in seen:
            got = _rule_translate(term)
            if got:
                picked[term] = (got, 0)
                n_rule += 1
        overrides = _load_keyword_overrides()
        for term, zh in overrides.items():
            picked[term] = (clean_zh_name(zh), 0)

        # 撞名护栏：一个中文名只能属于一个英文词条。两个词条撞同一个中文名时，
        # 权威来源（obs=0，来自参数化规则或人工真源）留下，学习值（obs>0）丢弃。
        #
        # 为什么需要：单对单学习在**两源本身有漂移**的单位上会学出「张冠李戴」——
        # 泰伦 Norn Assimilator 的 Toxinjector Harpoon 英文带 HARPOONED，而黑图那张
        # 中文兵牌同位置写的是「额外攻击」，于是 HARPOONED→额外攻击 被当成 1 次观测
        # 学了下来，与 EXTRA ATTACKS 撞名。单次观测 + 撞名 = 几乎必错，且这种错
        # **看起来是中文的**，比留英文更难被发现（用户看到「额外攻击」不会起疑）。
        dropped: List[Tuple[str, str]] = []
        by_zh: Dict[str, List[str]] = defaultdict(list)
        for en, (zh, _n) in picked.items():
            by_zh[zh].append(en)
        for zh, terms in by_zh.items():
            if len(terms) < 2:
                continue
            authoritative = [t for t in terms if picked[t][1] == 0]
            if not authoritative:
                continue          # 全是学习值：无从裁决，保留并交给 report 披露
            for t in terms:
                if picked[t][1] > 0:
                    dropped.append((t, zh))
                    del picked[t]

        if apply:
            conn.execute("DELETE FROM zh_keyword_glossary")
            conn.executemany(
                "INSERT INTO zh_keyword_glossary (term_en, term_zh, obs) VALUES (?,?,?)",
                [(en, clean_zh_name(zh), n) for en, (zh, n) in picked.items()])
            conn.commit()
        return {"terms": len(picked), "candidates": len(pairs),
                "by_rule": n_rule, "by_override": len(overrides),
                "dropped_collisions": sorted(dropped),
                "untranslated": sorted(seen - set(picked))[:40]}
    finally:
        conn.close()


def missing_terms(db_path) -> List[Tuple[str, int, str]]:
    """现役单位里仍缺中文名的武器：[(英文名, 出现行数, 举例单位)]，按出现次数降序。

    这是"还要人工补译多少"的工单。只看现役单位——传承/福基世界条目没人玩，不值当。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        cur_ids = set()
        for uid, pj in conn.execute("SELECT id, points_json FROM units"):
            try:
                if pj and (json.loads(pj) or {}).get("mfm"):
                    cur_ids.add(uid)
            except (json.JSONDecodeError, TypeError):
                continue
        cnt: Counter = Counter()
        sample: Dict[str, str] = {}
        for uid, nen, nz, unm in conn.execute(
                "SELECT w.unit_id, w.name_en, w.name_zh, u.name_en FROM weapons w "
                "JOIN units u ON u.id = w.unit_id"):
            if uid in cur_ids and nen and not (nz or "").strip():
                cnt[nen] += 1
                sample.setdefault(nen, unm or "")
        return [(en, n, sample.get(en, "")) for en, n in cnt.most_common()]
    finally:
        conn.close()


def _load_overrides() -> Dict[str, str]:
    """人工译名真源：{英文武器名: 中文名}。文件不存在＝还没补译，不是错误。"""
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    terms = data.get("weapons") if isinstance(data, dict) else None
    return {str(k): str(v) for k, v in (terms or {}).items() if k and v}


def coverage_report(db_path) -> Dict[str, Any]:
    """中文武器名覆盖率：全库 / 现役单位（现役=在官方现行 MFM 点数表里）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        cur_ids = set()
        for uid, pj in conn.execute("SELECT id, points_json FROM units"):
            try:
                if pj and (json.loads(pj) or {}).get("mfm"):
                    cur_ids.add(uid)
            except (json.JSONDecodeError, TypeError):
                continue
        tot = zh = cur_tot = cur_zh = 0
        for uid, nz in conn.execute("SELECT unit_id, name_zh FROM weapons"):
            has = bool(nz and nz.strip())
            tot += 1
            zh += has
            if uid in cur_ids:
                cur_tot += 1
                cur_zh += has
        return {"all": (zh, tot), "current": (cur_zh, cur_tot)}
    finally:
        conn.close()
