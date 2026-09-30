"""Compare verdicts only after validating actual question/expectation contracts.

Usage: compare_bench_runs.py [--allow-different-gold] BASE.json NEW.json
Different gold requires an explicit override and is never a regression claim.
Historical results without provenance use their detailed fields; source
equivalence remains unverified. This command does not execute or rejudge answers.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__:
    from .benchmark_json import loads_benchmark_json
else:
    from benchmark_json import loads_benchmark_json


_CONTRACT = ("faction", "question", "gold", "gold_type")
_TYPES = {"stat", "weapon", "ability", "rule", "points"}
_VERDICTS = {"✅", "⚠️", "❌"}
_INTRINSIC_63 = {
    "id": 63, "faction": "帝国卫队",
    "question": "坦克指挥官的坦克命令有什么效果？", "gold_type": "ability",
}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _positive_int(value):
    return type(value) is int and value > 0


def _validate_source(source, row_count):
    if not isinstance(source, dict):
        raise ValueError("summary.gold_source must be an object")
    for key in ("path", "version"):
        if not _text(source.get(key)):
            raise ValueError(f"gold_source.{key} must be nonempty text")
    if not re.fullmatch(r"v\d+(?:\.\d+)?", source["version"]):
        raise ValueError("gold_source.version must be a benchmark version such as v3.6")
    sha = source.get("sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("gold_source.sha256 must be a lowercase SHA-256 digest")
    if not _positive_int(source.get("edition")):
        raise ValueError("gold_source.edition must be a positive integer")
    if not _positive_int(source.get("total")) or source["total"] < row_count:
        raise ValueError("gold_source.total must be an integer >= executed rows")
    notes = source.get("source_limitations")
    if not isinstance(notes, list) or not notes or not all(_text(n) for n in notes):
        raise ValueError("gold_source.source_limitations must be nonempty text entries")


def _read_run(path):
    data = loads_benchmark_json(path.read_bytes())
    if not isinstance(data, dict):
        raise ValueError("result root must be an object")
    details = data.get("details")
    if not isinstance(details, list) or not details:
        raise ValueError("details must be a nonempty list")
    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        raise ValueError("summary must be an object when present")
    rows, axes = {}, None
    for index, row in enumerate(details):
        label = f"details[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{label} must be an object")
        qid = row.get("id")
        if not _positive_int(qid):
            raise ValueError(f"{label}.id must be a positive non-boolean integer")
        if qid in rows:
            raise ValueError(f"{label}.id duplicates #{qid}")
        for key in ("question", "faction"):
            if not _text(row.get(key)):
                raise ValueError(f"{label}.{key} must be nonempty text")
        kind = row.get("gold_type")
        if not isinstance(kind, str) or kind not in _TYPES:
            raise ValueError(f"{label}.gold_type is missing or unsupported")
        intrinsic = ("gold" in row and row["gold"] is None
                     and all(row.get(k) == v for k, v in _INTRINSIC_63.items()))
        if not intrinsic and not _text(row.get("gold")):
            raise ValueError(f"{label}.gold must be present and nonempty; only original #63 may be null")
        if "gold_metadata" in row and not isinstance(row["gold_metadata"], dict):
            raise ValueError(f"{label}.gold_metadata must be an object")
        metadata_identity = row.get("gold_metadata", {}).get("canonical_id")
        direct_identity = row.get("canonical_id")
        for value in (direct_identity, metadata_identity):
            if value is not None and not _text(value):
                raise ValueError(f"{label}.canonical_id must be nonempty text when present")
        if direct_identity is not None and metadata_identity is not None and direct_identity != metadata_identity:
            raise ValueError(f"{label}.canonical_id conflicts with gold_metadata.canonical_id")
        identity = direct_identity if direct_identity is not None else metadata_identity
        if intrinsic and identity is not None and identity != "000000680":
            raise ValueError(f"{label}.gold null contract has a different canonical_id")
        current_axes = (("verdict",) if "verdict" in row
                        else ("retrieval_verdict", "generation_verdict"))
        if "verdict" in row and any(k in row for k in ("retrieval_verdict", "generation_verdict")):
            raise ValueError(f"{label} has conflicting verdict axes")
        for key in current_axes:
            value = row.get(key)
            if not isinstance(value, str) or value not in _VERDICTS:
                raise ValueError(f"{label}.{key} is missing or invalid")
        if axes is not None and axes != current_axes:
            raise ValueError("verdict axes differ within the result")
        axes = current_axes
        rows[qid] = row
    source = summary.get("gold_source")
    if "gold_source" in summary:
        _validate_source(source, len(rows))
    totals = []
    if "total" in summary:
        totals.append(summary["total"])
    if "results" in summary:
        if not isinstance(summary["results"], dict):
            raise ValueError("summary.results must be an object")
        if "total" in summary["results"]:
            totals.append(summary["results"]["total"])
    if any(type(total) is not int or total != len(rows) for total in totals):
        raise ValueError("summary executed total must equal details row count")
    return rows, source, axes


def _render(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _field(mapping, key):
    return _render(mapping[key]) if key in mapping else "<absent>"


def _differences(base, new, base_source, new_source):
    """Return contract differences separately from unavailable historical metadata."""
    changes, unknowns = [], []
    only_base, only_new = sorted(base.keys() - new.keys()), sorted(new.keys() - base.keys())
    if only_base:
        changes.append(f"Only base IDs: {only_base}")
    if only_new:
        changes.append(f"Only new IDs: {only_new}")
    if base_source is not None and new_source is not None:
        # Locations can change without changing gold. Compare all other declared fields.
        for key in sorted((base_source.keys() | new_source.keys()) - {"path"}):
            if key not in base_source or key not in new_source or base_source[key] != new_source[key]:
                changes.append(f"gold_source.{key}: {_field(base_source, key)} -> "
                               f"{_field(new_source, key)}")
    for qid in sorted(base.keys() & new.keys()):
        before, after = base[qid], new[qid]
        for key in _CONTRACT:
            if before[key] != after[key]:
                changes.append(f"#{qid} {key}: {_render(before[key])} -> {_render(after[key])}")
        bm, nm = before.get("gold_metadata"), after.get("gold_metadata")
        if bm is not None and nm is not None:
            for key in sorted(bm.keys() | nm.keys()):
                if key not in bm or key not in nm or bm[key] != nm[key]:
                    changes.append(f"#{qid} gold_metadata.{key}: "
                                   f"{_field(bm, key)} -> {_field(nm, key)}")
        elif (bm is None) != (nm is None):
            unknowns.append(f"#{qid} gold_metadata availability differs; source equivalence is unverified")
        # Legacy rows may carry identity directly rather than inside gold_metadata.
        bi = before.get("canonical_id") or (bm or {}).get("canonical_id")
        ni = after.get("canonical_id") or (nm or {}).get("canonical_id")
        identity_reported = (bm is not None and nm is not None
                             and bm.get("canonical_id") == bi and nm.get("canonical_id") == ni)
        if bi is not None and ni is not None and bi != ni and not identity_reported:
            changes.append(f"#{qid} canonical_id: {_render(bi)} -> {_render(ni)}")
        elif (bi is None) != (ni is None):
            unknowns.append(f"#{qid} canonical_id availability differs; identity equivalence is unverified")
    return changes, unknowns


def main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-different-gold", action="store_true",
                        help="enumerate changed expectations and compare verdicts without a regression claim")
    parser.add_argument("base", type=Path)
    parser.add_argument("new", type=Path)
    args = parser.parse_args(argv[1:])
    try:
        base, base_source, axes = _read_run(args.base)
        new, new_source, new_axes = _read_run(args.new)
        if axes != new_axes:
            raise ValueError("verdict axes differ between runs")
    except (OSError, ValueError) as exc:
        print(f"Invalid benchmark input: {exc}", file=sys.stderr)
        return 2

    # Neither counts nor verdict transitions are printed until both full inputs validate.
    print(f"base rows {len(base)} / new rows {len(new)}")
    for label, source in (("base", base_source), ("new", new_source)):
        print(f"{label}: gold provenance {_render(source)}" if source is not None
              else f"{label}: gold provenance unavailable; source equivalence is unverified")
    changes, unknowns = _differences(base, new, base_source, new_source)
    for entry in changes + unknowns:
        print(entry)
    if changes and not args.allow_different_gold:
        print("Comparison refused: expectations/source versions differ. "
              "Use --allow-different-gold for a qualified cross-gold comparison.")
        return 2
    if changes:
        print("Cross-gold comparison: verdict changes are not an application regression claim.")
    else:
        print("Comparison of same detailed expectations; recorded provenance is not independent source verification.")
    for axis in axes:
        changed = [(qid, base[qid][axis], new[qid][axis])
                   for qid in sorted(base.keys() & new.keys())
                   if base[qid][axis] != new[qid][axis]]
        print(f"{axis} differences: {len(changed)}")
        for qid, before, after in changed:
            print(f"  #{qid}: {before} -> {after}")
        for anchor in (63, 109, 118):
            if anchor in new:
                before = base[anchor][axis] if anchor in base else "-"
                print(f"Anchor #{anchor} ({axis}): {before} -> {new[anchor][axis]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
