"use client";

import Link from "next/link";
import { useState } from "react";
import type { RichText } from "@/lib/answer";
import type { ChatMessage } from "@/lib/chat-state";
import { answerMarkdown, downloadAnswer } from "@/lib/answer-export";
import { Rich } from "../ui/Rich";
import { Datasheet } from "./Datasheet";
import styles from "./Chat.module.css";

function AnswerText({ text }: { text: RichText }) {
  return <Rich text={text} numClass={styles.answerStrong} strongClass={styles.answerStrong} kwClass={styles.answerKeyword} citeClass={styles.answerCite} />;
}

export function ChatAnswer({ message, onRetry, retryDisabled }: { message: ChatMessage; onRetry: () => void; retryDisabled: boolean }) {
  const { answer, question, status, id } = message;
  const [exportText, setExportText] = useState<string | null>(null);
  const [copyState, setCopyState] = useState("");
  const complete = status === "complete";
  const hasAnswer = answer.verdict.lede.length > 0;

  async function copyAnswer() {
    const markdown = answerMarkdown(question, answer);
    try {
      await navigator.clipboard.writeText(markdown);
      setCopyState("已复制");
    } catch {
      setExportText(markdown);
      setCopyState("请在下方选中并复制");
    }
  }

  return (
    <div>
      <div className={styles.assistantLabel}>
        <svg aria-hidden="true" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="m12 3 8 5v8l-8 5-8-5V8zM4 8l8 5 8-5m-8 5v8" strokeLinejoin="round" /></svg>
        40K 规则助手
      </div>
      {answer.degraded ? <p className={styles.warning}>{answer.traceWarn || "本次回答使用了兜底处理，请留意来源与补充说明。"}</p> : null}
      <div className={styles.answer}>
        {hasAnswer ? <p className={styles.paragraph}><AnswerText text={answer.verdict.lede} /></p> : null}
        {answer.calc.map((step, index) => <p key={`${step.n}-${index}`} className={styles.paragraph}><AnswerText text={step.text} /></p>)}
        {answer.sensitivity ? <aside className={styles.sensitivity}>
          <h3>{answer.sensitivity.title.replace(/^(?:◭\s*)?敏感性(?:\s*[·:：]\s*)?/, "").trim() || "补充说明"}</h3>
          <p><AnswerText text={answer.sensitivity.text} /></p>
        </aside> : null}
      </div>
      {status === "streaming" ? <p className={styles.working} role="status">
        <span className={styles.pulse} />{hasAnswer ? "正在整理回答……" : answer.trace.length ? "正在核对规则与来源……" : "正在思考并检索资料……"}
      </p> : null}
      {status === "error" || status === "stopped" ? <div className={styles.error} role="status">
        <p>{message.error || (status === "stopped" ? "已停止回答。以上内容可能不完整。" : "请求失败，请重试。")}</p>
        <button type="button" className={styles.retry} onClick={onRetry} disabled={retryDisabled}>重新提问</button>
      </div> : null}
      {answer.cites.length ? <details className={styles.details}>
        <summary>来源 · {answer.cites.length} 条</summary>
        <ol className={styles.sources}>
          {answer.cites.map((cite, index) => <li key={`${cite.n}-${index}`} value={cite.n}>
            <span className={styles.sourceTitle}>{cite.book}{cite.page != null && cite.page > 0 ? ` · p.${cite.page}` : cite.term ? ` · ${cite.term}` : ""}</span>
            {cite.section ? <span> · {cite.section}</span> : null}
            {cite.url && /^https?:\/\//i.test(cite.url) ? <a href={cite.url} target="_blank" rel="noopener noreferrer">打开来源</a> : null}
            {cite.wiki ? <div className={styles.sourcePath}>{cite.wiki}</div> : null}
          </li>)}
        </ol>
      </details> : null}
      {answer.trace.length || answer.traceWarn ? <details className={styles.details}>
        <summary>查看检索过程{answer.trace.length ? ` · ${answer.trace.length} 步` : ""}</summary>
        {answer.traceWarn ? <p className={styles.warning}>{answer.traceWarn}</p> : null}
        <ol className={styles.trace}>
          {answer.trace.map((step, index) => <li key={index}>
            <code>{step.fn}({step.args})</code>
            <span className={styles.traceResult}>{step.result}{step.note ? ` · ${step.note}` : ""}{step.status === "degraded" ? " · 结果有限" : ""}</span>
          </li>)}
        </ol>
      </details> : null}
      {answer.entityCard ? <details className={styles.details}>
        <summary>查看相关数据卡 · {answer.entityCard.nameZh || answer.entityCard.nameEn}</summary>
        <div className={styles.datasheet}><Datasheet card={answer.entityCard} showBadge={false} /></div>
      </details> : null}
      {hasAnswer && complete ? <div className={styles.actions}>
        <button type="button" onClick={copyAnswer}>
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M16 8V4H4v12h4" strokeLinejoin="round" /></svg>
          复制回答
        </button>
        <button type="button" onClick={() => downloadAnswer(question, answer)}>
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" strokeLinejoin="round" /></svg>
          下载 Markdown
        </button>
        <button type="button" onClick={() => setExportText(exportText === null ? answerMarkdown(question, answer) : null)} aria-expanded={exportText !== null} aria-controls={`markdown-${id}`}>
          {exportText === null ? "查看 Markdown" : "收起 Markdown"}
        </button>
        {answer.cta?.ready ? <Link className={styles.actionLink} href={answer.cta.kind === "simulator" ? "/simulator" : answer.cta.kind === "roster" ? "/roster" : "/codex"}>{answer.cta.kind === "simulator" ? "打开模拟器" : answer.cta.kind === "roster" ? "打开军表实验室" : "查看图鉴"}</Link> : null}
        <span role="status" className={styles.sourcePath}>{copyState}</span>
        {exportText !== null ? <div id={`markdown-${id}`} className={styles.copyPanel}>
          <p>AI 回答快照，可复制到 Obsidian 或保存为 .md 文件。</p>
          <textarea aria-label="Markdown 回答" readOnly value={exportText} rows={9} onFocus={(event) => event.currentTarget.select()} />
        </div> : null}
      </div> : null}
    </div>
  );
}
