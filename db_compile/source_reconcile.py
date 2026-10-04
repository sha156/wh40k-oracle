"""Apply reviewed official corrections atomically, with exact prior-value guards.

The manifest is curated from cited source pages. This module deliberately does
not interpret PDF prose or infer an entity's rules from its points value.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


MANIFEST = Path(__file__).with_name("source_reconcile_patches.json")
FIELDS = {
    "units": {"id", "faction_id", "name_en", "keywords_json", "version"},
    "models": {"unit_id", "name", "m", "t", "sv", "invuln", "w", "ld", "oc", "count_options_json"},
    "weapons": {"id", "unit_id", "name_en", "range", "a", "bs_ws", "s", "ap", "d", "keywords_json"},
    "abilities": {"id", "owner_id", "scope", "name_en", "text_zh"},
    "stratagems": {"id", "name_en", "faction", "detachment", "phase", "text_zh", "cp_cost"},
    "detachments": {"id", "name_en", "faction", "detachment_name", "rule_text"},
    "enhancements": {"id", "faction_id", "detachment_id", "detachment_name", "name", "description", "cost"},
    "datasheets": {"id", "name", "faction_id", "source_id", "loadout", "transport", "leader_head", "leader_footer"},
}
IDENTITY = {table: {"id"} for table in FIELDS}
IDENTITY["models"] = {"unit_id", "name"}


def _iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("An ISO source date is required")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid source date") from exc
    return value


def _https_url(value):
    if not isinstance(value, str) or any(ch.isspace() for ch in value):
        raise ValueError("A valid HTTPS source URL is required")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid source URL") from exc
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or port == 0):
        raise ValueError("A valid HTTPS source URL is required")


def _validate_source(src):
    if not isinstance(src, dict):
        raise ValueError("An official source must be an object")
    allowed = {"url", "sha256", "page", "title", "kind", "published", "article",
               "source_date", "date", "version"}
    if not set(src) <= allowed:
        raise ValueError("Unsupported official source metadata")
    _https_url(src.get("url"))
    if not isinstance(src.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", src["sha256"]):
        raise ValueError("A source SHA-256 is required")
    if type(src.get("page")) is not int or src["page"] < 1:
        raise ValueError("A one-based source page is required")
    for name in ("title", "kind", "version"):
        if name in src and (not isinstance(src[name], str) or not src[name].strip()):
            raise ValueError(f"Invalid source {name}")
    for name in ("published", "source_date", "date"):
        if name in src:
            _iso_date(src[name])
    if "article" in src:
        _https_url(src["article"])


def _validate_sources(sources):
    if not isinstance(sources, list) or not sources:
        raise ValueError("A nonempty official sources list is required")
    identities, documents = set(), {}
    for src in sources:
        _validate_source(src)
        identity = (src["url"], src["page"])
        if identity in identities:
            raise ValueError("Duplicate or conflicting official source identity")
        identities.add(identity)
        # Distinct cited pages of one document must agree on its bytes and
        # optional publication/version declarations, not only its URL.
        document = tuple((name, src.get(name)) for name in
                         ("sha256", "published", "source_date", "date", "version"))
        if src["url"] in documents and documents[src["url"]] != document:
            raise ValueError("Conflicting official source document")
        documents[src["url"]] = document


def _validate_metadata(manifest):
    ids = manifest.get("invalidate_translation_for", [])
    sources = manifest.get("unit_sources", {})
    if (not isinstance(ids, list) or any(not isinstance(uid, str) or not uid.strip() for uid in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("Unique canonical translation-invalidation IDs are required")
    if not isinstance(sources, dict) or any(not isinstance(uid, str) or not uid.strip() for uid in sources):
        raise ValueError("Official unit_sources requires canonical IDs and source lists")
    if ids or sources or "source_date" in manifest:
        _iso_date(manifest.get("source_date"))
    for value in sources.values():
        _validate_sources(value)
    if any(isinstance(name, str) and "coverage" in name for name in manifest):
        raise ValueError("Coverage metadata is not supported by this restoration contract")


def _validate_source_chronology(snapshots):
    """Exact snapshot and document continuity, without guessing version ranks."""
    seen, previous, documents, artifacts = [], None, {}, {}
    for _day, sources in snapshots:
        if sources != previous and sources in seen:
            raise ValueError("Revisited official source provenance")
        seen.append(sources)
        previous = sources
        for src in sources:
            url, digest = src["url"], src["sha256"]
            artifact = (url, digest)
            known = artifact in artifacts
            if known:
                for name in ("published", "source_date", "date", "version"):
                    prior = artifacts[artifact].get(name)
                    if prior is not None and src.get(name) != prior:
                        raise ValueError("Conflicting immutable official source metadata")
            artifacts[artifact] = src
            if url in documents and documents[url]["sha256"] != digest:
                if known:
                    raise ValueError("Revisited official source document")
                for name in ("published", "source_date", "date"):
                    prior = documents[url].get(name)
                    if prior is not None and (name not in src or src[name] < prior):
                        raise ValueError("Official source date would downgrade")
            documents[url] = src


def _validate(patch):
    if not isinstance(patch, dict):
        raise ValueError("An official patch must be an object")
    table = patch.get("table")
    if not isinstance(table, str) or table not in FIELDS:
        raise ValueError("Unsupported reconciliation table")
    key = patch.get("key", {})
    if not isinstance(key, dict) or set(key) != IDENTITY[table] or any(
            not isinstance(v, str) or not v for v in key.values()):
        raise ValueError("A complete canonical identity is required")
    values = patch.get("to", {})
    if (not isinstance(values, dict) or not values or
            not set(values) <= FIELDS[table] - IDENTITY[table]):
        raise ValueError("Invalid reconciliation fields")
    if "from" not in patch:
        raise ValueError("An explicit prior value or absent state is required")
    prior = patch["from"]
    if prior is not None and (not isinstance(prior, dict) or set(prior) != set(values)):
        raise ValueError("Every changed field requires a prior value")
    for value in list(values.values()) + (list(prior.values()) if prior is not None else []):
        if value is not None and (type(value) not in (str, int, float) or
                                  isinstance(value, float) and not math.isfinite(value)):
            raise ValueError("Reconciliation values must be finite SQLite scalars")
    _validate_source(patch.get("source"))
    additional = patch.get("additional_sources", [])
    if not isinstance(additional, list):
        raise ValueError("Additional sources must be a list")
    if additional:
        _validate_sources([patch["source"], *additional])


@dataclass(frozen=True)
class RowChain:
    """Complete reviewed states for one table and complete canonical identity."""

    table: str
    key: tuple
    fields: tuple
    states: tuple
    transitions: tuple


def _ordered_manifests(manifest, manifests):
    if manifest is not None and manifests is not None:
        raise ValueError("Supply a legacy manifest or ordered manifests, not both")
    ordered = True
    if manifests is None:
        manifest = manifest if manifest is not None else json.loads(MANIFEST.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("An official manifest must be an object")
        if "revisions" in manifest:
            if set(manifest) != {"revisions"}:
                raise ValueError("A revision envelope cannot contain a separate manifest")
            manifests = manifest["revisions"]
        else:
            manifests = [manifest]
            ordered = False
    if not isinstance(manifests, (list, tuple)) or not manifests:
        raise ValueError("At least one reviewed revision manifest is required")
    previous = None
    for item in manifests:
        if not isinstance(item, dict) or not isinstance(item.get("patches"), list):
            raise ValueError("Each revision requires a patches list")
        _validate_metadata(item)
        declared = item.get("source_date")
        if declared is not None or ordered:
            _iso_date(declared)
            if previous is not None and declared <= previous:
                raise ValueError("Revision dates must be strictly increasing and unique")
            previous = declared
    source_states = {}
    for item in manifests:
        for uid, sources in item.get("unit_sources", {}).items():
            source_states.setdefault(uid, []).append((item["source_date"], sources))
    for snapshots in source_states.values():
        _validate_source_chronology(snapshots)
    return copy.deepcopy(manifests)


def compile_revision_chain(manifests):
    """Validate and compile dated reviewed manifests without opening SQLite.

    Dates are strictly increasing, never sorted or guessed. Later first-touch
    guards fill earlier states because those fields were previously unchanged.
    """
    return _compile_rows(_ordered_manifests(None, manifests))


def _compile_rows(manifests):
    """Also support legacy flat transitions in their explicit patch order."""
    grouped = {}
    for manifest in manifests:
        citations = [src for sources in manifest.get("unit_sources", {}).values() for src in sources]
        for patch in manifest["patches"]:
            _validate(patch)
            citations.extend([patch["source"], *patch.get("additional_sources", [])])
            identity = (patch["table"], tuple(sorted(patch["key"].items())))
            grouped.setdefault(identity, []).append((manifest, patch))
        documents = {}
        for src in citations:
            known = documents.setdefault(src["url"], {})
            for field in ("sha256", "published", "source_date", "date", "version"):
                if field in src:
                    if field in known and known[field] != src[field]:
                        raise ValueError("Conflicting source declarations within a reviewed revision")
                    known[field] = src[field]
    chains = []
    for (table, key), declarations in grouped.items():
        patches = [patch for _, patch in declarations]
        initial = {}
        for patch in patches:
            for field in patch["to"]:
                if field not in initial:
                    initial[field] = (patch["from"] if patch["from"] is not None else patch["to"])[field]
        current = None if patches[0]["from"] is None else initial
        states = [current]
        for index, patch in enumerate(patches):
            prior = patch["from"]
            if prior is None:
                if index != 0:
                    raise ValueError(f"Conflicting absent-state declaration: {table}/{dict(key)}")
                updated = {**initial, **patch["to"]}
            else:
                if {field: current[field] for field in prior} != prior:
                    raise ValueError(f"Contradictory revision continuity: {table}/{dict(key)}")
                updated = {**current, **patch["to"]}
            # A dated unit reversal needs independently declared source anchors;
            # repeated field values alone cannot identify its current position.
            if updated in states and not (len(patches) == 1 and updated == current):
                if updated == current or table != "units":
                    raise ValueError(f"Ambiguous or duplicate reviewed state: {table}/{dict(key)}")
                _unit_checkpoints(dict(key)["id"], declarations)
            states.append(updated)
            current = updated
        chains.append(RowChain(table, key, tuple(sorted(initial)), tuple(states), tuple(patches)))
    return tuple(chains)


def _unit_checkpoints(uid, declarations):
    """Bind every transition to an explicit dated unit source declaration."""
    checkpoints, previous = [], None
    for manifest, patch in declarations:
        day = _iso_date(manifest.get("source_date"))
        sources = manifest.get("unit_sources", {}).get(uid)
        if not sources or previous is not None and day <= previous:
            raise ValueError(f"Dated unit reversal requires explicit source checkpoints: {uid}")
        if any(src.get("source_date", day) != day for src in sources):
            raise ValueError(f"Unit source checkpoint date does not bind revision: {uid}")
        for citation in [patch["source"], *patch.get("additional_sources", [])]:
            if not any(all(src.get(name) == value for name, value in citation.items())
                       for src in sources):
                raise ValueError(f"Unit source checkpoint does not bind patch evidence: {uid}")
        checkpoints.append((day, sources))
        previous = day
    _validate_source_chronology(checkpoints)
    return checkpoints


def _select_position(conn, chain, manifests, matches):
    """Use preexisting authority and the entire guarded row, before any writes."""
    declarations = [(item, patch) for item in manifests for patch in item["patches"]
                    if patch["table"] == chain.table
                    and tuple(sorted(patch["key"].items())) == chain.key]
    key = dict(chain.key)
    uid = key.get("id") if chain.table == "units" else key.get("unit_id")
    repeated = any(state in chain.states[:index] for index, state in enumerate(chain.states)
                   if index > 0)
    legacy_noop = len(chain.transitions) == 1 and chain.states[0] == chain.states[1]
    if uid is None:
        return matches[-1]
    current, history = _read_source_history(conn, uid)
    # Validate incoming conflicts before allowing a checkpoint to select rows.
    combined = dict(history)
    for item in manifests:
        sources = item.get("unit_sources", {}).get(uid)
        if sources is not None:
            day = item["source_date"]
            if day in combined and combined[day] != sources:
                raise ValueError(f"Conflicting official source identity: {uid}/{day}")
            combined[day] = sources
    _validate_source_chronology([(day, combined[day]) for day in sorted(combined)])
    if repeated and not legacy_noop:
        checkpoints = _unit_checkpoints(uid, declarations)
        if not history:
            raise ValueError(f"Dated unit reversal requires preexisting source history: {uid}")
        latest = max(history)
        positions = [index + 1 for index, (day, sources) in enumerate(checkpoints)
                     if day == latest and sources == current and index + 1 in matches]
        if len(positions) != 1:
            raise ValueError(f"Official source checkpoint and guarded row disagree: {uid}")
        return positions[0]
    position = matches[-1]
    if position < len(chain.transitions) and history:
        last_day = declarations[-1][0].get("source_date")
        if last_day is None or max(history) > last_day:
            raise ValueError(f"Older official revision cannot change newer checkpoint: {uid}")
    return position


def _single_metadata_row(conn, table, columns, uid):
    rows = conn.execute(f"SELECT {columns} FROM {table} WHERE unit_id=?", (uid,)).fetchall()
    if len(rows) > 1:
        raise ValueError(f"Ambiguous official provenance: {table}/{uid}")
    return rows[0] if rows else None


def _decode_sources(raw):
    try:
        sources = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("Malformed official sources JSON") from exc
    _validate_sources(sources)
    return sources


def _read_source_history(conn, uid):
    """Validate only preexisting provenance, without writes or date adoption.

    Missing tables are empty history, not authority to guess a checkpoint.
    An undated current list remains separate from the dated history. Callers
    must not use incoming declarations to manufacture preexisting authority.
    """
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
        "('official_unit_sources','official_unit_source_revisions')")}
    row = (_single_metadata_row(conn, "official_unit_sources", "sources_json", uid)
           if "official_unit_sources" in tables else None)
    current = _decode_sources(row[0]) if row else None
    history = {}
    if "official_unit_source_revisions" in tables:
        for day, raw in conn.execute(
                "SELECT source_date,sources_json FROM official_unit_source_revisions WHERE unit_id=?", (uid,)):
            _iso_date(day)
            if day in history:
                raise ValueError(f"Ambiguous official source chronology: {uid}/{day}")
            history[day] = _decode_sources(raw)
    if history:
        if current != history[sorted(history)[-1]]:
            raise ValueError(f"Official source provenance drift: {uid}")
        _validate_source_chronology([(day, history[day]) for day in sorted(history)])
    return current, history


def _restore_sources(conn, uid, incoming):
    """Merge exact dated snapshots; an unrecognized current list is drift.

    Legacy lists can be anchored only to an exactly matching declaration.
    Never infer their date from a unit's rule date or from PDF URL spelling.
    """
    current, history = _read_source_history(conn, uid)
    if not history and current is not None and not any(current == value for _, value in incoming):
        raise ValueError(f"Unrecognized legacy official source provenance: {uid}")
    combined = dict(history)
    for day, sources in incoming:
        if day in combined and combined[day] != sources:
            raise ValueError(f"Conflicting official source identity: {uid}/{day}")
        combined[day] = sources
    ordered = sorted(combined)
    _validate_source_chronology([(day, combined[day]) for day in ordered])
    final = combined[ordered[-1]]
    for day, sources in incoming:
        if day not in history:
            conn.execute("INSERT INTO official_unit_source_revisions VALUES (?,?,?)",
                         (uid, day, json.dumps(sources, ensure_ascii=False)))
    if current is None:
        conn.execute("INSERT INTO official_unit_sources VALUES (?,?)",
                     (uid, json.dumps(final, ensure_ascii=False)))
    elif current != final:
        conn.execute("UPDATE official_unit_sources SET sources_json=? WHERE unit_id=?",
                     (json.dumps(final, ensure_ascii=False), uid))


def _restore_metadata(conn, manifests):
    conn.execute("CREATE TABLE IF NOT EXISTS official_rule_revisions (unit_id TEXT PRIMARY KEY, source_date TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS official_unit_sources (unit_id TEXT PRIMARY KEY, sources_json TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS official_unit_source_revisions "
                 "(unit_id TEXT NOT NULL, source_date TEXT NOT NULL, sources_json TEXT NOT NULL, "
                 "PRIMARY KEY(unit_id,source_date))")
    revisions, sources = {}, {}
    for item in manifests:
        for uid in item.get("invalidate_translation_for", []):
            revisions[uid] = item["source_date"]
        for uid, value in item.get("unit_sources", {}).items():
            sources.setdefault(uid, []).append((item["source_date"], value))
    for uid in dict.fromkeys([*revisions, *sources]):
        targets = conn.execute("SELECT id FROM units WHERE id=?", (uid,)).fetchall()
        if len(targets) != 1:
            raise ValueError(f"{'Missing' if not targets else 'Ambiguous'} official metadata target: {uid}")
        # Validate existing rule metadata even when only sources are declared.
        row = _single_metadata_row(conn, "official_rule_revisions", "source_date", uid)
        if row:
            _iso_date(row[0])
        if uid in revisions:
            day = revisions[uid]
            if row is None:
                conn.execute("INSERT INTO official_rule_revisions VALUES (?,?)", (uid, day))
            elif day > row[0]:
                conn.execute("UPDATE official_rule_revisions SET source_date=? WHERE unit_id=?", (day, uid))
        if uid in sources:
            _restore_sources(conn, uid, sources[uid])


def apply_patches(db_path, manifest=None, *, manifests=None):
    """Advance only an exact reviewed suffix; roll back every row on failure.

    Legacy callers pass one manifest. Ordered callers use ``manifests=[...]``
    or a JSON ``{"revisions": [...]}`` envelope. Rows and exact dated provenance
    snapshots share one transaction. Legacy provenance must match a declared
    source list before adoption; unknown lists and same-date conflicts fail.
    Source syntax validation does not verify the actual promoted PDF bytes.
    """
    declared = _ordered_manifests(manifest, manifests)
    chains = _compile_rows(declared)
    report = {"applied": 0, "already": 0, "inserted": 0,
              "total": sum(len(item["patches"]) for item in declared)}
    with closing(sqlite3.connect(str(db_path))) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        for chain in chains:
            table, key, fields = chain.table, dict(chain.key), chain.fields
            where = " AND ".join(f"{name}=?" for name in key)
            rows = conn.execute(f"SELECT {','.join(fields)} FROM {table} WHERE {where}", tuple(key.values())).fetchall()
            if len(rows) > 1:
                raise ValueError(f"Ambiguous official patch: {table}/{key}")
            actual = dict(zip(fields, rows[0])) if rows else None
            matches = [index for index, state in enumerate(chain.states) if actual == state]
            if not matches:
                if actual is None:
                    raise ValueError(f"Missing official patch target: {table}/{key}")
                raise ValueError(f"Official patch prior-value mismatch: {table}/{key}")
            position = _select_position(conn, chain, declared, matches)
            report["already"] += position
            for index in range(position, len(chain.transitions)):
                if chain.states[index] is None:
                    combined = {**key, **chain.states[index + 1]}
                    conn.execute(f"INSERT INTO {table} ({','.join(combined)}) VALUES ({','.join('?' for _ in combined)})", tuple(combined.values()))
                    report["inserted"] += 1
                else:
                    values = chain.transitions[index]["to"]
                    conn.execute(f"UPDATE {table} SET {','.join(f'{field}=?' for field in values)} WHERE {where}", tuple(values.values()) + tuple(key.values()))
                    report["applied"] += 1
        _restore_metadata(conn, declared)
    return report


def requires_current_english(conn, unit_id):
    """Old translations cannot override a newer reviewed official rule."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='official_rule_revisions'").fetchone():
        return False
    return conn.execute("SELECT 1 FROM official_rule_revisions WHERE unit_id=?", (unit_id,)).fetchone() is not None


