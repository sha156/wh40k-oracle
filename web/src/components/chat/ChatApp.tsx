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
  /** 初始示例（永久回归 fixture）——首屏展示，提问后替换为真链路结果。 */
  initial: Exchange;
}

/**
 * 聊天页 client 壳（Stage 3 闭环）：持有当前 exchange + 流式状态，
 * 提问经 /chat SSE 逐槽位填充回答。首屏用 fixture 示例，提问后走真后端。
 */
export function ChatApp({ initial }: ChatAppProps) {
  const [question, setQuestion] = useState(initial.question);
  const [answer, setAnswer] = useState<Answer>(initial.answer);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const context = initial.context;

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
          { signal: ctrl.signal },
        );
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setStatus("error");
        setErrorMsg(
          "无法连接后端。请确认 web_api 已启动：" +
            ".venv\\Scripts\\python.exe -m uvicorn web_api.main:app --port 8000",
        );
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
