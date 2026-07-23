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

    def test_tool_exception_twice_consecutively_triggers_rag_search_fallback(self):
        # M#6 新语义：首次异常→错误写回 messages 给模型重试机会；
        # 同一工具**连续第二次**异常才降级 classic（旧行为是首次异常即降级）。
        def boom(query):
            raise RuntimeError("工具炸了")

        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "search_wiki", "args": {"query": "触发异常"}},
            {"type": "tool_call", "tool": "search_wiki", "args": {"query": "再试还是炸"}},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools(search_wiki=boom))

        result = loop.run("触发异常的问题")

        assert result.degraded is True
        assert "rag_search" in result.tool_calls
        # 首次异常的错误信息确实写回了 messages（第二次 next_step 能看到）
        assert any("执行异常" in str(m) for m in llm.next_step_calls[-1])

    def test_tool_exception_once_then_fixed_args_succeeds(self):
        # M#6：首次异常后模型换参数重试成功 → 不降级，正常作答
        calls = {"n": 0}

        def flaky(query):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("坏参数炸了")
            return {"found": True, "page": {"name_zh": "找到了"}, "results": []}

        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "search_wiki", "args": {"query": "坏参数"}},
            {"type": "tool_call", "tool": "search_wiki", "args": {"query": "好参数"}},
            {"type": "final", "content": "换参数后查到了。"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools(search_wiki=flaky))

        result = loop.run("会先炸一次的问题")

        assert result.degraded is False
        assert result.tool_calls == ["search_wiki"]  # 失败的那次不计入
        assert result.answer == "换参数后查到了。"

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
        """未建模工具（如 judge_fight_order）返回的"未建模"占位不应触发 rag_search 降级——
        它本身就是诚实答案的一部分，交给 LLM 合成最终回答。"""
        llm = ScriptedLLM("判", steps=[
            {"type": "tool_call", "tool": "judge_fight_order", "args": {}},
            {"type": "final", "content": "战斗顺序判定尚未建模，计划于 P5 提供，暂无法给出裁定。"},
        ])
        from agent.tools import judge_fight_order
        loop = AgentLoop(llm=llm, tools=_fake_tools(judge_fight_order=judge_fight_order))

        result = loop.run("谁先打？")

        assert result.degraded is False
        assert result.tool_calls == ["judge_fight_order"]
        assert "未建模" in result.answer


