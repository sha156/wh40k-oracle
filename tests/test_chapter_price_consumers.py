"""Paired consumer acceptance on independent copies of the retained actual DB."""
import json
import sqlite3
from contextlib import closing

import pytest

from agent import tools
from db_compile.calc_points import calc_points
from engines.roster import Roster, RosterUnit
from engines.roster.points import _chapter_slug, recompute, total_points
from web_api import codex, official_points
from web_api.contract import RosterIn
from web_api.roster import validate_roster
from tests.test_mfm_chapter_context import (
    BASE, BT_IDS, GENERIC_IDS, NAMES, REPEAT, actual_copy, all_tables, mfm,
)

TOTALS = (300, 525, 465, 525, 825, 600)


def project(actual_copy):
    path, factions, snapshot = actual_copy
    mfm.apply_points(path, factions, fetched_at=snapshot["fetched_at"])
    return path


def roster(uid, count, *, detachment=None, loadout=(("Multi-melta", 1),)):
    return Roster("SM", detachment, "strike_force", tuple(
        RosterUnit(uid, "display name is not price identity", 1, loadout=loadout)
        for _ in range(count)))


@pytest.mark.parametrize("index", range(6))
def test_actual_canonical_agent_and_card_agree_with_chapter_base(actual_copy, index):
    path = project(actual_copy)
    before = path.read_bytes()
    uid, base = BT_IDS[index], BASE[index]
    assert calc_points(path, [uid])[0].points == base
    agent = tools.calc_points([uid], db_path=path)
    assert agent["units"][0]["unit_id"] == uid
    assert agent["units"][0]["points"] == base
    assert any(s["url"].endswith("/black-templars") for s in agent["official_sources"])
    assert codex.unit_card(path, uid, lang="en").pts == str(base)
    assert path.read_bytes() == before


@pytest.mark.parametrize("index", range(6))
def test_actual_roster_api_and_occurrence_option_totals_agree_at_boundary(actual_copy, index):
    path = project(actual_copy)
    before = path.read_bytes()
    uid, base, repeat = BT_IDS[index], BASE[index], REPEAT[index]
    count = 4 if index == 0 else 3
    req = RosterIn(factionId="SM", units=[
        {"canonicalId": uid, "models": 1, "loadout": [["Multi-melta", 1]]}
        for _ in range(count)])
    assert validate_roster(path, req).total_points == TOTALS[index]
    priced = recompute(path, roster(uid, count))
    assert [u.points for u in priced.units] == [base] * (count - 1) + [repeat + 10]
    assert total_points(priced) == TOTALS[index]
    assert path.read_bytes() == before


@pytest.mark.parametrize("index", range(6))
def test_explicit_generic_and_chapter_selectors_never_exchange_canonical_ids(actual_copy, index):
    path = project(actual_copy)
    bt = official_points.exact_unit(path, NAMES[index], faction_slug="black-templars")
    generic = official_points.exact_unit(path, NAMES[index], faction_slug="space-marines")
    for price, matching, wrong in [(bt, BT_IDS[index], GENERIC_IDS[index]),
                                    (generic, GENERIC_IDS[index], BT_IDS[index])]:
        assert official_points._canonical_identity_matches(path, matching, price)
        assert not official_points._canonical_identity_matches(path, wrong, price)
        selector = price["faction_slug"]
        query = next(iter(official_points.exact_unit(path, NAMES[index])["candidates"]), None)
        assert query is not None
        from urllib.parse import quote
        selected = tools.calc_points([
            "@mfm:" + selector + ":" + quote(NAMES[index], safe="")], db_path=path)["units"][0]
        assert selected["points"] == price["points"] and selected["unit_id"] is None
        assert selected["official_prices"] == price["official_prices"]
        assert selected["points_only"] and selected["effective_date"] is None
    ambiguous = tools.calc_points([NAMES[index]], db_path=path)["units"][0]
    assert ambiguous["ambiguous"] and ambiguous["points"] is None
    assert len(ambiguous["candidates"]) == 6


@pytest.mark.parametrize("detachment", [None, "fp11e-bt-marshals", "fp11e-bt-miracle",
                                        "000000794", "000000796"])
def test_actual_bt_canonical_tie_prices_generic_entry_without_inventing_detachment_route(actual_copy, detachment):
    path = project(actual_copy)
    mixed = Roster("SM", detachment, "strike_force", (
        RosterUnit(BT_IDS[1], "Gladiator Lancer", 1),
        *roster(GENERIC_IDS[1], 2).units))
    with closing(sqlite3.connect(path)) as conn:
        assert _chapter_slug(conn, mixed) is None  # All five actual name-only routes are unproven.
    before = all_tables(path)
    assert [u.points for u in recompute(path, mixed).units] == [165, 165, 195]
    assert all_tables(path) == before


@pytest.mark.parametrize("detachment", [None, "000000794", "000000796"])
def test_generic_only_roster_keeps_generic_price_when_detachment_name_is_ambiguous(actual_copy, detachment):
    path = project(actual_copy)
    # Generic Executioner repeats charge for Heavy Laser Destroyer, not Multi-melta.
    r = roster(GENERIC_IDS[4], 3, detachment=detachment,
               loadout=(("Heavy Laser Destroyer", 1),))
    assert [u.points for u in recompute(path, r).units] == [260, 260, 290]


@pytest.mark.parametrize("keywords", [None, ["Adeptus Astartes", "Unknown Chapter"],
    ["Adeptus Astartes", "Black Templars", "Blood Angels"],
    ["Black Templars"], ["Adeptus Astartes", "Black Templars", "Agents of the Imperium"]])
