# tests/test_agent_loop.py
"""agent/loop.py：意图分类 → 工具调用循环 → 答案合成；异常/空结果降级 rag_search。

LLM 全部走 mock（FakeLLM 实现 LLMClient Protocol），不产生真实 API 调用。
"""
from pathlib import Path

from agent.context import SessionContext
from agent.loop import AgentLoop, AgentResult


class ScriptedLLM:
    """按预设脚本依次返回 next_step 结果的假 LLM；classify_intent 固定返回给定意图。"""

    def __init__(self, intent, steps):
        self._intent = intent
        self._steps = list(steps)
        self.next_step_calls = []

    def classify_intent(self, user_input):
        return self._intent

    def next_step(self, messages, tool_specs):
        self.next_step_calls.append(messages)
        return self._steps.pop(0)


class RaisingClassifyLLM:
    """分类抛异常 → 回落 DEFAULT_INTENT("查")。next_step 先走一次 rag_search 再 final，
    以便在零工具门控下仍能正常产出答案（本测试关注分类容错，不测门控）。"""

    def __init__(self):
        self._steps = [
            {"type": "tool_call", "tool": "rag_search", "args": {"query": "随便"}},
            {"type": "final", "content": "闲聊兜底回答"},
        ]

    def classify_intent(self, user_input):
        raise RuntimeError("模拟分类模型挂了")

    def next_step(self, messages, tool_specs):
        return self._steps.pop(0)


def _fake_tools(**overrides):
    tools = {
        "search_wiki": lambda query: {"found": False, "page": None, "results": []},
        "get_entity": lambda name_or_id: {"found": False, "page": None},
        "rag_search": lambda query: {
            "found": True,
            "passages": [{"text": "示例检索段落", "book": "测试书", "page": 5}],
        },
    }
    tools.update(overrides)
    return tools


class TestQueryFlowHappyPath:
    """stop condition②：查询类问题走通 意图分类→工具调用→答案合成。"""

    def test_classifies_intent_calls_tool_then_synthesizes_final_answer(self):
        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "get_entity", "args": {"name_or_id": "影阳指挥官"}},
            {"type": "final", "content": "影阳指挥官是钛帝国指挥官单位（引用：钛帝国十版CODEX 第X页）。",
             "sources": [{"book": "钛帝国十版CODEX", "page": 1}]},
        ])
        tools = _fake_tools(get_entity=lambda name_or_id: {
            "found": True,
            "page": {"fm": {"name_zh": "影阳指挥官", "name_en": "Commander Shadowsun"}},
        })
        loop = AgentLoop(llm=llm, tools=tools)

        result = loop.run("影阳指挥官是什么单位？")

        assert isinstance(result, AgentResult)
        assert result.intent == "查"
        assert result.tool_calls == ["get_entity"]
        assert result.degraded is False
        assert "影阳指挥官" in result.answer
        assert result.sources[0]["book"] == "钛帝国十版CODEX"

    def test_end_to_end_against_real_wiki_get_entity_tool(self):
        """用真实 agent.tools.get_entity（读真实 wiki/）验证查询流程闭环。"""
        from agent.tools import TOOLS as REAL_TOOLS

        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "get_entity", "args": {"name_or_id": "影阳指挥官"}},
            {"type": "final", "content": "已找到影阳指挥官实体页。"},
        ])
        loop = AgentLoop(llm=llm, tools=REAL_TOOLS)

        result = loop.run("影阳指挥官是什么单位？")

        assert result.degraded is False
        assert result.tool_calls == ["get_entity"]
        assert result.answer == "已找到影阳指挥官实体页。"

    def test_session_context_records_conversation_turns(self):
        # 用「闲聊」意图：它豁免零工具门控，单步 final 即可被接受，
        # 让本测试专注于会话记录本身而非门控行为。
        llm = ScriptedLLM("闲聊", steps=[{"type": "final", "content": "答案"}])
        loop = AgentLoop(llm=llm, tools=_fake_tools())
        session = SessionContext()

        loop.run("一个问题", session=session)

        assert session.history == [
            {"role": "user", "content": "一个问题"},
            {"role": "assistant", "content": "答案"},
        ]


class TestDegradesToRagSearch:
    """stop condition③：空结果/异常静默降级 rag_search。"""

    def test_empty_tool_result_triggers_rag_search_fallback(self):
        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "search_wiki", "args": {"query": "不存在的东西"}},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("查一个不存在的东西")

        assert result.degraded is True
        assert result.tool_calls == ["search_wiki", "rag_search"]
        assert "测试书" in result.answer

    def test_tool_exception_triggers_rag_search_fallback(self):
        def boom(query):
            raise RuntimeError("工具炸了")

        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "search_wiki", "args": {"query": "触发异常"}},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools(search_wiki=boom))

        result = loop.run("触发异常的问题")

        assert result.degraded is True
        assert "rag_search" in result.tool_calls

    def test_max_steps_exceeded_triggers_fallback(self):
        steps = [
            {"type": "tool_call", "tool": "rag_search", "args": {"query": "循环"}}
            for _ in range(6)
        ]
        llm = ScriptedLLM("查", steps=steps)
        loop = AgentLoop(llm=llm, tools=_fake_tools(), max_steps=6)

        result = loop.run("会无限循环调用工具的问题")

        assert result.degraded is True
        assert result.answer

    def test_rag_search_itself_returning_empty_does_not_loop_forever(self):
        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "rag_search", "args": {"query": "都没有"}},
            {"type": "final", "content": "兜底检索也没找到相关内容，无法确认。"},
        ])
        tools = _fake_tools(rag_search=lambda query: {"found": False, "passages": []})
        loop = AgentLoop(llm=llm, tools=tools, max_steps=6)

        result = loop.run("循环兜底也找不到")

        # rag_search 结果直接作为 messages 推进循环，未触发二次降级（rag_search 不在 _EMPTY_CHECKS 里）
        assert result.degraded is False
        assert result.tool_calls == ["rag_search"]
        assert result.answer == "兜底检索也没找到相关内容，无法确认。"

    def test_unmodeled_tool_call_does_not_trigger_fallback(self):
        """未建模工具（如 simulate_combat）返回的"未建模"占位不应触发 rag_search 降级——
        它本身就是诚实答案的一部分，交给 LLM 合成最终回答。"""
        llm = ScriptedLLM("谋", steps=[
            {"type": "tool_call", "tool": "simulate_combat",
             "args": {"attacker": "a", "defender": "b"}},
            {"type": "final", "content": "模拟功能尚未建模，计划于 P4 提供，暂无法给出数字结论。"},
        ])
        from agent.tools import simulate_combat
        loop = AgentLoop(llm=llm, tools=_fake_tools(simulate_combat=simulate_combat))

        result = loop.run("A打B谁赢？")

        assert result.degraded is False
        assert result.tool_calls == ["simulate_combat"]
        assert "未建模" in result.answer