class TestEmptyFinalContent:
    """M#5：final 空内容不算成功——先给一次重答机会，仍空则降级。"""

    def test_empty_final_nudged_then_real_answer(self):
        # 用「闲聊」意图避开零工具门控，专注验证空内容纠偏
        llm = ScriptedLLM("闲聊", steps=[
            {"type": "final", "content": "   "},
            {"type": "final", "content": "这次有真内容。"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("在吗")

        assert result.degraded is False
        assert result.answer == "这次有真内容。"
        # 纠偏消息确实注入过（第二次 next_step 能看到）
        assert any("空内容" in str(m) for m in llm.next_step_calls[-1])

    def test_empty_final_twice_degrades(self):
        llm = ScriptedLLM("闲聊", steps=[
            {"type": "final", "content": ""},
            {"type": "final", "content": None},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("在吗")

        assert result.degraded is True
        assert "rag_search" in result.tool_calls

    def test_empty_final_after_tool_call_also_gated(self):
        # 查过工具但 final 仍为空 → 同样先纠偏再放行真实答案
        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "rag_search", "args": {"query": "x"}},
            {"type": "final", "content": ""},
            {"type": "final", "content": "基于检索段落的回答。"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("问题")

        assert result.degraded is False
        assert result.answer == "基于检索段落的回答。"


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

    def test_scheme_intent_zero_tool_is_gated(self):
        # 谋类（模拟对战）自 P4-e 起 simulate_combat 已建模：零工具凭直觉估「谁能赢」
        # 应被门控——纠偏无效则降级 classic，而非放行编造的数字结论。
        llm = ScriptedLLM("谋", steps=[
            {"type": "final", "content": "凭感觉 10 个火战士稳赢，能杀 3 个。"},
            {"type": "final", "content": "还是这个结论。"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools())

        result = loop.run("10个火战士打5个终结者能杀几个？")

        assert result.degraded is True


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


class TestAmbiguousIsNotEmpty:
    """gnhf 审查模块 5 HIGH：ambiguous（同名多候选）是需要 LLM 消歧的实质性结果，
    不许被判空短路降级——否则评审 #25 的 candidates_preview + 提示词重查铁律整条不可达。"""

    def test_get_datasheet_ambiguous_reaches_llm_and_requery_succeeds(self):
        # ambiguous → 结果写回 messages → LLM 按候选名（含阵营）重查 → 正常作答不降级
        calls = []

        def fake_datasheet(name_or_id):
            calls.append(name_or_id)
            if name_or_id == "Helbrute":
                return {"found": False, "reason": "ambiguous",
                        "candidates": ["Helbrute (CSM)", "Helbrute (WE)"],
                        "candidates_preview": [{"candidate": "Helbrute (CSM)", "t": 9}]}
            return {"found": True, "datasheet": {"name_en": name_or_id, "T": 9}}

        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "get_datasheet", "args": {"name_or_id": "Helbrute"}},
            {"type": "tool_call", "tool": "get_datasheet",
             "args": {"name_or_id": "Helbrute (CSM)"}},
            {"type": "final", "content": "CSM 版 Helbrute 的 T 为 9。"},
        ])
        loop = AgentLoop(llm=llm, tools=_fake_tools(get_datasheet=fake_datasheet))

        result = loop.run("Helbrute 的韧性是多少？")

        assert result.degraded is False
        assert calls == ["Helbrute", "Helbrute (CSM)"]
        assert result.tool_calls == ["get_datasheet", "get_datasheet"]
        # LLM 确实见到过 ambiguous 候选（写回了 messages）
        assert any("candidates_preview" in str(m) for m in llm.next_step_calls[-1])

    def test_get_datasheet_plain_not_found_still_degrades(self):
        # 负向成对：普通查无此单位（无 reason）仍然立即降级 classic 兜底
        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "get_datasheet", "args": {"name_or_id": "不存在"}},
        ])
        tools = _fake_tools(get_datasheet=lambda name_or_id: {
            "found": False, "datasheet": None, "note": "库中未找到该单位"})
        loop = AgentLoop(llm=llm, tools=tools)

        result = loop.run("不存在单位的韧性？")

        assert result.degraded is True
        assert "rag_search" in result.tool_calls

    def test_get_entity_ambiguous_reaches_llm(self):
        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "get_entity", "args": {"name_or_id": "牛头怪"}},
            {"type": "final", "content": "该译名有多个候选：A、B，请确认指哪一个。"},
        ])
        tools = _fake_tools(get_entity=lambda name_or_id: {
            "found": False, "page": None,
            "resolved_via": {"confidence": "ambiguous", "candidates": ["A", "B"],
                             "name_en": None, "canonical_id": None},
            "note": "译名有多个候选，需向用户反问确认：A、B"})
        loop = AgentLoop(llm=llm, tools=tools)

        result = loop.run("牛头怪是什么？")

        assert result.degraded is False
        assert result.tool_calls == ["get_entity"]

    def test_entity_resolver_with_candidates_reaches_llm(self):
        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "entity_resolver", "args": {"name": "毒刃"}},
            {"type": "final", "content": "候选有两个，按上下文取 X。"},
        ])
        tools = _fake_tools(entity_resolver=lambda name: {
            "canonical_id": None, "name_en": None,
            "confidence": "ambiguous", "candidates": ["X", "Y"]})
        loop = AgentLoop(llm=llm, tools=tools)

        result = loop.run("毒刃是谁？")

        assert result.degraded is False

    def test_entity_resolver_no_candidates_still_degrades(self):
        # 负向成对：解析彻底失败（无 id 且无候选）仍降级
        llm = ScriptedLLM("查", steps=[
            {"type": "tool_call", "tool": "entity_resolver", "args": {"name": "乱码"}},
        ])
        tools = _fake_tools(entity_resolver=lambda name: {
            "canonical_id": None, "name_en": None,
            "confidence": "none", "candidates": []})
        loop = AgentLoop(llm=llm, tools=tools)

        result = loop.run("乱码是谁？")

        assert result.degraded is True


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
