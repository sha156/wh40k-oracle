"""Retired content cannot return through PDF or derived-cache entry points."""
import json
from pathlib import Path

import pytest

from corpus_policy import is_excluded_source, require_active_source

RETIRED = "沃坦联盟CODEX-双子星版 V1.30"


@pytest.mark.parametrize("source", [RETIRED, f"data/{RETIRED}.pdf",
    f"D:\\Project\\py\\RAG\\data\\{RETIRED}.PDF", f"data_refined/{RETIRED}/page_001.md"])
def test_retirement_matches_raw_and_derived_paths(source):
    assert is_excluded_source(source)
    with pytest.raises(ValueError, match="Source retired"):
        require_active_source(source)


@pytest.mark.parametrize("source", ["data/Faction Pack Leagues Of Votann.pdf",
    "data/官方中文/沃坦联盟.pdf", "blacklibrary", "data/Imperial Knights.pdf"])
def test_allowed_sources_are_preserved(source):
    assert not is_excluded_source(source)


def test_reintroduced_cache_cannot_supply_aliases_or_entities(tmp_path):
    from db_compile.aliases import harvest_bilingual_pairs
    from wiki_compile.extract import extract_book
    retired = tmp_path / RETIRED
    retired.mkdir()
    (retired / "page_001.md").write_text("## 旧名称 OLD UNIT\nOld rules.", encoding="utf-8")
    allowed = tmp_path / "Official Source"
    allowed.mkdir()
    (allowed / "page_001.md").write_text("## 官方名称 OFFICIAL UNIT\nCurrent rules.", encoding="utf-8")
    assert extract_book(retired) == []
    assert harvest_bilingual_pairs(tmp_path) == [("官方名称", "OFFICIAL UNIT")]


def test_retired_refinement_rejected_before_reading_pdf(tmp_path):
    from md_chunker import load_refined_book
    with pytest.raises(ValueError, match="Source retired"):
        load_refined_book(tmp_path / f"{RETIRED}.pdf", tmp_path, {})


def test_retired_terms_cannot_restore_database_names(tmp_path):
    from db_compile.build import _load_name_zh_by_id
    path = tmp_path / "terms.json"
    path.write_text(json.dumps({"pairs": [
        {"canonical_id": "retired", "zh": "旧名", "book": RETIRED},
        {"canonical_id": "kept", "zh": "现名", "book": "Official Source"},
    ]}), encoding="utf-8")
    assert _load_name_zh_by_id(path) == {"kept": "现名"}