class TestZeroToolAnswerGate:
    """P0-1 零工具直答门控：查/判/算 类问题不许一次工具都不调就凭记忆作答。"""

    def test_zero_tool_final_is_nudged_then_degrades_to_classic(self):
        # 模型两次都想零工具直答 → 一次纠偏无效 → 降级 classic 兜底。
        llm = ScriptedLLM("查", steps=[
            {"type": "final", "content": "莫塔里安的W为12。", "sources": [{"book": "核心书", "page": 189}]},
            {"type": "final", "content": "我还是坚持W为12。"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("莫塔里安的W是多少？")

        assert result.degraded is True
        assert result.tool_calls == ["rag_search"]  # 门控前零工具，降级后补 rag_search
        assert "测试书" in result.answer  # 来自 classic 兜底段落，而非编造的 W12
        # 纠偏消息确实注入过（第二次 next_step 能看到）
        assert any("先输出一个 tool_call" in str(m) for m in llm.next_step_calls[-1])

    def test_nudge_makes_model_use_tool_then_answer_is_grounded(self):
        # 纠偏后模型改走 get_datasheet 并成功 → 正常作答，不降级。
        llm = ScriptedLLM("查", steps=[
            {"type": "final", "content": "凭记忆：W12"},
            {"type": "tool_call", "tool": "get_datasheet", "args": {"name_or_id": "莫塔里安"}},
            {"type": "final", "content": "莫塔里安 W16。", "sources": [{"book": "钛帝国", "page": 1}]},
        ])
        tools = _fake_tools(get_datasheet=lambda name_or_id: {"found": True, "W": 16})
        loop = AgentLoop(llm=llm, tools=tools)

        result = loop.run("莫塔里安的W是多少？")

        assert result.degraded is False
        assert result.tool_calls == ["get_datasheet"]
        assert "W16" in result.answer

    def test_judge_intent_zero_tool_is_also_gated(self):
        llm = ScriptedLLM("判", steps=[
            {"type": "final", "content": "凭记忆判定：可以先手反击。"},
            {"type": "final", "content": "还是可以。"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("冲锋后对方能否先手反击？")

        assert result.degraded is True

    def test_chitchat_intent_allows_zero_tool_final(self):
        llm = ScriptedLLM("闲聊", steps=[{"type": "final", "content": "你好呀，随便聊。"}])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("在吗")

        assert result.degraded is False
        assert result.tool_calls == []
        assert result.answer == "你好呀，随便聊。"

    def test_planning_intent_zero_tool_final_not_gated(self):
        # 谋类的诚实「未建模」回答无需检索，不应被门控降级。
        llm = ScriptedLLM("谋", steps=[
            {"type": "final", "content": "模拟功能尚未建模（P4），暂无法给出数字结论。"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("10个火战士打5个终结者能杀几个？")

        assert result.degraded is False
        assert "未建模" in result.answer


class TestIntentClassificationFailsClosed:
    def test_classify_exception_falls_back_to_default_intent_and_still_answers(self):
        loop = AgentLoop(llm=RaisingClassifyLLM(), tools=_fake_tools())

        result = loop.run("随便问点什么")

        assert result.intent == "查"  # DEFAULT_INTENT
        assert result.answer == "闲聊兜底回答"

    def test_unknown_intent_label_falls_back_to_default(self):
        # 归一化到「查」后受零工具门控约束，故先走一次 rag_search 再 final。
        llm = ScriptedLLM("瞎猜的意图", steps=[
            {"type": "tool_call", "tool": "rag_search", "args": {"query": "x"}},
            {"type": "final", "content": "答案"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("问题")

        assert result.intent == "查"


class TestUnknownToolName:
    def test_unknown_tool_call_is_reported_back_and_loop_continues(self):
        # 用「闲聊」意图避开零工具门控，专注验证未知工具被回报后循环继续。
        llm = ScriptedLLM("闲聊", steps=[
            {"type": "tool_call", "tool": "does_not_exist", "args": {}},
            {"type": "final", "content": "尽管工具名不认识，仍然给出了回答"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("问题")

        assert result.degraded is False
        assert result.tool_calls == []  # 未知工具不计入 tool_calls
        assert result.answer == "尽管工具名不认识，仍然给出了回答"
