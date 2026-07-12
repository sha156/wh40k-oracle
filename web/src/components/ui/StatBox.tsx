interface StatBoxProps {
  lab: string; // M / T / SV / W / LD / OC
  val: string;
}

/** 官方切角属性格（Wahapedia dsCharFrame） */
export function StatBox({ lab, val }: StatBoxProps) {
  return (
    <div className="flex flex-col items-center gap-[3px]">
      <span className="font-cond text-[12px] font-bold tracking-[1px] text-[#d5e4e2]">
        {lab}
      </span>
      <span className="clip-statbox flex h-[42px] w-[46px] items-center justify-center bg-bone font-cond text-[19px] font-bold text-ink shadow-[inset_0_0_0_2px_#35555d] max-tablet:h-[38px] max-tablet:w-[42px] max-tablet:text-[17px]">
        {val}
      </span>
    </div>
  );
}
