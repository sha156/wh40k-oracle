import assert from "node:assert/strict";
import test from "node:test";
import { answerMarkdown } from "../src/lib/answer-export.ts";

const answer = {
  summary: "One lookup", trace: [], degraded: true,
  verdict: { label: "Answer", labelEn: "Answer", lede: [{ t: "text", s: "Two orders " }, { t: "cite", n: 1 }] },
  calc: [{ n: 1, text: [{ t: "num", s: "12" }, { t: "text", s: " inches" }] }],
  cites: [{ n: 1, book: "L3 structured database", term: "Commander", wiki: "", section: "Merged card" }],
  followups: [], sensitivity: { title: "Limit", text: [{ t: "text", s: "Keep ~~~ and 中文" }] },
};

test("archive keeps source limits and a lossless snapshot without inventing pages", () => {
  const out = answerMarkdown("Orders?\nDetails", answer, new Date("2026-09-20T00:00:00Z"));
  assert.match(out, /authority: ai-generated/);
  assert.match(out, /不是官方规则/);
  assert.match(out, /降级路径/);
  assert.match(out, /Two orders \[1\]/);
  assert.match(out, /L3 structured database · Commander/);
  assert.doesNotMatch(out, /p\.0|p\.undefined/);
  const body = out.split("~~~~json\n")[1].split("\n~~~~")[0];
  assert.deepEqual(JSON.parse(body), { question: "Orders?\nDetails", answer });
});

test("empty answers cannot be saved and missing citations remain explicit", () => {
  assert.throws(() => answerMarkdown("Empty", { ...answer, verdict: { ...answer.verdict, lede: [] } }));
  assert.match(answerMarkdown("No sources", { ...answer, cites: [] }), /未提供可追溯引用/);
});

test("copying a readable answer keeps prose, emphasis and sources without internal JSON", () => {
  const readable = { ...answer,
    calc: [{ n: 1, text: [{ t: "strong", s: "What changed" }, { t: "text", s: ": Two conditions." }] }],
    sensitivity: { title: "◭ 敏感性 · Comparison scope", text: [{ t: "text", s: "July to August." }] },
  };
  const out = answerMarkdown("Changes", readable, new Date("2026-09-21T00:00:00Z"), { includeSnapshot: false });
  assert.match(out, /\n\*\*What changed\*\*: Two conditions\.\n/);
  assert.match(out, /## Comparison scope/);
  assert.match(out, /L3 structured database · Commander/);
  assert.doesNotMatch(out, /\n1\. |完整回答快照|"trace"|敏感性/);
  assert.match(answerMarkdown("Changes", readable), /完整回答快照/);
});
