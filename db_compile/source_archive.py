"""Preserve explicitly deleted community-source cards outside the active roster DB.

These records are historical source evidence, never official current datasheets or
prices. Projection reads an existing local cache only; lookup opens SQLite read-only.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from db_compile.blacklibrary import DEFAULT_DETAILS_CACHE, DETAIL_API


SOURCE = "blacklibrary"
STATUS = "historical_source_only"
AUTHORITY = "third_party_deleted_record"
_ARCHIVE_COLUMNS = (
    "source", "source_id", "name_en", "name_zh", "faction_zh", "historical_points",
    "status", "authority", "source_url", "cached_at", "cache_timestamp_kind", "raw_json",
)
_ARCHIVE_DDL = """
    CREATE TABLE IF NOT EXISTS source_archived_units (
        source TEXT NOT NULL,
        source_id TEXT NOT NULL,
        name_en TEXT NOT NULL,
        name_zh TEXT NOT NULL,
        faction_zh TEXT NOT NULL,
        historical_points INTEGER,
        status TEXT NOT NULL,
        authority TEXT NOT NULL,
        source_url TEXT NOT NULL,
        cached_at TEXT,
        cache_timestamp_kind TEXT,
        raw_json TEXT NOT NULL,
        PRIMARY KEY (source, source_id)
    )
