"""标题解析与实体抽取测试。样本取自 data_refined 实测格式。"""
from wiki_compile.extract import parse_heading


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
