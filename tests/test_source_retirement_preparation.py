"""Approved exact-source retirement, including restored downstream caches."""
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

import pytest

from corpus_policy import is_excluded_source
from db_compile.entity_resolver import EntityResolver, _load_term_pairs
from wiki_compile.extract import EntityCandidate, extract_book
from wiki_compile.pair import Pair, PairingResult, pair_entities
from wiki_compile.terms import load_term_aliases, write_terms


# Frozen approved inventory, independent of the policy being tested.
APPROVED_STEMS = [
    "11版40K通用技能速查表", "6月4日分数中文", "6月4日平衡版中午",
    "兽人10版中文老湿腐版1.09", "千子军团CODEX-双子星版 V1.20",
    "吞世者10版中文DavidZ版1.05", "圣血天使10版中文DavidZ版1.05",
    "基因窃取者10版中文DavidZ版1.06", "太空死灵规则2.81",
    "太空野狼10版中文老湿腐版1.13", "帝国特勤中文",
    "帝皇之子10版中文老湿腐版1.05", "战斗修女10版中文DavidZ版1.07",
    "星界军10版中文老湿腐版1.27", "星际战士10版中文老湿腐版1.41",
    "机械修会10版中文老湿腐版1.11", "死亡守卫10版中文老湿腐版1.1",
    "泰伦虫族10版中文老湿腐版1.12", "混沌恶魔10E中文kasa1.2",
    "混沌星际战士10版中文老湿腐版1.17", "混沌骑士CODEX-双子星版 V1.20",
    "灰骑士中文", "艾达灵族10版中文 1.13", "钛帝国十版CODEX-20251112",
    "黑暗天使10版中文老湿腐版1.12", "黑暗灵族10版中文DavidZ版1.0",
    "黑色圣堂CODEX-双子星版 V1.20",
]
ORPHAN_STEMS = [
    "10版40K通用技能速查表1.08", "战锤40K总规则10版老湿腐版1.11", "规则注解中文",
]
OLD_VOTANN = "沃坦联盟CODEX-双子星版 V1.30"
TAU_STEM = "钛帝国十版CODEX-20251112"


@pytest.mark.parametrize("stem", APPROVED_STEMS + ORPHAN_STEMS + [OLD_VOTANN])
def test_exact_retired_pdf_and_cache_restoration_is_blocked(stem, tmp_path):
    from db_compile.aliases import harvest_bilingual_pairs
    from md_chunker import load_refined_book

    assert is_excluded_source("data/{}.pdf".format(stem))
    assert is_excluded_source("D:\\Project\\py\\RAG\\data\\{}.PDF".format(stem))
    book = tmp_path / stem
    book.mkdir()
    (book / "page_001.md").write_text("## 旧名称 OLD UNIT\nOld rules.", encoding="utf-8")
    assert extract_book(book) == []
    assert harvest_bilingual_pairs(tmp_path) == []
    with pytest.raises(ValueError, match="Source retired"):
        load_refined_book(tmp_path / (stem + ".pdf"), tmp_path, {})


@pytest.mark.parametrize("book", [TAU_STEM, "钛帝国十版", "兽人10版中文", "千子军团"])
def test_restored_terms_are_filtered_before_alias_conflicts(book, tmp_path):
    path = tmp_path / "terms.json"
    pairs = [
        {"zh": "独立译名", "en": "Wrong Target", "canonical_id": "wrong", "book": book},
        {"zh": "旧译专名", "en": "Retired Only", "canonical_id": "retired", "book": book},
        {"zh": "独立译名", "en": "Kept Target", "canonical_id": "kept", "book": "blacklibrary"},
    ]
    path.write_text(json.dumps({"pairs": pairs}, ensure_ascii=False), encoding="utf-8")
    assert load_term_aliases(path) == {"独立译名": "Kept Target"}
    assert _load_term_pairs(path) == pairs[2:]
    resolver = EntityResolver(terms_path=path)
    assert resolver.resolve("独立译名").canonical_id == "kept"
    assert resolver.resolve("旧译专名").canonical_id is None
    assert resolver.resolve("Retired Only").canonical_id is None