"""
_DELETED = re.compile(r"(?:\(已删除\)|\[已删除\]|【已删除】)\s*$")
_CALGAR_ALIASES = ("卡尔加", "普通卡尔加", "Marneus Calgar", "ordinary Marneus Calgar")
_SOURCE_SCOPE = (
    "黑图书馆本地缓存的历史记录，原始名称明确标注“已删除”。"
    "这是第三方历史资料，不是官方现行兵牌；historical_points 仅为缓存中的旧点数，"
    "不得作为当前点数或军表合法性依据，也不得与其他同名/不同装备版本混用。"
    "缓存时间仅指本地文件修改时间，不是规则发布日期或当前有效性验证。"
)


def _normalise(name: str) -> str:
    """Exact text comparison after case, width, whitespace and punctuation folding."""
    return "".join(
        char for char in unicodedata.normalize("NFKC", name).casefold()
        if not char.isspace() and not unicodedata.category(char).startswith("P")
    )


def _deleted_name(name: str) -> Optional[str]:
    folded = unicodedata.normalize("NFKC", name)
    if not _DELETED.search(folded):
        return None
    return _DELETED.sub("", folded).strip()


def _points(value) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"\d+", value.strip(), flags=re.ASCII):
        return int(value)
    return None


def _cache_stamp(cache_path: Optional[Path]) -> Optional[str]:
    if cache_path is None or not cache_path.is_file():
        return None
    return datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc).isoformat()


def preserve_archived_units(source_db_path, destination: sqlite3.Connection) -> int:
    """Carry verified historical evidence into a fresh DB before atomic replacement.

    Later source snapshots can omit deleted cards, so replaying the latest cache
    alone cannot restore this evidence. Copy only this module's known projection,
    validating its identity and price against the retained raw source. The caller
    owns the destination transaction; the previous database is opened read-only.
    """
    path = Path(source_db_path)
    if not path.is_file():
        return 0
    source = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        if not source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_archived_units'"
        ).fetchone():
            return 0
        rows = source.execute(
            "SELECT " + ", ".join(_ARCHIVE_COLUMNS) +
            " FROM source_archived_units WHERE source=? AND status=? AND authority=?",
            (SOURCE, STATUS, AUTHORITY),
        ).fetchall()
    finally:
        # Windows cannot atomically replace a database with an open connection.
        source.close()
    for row in rows:
        try:
            raw = json.loads(row["raw_json"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Archived source record has invalid raw JSON") from exc
        if not isinstance(raw, dict):
            raise ValueError("Archived source record must retain a source object")
        source_id = raw.get("id")
        if (isinstance(source_id, bool) or not isinstance(source_id, (int, str))
                or not str(source_id).strip() or str(source_id).strip() != row["source_id"]
                or not isinstance(row["name_zh"], str)
                or _deleted_name(row["name_zh"]) is None
                or row["name_zh"] != raw.get("name_zh")
                or row["name_en"] != (raw.get("name_en") or "")
                or row["faction_zh"] != (raw.get("faction_zh") or "")
                or row["historical_points"] != _points(raw.get("score"))
                or row["source_url"] != DETAIL_API):
            raise ValueError("Archived source record disagrees with its retained raw source")
    if rows:
        destination.execute(_ARCHIVE_DDL)
        destination.executemany(
            "INSERT INTO source_archived_units (" + ", ".join(_ARCHIVE_COLUMNS) + ")"
            " VALUES (" + ", ".join("?" for _ in _ARCHIVE_COLUMNS) + ")",
            [tuple(row[column] for column in _ARCHIVE_COLUMNS) for row in rows],
        )
    return len(rows)


def project_deleted_details(db_path, details: Optional[List[dict]] = None,
                            cache_path=None) -> Dict:
    """Upsert explicitly deleted cached cards in an independent historical table.

    Missing caches leave any previous archive intact. Later snapshots may cease
    listing a deleted card; absence alone never erases previously archived evidence.
    All writes (including table creation) share one transaction. ``units`` and its
    active points/aliases are never read or modified by this projection.
    """
    db_path = Path(db_path)
    path = Path(cache_path) if cache_path is not None else (
        DEFAULT_DETAILS_CACHE if details is None else None)
    report = {"source": SOURCE, "status": "projected", "records": 0,
              "archived": 0, "ignored": 0, "total_archived": 0,
              "cached_at": None, "cache_timestamp_kind": None}
    if details is None:
        if path is None or not path.is_file():
            return {**report, "status": "missing_cache"}
        details = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(details, list) or any(not isinstance(item, dict) for item in details):
        raise ValueError("Black Library details cache must contain a list of objects")
    if not db_path.is_file():
        return {**report, "status": "missing_database"}
    cached_at = _cache_stamp(path)
    report.update(records=len(details), cached_at=cached_at,
                  cache_timestamp_kind="file_mtime" if cached_at else None)
    rows = []
    source_ids = set()
    for record in details:
        name_zh = record.get("name_zh")
        if not isinstance(name_zh, str) or _deleted_name(name_zh) is None:
            continue
        source_id = record.get("id")
        if isinstance(source_id, bool) or not isinstance(source_id, (int, str)) or not str(source_id).strip():
            raise ValueError("Deleted source record has no stable source id")
        source_id = str(source_id).strip()
        if source_id in source_ids:
            raise ValueError("Duplicate deleted source id: " + source_id)
        source_ids.add(source_id)
        name_en = record.get("name_en") or ""
        faction_zh = record.get("faction_zh") or ""
        if not isinstance(name_en, str) or not isinstance(faction_zh, str):
            raise ValueError("Deleted source record has malformed names")
        rows.append((SOURCE, source_id, name_en, name_zh, faction_zh,
                     _points(record.get("score")), STATUS, AUTHORITY, DETAIL_API,
                     cached_at, "file_mtime" if cached_at else None,
                     json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False)))
    conn = sqlite3.connect(db_path.resolve().as_uri() + "?mode=rw", uri=True)
    try:
        with conn:
            conn.execute("BEGIN")
            conn.execute(_ARCHIVE_DDL)
            conn.executemany("""
                INSERT INTO source_archived_units
                    (source, source_id, name_en, name_zh, faction_zh, historical_points,
                     status, authority, source_url, cached_at, cache_timestamp_kind, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, source_id) DO UPDATE SET
                    name_en=excluded.name_en, name_zh=excluded.name_zh,
                    faction_zh=excluded.faction_zh, historical_points=excluded.historical_points,
                    status=excluded.status, authority=excluded.authority, source_url=excluded.source_url,
                    cached_at=excluded.cached_at, cache_timestamp_kind=excluded.cache_timestamp_kind,
                    raw_json=excluded.raw_json
            """, rows)
            report["total_archived"] = conn.execute(
                "SELECT COUNT(*) FROM source_archived_units WHERE source=?", (SOURCE,)
            ).fetchone()[0]
    finally:
        conn.close()
    report.update(archived=len(rows), ignored=len(details) - len(rows))
    return report


def _verified_calgar(row: sqlite3.Row) -> bool:
    """The short aliases belong to source id 6's ordinary card, never its armour variant."""
    return (row["source_id"] == "6"
            and _normalise(row["name_en"]) == "marneuscalgar"
            and _normalise(_deleted_name(row["name_zh"]) or "") == "马涅乌斯卡尔加"
            and _normalise(row["faction_zh"]) == "极限战士")


def _raw_text_fragments(value) -> List[str]:
    """Collect bounded source text while skipping duplicate rendered HTML fields."""
    if isinstance(value, str):
        text = re.sub(r"\s+", " ", value).strip()
        return [text] if text else []
    if isinstance(value, dict):
        texts: List[str] = []
        for key, item in value.items():
            if isinstance(key, str) and key.casefold().endswith("html"):
                continue
            texts.extend(_raw_text_fragments(item))
        return texts
    if isinstance(value, (list, tuple)):
        texts = []
        for item in value:
            texts.extend(_raw_text_fragments(item))
        return texts
    return []


