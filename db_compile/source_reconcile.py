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
    src = patch.get("source", {})
    if (not isinstance(src, dict) or not isinstance(src.get("url"), str) or
            not src["url"].startswith("https://") or
            not isinstance(src.get("sha256"), str) or
            not re.fullmatch(r"[0-9a-f]{64}", src["sha256"])):
        raise ValueError("A source URL and SHA-256 are required")
    if type(src.get("page")) is not int or src["page"] < 1:
        raise ValueError("A one-based source page is required")


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
        declared = item.get("source_date")
        if declared is not None or ordered:
            if not isinstance(declared, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", declared):
                raise ValueError("Each ordered revision requires an ISO source date")
            try:
                date.fromisoformat(declared)
            except ValueError as exc:
                raise ValueError("Invalid revision source date") from exc
            if previous is not None and declared <= previous:
                raise ValueError("Revision dates must be strictly increasing and unique")
            previous = declared
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
        for patch in manifest["patches"]:
            _validate(patch)
            identity = (patch["table"], tuple(sorted(patch["key"].items())))
            grouped.setdefault(identity, []).append(patch)
    chains = []
    for (table, key), patches in grouped.items():
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
            # A single legacy no-op retains its already-current behavior. Chains
            # must never revisit a state: suffix selection would be ambiguous.
            if updated in states and not (len(patches) == 1 and updated == current):
                raise ValueError(f"Ambiguous or duplicate reviewed state: {table}/{dict(key)}")
            states.append(updated)
            current = updated
        chains.append(RowChain(table, key, tuple(sorted(initial)), tuple(states), tuple(patches)))
    return tuple(chains)


def apply_patches(db_path, manifest=None, *, manifests=None):
    """Advance only an exact reviewed suffix; roll back every row on failure.

    Legacy callers pass one manifest. Ordered callers use ``manifests=[...]``
    or a JSON ``{"revisions": [...]}`` envelope. Metadata chronology validation
    is a separate pending contract; callers must not publish new source data yet.
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
            # Multiple matches only occur for the single permitted legacy no-op.
            position = matches[-1]
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
        conn.execute("CREATE TABLE IF NOT EXISTS official_rule_revisions (unit_id TEXT PRIMARY KEY, source_date TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS official_unit_sources (unit_id TEXT PRIMARY KEY, sources_json TEXT NOT NULL)")
        for item in declared:
            for uid in item.get("invalidate_translation_for", []):
                conn.execute("INSERT OR REPLACE INTO official_rule_revisions VALUES (?,?)", (uid, item["source_date"]))
            for uid, sources in item.get("unit_sources", {}).items():
                conn.execute("INSERT OR REPLACE INTO official_unit_sources VALUES (?,?)", (uid, json.dumps(sources, ensure_ascii=False)))
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
