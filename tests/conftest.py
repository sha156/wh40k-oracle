from pathlib import Path
import hashlib
import json
import shutil

import fitz
import pytest


def make_pdf(path: Path, texts) -> Path:
    """生成简单多页 PDF，每页一段 ASCII 文本（fitz 默认字体不含中文）。"""
    doc = fitz.open()
    for t in texts:
        page = doc.new_page()
        page.insert_text((72, 72), t)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def tiny_pdf(tmp_path):
    return make_pdf(
        tmp_path / "book.pdf",
        ["UNIT ALPHA M 6 T 4 SV 3+ W 5", "WEAPON TABLE Range 24 A 2 BS 3+"],
    )


@pytest.fixture(scope="module")
def retirement_snapshot():
    """Historical reconciliation stays frozen rather than constraining live counts."""
    path = Path(__file__).parent / "fixtures/source_retirement_preparation.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=["active", "original", "cleaned"])
def retirement_assets(request, tmp_path_factory, retirement_snapshot):
    """Exercise active and both saved preparation states using disposable copies."""
    root = Path(__file__).resolve().parents[1]
    evidence = root / "db_sources/release-check-20260930/retirement-preparation"
    state = request.param
    if state == "active":
        sources = (root / "db/wh40k.sqlite", root / "wiki/terms.json")
    else:
        db_name = "database-original.sqlite" if state == "original" else "database-alias-trial.sqlite"
        term_dir = "original" if state == "original" else "filtered"
        sources = (evidence / "iteration-04" / db_name,
                   evidence / "iteration-01/terms" / term_dir / "terms.json")
    if not all(path.exists() for path in sources):
        pytest.skip("Local {} preparation assets are unavailable".format(state))
    digests = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    if state != "active":
        for path, digest in digests.items():
            assert digest == retirement_snapshot["sources_sha256"][path.relative_to(root).as_posix()]
    copied = tmp_path_factory.mktemp("retirement-" + state)
    db, terms = copied / "copy.sqlite", copied / "terms.json"
    for source, target in zip(sources, (db, terms)):
        shutil.copy2(source, target)
    yield {"state": state, "db": db, "terms": terms}
    assert digests == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
