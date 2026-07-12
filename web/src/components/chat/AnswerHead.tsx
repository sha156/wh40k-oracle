interface AnswerHeadProps {
  summary: string; // 如 "检索 4 步 · 引用 3 条 · 期望值粗算"
}

/** 应答分隔头：骷髅 + 标题 + 分隔线 + 摘要 */
export function AnswerHead({ summary }: AnswerHeadProps) {
  return (
    <div className="mb-3 flex items-center gap-[10px] font-cond text-[12.5px] tracking-[2px] text-[#8fa19c] uppercase max-tablet:flex-wrap max-tablet:text-[11px]">
      <span className="text-[14px] text-redfont">☠</span> 规则专家 · 应答{" "}
      <span className="h-px flex-1 bg-[linear-gradient(90deg,#33463f,transparent)]" />
      <span className="font-mono text-[11px] tracking-normal">{summary}</span>
    </div>
  );
}