def unit_sources(conn, unit_id):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='official_unit_sources'").fetchone():
        return []
    row = conn.execute("SELECT sources_json FROM official_unit_sources WHERE unit_id=?", (unit_id,)).fetchone()
    return json.loads(row[0]) if row else []


def stale_translation_ids(db_path, documents):
    """Identify obsolete Chinese chunks without touching official PDF chunks."""
    with closing(sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='official_rule_revisions'").fetchone():
            return []
        names = {row[0] for row in conn.execute(
            "SELECT z.name_zh FROM unit_zh_detail z JOIN official_rule_revisions r "
            "ON r.unit_id=z.canonical_id")}
    return [key for key, doc in documents.items()
            if doc.metadata.get("source") == "blacklibrary" and doc.metadata.get("unit") in names]


def prune_index(db_path, index_path):
    """Prune a trusted local FAISS asset, retaining an exact pre-change backup."""
    import shutil
    import tempfile
    from langchain_community.vectorstores import FAISS
    from langchain_core.embeddings import Embeddings

    class NoEmbedding(Embeddings):
        def embed_documents(self, texts):
            raise RuntimeError("Pruning must not generate embeddings")

        def embed_query(self, text):
            raise RuntimeError("Pruning must not generate embeddings")

    store = FAISS.load_local(str(index_path), NoEmbedding(), allow_dangerous_deserialization=True)
    ids = stale_translation_ids(db_path, store.docstore._dict)
    before = store.index.ntotal
    backup = None
    if ids:
        backup = Path(tempfile.mkdtemp(prefix="wh40k-before-translation-prune-"))
        for name in ("index.faiss", "index.pkl"):
            shutil.copy2(Path(index_path) / name, backup / name)
        store.delete(ids)
        store.save_local(str(index_path))
    return {"before": before, "removed": len(ids), "after": store.index.ntotal,
            "backup": str(backup) if backup else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("db/wh40k.sqlite"))
    parser.add_argument("--prune-index", type=Path,
                        help="Remove obsolete translations from this trusted local FAISS index")
    args = parser.parse_args()
    print(json.dumps(apply_patches(args.db), indent=2))
    if args.prune_index:
        print(json.dumps(prune_index(args.db, args.prune_index), indent=2))


if __name__ == "__main__":
    main()
