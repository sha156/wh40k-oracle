"use client";
import { useEffect, useRef, useState } from "react";
import { parseRoster, type ParsedRoster, type RosterPayload, type RosterSize } from "@/lib/roster";
import { latestRequest } from "@/lib/latest-request";

export function RosterImport({ factionId, detachmentId, size, onImport }: {
  factionId: string; detachmentId: string | null; size: RosterSize;
  onImport: (roster: RosterPayload) => void;
}) {
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<ParsedRoster | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const requests = useRef(latestRequest());
  useEffect(() => {
    const pending = requests.current;
    return () => pending.cancel();
  }, []);
  async function preview() {
    const request = requests.current.start();
    setBusy(true); setParsed(null); setError("");
    try {
      const result = await parseRoster(text, factionId, detachmentId, size, request.signal);
      if (request.isCurrent()) setParsed(result);
    }
    catch (e) { if (request.isCurrent()) setError(e instanceof Error ? e.message : "导入失败"); }
    finally { if (request.isCurrent()) setBusy(false); }
  }
  return <details className="mb-4 border border-panel-line bg-panel p-4 text-sm">
    <summary className="cursor-pointer text-bone">从文本导入军表</summary>
    <p className="my-3 text-[#a9bcb6]">每行一个单位，使用所选阵营的完整单位名或 ID。示例：5x Intercessor Squad。可添加 | warlord、| enhancement=强化名、| weapons=武器名:数量。点数会重新计算。</p>
    <textarea aria-label="军表文本" value={text} maxLength={20000} rows={6}
      onChange={e => { requests.current.cancel(); setBusy(false); setError(""); setText(e.target.value); setParsed(null); }}
      className="w-full border border-panel-line bg-dark p-3 text-bone"
      placeholder={"5x Intercessor Squad\nApothecary Biologis | models=1 | warlord"} />
    <button type="button" onClick={preview} disabled={busy || !text.trim()} className="my-3 border border-tau px-4 py-2 text-bone disabled:opacity-40">{busy ? "解析中…" : "预览导入"}</button>
    {error && <p role="alert" className="text-[#d99]">{error}</p>}
    {parsed && <div aria-live="polite">
      <p>已识别 {parsed.roster.units.length} 个单位。</p>
      {parsed.issues.map((i, n) => <p key={n} className="my-1 text-[#d99]">第 {i.line} 行：{i.reason} {i.text}</p>)}
      {parsed.complete && <button type="button" className="border border-tau px-4 py-2 text-bone" onClick={() => { onImport(parsed.roster); setParsed(null); }}>使用这份军表（替换当前编制）</button>}
    </div>}
  </details>;
}
