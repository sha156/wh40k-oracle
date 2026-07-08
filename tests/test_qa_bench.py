# tests/test_qa_bench.py
"""scripts/qa_bench.py：judge 输出 → ✅/⚠️/❌ 解析（唯一值得单测的纯函数）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from qa_bench import (  # noqa: E402
    classify_stage,
    parse_verdict,
    summarize_layered,
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
