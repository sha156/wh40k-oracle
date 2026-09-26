import type { Answer, Exchange } from "./answer";
import { validAnswer } from "./answer-validation.mjs";

export type MessageStatus = "streaming" | "complete" | "error" | "stopped";
export interface ChatMessage extends Exchange {
  id: string;
  status: MessageStatus;
  error?: string;
  startsSession?: boolean;
}

export interface ChatState {
  messages: ChatMessage[];
  activeId: string | null;
}

export type ChatAction =
  | { type: "start"; message: ChatMessage }
  | { type: "update"; id: string; update: (answer: Answer) => Answer }
  | { type: "finish"; id: string; status: Exclude<MessageStatus, "streaming">; error?: string }
  | { type: "restore"; messages: ChatMessage[] }
  | { type: "reset" };

/** Request IDs fence off late SSE events after cancellation or a new conversation. */
export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  if (action.type === "reset") return { messages: [], activeId: null };
  if (action.type === "restore") return state.messages.length ? state : { messages: action.messages, activeId: null };
  if (action.type === "start") {
    if (state.activeId) return state;
    return { messages: [...state.messages, action.message], activeId: action.message.id };
  }
  if (action.id !== state.activeId) return state;
  return {
    activeId: action.type === "finish" ? null : state.activeId,
    messages: state.messages.map((message) => message.id !== action.id ? message : action.type === "update"
      ? { ...message, answer: action.update(message.answer) }
      : { ...message, status: action.status, error: action.error }),
  };
}

export const HISTORY_KEY = "wh40k-chat-transcript-v1";
export const HISTORY_LIMIT = 30;
export const HISTORY_MAX_CHARS = 1_500_000;

const record = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const string = (value: unknown): value is string => typeof value === "string";
const optionalString = (value: unknown) => value === undefined || string(value);
function answer(value: unknown): value is Answer { return validAnswer(value); }

/** Stored transcripts are untrusted and are never sent as model conversation memory. */
export function restoreTranscript(raw: string | null): ChatMessage[] {
  if (!raw || raw.length > HISTORY_MAX_CHARS) return [];
  try {
    // Pydantic emits optional object fields as null, whereas the TS contract uses
    // absent properties. Do not remove null array entries: those must fail validation.
    const parsed: unknown = JSON.parse(raw, function (_key, value) {
      return value === null && !Array.isArray(this) ? undefined : value;
    });
    if (!record(parsed) || parsed.version !== 1 || !Array.isArray(parsed.messages)) return [];
    const seen = new Set<string>();
    return parsed.messages.slice(-HISTORY_LIMIT).flatMap((item): ChatMessage[] => {
      if (!record(item) || !string(item.id) || seen.has(item.id) || !string(item.question) || !string(item.context) || !answer(item.answer)
        || !["complete", "streaming", "error", "stopped"].includes(String(item.status)) || !optionalString(item.error)
        || item.startsSession !== undefined && typeof item.startsSession !== "boolean") return [];
      seen.add(item.id);
      return [{
        id: item.id, question: item.question, context: item.context, answer: item.answer,
        status: item.status === "streaming" ? "stopped" : item.status as MessageStatus,
        error: item.status === "streaming" ? "上次回答在完成前中断。" : item.error,
        startsSession: item.startsSession,
      }];
    });
  } catch {
    return [];
  }
}

/** Retain complete messages; never truncate the text of an answer to fit storage. */
export function serializeTranscript(messages: ChatMessage[]): string {
  const kept = messages.slice(-HISTORY_LIMIT);
  let raw = JSON.stringify({ version: 1, messages: kept });
  while (raw.length > HISTORY_MAX_CHARS && kept.length) {
    kept.shift();
    raw = JSON.stringify({ version: 1, messages: kept });
  }
  return raw;
}

export function shouldSendOnEnter(event: { key: string; shiftKey: boolean; isComposing: boolean; keyCode?: number }): boolean {
  return event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229;
}
