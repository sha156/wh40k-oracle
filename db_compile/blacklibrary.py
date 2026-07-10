"""blacklibrary：黑图书馆小程序开放 API 中英对照源。

blackforum.czmakj.com 后端无签名墙，直连枚举 40K 单位（中英名+分数+完整中文 datasheet）。
是补 aliases 中文别名层的权威源（比 LLM 机翻可靠：中英都是官方汉化组译名）。

requests 必须 trust_env=False——抓包时 Fiddler 会开系统代理并劫持导致 SSL 失败。
fetch 结果缓存到 db_sources/blacklibrary/units.json，供 --offline 重建复用。
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

LIST_API = "https://blackforum.czmakj.com/app/manager/forum/unit/list"
DETAIL_API = "https://blackforum.czmakj.com/app/unit/detail"
GAME_ID_40K = 2
PAGE_SIZE = 50
_HDR = {"Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

DEFAULT_CACHE = Path("db_sources/blacklibrary/units.json")
DEFAULT_DETAILS_CACHE = Path("db_sources/blacklibrary/details.json")


def fetch_unit_list() -> List[dict]:
    """全量翻页拉 40K 单位。按页是否满判结束（不依赖易失的 total 字段，防早停）。

    - 「最后一页」= 响应带 data 键且为空列表 → 正常结束；
      「业务错误载荷」= 响应根本没有 data 键 → 抛 RuntimeError，不能当翻页结束
      （否则接口报错会被误判为『抓完了』，静默漏抓整库）。
    - 结束时用接口宣称的 total 对账，不一致打显眼差额警告。
    """
    sess = requests.Session()
    sess.trust_env = False
    units: List[dict] = []
    seen = set()
    total = None
    page = 1
    while page <= 60:
        for attempt in range(3):
            try:
                j = sess.post(LIST_API, json={"pageNum": page, "pageSize": PAGE_SIZE,
                              "gameId": GAME_ID_40K, "unitName": ""},
                              headers=_HDR, timeout=25).json()
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1.5)
        if "data" not in j:
            raise RuntimeError(
                f"黑图书馆接口返回业务错误载荷（第 {page} 页无 data 键）："
                f"{str(j)[:200]}")
        data = j["data"] or []
        if total is None and j.get("total"):
            total = j.get("total")
        if not data:
            break
        for u in data:
            if u.get("id") not in seen:
                seen.add(u.get("id"))
                units.append(u)
        if len(data) < PAGE_SIZE:
            break
        page += 1
    if total is not None and len(units) != total:
        print(f"  ⚠️ 黑图书馆抓取对账不符：目标 {total} vs 实际 {len(units)}"
              f"（差额 {total - len(units)}）", flush=True)
    return units


def load_or_fetch_units(cache_path: Optional[Path] = None,
                        offline: bool = False) -> Tuple[List[dict], str]:
    """在线抓取并刷新缓存；离线或抓取失败时读缓存。返回 (units, 来源说明)。"""
    cache_path = Path(cache_path) if cache_path else DEFAULT_CACHE
    if offline:
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8")), "缓存(offline)"
        return [], "无缓存(offline)"
    try:
        units = fetch_unit_list()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(units, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        return units, "在线抓取"
    except Exception as exc:
        if cache_path.exists():
            return (json.loads(cache_path.read_text(encoding="utf-8")),
                    f"抓取失败复用缓存({type(exc).__name__})")
        raise


def units_to_pairs(units: List[dict]) -> List[Tuple[str, str]]:
    """(unitName 中文, unitEnglishName 英文) 对。"""
    return [(u.get("unitName") or "", u.get("unitEnglishName") or "") for u in units]


# ── 中文原生 datasheet 层（/app/unit/detail 抓取产物）──────────────────

def load_details(cache_path: Optional[Path] = None) -> List[dict]:
    """读中文 datasheet 缓存（scripts/fetch_blacklibrary_details.py 产物）。无则返回空。"""
    cache_path = Path(cache_path) if cache_path else DEFAULT_DETAILS_CACHE
    if not cache_path.exists():
        return []
    return json.loads(cache_path.read_text(encoding="utf-8"))


def _clean_stats(detail: dict) -> list:
    """滤掉黑图书馆属性数组尾部的空占位行（unitName='' 且 m==0）。"""
    out = []
    for m in (detail.get("属性") or []):
        if not (m.get("unitName") or "").strip() and str(m.get("m")) in ("0", "0.0"):
            continue
        out.append(m)
    return out


def _en_to_id_map(conn: sqlite3.Connection) -> Dict[str, str]:
    return {(n or "").strip().lower(): c
            for c, n in conn.execute("SELECT id, name_en FROM units") if n}


def populate_zh_details(db_path, details: List[dict]) -> Dict[str, int]:
    """把黑图书馆中文 datasheet 灌进 `unit_zh_detail` 表（canonical_id 经 name_en 匹配）。

    英文=权威真值不动；本表是叠加的中文原生内容层（属性/能力/武器/简介）。
    幂等：建表 IF NOT EXISTS + 先删本源旧行。返回 {records, matched, unmatched, no_detail}。
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unit_zh_detail (
                canonical_id TEXT PRIMARY KEY,
                name_zh      TEXT,
                faction_zh   TEXT,
                score        INTEGER,
                stats_json   TEXT,
                abilities_json TEXT,
                weapons_json TEXT,
                intro_json   TEXT,
                source       TEXT DEFAULT 'blackforum'
            )""")
        conn.execute("DELETE FROM unit_zh_detail WHERE source = 'blackforum'")
        en2id = _en_to_id_map(conn)
        matched = no_detail = 0
        for r in details:
            en = (r.get("name_en") or "").strip().lower()
            cid = en2id.get(en)
            if not cid:
                continue
            det = r.get("detail")
            if not det:
                no_detail += 1
                continue
            weapons = {"射击武器": det.get("射击武器"), "近战武器": det.get("近战武器")}
            conn.execute(
                "INSERT OR REPLACE INTO unit_zh_detail "
                "(canonical_id, name_zh, faction_zh, score, stats_json, "
                " abilities_json, weapons_json, intro_json, source) "
                "VALUES (?,?,?,?,?,?,?,?, 'blackforum')",
                (cid, r.get("name_zh"), r.get("faction_zh"), r.get("score"),
                 json.dumps(_clean_stats(det), ensure_ascii=False),
                 json.dumps(det.get("能力"), ensure_ascii=False),
                 json.dumps(weapons, ensure_ascii=False),
                 json.dumps(det.get("简介"), ensure_ascii=False)))
            matched += 1
        conn.commit()
        return {"records": len(details), "matched": matched,
                "unmatched": len(details) - matched - no_detail, "no_detail": no_detail}
    finally:
        conn.close()


def fill_name_zh(db_path, units: List[dict]) -> Dict[str, int]:
    """用黑图书馆中文名补 units.name_zh 的空缺（不覆盖已有值，英文权威不动）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        en2id = _en_to_id_map(conn)
        filled = 0
        for u in units:
            en = (u.get("unitEnglishName") or "").strip().lower()
            zh = (u.get("unitName") or "").strip()
            cid = en2id.get(en)
            if not cid or not zh:
                continue
            cur = conn.execute(
                "UPDATE units SET name_zh = ? "
                "WHERE id = ? AND (name_zh IS NULL OR name_zh = '')", (zh, cid))
            filled += cur.rowcount
        conn.commit()
        return {"filled": filled}
    finally:
        conn.close()


