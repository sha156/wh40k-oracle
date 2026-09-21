import assert from "node:assert/strict";
import test from "node:test";
import { chatReducer, restoreTranscript, serializeTranscript, shouldSendOnEnter, HISTORY_LIMIT, HISTORY_MAX_CHARS } from "../src/lib/chat-state.ts";

function message(id, status = "streaming") {
  return {
    id, status, question: "破敌重誓改了什么？", context: "第11版",
    answer: {
      summary: "Two sources", degraded: false, trace: [], followups: [],
      verdict: { label: "Updated", labelEn: "Updated", lede: [{ t: "text", s: "先回答问题。" }] },
      calc: [{ n: 1, text: [{ t: "text", s: "完整比较，包括没有变化的部分。" }, { t: "cite", n: 1 }] }],
      sensitivity: { title: "比较范围", text: [{ t: "text", s: "无法验证旧版的部分需保留限制。" }] },
      cites: [{ n: 1, book: "Faction pack", page: 60, wiki: "example" }],
    },
  };
}

test("following turns keep the complete first answer and all streamed paragraphs", () => {
  let state = chatReducer({ messages: [], activeId: null }, { type: "start", message: message("first") });
  state = chatReducer(state, { type: "update", id: "first", update: (answer) => ({ ...answer, calc: [...answer.calc, { n: 2, text: [{ t: "text", s: "实战影响也必须保留。" }] }] }) });
  state = chatReducer(state, { type: "finish", id: "first", status: "complete" });
  const first = state.messages[0];
  state = chatReducer(state, { type: "start", message: message("second") });
  assert.equal(state.messages.length, 2);
  assert.equal(state.messages[0], first);
  assert.equal(state.messages[0].answer.calc.length, 2);
  assert.equal(state.activeId, "second");
});

test("reset and stop fence off late response events and completion", () => {
  let state = chatReducer({ messages: [], activeId: null }, { type: "start", message: message("old") });
  state = chatReducer(state, { type: "reset" });
  state = chatReducer(state, { type: "start", message: message("new") });
  for (const action of [
    { type: "update", id: "old", update: () => { throw Error("stale updates must not run"); } },
    { type: "finish", id: "old", status: "error", error: "late failure" },
    { type: "start", message: message("duplicate") },
  ]) assert.equal(chatReducer(state, action), state);
  state = chatReducer(state, { type: "finish", id: "new", status: "stopped" });
  assert.equal(state.activeId, null);
  assert.equal(state.messages[0].status, "stopped");
  assert.equal(chatReducer(state, { type: "update", id: "new", update: () => { throw Error("cancelled"); } }), state);
});

test("restored reading records retain all prose and label interrupted answers", () => {
  const complete = message("done", "complete");
  const raw = serializeTranscript([complete, message("interrupted")]);
  const restored = restoreTranscript(raw);
  assert.deepEqual(restored[0].answer, complete.answer);
  assert.equal(restored[1].status, "stopped");
  assert.match(restored[1].error, /中断/);
  assert.doesNotMatch(raw, /sessionId|session_id/);
});

test("invalid and oversized stored data cannot crash rendering", () => {
  for (const raw of [null, "{broken", "null", '{"version":2,"messages":[]}', " ".repeat(HISTORY_MAX_CHARS + 1)]) {
    assert.deepEqual(restoreTranscript(raw), []);
  }
  const invalid = message("invalid", "complete");
  invalid.answer.calc[0].text = [{ t: "text", s: { malicious: true } }];
  const invalidCard = message("invalid-card", "complete");
  invalidCard.answer.entityCard = { nameZh: "Broken" };
  const raw = JSON.stringify({ version: 1, messages: [invalid, invalidCard, message("valid", "complete"), message("valid", "complete")] });
  assert.deepEqual(restoreTranscript(raw).map((item) => item.id), ["valid"]);
});

test("real backend null-bearing optional fields restore safely", () => {
  const backend = message("nullable-backend", "complete");
  backend.answer.trace = [{ fn: "get_datasheet", args: "('基里曼')", result: "已命中", status: "ok", note: null }];
  backend.answer.traceWarn = null;
  backend.answer.cta = null;
  backend.answer.cites[0] = { n: 1, book: "MFM", wiki: "", page: null, section: null, term: null, url: null };
  backend.answer.entityCard = {
    nameZh: "基里曼", nameEn: "Roboute Guilliman", pts: "355", role: null, invuln: null,
    stats: [], ranged: [], melee: [], abilities: [{ name: "Example", text: "Preserved", tag: null, rich: null }],
    composition: [], keywords: "INFANTRY", faction: "SM", src: "Structured database", wiki: "unit.md",
    loadout: null, damaged: null, leads: null, legend: null, factionKeywords: null,
  };
  const restored = restoreTranscript(serializeTranscript([backend]));
  assert.equal(restored.length, 1);
  assert.equal(restored[0].answer.entityCard.nameEn, "Roboute Guilliman");
  assert.equal(restored[0].answer.entityCard.abilities[0].text, "Preserved");
  assert.equal(restored[0].answer.trace[0].note, undefined);
  assert.deepEqual(restored[0].answer.calc, backend.answer.calc);
  backend.answer.calc.push(null);
  assert.deepEqual(restoreTranscript(serializeTranscript([backend])), []);
});

test("history is bounded by count and size without truncating an answer", () => {
  const messages = Array.from({ length: HISTORY_LIMIT + 5 }, (_, index) => message(String(index), "complete"));
  let restored = restoreTranscript(serializeTranscript(messages));
  assert.equal(restored.length, HISTORY_LIMIT);
  assert.equal(restored[0].id, "5");
  const big = message("big", "complete");
  big.answer.verdict.lede[0].s = "X".repeat(HISTORY_MAX_CHARS);
  restored = restoreTranscript(serializeTranscript([big, message("recent", "complete")]));
  assert.deepEqual(restored.map((item) => item.id), ["recent"]);
  assert.deepEqual(restored[0].answer, message("recent", "complete").answer);
});

test("Enter submits; Shift+Enter and IME confirmation never submit", () => {
  const enter = { key: "Enter", shiftKey: false, isComposing: false, keyCode: 13 };
  assert.equal(shouldSendOnEnter(enter), true);
  assert.equal(shouldSendOnEnter({ ...enter, shiftKey: true }), false);
  assert.equal(shouldSendOnEnter({ ...enter, isComposing: true }), false);
  assert.equal(shouldSendOnEnter({ ...enter, keyCode: 229 }), false);
  assert.equal(shouldSendOnEnter({ ...enter, key: "a" }), false);
});
