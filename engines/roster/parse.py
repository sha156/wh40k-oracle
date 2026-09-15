"""Conservative text import: exact names/IDs, explicit sizes, unresolved lines.

Examples:
Faction: Space Marines
Detachment: Gladius Task Force
5x Intercessor Squad
Apothecary Biologis | models=1 | warlord | weapons=Absolvor bolt pistol:1

One unit per line; | separates model, enhancement and weapon fields. An
unsupported export line is returned to the caller instead of silently ignored.
"""
from __future__ import annotations
from contextlib import closing
import re
import sqlite3


def _key(text):
    return " ".join(text.strip().casefold().replace("’", "'").replace("·", ".").split())


def parse_roster(db_path, text, faction_id=None, detachment_id=None, size="strike_force"):
    if not isinstance(text, str) or len(text) > 20000:
        raise ValueError("军表文本须在 20000 字符以内")
    issues, units = [], []
    lines = list(enumerate(text.splitlines(), 1))
    with closing(sqlite3.connect(str(db_path))) as conn:
        factions = list(conn.execute("SELECT id,name FROM factions"))
        catalogue = list(conn.execute("SELECT id,faction_id,name_en,name_zh FROM units"))
        detachments = list(conn.execute("SELECT DISTINCT detachment_id,detachment_name,faction_id FROM enhancements"))
        def issue(number, value, reason):
            issues.append({"line": number, "text": value, "reason": reason})
        # Resolve explicit headers before units, independent of their position.
        header_lines = set()
        for number, line in lines:
            header = re.fullmatch(r"\s*(Faction|Detachment|Size|阵营|分队|规模)\s*[:：]\s*(.+)", line, re.I)
            if not header:
                continue
            header_lines.add(number)
            label, value = header[1].casefold(), header[2].strip()
            if label in ("faction", "阵营"):
                hits = {fid for fid, name in factions if _key(value) in (_key(fid), _key(name))}
                if len(hits) != 1 or (faction_id and faction_id not in hits):
                    issue(number, line, "阵营未知、重名或与所选阵营冲突")
                else:
                    faction_id = hits.pop()
            elif label in ("size", "规模"):
                sizes = {"1000": "incursion", "2000": "strike_force", "3000": "onslaught"}
                size = sizes.get(value, value)
            # Detachment resolution waits until faction is known.
        for number, line in lines:
            header = re.fullmatch(r"\s*(?:Detachment|分队)\s*[:：]\s*(.+)", line, re.I)
            if header:
                hits = {did for did, name, fid in detachments if fid == faction_id and _key(header[1]) in (_key(did or ""), _key(name or ""))}
                if len(hits) != 1 or (detachment_id and detachment_id not in hits):
                    issue(number, line, "分队未知、重名或与所选分队冲突")
                else:
                    detachment_id = hits.pop()
        if not faction_id:
            issue(0, "", "请指定 Faction: 阵营名，或先选择阵营")
        if size not in ("incursion", "strike_force", "onslaught"):
            issue(0, size, "规模不支持")
        for number, line in lines:
            if number in header_lines or not line.strip():
                continue
            try:
                parts = [p.strip() for p in line.strip().lstrip("• ").split("|")]
                name = parts.pop(0)
                count = None
                prefix = re.fullmatch(r"(\d+)\s*[x×]\s*(.+)", name, re.I)
                suffix = re.fullmatch(r"(.+?)\s*\((\d+)\s*models?\)", name, re.I)
                if prefix:
                    count, name = int(prefix[1]), prefix[2]
                elif suffix:
                    name, count = suffix[1], int(suffix[2])
                hits = [r for r in catalogue if (not faction_id or r[1] == faction_id)
                        and _key(name) in {_key(n) for n in (r[0], r[2], r[3]) if n}]
                if len(hits) != 1:
                    raise ValueError("单位未精确匹配或有重名；请使用图鉴中的完整名称或 canonical id")
                uid, _, name_en, _ = hits[0]
                warlord, enhancement, weapons = False, None, []
                seen = set()
                for field in parts:
                    key, sep, value = field.partition("=")
                    key = key.casefold()
                    if key in seen:
                        raise ValueError("字段重复: " + key)
                    seen.add(key)
                    if key == "warlord" and not sep:
                        warlord = True
                    elif key == "models" and sep and value.isdigit() and count is None:
                        count = int(value)
                    elif key == "enhancement" and sep:
                        hits_e = [n for (n,) in conn.execute("SELECT name FROM enhancements WHERE detachment_id=?", (detachment_id,)) if _key(n) == _key(value)]
                        if len(set(hits_e)) != 1:
                            raise ValueError("强化未在所选分队中精确匹配")
                        enhancement = hits_e[0]
                    elif key == "weapons" and sep:
                        pool = { _key(n): n for (n,) in conn.execute("SELECT name_en FROM weapons WHERE unit_id=?", (uid,)) }
                        for weapon in value.split(";"):
                            weapon_name, colon, quantity = weapon.rpartition(":")
                            if not colon or not quantity.isdigit() or not 1 <= int(quantity) <= 100 or _key(weapon_name) not in pool:
                                raise ValueError("武器格式须为精确武器名:数量，多种武器用分号分隔")
                            canonical_weapon = pool[_key(weapon_name)]
                            if any(w[0] == canonical_weapon for w in weapons):
                                raise ValueError("武器重复；请将同名武器数量合并为一项")
                            weapons.append([canonical_weapon, int(quantity)])
                    else:
                        raise ValueError("不支持的字段: " + field)
                if count is None or not 1 <= count <= 100:
                    raise ValueError("请明确模型数，例如 5x 单位名 或 单位名 | models=5")
                if len(weapons) > 40 or len(units) >= 60:
                    raise ValueError("超过 60 个单位或 40 项武器的导入上限")
                units.append({"canonicalId": uid, "nameEn": name_en, "models": count,
                              "isWarlord": warlord, "enhancement": enhancement, "loadout": weapons})
            except ValueError as exc:
                issue(number, line, str(exc))
    if not units:
        issue(0, "", "未解析出单位")
    return {"complete": bool(units) and not issues, "issues": issues,
            "roster": {"factionId": faction_id or "", "detachmentId": detachment_id,
                       "size": size, "units": units}}
