import sources from "@/data/official-sources.json";

/** Reviewed download links; this is a source archive, not a database coverage claim. */
export function OfficialSources() {
  return <section className="mb-4 border border-gold/40 bg-[#171509] px-4 py-3 text-sm text-bone">
    <p className="mb-3 text-[#a9bcb6]">下方中文改动清单保留 2026-07-26 快照。最新英文文件核对于 {sources.fetched_at}，规则更新以原文为准。点数已单独同步，兵牌属性与技能尚未逐字段复核全部新补丁。</p>
    <details>
    <summary className="cursor-pointer">查看 {sources.documents.length} 份官方英文文件</summary>
    <ul className="grid gap-2 sm:grid-cols-2">
      {sources.documents.map(doc => <li key={doc.url}>
        <a className="underline hover:text-gold" href={doc.url} target="_blank" rel="noopener noreferrer">{doc.title}</a>
      </li>)}
    </ul>
    </details>
  </section>;
}
