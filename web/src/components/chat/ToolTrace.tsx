import type { TraceStep } from "@/lib/answer";
import { SlotBadge } from "../ui/SlotBadge";

interface ToolTraceProps {
  steps: TraceStep[];
  warn?: string;
  defaultOpen?: boolean;
}

/** E3 机魂运转记录：可折叠工具调用轨迹（原生 details，无 JS 依赖） */
export function ToolTrace({ steps, warn, defaultOpen = true }: ToolTraceProps) {
  return (
    <details
      className="relative mb-[18px] border border-panel-line border-l-[3px] border-l-tau bg-panel"
      open={defaultOpen}
    >
      <SlotBadge id="E3" />
      <summary className="flex cursor-pointer list-none items-center gap-[10px] px-3.5 py-2 font-cond text-[13px] tracking-[1.5px] text-sage [&::-webkit-details-marker]:hidden">
        <span className="text-[15px] text-tau">⚙</span> 机魂运转记录 · TOOL
        TRACE
        {warn ? (
          <span className="ml-auto border border-amber/40 px-2 py-px font-mono text-[11px] tracking-normal text-amber">
            {warn}
          </span>
        ) : null}
      </summary>
      <div className="border-t border-dashed border-panel-line px-3.5 pt-2.5 pb-3">
        {steps.map((step, i) => {
          const degraded = step.status === "degraded";
          return (
            <div
              key={i}
              className="flex items-baseline gap-[10px] py-[3px] font-mono text-[12.5px] text-[#8ea39d]"
            >
              <span className="text-[#5a6f69]">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>
                <span className={degraded ? "text-amber" : "text-cyan-glow"}>
                  {step.fn}
                </span>
                {step.args}
                {step.result ? <> → {step.result}</> : null}{" "}
                {step.note ? (
                  <span className="text-[#b5a27a]">{step.note}</span>
                ) : null}
              </span>
              <span
                className={`ml-auto ${degraded ? "text-amber" : "text-[#59a06b]"}`}
              >
                {degraded ? "⚠" : "✓"}
              </span>
            </div>
          );
        })}
      </div>
    </details>
  );
}
