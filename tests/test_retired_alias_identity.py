"""Retiring a spelling must not turn it into a different unit through fuzzy lookup."""
import json
import shutil
from pathlib import Path

import pytest

from db_compile.entity_resolver import EntityResolver


# Observed on the actual filtered alias rebuild, not invented rule/name data.
RETARGETS = {
    "仇天使机甲": "000000908",
    "圣像旗手": "000002775",
    "天行者司战": "000000583",
    "携疱者": "000004113",
    "洒血鬼教徒": "000000512",
    "犀牛运兵车": "000002723",
    "瘟疫旗手": "000002775",
    "西多尼亚枪骑兵": "000003695",
    "豺狼邪教徒": "000003849",
    "轰轰飚速车": "000001539",
    "钢牛领主": "000000524",
}
ROOT = Path(__file__).resolve().parents[1]


def _resolver(tmp_path, pairs):
    terms = tmp_path / "terms.json"
    terms.write_text(json.dumps({"pairs": pairs}, ensure_ascii=False), encoding="utf-8")
    return EntityResolver(terms_path=terms)


def test_retired_spelling_does_not_become_a_nearby_unit(tmp_path):
    resolver = _resolver(tmp_path, [{"zh": "天行者司巫", "en": "Farseer Skyrunner",
                                    "canonical_id": "farseer", "book": "blacklibrary"}])
    result = resolver.resolve("天行者司战")
    assert result.canonical_id is None
    assert result.confidence == "none"
    assert result.candidates == []


def test_retained_exact_evidence_overrides_the_fuzzy_guard(tmp_path):
    resolver = _resolver(tmp_path, [{"zh": "天行者司战", "en": "Autarch Skyrunner",
                                    "canonical_id": "autarch", "book": "blacklibrary"}])
    assert resolver.resolve("天行者司战").canonical_id == "autarch"
    assert resolver.resolve("天行者司战").confidence == "exact"


def test_retained_normalized_exact_evidence_overrides_guard(tmp_path):
    resolver = _resolver(tmp_path, [{"zh": "天行者·司战", "en": "Autarch Skyrunner",
                                    "canonical_id": "autarch", "book": "blacklibrary"}])
    result = resolver.resolve("天行者司战")
    assert result.canonical_id == "autarch"
    assert result.confidence == "exact"


def test_explicit_community_mapping_overrides_guard(tmp_path):
    _resolver(tmp_path, [{"zh": "官方译名", "en": "Autarch Skyrunner",
                          "canonical_id": "autarch", "book": "blacklibrary"}])
    app = tmp_path / "app.py"
    app.write_text('UNIT_ALIASES = {"天行者司战": "Autarch Skyrunner"}\n', encoding="utf-8")
    resolver = EntityResolver(terms_path=tmp_path / "terms.json", app_path=app)
    assert resolver.resolve("天行者司战").canonical_id == "autarch"
    assert resolver.resolve("天行者司战").confidence == "exact"


def test_retired_separator_variant_cannot_escape_guard(tmp_path):
    resolver = _resolver(tmp_path, [{"zh": "天行者司巫", "en": "Farseer Skyrunner",
                                    "canonical_id": "farseer", "book": "blacklibrary"}])
    assert resolver.resolve("天行者·司战").canonical_id is None


def test_unrelated_typo_correction_is_preserved(tmp_path):
    resolver = _resolver(tmp_path, [{"zh": "影阳指挥官", "en": "Commander Shadowsun",
                                    "canonical_id": "shadowsun", "book": "blacklibrary"}])
    result = resolver.resolve("Commander Shadowsu")
    assert result.canonical_id == "shadowsun"
    assert result.confidence == "fuzzy"


@pytest.fixture(scope="module")
def filtered_resolver(tmp_path_factory):
    from db_compile.aliases import populate_aliases

    source = ROOT / "db/wh40k.sqlite"
    caches = ROOT / "data_refined"
    if not source.exists() or not caches.exists():
        pytest.skip("Actual database and refined assets are unavailable")
    copy = tmp_path_factory.mktemp("retired-alias-identity") / "copy.sqlite"
    shutil.copy2(source, copy)
    populate_aliases(copy, caches)
    return EntityResolver(db_path=copy, terms_path=ROOT / "wiki/terms.json",
                          app_path=ROOT / "app.py")


@pytest.mark.parametrize("query,wrong_target", list(RETARGETS.items()))
def test_actual_filtered_database_rejects_all_observed_retargets(filtered_resolver,
                                                               query, wrong_target):
    result = filtered_resolver.resolve(query)
    assert result.canonical_id is None, (query, wrong_target, result)
    assert result.confidence == "none"


def test_guard_is_not_a_source_or_book_exclusion():
    from corpus_policy import is_excluded_book, is_excluded_source

    for spelling in RETARGETS:
        assert not is_excluded_book(spelling)
        assert not is_excluded_source("data/官方中文/" + spelling + ".pdf")


def test_audited_negative_catalogue_is_complete():
    from corpus_policy import retired_alias_spellings

    spellings = retired_alias_spellings()
    assert len(spellings) == 228
    assert set(RETARGETS) <= spellings


@pytest.mark.parametrize("invalid", [None, [" "], [123]])
def test_malformed_negative_catalogue_fails_closed(tmp_path, monkeypatch, invalid):
    import corpus_policy

    path = tmp_path / "corpus_policy.json"
    path.write_text(json.dumps({"excluded_stems": [], "excluded_book_names": [],
                                "retired_alias_spellings": invalid}), encoding="utf-8")
    monkeypatch.setattr(corpus_policy, "__file__", str(tmp_path / "corpus_policy.py"))
    corpus_policy._policy.cache_clear()
    try:
        with pytest.raises(ValueError, match="retired_alias_spellings"):
            corpus_policy.retired_alias_spellings()
    finally:
        corpus_policy._policy.cache_clear()


def test_actual_original_alias_identities_are_unchanged():
    from db_compile.aliases import load_zh_aliases

    source = ROOT / "db/wh40k.sqlite"
    if not source.exists():
        pytest.skip("Actual database is unavailable")
    aliases = load_zh_aliases(source)
    resolver = EntityResolver(db_path=source, terms_path=ROOT / "wiki/terms.json",
                              app_path=ROOT / "app.py")
    assert len(aliases) == 1206
    for name, cid in aliases.items():
        result = resolver.resolve(name)
        assert result.canonical_id == cid, (name, cid, result)
        assert result.confidence == "exact"
