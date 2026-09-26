"use client";

import { useRef, useState } from "react";
import { shouldSendOnEnter } from "@/lib/chat-state";
import styles from "./Chat.module.css";

interface ComposerProps {
  followups: string[];
  placeholder?: string;
  onSubmit?: (question: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  streaming?: boolean;
}

export function Composer({
  followups,
  placeholder = "问规则、查点数，或直接描述你的问题……",
  onSubmit,
  onStop,
  disabled = false,
  streaming = false,
}: ComposerProps) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const composingRef = useRef(false);

  const send = () => {
    const question = value.trim();
    if (!question || disabled || streaming) return;
    onSubmit?.(question);
    setValue("");
    if (inputRef.current) inputRef.current.style.height = "auto";
  };

  return (
    <div className={styles.composerWrap}>
      {followups.length > 0 ? <div className={styles.followups} aria-label="建议追问">
        {followups.map((question, index) => <button
          key={`${question}-${index}`}
          type="button"
          disabled={disabled || streaming}
          onClick={() => onSubmit?.(question)}
        >{question}</button>)}
      </div> : null}
      <form className={styles.composer} onSubmit={(event) => { event.preventDefault(); send(); }}>
        <textarea
          ref={inputRef}
          aria-label="向 40K 规则助手提问"
          value={value}
          rows={2}
          maxLength={8000}
          onChange={(event) => {
            setValue(event.target.value);
            event.target.style.height = "auto";
            event.target.style.height = `${Math.min(event.target.scrollHeight, 180)}px`;
          }}
          onCompositionStart={() => { composingRef.current = true; }}
          onCompositionEnd={() => { composingRef.current = false; }}
          onKeyDown={(event) => {
            if (shouldSendOnEnter({
              key: event.key, shiftKey: event.shiftKey,
              isComposing: composingRef.current || event.nativeEvent.isComposing,
              keyCode: event.nativeEvent.keyCode,
            })) {
              event.preventDefault();
              send();
            }
          }}
          placeholder={placeholder}
        />
        <div className={styles.composerFooter}>
          <span className={styles.modelBadge}><span className={styles.modelDot} />DeepSeek Flash</span>
          <span className={styles.composerHint}>Enter 发送 · Shift + Enter 换行</span>
          {streaming ? <button className={styles.send} type="button" aria-label="停止回答" title="停止回答" onClick={onStop}>
            <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><rect x="2" y="2" width="12" height="12" rx="2" /></svg>
          </button> : <button className={styles.send} type="submit" disabled={disabled || !value.trim()} aria-label="发送消息" title="发送消息">
            <svg aria-hidden="true" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 19V5m-6 6 6-6 6 6" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>}
        </div>
      </form>
      <p className={styles.footerNote}>AI 回答可能有误，请核对引用。记录仅保存在此浏览器，最多保留最近 30 条。</p>
    </div>
  );
}
