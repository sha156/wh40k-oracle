/**
 * 后端 /chat SSE 客户端（BUILD-PLAN Stage 3 闭环）。
 * 浏览器 EventSource 只支持 GET，故用 fetch 手动解析 POST 的 SSE 流：
 * 先流 meta/trace，再逐槽位（verdict/calc/entityCard/cite/sensitivity/cta/followups），末 done。
 */
import type {
  Answer,
  CalcStep,
  Cite,
  Cta,
  EntityCard,
  Sensitivity,
  TraceStep,
  Verdict,
} from "./answer";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

export interface ChatMeta {
  summary: string;
  traceWarn?: string | null;
  degraded: boolean;
}

export interface ChatHandlers {
  onMeta?: (m: ChatMeta) => void;
  onTrace?: (step: TraceStep) => void;
  onVerdict?: (v: Verdict) => void;
  onCalc?: (c: CalcStep) => void;
  onEntityCard?: (e: EntityCard) => void;
  onCite?: (c: Cite) => void;
  onSensitivity?: (s: Sensitivity) => void;
  onCta?: (c: Cta) => void;
  onFollowups?: (f: string[]) => void;
  onDone?: () => void;
}

const DISPATCH: Record<string, keyof ChatHandlers> = {
  meta: "onMeta",
  trace: "onTrace",
  verdict: "onVerdict",
  calc: "onCalc",
  entityCard: "onEntityCard",
  cite: "onCite",
  sensitivity: "onSensitivity",
  cta: "onCta",
  followups: "onFollowups",
  done: "onDone",
};

function dispatch(event: string, data: unknown, handlers: ChatHandlers): void {
  const key = DISPATCH[event];
  if (!key) return;
  const fn = handlers[key] as ((arg: unknown) => void) | undefined;
  fn?.(data);
}

/** 解析一个 SSE 事件块（event: / data: 行）。 */
function parseBlock(block: string): { event: string; data: unknown } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}

/** 发起一次 /chat SSE 请求，事件到达即回调。可 abort。 */
export async function streamChat(
  question: string,
  context: string,
  handlers: ChatHandlers,
  opts: { signal?: AbortSignal; sessionId?: string } = {},
): Promise<void> {
  const resp = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, context, session_id: opts.sessionId }),
    signal: opts.signal,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`后端返回 ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE 事件以空行分隔
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const parsed = parseBlock(block);
      if (parsed) dispatch(parsed.event, parsed.data, handlers);
    }
  }
}

/** 空回答骨架：新查询开始时重置，事件到达再逐槽位填充。 */
export function emptyAnswer(): Answer {
  return {
    summary: "",
    trace: [],
    verdict: { label: "", labelEn: "", lede: [] },
    calc: [],
    cites: [],
    followups: [],
    degraded: false,
  };
}
