import type { Verdict } from "@/lib/answer";
import { Rich } from "../ui/Rich";
import { SlotBadge } from "../ui/SlotBadge";
import { VerdictShield } from "../ui/VerdictShield";

interface VerdictCardProps {
  verdict: Verdict;
}

/** E4 判定卡：斜纹缎带 + 结论 + 审定盾章 */
export function VerdictCard({ verdict }: VerdictCardProps) {
  return (
    <div className="clip-notch-18 relative mb-[18px] flex bg-[linear-gradient(#f2f3ec,var(--color-bone))] text-ink shadow-[0_6px_24px_rgba(0,0,0,.5)] max-tablet:flex-wrap">
      <SlotBadge id="E4" onLight />
      <div className="flex-none basis-[10px] bg-[repeating-linear-gradient(-45deg,var(--color-gw-red)_0_12px,#5e0404_12px_24px)] max-tablet:order-0 max-tablet:basis-2" />
      <div className="flex-1 py-4 pr-[22px] pl-[18px] max-tablet:order-1 max-tablet:flex-[1_1_100%] max-tablet:px-3.5 max-tablet:py-3">
        <h2 className="mb-1.5 font-cond text-[14px] tracking-[2.5px] text-gw-red uppercase">
          判定 · Verdict
        </h2>
        <p className="text-[15px] leading-[1.9] max-tablet:text-[14px]">
          <Rich
            text={verdict.lede}
            numClass="font-cond text-[16px] font-bold"
            strongClass="font-bold text-gw-red"
          />
        </p>
      </div>
      <div className="flex flex-none basis-32 flex-col items-center justify-center py-3.5 pr-4 max-tablet:order-2 max-tablet:flex-[1_1_100%] max-tablet:flex-row max-tablet:justify-center max-tablet:gap-3 max-tablet:px-3.5 max-tablet:pt-0 max-tablet:pb-3.5">
        <VerdictShield label={verdict.label} sub={verdict.labelEn} />
        <span className="mt-1.5 font-cond text-[10.5px] tracking-[2px] text-[#6b6f66] uppercase">
          审定印记
        </span>
      </div>
    </div>
  );
}