def _collect_text(node) -> list:
    """递归从 content 节点里抠出所有 text（结构有 str/dict/list 多种变体）。"""
    out = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        if isinstance(node.get("text"), str):
            out.append(node["text"])
        if node.get("content") is not None:
            out += _collect_text(node["content"])
    elif isinstance(node, list):
        for x in node:
            out += _collect_text(x)
    return out


def _flatten_ability(ab: dict) -> str:
    """能力 JSON → 「名称：正文」纯文本。"""
    if not isinstance(ab, dict):
        return ""
    name = ab.get("name") or ""
    body = "".join(_collect_text(ab.get("content"))).strip()
    return f"{name}：{body}" if body else name


def _flatten_weapon(w: dict, melee: bool) -> str:
    """武器 JSON → 一行属性摘要。"""
    tag = "近战" if melee else "射击"
    skill = "、".join(w.get("skill") or [])
    core = (f"攻击{w.get('攻击次数','?')} 命中{w.get('命中','?')} "
            f"S{w.get('造伤','?')} AP{w.get('破甲','?')} D{w.get('伤害','?')}")
    rng = "" if melee else f"射程{w.get('射程','?')}\" "
    tail = f"（{skill}）" if skill else ""
    return f"- [{tag}] {w.get('name','?')}：{rng}{core}{tail}"


