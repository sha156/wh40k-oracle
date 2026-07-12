import { SlotBadge } from "../ui/SlotBadge";

interface AskCardProps {
  question: string;
  who?: string;
}

/** E2 提问卡：右对齐骨白切角卡 */
export function AskCard({ question, who = "指挥官 · 呈问" }: AskCardProps) {
  return (
    <div className="mb-5 flex justify-end">
      <div className="clip-plate-14 relative max-w-[640px] bg-[linear-gradient(#f0f1ea,var(--color-bone))] px-5 pt-3.5 pb-3 text-ink shadow-[0_4px_18px_rgba(0,0,0,.5)] max-tablet:max-w-full max-tablet:px-3.5 max-tablet:pt-3 max-tablet:pb-2.5">
        <SlotBadge id="E2" onLight />
        <div className="mb-[3px] font-cond text-[11.5px] font-bold tracking-[2.5px] text-gw-red uppercase">
          {who}
        </div>
        <div className="text-[15.5px] font-semibold max-tablet:text-[14.5px]">
          {question}
        </div>
      </div>
    </div>
  );
}
