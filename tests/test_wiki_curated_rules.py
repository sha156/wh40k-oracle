"""Retained-rule publication fails closed and never touches unrelated pages."""
from __future__ import annotations

import csv
from pathlib import Path
import shutil

import pytest
import yaml

from wiki_engine import curated_rules as rules
from wiki_engine._io import GenHashesCorrupt
from wiki_engine.models import WikiPage

REPO = Path(__file__).resolve().parents[1]
missing = [relative for relative, _ in rules.SOURCES.values()
           if not (REPO / relative).is_file()]
needs_sources = pytest.mark.skipif(
    bool(missing), reason="Missing retained curated-rule assets: " + ", ".join(missing))


@pytest.fixture
def copied_wiki(tmp_path):
    wiki = tmp_path / "wiki"
    (wiki / "core-rules").mkdir(parents=True)
    for slug in rules.SLUGS:
        source = REPO / "wiki/core-rules" / (slug + ".md")
        # Preserve real metadata and add an unknown field to catch lossy schema
        # round trips. Force an older body to exercise publication after the real
        # pages have themselves been reconciled.
        fm = yaml.safe_load(source.read_text(encoding="utf-8").split("---", 2)[1])
        fm["review_context"] = {"keep": ["custom metadata", slug]}
        fm["updated"] = "2026-07-01"
        (wiki / "core-rules" / (slug + ".md")).write_text(
            "---\n{}---\n\nOld body\n".format(yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)),
            encoding="utf-8")
    (wiki / "log.md").write_text("Original log\n", encoding="utf-8")
    (wiki / "core-rules/unrelated.md").write_text("Preserve unrelated bytes\n", encoding="utf-8")
    return wiki


def snapshot(wiki):
    return {path.relative_to(wiki).as_posix(): path.read_bytes()
            for path in wiki.rglob("*") if path.is_file()}


def test_changed_source_fails_before_any_publication(copied_wiki, tmp_path, monkeypatch):
    root = tmp_path / "sources"
    root.mkdir()
    (root / "input.csv").write_bytes(b"changed body")
    monkeypatch.setattr(rules, "SOURCES", {"abilities": ("input.csv", "0" * 64)})
    before = snapshot(copied_wiki)
    with pytest.raises(ValueError, match="Unreviewed curated-rule source"):
        rules.generate_all(copied_wiki, root)
    assert snapshot(copied_wiki) == before


def test_missing_source_fails_before_any_publication(copied_wiki, tmp_path):
    before = snapshot(copied_wiki)
    with pytest.raises(FileNotFoundError):
        rules.generate_all(copied_wiki, tmp_path / "absent")
    assert snapshot(copied_wiki) == before


def test_boundaries_require_complete_nonempty_rule():
    for text in ("start body", "end body", "startend", "start body startend"):
        with pytest.raises(ValueError):
            rules._between(text, "start", "end")


def test_dark_pacts_uses_csm_identity_not_first_shared_row(tmp_path):
    csv_path = tmp_path / "Abilities.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, delimiter="|", fieldnames=["id", "name", "faction_id", "description"])
        writer.writeheader()
        for faction, description in (("CD", "Wrong faction body"), ("CSM", "CSM complete body")):
            writer.writerow({"id": "000008359", "name": "Dark Pacts", "faction_id": faction,
                             "description": description})
    assert rules._dark_pacts(csv_path) == "CSM complete body"
    with csv_path.open("a", encoding="utf-8") as stream:
        stream.write("000008359|Dark Pacts|CSM|Duplicate body\n")
    with pytest.raises(ValueError, match="exactly one CSM"):
        rules._dark_pacts(csv_path)


@needs_sources
def test_real_generation_is_complete_preserves_metadata_and_is_idempotent(copied_wiki):
    before = snapshot(copied_wiki)
    result = rules.generate_all(copied_wiki)
    assert result["reviewed"] == result["written"] == 3
    assert set(result["changed"]) == {"core-rules/" + slug + ".md" for slug in rules.SLUGS}
    for slug in rules.SLUGS:
        path = copied_wiki / "core-rules" / (slug + ".md")
        old = yaml.safe_load(before["core-rules/" + slug + ".md"].decode().split("---", 2)[1])
        new = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])
        assert {k: v for k, v in old.items() if k not in {"sources", "updated", "version"}} == {
            k: v for k, v in new.items() if k not in {"sources", "updated", "version"}}
        if slug != "dark-pact":
            assert old.get("version") == new.get("version")
        assert WikiPage.from_markdown(path.read_text(encoding="utf-8")).fm.id == slug
    after = snapshot(copied_wiki)
    assert after["core-rules/unrelated.md"] == before["core-rules/unrelated.md"]
    assert after["log.md"].startswith(before["log.md"])
    assert rules.generate_all(copied_wiki)["written"] == 0
    assert snapshot(copied_wiki) == after


