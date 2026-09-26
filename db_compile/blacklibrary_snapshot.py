"""Validate a captured community snapshot and stage a non-destructive cache merge.

This command never writes the live database or changes official rules/points.
Failed and empty captures retain the previous cache record, explicitly labelled
as older content. The staged cache can use the normal offline restoration path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.fetch_blacklibrary_snapshot import parsed_detail, source_id
from db_compile.blacklibrary_scope import reviewed_empty_listing


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_json(root, name, expected):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if root not in path.parents:
        raise ValueError("Snapshot path escapes its directory")
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError("Snapshot hash mismatch: " + name)
    return json.loads(raw)


def unique_records(records):
    result = {}
    for record in records:
        key = source_id(record)
        if key in result:
            raise ValueError("Duplicate source identity: " + key)
        result[key] = record
    return result


def merge_snapshot(snapshot, existing):
    root = Path(snapshot)
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if (manifest.get("schema_version") != 1 or manifest.get("game_id") != 2
            or manifest.get("unit_list_reconciled") is not True
            or manifest.get("status") not in ("partial", "complete_known_endpoints")):
        raise ValueError("Snapshot inventory is not reconciled 40K content")
    outputs = {}
    for name, meta in manifest["outputs"].items():
        rows = checked_json(root, name, meta["sha256"])
        if not isinstance(rows, list) or len(rows) != meta["records"]:
            raise ValueError("Snapshot output count mismatch: " + name)
        outputs[name] = rows
    units = unique_records(outputs["units.json"])
    details = unique_records(outputs["details.json"])
    if set(units) != set(details) or len(units) != manifest["unit_list_expected"]:
        raise ValueError("Snapshot detail inventory does not reconcile")
    # Independently check raw content, not just the compiled output's hash.
    raw = {}
    for key, meta in manifest["requests"].items():
        if meta.get("path"):
            raw[key] = checked_json(root, meta["path"], meta["sha256"])
    inventory = []
    for key, meta in manifest["requests"].items():
        if meta.get("endpoint") == "manager/forum/unit/list":
            envelope = raw[key]["envelope"]
            if meta["status"] != "captured" or str(envelope["code"]) != "200":
                raise ValueError("Inventory capture is not verified")
            inventory.extend(envelope["data"])
    if unique_records(inventory) != units:
        raise ValueError("Compiled inventory differs from raw captures")
    prior = unique_records(existing)
    merged = dict(prior)
    changed, added, accepted, rejected = [], [], [], []
    fields = ("name_en", "name_zh", "faction_zh", "score", "detail")
    for sid, row in details.items():
        if row.get("detail_status") not in ("captured", "failed", "source_empty", "ignored_empty_listing"):
            raise ValueError("Unknown detail status")
        if row["detail_status"] == "ignored_empty_listing" and not reviewed_empty_listing(units[sid]):
            raise ValueError("Ignored listing does not match reviewed policy: " + sid)
        if row["detail_status"] != "captured":
            rejected.append(sid)
            continue
        unit = units[sid]
        origin = row["source_capture"]
        if origin == "unit_list":
            source = unit
        else:
            meta = manifest["requests"][origin]
            capture = raw[origin]
            request = {"gameId": 2, "topName": unit["topName"],
                       "unitName": unit["unitEnglishName"]}
            if (meta["status"] != "captured" or meta["endpoint"] != "unit/detail"
                    or meta["method"] != "POST" or meta["request"] != request
                    or capture["request"] != request or str(capture["envelope"]["code"]) != "200"):
                raise ValueError("Detail capture request is not verified: " + sid)
            source = capture["envelope"]["data"]
        if (source_id(source) != sid or source.get("gameId") != 2
                or source.get("topName") != unit["topName"]):
            raise ValueError("Detail identity mismatch: " + sid)
        expected = dict(name_en=source.get("unitEnglishName"), name_zh=source.get("unitName"),
                        faction_zh=source.get("topName"), score=source.get("unitScore"),
                        detail=parsed_detail(source))
        if not expected["detail"] or any(row.get(k) != expected[k] for k in fields):
            raise ValueError("Compiled detail differs from capture: " + sid)
        accepted.append(sid)
        if sid not in prior:
            added.append(sid)
        elif any(prior[sid].get(k) != row.get(k) for k in fields):
            changed.append(sid)
        merged[sid] = dict(row, provenance={
            "snapshot": root.name, "manifest_sha256": sha(manifest_bytes),
            "capture": origin, "status": "verified_capture",
            "fetched_at": manifest["requests"].get(origin, {}).get("fetched_at"),
            "authority": "third_party_community_source"})
    retained = sorted(set(prior) - set(accepted))
    for sid in retained:
        merged[sid] = dict(prior[sid], provenance={
            "status": "retained_previous_cache", "snapshot": root.name,
            "reason": details[sid]["detail_status"] if sid in details else "absent_from_inventory",
            "authority": "third_party_community_source", "previous": prior[sid].get("provenance")})
    report = {"snapshot": str(root.resolve()), "manifest_sha256": sha(manifest_bytes),
              "accepted": len(accepted), "changed": changed, "added": added,
              "retained_previous": retained, "not_imported": rejected,
              "merged_records": len(merged), "raw_hashes_checked": len(raw)}
    return list(merged.values()), outputs["units.json"], report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--existing", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    # A new staging directory makes accidental canonical-cache replacement impossible.
    if args.out.exists():
        parser.error("--out must be a new staging directory")
    existing = json.loads(args.existing.read_text(encoding="utf-8"))
    details, units, report = merge_snapshot(args.snapshot, existing)
    args.out.mkdir(parents=True)
    for name, value in (("details.json", details), ("units.json", units), ("merge-report.json", report)):
        (args.out / name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"accepted": report["accepted"], "changed": len(report["changed"]),
                      "added": len(report["added"]), "retained": len(report["retained_previous"]),
                      "merged": len(details)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
