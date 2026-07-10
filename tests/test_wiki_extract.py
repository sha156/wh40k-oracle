"""标题解析与实体抽取测试。样本取自 data_refined 实测格式。"""
from pathlib import Path

from wiki_compile.extract import extract_book, extract_entities, parse_heading


def _write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8")


class TestParseHeading:
    def test_bilingual_heading(self):
        assert parse_heading("克鲁特狂兽小队 KROOTOX RAMPAGERS") == (
            "克鲁特狂兽小队", "KROOTOX RAMPAGERS")

    def test_numbered_prefix_stripped(self):
        assert parse_heading("(TX4)水虎鱼 PIRANHAS") == ("水虎鱼", "PIRANHAS")
        assert parse_heading("(XV88)炮击战斗服小队 BROADSIDE BATTLESUITS") == (
            "炮击战斗服小队", "BROADSIDE BATTLESUITS")

    def test_pure_english_heading(self):
        assert parse_heading("TA’UNAR SUPREMACY ARMOUR") == (
            None, "TA’UNAR SUPREMACY ARMOUR")

    def test_pure_chinese_heading(self):
        assert parse_heading("冲锋阶段") == ("冲锋阶段", None)

    def test_inline_model_code_not_english_name(self):
        # 型号码在中文名里、真正英文名在结尾
        assert parse_heading("XV104暴风谍影战斗服 RIPTIDE BATTLESUITS")[1] == (
            "RIPTIDE BATTLESUITS")

    def test_short_english_tail_ignored(self):
        # 结尾孤立大写字母不算英文名（长度<3）
        zh, en = parse_heading("战术目标 A")
        assert en is None

    def test_duplicated_model_code_prefix(self):
        # 型号码同时出现在中文名尾和英文名头：'虎鲨AX-1-0 AX-1-0 TIGER SHARK'
        # 重复的首 token 应归中文侧，英文侧与 canonical 'AX-1-0 Tiger Shark' 对齐
        assert parse_heading("虎鲨AX-1-0 AX-1-0 TIGER SHARK") == (
            "虎鲨AX-1-0", "AX-1-0 TIGER SHARK")

    def test_mixed_case_english_tail(self):
        # 混合大小写英文尾（含弯撇号）：'夏司’欧 R’ALAI Shas’o R’alai'
        # 应切出 en='Shas’o R’alai'，与 canonical 'Shas’o R’alai' 对齐
        assert parse_heading("夏司’欧 R’ALAI Shas’o R’alai") == (
            "夏司’欧 R’ALAI", "Shas’o R’alai")

    def test_pure_mixed_case_english_heading_unchanged(self):
        # 无中文的混合大小写标题保持旧行为（整体归 zh 侧），不误切
        assert parse_heading("Champions of Faith") == (
            "Champions of Faith", None)


class TestExtractBook:
    def _make_book(self, tmp_path: Path) -> Path:
        book = tmp_path / "测试书"
        book.mkdir()
        _write(book / "page_001.md",
               "## 火战士队 FIRE WARRIORS\n| M | T |\n### 远程武器\n...")
        # 续页：CONT 标记 → 页码并入前一实体
        _write(book / "page_002.md",
               "<!--CONT-->\n### 技能\n...")
        # 解说标题 → 并入同名实体，不新建
        _write(book / "page_003.md",
               "## 火战士队 FIRE WARRIORS 能力详解\n...\n## 冷言 COLDSTAR\n...")
        # meta 文件不应干扰扫描
        _write(book / "page_001.meta.json", "{}")
        return book

    def test_extracts_and_merges(self, tmp_path):
        cands = extract_book(self._make_book(tmp_path))
        assert [c.name_zh for c in cands] == ["火战士队", "冷言"]
        fw = cands[0]
        assert fw.name_en == "FIRE WARRIORS"
        assert fw.pages == [1, 2, 3]      # 首页 + CONT续页 + 详解页
        assert cands[1].pages == [3]

    def test_cont_page_starting_with_new_heading_not_merged(self, tmp_path):
        # CONT 标记后第一条实际内容就是新 ## 标题 → 该页不是前一实体的续页
        book = tmp_path / "c"
        book.mkdir()
        _write(book / "page_001.md",
               "## 火战士队 FIRE WARRIORS\n| M | T |\n...")
        _write(book / "page_002.md",
               "<!--CONT-->\n\n## 迅捷突袭 RAPID ASSAULT\n...")
        cands = extract_book(book)
        assert [c.name_zh for c in cands] == ["火战士队", "迅捷突袭"]
        assert cands[0].pages == [1]      # 页2不并入前一实体
        assert cands[1].pages == [2]

    def test_pure_noise_heading_skipped(self, tmp_path):
        book = tmp_path / "b"
        book.mkdir()
        _write(book / "page_001.md", "## 能力详解\n...")
        assert extract_book(book) == []

    def test_orphan_cont_page_warns(self, tmp_path, capsys):
        # L：无前置实体的真续页（CONT 标记 + 无 ## 标题）不再静默丢弃，打警告
        book = tmp_path / "孤书"
        book.mkdir()
        _write(book / "page_002.md", "<!--CONT-->\n续页内容但没有归属实体\n")
        assert extract_book(book) == []
        out = capsys.readouterr().out
        assert "无归属" in out and "孤书" in out and "2" in out

    def test_orphan_cont_page_with_new_heading_no_warning(self, tmp_path, capsys):
        # CONT 后第一条内容就是新 ## 标题 → 内容并未丢失，不打警告
        book = tmp_path / "孤书2"
        book.mkdir()
        _write(book / "page_002.md", "<!--CONT-->\n\n## 新单位 NEW UNIT\n...")
        cands = extract_book(book)
        assert [c.name_zh for c in cands] == ["新单位"]
        assert "无归属" not in capsys.readouterr().out

    def test_extract_entities_walks_all_books(self, tmp_path):
        b1 = tmp_path / "书一"; b1.mkdir()
        _write(b1 / "page_001.md", "## 单位甲 UNIT ALPHA\n...")
        b2 = tmp_path / "书二"; b2.mkdir()
        _write(b2 / "page_001.md", "## 单位乙 UNIT BETA\n...")
        cands = extract_entities(tmp_path)
        assert {(c.book, c.name_zh) for c in cands} == {
            ("书一", "单位甲"), ("书二", "单位乙")}
