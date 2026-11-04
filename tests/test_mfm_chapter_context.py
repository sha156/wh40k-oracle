"""Paired price-context acceptance; actual assets are read only and copies disposable."""
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from db_compile import mfm
from db_compile.mfm_sync import operational_factions

ASSETS = Path("D:/Project/py/RAG")
BT_IDS = ("000002786", "000002787", "000002788", "000002789", "000002790", "000002791")
GENERIC_IDS = ("000002568", "000002705", "000001825", "000001667", "000002722", "000002721")
NAMES = ("Impulsor", "Gladiator Lancer", "Gladiator Valiant", "Gladiator Reaper", "Repulsor Executioner", "Repulsor")
BASE = (70, 165, 145, 165, 265, 190)
REPEAT = (80, 185, 165, 185, 285, 210)
RAW_SHA = "f819675c38d99f84673696604eff78d54863cc0f4a7b5f4457291e89909bae7d"


@pytest.fixture
def actual_copy(tmp_path):
    source = ASSETS / "db/wh40k.sqlite"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    assert before == "afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855"
    cache = ASSETS / "db_sources/mfm/mfm_points.json"
    cache_sha = hashlib.sha256(cache.read_bytes()).hexdigest()
    snapshot = json.loads(cache.read_text(encoding="utf-8"))["source_snapshot"]
    raw = ASSETS / "db_sources/mfm/snapshots/fetch-jtgkljt3/black-templars.html"
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == RAW_SHA
    generic_raw = raw.with_name("space-marines.html")
    generic_sha = snapshot["pages"]["space-marines"]["sha256"]
    assert hashlib.sha256(generic_raw.read_bytes()).hexdigest() == generic_sha
    path = tmp_path / "copy.sqlite"
    shutil.copy2(source, path)
    factions = {slug: [row for row in rows if row[0].casefold() in {n.casefold() for n in NAMES}]
                for slug, rows in operational_factions(snapshot).items()
                if slug in ("space-marines", "black-templars")}
    yield path, factions, snapshot
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == RAW_SHA
    assert hashlib.sha256(generic_raw.read_bytes()).hexdigest() == generic_sha
    assert hashlib.sha256(cache.read_bytes()).hexdigest() == cache_sha


def records(path):
    with closing(sqlite3.connect(path)) as conn:
        return dict(conn.execute("SELECT id,points_json FROM units"))


def all_tables(path):
    with closing(sqlite3.connect(path)) as conn:
        return {name: conn.execute('SELECT * FROM "' + name + '" ORDER BY rowid').fetchall()
                for name, in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def expected_rows(factions, slug, name):
    return [{"tier": t, "models": n, "cost": p} for u, t, n, p in factions[slug]
            if u.casefold() == name.casefold()]


def test_check_detects_chapter_prices_despite_generic_convergence(actual_copy):
    path, factions, _ = actual_copy
    report = mfm.check_points(path, factions)
    assert {(r["unit"], r["mfm"]) for r in report["diffs"]} == {
        ("Gladiator Lancer", 165), ("Gladiator Valiant", 145), ("Repulsor Executioner", 265)}


@pytest.mark.parametrize("reverse", [False, True])
def test_six_exact_chapter_tiers_preserve_generic_and_complete_ledger(actual_copy, reverse):
    path, factions, snapshot = actual_copy
    if reverse:
        factions = dict(reversed(list(factions.items())))
    before = records(path)
    tables = all_tables(path)
    assert len(tables["official_mfm_points"]) == 3635
    mfm.apply_points(path, factions, fetched_at=snapshot["fetched_at"])
    after = records(path)
    for uid, name, base, repeat in zip(BT_IDS, NAMES, BASE, REPEAT):
        data = json.loads(after[uid])
        assert data["points"] == base
        assert data["items"] == [dict(json.loads(before[uid])["items"][0], cost=base)]
        assert data["mfm"]["tiers"] == expected_rows(factions, "black-templars", name)
        assert data["mfm"]["tiers"][1]["cost"] == repeat
        assert data["mfm"]["source_slug"] == "black-templars"
        assert data["mfm"]["source_url"].endswith("/en/black-templars")
        assert data["mfm"]["source_sha256"] == RAW_SHA
        assert data["mfm"]["source_section"] == "UNITS"
    assert {uid: value for uid, value in after.items() if uid not in BT_IDS} == {
        uid: value for uid, value in before.items() if uid not in BT_IDS}
    for uid, name in zip(GENERIC_IDS, NAMES):
        assert json.loads(after[uid])["mfm"]["tiers"] == expected_rows(factions, "space-marines", name)
    report = mfm.check_points(path, factions)
    assert report["compared"] == report["agree"] == 12
    assert not report["diffs"]
    assert not report["db_context_diffs"]
    second = mfm.apply_points(path, factions, fetched_at=snapshot["fetched_at"])
    assert second["units_updated"] == 0
    assert records(path) == after
    assert {k: v for k, v in all_tables(path).items() if k != "units"} == {
        k: v for k, v in tables.items() if k != "units"}
    with closing(sqlite3.connect(path)) as conn:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(units)")]
    id_index, points_index = columns.index("id"), columns.index("points_json")
    expected_units = []
    for row in tables["units"]:
        updated = list(row)
        if row[id_index] in BT_IDS:
            updated[points_index] = after[row[id_index]]
        expected_units.append(tuple(updated))
    assert all_tables(path)["units"] == expected_units


@pytest.mark.parametrize("keywords", [
    None,
    ["Adeptus Astartes", "Black Templars", "Blood Angels"],
    ["Adeptus Astartes", "Unknown Chapter"],
    ["Black Templars"], ["Adeptus Astartes", "Black Templars", "Agents of the Imperium"],
])
def test_uncertain_chapter_is_explicitly_unmatched(actual_copy, keywords):
    path, factions, snapshot = actual_copy
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE units SET keywords_json=? WHERE id=?",
                     (None if keywords is None else json.dumps({"faction_keywords": keywords}), BT_IDS[1]))
    before = records(path)[BT_IDS[1]]
    result = mfm.apply_points(path, factions, fetched_at=snapshot["fetched_at"])
    assert records(path)[BT_IDS[1]] == before
    assert BT_IDS[1] in {row["id"] for row in result["context_unmatched"]}
    assert BT_IDS[1] in {row["id"] for row in mfm.check_points(path, factions)["context_unmatched"]}


