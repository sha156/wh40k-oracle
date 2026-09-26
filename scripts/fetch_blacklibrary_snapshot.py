"""Snapshot public Black Library 40K content without changing canonical caches/DB.

The source is community material, not official-current rules. A complete snapshot
means the known public endpoints reconciled, not that every site feature or rule
is covered. Resume by passing the same --out directory. Failed requests are retried;
successful captures are reused only after their stored hash has been checked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db_compile.blacklibrary_scope import reviewed_empty_listing

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://blackforum.czmakj.com/app/"
LIST_PATH = "manager/forum/unit/list"
DETAIL_PATH = "unit/detail"
RULE_PATH = "army/rule"
POWER_PATH = "manager/forum/power/list/foA"
CATALOGS = {
    "40k-factions": "https://fanjiang.czmakj.com/community-mp-imgs/yellow/40k/阵营.json",
    "40k-universal-rules": "https://fanjiang.czmakj.com/community-mp-imgs/yellow/40k/skillDesc.json",
    "aos-factions-observed-only": "https://fanjiang.czmakj.com/community-mp-imgs/yellow/阵营.json",
}
PAGE_SIZE = 50
PRIVATE_KEYS = {
    "userid", "userhead", "users", "manageruserid", "nickname", "authorization",
    "accesstoken", "refreshtoken", "token", "password", "cookie", "setcookie",
}
DELETED = re.compile(r"(?:（已删除）|\(已删除\)|\[已删除\]|【已删除】)\s*$")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sanitize(value):
    """Remove account metadata recursively, including embedded card JSON."""
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if re.sub(r"[^a-z]", "", key.casefold()) in PRIVATE_KEYS:
                continue
            if key == "unitDetail" and isinstance(item, str) and item.strip():
                try:
                    parsed = json.loads(item)
                except ValueError:
                    pass  # Preserve malformed game content for explicit validation failure.
                else:
                    item = json.dumps(sanitize(parsed), ensure_ascii=False, sort_keys=True)
            result[key] = sanitize(item)
        return result
    return value


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                       allow_nan=False) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = encode(value)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)
    return digest(data)


class SourceError(ValueError):
    pass


def source_id(record):
    value = record.get("id")
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).strip():
        raise SourceError("record has no stable source id")
    return str(value).strip()


def parsed_detail(record):
    if "unitDetail" not in record:
        raise SourceError("detail response lacks unitDetail field")
    value = record["unitDetail"]
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as exc:
            raise SourceError("unitDetail is not valid JSON") from exc
    if not isinstance(value, dict):
        raise SourceError("unitDetail is not an object")
    return value or None


class Snapshot:
    def __init__(self, out, session=None, interval=0.3, retries=3, sleep=time.sleep):
        self.out = Path(out)
        if self.out.resolve() == (ROOT / "db_sources/blacklibrary").resolve():
            raise SourceError("snapshot output cannot replace the canonical Black Library cache directory")
        self.out.mkdir(parents=True, exist_ok=True)
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.interval, self.retries, self.sleep = interval, retries, sleep
        manifest_path = self.out / "manifest.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
            "schema_version": 1, "started_at": utc_now(), "game_id": 2,
            "authority": "third_party_community_source",
            "scope": "Known public game-content endpoints only; not official-current verification.",
            "requests": {}, "outputs": {},
            "sanitization": {"removed_account_keys": sorted(PRIVATE_KEYS),
                             "hash_scope": "sanitized stored content; no request headers retained"},
        }
        if self.manifest.get("schema_version") != 1 or self.manifest.get("game_id") != 2:
            raise SourceError("snapshot manifest is incompatible")

    def checkpoint(self):
        self.manifest["updated_at"] = utc_now()
        write_json(self.out / "manifest.json", self.manifest)

    def failure(self, key, message):
        entry = self.manifest["requests"].setdefault(key, {})
        if message != "request failed: " + key or not entry.get("error"):
            entry["error"] = message
        entry["status"] = "failed"
        self.checkpoint()

    def capture(self, key, endpoint, payload=None, method="POST"):
        entries = self.manifest["requests"]
        previous = entries.get(key, {})
        path = self.out / "raw" / (key + ".json")
        if (previous.get("status") in ("captured", "source_empty") and path.is_file()
                and digest(path.read_bytes()) == previous.get("sha256")
                and previous.get("endpoint") == endpoint and previous.get("request") == payload
                and previous.get("method", "POST") == method):
            return json.loads(path.read_text(encoding="utf-8"))["envelope"]
        entry = {"endpoint": endpoint, "request": payload, "method": method, "status": "pending",
                 "path": path.relative_to(self.out).as_posix()}
        entries[key] = entry
        for attempt in range(1, self.retries + 1):
            self.sleep(self.interval if attempt == 1 else max(self.interval, attempt - 1))
            try:
                response = (self.session.get(endpoint, timeout=25) if method == "GET"
                            else self.session.post(BASE_URL + endpoint, json=payload, timeout=25))
                response.raise_for_status()
                envelope = sanitize(response.json())
                if method == "POST" and not isinstance(envelope, dict):
                    raise SourceError("endpoint envelope is not an object")
                entry.update(fetched_at=utc_now(), attempts=attempt)
                stored = {"endpoint": endpoint, "request": payload, "method": method,
                          "fetched_at": entry["fetched_at"], "envelope": envelope}
                entry["sha256"] = write_json(path, stored)
                # Observed on two named faction-rule lookups. Other business
                # errors remain failures; do not treat every null/error as empty.
                known_empty = (method == "POST" and endpoint == RULE_PATH
                               and str(envelope.get("code")) == "1010"
                               and envelope.get("text") == "数据不存在"
                               and "data" in envelope and envelope["data"] is None)
                if method == "POST" and not known_empty and (
                    str(envelope.get("code")) != "200" or "data" not in envelope
                ):
                    raise SourceError("endpoint did not return a successful data envelope")
                entry["status"] = "source_empty" if known_empty else "captured"
                self.checkpoint()
                return envelope
            except (requests.RequestException, ValueError, TypeError) as exc:
                # Exception messages may contain request details. Retain only the
                # class, or our own fixed schema error text, never auth/request headers.
                entry.update(attempts=attempt, error=str(exc) if isinstance(exc, SourceError)
                             else type(exc).__name__, status="failed")
                self.checkpoint()
        raise SourceError("request failed: " + key)

    def output(self, name, value):
        checksum = write_json(self.out / name, value)
        self.manifest["outputs"][name] = {"sha256": checksum, "records": len(value)}

    def fetch_units(self):
        units, seen, expected, pages = [], set(), None, None
        page = 1
        while pages is None or page <= pages:
            key = f"unit-list/page-{page:03d}"
            envelope = self.capture(key, LIST_PATH, {"gameId": 2, "unitName": "",
                                    "pageNum": page, "pageSize": PAGE_SIZE})
            try:
                total, page_count = envelope.get("totalCount"), envelope.get("pageLength")
                if (type(total) is not int or total < 0 or type(page_count) is not int
                        or page_count != max(1, math.ceil(total / PAGE_SIZE))
                        or envelope.get("currentPageNo") != page):
                    raise SourceError("unit list pagination metadata is missing or inconsistent")
                if expected is None:
                    expected, pages = total, page_count
                    self.manifest["unit_list_expected"] = total
                elif total != expected or page_count != pages:
                    raise SourceError("unit list changed while paginating; use a new snapshot")
                records = envelope["data"]
                wanted = min(PAGE_SIZE, max(0, expected - (page - 1) * PAGE_SIZE))
                if not isinstance(records, list) or len(records) != wanted:
                    raise SourceError("unit list page count disagrees with totalCount")
                for unit in records:
                    if not isinstance(unit, dict) or unit.get("gameId") != 2:
                        raise SourceError("unit list contains a malformed or non-40K record")
                    sid = source_id(unit)
                    if sid in seen:
                        raise SourceError("unit list contains a duplicate source identity")
                    if not isinstance(unit.get("topName"), str) or not unit["topName"].strip():
                        raise SourceError("unit list has no faction identity")
                    seen.add(sid)
                    units.append(unit)
            except SourceError as exc:
                self.failure(key, str(exc))
                raise
            page += 1
        if len(units) != expected:
            raise SourceError("unit list final count did not reconcile")
        self.output("units.json", units)
        self.manifest["unit_list_reconciled"] = True
        return units

    def fetch_details(self, units):
        details = []
        for index, unit in enumerate(units, 1):
            sid = source_id(unit)
            key = "unit-details/" + hashlib.sha256(sid.encode()).hexdigest()[:16]
            status, detail, origin = "captured", None, "unit_list"
            record = unit
            try:
                detail = parsed_detail(unit)
                exclusion = reviewed_empty_listing(unit) if detail is None else None
                if exclusion:
                    status = "ignored_empty_listing"
                    self.manifest["requests"][key] = {
                        "status": status, "reason": exclusion["reason"],
                        "inventory_sha256": exclusion["inventory_sha256"],
                    }
                elif detail is None:
                    name = unit.get("unitEnglishName")
                    if not isinstance(name, str) or not name.strip():
                        raise SourceError("unit lacks an English detail lookup name")
                    envelope = self.capture(key, DETAIL_PATH, {"gameId": 2,
                        "topName": unit["topName"], "unitName": name})
                    origin = key
                    fetched = envelope["data"]
                    if fetched is None:
                        status = "source_empty"
                    else:
                        if (not isinstance(fetched, dict) or source_id(fetched) != sid
                                or fetched.get("gameId") != 2
                                or fetched.get("topName") != unit["topName"]):
                            raise SourceError("detail response identity differs from the listed unit")
                        record = fetched
                        detail = parsed_detail(record)
                        status = "captured" if detail is not None else "source_empty"
                    self.manifest["requests"][key]["status"] = status
            except SourceError as exc:
                self.failure(key, str(exc))
                status = "failed"
            details.append({"id": unit["id"], "faction_zh": record.get("topName"),
                "name_zh": record.get("unitName"), "name_en": record.get("unitEnglishName"),
                "score": record.get("unitScore"), "detail": detail,
                "detail_status": status, "source_capture": origin,
                "authority": "third_party_community_source"})
            if index % 25 == 0 or index == len(units):
                self.output("details.json", details)
                self.manifest["details_progress"] = {"processed": index, "expected": len(units)}
                self.checkpoint()
                print(f"Details {index}/{len(units)}", flush=True)
        return details

    def fetch_factions(self, factions):
        records = []
        for faction in factions:
            slug = hashlib.sha256(faction.encode()).hexdigest()[:16]
            for kind, endpoint, payload in (
                ("army_rule", RULE_PATH, {"gameId": 2, "topName": faction}),
                ("powers", POWER_PATH, {"gameId": 2, "topName": faction, "subName": "",
                                       "pageNum": 1, "pageSize": 1000}),
            ):
                key = "factions/" + slug + "/" + kind
                status, count = "failed", 0
                try:
                    envelope = self.capture(key, endpoint, payload)
                    data = envelope["data"]
                    if data is None or data == [] or data == {}:
                        status = "source_empty"
                    elif kind == "army_rule":
                        if not isinstance(data, dict) or data.get("gameId") != 2 or data.get("topName") != faction:
                            raise SourceError("army rule has a malformed or mismatched identity")
                        status, count = "captured", 1
                    else:
                        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
                            raise SourceError("powers response is not a list of records")
                        ids = [source_id(row) for row in data]
                        if len(ids) != len(set(ids)):
                            raise SourceError("powers response contains duplicate source identities")
                        if any(row.get("gameId") != 2 or row.get("topName") != faction for row in data):
                            raise SourceError("powers response contains a mismatched identity")
                        # This observed endpoint returns the complete list and ignores
                        # pagination. Keep every row rather than truncating to pageSize.
                        status, count = "captured", len(data)
                    self.manifest["requests"][key]["status"] = status
                except SourceError as exc:
                    self.failure(key, str(exc))
                records.append({"faction_zh": faction, "kind": kind, "status": status,
                                "records": count, "source_capture": key})
                self.checkpoint()
        self.output("factions.json", records)
        return records

    def fetch_catalogs(self):
        factions = set()
        for name, url in CATALOGS.items():
            key = "catalogs/" + name
            try:
                data = self.capture(key, url, method="GET")
                if not isinstance(data, list) or not data or any(not isinstance(row, dict) for row in data):
                    raise SourceError("catalog is not a non-empty list of objects")
                if name == "40k-factions":
                    for row in data:
                        faction = row.get("种族名称")
                        if not isinstance(faction, str) or not faction.strip():
                            raise SourceError("40K catalog faction has no name")
                        factions.add(faction)
                elif name == "40k-universal-rules" and any(
                    not all(isinstance(row.get(field), str) for field in ("cName", "eName", "desc"))
                    for row in data
                ):
                    raise SourceError("universal rule catalog has malformed rule text")
                self.output("catalogs/" + name + ".json", data)
            except SourceError as exc:
                self.failure(key, str(exc))
        self.manifest["excluded_scope"] = ["AoS unit/rule crawling; observed AoS catalog retained only"]
        return factions

    def preserve_deleted(self, units, caches):
        present = {source_id(unit) for unit in units}
        retained = []
        seen = set()
        for path in caches:
            path = Path(path)
            if not path.is_file():
                continue
            records = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                raise SourceError("historical cache is not a list")
            for record in records:
                if not isinstance(record, dict) or not DELETED.search(str(record.get("name_zh") or "")):
                    continue
                sid = source_id(record)
                if sid in present:
                    continue
                cleaned = sanitize(record)
                fingerprint = digest(encode(cleaned))
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                retained.append({"record": cleaned, "source_cache": path.name,
                    "source_cache_sha256": digest(path.read_bytes()),
                    "cache_mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                    "status": "historical_source_only", "is_current": False,
                    "authority": "third_party_deleted_record",
                    "scope": "Previously cached deleted record; cache time is not a rules publication date."})
        self.output("historical_deleted_details.json", retained)

    def run(self, historical_caches=()):
        self.manifest.pop("error", None)
        self.manifest.update(status="in_progress", unit_list_reconciled=False)
        self.checkpoint()
        try:
            units = self.fetch_units()
            factions = sorted({unit["topName"] for unit in units} | self.fetch_catalogs())
            self.manifest["factions"] = factions
            self.preserve_deleted(units, historical_caches)
            self.fetch_factions(factions)
            details = self.fetch_details(units)
            failed = [key for key, value in self.manifest["requests"].items() if value.get("status") == "failed"]
            self.manifest.update(status="partial" if failed else "complete_known_endpoints",
                failed_requests=failed,
                counts={"units": len(units), "factions": len(factions), "details": len(details),
                        "details_with_content": sum(row["detail_status"] == "captured" for row in details),
                        "details_source_empty": sum(row["detail_status"] == "source_empty" for row in details),
                        "details_ignored": sum(row["detail_status"] == "ignored_empty_listing" for row in details),
                        "details_failed": sum(row["detail_status"] == "failed" for row in details)})
        except (SourceError, OSError, ValueError) as exc:
            self.manifest.update(status="partial", error=str(exc) if isinstance(exc, SourceError) else type(exc).__name__)
        self.checkpoint()
        return self.manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "db_sources/blacklibrary/snapshots" /
                        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--interval", type=float, default=0.3)
    parser.add_argument("--historical-cache", action="append", type=Path)
    args = parser.parse_args()
    if args.interval < 0.15:
        parser.error("--interval must be at least 0.15 seconds")
    caches = args.historical_cache or [ROOT / "db_sources/blacklibrary/details.json"]
    result = Snapshot(args.out, interval=args.interval).run(caches)
    print(json.dumps({"path": str(args.out), "status": result["status"],
                      "counts": result.get("counts"), "failed": result.get("failed_requests")},
                     ensure_ascii=False), flush=True)
    return 0 if result["status"] == "complete_known_endpoints" else 1


if __name__ == "__main__":
    raise SystemExit(main())
