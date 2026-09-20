interface VerdictShieldProps {
  label: string; // 盾章大字，如「值得带」
  sub?: string; // 盾章小字，如 Sanctioned
}

/** 判定盾章（Wahapedia 盾形坐标，下 40% 收尖） */
export function VerdictShield({ label, sub }: VerdictShieldProps) {
  return (
    <div className="clip-shield flex h-[104px] w-[92px] flex-col items-center justify-center bg-[linear-gradient(160deg,#c11616,var(--color-gw-red)_55%,#5c0303)] pb-[30px] text-white [text-shadow:0_1px_2px_rgba(0,0,0,.55)] max-tablet:h-[86px] max-tablet:w-[76px]">
      {/* pb-30px：盾形下收尖，内容整体上移防裁切 */}
      <span className={`px-1 text-center font-body font-extrabold leading-tight ${Array.from(label).length > 3 ? "text-[18px] tracking-normal max-tablet:text-[15px]" : "text-[26px] tracking-[2px] max-tablet:text-[21px]"}`}>
        {label}
      </span>
      {sub ? (
        <span className="mt-1 max-w-full px-1 text-center font-cond text-[9px] leading-tight tracking-[0.5px] uppercase opacity-85 max-tablet:text-[8px]">
          {sub}
        </span>
      ) : null}
    </div>
  );
}
