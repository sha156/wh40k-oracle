import type { CritiqueReport, UnitAssessment } from "@/lib/roster";

const ARCH_ORDER = ["geq", "meq", "teq", "veh"] as const;
const ARCH_LABEL: Record<string, string> = {
  geq: "杂兵", meq: "战锤", teq: "终结者", veh: "载具",
};

function fmt(v: number | null): string {
  return v == null ? "—" : v.toFixed(1);
}

/** 每100点伤害着色：越高越亮青（0–6 映射到透明度） */
function cellStyle(v: number | null): string {
  if (v == null) return "text-[#5c6f6a]";
  const a = Math.min(1, v / 6);
  return `text-cyan-glow`.concat(a > 0.5 ? " font-bold" : "");
}

function UnitScoreRow({ a }: { a: UnitAssessment }) {
  if (!a.assessed) {
    return (
      <tr className="border-b border-[#1a2624]">
        <td className="px-3 py-1.5 text-[12.5px] text-bone">{a.nameEn}</td>
        <td colSpan={4} className="px-3 py-1.5 text-[11.5px] text-[#7d8a86] italic">
          {a.note}
        </td>
      </tr>
    );
  }
  const byKey = new Map(a.scores.map((s) => [s.key, s.damagePer100]));
  return (
    <tr className="border-b border-[#1a2624] hover:bg-[#14262a]">
      <td className="px-3 py-1.5">
        <span className="text-[12.5px] text-bone">{a.nameEn}</span>
        <span className="ml-1.5 font-mono text-[10px] text-[#6f827c]">
          {a.phase === "melee" ? "近战" : "射击"} · {a.points ?? "?"}分
        </span>
      </td>
      {ARCH_ORDER.map((k) => {
        const v = byKey.get(k) ?? null;
        return (
          <td key={k} className={`px-3 py-1.5 text-right font-mono text-[12.5px] ${cellStyle(v)}`}>
            {fmt(v)}
          </td>
        );
      })}
    </tr>
  );
}

export function CritiquePanel({
  report,
  loading,
}: {
  report: CritiqueReport | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="border border-panel-line bg-[#0d1517] px-4 py-8 text-center font-cond text-[13px] tracking-[1px] text-sage uppercase">
        逐单位蒙特卡洛解算中…
      </div>
    );
  }
  if (!report) return null;
  return (
    <div className="clip-plate-10 border border-panel-line bg-panel">
      <div className="border-b border-panel-line px-4 py-2 font-cond text-[13px] tracking-[2px] text-sage uppercase">
        强度点评 · 每 100 点期望伤害
      </div>
      {report.summary.length > 0 ? (
        <div className="border-b border-panel-line bg-[#0f191c] px-4 py-2">
          {report.summary.map((s, i) => (
            <p key={i} className="my-0.5 text-[12.5px] text-[#a9bcb6]">
              {s}
            </p>
          ))}
        </div>
      ) : null}
      <div className="overflow-x-auto px-2 py-2">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-[#1d3238]">
              <th className="px-3 py-1 text-left font-cond text-[11px] tracking-[1px] text-[#7d8a86] uppercase">
                单位
              </th>
              {ARCH_ORDER.map((k) => (
                <th
                  key={k}
                  className="px-3 py-1 text-right font-cond text-[11px] tracking-[1px] text-[#7d8a86] uppercase"
                >
                  {ARCH_LABEL[k]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.assessments.map((a) => (
              <UnitScoreRow key={a.canonicalId + a.nameEn} a={a} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="border-t border-dashed border-[#1d3238] px-4 py-2">
        <p className="font-cond text-[10.5px] tracking-[1px] text-[#4d5854] uppercase">
          建模边界
        </p>
        {report.notModeled.map((s, i) => (
          <p key={i} className="text-[11px] text-[#6f827c]">
            · {s}
          </p>
        ))}
      </div>
    </div>
  );
}
