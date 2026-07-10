# tests/test_qa_bench.py
"""scripts/qa_bench.py：judge 输出解析 + 两段式机械判分纯函数。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from qa_bench import (  # noqa: E402
    asked_fields,
    classify_stage,
    decide_mechanical,
    judge_gold_mechanical,
    parse_gold_fields,
    parse_verdict,
    summarize_layered,
    _stat_token,
)


class TestParseVerdict:
    def test_emoji_marks_win(self):
        assert parse_verdict("✅\n回答正确") == "✅"
        assert parse_verdict("❌ 答非所问") == "❌"
        assert parse_verdict("⚠️ 信息不全") == "⚠️"

    def test_emoji_takes_priority_over_keywords(self):
        # 同时含 ❌ 和「正确」时，emoji 标记优先
        assert parse_verdict("❌ 数值不正确") == "❌"

    def test_keyword_fallback_when_no_emoji(self):
        assert parse_verdict("回答正确且完整") == "✅"
        assert parse_verdict("这里数值错误，属于编造") == "❌"

    def test_defaults_to_partial(self):
        assert parse_verdict("模棱两可的评语") == "⚠️"
        assert parse_verdict("") == "⚠️"


class TestClassifyStage:
    """把 (检索判, 生成判) 归到瓶颈桶——定位『伤害死在哪一步』。"""

    def test_generation_correct_is_ok_regardless(self):
        assert classify_stage("✅", "✅") == "ok"
        # 生成对了就算成功，即便检索判偏严
        assert classify_stage("⚠️", "✅") == "ok"

    def test_retrieval_miss_blamed_on_retrieval(self):
        # 没检索到 → 答不好归检索，不冤枉生成层
        assert classify_stage("❌", "❌") == "retrieval_miss"
        assert classify_stage("❌", "⚠️") == "retrieval_miss"

    def test_found_but_botched_is_generation_error(self):
        # 检索到了却没答对 → 生成层的锅
        assert classify_stage("✅", "❌") == "generation_error"
        assert classify_stage("✅", "⚠️") == "generation_error"

    def test_partial_retrieval_bucket(self):
        assert classify_stage("⚠️", "❌") == "partial_retrieval"
        assert classify_stage("⚠️", "⚠️") == "partial_retrieval"


class TestSummarizeLayered:
    def test_two_column_counts_and_conditional(self):
        results = [
            {"retrieval_verdict": "✅", "generation_verdict": "✅"},  # ok
            {"retrieval_verdict": "✅", "generation_verdict": "❌"},  # gen error
            {"retrieval_verdict": "❌", "generation_verdict": "❌"},  # retr miss
            {"retrieval_verdict": "⚠️", "generation_verdict": "⚠️"},  # partial
        ]
        s = summarize_layered(results)
        assert s["total"] == 4
        # 检索层：1 hit / 1 partial / ... 实际 ✅=2 (前两条都检索✅)
        assert s["retrieval"]["hit"] == 2
        assert s["retrieval"]["miss"] == 1
        assert s["retrieval_accuracy"] == 50.0  # 2/4
        # 生成层：✅=1
        assert s["generation_accuracy"] == 25.0  # 1/4
        # 条件生成率：检索✅的 2 条里生成✅ 1 条 → 50%
        assert s["conditional_gen_accuracy"] == 50.0
        # 瓶颈桶
        assert s["stages"]["ok"] == 1
        assert s["stages"]["generation_error"] == 1
        assert s["stages"]["retrieval_miss"] == 1
        assert s["stages"]["partial_retrieval"] == 1

    def test_conditional_is_none_when_no_retrieval_hit(self):
        results = [{"retrieval_verdict": "❌", "generation_verdict": "❌"}]
        s = summarize_layered(results)
        assert s["conditional_gen_accuracy"] is None


class TestStatToken:
    """属性值归一化：去移动单位/多余文字，折叠连续 +，抽出可比对 token。"""

    def test_strips_inch_markers(self):
        assert _stat_token('10"') == "10"
        assert _stat_token("10寸") == "10"
        assert _stat_token("14寸") == "14"

    def test_keeps_save_plus_and_collapses_double_plus(self):
        assert _stat_token("3+") == "3+"
        assert _stat_token("5++") == "5+"  # 特殊保护双加号与单加号等价

    def test_keeps_negative_ap(self):
        assert _stat_token("-4") == "-4"
        assert _stat_token("0") == "0"

    def test_dice_notation(self):
        assert _stat_token("D6") == "d6"
        assert _stat_token("D6+1") == "d6+1"
        assert _stat_token("2D6") == "2d6"

    def test_extracts_token_from_embedded_prose(self):
        # gold 里数值后跟解释文字，仍抽出首个规范 token
        assert _stat_token("2+（10版中WS体现在近战武器上") == "2+"
        assert _stat_token("1。") == "1"

    def test_none_and_no_digit(self):
        assert _stat_token(None) is None
        assert _stat_token("无") == "无"

    def test_bare_dash_equals_none(self):
        # 裸破折号（各种 dash）= 该项无，与「无」等价（#29 特殊保护：- vs 无）
        assert _stat_token("-") == "无"
        assert _stat_token("—") == "无"
        assert _stat_token("–") == "无"
        # 有数字的负值不受影响
        assert _stat_token("-4") == "-4"


class TestParseGoldFields:
    def test_single_entity_latin_fields(self):
        assert parse_gold_fields('影阳指挥官：M=10" T=4') == {"M": '10"', "T": "4"}

    def test_multichar_keys_not_split(self):
        got = parse_gold_fields("幽冥骑士：T=12 SV=2+ W=18")
        assert got == {"T": "12", "SV": "2+", "W": "18"}

    def test_invuln_special_save(self):
        got = parse_gold_fields("燃雨战斗服：特殊保护=5++ W=15")
        assert got == {"INV": "5++", "W": "15"}

    def test_weapon_fields(self):
        assert parse_gold_fields("High-energy fusion blaster S=10 AP=-4 D=D6") == {
            "S": "10", "AP": "-4", "D": "D6"}

    def test_multi_weapon_returns_none(self):
        # 同字段重复出现 → 多武器/多模型，机械对齐不了，交 LLM
        assert parse_gold_fields(
            "Big choppa S=7 AP=-1 D=2；Choppa S=4 AP=-1 D=1") is None

    def test_empty_gold(self):
        assert parse_gold_fields("") is None
        assert parse_gold_fields("纯文字没有数值") is None


class TestAskedFields:
    def test_latin_codes(self):
        assert asked_fields("影阳指挥官的M和T各是多少？") == {"M", "T"}

    def test_weapon_codes(self):
        assert asked_fields("高能融合炮的S、AP、D各是多少？") == {"S", "AP", "D"}

    def test_special_save_word(self):
        assert asked_fields("终结者小队的SV和特殊保护是多少？") == {"SV", "INV"}

    def test_chinese_synonyms(self):
        got = asked_fields("这个单位的韧性和生命值是多少？")
        assert "T" in got and "W" in got


class TestDecideMechanical:
    """纯函数：按 token 逐字段比对给 ✅/⚠️/❌。"""

    def test_all_correct(self):
        v, _ = decide_mechanical({"M": '10"', "T": "4"}, ["M", "T"],
                                 {"M": "10寸", "T": "4"})
        assert v == "✅"

    def test_extra_field_in_answer_not_penalized(self):
        # #81：问 M/SV，答对了还多报没问的 T=5 —— 不扣分
        v, _ = decide_mechanical({"M": '5"', "SV": "4+"}, ["M", "SV"],
                                 {"M": "5寸", "SV": "4+"})
        assert v == "✅"

    def test_missing_field_is_partial_not_wrong(self):
        v, _ = decide_mechanical({"M": '10"', "T": "4"}, ["M", "T"],
                                 {"M": "10寸", "T": None})
        assert v == "⚠️"

    def test_contradiction_is_wrong(self):
        # #30：gold W=16，答 W=12 → ❌
        v, reason = decide_mechanical({"W": "16"}, ["W"], {"W": "12"})
        assert v == "❌"
        assert "16" in reason

    def test_all_missing_is_wrong(self):
        v, _ = decide_mechanical({"W": "16"}, ["W"], {"W": None})
        assert v == "❌"

    def test_invuln_double_plus_matches_single(self):
        v, _ = decide_mechanical({"INV": "5++"}, ["INV"], {"INV": "5+"})
        assert v == "✅"

    def test_invuln_none_dash_matches_wu(self):
        # #29：gold 特殊保护「无」，回答给「-」→ 两者都表示无特殊保护，应 ✅
        v, _ = decide_mechanical({"INV": "无"}, ["INV"], {"INV": "-"})
        assert v == "✅"

    # ── 多值抽取（答案覆盖多子单位/多武器，任一匹配 gold 即命中）──────────
    def test_multi_value_any_match_passes(self):
        # #95 噪音战士：答案先列爆音炮(S10/AP-2)又列音波枪(S5/AP-1)；gold 要 S5/AP-1
        v, _ = decide_mechanical(
            {"S": "5", "AP": "-1"}, ["S", "AP"],
            {"S": ["10", "5"], "AP": ["-2", "-1"]},
        )
        assert v == "✅"

    def test_multi_value_none_match_is_wrong(self):
        # 多值但没有一个对上标准 → ❌（不是靠罗列蒙混）
        v, reason = decide_mechanical({"S": "5"}, ["S"], {"S": ["10", "8"]})
        assert v == "❌"
        assert "5" in reason

    def test_multi_value_partial_is_partial(self):
        # #62 型：M 多子单位任一命中，T 漏答 → ⚠️（漏项不判❌）
        v, _ = decide_mechanical(
            {"M": '6"', "T": "3"}, ["M", "T"],
            {"M": ["6", "6"], "T": []},
        )
        assert v == "⚠️"

    def test_scalar_backward_compatible(self):
        # 旧契约：单值标量仍照常比对
        v, _ = decide_mechanical({"M": '10"'}, ["M"], {"M": "10寸"})
        assert v == "✅"

    # ── H18 记录匹配：多值字段按下标对齐成记录，必须同一记录全部命中 ────────
    def test_cross_field_patchwork_not_pass(self):
        # H18 回归（审查实测用例）：答案两把武器 (S5,AP-2)/(S10,AP-1)，
        # gold 要求 (S5,AP-1)——S、AP 各自都出现过标准值，但没有一把武器
        # 同时满足，绝不能 ✅（旧逻辑各字段独立"任一命中"误判 ✅）。
        v, reason = decide_mechanical(
            {"S": "5", "AP": "-1"}, ["S", "AP"],
            {"S": ["5", "10"], "AP": ["-2", "-1"]},
        )
        assert v == "⚠️"
        assert "拼凑" in reason

    def test_record_aligned_match_passes(self):
        # 对照组：同样两把武器但第二把 (5,-1) 与 gold 对齐命中 → ✅
        v, _ = decide_mechanical(
            {"S": "5", "AP": "-1"}, ["S", "AP"],
            {"S": ["10", "5"], "AP": ["-2", "-1"]},
        )
        assert v == "✅"

    def test_scalar_field_applies_to_all_records(self):
        # 标量字段视为对所有记录生效（下标越界取标量值的语义）
        v, _ = decide_mechanical(
            {"S": "5", "AP": "-1"}, ["S", "AP"],
            {"S": "5", "AP": ["-2", "-1"]},
        )
        assert v == "✅"

    def test_null_placeholder_keeps_alignment(self):
        # 抽取 prompt 约定缺失字段用 null 占位：第一把武器缺 AP，
        # 第二把 (5,-1) 仍在同一下标对齐命中 → ✅
        v, _ = decide_mechanical(
            {"S": "5", "AP": "-1"}, ["S", "AP"],
            {"S": ["10", "5"], "AP": [None, "-1"]},
        )
        assert v == "✅"

    def test_list_shorter_than_records_treated_missing(self):
        # AP 只抽到 1 个值（对齐在第 0 把武器），S 的标准值在第 1 把——
        # 无任何记录同时命中 → 不给 ✅
        v, _ = decide_mechanical(
            {"S": "5", "AP": "-1"}, ["S", "AP"],
            {"S": ["10", "5"], "AP": ["-1"]},
        )
        assert v == "⚠️"

    def test_multi_value_end_to_end_extraction(self):
        # 假 client 返回数组形式的抽取 JSON，机械判分应任一匹配即 ✅
        client = _FakeExtractClient({"S": ["10", "5"], "AP": ["-2", "-1"]})
        v, _ = judge_gold_mechanical(
            "m", client, "噪音战士的S和AP是多少？",
            "Sonic blaster S=5 AP=-1 D=2", "爆音炮S10 AP-2；音波枪S5 AP-1",
        )
        assert v == "✅"


class _FakeExtractClient:
    """假 client：extract_answer_fields 调用它时返回预设的抽取 JSON。"""

    def __init__(self, extracted):
        self._json = json.dumps(extracted, ensure_ascii=False)
        self.chat = self  # 让 client.chat.completions.create 可达
        self.completions = self

    def create(self, **kwargs):
        payload = self._json

        class _Msg:
            content = payload

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        return _Resp()


class TestJudgeGoldMechanicalEndToEnd:
    """机械判分编排（gold 解析 + 假抽取 + 决策），不触真实 API。"""

    def test_multi_weapon_gold_returns_none_for_llm_fallback(self):
        client = _FakeExtractClient({})
        got = judge_gold_mechanical(
            "m", client, "兽人小子的格斗武器S和AP是多少？",
            "Big choppa S=7 AP=-1 D=2；Choppa S=4 AP=-1 D=1", "答案",
        )
        assert got is None  # 交回 LLM judge

    def test_correct_stat_answer_passes(self):
        client = _FakeExtractClient({"M": "10寸", "T": "4"})
        v, _ = judge_gold_mechanical(
            "m", client, "影阳指挥官的M和T各是多少？",
            '影阳指挥官：M=10" T=4', "M为10寸，T为4。",
        )
        assert v == "✅"

    def test_wrong_stat_answer_fails(self):
        client = _FakeExtractClient({"W": "12"})
        v, _ = judge_gold_mechanical(
            "m", client, "莫塔里安的W是多少？", "莫塔里安：W=16", "W为12",
        )
        assert v == "❌"

    def test_cross_field_patchwork_end_to_end_not_pass(self):
        # H18 端到端回归：抽取器返回两把武器 (S5,AP-2)/(S10,AP-1)，
        # gold (S5,AP-1)——旧逻辑判 ✅，新记录匹配必须拦下。
        client = _FakeExtractClient({"S": ["5", "10"], "AP": ["-2", "-1"]})
        v, _ = judge_gold_mechanical(
            "m", client, "这把武器的S和AP是多少？",
            "Some blaster S=5 AP=-1 D=2", "武器A S5 AP-2；武器B S10 AP-1",
        )
        assert v != "✅"
