import type { Answer } from "@/lib/answer";
import { PlateButton } from "../ui/PlateButton";
import { Rich } from "../ui/Rich";
import { SlotBadge } from "../ui/SlotBadge";

interface SensitivityCtaProps {
  sensitivity?: Answer["sensitivity"];
  cta?: Answer["cta"];
}

/** E8 敏感性提示 + 模拟器 CTA */
export function SensitivityCta({ sensitivity, cta }: SensitivityCtaProps) {
  if (!sensitivity && !cta) return null;
  return (
    <div className="relative mb-[26px] flex items-stretch gap-3.5 max-wide:flex-col">
      <SlotBadge id="E8" className="-top-4" />
      {sensitivity ? (
        <div className="flex-1 border border-amber/45 border-l-4 border-l-amber bg-[linear-gradient(100deg,rgba(201,147,10,.14),rgba(201,147,10,.05))] px-4 py-3 text-[13.5px] text-[#d8cdb2]">
          <div className="mb-1 font-cond text-[12px] font-bold tracking-[2px] text-amber uppercase">
            {sensitivity.title}
          </div>
          <Rich
            text={sensitivity.text}
            numClass="font-cond text-[14.5px] font-bold text-[#f0e3bd]"
          />
        </div>
      ) : null}
      {cta ? (
        <div className="flex flex-none flex-col items-center gap-1 self-center max-tablet:w-full">
          <PlateButton
            href="#"
            clip="slant-14"
            className="px-[30px] py-3 text-[15px] shadow-[0_4px_14px_rgba(153,0,0,.4)] max-tablet:w-full max-tablet:px-4 max-tablet:text-center max-tablet:text-[14px]"
          >
            {cta.label}
          </PlateButton>
          {cta.mini ? (
            <span className="font-mono text-[10.5px] text-[#7a8f89]">
              {cta.mini}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
