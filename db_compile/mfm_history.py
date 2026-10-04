"""Replay two reviewed historical price identities, never current membership.

The binding file was extracted from the retained official ledger and database.
Actual retained HTML must still verify every row before a CSV skeleton can gain
historical authority. Neither capture time nor heading absence is an effective
date, a Legends decision or evidence about numerical datasheet bodies.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from db_compile.mfm import MFM_BASE
from db_compile.mfm_source import parse_source_page


BINDINGS = Path(__file__).with_name("mfm_history_bindings.json")
DEFAULT_SNAPSHOT = Path("db_sources/mfm/snapshots/2026-09-14")


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError("Historical MFM timestamp is missing")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Historical MFM timestamp lacks timezone")
    return stamp


def _identity(conn, binding):
    uid = binding["canonical"]["id"]
    unit = conn.execute(
        "SELECT id,name_en,faction_id,keywords_json,points_json FROM units WHERE id=?",
        (uid,),
    ).fetchone()
    if unit is None:
        return None
    if dict(zip(("id", "name_en", "faction_id", "keywords_json"), unit[:4])) != binding["canonical"]:
        raise ValueError("Historical MFM canonical identity changed: " + uid)
    sheet = conn.execute(
        "SELECT name,faction_id,source_id,link FROM datasheets WHERE id=?", (uid,),
    ).fetchone()
    if sheet is None or dict(zip(("name", "faction_id", "source_id", "link"), sheet)) != binding["datasheet"]:
        raise ValueError("Historical MFM datasheet identity changed: " + uid)
    return json.loads(unit[4] or "{}")


def _verified_source(snapshot_dir, bindings):
    expected = bindings["snapshot"]
    manifest_path = snapshot_dir / "manifest.json"
    raw_path = snapshot_dir / (expected["faction_slug"] + ".html")
    if not manifest_path.is_file() or not raw_path.is_file():
        return None
    manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != expected["manifest_sha256"]:
        raise ValueError("Historical MFM manifest fingerprint changed")
    manifest = json.loads(manifest_bytes)
    if (manifest["fetched_at"] != expected["fetched_at"]
            or manifest["pages"][expected["faction_slug"]] != expected["page"]):
        raise ValueError("Historical MFM snapshot provenance changed")
    raw = raw_path.read_bytes()
    if (len(raw) != expected["page"]["bytes"]
            or hashlib.sha256(raw).hexdigest() != expected["page"]["sha256"]):
        raise ValueError("Historical MFM raw source fingerprint changed")
    page = parse_source_page(raw.decode("utf-8"))
    ledger = [dict(faction_slug=expected["faction_slug"], ordinal=i,
                   kind=row["kind"], section=row["section"], unit_name=row["unit"],
                   tier=row["tier"], models=row["models"], cost=row["cost"],
                   source_url=expected["page"]["url"],
                   source_sha256=expected["page"]["sha256"], fetched_at=expected["fetched_at"])
              for i, row in enumerate(page["rows"])]
    for binding in bindings["records"]:
        rows = [row for row in ledger if row["unit_name"] == binding["canonical"]["name_en"].upper()
                and row["kind"] == "unit"]
        prior = binding["prior_official_price"]
        tiers = [{k: row[k] for k in ("tier", "models", "cost")} for row in rows]
        items = [{"line": "1", "desc": row["models"], "cost": row["cost"]} for row in rows]
        if (rows != binding["ledger_rows"] or not rows
                or prior != {"points": min(row["cost"] for row in rows), "items": items,
                             "mfm": {"current": True, "source_url": MFM_BASE,
                                     "fetched_at": expected["fetched_at"], "tiers": tiers}}):
            raise ValueError("Historical MFM price disagrees with retained source")
    return ledger


def _historical_payload(binding):
    payload = copy.deepcopy(binding["prior_official_price"])
    payload["mfm"].update(current=False,
                          source_sha256=binding["ledger_rows"][0]["source_sha256"],
                          historical_source_rows=copy.deepcopy(binding["ledger_rows"]))
    return payload


def _prior_ledger(conn, binding):
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='official_mfm_points'"
    ).fetchone():
        return []
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM official_mfm_points WHERE faction_slug=? AND unit_name=? ORDER BY ordinal",
            (binding["ledger_rows"][0]["faction_slug"], binding["canonical"]["name_en"].upper()),
        )]
    finally:
        conn.row_factory = None


def _prior_price(conn, binding):
    payload = _identity(conn, binding)
    if payload is None:
        return "absent"
    source = payload.get("mfm", {})
    if not isinstance(source, dict):
        raise ValueError("Historical MFM prior provenance is malformed")
    source = copy.deepcopy(source)
    checked = source.pop("checked_at", None)
    if checked is not None:
        _stamp(checked)
    # A later current price is restored by the normal MFM layer. Do not turn it
    # into this older historical price, even temporarily in the new skeleton.
    if (source.get("current") is True and source.get("source_url") == MFM_BASE
            and _stamp(source.get("fetched_at")) > _stamp(binding["prior_official_price"]["mfm"]["fetched_at"])):
        # A changed timestamp alone cannot evade the exact historical guard.
        # Require independently retained current ledger rows to support the
        # later block before leaving its restoration to the current MFM layer.
        rows = _prior_ledger(conn, binding)
        tiers = [{k: row[k] for k in ("tier", "models", "cost")} for row in rows]
        from db_compile.mfm import _base_prices
        base = _base_prices([(r["tier"], r["models"], r["cost"]) for r in rows],
                            binding["canonical"]["id"])
        items = payload.get("items", [])
        if (not rows or tiers != source.get("tiers")
                or any(r["fetched_at"] != source["fetched_at"] or r["kind"] != "unit"
                       or r["source_url"] != binding["ledger_rows"][0]["source_url"]
                       or len(r["source_sha256"]) != 64 for r in rows)
                or {i["desc"]: i["cost"] for i in items} != base
                or payload.get("points") != min(base.values())):
            raise ValueError("Historical MFM newer current price lacks matching ledger")
        return "newer_current"
    original = copy.deepcopy(payload)
    original.pop("mfm", None)
    prior = copy.deepcopy(binding["prior_official_price"])
    prior_source = prior.pop("mfm")
    historic = _historical_payload(binding)["mfm"]
    if (original == binding["csv_price"] and source in ({}, {"current": False})):
        pass  # Narrow recovery from the exact verified AFB/mirror price fields.
    elif (original == prior and isinstance(source.get("current"), bool)
          and source in (dict(prior_source, current=True), dict(prior_source, current=False), historic)):
        pass
    else:
        raise ValueError("Historical MFM prior price/source mismatch: " + binding["canonical"]["id"])
    rows = _prior_ledger(conn, binding)
    if rows and rows != binding["ledger_rows"]:
        raise ValueError("Historical MFM prior ledger disagrees with retained source")
    return "eligible"


def preserve_historical_prices(source_db_path, destination, snapshot_dir=None):
    """Validate the complete narrow batch before writing in the builder transaction.

    Missing raw evidence is reported without granting CSV prices official
    authority. Invalid available evidence aborts the atomic build. Only price
    JSON changes; no old table, name, alias, body or current ledger is copied.
    """
    bindings = json.loads(BINDINGS.read_text(encoding="utf-8"))
    report = {"status": "not_applicable", "restored": [], "newer_current": []}
    present = [binding for binding in bindings["records"] if destination.execute(
        "SELECT 1 FROM units WHERE id=?", (binding["canonical"]["id"],),
    ).fetchone()]
    if not present:
        return report
    snapshot_dir = Path(snapshot_dir) if snapshot_dir is not None else DEFAULT_SNAPSHOT
    if _verified_source(snapshot_dir, bindings) is None:
        return dict(report, status="unavailable", snapshot=str(snapshot_dir))
    candidates = []
    for binding in present:
        payload = _identity(destination, binding)
        if payload is not None:
            if payload != binding["csv_price"]:
                raise ValueError("Historical MFM CSV price from-guard changed: " + binding["canonical"]["id"])
            candidates.append(binding)
    eligible = []
    path = Path(source_db_path)
    if path.is_file():
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            has_units = source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='units'").fetchone()
            for binding in candidates:
                status = _prior_price(source, binding) if has_units else "absent"
                if status == "newer_current":
                    report["newer_current"].append(binding["canonical"]["id"])
                else:
                    eligible.append(binding)
    else:
        eligible = candidates
    for binding in eligible:
        destination.execute("UPDATE units SET points_json=? WHERE id=?",
                            (json.dumps(_historical_payload(binding), ensure_ascii=False), binding["canonical"]["id"]))
        report["restored"].append(binding["canonical"]["id"])
    return dict(report, status="verified")
