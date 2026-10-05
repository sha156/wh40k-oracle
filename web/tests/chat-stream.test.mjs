import assert from "node:assert/strict";
import test from "node:test";
import { streamChat } from "../src/lib/api.ts";

const verdict = { label: "Answer", labelEn: "Answer", lede: [{ t: "text", s: "中文规则。" }] };
const event = (name, data) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;

async function withResponse(chunks, fn) {
  const original = globalThis.fetch;
  const encoder = new TextEncoder();
  globalThis.fetch = async () => new Response(new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(typeof chunk === "string" ? encoder.encode(chunk) : chunk);
      controller.close();
    },
  }), { headers: { "Content-Type": "text/event-stream" } });
  try { await fn(); } finally { globalThis.fetch = original; }
}

test("split UTF-8 and CRLF chunks preserve complete ordered paragraphs", async () => {
  const body = [event("verdict", verdict), event("calc", { n: 1, text: [{ t: "text", s: "完整正文" }] }), event("done", {})].join("").replaceAll("\n", "\r\n");
  const bytes = new TextEncoder().encode(body);
  const received = [];
  await withResponse(Array.from(bytes, (byte) => Uint8Array.of(byte)), async () => {
    await streamChat("question", "context", { onVerdict: (v) => received.push(v.lede[0].s), onCalc: (c) => received.push(c.text[0].s) });
  });
  assert.deepEqual(received, ["中文规则。", "完整正文"]);
});

test("parseable malformed event payloads fail before reaching React", async () => {
  for (const [name, data] of [["verdict", null], ["calc", { n: 1, text: "bad" }], ["trace", { fn: 42 }], ["cite", { n: 1 }]]) {
    let dispatched = false;
    await withResponse([event(name, data), event("done", {})], async () => {
      await assert.rejects(streamChat("question", "context", {
        onVerdict: () => { dispatched = true; }, onCalc: () => { dispatched = true; },
        onTrace: () => { dispatched = true; }, onCite: () => { dispatched = true; },
      }), /回答数据/);
    });
    assert.equal(dispatched, false);
  }
});

test("a done event without an answer is an error, not an empty successful reply", async () => {
  await withResponse([event("done", {})], async () => {
    await assert.rejects(streamChat("question", "context", {}), /完整回答/);
  });
});

test("metadata cannot overwrite saved answer defaults with missing degraded state", async () => {
  for (const data of [{ summary: "Answer" }, { summary: "Answer", degraded: null }]) {
    let dispatched = false;
    await withResponse([event("meta", data), event("verdict", verdict), event("done", {})], async () => {
      await assert.rejects(streamChat("question", "context", {
        onMeta: () => { dispatched = true; },
      }), /回答数据/);
    });
    assert.equal(dispatched, false);
  }
});

test("unexpected EOF remains an explicit transfer failure", async () => {
  await withResponse([event("verdict", verdict)], async () => {
    await assert.rejects(streamChat("question", "context", {}), /传输中断/);
  });
});

test("done closes a still-open stream and preserves nullable backend fields", { timeout: 2000 }, async () => {
  const original = globalThis.fetch;
  let cancelled = false;
  let trace;
  globalThis.fetch = async () => new Response(new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(event("trace", { fn: "get_datasheet", args: "unit", status: "ok", note: null }) + event("verdict", verdict) + event("done", {})));
      // A proxy may keep the connection open after the application is done.
    },
    cancel() { cancelled = true; },
  }));
  try {
    await streamChat("question", "context", { onTrace: (value) => { trace = value; } });
    assert.equal(cancelled, true);
    assert.equal(trace.note, undefined);
  } finally { globalThis.fetch = original; }
});