def test_terms_writer_filters_pairs_and_unmatched_without_mutating_input(tmp_path):
    result = PairingResult(
        pairs=[Pair("旧译专名", "Retired Only", "retired", "TAU", TAU_STEM, [1], "exact"),
               Pair("独立译名", "Kept Target", "kept", "TAU", "blacklibrary", [2], "exact")],
        unmatched=[EntityCandidate("钛帝国十版", "旧标题", "旧标题", None, [3]),
                   EntityCandidate("Faction Pack Tau Empire", "Kept Heading", None, "Kept Heading", [4])],
    )
    before = asdict(result)
    write_terms(result, tmp_path)
    data = json.loads((tmp_path / "terms.json").read_text(encoding="utf-8"))
    assert data["pairs"] == [asdict(result.pairs[1])]
    assert "旧译专名" not in (tmp_path / "terms.md").read_text(encoding="utf-8")
    review = (tmp_path / "review_needed.md").read_text(encoding="utf-8")
    assert "旧标题" not in review
    assert "Kept Heading" in review
    assert asdict(result) == before


def test_restored_entities_do_not_supply_pairing_or_faction_votes():
    from wiki_compile.canonical import CanonicalEntry

    entities = [EntityCandidate(TAU_STEM, "旧译 OLD UNIT", "旧译", "OLD UNIT", [1]),
                EntityCandidate("Faction Pack Tau Empire", "KEPT UNIT", None, "KEPT UNIT", [2])]
    canonical = [CanonicalEntry("old", "OLD UNIT", "TAU"),
                 CanonicalEntry("kept", "KEPT UNIT", "TAU")]
    result = pair_entities(entities, canonical)
    assert [p.canonical_id for p in result.pairs] == ["kept"]
    assert result.unmatched == []


def test_canonical_database_and_independent_alias_survive_retired_cached_pair(tmp_path):
    db = tmp_path / "db.sqlite"
    with sqlite3.connect(str(db)) as conn:
        conn.execute("CREATE TABLE datasheets (id TEXT, name TEXT, faction_id TEXT)")
        conn.execute("INSERT INTO datasheets VALUES ('kept', 'Kept Target', 'TAU')")
        conn.execute("CREATE TABLE aliases (alias TEXT, canonical_id TEXT, lang TEXT, source TEXT)")
        conn.execute("INSERT INTO aliases VALUES ('独立译名', 'kept', 'zh', 'blackforum')")
    path = tmp_path / "terms.json"
    path.write_text(json.dumps({"pairs": [
        {"zh": "独立译名", "en": "Wrong Target", "canonical_id": "wrong", "book": TAU_STEM},
    ]}), encoding="utf-8")
    resolver = EntityResolver(terms_path=path, db_path=db)
    assert resolver.resolve("独立译名").canonical_id == "kept"
    assert resolver.resolve("Kept Target").canonical_id == "kept"
    with sqlite3.connect(str(db)) as conn:
        assert conn.execute("SELECT * FROM aliases").fetchall() == [
            ("独立译名", "kept", "zh", "blackforum")]


def test_actual_approved_inventory_and_retained_sources():
    from corpus_policy import is_excluded_book

    root = Path(__file__).resolve().parent.parent
    inventory = root / "db_sources/release-check-20260930/fan-source-inventory.json"
    if not inventory.exists():
        pytest.skip("Local pre-retirement inventory is absent")
    data = json.loads(inventory.read_text(encoding="utf-8"))
    assert {r["stem"] for r in data["fan_or_unverified"]} == set(APPROVED_STEMS)
    for row in data["fan_or_unverified"]:
        assert is_excluded_source(row["path"])
        assert all(is_excluded_book(book) for book in row["index_books"])
    for row in data["retained_root_english"] + data["retained_official_chinese"]:
        assert not is_excluded_source(row["path"])
        assert all(not is_excluded_book(book) for book in row.get("index_books", []))


def test_actual_terms_retain_exact_official_pairs(tmp_path):
    root = Path(__file__).resolve().parent.parent
    path = root / "wiki/terms.json"
    raw = json.loads(path.read_text(encoding="utf-8"))["pairs"]
    retired = [p for p in raw if p["book"] == TAU_STEM]
    kept = [p for p in raw if p["book"] != TAU_STEM]
    assert len(retired) == 62
    assert len(kept) == 125
    assert _load_term_pairs(path) == kept
    write_terms(PairingResult(pairs=[Pair(**p) for p in raw]), tmp_path)
    assert json.loads((tmp_path / "terms.json").read_text(encoding="utf-8"))["pairs"] == kept


