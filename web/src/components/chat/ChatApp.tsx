"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import type { Answer, Exchange } from "@/lib/answer";
import { emptyAnswer, streamChat } from "@/lib/api";
import { chatReducer, HISTORY_KEY, restoreTranscript, serializeTranscript } from "@/lib/chat-state";
import { Composer } from "./Composer";
import { SiteHeader } from "./SiteHeader";
import { ChatAnswer } from "./ChatAnswer";
import styles from "./Chat.module.css";

const EXAMPLES = [
  "基里曼当前多少分？",
  "掩体在第11版如何生效？",
  "破敌重誓相比于以前更新了什么？",
];

interface ChatAppProps {
  initial?: Exchange;
}

export function ChatApp({ initial }: ChatAppProps) {
  const [state, dispatch] = useReducer(chatReducer, {
    messages: initial ? [{ ...initial, id: "preview", status: "complete" as const }] : [],
    activeId: null,
  });
  const [hydrated, setHydrated] = useState(Boolean(initial));
  const [restored, setRestored] = useState(false);
  const [storageWarning, setStorageWarning] = useState(false);
  const [showJump, setShowJump] = useState(false);
  const [conversationKey, setConversationKey] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const sessionRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const followBottom = useRef(true);
  const context = initial?.context ?? "当前语境：通用 · 第11版";
  const streaming = state.activeId !== null;

  useEffect(() => {
    if (initial) return;
    let mounted = true;
    // Wait until hydration so server and client initially render the same page.
    queueMicrotask(() => {
      if (!mounted) return;
      try {
        const messages = restoreTranscript(localStorage.getItem(HISTORY_KEY));
        dispatch({ type: "restore", messages });
        setRestored(messages.length > 0);
      } catch {
        setStorageWarning(true);
      }
      setHydrated(true);
    });
    return () => { mounted = false; };
  }, [initial]);

  useEffect(() => {
    if (!hydrated || initial) return;
    try {
      localStorage.setItem(HISTORY_KEY, serializeTranscript(state.messages));
    } catch {
      queueMicrotask(() => setStorageWarning(true));
    }
  }, [state.messages, hydrated, initial]);

  useEffect(() => () => { abortRef.current?.abort(); }, []);

  useEffect(() => {
    if (followBottom.current && scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "instant" });
    }
  }, [state.messages]);

  const submit = useCallback(async (rawQuestion: string) => {
    const question = rawQuestion.trim();
    if (!question || abortRef.current || !hydrated) return;
    const controller = new AbortController();
    abortRef.current = controller;
    const id = crypto.randomUUID();
    const startsSession = sessionRef.current === null && state.messages.length > 0;
    sessionRef.current ??= crypto.randomUUID();
    followBottom.current = true;
    setShowJump(false);
    setRestored(false);
    dispatch({ type: "start", message: { id, question, context, answer: emptyAnswer(), status: "streaming", startsSession } });
    const current = () => abortRef.current === controller && !controller.signal.aborted;
    const update = (apply: (answer: Answer) => Answer) => {
      if (current()) dispatch({ type: "update", id, update: apply });
    };
    try {
      await streamChat(question, context, {
        onMeta: (meta) => update((answer) => ({ ...answer, summary: meta.summary, traceWarn: meta.traceWarn ?? undefined, degraded: meta.degraded })),
        onTrace: (step) => update((answer) => ({ ...answer, trace: [...answer.trace, step] })),
        onVerdict: (verdict) => update((answer) => ({ ...answer, verdict })),
        onCalc: (step) => update((answer) => ({ ...answer, calc: [...answer.calc, step] })),
        onEntityCard: (entityCard) => update((answer) => ({ ...answer, entityCard })),
        onCite: (cite) => update((answer) => ({ ...answer, cites: [...answer.cites, cite] })),
        onSensitivity: (sensitivity) => update((answer) => ({ ...answer, sensitivity })),
        onCta: (cta) => update((answer) => ({ ...answer, cta })),
        onFollowups: (followups) => update((answer) => ({ ...answer, followups })),
      }, { signal: controller.signal, sessionId: sessionRef.current });
      if (current()) dispatch({ type: "finish", id, status: "complete" });
    } catch (error) {
      if (current()) dispatch({ type: "finish", id, status: "error", error: error instanceof Error ? error.message : "请求失败，请稍后重试。" });
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [context, hydrated, state.messages.length]);

  function stop() {
    abortRef.current?.abort();
    abortRef.current = null;
    if (state.activeId) dispatch({ type: "finish", id: state.activeId, status: "stopped" });
    // The server may still finish an aborted request. Isolate any subsequent turn.
    sessionRef.current = null;
  }

  function newConversation() {
    abortRef.current?.abort();
    abortRef.current = null;
    sessionRef.current = null;
    dispatch({ type: "reset" });
    setConversationKey((key) => key + 1);
    setRestored(false);
    followBottom.current = true;
    setShowJump(false);
  }

  const lastAnswer = state.messages.at(-1);
  return (
    <div className={styles.shell}>
      <SiteHeader variant="chat" context={context} onNewChat={newConversation} />
      <div ref={scrollRef} className={styles.scrollArea} onScroll={(event) => {
        const area = event.currentTarget;
        followBottom.current = area.scrollHeight - area.scrollTop - area.clientHeight < 100;
        setShowJump(!followBottom.current);
      }}>
        <main className={`${styles.main} ${state.messages.length === 0 ? styles.emptyMain : ""}`}>
          {storageWarning ? <p className={styles.notice}>此浏览器无法保存记录，关闭页面后本次对话将不会保留。</p> : null}
          {restored ? <p className={styles.notice}>已恢复本机保存的阅读记录。继续提问会开始新的对话，请重新说明需要沿用的背景。</p> : null}
          {state.messages.length === 0 ? <div className={styles.welcome}>
            <p className={styles.eyebrow}>WARHAMMER 40,000 · 第 11 版</p>
            <h1>今天想了解什么规则？</h1>
            <p className={styles.intro}>查询单位点数、理解规则变化，或一起推演战场上的选择。<br />完整解答，附上可核对的来源。</p>
            <div className={styles.examples}>
              {EXAMPLES.map((question, index) => <button className={styles.example} key={question} type="button" onClick={() => submit(question)} disabled={!hydrated}>
                <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  {index === 0 ? <><circle cx="10" cy="10" r="6" /><path d="m15 15 5 5" /></> : index === 1 ? <><path d="M4 4h7v16H4zm9 0h7v16h-7M7 8h1m-1 4h1m8-4h1m-1 4h1" /></> : <><path d="M5 6h14m-4-4 4 4-4 4M19 18H5m4-4-4 4 4 4" strokeLinejoin="round" /></>}
                </svg>
                <span>{question}</span>
                <svg className={styles.exampleArrow} aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="m9 5 7 7-7 7" /></svg>
              </button>)}
            </div>
          </div> : state.messages.map((message) => <article className={styles.exchange} key={message.id} aria-labelledby={`question-${message.id}`}>
            {message.startsSession ? <div className={styles.sessionDivider}>新对话 · 以上记录仅供阅读</div> : null}
            <div className={styles.question}><h2 id={`question-${message.id}`}>{message.question}</h2></div>
            <ChatAnswer message={message} onRetry={() => submit(message.question)} retryDisabled={streaming} />
          </article>)}
        </main>
        {showJump ? <button type="button" className={styles.jump} onClick={() => {
          followBottom.current = true;
          setShowJump(false);
          scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "instant" });
        }}>回到最新消息 ↓</button> : null}
      </div>
      <Composer
        key={conversationKey}
        followups={!streaming && lastAnswer?.status === "complete" ? lastAnswer.answer.followups : []}
        onSubmit={submit}
        onStop={stop}
        streaming={streaming}
        disabled={!hydrated}
      />
    </div>
  );
}
