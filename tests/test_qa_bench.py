# tests/test_qa_bench.py
"""scripts/qa_bench.py：judge 输出 → ✅/⚠️/❌ 解析（唯一值得单测的纯函数）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from qa_bench import parse_verdict  # noqa: E402


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
