"""Official keyword defaults are repository inputs; explicit paths remain caller inputs."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from wiki_engine import keyword_index as ki
from wiki_engine.core_rules_zh import EN_PDF, ZH_PDF

REPO = Path(__file__).resolve().parents[1]
needs_sources = pytest.mark.skipif(
    not all((REPO / path).exists() for path in (EN_PDF, ZH_PDF)),
    reason="Retained official bilingual Core Rules PDFs are absent")


@pytest.fixture
def official_pair(tmp_path):
    if not all((REPO / path).exists() for path in (EN_PDF, ZH_PDF)):
        pytest.skip("Retained official bilingual Core Rules PDFs are absent")
    en, zh = tmp_path / "custom-english.pdf", tmp_path / "custom-chinese.pdf"
    shutil.copy2(REPO / EN_PDF, en)
    shutil.copy2(REPO / ZH_PDF, zh)
    return en, zh


@needs_sources
@pytest.mark.parametrize("explicit_english", [False, True])
def test_repository_defaults_outside_cwd(tmp_path, monkeypatch, explicit_english):
    expected = ki.parse_quickref(REPO / EN_PDF, REPO / ZH_PDF)
    assert len(expected) == 35
    monkeypatch.chdir(tmp_path)
    actual = ki.parse_quickref(REPO / EN_PDF) if explicit_english else ki.parse_quickref()
    # All identities, Chinese names, section numbers and transition flags survive.
    assert actual == expected
    assert ki.classify("PISTOL", actual) == "transitional"
    for token in ("ANTI-INFANTRY 4+", "RAPID FIRE D6+3",
                  "SUSTAINED HITS 1: INFANTRY/BEASTS"):
        assert ki.classify(token, actual) == "universal"


@needs_sources
def test_default_sources_cannot_be_shadowed_by_cwd(tmp_path, monkeypatch):
    expected = ki.parse_quickref(REPO / EN_PDF, REPO / ZH_PDF)
    for relative in (EN_PDF, ZH_PDF):
        shadow = tmp_path / relative
        shadow.parent.mkdir(parents=True, exist_ok=True)
        shadow.write_bytes(b"Not an official PDF")
    monkeypatch.chdir(tmp_path)
    assert ki.parse_quickref() == expected


def test_explicit_relative_pdf_pair_uses_caller_cwd(official_pair, monkeypatch):
    en, zh = official_pair
    expected = ki.parse_quickref(en, zh)
    monkeypatch.chdir(en.parent)
    assert ki.parse_quickref(Path(en.name), Path(zh.name)) == expected


@needs_sources
def test_generation_outside_cwd_preserves_complete_payload(tmp_path, monkeypatch,
                                                          retirement_assets):
    db = retirement_assets["db"]
    wiki = REPO / "wiki"
    baseline = tmp_path / "baseline"
    ki.generate(db, wiki, REPO / EN_PDF, out_root=baseline)
    monkeypatch.chdir(tmp_path)
    report = ki.generate(db, wiki, out_root=tmp_path / "outside")
    assert report["core_rules_entries"] == report["quickref_entries"] == 35
    assert report["groups"] == {"universal": 36, "transitional": 1, "unit-specific": 13}
    for relative in (ki.INDEX_REL, ki.PAYLOAD_REL):
        assert (tmp_path / "outside" / relative).read_bytes() == (baseline / relative).read_bytes()


def test_generation_accepts_explicit_chinese_companion(official_pair, tmp_path,
                                                      retirement_assets, monkeypatch):
    en, zh = official_pair
    monkeypatch.chdir(tmp_path)
    # A custom missing companion must be honored, not replaced by the default.
    with pytest.raises(FileNotFoundError, match="missing-chinese.pdf"):
        ki.generate(retirement_assets["db"], REPO / "wiki", en,
                    out_root=tmp_path / "missing-output",
                    zh_pdf_path=tmp_path / "missing-chinese.pdf")
    assert not (tmp_path / "missing-output").exists()
    report = ki.generate(retirement_assets["db"], REPO / "wiki", Path(en.name),
                         tmp_path / "custom-output", zh_pdf_path=Path(zh.name))
    assert report["core_rules_entries"] == 35
    items = json.loads((tmp_path / "custom-output" / ki.PAYLOAD_REL).read_text(
        encoding="utf-8"))["items"]
    pistol = next(item for item in items if item["base"] == "PISTOL")
    assert (pistol["section"], pistol["group"], pistol["quickrefZh"]) == (
        "24.27", "transitional", None)


@needs_sources
@pytest.mark.parametrize("entrypoint", ["package", "module"])
@pytest.mark.parametrize("custom", [False, True])
def test_both_keyword_clis_use_official_defaults_and_explicit_companion(
        entrypoint, custom, official_pair, tmp_path, monkeypatch, retirement_assets):
    from wiki_engine import cli

    en, zh = official_pair
    wiki = tmp_path / "cli-output"
    baseline = tmp_path / "expected-output"
    ki.generate(retirement_assets["db"], wiki, en, baseline)
    argv = ["wiki_engine", "keywords"] if entrypoint == "package" else ["keyword_index"]
    argv += ["--db", str(retirement_assets["db"]), "--wiki", str(wiki)]
    if custom:
        argv += ["--pdf", en.name, "--zh-pdf", zh.name]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    (cli.main if entrypoint == "package" else ki.main)()
    for relative in (ki.INDEX_REL, ki.PAYLOAD_REL):
        assert (wiki / relative).read_bytes() == (baseline / relative).read_bytes()


@pytest.mark.parametrize("retired_language", ["english", "chinese"])
def test_generation_rejects_retired_input_before_any_output(tmp_path, retired_language):
    retired = Path("data/11版40K通用技能速查表.pdf")
    args = {"pdf_path": retired} if retired_language == "english" else {"zh_pdf_path": retired}
    with pytest.raises(ValueError, match="Source retired"):
        ki.generate(tmp_path / "no-database.sqlite", tmp_path / "no-wiki",
                    out_root=tmp_path / "output", **args)
    assert not (tmp_path / "no-database.sqlite").exists()
    assert not (tmp_path / "output").exists()


@needs_sources
@pytest.mark.parametrize("entrypoint", ["package", "module"])
@pytest.mark.parametrize("retired", [False, True])
def test_both_clis_honor_invalid_explicit_companion(tmp_path, monkeypatch, entrypoint, retired):
    from wiki_engine import cli

    companion = "data/11版40K通用技能速查表.pdf" if retired else "missing-chinese.pdf"
    argv = ["wiki_engine", "keywords"] if entrypoint == "package" else ["keyword_index"]
    argv += ["--db", str(tmp_path / "no-database.sqlite"), "--wiki", str(tmp_path / "output"),
             "--zh-pdf", companion]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    exception = ValueError if retired else FileNotFoundError
    message = "Source retired" if retired else "missing-chinese.pdf"
    with pytest.raises(exception, match=message):
        (cli.main if entrypoint == "package" else ki.main)()
    assert not (tmp_path / "no-database.sqlite").exists()
    assert not (tmp_path / "output").exists()
