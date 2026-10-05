"""Coverage decisions at real simulation and roster boundaries, temporary SQL only."""
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict

import pytest

from agent.tools import simulate_combat_resolved
from db_compile.source_coverage import apply_coverage
from engines.roster import Roster, RosterUnit, validate
from engines.roster.critique import critique
from tests.test_db_compile_datasheet import _make_db
from tests.test_source_coverage_consumers import UID, assert_provenance, declaration
from web_api.simulate import run_simulation


OTHER = "fixture-defender"
GUN = "Plasma pistol – standard"
OPTIONS = {"n": 100, "seed": 7, "reverse_phase": "shooting", "loadout": [(GUN, 1)],
           "defender_loadout": [(GUN, 1)]}


def database(tmp_path):
    db = _make_db(tmp_path)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.executescript("""
            CREATE TABLE abilities(id TEXT, owner_id TEXT, name_en TEXT, text_zh TEXT, effect_dsl_json TEXT);
            CREATE TABLE stratagems(effect_dsl_json TEXT);
            CREATE TABLE enhancements(id TEXT, faction_id TEXT, detachment_id TEXT,
                detachment_name TEXT, name TEXT, cost INTEGER, effect_dsl_json TEXT);
            CREATE TABLE detachments(name_en TEXT, faction TEXT);
        """)
        row = conn.execute("SELECT * FROM units WHERE id=?", (UID,)).fetchone()
        conn.execute("INSERT INTO units VALUES (?,?,?,?,?,?,?)", (OTHER, *row[1:2], "Fixture Defender", *row[3:]))
        row = conn.execute("SELECT * FROM models WHERE unit_id=?", (UID,)).fetchone()
        conn.execute("INSERT INTO models VALUES (?,?,?,?,?,?,?,?,?,?,?)", (OTHER, *row[1:]))
        for row in conn.execute("SELECT * FROM weapons WHERE unit_id=?", (UID,)).fetchall():
            conn.execute("INSERT INTO weapons VALUES (?,?,?,?,?,?,?,?,?,?,?)", ("other-" + row[0], OTHER, *row[2:]))
    return db


def install(db, records):
    from db_compile.mfm_source import write_ledger
    src = records[0]["points"]["sources"][0]
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("BEGIN")
        conn.execute("UPDATE units SET points_json=?", (json.dumps({
            "items": [{"desc": "1 model", "cost": 85}], "mfm": {"current": True}}),))
        write_ledger(conn, {"fetched_at": src["captured_at"], "pages": {
            "chaos-space-marines": {"url": src["url"], "sha256": src["sha256"], "rows": [
                {"kind": "unit", "section": "UNITS", "unit": r["identity"]["name_en"],
                 "tier": "YOUR UNIT COSTS", "models": "1 model", "cost": 85} for r in records]}}})
        apply_coverage(conn, {"schema_version": 1, "records": records},
                       expected_records=[None] * len(records))


def for_side(status, retained, side):
    record = declaration(status, retained)
    if side == OTHER:
        record["identity"].update(unit_id=OTHER, name_en="Fixture Defender")
    return record


def resolved(db, options=None):
    return simulate_combat_resolved({"canonical_id": UID, "name_en": "Chaos Lord"},
                                   {"canonical_id": OTHER, "name_en": "Fixture Defender"},
                                   OPTIONS if options is None else options, db)


def roster(uid=UID, name="Chaos Lord", loadout=True):
    return Roster("CSM", None, "strike_force", (
        RosterUnit(uid, name, 1, is_warlord=True, loadout=((GUN, 1),) if loadout else ()),))


def whole_note(note, record):
    assert note
    for value in (record["identity"]["name_en"], record["identity"]["unit_id"] or "no canonical body",
                  "CSM", "chaos-space-marines", "reviewed 2026-10-01", record["body"]["status"],
                  "Points: current_published", "points effective date unverified", "does not certify body"):
        assert value in note
    for src in record["body"]["sources"] + record["points"]["sources"]:
        assert_provenance(note, src)
    if record["body"]["effective_date"]:
        assert "body effective 2026-09-14" in note
    if record["body"]["retained_snapshot"]:
        assert "retained full_body effective 2026-09-14" in note
        assert_provenance(note, record["body"]["retained_snapshot"]["sources"][0])
    if record["body"]["status"] == "fields_only":
        assert "verified scope: " + ", ".join(record["body"]["scope"]) in note
        assert "full body unverified" in note


