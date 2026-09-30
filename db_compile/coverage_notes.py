"""Whole, exact coverage qualifiers for existing consumer note surfaces.

The registry owns validation and identity matching. This module never derives
coverage from SQL existence, price membership, capture dates or faction names.
Missing declarations return None so legacy consumers keep their exact payload.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Collection
from dataclasses import dataclass

from db_compile.source_coverage import resolve_coverage


class CoverageError(ValueError):
    """An explicit declaration is invalid; callers must not use legacy fallback."""


def _provenance(sources: list[dict]) -> str:
    if not sources:
        return "none"
    parts = []
    for source in sources:
        page = "; page " + str(source["page"]) if source["page"] is not None else ""
        day = source["source_date"] or "unavailable"
        parts.append(
            f'{source["url"]} [kind {source["kind"]}{page}; SHA-256 {source["sha256"]}; '
            f'source date {day}; captured {source["captured_at"]}]'
        )
    return " / ".join(parts)


def describe_coverage(record: dict) -> str:
    """Render a record already validated by resolve_coverage, without truncation."""
    identity, body, points = record["identity"], record["body"], record["points"]
    uid = identity["unit_id"] or "none (no canonical body)"
    keywords = ", ".join(identity["faction_keywords"]) or "none"
    note = (
        f'Source coverage: {identity["name_en"]} [unit_id {uid}; faction '
        f'{identity["faction_id"]}; source faction {identity["faction_slug"]}; '
        f'faction keywords {keywords}; reviewed {record["reviewed_on"]}]. '
        f'Body: {body["status"]}; verified scope: {", ".join(body["scope"]) or "none"}; '
    )
    if body["effective_date"] is not None:
        note += f'body effective {body["effective_date"]}. '
    else:
        note += "body effective date unverified. "
    status = body["status"]
    if status == "fields_only":
        note += "Only the listed fields are verified; full body unverified. "
    elif status == "historical_snapshot":
        note += "Historical full body, not verified current rules. "
    elif status == "newer_full_unavailable":
        note += "The newer full body unavailable; "
        retained = body["retained_snapshot"]
        if retained is None:
            note += "no verified retained body; stored rows are body-unverified. "
        else:
            note += (
                f'retained full_body effective {retained["effective_date"]}, '
                'not verified current rules. Retained body provenance: '
                + _provenance(retained["sources"]) + ". "
            )
    elif status == "source_only_price":
        note += "Price evidence only; no canonical body, models or weapons. "
    note += "Body provenance: " + _provenance(body["sources"]) + ". "
    date_note = ("points effective " + points["effective_date"]
                 if points["effective_date"] is not None else "points effective date unverified")
    note += (
        f'Points: {points["status"]}; {date_note}; price provenance: '
        + _provenance(points["sources"]) + ". "
        "A published price does not certify body, composition/equipment or legal-list eligibility; "
        "source dates and captures are provenance, not inferred effective dates."
    )
    return note


def _resolve(conn: sqlite3.Connection, **identity: str | None) -> dict | None:
    """Keep invalid explicit declarations distinct from missing legacy metadata."""
    try:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_coverage_registry'"
        ).fetchone():
            return None
        record = resolve_coverage(conn, **identity)
    except (ValueError, sqlite3.DatabaseError) as exc:
        raise CoverageError("Source coverage invalid: " + str(exc)) from exc
    return record


def coverage_note(conn: sqlite3.Connection, **identity) -> str | None:
    """Resolve one strict canonical/source-only identity, or preserve legacy None."""
    record = _resolve(conn, **identity)
    return describe_coverage(record) if record is not None else None


@dataclass(frozen=True)
class BodySupport:
    supported: bool
    note: str | None = None
    status: str | None = None
    scope: frozenset[str] = frozenset()


def body_support(conn: sqlite3.Connection, *, required_fields: Collection[str],
                 **identity: str | None) -> BodySupport:
    """Allow only declared fields or a verified loadable full/retained body.

    Callers state the body fields their existing algorithms consume. Prices and
    explicit user model/loadout choices cannot upgrade missing body verification.
    Missing metadata preserves the legacy path; full body loadability and exact
    identity are checked by the strict registry before any consumer assembly.
    """
    record = _resolve(conn, **identity)
    if record is None:
        return BodySupport(True)
    body = record["body"]
    status, scope = body["status"], frozenset(body["scope"])
    full = status in ("current_full_verified", "historical_snapshot") or (
        status == "newer_full_unavailable" and body["retained_snapshot"] is not None)
    supported = full or (status == "fields_only" and set(required_fields) <= scope)
    note = describe_coverage(record)
    if not supported:
        missing = sorted(set(required_fields) - scope)
        note += " Calculation body-unverified; required fields not verified: " + ", ".join(missing) + "."
    return BodySupport(supported, note, status, scope)