_CALGAR_ZH_COMPOSITION = re.compile(
    r"(?:马涅乌斯[·.]?)?卡尔加"
    r"(?:(?!不能|无法|不可以|没有|未).){0,80}?"
    r"(?:和|与|及)(?<!\d)(?:两|二|2)(?!\d)(?:名|个|位)?"
    r"(?:常胜护卫|荣胜卫队|维克特里克斯(?:卫队|护卫))"
    r".{0,40}?(?:组成|编成)(?:一个|1个)?单位"
)
_CALGAR_EN_COMPOSITION = re.compile(
    r"\bmarneus\s+calgar\b.{0,80}?\b(?:and|with)\s+"
    r"(?<!\d)(?:two|2)(?!\d)\s+victrix\s+honou?r\s+guards?\b",
    flags=re.IGNORECASE,
)
_COMPOSITION_NEGATION = re.compile(
    r"不允许|不得|不能|无法|不可以|没有|未|禁止|"
    r"\b(?:cannot|can't|not|never|must\s+not|may\s+not)\b",
    flags=re.IGNORECASE,
)


def _affirmative_composition_match(pattern: re.Pattern, text: str) -> Optional[str]:
    """Return a positive match only when its complete source clause is affirmative."""
    normalized = unicodedata.normalize("NFKC", text)
    for clause in re.split(r"[。！？；;\r\n]+", normalized):
        match = pattern.search(clause)
        if match and not _COMPOSITION_NEGATION.search(clause):
            return match.group(0)
    return None


def _calgar_composition_evidence(row: sqlite3.Row, raw: dict) -> Optional[str]:
    """Return the retained unit-composition sentence, or no identity projection.

    Source id/name validation alone establishes the archived card identity but not
    its model composition.  Require one source fragment to name Calgar and two
    guard models together before exposing the ordinary-card boundary to an LLM.
    """
    if not _verified_calgar(row):
        return None
    # An English noun phrase without "forms a unit" is evidence only when the
    # source itself labels that field as composition.  This supports retained
    # normalized fixtures without promoting arbitrary combat prose.
    composition_fields = [raw.get("composition")]
    detail = raw.get("detail")
    if isinstance(detail, dict):
        composition_fields.extend(
            detail.get(key) for key in ("composition", "unit_composition")
        )
    for value in composition_fields:
        for text in _raw_text_fragments(value):
            evidence = _affirmative_composition_match(_CALGAR_EN_COMPOSITION, text)
            if evidence:
                return evidence
    for text in _raw_text_fragments(raw):
        evidence = _affirmative_composition_match(_CALGAR_ZH_COMPOSITION, text)
        if evidence:
            # Return the matched affirmative sentence itself, so a long source
            # fragment cannot truncate away the evidence that authorized scope.
            return evidence
    return None


def find_archived_unit(db_path, query: str) -> Optional[dict]:
    """Return one unambiguous historical source match, without fuzzy/sub-string guessing."""
    path = Path(db_path)
    if not path.is_file() or not isinstance(query, str) or not _normalise(query):
        return None
    key = _normalise(query)
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_archived_units'"
        ).fetchone():
            return None
        matches = []
        for row in conn.execute(
            "SELECT * FROM source_archived_units WHERE source=? AND status=? AND authority=?",
            (SOURCE, STATUS, AUTHORITY),
        ):
            if _deleted_name(row["name_zh"]) is None:
                continue
            exact_names = (row["name_en"], row["name_zh"], _deleted_name(row["name_zh"]) or "")
            if key in {_normalise(name) for name in exact_names if name}:
                matches.append((row, "exact"))
            elif _verified_calgar(row) and key in {_normalise(name) for name in _CALGAR_ALIASES}:
                matches.append((row, "verified_alias"))
        if len(matches) != 1:
            return None
        row, match_type = matches[0]
        raw = json.loads(row["raw_json"])
        result = {
            "found": True, "archive_id": SOURCE + ":" + row["source_id"],
            "source": SOURCE, "source_id": row["source_id"],
            "name_en": row["name_en"], "name_zh": row["name_zh"],
            "faction_zh": row["faction_zh"], "historical_points": row["historical_points"],
            "status": STATUS, "authority": AUTHORITY, "is_current": False,
            "source_url": row["source_url"], "cached_at": row["cached_at"],
            "cache_timestamp_kind": row["cache_timestamp_kind"],
            "raw": raw, "match_type": match_type,
            "source_scope": _SOURCE_SCOPE,
        }
        composition = _calgar_composition_evidence(row, raw)
        if composition:
            result["identity_scope"] = {
                "evidence_kind": "retained_source_unit_composition",
                "card_name": row["name_en"],
                "composition_evidence": composition,
                "model_counts": {"calgar": 1, "guard_models": 2},
                "variant_boundary": (
                    "该历史记录明确对应 Marneus Calgar 兵牌及“卡尔加 + 两名护卫模型”"
                    "的单位编成；它不是把安提洛库斯之铠版本混在一起的模糊缓存命中。"
                ),
            }
        return result
    finally:
        conn.close()
