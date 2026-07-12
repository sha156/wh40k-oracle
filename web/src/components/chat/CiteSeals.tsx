import type { Cite } from "@/lib/answer";
import { SlotBadge } from "../ui/SlotBadge";
import { WaxSeal } from "../ui/WaxSeal";

interface CiteSealsProps {
  cites: Cite[];
}

/** E7 纯净封蜡引用：羊皮纸撕边卡 + 红蜡编号章 */
export function CiteSeals({ cites }: CiteSealsProps) {
  return (
    <div className="relative mb-[18px] grid grid-cols-3 gap-3 max-wide:grid-cols-1">
      <SlotBadge id="E7" className="-top-4" />
      {cites.map((c) => (
        <div
          key={c.n}
          className="clip-parchment relative min-h-[74px] bg-[linear-gradient(#efe9d6,#e6dec5)] py-3 pr-3.5 pb-2.5 pl-[52px] text-ink shadow-[0_4px_14px_rgba(0,0,0,.45)] max-tablet:min-h-0 max-tablet:py-2.5 max-tablet:pr-3 max-tablet:pl-12"
        >
          <WaxSeal className="absolute top-3 left-2.5">{c.n}</WaxSeal>
          <div className="text-[12.8px] leading-normal font-bold">
            {c.book}
            {c.section ? <> {c.section} ·</> : null}{" "}
            <span className="font-cond text-[12.5px] font-bold text-redfont">
              {c.page !== undefined ? `p.${c.page}` : c.term}
            </span>
          </div>
          <a
            className="mt-[3px] block font-mono text-[10.5px] break-all text-[#6b6046] underline decoration-dotted"
            href="#"
          >
            {c.wiki}
          </a>
        </div>
      ))}
    </div>
  );
}
