"""Apply reviewed official corrections atomically, with exact prior-value guards.

The manifest is curated from cited source pages. This module deliberately does
not interpret PDF prose or infer an entity's rules from its points value.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from contextlib import closing
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
    table = patch.get("table")
    if table not in FIELDS:
        raise ValueError("Unsupported reconciliation table")
    key = patch.get("key", {})
    if set(key) != IDENTITY[table] or any(not v for v in key.values()):
        raise ValueError("A complete canonical identity is required")
    values = patch.get("to", {})
    if not values or not set(values) <= FIELDS[table] - IDENTITY[table]:
        raise ValueError("Invalid reconciliation fields")
    if patch.get("from") is not None and set(patch["from"]) != set(values):
        raise ValueError("Every changed field requires a prior value")
    src = patch.get("source", {})
    if not src.get("url", "").startswith("https://") or not re.fullmatch(r"[0-9a-f]{64}", src.get("sha256", "")):
        raise ValueError("A source URL and SHA-256 are required")
    if not isinstance(src.get("page"), int) or src["page"] < 1:
        raise ValueError("A one-based source page is required")


def apply_patches(db_path, manifest=None):
    """Fail the entire transaction on drift, missing rows or ambiguous identities."""
    manifest = manifest if manifest is not None else json.loads(MANIFEST.read_text(encoding="utf-8"))
    patches = manifest["patches"]
    for patch in patches:
        _validate(patch)
    report = {"applied": 0, "already": 0, "inserted": 0, "total": len(patches)}
    with closing(sqlite3.connect(str(db_path))) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        for p in patches:
            table, key, values = p["table"], p["key"], p["to"]
            fields = list(values)
            where = " AND ".join(f"{name}=?" for name in key)
            rows = conn.execute(f"SELECT {','.join(fields)} FROM {table} WHERE {where}", tuple(key.values())).fetchall()
            if len(rows) > 1:
                raise ValueError(f"Ambiguous official patch: {table}/{key}")
            if not rows:
                if p.get("from") is not None:
                    raise ValueError(f"Missing official patch target: {table}/{key}")
                combined = {**key, **values}
                conn.execute(f"INSERT INTO {table} ({','.join(combined)}) VALUES ({','.join('?' for _ in combined)})", tuple(combined.values()))
                report["inserted"] += 1
                continue
            actual = dict(zip(fields, rows[0]))
            if actual == values:
                report["already"] += 1
                continue
            if actual != p.get("from"):
                raise ValueError(f"Official patch prior-value mismatch: {table}/{key}")
            conn.execute(f"UPDATE {table} SET {','.join(f'{field}=?' for field in fields)} WHERE {where}", tuple(values.values()) + tuple(key.values()))
            report["applied"] += 1
        conn.execute("CREATE TABLE IF NOT EXISTS official_rule_revisions (unit_id TEXT PRIMARY KEY, source_date TEXT NOT NULL)")
        for uid in manifest.get("invalidate_translation_for", []):
            conn.execute("INSERT OR REPLACE INTO official_rule_revisions VALUES (?,?)", (uid, manifest["source_date"]))
        conn.execute("CREATE TABLE IF NOT EXISTS official_unit_sources (unit_id TEXT PRIMARY KEY, sources_json TEXT NOT NULL)")
        for uid, sources in manifest.get("unit_sources", {}).items():
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
