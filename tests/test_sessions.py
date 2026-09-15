import pytest
from agent.context import SessionContext
from agent.loop import AgentLoop
from web_api.sessions import SessionStore


def test_history_reaches_next_request_without_mutating_old_turns():
    session = SessionContext()
    session.append_turn("user", "My army is Space Marines")
    session.append_turn("assistant", "Recorded")
    class LLM:
        def classify_intent(self, text):
            return "闲聊"
        def next_step(self, messages, tools):
            assert messages[0]["content"] == "My army is Space Marines"
            assert messages[-1]["content"] == "What army did I mention?"
            messages[0]["content"] = "mutation must not escape"
            return {"type": "final", "content": "Space Marines"}
    result = AgentLoop(LLM(), {}).run("What army did I mention?", session)
    assert result.answer == "Space Marines"
    assert session.history[0]["content"] == "My army is Space Marines"


def test_history_and_session_count_are_bounded_and_expire():
    now = [0]
    store = SessionStore(capacity=2, ttl=10, clock=lambda: now[0])
    with store.session("a") as session:
        for _ in range(20):
            session.append_turn("user", "x" * 5000)
        assert len(session.history) == 12
        assert len(session.history[0]["content"]) == 4000
        with store.session("b"):
            with pytest.raises(RuntimeError, match="繁忙"):
                with store.session("c"):
                    pass
    with store.session("b") as other:
        assert not other.history
    now[0] = 11
    with store.session("a") as expired:
        assert not expired.history
    assert len(store._entries) == 1


def test_anonymous_requests_never_share_context():
    store = SessionStore()
    with store.session(None) as first:
        first.append_turn("user", "private")
    with store.session(None) as second:
        assert not second.history


def test_web_tracing_preserves_positional_fallback_search():
    from web_api.trace import TraceRecorder
    class FailedLLM:
        def classify_intent(self, text):
            return "查"
        def next_step(self, messages, tools):
            raise RuntimeError("model temporarily unavailable")
    def search(query):
        return {"found": True, "passages": [{"book": "Core Rules", "page": 1,
                                              "text": "Verified source: " + query}]}
    recorder = TraceRecorder({"rag_search": search})
    result = AgentLoop(FailedLLM(), recorder.wrapped_tools()).run("test question")
    assert result.degraded
    assert result.sources[0]["text"] == "Verified source: test question"
    assert recorder.last_args["rag_search"] == {"query": "test question"}
    assert len(recorder.steps) == 1


def test_history_does_not_bypass_current_fact_verification():
    class LLM:
        def classify_intent(self, text):
            return "算"
        def next_step(self, messages, tools):
            return {"type": "final", "content": "Old price from history"}
    session = SessionContext()
    session.append_turn("assistant", "This unit costs 123 points")
    result = AgentLoop(LLM(), {}).run("How much does it cost now?", session)
    assert result.degraded
    assert result.answer != "Old price from history"
