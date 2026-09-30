"""Explicit reviewed body coverage, separate from price and patch manifests.

No registry is loaded or inferred automatically. Promotion supplies declarations
and exact prior records in its own SQLite transaction. Prices stay in the MFM
ledger; coverage neither inserts units nor certifies bodies from price membership.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from urllib.parse import urlsplit


BODY_STATUSES = {
    "current_full_verified", "fields_only", "historical_snapshot",
    "newer_full_unavailable", "source_only_price",
}
BODY_FIELDS = {"models", "weapons", "abilities", "equipment", "composition", "keywords"}
_TABLE = "source_coverage_registry"


def _object(value, keys, label):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("Invalid " + label + " fields")


def _text(value, label):
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(ord(c) < 32 for c in value)):
        raise ValueError("Invalid " + label)


def _day(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Invalid " + label)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid " + label) from exc


def _stamp(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        raise ValueError("Invalid source capture timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid source capture timestamp") from exc


def _sources(sources):
    if not isinstance(sources, list):
        raise ValueError("Sources must be a list")
    seen, documents = set(), {}
    for src in sources:
        _object(src, {"url", "sha256", "kind", "page", "source_date", "captured_at"}, "source")
        _text(src["url"], "source URL")
        try:
            url = urlsplit(src["url"])
            port = url.port
        except ValueError as exc:
            raise ValueError("Invalid source URL") from exc
        if (url.scheme != "https" or not url.hostname or url.username is not None
                or url.password is not None or port == 0 or any(c.isspace() for c in src["url"])):
            raise ValueError("Invalid HTTPS source URL")
        if not isinstance(src["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", src["sha256"]):
            raise ValueError("Invalid source SHA-256")
        if src["kind"] not in ("pdf", "web", "preview_image"):
            raise ValueError("Invalid source kind")
        if src["kind"] == "web":
            if src["page"] is not None:
                raise ValueError("Web source page must be null")
        elif type(src["page"]) is not int or src["page"] < 1:
            raise ValueError("A one-based source page is required")
        if src["source_date"] is not None:
            _day(src["source_date"], "source date")
        _stamp(src["captured_at"])
        key = (src["url"], src["page"])
        if key in seen:
            raise ValueError("Duplicate source page")
        seen.add(key)
        document = (src["sha256"], src["kind"], src["source_date"], src["captured_at"])
        if src["url"] in documents and documents[src["url"]] != document:
            raise ValueError("Conflicting source document provenance")
        documents[src["url"]] = document


def _scope(scope, full=False, empty=False):
    if not isinstance(scope, list) or any(not isinstance(s, str) for s in scope):
        raise ValueError("Invalid body scope")
    if full:
        valid = scope == ["full_body"]
    elif empty:
        valid = scope == []
    else:
        valid = bool(scope) and len(set(scope)) == len(scope) and set(scope) <= BODY_FIELDS
    if not valid:
        raise ValueError("Invalid body scope")


def validate_manifest(manifest):
    """Return an independent strict declaration; never infer dates/status/scope."""
    _object(manifest, {"schema_version", "records"}, "coverage manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("Unsupported coverage schema version")
    if not isinstance(manifest["records"], list) or not manifest["records"]:
        raise ValueError("Nonempty coverage records are required")
    seen = set()
    for record in manifest["records"]:
        _object(record, {"identity", "reviewed_on", "body", "points"}, "coverage record")
        identity = record["identity"]
        _object(identity, {"unit_id", "name_en", "faction_id", "faction_slug", "faction_keywords"}, "identity")
        for name in ("name_en", "faction_id", "faction_slug"):
            _text(identity[name], name)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identity["faction_slug"]):
            raise ValueError("Invalid exact faction slug")
        if identity["unit_id"] is not None:
            _text(identity["unit_id"], "canonical unit ID")
        keywords = identity["faction_keywords"]
        if not isinstance(keywords, list):
            raise ValueError("Invalid faction keywords")
        for keyword in keywords:
            _text(keyword, "faction keyword")
        if len(set(keywords)) != len(keywords):
            raise ValueError("Duplicate faction keyword")
        _day(record["reviewed_on"], "review date")
        body = record["body"]
        _object(body, {"status", "scope", "effective_date", "sources", "retained_snapshot"}, "body")
        if not isinstance(body["status"], str) or body["status"] not in BODY_STATUSES:
            raise ValueError("Unknown body coverage status")
        status = body["status"]
        _scope(body["scope"], full=status in ("current_full_verified", "historical_snapshot"),
               empty=status in ("newer_full_unavailable", "source_only_price"))
        if status in ("current_full_verified", "historical_snapshot"):
            _day(body["effective_date"], "body effective date")
        elif body["effective_date"] is not None:
            # A preview/capture date cannot become a full body's legal-start date.
            raise ValueError("Unverified full body effective date must be null")
        _sources(body["sources"])
        if not body["sources"]:
            raise ValueError("Body status requires explicit source evidence")
        if status in ("current_full_verified", "historical_snapshot") and any(
                s["kind"] == "preview_image" for s in body["sources"]):
            raise ValueError("Preview evidence cannot certify a full body")
        retained = body["retained_snapshot"]
        if retained is not None:
            if status != "newer_full_unavailable" or identity["unit_id"] is None:
                raise ValueError("Retained body requires a canonical unavailable-newer identity")
            _object(retained, {"effective_date", "scope", "sources"}, "retained snapshot")
            _day(retained["effective_date"], "retained body effective date")
            _scope(retained["scope"], full=True)
            _sources(retained["sources"])
            if not retained["sources"] or any(s["kind"] == "preview_image" for s in retained["sources"]):
                raise ValueError("Retained full body requires full source evidence")
        points = record["points"]
        _object(points, {"status", "effective_date", "sources"}, "points")
        if points["status"] not in ("current_published", "historical", "unavailable"):
            raise ValueError("Unknown points status")
        if points["effective_date"] is not None:
            _day(points["effective_date"], "points effective date")
        _sources(points["sources"])
        if points["status"] == "unavailable":
            if points["sources"] or points["effective_date"] is not None:
                raise ValueError("Unavailable points cannot have price provenance")
        elif not points["sources"]:
            raise ValueError("Published/historical points require source evidence")
        if (identity["unit_id"] is None) != (status == "source_only_price"):
            raise ValueError("Source-only prices must not claim a canonical body ID")
        if status == "source_only_price" and points["status"] != "current_published":
            raise ValueError("Source-only price identity requires published price evidence")
        if status == "source_only_price" and body["sources"] != points["sources"]:
            raise ValueError("Source-only body limitation must cite the exact price evidence")
        for evidence in (body, points, retained):
            if evidence is None:
                continue
            if evidence["effective_date"] is not None and evidence["effective_date"] > record["reviewed_on"]:
                raise ValueError("Current/historical effective date is after review")
            for source in evidence["sources"]:
                if source["captured_at"][:10] > record["reviewed_on"]:
                    raise ValueError("Source capture is after review")
        key = _key(identity)
        if key in seen:
            raise ValueError("Duplicate coverage identity")
        seen.add(key)
    return copy.deepcopy(manifest)


def _key(identity):
    if identity["unit_id"] is not None:
        parts = ["canonical", identity["unit_id"]]
    else:
        parts = ["price", identity["faction_slug"], identity["name_en"].casefold()]
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"))


def _exists(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()


def _check_identity(conn, record):
    identity = record["identity"]
    uid = identity["unit_id"]
    if uid is not None:
        row = conn.execute("SELECT name_en,faction_id,keywords_json,points_json FROM units WHERE id=?", (uid,)).fetchone()
        if row is None or tuple(row[:2]) != (identity["name_en"], identity["faction_id"]):
            raise ValueError("Exact canonical coverage identity mismatch")
        try:
            keywords = json.loads(row[2] or "{}").get("faction_keywords", [])
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid canonical faction keywords") from exc
        if keywords != identity["faction_keywords"]:
            raise ValueError("Exact canonical faction keywords mismatch")
        if (record["body"]["status"] in ("current_full_verified", "historical_snapshot")
                or record["body"]["retained_snapshot"] is not None):
            if not conn.execute("SELECT 1 FROM models WHERE unit_id=? LIMIT 1", (uid,)).fetchone():
                raise ValueError("Verified full/retained body requires a stored model record")
        try:
            prices = json.loads(row[3] or "{}")
            marker = (prices.get("mfm") or {}).get("current")
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid canonical price provenance") from exc
        if record["points"]["status"] == "current_published" and marker is not True:
            raise ValueError("Canonical current points require an explicit current projection")
        if record["points"]["status"] == "historical" and marker is not False:
            raise ValueError("Canonical historical points require an explicit non-current projection")
        if record["points"]["status"] == "unavailable" and marker is True:
            raise ValueError("Current canonical price projection conflicts with unavailable points")
    else:
        # Do not attach a ledger-only name to a fuzzy sibling or invent a body.
        if conn.execute("SELECT 1 FROM units WHERE faction_id=? AND lower(name_en)=lower(?)",
                        (identity["faction_id"], identity["name_en"])).fetchone():
            raise ValueError("Source-only identity already has a canonical body")
    if not conn.execute("SELECT 1 FROM factions WHERE id=?", (identity["faction_id"],)).fetchone():
        raise ValueError("Unknown canonical faction")
    from db_compile.mfm import MFM_SLUG_TO_FACTION
    if MFM_SLUG_TO_FACTION.get(identity["faction_slug"]) != identity["faction_id"]:
        raise ValueError("Exact source faction does not match canonical faction")
    if identity["faction_id"] == "SM" and identity["faction_slug"] != "space-marines":
        chapter = identity["faction_slug"].replace("-", " ")
        if chapter not in {kw.casefold() for kw in identity["faction_keywords"]}:
            raise ValueError("Exact source chapter does not match faction keywords")
    if record["points"]["status"] == "current_published":
        if not _exists(conn, "official_mfm_points"):
            raise ValueError("Published price identity requires the exact staged ledger")
        rows = conn.execute(
            "SELECT source_url,source_sha256,fetched_at FROM official_mfm_points "
            "WHERE kind='unit' AND faction_slug=? AND lower(unit_name)=lower(?)",
            (identity["faction_slug"], identity["name_en"])).fetchall()
        actual = {(r[0], r[1], r[2]) for r in rows}
        expected = {(s["url"], s["sha256"], s["captured_at"]) for s in record["points"]["sources"]}
        if not actual or actual != expected:
            raise ValueError("Exact published price provenance mismatch")


def _stored(conn, key):
    if not _exists(conn, _TABLE):
        return None
    row = conn.execute("SELECT record_json FROM source_coverage_registry WHERE identity_key=?", (key,)).fetchone()
    if row is None:
        return None
    try:
        record = json.loads(row[0])
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid stored coverage JSON") from exc
    validate_manifest({"schema_version": 1, "records": [record]})
    if _key(record["identity"]) != key:
        raise ValueError("Stored coverage identity key mismatch")
    return record


def resolve_coverage(conn, *, unit_id=None, name_en=None, faction_slug=None):
    """Read one exact declaration or None; absent registries preserve legacy use.

    Source-only access requires both full English name and exact source slug.
    There is no name-only, fuzzy, price-based or historical-to-current fallback.
    """
    if unit_id is not None:
        if name_en is not None or faction_slug is not None:
            raise ValueError("Choose canonical ID or exact source-only identity")
        _text(unit_id, "canonical unit ID")
        key = _key({"unit_id": unit_id})
    else:
        _text(name_en, "full source name")
        _text(faction_slug, "exact source faction")
        key = _key({"unit_id": None, "name_en": name_en, "faction_slug": faction_slug})
    record = _stored(conn, key)
    if record is not None:
        _check_identity(conn, record)
    return record


def apply_coverage(conn: sqlite3.Connection, manifest, *, expected_records):
    """Stage a guarded delta inside the caller's active promotion transaction.

    expected_records is aligned with manifest.records: each exact previous
    declaration, or None for an absent identity. Unmentioned records/history are
    preserved. This function never commits, opens a DB, or changes body/price data.
    A savepoint also undoes its writes if the caller catches an application error.
    """
    candidate = validate_manifest(manifest)
    records = candidate["records"]
    if not isinstance(expected_records, list) or len(expected_records) != len(records):
        raise ValueError("Exact aligned prior coverage records are required")
    if not conn.in_transaction:
        raise ValueError("Coverage application requires the caller's active transaction")
    conn.execute("SAVEPOINT source_coverage_apply")
    try:
        for record, expected in zip(records, expected_records):
            _check_identity(conn, record)
            previous = _stored(conn, _key(record["identity"]))
            if previous != expected:
                raise ValueError("Exact prior coverage record mismatch")
            if previous is not None and record != previous:
                if record["identity"] != previous["identity"]:
                    raise ValueError("Coverage identity cannot be reassigned")
                if record["reviewed_on"] < previous["reviewed_on"]:
                    raise ValueError("Coverage review date would downgrade")
                old_body = previous["body"]
                old_snapshot = old_body["retained_snapshot"] or old_body
                if record["body"]["status"] == "current_full_verified":
                    old_date = old_snapshot["effective_date"]
                    if old_date and record["body"]["effective_date"] < old_date:
                        raise ValueError("Verified body date would downgrade")
                    if old_body["status"] == "newer_full_unavailable" and (
                            {s["sha256"] for s in record["body"]["sources"]}
                            <= {s["sha256"] for s in old_snapshot["sources"]}):
                        raise ValueError("Retained sources cannot recertify an unavailable newer body")
        conn.execute("CREATE TABLE IF NOT EXISTS source_coverage_registry "
                     "(identity_key TEXT PRIMARY KEY,record_json TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS source_coverage_history "
                     "(identity_key TEXT NOT NULL,record_sha256 TEXT NOT NULL,record_json TEXT NOT NULL,"
                     "PRIMARY KEY(identity_key,record_sha256))")
        for record in records:
            key = _key(record["identity"])
            payload = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            conn.execute("INSERT OR IGNORE INTO source_coverage_history VALUES (?,?,?)", (key, digest, payload))
            conn.execute("INSERT OR REPLACE INTO source_coverage_registry VALUES (?,?)", (key, payload))
        conn.execute("RELEASE SAVEPOINT source_coverage_apply")
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT source_coverage_apply")
        conn.execute("RELEASE SAVEPOINT source_coverage_apply")
        raise
    return {"records": len(records), "schema_version": 1}
