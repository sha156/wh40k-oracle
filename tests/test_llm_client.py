# tests/test_llm_client.py
"""agent/llm_client.py：真实 LLMClient 的 JSON 协议解析与 fail-closed 行为。

不产生任何真实 API 调用——注入 FakeOpenAIClient 替换 .chat.completions.create。
"""
from types import SimpleNamespace

import pytest

from agent.llm_client import (
    OpenAICompatLLMClient,
    _extract_json_object,
    _render_catalog,
)
from agent.loop import AgentLoop, DEFAULT_INTENT


class FakeOpenAIClient:
    """按预设脚本依次返回 content 的假 OpenAI 客户端。

    单个脚本项可以是字符串（正常返回）或 Exception 实例（抛出，模拟 API 故障）。
    暴露 .chat.completions.create，签名与真实 SDK 一致。
    """

    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.calls = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        out = self._outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        message = SimpleNamespace(content=out)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _client(outputs, **kw):
    return OpenAICompatLLMClient(client=FakeOpenAIClient(outputs), **kw)


# ── _extract_json_object 纯函数 ────────────────────────────────────

class TestExtractJsonObject:
    def test_parses_plain_json(self):
        obj = _extract_json_object('{"type": "final", "content": "答案"}')
        assert obj["type"] == "final"

    def test_strips_markdown_fence(self):
        raw = '```json\n{"type": "tool_call", "tool": "rag_search", "args": {"query": "x"}}\n```'
        obj = _extract_json_object(raw)
        assert obj["tool"] == "rag_search"

    def test_extracts_object_amid_noise(self):
        raw = '好的，我的决定是：{"type": "final", "content": "hi"} 以上。'
        assert _extract_json_object(raw)["content"] == "hi"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _extract_json_object("   ")

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            _extract_json_object("这里根本没有 JSON")

    def test_missing_type_field_raises(self):
        with pytest.raises(ValueError):
            _extract_json_object('{"content": "缺 type"}')


# ── _render_catalog 带参数提示 ─────────────────────────────────────

def test_render_catalog_includes_arg_hints():
    specs = [{"name": "get_entity", "description": "读实体页"}]
    catalog = _render_catalog(specs)
    assert "get_entity" in catalog
    assert "name_or_id" in catalog  # arg 提示表命中


# ── classify_intent ───────────────────────────────────────────────

class TestClassifyIntent:
    def test_returns_recognized_intent(self):
        llm = _client(["查"])
        assert llm.classify_intent("影阳指挥官的 T 是多少？") == "查"

    def test_intent_embedded_in_noise_still_extracted(self):
        llm = _client(["意图是：算"])
        assert llm.classify_intent("这套军表多少分？") == "算"

    def test_unrecognized_output_falls_back_to_default(self):
        llm = _client(["火星"])
        assert llm.classify_intent("随便问") == DEFAULT_INTENT

    def test_api_exception_falls_back_to_default(self):
        llm = _client([RuntimeError("api down")])
        assert llm.classify_intent("问题") == DEFAULT_INTENT


# ── next_step ──────────────────────────────────────────────────────

class TestNextStep:
    def test_parses_tool_call_step(self):
        llm = _client(['{"type": "tool_call", "tool": "search_wiki", "args": {"query": "先锋战士"}}'])
        step = llm.next_step([{"role": "user", "content": "先锋战士"}], [])
        assert step["type"] == "tool_call"
        assert step["tool"] == "search_wiki"
        assert step["args"]["query"] == "先锋战士"

    def test_parses_final_step_with_sources(self):
        llm = _client(['{"type": "final", "content": "答案", "sources": [{"book": "钛帝国", "page": 17}]}'])
        step = llm.next_step([{"role": "user", "content": "x"}], [])
        assert step["type"] == "final"
        assert step["sources"][0]["page"] == 17

    def test_serializes_dict_tool_result_into_prompt(self):
        fake = FakeOpenAIClient(['{"type": "final", "content": "done"}'])
        llm = OpenAICompatLLMClient(client=fake)
        messages = [
            {"role": "user", "content": "问题"},
            {"role": "tool", "name": "get_entity", "content": {"found": True, "page": {"x": 1}}},
        ]
        llm.next_step(messages, [])
        sent = fake.calls[0]["messages"]
        # 工具 dict 结果被序列化进某条 user 消息
        assert any("get_entity" in m["content"] and "found" in m["content"] for m in sent)

    def test_serializes_nonjson_dataclass_tool_result(self):
        """工具返回内嵌 WikiPage 之类非 JSON 对象时，用 to_markdown/asdict 兜底，
        绝不因序列化崩溃（回归：Object of type WikiPage is not JSON serializable）。"""
        import dataclasses

        @dataclasses.dataclass
        class _FakePage:
            def to_markdown(self):
                return "## 影阳指挥官\n| M | T |\n| 10 | 4 |"

        fake = FakeOpenAIClient(['{"type": "final", "content": "ok"}'])
        llm = OpenAICompatLLMClient(client=fake)
        messages = [
            {"role": "user", "content": "影阳指挥官"},
            {"role": "tool", "name": "get_entity", "content": {"found": True, "page": _FakePage()}},
        ]
        llm.next_step(messages, [])  # 不抛异常即通过
        sent = fake.calls[0]["messages"]
        assert any("影阳指挥官" in m["content"] for m in sent)

    def test_unparseable_output_raises(self):
        llm = _client(["模型今天不听话，什么都没输出正确"])
        with pytest.raises(ValueError):
            llm.next_step([{"role": "user", "content": "x"}], [])

    def test_falls_back_when_response_format_unsupported(self):
        # 第一次带 response_format 抛错，第二次普通模式成功
        fake = FakeOpenAIClient([
            RuntimeError("response_format not supported"),
            '{"type": "final", "content": "退回普通模式也能答"}',
        ])
        llm = OpenAICompatLLMClient(client=fake)
        step = llm.next_step([{"role": "user", "content": "x"}], [])
        assert step["content"] == "退回普通模式也能答"


# ── 与 AgentLoop 端到端（用假 client 驱动真实 loop）──────────────────

class TestEndToEndWithAgentLoop:
    def test_tool_call_then_final_drives_loop(self):
        llm = _client([
            "查",  # classify_intent
            '{"type": "tool_call", "tool": "get_entity", "args": {"name_or_id": "影阳指挥官"}}',
            '{"type": "final", "content": "影阳指挥官已找到 [《钛帝国》第17页]。", "sources": []}',
        ])
        tools = {"get_entity": lambda name_or_id: {"found": True, "page": {"name_zh": name_or_id}}}
        loop = AgentLoop(llm=llm, tools=tools)

        result = loop.run("影阳指挥官是什么？")

        assert result.intent == "查"
        assert result.degraded is False
        assert result.tool_calls == ["get_entity"]
        assert "影阳指挥官" in result.answer

    def test_bad_json_midloop_degrades_to_rag_search(self):
        llm = _client([
            "查",           # classify_intent
            "彻底不是 JSON",  # next_step 抛 ValueError → loop.run 降级
        ])
        tools = {
            "rag_search": lambda query: {
                "found": True,
                "passages": [{"text": "兜底段落", "book": "测试书", "page": 3}],
            }
        }
        loop = AgentLoop(llm=llm, tools=tools)

        result = loop.run("触发解析失败")

        assert result.degraded is True
        assert "rag_search" in result.tool_calls
        assert "测试书" in result.answer


def test_unknown_provider_without_overrides_raises():
    with pytest.raises(ValueError):
        OpenAICompatLLMClient(provider="不存在的供应商", client=object())
