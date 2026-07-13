import type { ValidationIssue, ValidationReport } from "@/lib/roster";

const SEV_STYLE: Record<string, { box: string; tag: string; label: string }> = {
  error: { box: "border-redfont/40 bg-[#1a0d0d]", tag: "text-redfont", label: "违规" },
  warn: { box: "border-gold/30 bg-[#141207]", tag: "text-gold", label: "注意" },
  info: { box: "border-panel-line bg-[#0d1517]", tag: "text-sage", label: "提示" },
};

function IssueRow({ issue }: { issue: ValidationIssue }) {
  const s = SEV_STYLE[issue.severity] ?? SEV_STYLE.info;
  return (
    <div className={`border ${s.box} px-3 py-1.5`}>
      <span className={`mr-2 font-cond text-[11px] tracking-[1px] ${s.tag} uppercase`}>
        {issue.surfacedOnly ? "未校验" : s.label}
      </span>
      <span className="text-[12.5px] text-[#c7d2cd]">{issue.message}</span>
      {issue.anchor ? (
        <span className="ml-1.5 font-mono text-[10.5px] text-[#4d5854]">
          [{issue.anchor}]
        </span>
      ) : null}
    </div>
  );
}

export function ValidationPanel({ report }: { report: ValidationReport | null }) {
  if (!report) {
    return (
      <div className="border border-dashed border-panel-line bg-[#0d1517] px-4 py-6 text-center font-cond text-[12.5px] tracking-[1px] text-[#5c6f6a] uppercase">
        加入单位后自动校验点数与编制
      </div>
    );
  }
  const over = report.totalPoints > report.limit;
  const pct = Math.min(100, (report.totalPoints / report.limit) * 100);
  return (
    <div className="clip-plate-10 border border-panel-line bg-panel">
      <div className="flex items-baseline justify-between border-b border-panel-line px-4 py-2">
        <span className="font-cond text-[13px] tracking-[2px] text-sage uppercase">
          编制校验
        </span>
        <span
          className={`clip-slant-8 px-2.5 py-0.5 font-cond text-[12px] font-bold tracking-[1px] uppercase ${
            report.legal
              ? "bg-[#0e3b2a] text-[#7fe0b0]"
              : "bg-[#3b0e0e] text-[#ffb0b0]"
          }`}
        >
          {report.legal ? "合法" : "不合法"}
        </span>
      </div>
      <div className="px-4 py-3">
        <div className="mb-1 flex items-baseline justify-between font-mono text-[12px]">
          <span className="text-[#8fa19b]">总点数</span>
          <span className={over ? "text-redfont" : "text-cyan-glow"}>
            <b className="font-cond text-[18px]">{report.totalPoints}</b>
            <span className="text-[#5c6f6a]"> / {report.limit}</span>
          </span>
        </div>
        <div className="h-2 border border-[#1d3238] bg-[rgba(111,195,212,.06)]">
          <i
            className={`block h-full ${over ? "bg-redfont/70" : "bg-[linear-gradient(90deg,rgba(111,195,212,.4),rgba(111,195,212,.85))]"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        {report.issues.length > 0 ? (
          <div className="mt-3 flex flex-col gap-1.5">
            {report.issues.map((i, idx) => (
              <IssueRow key={`${i.code}-${idx}`} issue={i} />
            ))}
          </div>
        ) : (
          <p className="mt-3 font-mono text-[11.5px] text-[#5c8a6a]">
            ✓ 未发现编制问题
          </p>
        )}
      </div>
    </div>
  );
}
