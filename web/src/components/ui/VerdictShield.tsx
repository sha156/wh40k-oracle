interface VerdictShieldProps {
  label: string; // 盾章大字，如「值得带」
  sub?: string; // 盾章小字，如 Sanctioned
}

/** 判定盾章（Wahapedia 盾形坐标，下 40% 收尖） */
export function VerdictShield({ label, sub }: VerdictShieldProps) {
  return (
    <div className="clip-shield flex h-[104px] w-[92px] flex-col items-center justify-center bg-[linear-gradient(160deg,#c11616,var(--color-gw-red)_55%,#5c0303)] pb-[30px] text-white [text-shadow:0_1px_2px_rgba(0,0,0,.55)] max-tablet:h-[86px] max-tablet:w-[76px]">
      {/* pb-30px：盾形下收尖，内容整体上移防裁切 */}
      <span className="font-body text-[26px] font-extrabold tracking-[2px] max-tablet:text-[21px]">
        {label}
      </span>
      {sub ? (
        <span className="font-cond text-[10px] tracking-[3px] uppercase opacity-85">
          {sub}
        </span>
      ) : null}
    </div>
  );
}
