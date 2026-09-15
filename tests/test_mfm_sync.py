"""Official source boundary and exact points-sync regressions."""
import json
import sqlite3
from contextlib import closing

import pytest

from db_compile import mfm
from db_compile.mfm_source import parse_source_page, verify_ledger
from db_compile.mfm_sync import apply_snapshot, operational_factions


def card(name, cost, color="bg-slate-500", models="1 model"):
    return (f'<div class="px-1 py-0.5 {color} font-bold text-xl text-white">{name}</div>'
            '<div class="bg-slate-200 font-bold">YOUR UNIT COSTS</div>'
            f'<ul><li><span>{models}</span><span>{cost} pts</span></li></ul>')


def database(tmp_path, items):
    path = tmp_path / "points.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE units (id TEXT, faction_id TEXT, name_en TEXT, points_json TEXT)")
        conn.execute("INSERT INTO units VALUES (?, ?, ?, ?)",
                     ("u1", "ORK", "Gorkanaut", json.dumps({"items": items, "points": 999})))
    return path


def test_plain_coloured_header_cannot_leak_into_previous_unit():
    # September live page: Ghazghkull has a plain red header, no keep-all span.
    html = card("GARGANTUAN SQUIGGOTH", 500) + card("GHAZGHKULL THRAKA", 300, "bg-red-500")
    assert mfm.parse_mfm_html(html) == [
        ("GARGANTUAN SQUIGGOTH", "YOUR UNIT COSTS", "1 model", 500),
        ("GHAZGHKULL THRAKA", "YOUR UNIT COSTS", "1 model", 300),
    ]


def test_header_detection_is_independent_of_css_class_order():
    html = card("GRETCHIN", 45, "bg-new-theme", "10 Gretchin").replace(
        "bg-new-theme font-bold text-xl", "text-xl bg-new-theme font-bold")
    assert mfm.parse_mfm_html(html)[0][0] == "GRETCHIN"


def test_conflicting_official_base_prices_abort_before_any_write(tmp_path):
    path = database(tmp_path, [{"desc": "1 model", "cost": 325}])
    before = path.read_bytes()
    rows = {"orks": [("GORKANAUT", "YOUR UNIT COSTS", "1 model", 325),
                     ("GORKANAUT", "YOUR UNIT COSTS", "1 model", 150)]}
    with pytest.raises(mfm.MfmParseBroken, match="conflict"):
        mfm.apply_points(path, rows)
    assert path.read_bytes() == before


def test_sync_replaces_removed_tiers_and_reports_missing_tiers(tmp_path):
    path = database(tmp_path, [{"desc": "1 model", "cost": 100},
                               {"desc": "2 models", "cost": 200}])
    rows = {"orks": [("GORKANAUT", "YOUR UNIT COSTS", "3 models", 325)]}
    report = mfm.check_points(path, rows)
    assert report["db_missing_tiers"]
    assert report["db_extra_tiers"]
    mfm.apply_points(path, rows, fetched_at="2026-09-14")
    with sqlite3.connect(path) as conn:
        data = json.loads(conn.execute("SELECT points_json FROM units").fetchone()[0])
    assert data["items"] == [{"line": None, "desc": "3 models", "cost": 325}]
    report = mfm.check_points(path, rows)
    assert report["agree"] == report["compared"] == 1
    assert not report["db_missing_tiers"]
    assert not report["db_extra_tiers"]


def source_card(body):
    return '<div class="print:break-inside-avoid-page">' + body + '</div>'


def snapshot():
    html = ('<h3>UNITS</h3>' + source_card(card("GORKANAUT", 325))
            + source_card(card("NAZDREG", 175, "bg-red-500"))
            + '<h3>ALLIED CONDITION</h3>' + source_card(card("GORKANAUT", 355))
            + '<h3>DETACHMENTS</h3>' + source_card(
                '<div><span class="text-xl break-all">WAR HORDE</span><span>2DP</span></div>'
                '<div style="background-color:#abc">TAKE AND HOLD</div>'
                '<div>ENHANCEMENTS</div><ul><li><div><span>Example Upgrade</span>'
                '<span>25 pts</span></div></li></ul>'))
    page = parse_source_page(html)
    return {"fetched_at": "2026-09-14", "pages": {"orks": dict(
        page, url="https://mfm.warhammer-community.com/en/orks", sha256="abc")}}


