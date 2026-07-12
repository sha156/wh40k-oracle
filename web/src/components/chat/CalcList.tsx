import type { CalcStep } from "@/lib/answer";
import { Rich } from "../ui/Rich";
import { SlotBadge } from "../ui/SlotBadge";

interface CalcListProps {
  steps: CalcStep[];
  title?: string;
}

/** E5 计算依据：编号推演链 */
export function CalcList({
  steps,
  title = "计算依据 · Adeptus Calculus",
}: CalcListProps) {
  return (
    <div className="relative mb-[18px] border border-panel-line bg-panel">
      <SlotBadge id="E5" />
      <div className="border-b border-panel-line bg-[linear-gradient(90deg,#16262b,transparent)] px-3.5 py-2 font-cond text-[13px] tracking-[2.5px] text-sage uppercase">
        {title}
      </div>
      <ol className="list-none px-4 pt-2 pb-3 max-tablet:px-2.5 max-tablet:pt-1.5 max-tablet:pb-2.5">
        {steps.map((step) => (
          <li
            key={step.n}
            className="flex items-baseline gap-3 border-b border-dotted border-panel-line py-[7px] text-[13.5px] text-[#c3cdc7] last:border-b-0 max-tablet:gap-2 max-tablet:text-[12.8px]"
          >
            <span className="clip-statbox h-[22px] flex-none basis-[22px] bg-gw-red text-center font-cond text-[13px] leading-[22px] font-bold text-white">
              {step.n}
            </span>
            <span>
              <Rich
                text={step.text}
                numClass="font-cond text-[14.5px] font-bold text-bone"
                kwClass="font-semibold text-cyan-glow"
              />
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