@pytest.mark.parametrize("source", [
    "data/官方中文/千子军团.pdf", "data/官方中文/混沌骑士.pdf",
    "data_refined/Official Source/钛帝国十版.md", "blacklibrary/千子军团",
    "data/Faction Pack Thousand Sons.pdf", "data/帝国骑士英文.pdf",
    "data/死亡守望英文1.01.pdf", TAU_STEM + "-different-source",
])
def test_metadata_labels_do_not_exclude_official_paths_or_similar_stems(source):
    from corpus_policy import is_excluded_book

    assert not is_excluded_source(source)
    assert not is_excluded_book(source)


def test_book_metadata_is_exact_and_case_insensitive():
    from corpus_policy import is_excluded_book

    assert is_excluded_book("钛帝国十版")
    assert is_excluded_book(TAU_STEM.lower())
    assert not is_excluded_book("Faction Pack Tau Empire")
    assert not is_excluded_source("千子军团")
    assert not is_excluded_book("千子军团单位")


@pytest.mark.parametrize("book", [
    "钛帝国十版", "沃坦联盟", "10版40K通用技能速查表", "战锤40K总规则10版", "规则注解中文",
])
def test_normalized_metadata_cannot_restore_database_names(book, tmp_path):
    from db_compile.build import _load_name_zh_by_id

    path = tmp_path / "terms.json"
    path.write_text(json.dumps({"pairs": [
        {"canonical_id": "retired", "zh": "旧译", "book": book},
        {"canonical_id": "kept", "zh": "现译", "book": "blacklibrary"},
    ]}), encoding="utf-8")
    assert _load_name_zh_by_id(path) == {"kept": "现译"}


def test_normalized_pairing_cache_cannot_reach_synthesis(tmp_path, monkeypatch):
    import wiki_engine.synthesize as synthesis

    def unexpected(*args, **kwargs):
        pytest.fail("Retired cached entries reached page synthesis")

    monkeypatch.setattr(synthesis, "synthesize_page", unexpected)
    book = "钛帝国十版"
    path = tmp_path / "pairing.json"
    path.write_text(json.dumps({
        "pairs": [asdict(Pair("旧译", "OLD UNIT", "old", "TAU", book, [1], "exact"))],
        "unmatched": [asdict(EntityCandidate(book, "旧译 OLD UNIT", "旧译", "OLD UNIT", [1]))],
    }), encoding="utf-8")
    refined = tmp_path / "refined"
    (refined / book).mkdir(parents=True)
    (refined / book / "page_001.md").write_text("## 旧译 OLD UNIT\nOld rules.", encoding="utf-8")
    stats = synthesis.synthesize_all(path, refined, tmp_path / "wiki", tmp_path / "cache", client=object())
    assert stats["pairs"] == stats["synthesized"] == stats["failed"] == 0
    assert list((tmp_path / "wiki").rglob("*.md")) == []


@pytest.mark.parametrize("pairs", [None, "invalid", {}, [None, "invalid"]])
def test_resolver_ignores_malformed_cached_pair_containers(pairs, tmp_path):
    path = tmp_path / "terms.json"
    path.write_text(json.dumps({"pairs": pairs}), encoding="utf-8")
    assert _load_term_pairs(path) == []


@pytest.mark.parametrize("name,cid,en", [
    ("影阳指挥官", "000000407", "Commander Shadowsun"),
    ("远见指挥官", "000000406", "Commander Farsight"),
])
def test_actual_tau_independent_blacklibrary_alias_survives_retired_pilot(name, cid, en):
    root = Path(__file__).resolve().parent.parent
    db = root / "db/wh40k.sqlite"
    if not db.exists():
        pytest.skip("Local canonical database is absent")
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
        assert conn.execute(
            "SELECT canonical_id FROM aliases WHERE alias=? AND source='blackforum'",
            (name,),
        ).fetchall() == [(cid,)]
    resolver = EntityResolver(terms_path=root / "wiki/terms.json", db_path=db)
    result = resolver.resolve(name)
    assert (result.canonical_id, result.name_en, result.confidence) == (cid, en, "exact")
