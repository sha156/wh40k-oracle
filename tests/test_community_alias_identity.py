"""Community indirection preserves target confidence and the exact-only boundary."""
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from agent.tools import entity_resolver, get_datasheet
from db_compile.datasheet import find_datasheet
from db_compile.entity_resolver import EntityResolver

ROOT = Path(__file__).resolve().parents[1]


def _resolver(tmp_path, aliases, pairs):
    app = tmp_path / "app.py"
    app.write_text("UNIT_ALIASES = " + repr(aliases) + "\n", encoding="utf-8")
    terms = tmp_path / "terms.json"
    terms.write_text(json.dumps({"pairs": pairs}), encoding="utf-8")
    return EntityResolver(app_path=app, terms_path=terms)


def _pair(zh="影阳指挥官", en="Commander Shadowsun", cid="shadowsun", faction="TAU"):
    return {"zh": zh, "en": en, "canonical_id": cid, "faction_id": faction,
            "book": "blacklibrary"}


@pytest.mark.parametrize("target,confidence", [
    ("影阳指挥官", "exact"),
    ("Commander Shadowsu", "fuzzy"),
    ("unresolved designation", "none"),
    ("天行者司战", "none"),
    ("", "none"),
])
def test_indirection_returns_target_result_without_nickname_fallback(tmp_path, target, confidence):
    # The nickname itself resembles a known name. That must not rescue a missing target.
    resolver = _resolver(tmp_path, {"影阳指挥": target}, [_pair()])
    expected = resolver.resolve(target)
    assert expected.confidence == confidence
    assert resolver.resolve("影阳指挥") == expected
    tool = entity_resolver("影阳指挥", resolver=resolver)
    assert tool["confidence"] == confidence
    if confidence == "fuzzy":
        assert "模糊匹配" in tool["note"]


def test_ambiguity_and_qualified_candidates_survive_community_chain(tmp_path):
    resolver = _resolver(tmp_path, {"nickname": "middle", "middle": "Helbrute"}, [
        _pair("甲", "Helbrute", "we", "WE"),
        _pair("乙", "Helbrute", "dg", "DG"),
    ])
    expected = resolver.resolve("Helbrute")
    assert expected.confidence == "ambiguous"
    assert expected.candidates == ["Helbrute (WE)", "Helbrute (DG)"]
    assert resolver.resolve("nickname") == expected
    for candidate, cid in zip(expected.candidates, ("we", "dg")):
        result = resolver.resolve(candidate)
        assert result.confidence == "exact"
        assert result.canonical_id == cid


@pytest.mark.parametrize("aliases", [
    {"影阳指挥": "影阳指挥"},
    {"影阳指挥": "middle", "middle": "影阳指挥"},
])
def test_cycles_are_unresolved_without_nickname_fallback(tmp_path, aliases):
    resolver = _resolver(tmp_path, aliases, [_pair()])
    result = resolver.resolve("影阳指挥")
    assert result.confidence == "none"
    assert result.canonical_id is None
    assert result.candidates == result.suggestions == []


def test_long_chain_is_iterative_and_retained_exact_target_works(tmp_path):
    aliases = {"alias{}".format(i): "alias{}".format(i + 1) for i in range(1100)}
    aliases["alias1100"] = "影阳指挥官"
    resolver = _resolver(tmp_path, aliases, [_pair()])
    assert resolver.resolve("alias0") == resolver.resolve("影阳指挥官")
    # Each call owns its traversal state.
    assert resolver.resolve("alias0").confidence == "exact"


def test_exact_retained_name_precedes_a_conflicting_community_cycle(tmp_path):
    resolver = _resolver(tmp_path, {"影阳指挥官": "影阳指挥官"}, [_pair()])
    assert resolver.resolve("影阳指挥官").confidence == "exact"


@pytest.fixture(scope="module", params=["database-original.sqlite", "database-alias-trial.sqlite"])
def saved_resolver(request, tmp_path_factory):
    # These are saved preparation snapshots, never the active DB or diagnostic name trial.
    source = ROOT / "db_sources/release-check-20260930/retirement-preparation/iteration-04" / request.param
    if not source.exists():
        pytest.skip("Saved preparation database is unavailable")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    db = tmp_path_factory.mktemp("community-identity") / request.param
    shutil.copy2(source, db)
    resolver = EntityResolver(db_path=db, terms_path=ROOT / "wiki/terms.json", app_path=ROOT / "app.py")
    yield db, resolver, request.param
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest


def test_actual_warriors_alias_preserves_target_and_datasheet_boundary(saved_resolver):
    db, resolver, filename = saved_resolver
    expected = resolver.resolve("泰伦武士")
    if filename == "database-original.sqlite":
        assert expected.confidence == "ambiguous"
        assert set(expected.candidates) == {"骨刃利爪泰伦武士", "生化喷吐泰伦武士"}
    else:
        assert expected.confidence == "fuzzy"
        assert expected.canonical_id == "000002692"
        assert expected.name_en == "Tyranid Warriors With Ranged Bio-weapons"
    assert resolver.resolve("虫族武士") == expected
    tool = entity_resolver("虫族武士", resolver=resolver)
    assert tool["confidence"] == expected.confidence
    assert tool["candidates"] == expected.candidates
    assert find_datasheet(db, "虫族武士", resolver=resolver) is None
    card = get_datasheet("虫族武士", db_path=db, resolver=resolver)
    assert card["found"] is False
    assert card["datasheet"] is None
    if expected.confidence == "ambiguous":
        assert card["reason"] == "ambiguous"
        assert card["candidates"] == expected.candidates


def test_actual_retained_community_exact_mapping_still_loads_datasheet(saved_resolver):
    db, resolver, _ = saved_resolver
    # Existing app alias, not a revived retired translation.
    assert resolver._unit_aliases["激素虫"] == "刀虫"
    result = resolver.resolve("激素虫")
    assert result.confidence == "exact"
    assert result.canonical_id == "000000469"
    assert find_datasheet(db, "激素虫", resolver=resolver).unit_id == "000000469"
