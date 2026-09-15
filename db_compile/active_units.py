"""Shared definition of units with current pricing.

A complete official MFM snapshot is authoritative, including Harlequins and
chapter sections. Its current flags supersede the historical MFM/Black Library
union: a translated datasheet alone does not prove current matched-play pricing.
Legacy databases without the complete ledger retain the old compatibility rule.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Set

_log = logging.getLogger(__name__)


def mfm_priced_unit_ids(conn: sqlite3.Connection) -> Set[str]:
    """`points_json` 里带 `mfm` 溯源块的单位 = 出现在官方现行 MFM 点数表里。"""
    ids: Set[str] = set()
    for uid, pj in conn.execute("SELECT id, points_json FROM units"):
        try:
            source = (json.loads(pj) or {}).get("mfm") if pj else None
            if source and source.get("current", True):
                ids.add(uid)
        except (json.JSONDecodeError, TypeError):
            continue
    return ids


def blacklibrary_unit_ids(conn: sqlite3.Connection) -> Set[str]:
    """被黑图书馆中文层收录的单位（收录面≈在售面）。表缺失时抛，见 `active_unit_ids`。"""
    return {uid for (uid,) in conn.execute("SELECT canonical_id FROM unit_zh_detail")
            if uid}


def active_unit_ids(conn: sqlite3.Connection) -> Set[str]:
    """Use official snapshot membership, or the legacy union before migration.

    A missing translation table in a legacy database still raises rather than
    silently reducing its old eligibility pool.
    """
    ids = mfm_priced_unit_ids(conn)
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='official_mfm_points'").fetchone():
        # A complete official snapshot replaces the old approximate "on sale"
        # union. A translated legacy datasheet does not establish current pricing.
        return ids
    ids |= blacklibrary_unit_ids(conn)
    return ids
