"""Read the complete official price ledger, including prices without datasheets."""
from contextlib import closing
from pathlib import Path
import sqlite3


def browse(db_path, query="", offset=0, limit=50):
    with closing(sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='official_mfm_points'").fetchone():
            raise ValueError("官方完整点数快照尚未同步")
        query = query.strip().casefold()
        rows = [dict(r) for r in conn.execute("SELECT * FROM official_mfm_points ORDER BY faction_slug,ordinal")]
        matches = [r for r in rows if not query or query in (r["unit_name"] + " " + r["models"] + " " + r["faction_slug"]).casefold()]
        return {"total": len(matches), "sourceRows": len(rows), "offset": offset,
                "fetchedAt": rows[0]["fetched_at"] if rows else None,
                "rows": matches[offset:offset + limit]}


def exact_unit(db_path, name):
    from db_compile.mfm import is_base_tier
    from db_compile.point_tiers import minimum_unit_cost
    result = browse(db_path, name, limit=5000)
    rows = [r for r in result["rows"] if r["kind"] == "unit" and r["unit_name"].casefold() == name.strip().casefold()]
    if not rows:
        return None
    points = {minimum_unit_cost([{"desc": r["models"], "cost": r["cost"]}
                                 for r in rows if r["faction_slug"] == slug and is_base_tier(r["tier"])])
              for slug in {r["faction_slug"] for r in rows}}
    return {"unit_id": None, "name_en": rows[0]["unit_name"],
            "points": next(iter(points)) if len(points) == 1 else None,
            "official_prices": rows, "points_only": True,
            "note": "官方 MFM 有此单位的点数；结构库尚无已匹配兵牌，不能据此编造属性。不同阵营/编制的价格请按来源档位选择。"}
