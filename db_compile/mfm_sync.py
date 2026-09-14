"""Snapshot, reconcile and atomically sync official unit/enhancement points.

Run: python -m db_compile.mfm_sync --fetch --apply
Omit --apply to rehearse on a temporary copy. Source pages and reports remain
under ignored db_sources/mfm; full datasheets are never invented from prices.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path

from db_compile import mfm
from db_compile.mfm_source import load_snapshot, verify_ledger, write_ledger


def _name_key(name):
    # Publisher type suffixes are metadata, not part of the enhancement name.
    text = (name or "").strip().casefold().replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s*\((?:aura|psychic|upgrade)\)\s*$", "", text)
    return " ".join(text.split())


def fetch_snapshot(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    # Every fetch has a separate directory, so an interrupted download cannot
    # corrupt the previous snapshot or its hash manifest.
    root = Path(tempfile.mkdtemp(prefix="fetch-", dir=str(root)))
    home = mfm._fetch(mfm.MFM_BASE + "/en")
    slugs = mfm.list_faction_slugs(home)
    if not slugs:
        raise mfm.MfmParseBroken("No official faction links")
    pages = {}
    for slug in slugs:
        for attempt in range(3):
            try:
                raw = mfm._fetch(mfm.MFM_BASE + "/en/" + slug).encode("utf-8")
                break
            except (OSError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
        (root / (slug + ".html")).write_bytes(raw)
        pages[slug] = {"url": mfm.MFM_BASE + "/en/" + slug,
                       "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    (root / "manifest.json").write_text(json.dumps({
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "pages": pages
    }, indent=2), encoding="utf-8")
    # Parsing all pages must succeed before the snapshot can be applied.
    return load_snapshot(root)


def fetch_cache(path):
    path = Path(path)
    snapshot = fetch_snapshot(path.parent / "snapshots")
    factions = operational_factions(snapshot)
    mfm._guard_cache_regression(path, factions)
    data = {"source": mfm.MFM_BASE, "fetched_at": snapshot["fetched_at"],
            "failed": [], "parse_broken": [], "factions": factions,
            "source_snapshot": snapshot}
    temp = path.with_suffix(".pending.json")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    temp.replace(path)
    return factions


def operational_factions(snapshot):
    factions = {}
    for slug, page in snapshot["pages"].items():
        rows = [r for r in page["rows"] if r["kind"] == "unit"]
        primary = [r for r in rows if r["section"] in mfm._PRIMARY_SECTIONS]
        priced = {r["unit"].casefold() for r in primary}
        secondary = [r for r in rows if r["section"] not in mfm._PRIMARY_SECTIONS
                     and r["unit"].casefold() not in priced]
        factions[slug] = list(dict.fromkeys((r["unit"], r["tier"], r["models"], r["cost"])
                                           for r in primary + secondary))
    return factions


def _enhancements(conn, snapshot, apply=False):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(enhancements)")}
    if not {"id", "faction_id", "name", "detachment_name", "cost"} <= cols:
        raise RuntimeError("Enhancement table is missing required columns")
    db_rows = {}
    for uid, fid, name, detachment, cost in conn.execute(
            "SELECT id,faction_id,name,detachment_name,cost FROM enhancements"):
        key = (fid, _name_key(detachment), _name_key(name))
        db_rows.setdefault(key, []).append((uid, cost))
    prices = {}
    for slug in sorted(snapshot["pages"], key=lambda s: (s != "space-marines", s)):
        fid = mfm.MFM_SLUG_TO_FACTION.get(slug)
        for row in snapshot["pages"][slug]["rows"]:
            if row["kind"] == "enhancement":
                key = (fid, _name_key(row["unit"]), _name_key(row["models"]))
                if key in prices and prices[key] != row["cost"]:
                    raise mfm.MfmParseBroken(f"Enhancement price conflict: {key}")
                prices[key] = row["cost"]
    changes, unmatched, matched = [], [], 0
    for key, cost in prices.items():
        hits = db_rows.get(key, [])
        if not hits:
            unmatched.append({"faction": key[0], "detachment": key[1], "name": key[2], "cost": cost})
        for uid, old in hits:
            matched += 1
            if old != cost:
                changes.append({"id": uid, "name": key[2], "db": old, "official": cost})
            if apply:
                conn.execute("UPDATE enhancements SET cost=? WHERE id=?", (cost, uid))
    return {"source_entries": len(prices), "matched_database_rows": matched,
            "changes": changes, "points_only": unmatched}


def apply_snapshot(db_path, snapshot):
    factions = operational_factions(snapshot)
    before = mfm.check_points(db_path, factions)
    with closing(sqlite3.connect(str(db_path))) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        enhancement_report = _enhancements(conn, snapshot, apply=True)
        # An old MFM provenance block must not permanently mean "current".
        # Keep historical costs, but only entries matched by this snapshot regain
        # current=True. The official ledger remains complete independently.
        for uid, raw in conn.execute("SELECT id,points_json FROM units").fetchall():
            try:
                data = json.loads(raw or "{}")
            except (TypeError, ValueError):
                continue
            if isinstance(data, dict):
                if not isinstance(data.get("mfm"), dict):
                    data["mfm"] = {}
                data["mfm"]["current"] = False
                data["mfm"]["checked_at"] = snapshot["fetched_at"]
                conn.execute("UPDATE units SET points_json=? WHERE id=?",
                             (json.dumps(data, ensure_ascii=False), uid))
        applied = mfm.apply_points(db_path, factions, fetched_at=snapshot["fetched_at"], connection=conn)
        count = write_ledger(conn, snapshot)
        conn.execute("""CREATE TABLE IF NOT EXISTS official_mfm_detachments (
            faction_slug TEXT, name TEXT, dp INTEGER, disposition_json TEXT,
            source_url TEXT, fetched_at TEXT, PRIMARY KEY(faction_slug,name))""")
        conn.execute("DELETE FROM official_mfm_detachments")
        for slug, page in snapshot["pages"].items():
            for card in page["detachments"]:
                conn.execute("INSERT INTO official_mfm_detachments VALUES (?,?,?,?,?,?)",
                             (slug, card["name"], card["dp"], json.dumps(card["disposition"]),
                              page["url"], snapshot["fetched_at"]))
        after = mfm.check_points(db_path, factions, connection=conn)
        enhancements_after = _enhancements(conn, snapshot)
        ledger = verify_ledger(db_path, snapshot, connection=conn)
        if (after["diffs"] or after["db_missing_tiers"] or after["db_extra_tiers"]
                or after["db_unparsed"] or enhancements_after["changes"] or not ledger["equal"]):
            raise RuntimeError("Official sync did not converge; transaction rolled back")
    return {"fetched_at": snapshot["fetched_at"], "official_pages": len(snapshot["pages"]),
            "ledger": ledger, "unit_prices_before": before, "unit_prices_after": after,
            "units_applied": applied, "enhancements": enhancement_report,
            "official_rows": count,
            "note": "Points-only records are retained in the official ledger; they do not assert datasheet coverage."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--db", type=Path, default=Path("db/wh40k.sqlite"))
    parser.add_argument("--snapshot", type=Path,
                        default=Path("db_sources/mfm/snapshots") / dt.datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--report", type=Path, default=Path("db_sources/mfm/sync-report.json"))
    args = parser.parse_args()
    snapshot = fetch_snapshot(args.snapshot) if args.fetch else load_snapshot(args.snapshot)
    mfm._guard_cache_regression(Path("db_sources/mfm/mfm_points.json"), operational_factions(snapshot))
    with tempfile.TemporaryDirectory(prefix="wh40k-sync-trial-") as temp:
        trial = Path(temp) / "wh40k.sqlite"
        with closing(sqlite3.connect(str(args.db))) as source, closing(sqlite3.connect(str(trial))) as dest:
            source.backup(dest)
        report = apply_snapshot(trial, snapshot)
    if args.apply:
        # Always preserve a recoverable pre-sync database; never overwrite a prior backup.
        backup_dir = Path(tempfile.mkdtemp(prefix="wh40k-before-official-sync-"))
        with closing(sqlite3.connect(str(args.db))) as source, closing(sqlite3.connect(str(backup_dir / "wh40k.sqlite"))) as dest:
            source.backup(dest)
        report = apply_snapshot(args.db, snapshot)
        report["backup"] = str(backup_dir / "wh40k.sqlite")
        cache = {"source": mfm.MFM_BASE, "fetched_at": snapshot["fetched_at"],
                 "failed": [], "parse_broken": [], "factions": operational_factions(snapshot),
                 "source_snapshot": snapshot}
        Path("db_sources/mfm/mfm_points.json").write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    report["applied"] = args.apply
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"applied": args.apply, "ledger": report["ledger"],
                      "units_applied": report["units_applied"],
                      "unit_mismatches_after": len(report["unit_prices_after"]["diffs"]),
                      "enhancement_changes": len(report["enhancements"]["changes"]),
                      "points_only_units": report["unit_prices_after"]["mfm_only"],
                      "report": str(args.report)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