@needs_sources
def test_manual_edit_and_corrupt_registry_fail_closed(copied_wiki):
    rules.generate_all(copied_wiki)
    last = copied_wiki / "core-rules/oath-of-moment.md"
    last.write_text(last.read_text(encoding="utf-8") + "\nManual edit\n", encoding="utf-8")
    before = snapshot(copied_wiki)
    with pytest.raises(ValueError, match="manual edit requires review"):
        rules.generate_all(copied_wiki)
    assert snapshot(copied_wiki) == before
    (copied_wiki / ".gen_hashes.json").write_text("broken", encoding="utf-8")
    before = snapshot(copied_wiki)
    with pytest.raises(GenHashesCorrupt):
        rules.generate_all(copied_wiki)
    assert snapshot(copied_wiki) == before


@needs_sources
@pytest.mark.parametrize("problem", ["missing", "identity"])
def test_last_page_preflight_prevents_partial_publication(copied_wiki, problem):
    last = copied_wiki / "core-rules/oath-of-moment.md"
    if problem == "missing":
        last.unlink()
        expected = FileNotFoundError
    else:
        last.write_text(last.read_text(encoding="utf-8").replace("id: oath-of-moment", "id: wrong"),
                        encoding="utf-8")
        expected = ValueError
    before = snapshot(copied_wiki)
    with pytest.raises(expected):
        rules.generate_all(copied_wiki)
    assert snapshot(copied_wiki) == before


@needs_sources
def test_real_rules_keep_all_effects_and_honest_authority(copied_wiki):
    rules.generate_all(copied_wiki)
    texts = {slug: (copied_wiki / "core-rules" / (slug + ".md")).read_text(encoding="utf-8")
             for slug in rules.SLUGS}
    cleave, dark, oath = (texts[slug] for slug in rules.SLUGS)
    for token in ("[CLEAVE X]", "one target", "every five models", "16 models", "total of six", "爆炸 X"):
        assert token in cleave
    for token in ("Leadership test before any effects", "D3 mortal wounds", "[LETHAL HITS]",
                  "[SUSTAINED HITS 1]", "until the end of the phase", "不是 GW 官方出版物"):
        assert token in dark
    for token in ("start of your Command phase", "next Command phase", "re-roll the Hit roll",
                  "Codex: Space Marines Detachment", "BLOOD ANGELS", "DARK ANGELS", "DEATHWATCH",
                  "SPACE WOLVES", "Munitorum Field Manual sections", "add 1 to the Wound roll"):
        assert token in oath
    for text in texts.values():
        assert all(retired not in text for retired in ("通用技能速查表", "老湿腐", "6月4日平衡"))
    assert "区别只有" not in cleave
    assert "BLACK TEMPLARS" not in oath
    assert "未改动本军队规则" not in dark
    assert "官方中文原文" not in dark
    assert "部分汉化版本" not in oath
    assert "译作" not in oath


@needs_sources
@pytest.mark.parametrize("relative", ["core-rules/cleave.md", ".gen_hashes.json", "log.md"])
def test_real_generation_ignores_planted_temp_links(copied_wiki, tmp_path, relative):
    outside = tmp_path / "outside-sentinel"
    outside.write_bytes(b"outside original")
    target = copied_wiki / relative
    planted = target.with_name(target.name + ".tmp")
    planted.symlink_to(outside)
    rules.generate_all(copied_wiki)
    assert outside.read_bytes() == b"outside original"
    assert planted.is_symlink() and planted.resolve() == outside
    assert target.is_file() and not target.is_symlink()
    after = snapshot(copied_wiki)
    assert rules.generate_all(copied_wiki)["written"] == 0
    assert snapshot(copied_wiki) == after


@needs_sources
@pytest.mark.parametrize("relative", ["core-rules/cleave.md", "core-rules/oath-of-moment.md",
                                      ".gen_hashes.json", "log.md"])
def test_final_output_links_still_fail_before_publication(copied_wiki, tmp_path, relative):
    target = copied_wiki / relative
    outside = tmp_path / "outside"
    outside.write_bytes(target.read_bytes() if target.exists() else b"{}")
    if target.exists():
        target.unlink()
    target.symlink_to(outside)
    before = snapshot(copied_wiki)
    original = outside.read_bytes()
    with pytest.raises(ValueError):
        rules.generate_all(copied_wiki)
    assert snapshot(copied_wiki) == before and outside.read_bytes() == original


@needs_sources
@pytest.mark.parametrize("key", list(rules.SOURCES))
@pytest.mark.parametrize("problem", ["missing", "changed"])
def test_each_actual_pinned_input_blocks_all_outputs(copied_wiki, tmp_path, key, problem):
    sources = tmp_path / "source-copy"
    target = sources / rules.SOURCES[key][0]
    for relative, _ in rules.SOURCES.values():
        destination = sources / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination == target:
            shutil.copy2(REPO / relative, destination)
        else:
            # Other pinned inputs are read-only links; never duplicate the
            # whole large source pack for each independent negative control.
            destination.symlink_to(REPO / relative)
    try:
        if problem == "missing":
            target.unlink()
            expected = FileNotFoundError
        else:
            with target.open("ab") as stream:
                stream.write(b"unreviewed change")
            expected = ValueError
        before = snapshot(copied_wiki)
        with pytest.raises(expected):
            rules.generate_all(copied_wiki, sources)
        assert snapshot(copied_wiki) == before
    finally:
        if target.exists():
            target.unlink()
