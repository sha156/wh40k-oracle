"""Builder/update/MFM regressions using explicitly synthetic offline source HTML.

Canonical guards and price payloads come from the reviewed binding file. These
small source fixtures are not the real-source proof; the companion acceptance
also runs the full retained HTML and full CSV on independent database copies.
"""
import copy
import hashlib
import inspect
import json
import sqlite3
from contextlib import closing

import pytest

from db_compile import build, mfm_history
from db_compile.mfm_source import parse_source_page, write_ledger
from db_compile.mfm_sync import apply_snapshot
from db_compile.update import UpdateConfig, stage_build, stage_mfm_apply


def _csv(path, name, fields, rows):
    (path / name).write_text(
        "|".join(fields) + "|\n" + "".join("|".join(str(r.get(f, "")) for f in fields) + "|\n" for r in rows),
        encoding="utf-8",
    )


def _card(row):
    return ('<h3>' + row["section"] + '</h3><div class="print:break-inside-avoid-page">'
            '<div class="font-bold text-xl">' + row["unit_name"] + '</div><div>'
            + row["tier"] + '</div><ul><li><span>' + row["models"] + '</span><span>'
            + str(row["cost"]) + ' pts</span></li></ul></div>')


@pytest.fixture
def trial(tmp_path, monkeypatch):
    data = json.loads(mfm_history.BINDINGS.read_text("utf-8"))
    snapshot = tmp_path / "synthetic-snapshot"
    snapshot.mkdir()
    raw = "".join(_card(b["ledger_rows"][0]) for b in data["records"]).encode()
    meta = data["snapshot"]
    meta["page"]["sha256"] = hashlib.sha256(raw).hexdigest()
    meta["page"]["bytes"] = len(raw)
    manifest = {"fetched_at": meta["fetched_at"], "pages": {meta["faction_slug"]: meta["page"]}}
    manifest_bytes = json.dumps(manifest).encode()
    meta["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    (snapshot / "manifest.json").write_bytes(manifest_bytes)
    (snapshot / "space-marines.html").write_bytes(raw)
    for i, b in enumerate(data["records"]):
        b["ledger_rows"][0].update(ordinal=i, source_sha256=meta["page"]["sha256"])
    bindings = tmp_path / "synthetic-bindings.json"
    bindings.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(mfm_history, "BINDINGS", bindings)
    csv = tmp_path / "csv"
    csv.mkdir()
    sheets = [dict(id=b["canonical"]["id"], **b["datasheet"]) for b in data["records"]]
    _csv(csv, "Factions.csv", ("id", "name"), [{"id": "SM", "name": "Space Marines"}])
    _csv(csv, "Datasheets.csv", ("id", "name", "faction_id", "source_id", "link"), sheets)
    _csv(csv, "Datasheets_models_cost.csv", ("datasheet_id", "line", "description", "cost"), [
        dict(datasheet_id=b["canonical"]["id"], line="1", description="1 model", cost=b["csv_price"]["points"])
        for b in data["records"]])
    keywords = []
    for b in data["records"]:
        for key, values in json.loads(b["canonical"]["keywords_json"]).items():
            keywords.extend(dict(datasheet_id=b["canonical"]["id"], keyword=value,
                                 is_faction_keyword=str(key == "faction_keywords").lower()) for value in values)
    _csv(csv, "Datasheets_keywords.csv", ("datasheet_id", "keyword", "is_faction_keyword"), keywords)
    db = tmp_path / "trial.sqlite"
    cfg = UpdateConfig(csv_dir=csv, db=db, terms=tmp_path / "absent.json",
                       mfm_json=tmp_path / "current.json", offline=True)
    cfg.historical_mfm_snapshot = snapshot
    return cfg, data, bindings


def _prices(db):
    with closing(sqlite3.connect(db)) as c:
        return {uid: json.loads(raw) for uid, raw in c.execute("SELECT id,points_json FROM units")}


def _rename(db):
    renamed = db.with_name("renamed.sqlite")
    db.rename(renamed)
    renamed.rename(db)


def _seed(trial, kind):
    cfg, data, _ = trial
    # Allow the independently frozen parent to execute its real old builder;
    # the adapter supplies no missing API, restoration behavior or result.
    kwargs = ({"historical_mfm_snapshot": cfg.db.parent / "unavailable"}
              if "historical_mfm_snapshot" in inspect.signature(build.build_database).parameters else {})
    build.build_database(cfg.csv_dir, cfg.db, **kwargs)
    with closing(sqlite3.connect(cfg.db)) as c, c:
        for b in data["records"]:
            if kind == "official":
                payload = b["prior_official_price"]
            else:
                payload = dict(b["csv_price"], mfm={"current": False, "checked_at": "2026-10-03T19:00:56Z"})
            c.execute("UPDATE units SET points_json=? WHERE id=?", (json.dumps(payload), b["canonical"]["id"]))


@pytest.mark.parametrize("prior", ["clean", "official", "afb"])
def test_real_build_and_update_restore_dated_history_without_prior_names(trial, prior):
    cfg, data, _ = trial
    if prior != "clean":
        _seed(trial, prior)
    for _ in range(2):
        result = stage_build(cfg)
        assert result.ok
        # Empty latest snapshot removes membership while preserving history.
        cfg.mfm_json.write_text(json.dumps({"source_snapshot": {
            "fetched_at": "2026-10-03T19:00:56Z", "pages": {}}}), encoding="utf-8")
        assert stage_mfm_apply(cfg).ok
        for b in data["records"]:
            p = _prices(cfg.db)[b["canonical"]["id"]]
            assert p["items"] == b["prior_official_price"]["items"]
            assert p["points"] == b["prior_official_price"]["points"]
            assert p["mfm"]["current"] is False
            assert p["mfm"]["fetched_at"] == data["snapshot"]["fetched_at"]
            assert p["mfm"]["historical_source_rows"] == b["ledger_rows"]
            assert p["mfm"]["source_sha256"] == data["snapshot"]["page"]["sha256"]
            assert not any("effective" in key for key in p["mfm"])
        assert result.detail["historical_prices"]["restored"] == [b["canonical"]["id"] for b in data["records"]]
        with closing(sqlite3.connect(cfg.db)) as c:
            assert c.execute("SELECT name_zh FROM units").fetchall() == [(None,), (None,)]
        _rename(cfg.db)


@pytest.mark.parametrize("field", ["name_en", "faction_id", "keywords_json", "source_id", "link"])
def test_previous_canonical_identity_drift_aborts_atomic_build(trial, field):
    cfg, data, _ = trial
    _seed(trial, "official")
    table = "datasheets" if field in ("source_id", "link") else "units"
    with closing(sqlite3.connect(cfg.db)) as c, c:
        c.execute(f"UPDATE {table} SET {field}='drift' WHERE id=?", (data["records"][1]["canonical"]["id"],))
    before = cfg.db.read_bytes()
    with pytest.raises(ValueError, match="identity changed"):
        stage_build(cfg)
    assert cfg.db.read_bytes() == before and not cfg.db.with_suffix(".tmp.sqlite").exists()
    _rename(cfg.db)


@pytest.mark.parametrize("binding_index", [0, 1])
@pytest.mark.parametrize("raw", [
    "null", "[]", "false", "0", '"unknown"', "{}", None,
    '{"mfm":[]}', '{"items":null}', '{"mfm":null}', "{",
])
def test_existing_malformed_prior_price_aborts_atomic_build(trial, binding_index, raw):
    cfg, data, _ = trial
    _seed(trial, "official")
    uid = data["records"][binding_index]["canonical"]["id"]
    with closing(sqlite3.connect(cfg.db)) as c, c:
        c.execute("UPDATE units SET points_json=? WHERE id=?", (raw, uid))
    before = cfg.db.read_bytes()
    # JSON null must not masquerade as the missing-row sentinel. Neighboring
    # malformed evidence must also reject before the builder replaces the DB.
    expected = ValueError if raw == "null" else (ValueError, TypeError, AttributeError)
    with pytest.raises(expected):
        build.build_database(cfg.csv_dir, cfg.db, historical_mfm_snapshot=cfg.historical_mfm_snapshot)
    assert cfg.db.read_bytes() == before and not cfg.db.with_suffix(".tmp.sqlite").exists()
    _rename(cfg.db)


@pytest.mark.parametrize("binding_index", [0, 1])
def test_genuinely_absent_prior_identity_restores_verified_history(trial, binding_index):
    cfg, data, _ = trial
    _seed(trial, "official")
    uid = data["records"][binding_index]["canonical"]["id"]
    with closing(sqlite3.connect(cfg.db)) as c, c:
        c.execute("DELETE FROM units WHERE id=?", (uid,))
        c.execute("DELETE FROM datasheets WHERE id=?", (uid,))
    result = build.build_database(cfg.csv_dir, cfg.db, historical_mfm_snapshot=cfg.historical_mfm_snapshot)
    assert result.historical_prices["restored"] == [b["canonical"]["id"] for b in data["records"]]
    assert _prices(cfg.db) == {
        b["canonical"]["id"]: mfm_history._historical_payload(b) for b in data["records"]
    }
    _rename(cfg.db)


@pytest.mark.parametrize("field", ["points", "cost", "fetched_at", "future_capture", "source_url", "tier", "history_sha", "current", "checked_at"])
def test_prior_official_price_and_provenance_mismatch_aborts_before_replacement(trial, field):
    cfg, data, _ = trial
    _seed(trial, "official")
    b = data["records"][1]
    payload = copy.deepcopy(b["prior_official_price"])
    if field == "points":
        payload["points"] += 1
    elif field == "cost":
        payload["items"][0]["cost"] += 1
    elif field == "tier":
        payload["mfm"]["tiers"][0]["cost"] += 1
    elif field == "history_sha":
        payload["mfm"]["source_sha256"] = "a" * 64
    elif field == "current":
        payload["mfm"]["current"] = 1
    elif field == "future_capture":
        payload["mfm"]["fetched_at"] = "2026-09-15T12:00:00Z"
    else:
        payload["mfm"][field] = "drift"
    with closing(sqlite3.connect(cfg.db)) as c, c:
        c.execute("UPDATE units SET points_json=? WHERE id=?", (json.dumps(payload), b["canonical"]["id"]))
    before = cfg.db.read_bytes()
    with pytest.raises(ValueError):
        stage_build(cfg)
    assert cfg.db.read_bytes() == before
    _rename(cfg.db)


@pytest.mark.parametrize("change", ["raw", "manifest", "binding_cost", "binding_ordinal", "binding_capture", "csv_price", "csv_faction", "csv_keyword"])
def test_source_binding_and_skeleton_drift_rejects(trial, change):
    cfg, data, bindings = trial
    _seed(trial, "afb")
    before = cfg.db.read_bytes()
    if change in ("raw", "manifest"):
        path = cfg.historical_mfm_snapshot / ("space-marines.html" if change == "raw" else "manifest.json")
        path.write_bytes(path.read_bytes() + b" ")
    elif change.startswith("binding"):
        row = data["records"][1]["ledger_rows"][0]
        row[{"binding_cost": "cost", "binding_ordinal": "ordinal", "binding_capture": "fetched_at"}[change]] = "drift"
        bindings.write_text(json.dumps(data), encoding="utf-8")
    else:
        name = {"csv_price": "Datasheets_models_cost.csv", "csv_faction": "Datasheets.csv",
                "csv_keyword": "Datasheets_keywords.csv"}[change]
        path = cfg.csv_dir / name
        text = path.read_text("utf-8")
        if change == "csv_price":
            text = text.replace("|140|", "|141|")
        elif change == "csv_faction":
            text = text.replace("|SM|", "|GK|")
        else:
            text = text.replace("|Ultramarines|", "|Grey Knights|")
        path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        stage_build(cfg)
    assert cfg.db.read_bytes() == before and not cfg.db.with_suffix(".tmp.sqlite").exists()
    _rename(cfg.db)


def test_prior_official_ledger_mismatch_rejects(trial):
    cfg, data, _ = trial
    _seed(trial, "official")
    raw = (cfg.historical_mfm_snapshot / "space-marines.html").read_text("utf-8")
    snapshot = {"fetched_at": data["snapshot"]["fetched_at"], "pages": {"space-marines": dict(
        parse_source_page(raw), **data["snapshot"]["page"])}}
    with closing(sqlite3.connect(cfg.db)) as c, c:
        write_ledger(c, snapshot)
        c.execute("UPDATE official_mfm_points SET cost=999 WHERE ordinal=1")
    before = cfg.db.read_bytes()
    with pytest.raises(ValueError, match="prior ledger"):
        stage_build(cfg)
    assert cfg.db.read_bytes() == before
    _rename(cfg.db)


def test_unavailable_history_does_not_promote_csv_to_official(trial):
    cfg, data, _ = trial
    (cfg.historical_mfm_snapshot / "space-marines.html").unlink()
    result = stage_build(cfg)
    assert result.ok and "unavailable" in result.warning
    for b in data["records"]:
        assert _prices(cfg.db)[b["canonical"]["id"]] == b["csv_price"]


def test_new_current_publication_wins_and_repeated_rebuild_does_not_restore_stale_history(trial):
    cfg, data, _ = trial
    assert stage_build(cfg).ok
    rows = []
    for b in data["records"]:
        rows.append(dict(b["ledger_rows"][0], cost=b["csv_price"]["points"] + 7))
    page = parse_source_page("".join(_card(row) for row in rows))
    snapshot = {"fetched_at": "2026-10-04T12:00:00Z", "pages": {"space-marines": dict(
        page, url=data["snapshot"]["page"]["url"], sha256="b" * 64)}}
    for repeat in range(2):
        if repeat:
            result = stage_build(cfg)
            if "historical_prices" in result.detail:
                assert result.detail["historical_prices"]["newer_current"] == [b["canonical"]["id"] for b in data["records"]]
                assert result.detail["historical_prices"]["restored"] == []
        assert apply_snapshot(cfg.db, snapshot)["ledger"]["equal"]
        for b, row in zip(data["records"], rows):
            p = _prices(cfg.db)[b["canonical"]["id"]]
            assert p["points"] == row["cost"] and p["mfm"]["current"] is True
            assert "historical_source_rows" not in p["mfm"]
        _rename(cfg.db)


def test_history_stage_failure_after_preparation_preserves_previous_database(trial, monkeypatch):
    cfg, _, _ = trial
    _seed(trial, "afb")
    before = cfg.db.read_bytes()

    def fail(*args):
        raise RuntimeError("later archive failure")

    monkeypatch.setattr(build, "preserve_archived_units", fail)
    with pytest.raises(RuntimeError, match="later archive failure"):
        stage_build(cfg)
    assert cfg.db.read_bytes() == before and not cfg.db.with_suffix(".tmp.sqlite").exists()
    _rename(cfg.db)


def test_empty_rebuild_is_not_applicable_and_does_not_open_old_database(tmp_path, monkeypatch):
    target = tmp_path / "old.sqlite"
    target.write_bytes(b"unreadable old DB")
    monkeypatch.setattr(build, "preserve_archived_units", lambda *args: 0)
    kwargs = ({"historical_mfm_snapshot": tmp_path / "missing"}
              if "historical_mfm_snapshot" in inspect.signature(build.build_database).parameters else {})
    result = build.build_database(tmp_path, target, **kwargs)
    if hasattr(result, "historical_prices"):
        assert result.historical_prices["status"] == "not_applicable"
    _rename(target)
