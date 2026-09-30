"""Synthetic non-current prices must never become current card/picker prices."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

import pytest

from db_compile.calc_points import calc_points
from db_compile.datasheet import _parse_points, lookup_datasheet
from db_compile.schema import ALL_DDL
from engines.roster import Roster, RosterUnit, validate
from engines.roster.points import recompute, unit_cost
from web_api.codex import list_units, unit_card
from web_api.entity_card import build_entity_card


ARMOUR = "999990155"  # Synthetic canonical ID; never loaded from production.
NAME = "Marneus Calgar in Armour of Antilochus"
OPTIONS = [{"line": "1", "desc": "1 model", "cost": 155}]
SOURCE = {
    "current": False,
    "fetched_at": "2026-09-14T12:00:00Z",
    "checked_at": "2026-09-30T12:00:00Z",
    "source_url": "https://example.invalid/synthetic-mfm",
    "source_sha256": "a" * 64,
    "tiers": [{"tier": "YOUR UNIT COSTS", "models": "1 model", "cost": 155}],
}


def fixture_database(tmp_path, payload):
    """Real schema and stored payloads, no production DB or source reads."""
    path = tmp_path / "synthetic.sqlite"
    with sqlite3.connect(str(path)) as conn:
        for ddl in ALL_DDL:
            conn.executescript(ddl)
        conn.execute("CREATE TABLE official_mfm_points (faction_slug TEXT)")
        conn.execute("INSERT INTO factions (id,name) VALUES ('SM','Space Marines')")
        conn.execute("INSERT INTO datasheets (id,name,faction_id) VALUES (?,?,'SM')",
                     (ARMOUR, NAME))
        conn.execute(
            "INSERT INTO units (id,faction_id,name_en,points_json,keywords_json) "
            "VALUES (?,'SM',?,?,?)", (ARMOUR, NAME, json.dumps(payload), json.dumps({
                "keywords": ["CHARACTER", "EPIC HERO"],
                "faction_keywords": ["ADEPTUS ASTARTES", "ULTRAMARINES"],
            })))
        conn.execute(
            "INSERT INTO models (unit_id,name,m,t,sv,invuln,w,ld,oc) "
            "VALUES (?,?,'6','6','2+','4+','8','6+','3')", (ARMOUR, NAME))
    return path


def payload(source=SOURCE, options=OPTIONS):
    result = {"points": 155, "items": options}
    if source is not None:
        result["mfm"] = source
    return result


def text(rows):
    return " | ".join("".join(getattr(span, "s", "") for span in row) for row in rows)


def test_noncurrent_parser_never_returns_current_options():
    assert _parse_points(json.dumps(payload())) == (None, [])


def test_historical_evidence_retains_exact_variant_tiers_and_source(tmp_path):
    db = fixture_database(tmp_path, payload())
    before = db.read_bytes()
    ds = lookup_datasheet(db, ARMOUR)
    assert ds.unit_id == ARMOUR and ds.name_en == NAME and ds.faction == "Space Marines"
    assert ds.points_min is None and ds.points_options == []
    assert ds.historical_points == {
        "status": "historical", "points_options": OPTIONS, "source": SOURCE,
    }
    assert "155" in ds.source_note and "Historical" in ds.source_note
    assert "captured 2026-09-14" in ds.source_note
    assert "checked 2026-09-30" in ds.source_note
    assert "effective" not in ds.source_note.lower()
    assert "180" not in ds.source_note and "200" not in ds.source_note
    assert ds.models[0].name == NAME and ds.models[0].w == "8"
    assert db.read_bytes() == before


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_direct_card_and_chat_payload_omit_historical_badge_and_composition(tmp_path, lang):
    db = fixture_database(tmp_path, payload())
    direct = unit_card(db, ARMOUR, lang=lang)
    result = {"found": True, "datasheet": asdict(lookup_datasheet(db, ARMOUR)),
              "lang": lang}
    chat = build_entity_card(result)
    # Even an injected community override cannot restore a retired current tier.
    overridden = build_entity_card(dict(result, zh_composition=["1 个模型，155分"]))
    for card in (direct, chat, overridden):
        assert card.pts == "—"
        assert "155" not in text(card.composition)
        assert "Historical" in card.src and "155" in card.src
    assert direct.faction_keywords == "ADEPTUS ASTARTES，ULTRAMARINES"


def test_unknown_capture_is_explicit_and_check_date_is_not_relabelled(tmp_path):
    source = {"current": False, "checked_at": "2026-09-30"}
    ds = lookup_datasheet(fixture_database(tmp_path, payload(source)), ARMOUR)
    assert "capture date unavailable" in ds.source_note
    assert "captured 2026-09-30" not in ds.source_note
    assert ds.historical_points["source"] == source


def test_historical_preview_does_not_claim_current_mfm(tmp_path, monkeypatch):
    monkeypatch.setattr("db_compile.source_reconcile.unit_sources", lambda *args: [{
        "kind": "official-preview-image", "published": "2026-09-14",
    }])
    ds = lookup_datasheet(fixture_database(tmp_path, payload()), ARMOUR)
    assert "Historical" in ds.source_note
    assert "released codex rules not verified" in ds.source_note
    assert "current MFM points" not in ds.source_note


def test_agent_datasheet_adapter_keeps_history_without_current_citation(tmp_path):
    from agent.tools import get_datasheet
    from db_compile.entity_resolver import EntityResolver

    db = fixture_database(tmp_path, payload())
    result = get_datasheet(ARMOUR, db_path=db, resolver=EntityResolver(db_path=db))
    assert result["found"] is True and result["datasheet"]["unit_id"] == ARMOUR
    assert result["datasheet"]["points_options"] == []
    assert result["datasheet"]["historical_points"]["source"] == SOURCE
    assert not result.get("official_sources")
    assert build_entity_card(result).pts == "—"


def test_retired_prices_stay_unpriced_in_list_picker_and_roster(tmp_path):
    db = fixture_database(tmp_path, payload())
    assert list_units(db, "SM") == []
    # Simulator and roster pickers reuse this catalogue API, not card options.
    listed = list_units(db, "SM", include_legacy=True)
    assert listed[0]["legacy"] is True and listed[0]["pts"] is None
    assert calc_points(db, [ARMOUR])[0].points is None
    assert unit_cost(json.dumps(payload()), 1) is None
    roster = Roster("SM", None, "strike_force", (
        RosterUnit(ARMOUR, NAME, 1, is_warlord=True, points=155),))
    assert recompute(db, roster).units[0].points is None
    report = validate(db, roster)
    assert report.total_points == 0
    assert any(i.code == "unit_unpriced" and i.surfaced_only for i in report.issues)
    assert roster.units[0].points == 155  # No shared mutable comparison input.


@pytest.mark.parametrize("source", [None, {"fetched_at": "2026-09-14"},
                                    dict(SOURCE, current=True)])
def test_current_and_legacy_prices_keep_exact_tiers_and_card_behavior(tmp_path, source):
    options = OPTIONS + [{"line": "2", "desc": "2 models", "cost": 310}]
    if source and source.get("tiers"):
        source = dict(source, tiers=source["tiers"] + [
            {"tier": "YOUR UNIT COSTS", "models": "2 models", "cost": 310}])
    db = fixture_database(tmp_path, payload(source, options))
    ds = lookup_datasheet(db, ARMOUR)
    assert ds.points_min == 155 and ds.points_options == options
    assert getattr(ds, "historical_points", None) is None and ds.source_note is None
    assert unit_cost(json.dumps(payload(source, options)), 2) == 310
    assert list_units(db, "SM", include_legacy=True)[0]["pts"] == "155 分起"
    for lang, unit in (("en", "pts"), ("zh", "分")):
        card = unit_card(db, ARMOUR, lang=lang)
        assert card.pts == "155 / 310"
        assert "155 " + unit in text(card.composition)
        assert "310 " + unit in text(card.composition)
        assert card.src == "L3 结构库 · Space Marines"


def test_missing_price_is_unknown_without_inventing_history(tmp_path):
    ds = lookup_datasheet(fixture_database(tmp_path, {}), ARMOUR)
    assert ds.points_min is None and ds.points_options == []
    assert getattr(ds, "historical_points", None) is None and ds.source_note is None
    assert build_entity_card({"found": True, "datasheet": asdict(ds)}).pts == "—"
