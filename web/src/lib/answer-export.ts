import type { Answer, RichText } from "./answer";

function plain(spans: RichText): string {
  return spans.map((span) => span.t === "cite" ? `[${span.n}]` : span.s).join("");
}

/** Explicit user download; never writes AI output into the official wiki. */
export function answerMarkdown(question: string, answer: Answer, savedAt = new Date()): string {
  if (!answer.verdict.lede.length) throw new Error("没有完整回答可保存。");
  const lines = [
    "---", "type: archived-answer", "authority: ai-generated",
    `saved_at: ${JSON.stringify(savedAt.toISOString())}`, "---", "",
    `# ${question.replace(/[\r\n]+/g, " ")}`, "",
    "> AI 生成的回答快照，未经人工复核，不是官方规则。点数和规则可能随后更新。", "",
    ...(answer.degraded ? ["> 本次回答使用了降级路径。", ""] : []),
    plain(answer.verdict.lede), "",
    ...answer.calc.map((step) => `${step.n}. ${plain(step.text)}`), "",
  ];
  if (answer.sensitivity) lines.push(`## ${answer.sensitivity.title}`, "", plain(answer.sensitivity.text), "");
  lines.push("## 引用", "");
  for (const cite of answer.cites) {
    const location = cite.page != null && cite.page > 0 ? ` · p.${cite.page}` : "";
    lines.push(`[${cite.n}] ${cite.book}${location}${cite.term ? ` · ${cite.term}` : ""}`);
    if (cite.section) lines.push(`类别：${cite.section}`);
    if (cite.wiki) lines.push(`Wiki：${cite.wiki}`);
    if (cite.url) lines.push(cite.url);
    lines.push("");
  }
  if (!answer.cites.length) lines.push("本次回答未提供可追溯引用。", "");
  // Preserve all fields (including a full datasheet and trace) losslessly.
  const snapshot = JSON.stringify({ question, answer }, null, 2);
  const fence = "~".repeat(Math.max(3, ...Array.from(snapshot.matchAll(/~+/g), (m) => m[0].length + 1)));
  lines.push("## 完整回答快照", "", `${fence}json`, snapshot, fence, "");
  return lines.join("\n");
}

export function downloadAnswer(question: string, answer: Answer): void {
  const now = new Date();
  const url = URL.createObjectURL(new Blob([answerMarkdown(question, answer, now)], { type: "text/markdown;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `40k-answer-${now.toISOString().replace(/[:.]/g, "-")}.md`;
  document.body.appendChild(link);
  try {
    link.click();
  } finally {
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
