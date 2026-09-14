"use client";

import { useCallback, useRef, useState } from "react";

import { AnswerHead } from "@/components/chat/AnswerHead";
import { AskCard } from "@/components/chat/AskCard";
import { CalcList } from "@/components/chat/CalcList";
import { CiteSeals } from "@/components/chat/CiteSeals";
import { Composer } from "@/components/chat/Composer";
import { Datasheet } from "@/components/chat/Datasheet";
import { SensitivityCta } from "@/components/chat/SensitivityCta";
import { SiteHeader } from "@/components/chat/SiteHeader";
import { ToolTrace } from "@/components/chat/ToolTrace";
import { VerdictCard } from "@/components/chat/VerdictCard";
import type { Answer, Exchange } from "@/lib/answer";
import { emptyAnswer, streamChat } from "@/lib/api";

type Status = "idle" | "streaming" | "error";

interface ChatAppProps {
  /** Optional supplied answer for previews; live pages start with an empty conversation. */
  initial?: Exchange;
}

/**
 * 聊天页 client 壳（Stage 3 闭环）：持有当前 exchange + 流式状态，
 * Questions use /chat SSE; the landing page offers prompts before the first answer.
 */
export function ChatApp({ initial }: ChatAppProps) {
  const [question, setQuestion] = useState(initial?.question ?? "查询规则、官方点数，或分析你的军表。");
  const [answer, setAnswer] = useState<Answer>(initial?.answer ?? {
    ...emptyAnswer(), followups: ["基里曼当前多少分？", "掩体在第11版如何生效？"],
  });
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const sessionRef = useRef<string | null>(null);

  const context = initial?.context ?? "当前语境：通用 · 第11版";

  const submit = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed || status === "streaming") return;

      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setQuestion(trimmed);
      setAnswer(emptyAnswer());
      setStatus("streaming");
      setErrorMsg(null);

      try {
        sessionRef.current ??= crypto.randomUUID();
        await streamChat(
          trimmed,
          context,
          {
            onMeta: (m) =>
              setAnswer((a) => ({
                ...a,
                summary: m.summary,
                traceWarn: m.traceWarn ?? undefined,
                degraded: m.degraded,
              })),
            onTrace: (step) =>
              setAnswer((a) => ({ ...a, trace: [...a.trace, step] })),
            onVerdict: (v) => setAnswer((a) => ({ ...a, verdict: v })),
            onCalc: (c) => setAnswer((a) => ({ ...a, calc: [...a.calc, c] })),
            onEntityCard: (e) => setAnswer((a) => ({ ...a, entityCard: e })),
            onCite: (c) => setAnswer((a) => ({ ...a, cites: [...a.cites, c] })),
            onSensitivity: (s) => setAnswer((a) => ({ ...a, sensitivity: s })),
            onCta: (c) => setAnswer((a) => ({ ...a, cta: c })),
            onFollowups: (f) => setAnswer((a) => ({ ...a, followups: f })),
            onDone: () => setStatus("idle"),
          },
          { signal: ctrl.signal, sessionId: sessionRef.current },
        );
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setStatus("error");
        setErrorMsg(err instanceof Error ? err.message : "请求失败，请稍后重试。");
      }
    },
    [context, status],
  );

  const hasVerdict = answer.verdict.lede.length > 0;
  const streaming = status === "streaming";

  return (
    <>
      <SiteHeader context={context} />
      <main className="mx-auto max-w-[1100px] px-5 pt-[26px] pb-[150px] max-tablet:px-2.5 max-tablet:pt-4 max-tablet:pb-[210px]">
        <AskCard question={question} />
        <div>
          <AnswerHead summary={answer.summary || (streaming ? "机魂运算中……" : "")} />
          {status === "error" ? (
            <p className="my-4 border border-redfont/40 bg-[#1a0d0d] px-4 py-3 font-mono text-[12.5px] text-[#d99] break-all">
              {errorMsg}
            </p>
          ) : null}
          <ToolTrace steps={answer.trace} warn={answer.traceWarn} />
          {hasVerdict ? <VerdictCard verdict={answer.verdict} /> : null}
          <CalcList steps={answer.calc} />
          {answer.entityCard ? <Datasheet card={answer.entityCard} /> : null}
          <CiteSeals cites={answer.cites} />
          <SensitivityCta
            sensitivity={answer.sensitivity}
            cta={answer.cta}
          />
        </div>
      </main>
      <Composer
        followups={answer.followups}
        onSubmit={submit}
        disabled={streaming}
      />
    </>
  );
}
