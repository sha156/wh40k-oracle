import sqlite3

import pytest

from db_compile.source_reconcile import apply_patches


def patch(uid, old, new):
    return {"table": "abilities", "key": {"id": uid}, "from": {"text_zh": old},
            "to": {"text_zh": new}, "source": {"url": "https://example.com/rules.pdf",
            "page": 7, "sha256": "a" * 64}}


def test_drift_rolls_back_preceding_changes(tmp_path):
    db = tmp_path / "trial.sqlite"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE abilities(id TEXT PRIMARY KEY,text_zh TEXT)")
        c.executemany("INSERT INTO abilities VALUES (?,?)", [("one", "old"), ("two", "upstream change")])
    with pytest.raises(ValueError, match="prior-value mismatch"):
        apply_patches(db, {"patches": [patch("one", "old", "new"), patch("two", "old", "new")]})
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT text_zh FROM abilities WHERE id='one'").fetchone()[0] == "old"


def test_repeated_apply_preserves_exact_official_text(tmp_path):
    db = tmp_path / "trial.sqlite"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE abilities(id TEXT PRIMARY KEY,text_zh TEXT)")
        c.execute("INSERT INTO abilities VALUES ('one','old')")
    manifest = {"patches": [patch("one", "old", "Move 8\"; ignore CHARACTER models.")]}
    assert apply_patches(db, manifest)["applied"] == 1
    assert apply_patches(db, manifest)["already"] == 1


def test_untrusted_field_is_rejected_before_sql(tmp_path):
    p = patch("one", "old", "new")
    p["to"] = {"text_zh; DROP TABLE units": "bad"}
    with pytest.raises(ValueError, match="fields"):
        apply_patches(tmp_path / "uncreated.sqlite", {"patches": [p]})
    assert not (tmp_path / "uncreated.sqlite").exists()


@pytest.mark.parametrize("phase,keywords,expected", [
    ("shooting", {"astra militarum"}, True),
    ("shooting", {"astra militarum", "titanic"}, False),
    ("shooting", {"adeptus astartes"}, False),
    ("melee", {"astra militarum"}, False),
])
def test_current_camouflage_excludes_titans_and_melee(phase, keywords, expected):
    from types import SimpleNamespace
    from engines.simulator.effect_params import _cond_true
    target = SimpleNamespace(keywords=keywords)
    stance = SimpleNamespace(phase=phase)
    assert _cond_true(("shooting_astra_militarum_non_titanic",), stance, target) is expected


def test_shared_titan_price_conflict_does_not_create_database(tmp_path):
    from db_compile.mfm import MfmParseBroken, apply_points
    db = tmp_path / "uncreated.sqlite"
    rows = {"titan-legions": [("WARHOUND TITAN", "YOUR UNIT COSTS", "1 model", 1100)],
            "chaos-titan-legions": [("CHAOS WARHOUND TITAN", "YOUR UNIT COSTS", "1 model", 1200)]}
    with pytest.raises(MfmParseBroken, match="Shared Titan"):
        apply_points(db, rows)
    assert not db.exists()


def test_translation_invalidation_does_not_erase_cached_source(tmp_path):
    from db_compile.blacklibrary import load_zh_detail
    db = tmp_path / "trial.sqlite"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE unit_zh_detail(canonical_id TEXT,name_zh TEXT,faction_zh TEXT,stats_json TEXT,abilities_json TEXT,weapons_json TEXT)")
        c.execute("INSERT INTO unit_zh_detail VALUES ('one','Name','Faction','[]','[\"Old rule\"]','[]')")
        c.execute("CREATE TABLE official_rule_revisions(unit_id TEXT,source_date TEXT)")
        c.execute("INSERT INTO official_rule_revisions VALUES ('one','2026-09-14')")
    assert load_zh_detail(db, "one")["能力"] is None
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT abilities_json FROM unit_zh_detail").fetchone()[0] == '["Old rule"]'


def test_prune_targets_only_obsolete_translation_documents(tmp_path):
    from types import SimpleNamespace
    from db_compile.source_reconcile import stale_translation_ids
    db = tmp_path / "trial.sqlite"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE official_rule_revisions(unit_id TEXT,source_date TEXT)")
        c.execute("CREATE TABLE unit_zh_detail(canonical_id TEXT,name_zh TEXT)")
        c.execute("INSERT INTO official_rule_revisions VALUES ('one','2026-09-14')")
        c.execute("INSERT INTO unit_zh_detail VALUES ('one','Updated unit')")
    docs = {"obsolete": SimpleNamespace(metadata={"source": "blacklibrary", "unit": "Updated unit"}),
            "unaffected": SimpleNamespace(metadata={"source": "blacklibrary", "unit": "Other unit"}),
            "official": SimpleNamespace(metadata={"source": "rules.pdf", "unit": "Updated unit"})}
    assert stale_translation_ids(db, docs) == ["obsolete"]


@pytest.mark.parametrize("text,keyword,expected", [
    ("ANTI-MONSTER/VEHICLE 3+", "monster", True),
    ("ANTI-MONSTER/VEHICLE 3+", "vehicle", True),
    ("ANTI-MONSTER/VEHICLE 3+", "infantry", False),
    ("ANTI-non-MONSTER/VEHICLE 2+", "infantry", True),
    ("ANTI-non-MONSTER/VEHICLE 2+", "monster", False),
    ("LETHAL HITS: non-MONSTER/VEHICLE", "vehicle", False),
    ("LETHAL HITS: non-MONSTER/VEHICLE", "infantry", True),
    ("DEVASTATING WOUNDS: non-MONSTER/VEHICLE", "vehicle", False),
])
def test_current_weapon_keyword_conditions(text, keyword, expected):
    from types import SimpleNamespace
    from engines.simulator.parse import parse_keyword_token
    from engines.simulator.keywords import keyword_to_effects
    from engines.simulator.effect_params import _cond_true
    parsed = parse_keyword_token(text)
    assert parsed.recognized
    effects, _, _ = keyword_to_effects(parsed)
    assert len(effects) == 1
    assert _cond_true(effects[0].condition, SimpleNamespace(), SimpleNamespace(keywords={keyword})) is expected