def test_source_ledger_retains_conditional_and_enhancement_prices():
    data = snapshot()
    assert len(data["pages"]["orks"]["rows"]) == 4
    assert len(operational_factions(data)["orks"]) == 2
    assert data["pages"]["orks"]["detachments"][0]["dp"] == 2


def test_unknown_card_header_and_orphan_price_abort_instead_of_leaking():
    html = source_card(card("GORKANAUT", 325))
    html += source_card(card("NAZDREG", 175).replace("text-xl", "unknown-header"))
    with pytest.raises(mfm.MfmParseBroken, match="names"):
        parse_source_page(html)
    with pytest.raises(mfm.MfmParseBroken, match="coverage"):
        parse_source_page(source_card(card("GORKANAUT", 325)) + '<li><span>1 model</span><span>90 pts</span></li>')


def test_sync_includes_points_only_units_and_updates_enhancements_without_faking_datasheets(tmp_path):
    path = database(tmp_path, [{"desc": "1 model", "cost": 300}])
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE enhancements (id TEXT, faction_id TEXT, name TEXT, detachment_name TEXT, cost INTEGER)")
        conn.execute("INSERT INTO enhancements VALUES ('e1','ORK','Example Upgrade (Aura)','War Horde',10)")
    report = apply_snapshot(path, snapshot())
    assert report["ledger"] == {"source_rows": 4, "database_rows": 4, "equal": True}
    assert report["unit_prices_after"]["mfm_only"] == ["NAZDREG"]
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM units").fetchone()[0] == 1
        assert conn.execute("SELECT cost FROM enhancements").fetchone()[0] == 25
    second = apply_snapshot(path, snapshot())
    assert second["units_applied"]["units_updated"] == 0
    assert second["enhancements"]["changes"] == []
    assert verify_ledger(path, snapshot())["equal"]


def test_failed_post_write_reconciliation_rolls_back_every_table(tmp_path, monkeypatch):
    from db_compile import mfm_sync
    path = database(tmp_path, [{"desc": "1 model", "cost": 300}])
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE enhancements (id TEXT, faction_id TEXT, name TEXT, detachment_name TEXT, cost INTEGER)")
        conn.execute("INSERT INTO enhancements VALUES ('e1','ORK','Example Upgrade','War Horde',10)")
    before = path.read_bytes()
    monkeypatch.setattr(mfm_sync, "verify_ledger", lambda *a, **kw: {"equal": False})
    with pytest.raises(RuntimeError, match="rolled back"):
        apply_snapshot(path, snapshot())
    assert path.read_bytes() == before


def test_legacy_fetch_cannot_replace_complete_snapshot(tmp_path):
    path = tmp_path / "cache.json"
    original = json.dumps({"source_snapshot": snapshot()})
    path.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="complete official snapshot"):
        mfm.fetch_all(path, force=True)
    assert path.read_text(encoding="utf-8") == original


def test_unmatched_legacy_price_is_not_reported_as_current(tmp_path):
    from db_compile.calc_points import calc_points
    path = database(tmp_path, [{"desc": "1 model", "cost": 300}])
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE enhancements (id TEXT, faction_id TEXT, name TEXT, detachment_name TEXT, cost INTEGER)")
        conn.execute("INSERT INTO units VALUES ('legacy','ORK','Archived example',?)",
                     (json.dumps({"items": [{"desc": "1 model", "cost": 123}]}),))
    apply_snapshot(path, snapshot())
    row = calc_points(path, ["legacy"])[0]
    assert row.points is None
    assert "历史点数" in row.note
    from wiki_engine.keyword_index import _current_unit_ids
    with closing(sqlite3.connect(path)) as conn:
        assert _current_unit_ids(conn) == {"u1"}


def test_rebuild_restores_inserted_enhancements_before_applying_official_prices():
    from db_compile.update import _RESTORE_STAGES, stage_fp_rules, stage_mfm_apply
    stages = [fn for title, fn in _RESTORE_STAGES]
    assert stages.index(stage_fp_rules) < stages.index(stage_mfm_apply)
