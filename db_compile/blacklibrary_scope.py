"""Reviewed empty source listings, guarded against future inventory changes."""
import hashlib
import json
from pathlib import Path


POLICY = Path(__file__).with_name("blacklibrary_listing_policy.json")


def reviewed_empty_listing(unit):
    """Return a reviewed exclusion only for the identical empty inventory row.

    Matching by name alone could suppress the full datasheet or a later source
    update. These exclusions affect crawl work, never canonical database rows.
    """
    if unit.get("unitEnglishName") or unit.get("unitDetail"):
        return None
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if policy.get("schema_version") != 1:
        raise ValueError("Unsupported Black Library listing policy")
    raw = (json.dumps(unit, ensure_ascii=False, indent=2, sort_keys=True,
                      allow_nan=False) + "\n").encode("utf-8")
    fingerprint = hashlib.sha256(raw).hexdigest()
    for record in policy["records"]:
        if (record["id"] == str(unit.get("id"))
                and record["inventory_sha256"] == fingerprint):
            return record
    return None