def build_blacklibrary_docs(db_path):
    """把 unit_zh_detail 全表渲染成检索文档（每单位一个 chunk：属性+武器+能力全文）。

    供 ingest.py 注入 L1 索引：黑图书馆中文原生内容进检索层，规则/能力题可召回干净中文，
    补汉化 PDF 的不全。返回 List[Document]（book='黑图书馆'）。表不存在返回 []。
    """
    from langchain_core.documents import Document

    conn = sqlite3.connect(str(db_path))
    try:
        try:
            rows = conn.execute(
                "SELECT canonical_id, name_zh, faction_zh, stats_json, "
                "abilities_json, weapons_json FROM unit_zh_detail "
                "WHERE source='blackforum'").fetchall()
        except sqlite3.OperationalError:
            return []
    finally:
        conn.close()

    docs = []
    for cid, name_zh, faction_zh, stats_j, ab_j, w_j in rows:
        if not name_zh:
            continue
        # 不渲染黑图书馆分数：它无版本标记，会成为绕过官方 MFM 权威链的第 4 个点数源，
        # 经 classic 检索直接流入回答。点数一律走 L3 的 units.points_json(官方 MFM 覆写)。
        lines = [f"## {name_zh}", f"所属：{faction_zh or '未知'}"]
        # 属性
        stats = json.loads(stats_j) if stats_j else []
        for m in stats:
            lines.append(
                f"**{m.get('unitName') or name_zh}**：M{m.get('m','?')}\" "
                f"T{m.get('t','?')} SV{m.get('sv','?')}+ W{m.get('w','?')} "
                f"LD{m.get('ld','?')} OC{m.get('oc','?')}")
        # 武器
        weapons = json.loads(w_j) if w_j else {}
        wl = [_flatten_weapon(x, False) for x in (weapons.get("射击武器") or [])]
        wl += [_flatten_weapon(x, True) for x in (weapons.get("近战武器") or [])]
        if wl:
            lines.append("**武器**")
            lines.extend(wl)
        # 能力全文
        abilities = json.loads(ab_j) if ab_j else []
        ab_txt = [_flatten_ability(a) for a in abilities if _flatten_ability(a)]
        if ab_txt:
            lines.append("**能力**")
            lines.extend(f"- {t}" for t in ab_txt)

        docs.append(Document(
            page_content="\n".join(lines).strip(),
            metadata={"source": "blacklibrary", "book": "黑图书馆",
                      "unit": name_zh, "page": 0}))
    return docs


def load_zh_detail(db_path, canonical_id: str) -> Optional[dict]:
    """读某单位的中文原生 datasheet（供 get_datasheet 附加中文层）。表不存在返回 None。"""
    conn = sqlite3.connect(str(db_path))
    try:
        try:
            row = conn.execute(
                "SELECT name_zh, faction_zh, stats_json, abilities_json, weapons_json "
                "FROM unit_zh_detail WHERE canonical_id = ?", (canonical_id,)).fetchone()
        except sqlite3.OperationalError:
            return None
        if not row:
            return None
        return {
            "name_zh": row[0], "faction_zh": row[1],
            "属性": json.loads(row[2]) if row[2] else [],
            "能力": json.loads(row[3]) if row[3] else None,
            "武器": json.loads(row[4]) if row[4] else None,
        }
    finally:
        conn.close()
