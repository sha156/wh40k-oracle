"use client";
import { useEffect, useState } from "react";

interface PriceRow {
  faction_slug: string; ordinal: number; kind: string; unit_name: string;
  tier: string; models: string; cost: number; source_url: string;
}
interface Prices { total: number; sourceRows: number; fetchedAt: string; rows: PriceRow[] }
const API = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

export function OfficialPoints() {
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [snapshot, setSnapshot] = useState<{ query: string; offset: number; data: Prices } | null>(null);
  const data = snapshot?.query === query && snapshot.offset === offset ? snapshot.data : null;
  const [error, setError] = useState("");
  useEffect(() => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      fetch(`${API}/codex/points?query=${encodeURIComponent(query)}&offset=${offset}`, { signal: ctrl.signal })
        .then(async r => { if (!r.ok) throw new Error(`点数查询失败 (${r.status})`); return await r.json() as Prices; })
        .then(result => { if (!ctrl.signal.aborted) { setSnapshot({ query, offset, data: result }); setError(""); } })
        .catch(e => { if (!ctrl.signal.aborted && e.name !== "AbortError") setError(e.message); });
    }, 200);
    return () => { clearTimeout(timer); ctrl.abort(); };
  }, [query, offset]);
  return <section className="text-bone">
    <h2 className="mb-3 text-xl">官方点数 · Munitorum Field Manual</h2>
    <p className="mb-4 text-sm text-[#a9bcb6]">保留官方的单位、重复编制、装备与强化价格。存在点数记录不代表结构库已收录完整兵牌。</p>
    <input aria-label="搜索官方点数" placeholder="英文单位、强化、武器或阵营名" value={query}
      onChange={e => { setQuery(e.target.value); setOffset(0); setError(""); }} className="mb-3 w-full border border-panel-line bg-dark p-3" />
    {error && <p role="alert" className="text-[#d99]">{error}</p>}
    {!data && !error && <p role="status" className="my-3 text-sm text-[#a9bcb6]">正在查询官方点数…</p>}
    {data && <>
      <p className="mb-3 text-sm">完整快照 {data.sourceRows} 条 · 匹配 {data.total} 条 · 抓取 {new Date(data.fetchedAt).toLocaleDateString()}</p>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm">
        <thead><tr>{["阵营 / 单位或分队", "档位", "编制 / 装备 / 强化", "点数", "来源"].map(h => <th key={h} className="border-b border-panel-line p-2">{h}</th>)}</tr></thead>
        <tbody>{data.rows.map(r => <tr key={`${r.faction_slug}/${r.ordinal}`}>
          <td className="border-b border-panel-line p-2"><span className="block text-xs text-[#a9bcb6]">{r.faction_slug}</span>{r.unit_name}</td>
          <td className="p-2">{r.tier}</td><td className="p-2">{r.models}</td><td className="p-2 font-bold">{r.cost}</td>
          <td className="p-2"><a href={r.source_url} target="_blank" rel="noopener noreferrer" className="underline">MFM ↗</a></td>
        </tr>)}</tbody>
      </table></div>
      <div className="my-4 flex gap-4">
        <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))} className="disabled:opacity-30">上一页</button>
        <span>{data.total ? offset + 1 : 0}–{Math.min(offset + 50, data.total)} / {data.total}</span>
        <button disabled={offset + 50 >= data.total} onClick={() => setOffset(offset + 50)} className="disabled:opacity-30">下一页</button>
      </div>
    </>}
  </section>;
}