def test_check_detects_missing_paid_option_even_when_base_matches(actual_copy):
    path, factions, snapshot = actual_copy
    mfm.apply_points(path, factions, fetched_at=snapshot["fetched_at"])
    with closing(sqlite3.connect(path)) as conn, conn:
        data = json.loads(records(path)[BT_IDS[0]])
        data["mfm"]["tiers"] = [r for r in data["mfm"]["tiers"] if r["models"] != "per Multi-melta"]
        conn.execute("UPDATE units SET points_json=? WHERE id=?", (json.dumps(data), BT_IDS[0]))
    report = mfm.check_points(path, factions)
    assert not report["diffs"]
    assert BT_IDS[0] in {r["id"] for r in report["db_context_diffs"]}


class CancelledProjection(BaseException):
    """Controlled cancellation, deliberately outside Exception."""


@pytest.mark.parametrize("failure", [RuntimeError, CancelledProjection])
def test_direct_late_projection_failure_rolls_back_exact_copy(actual_copy, monkeypatch, failure):
    from db_compile import point_tiers

    path, factions, snapshot = actual_copy
    before = path.read_bytes()
    original = point_tiers.minimum_unit_cost
    calls = 0

    def cancel_after_prior_update(items):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise failure("controlled late projection failure")
        return original(items)

    monkeypatch.setattr(point_tiers, "minimum_unit_cost", cancel_after_prior_update)
    with pytest.raises(failure, match="controlled late"):
        mfm.apply_points(path, factions, fetched_at=snapshot["fetched_at"])
    assert calls == 4
    assert path.read_bytes() == before


@pytest.mark.parametrize("failure", [RuntimeError, CancelledProjection])
def test_snapshot_late_failure_rolls_back_all_tables(actual_copy, monkeypatch, failure):
    from db_compile import mfm_sync

    path, _, snapshot = actual_copy
    before = path.read_bytes()

    def cancel_after_all_writes(*args, **kwargs):
        raise failure("controlled late snapshot failure")

    monkeypatch.setattr(mfm_sync, "verify_ledger", cancel_after_all_writes)
    with pytest.raises(failure, match="controlled late"):
        mfm_sync.apply_snapshot(path, snapshot)
    assert path.read_bytes() == before


def test_keyword_order_does_not_change_chapter_identity(actual_copy):
    path, factions, snapshot = actual_copy
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE units SET keywords_json=? WHERE id=?", (
            json.dumps({"faction_keywords": ["Adeptus Astartes", "Black Templars"]}), BT_IDS[1]))
    mfm.apply_points(path, factions, fetched_at=snapshot["fetched_at"])
    assert json.loads(records(path)[BT_IDS[1]])["points"] == 165


def test_wrong_source_receipt_is_unmatched_not_generic_fallback(actual_copy):
    path, factions, snapshot = actual_copy
    factions["black-templars"] = [
        (u, t, n, p + 1 if u == "GLADIATOR LANCER" and n == "1 model" else p)
        for u, t, n, p in factions["black-templars"]]
    before = records(path)[BT_IDS[1]]
    result = mfm.apply_points(path, factions, fetched_at=snapshot["fetched_at"])
    assert records(path)[BT_IDS[1]] == before
    assert BT_IDS[1] in {r["id"] for r in result["context_unmatched"]}
