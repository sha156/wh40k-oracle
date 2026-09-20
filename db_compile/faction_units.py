"""Read-only faction inventory; database coverage and official prices stay distinct."""
from contextlib import closing
from pathlib import Path
import sqlite3

from db_compile.active_units import active_unit_ids
from db_compile.mfm import MFM_SLUG_TO_FACTION, TITAN_DATASHEET_RULE, _TITAN_DATASHEET_ALIASES
from wiki_engine.from_db import FACTION_DIRS
from wiki_engine.models import FACTION_NAMES


def list_faction_units(db_path, faction, *, offset=0, limit=20):
    if (not isinstance(faction, str) or not faction.strip()
            or type(offset) is not int or offset < 0
            or type(limit) is not int or not 1 <= limit <= 50):
        return {"found": False, "param_error": True,
                "note": "faction 须为阵营名称；offset >= 0，limit 为 1–50 的整数。"}
    path = Path(db_path).resolve()
    if not path.is_file():
        return {"found": False, "error": True, "note": "结构库不存在；不能据此断言阵营有 0 个单位。"}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        key = faction.strip().casefold()
        factions = list(conn.execute("SELECT id, name FROM factions"))
        hits = [(fid, name) for fid, name in factions if key in {
            fid.casefold(), name.casefold(), FACTION_DIRS.get(fid, "").casefold(),
            FACTION_NAMES.get(fid, "").casefold(),
        }]
        if len(hits) != 1:
            return {"found": False, "note": "阵营未精确匹配；请使用候选阵营名称或 ID，未知不等于单位数为零。",
                    "factions": [{"id": fid, "name": name} for fid, name in factions]}
        fid, name = hits[0]
        current = active_unit_ids(conn)
        units = [{"id": uid, "name_en": en, "name_zh": zh}
                 for uid, en, zh in conn.execute(
                     "SELECT id,name_en,name_zh FROM units WHERE faction_id=? ORDER BY name_en,id", (fid,))
                 if uid in current]
        pages = []
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='official_mfm_points'").fetchone():
            for slug, mapped_fid in MFM_SLUG_TO_FACTION.items():
                if mapped_fid != fid:
                    continue
                rows = list(conn.execute(
                    "SELECT DISTINCT unit_name,source_url,fetched_at FROM official_mfm_points "
                    "WHERE faction_slug=? AND kind='unit' ORDER BY unit_name", (slug,)))
                if rows:
                    names = sorted({r[0] for r in rows})
                    pages.append({"slug": slug, "unit_count": len(names), "unit_names": names[:10],
                                  "names_truncated": len(names) > 10,
                                  "sources": [{"url": url, "fetched_at": date}
                                              for url, date in sorted({(r[1], r[2]) for r in rows})]})
        selected = units[offset:offset + limit]
        result = {"found": True, "faction_id": fid, "faction": name,
                "scope": "current_database_datasheets", "database_count": len(units),
                "offset": offset, "returned": len(selected),
                "next_offset": offset + limit if offset + limit < len(units) else None,
                "note": "database_count 是当前结构库兵牌总数（按统一现役口径），不受分页影响；官方每页 unit_count 按单位名去重，不把价格档位或强化算成单位。不同官方页可能重印同一单位，不可把各页数量直接相加。点数条目可能尚无兵牌，库内兵牌也不证明全部规则已更新。共享兵牌须另查官方规则。",
                "official_pages": pages, "units": selected}
        if fid == "TL":
            result["shared_datasheets"] = {
                "aliases": dict(_TITAN_DATASHEET_ALIASES),
                "source": dict(TITAN_DATASHEET_RULE),
            }
        return result
