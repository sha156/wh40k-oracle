from pathlib import Path

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