@pytest.mark.parametrize("side", [UID, OTHER])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("status,retained,allowed", [
    ("current_full_verified", True, True), ("historical_snapshot", True, True),
    ("newer_full_unavailable", True, True), ("newer_full_unavailable", False, False),
    ("fields_only", True, False),
])
def test_simulation_checks_each_body_before_output(tmp_path, side, reverse, status, retained, allowed):
    db = database(tmp_path)
    record = for_side(status, retained, side)
    install(db, [record])
    before = db.read_bytes()
    options = {k: v for k, v in OPTIONS.items() if k != "defender_loadout"}
    if reverse:
        options.update(reverse=True, defender_loadout=[(GUN, 1)])
    res = run_simulation(db, UID, OTHER, options)
    assert res is not None and res.ok is allowed, res
    whole_note(res.warning if allowed else res.note, record)
    if allowed:
        assert res.report and res.report.expected_damage > 0
        assert bool(res.report.reverse) is reverse
    else:
        assert res.reason == "body_unverified" and res.report is None
        assert ("attacker" if side == UID else "defender") in res.note
    assert db.read_bytes() == before


def test_both_retained_notes_are_whole_once_and_reversing_is_numeric_equivalent(tmp_path):
    db = database(tmp_path)
    before = resolved(db)
    records = [for_side("historical_snapshot", True, UID),
               for_side("newer_full_unavailable", True, OTHER)]
    install(db, records)
    after = resolved(db)
    assert before["ok"] and after["ok"]
    assert after["report"] == before["report"]
    for record in records:
        whole_note(after["warning"], record)
        assert after["warning"].count("Source coverage: " + record["identity"]["name_en"]) == 1
    swapped = simulate_combat_resolved({"canonical_id": OTHER, "name_en": "Fixture Defender"},
                                      {"canonical_id": UID, "name_en": "Chaos Lord"}, OPTIONS, db)
    assert swapped["ok"] and swapped["report"]["reverse"]
    for record in records:
        whole_note(swapped["warning"], record)


@pytest.mark.parametrize("status,retained,assessed", [
    ("current_full_verified", True, True), ("historical_snapshot", True, True),
    ("newer_full_unavailable", True, True), ("newer_full_unavailable", False, False),
    ("fields_only", True, False),
])
def test_roster_price_validity_discloses_body_and_critique_does_not_fabricate(tmp_path, status, retained, assessed):
    db = database(tmp_path)
    record = declaration(status, retained)
    install(db, [record])
    before = db.read_bytes()
    report = validate(db, roster())
    assert report.legal and report.total_points == 85 and not report.errors
    issue = next(i for i in report.issues if i.code == "source_coverage")
    whole_note(issue.message, record)
    assert issue.surfaced_only and issue.severity == "warn"
    assert "legal=True means no checked constraint failed" in issue.message
    critique_report = critique(db, roster(), n=100, seed=7)
    assessment = critique_report.assessments[0]
    assert assessment.assessed is assessed
    whole_note(assessment.note, record)
    assert assessment.scores if assessed else not assessment.scores
    assert any(assessment.note in note for note in critique_report.not_modeled)
    assert db.read_bytes() == before


def test_fields_only_complete_calculation_scope_is_not_a_full_rules_guarantee(tmp_path):
    db = database(tmp_path)
    record = declaration("fields_only")
    record["body"]["scope"] = ["models", "weapons", "keywords", "composition", "equipment", "abilities"]
    install(db, [record])
    res = resolved(db)
    assert res["ok"], res
    whole_note(res["warning"], record)
    assessment = critique(db, roster(), n=100).assessments[0]
    assert assessment.assessed
    whole_note(assessment.note, record)


def test_defender_fields_do_not_certify_reverse_weapons(tmp_path):
    db = database(tmp_path)
    record = for_side("fields_only", True, OTHER)
    record["body"]["scope"] = ["models", "keywords", "abilities", "composition"]
    install(db, [record])
    forward = resolved(db, {k: v for k, v in OPTIONS.items() if k != "defender_loadout"})
    assert forward["ok"], forward
    whole_note(forward["warning"], record)
    reverse = resolved(db)
    assert not reverse["ok"] and reverse["reason"] == "body_unverified"
    assert "weapons" in reverse["note"] and "equipment" in reverse["note"]


@pytest.mark.parametrize("status", ["historical_snapshot", "newer_full_unavailable", "fields_only"])
def test_roster_unverified_keywords_do_not_fabricate_current_hard_errors(tmp_path, status):
    db = database(tmp_path)
    record = declaration(status)
    if status == "fields_only":
        record["body"]["scope"] = ["models"]
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET keywords_json=? WHERE id=?", (json.dumps({
            "keywords": ["Infantry", "Epic Hero"], "faction_keywords": ["Chaos"]}), UID))
    install(db, [record])
    r = roster()
    r = Roster(r.faction_id, r.detachment_id, r.size, r.units + r.units)
    # One warlord and two stale EPIC HERO copies: price checking still works,
    # while current character/copy eligibility cannot be proved by this body.
    from dataclasses import replace
    r = replace(r, units=(r.units[0], replace(r.units[1], is_warlord=False)))
    result = validate(db, r)
    assert result.legal and result.total_points == 170 and not result.errors
    issue = next(i for i in result.issues if i.code == "source_coverage")
    assert "Keyword-based eligibility/copy limits remain unverified" in issue.message
    whole_note(issue.message, record)