def test_uncertain_canonical_identity_cannot_recover_generic_roster_or_selector_price(actual_copy, keywords):
    path = project(actual_copy)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE units SET keywords_json=? WHERE id=?", (
            None if keywords is None else json.dumps({"faction_keywords": keywords}), BT_IDS[1]))
    r = roster(BT_IDS[1], 3)
    assert all(u.points is None for u in recompute(path, r).units)
    for slug in ("space-marines", "black-templars"):
        price = official_points.exact_unit(path, NAMES[1], faction_slug=slug)
        assert not official_points._canonical_identity_matches(path, BT_IDS[1], price)


def test_distinct_chapters_and_conflicting_exact_detachment_route_fail_closed(actual_copy):
    path = project(actual_copy)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE units SET keywords_json=? WHERE id=?", (
            json.dumps({"faction_keywords": ["Adeptus Astartes", "Blood Angels"]}), GENERIC_IDS[1]))
    r = Roster("SM", None, "strike_force", (
        *roster(BT_IDS[1], 1).units, *roster(GENERIC_IDS[1], 1).units))
    assert all(u.points is None for u in recompute(path, r).units)
    # Synthetic conflicting route on this disposable copy, preserving actual ledger unit rows.
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE enhancements SET detachment_name='Exact conflicting route' WHERE detachment_id='fp11e-bt-marshals'")
        conn.execute("UPDATE official_mfm_detachments SET name='Exact conflicting route' "
                     "WHERE faction_slug='blood-angels' AND name=(SELECT name FROM "
                     "official_mfm_detachments WHERE faction_slug='blood-angels' ORDER BY name LIMIT 1)")
    assert all(u.points is None for u in recompute(path, roster(
        BT_IDS[1], 3, detachment="fp11e-bt-marshals")).units)


@pytest.mark.parametrize("chapters", [("Black Templars", "Ultramarines"),
                                    ("Ultramarines", "White Scars")])
def test_named_chapters_cannot_merge_through_their_generic_price_route(actual_copy, chapters):
    path = project(actual_copy)
    with closing(sqlite3.connect(path)) as conn, conn:
        for uid, chapter in zip((BT_IDS[1], GENERIC_IDS[1]), chapters):
            conn.execute("UPDATE units SET keywords_json=? WHERE id=?", (
                json.dumps({"faction_keywords": ["Adeptus Astartes", chapter]}), uid))
    r = Roster("SM", None, "strike_force", (
        *roster(BT_IDS[1], 1).units, *roster(GENERIC_IDS[1], 1).units))
    assert all(u.points is None for u in recompute(path, r).units)


def test_exact_retained_unique_detachment_can_price_generic_unit_only_with_matching_chapter(actual_copy):
    path = project(actual_copy)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE enhancements SET detachment_name=? WHERE detachment_id='fp11e-bt-marshals'",
                     ("MARSHAL'S HOUSEHOLD",))
    r = roster(GENERIC_IDS[1], 3, detachment="fp11e-bt-marshals")
    with closing(sqlite3.connect(path)) as conn:
        assert _chapter_slug(conn, r) == "black-templars"
    assert [u.points for u in recompute(path, r).units] == [165, 165, 195]
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE units SET keywords_json=? WHERE id=?", (
            json.dumps({"faction_keywords": ["Adeptus Astartes", "Ultramarines"]}), GENERIC_IDS[1]))
    assert all(u.points is None for u in recompute(path, r).units)


@pytest.mark.parametrize("loadout,last", [((), None), ((("Typo weapon", 1),), None),
    ((("Multi-melta", 2),), 205), ((("Multi-melta - focused", 1),), 195),
    ((("Multi-melta", 1), ("Multi-melta", 1)), 205),
    ((("Multi-melta", 0),), None), ((("Multi-melta", True),), None)])
def test_repeated_paid_options_counts_and_unknown_loadout_guards(actual_copy, loadout, last):
    path = project(actual_copy)
    assert recompute(path, roster(BT_IDS[1], 3, loadout=loadout)).units[-1].points == last


def test_impulsor_both_options_and_known_free_weapon_stay_separate_from_base(actual_copy):
    path = project(actual_copy)
    paid = recompute(path, roster(BT_IDS[0], 4,
        loadout=(("Multi-melta", 2), ("Orbital Comms Array", 1))))
    assert [u.points for u in paid.units] == [70, 70, 70, 110]
    with closing(sqlite3.connect(path)) as conn:
        free, = conn.execute("SELECT name_en FROM weapons WHERE unit_id=? AND name_en!='Multi-melta' ORDER BY rowid LIMIT 1", (BT_IDS[1],)).fetchone()
    assert recompute(path, roster(BT_IDS[1], 3, loadout=((free, 1),))).units[-1].points == 185
    assert recompute(path, roster(BT_IDS[4], 3, loadout=(("Multi-melta", 1),))).units[-1].points == 295
    doubled_models = Roster("SM", None, "strike_force", (
        RosterUnit(BT_IDS[1], NAMES[1], 2, loadout=(("Multi-melta", 1),)),))
    assert recompute(path, doubled_models).units[0].points is None
    req = RosterIn(factionId="SM", units=[
        {"canonicalId": BT_IDS[1], "models": 1,
         "loadout": [["Multi-melta", 1], ["Multi-melta", 1]]} for _ in range(3)])
    assert validate_roster(path, req).total_points == 535


def test_missing_exact_chapter_head_or_wrong_roster_faction_never_falls_back(actual_copy):
    path = project(actual_copy)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("DELETE FROM official_mfm_points WHERE faction_slug='black-templars' AND unit_name='GLADIATOR LANCER'")
    assert all(u.points is None for u in recompute(path, roster(BT_IDS[1], 3)).units)
    r = Roster("AC", None, "strike_force", roster(BT_IDS[1], 1).units)
    assert recompute(path, r).units[0].points is None