def test_retained_critique_keeps_qualifier_when_loadout_absent_or_invalid(tmp_path):
    db = database(tmp_path)
    record = declaration("newer_full_unavailable")
    install(db, [record])
    for r in (roster(loadout=False), Roster("CSM", None, "strike_force", (
            RosterUnit(UID, "Chaos Lord", 1, loadout=(("Wrong weapon", 1),)),))):
        result = critique(db, r, n=100)
        assessment = result.assessments[0]
        assert not assessment.assessed and not assessment.scores
        whole_note(assessment.note, record)
        assert any(assessment.note in value for value in result.not_modeled)
        assert "来源覆盖限制" in " ".join(result.summary)


@pytest.mark.parametrize("mutation", ["identity", "json", "models", "deleted"])
def test_invalid_declarations_visible_before_simulation_or_roster_use(tmp_path, mutation):
    db = database(tmp_path)
    install(db, [declaration()])
    with closing(sqlite3.connect(db)) as conn, conn:
        if mutation == "identity":
            conn.execute("UPDATE units SET name_en='Wrong sibling' WHERE id=?", (UID,))
        elif mutation == "models":
            conn.execute("DELETE FROM models WHERE unit_id=?", (UID,))
        elif mutation == "deleted":
            conn.execute("DELETE FROM units WHERE id=?", (UID,))
        else:
            conn.execute("UPDATE source_coverage_registry SET record_json='broken'")
    result = resolved(db)
    assert not result["ok"] and result["reason"] == "coverage_invalid"
    assert "Source coverage invalid" in result["note"]
    from db_compile.coverage_notes import CoverageError
    with pytest.raises(CoverageError):
        validate(db, roster())
    with pytest.raises(CoverageError):
        critique(db, roster(), n=100)
    response = run_simulation(db, UID, OTHER, OPTIONS)
    assert response and not response.ok and response.reason == "coverage_invalid"


def test_source_only_price_has_no_roster_or_combat_body(tmp_path):
    db = database(tmp_path)
    install(db, [declaration("source_only_price")])
    r = roster("Source Hero", "Source Hero")
    report = validate(db, r)
    assert report.total_points == 0
    assert any(i.code == "unit_not_found" for i in report.issues)
    a = critique(db, r, n=100).assessments[0]
    assert not a.assessed and not a.scores and a.points is None
    assert run_simulation(db, "Source Hero", OTHER, OPTIONS) is None
    res = simulate_combat_resolved({"canonical_id": "Source Hero", "name_en": "Source Hero"},
                                  {"canonical_id": OTHER, "name_en": "Fixture Defender"}, OPTIONS, db)
    assert not res["ok"] and res["reason"] == "not_found"


def test_legacy_absent_and_empty_registry_payloads_and_unknown_errors_unchanged(tmp_path):
    db = database(tmp_path)
    before = (resolved(db), asdict(validate(db, roster())), asdict(critique(db, roster(), n=100)))
    assert before[0]["ok"] and before[2]["assessments"][0]["assessed"]
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE source_coverage_registry(identity_key TEXT PRIMARY KEY,record_json TEXT NOT NULL)")
    after = (resolved(db), asdict(validate(db, roster())), asdict(critique(db, roster(), n=100)))
    assert after == before
    assert run_simulation(db, "unknown", OTHER, OPTIONS) is None
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("DELETE FROM models WHERE unit_id=?", (OTHER,))
    res = resolved(db)
    assert not res["ok"] and res["reason"] == "not_found"


def failure_records(swapped=False):
    """Two dated bodies with independent prices and deliberately long provenance."""
    statuses = ["historical_snapshot", "newer_full_unavailable"]
    if swapped:
        statuses.reverse()
    records = [for_side(status, True, side) for status, side in zip(statuses, (UID, OTHER))]
    for record in records:
        sources = record["body"]["sources"] + record["points"]["sources"]
        if record["body"]["retained_snapshot"]:
            sources += record["body"]["retained_snapshot"]["sources"]
        for index, src in enumerate(sources):
            subject = ("current-price" if src in record["points"]["sources"]
                       else record["identity"]["unit_id"])
            src["url"] += "/" + (subject + f"-source-{index}-") * 160
    return records


def failure_options(case):
    options = dict(OPTIONS)
    if case == "attacker-invalid-loadout":
        options["loadout"] = [("Wrong weapon", 1)]
    elif case == "attacker-wrong-phase":
        options["phase"] = "melee"
    elif case == "defender-invalid-loadout":
        options["defender_loadout"] = [("Wrong weapon", 1)]
    elif case == "defender-wrong-phase":
        options["reverse_phase"] = "melee"
    else:
        raise AssertionError(case)
    return options


def failure_result(db, options, caller):
    if caller == "tool":
        return resolved(db, options)
    return run_simulation(db, UID, OTHER, options).model_dump()


def assert_failure_qualifiers(result, records):
    from db_compile.coverage_notes import describe_coverage
    assert not result["ok"] and not result.get("report")
    for side, record in zip(("attacker", "defender"), records):
        qualifier = f"{side}: {describe_coverage(record)}"
        assert result["note"].count(qualifier) == 1
        whole_note(result["note"], record)


@pytest.mark.parametrize("caller", ["tool", "web"])
@pytest.mark.parametrize("swapped", [False, True])
@pytest.mark.parametrize("case", [
    "attacker-invalid-loadout", "attacker-wrong-phase",
    "defender-invalid-loadout", "defender-wrong-phase",
])
def test_ordinary_failure_retains_both_whole_qualifiers(tmp_path, caller, swapped, case):
    db = database(tmp_path)
    records = failure_records(swapped)
    install(db, records)
    before = db.read_bytes()
    result = failure_result(db, failure_options(case), caller)
    assert result["weapon_pool"] and result["model_tiers"] == [{"models": 1, "cost": 85}]
    expected = ("defender_" if case.startswith("defender") else "") + (
        "loadout_required" if case.endswith("invalid-loadout") else "no_weapon_for_phase")
    assert result["reason"] == expected
    assert_failure_qualifiers(result, records)
    assert db.read_bytes() == before


@pytest.mark.parametrize("caller", ["tool", "web"])
@pytest.mark.parametrize("boundary", [
    "attacker-missing", "target-missing", "reverse-missing", "execution",
    "attacker-no-phase-pool", "defender-no-phase-pool",
])
def test_other_post_coverage_failures_keep_notes(tmp_path, monkeypatch, caller, boundary):
    db = database(tmp_path)
    records = failure_records()
    install(db, records)
    import engines.simulator.assembly as assembly
    import engines.simulator.profile as profile
    import engines.simulator.engine as engine
    options = dict(OPTIONS)
    if boundary in ("attacker-missing", "reverse-missing"):
        original = assembly.assemble_attacker
        missing = UID if boundary == "attacker-missing" else OTHER

        def controlled_assembly(db_path, unit_id, **kwargs):
            return None if unit_id == missing else original(db_path, unit_id, **kwargs)

        monkeypatch.setattr(assembly, "assemble_attacker", controlled_assembly)
    elif boundary == "target-missing":
        monkeypatch.setattr(profile, "load_target", lambda *args, **kwargs: None)
    elif boundary == "execution":
        def fail_execution(*args, **kwargs):
            raise RuntimeError("controlled execution failure after supported bodies")

        monkeypatch.setattr(engine, "simulate_matchup", fail_execution)
    else:
        uid = UID if boundary.startswith("attacker") else OTHER
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("DELETE FROM weapons WHERE unit_id=? AND range != 'Melee'", (uid,))
        options.pop("loadout" if uid == UID else "defender_loadout")
        options["reverse"] = True
    before = db.read_bytes()
    result = failure_result(db, options, caller)
    assert_failure_qualifiers(result, records)
    if boundary == "execution":
        assert "controlled execution failure" in result["note"]
    elif boundary.endswith("no-phase-pool"):
        assert result["weapon_pool"] and result["model_tiers"]
    else:
        assert result["reason"] == "not_found"
    assert db.read_bytes() == before


@pytest.mark.parametrize("empty_registry", [False, True])
@pytest.mark.parametrize("case", [
    "attacker-invalid-loadout", "attacker-wrong-phase",
    "defender-invalid-loadout", "defender-wrong-phase",
])
def test_absent_declarations_do_not_invent_failure_qualifiers(tmp_path, empty_registry, case):
    db = database(tmp_path)
    if empty_registry:
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("CREATE TABLE source_coverage_registry(identity_key TEXT PRIMARY KEY,record_json TEXT NOT NULL)")
    before = db.read_bytes()
    for caller in ("tool", "web"):
        result = failure_result(db, failure_options(case), caller)
        assert not result["ok"] and not result.get("report")
        assert "Source coverage:" not in result["note"]
        assert not result.get("warning")
    assert db.read_bytes() == before
