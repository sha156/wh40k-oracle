import type { ReactNode } from "react";

interface KwBarProps {
  label?: string;
  children: ReactNode; // 关键词内容
  faction?: string; // 右侧阵营铭条
}

/** 兵牌底部关键词条（暗底 + 阵营切角铭条） */
export function KwBar({ label = "关键词:", children, faction }: KwBarProps) {
  return (
    <div className="flex items-center gap-[10px] bg-dark px-[14px] py-[6px] text-[12px] text-[#fefefe] max-tablet:flex-wrap max-tablet:px-[10px] max-tablet:text-[11px]">
      <span className="font-cond text-[11px] tracking-[2px] text-[#8fa8a5] uppercase">
        {label}
      </span>
      {children}
      {faction ? (
        <span className="clip-slant-8 ml-auto bg-tau-ban px-3 py-[2px] font-cond tracking-[1.5px] max-tablet:ml-0">
          {faction}
        </span>
      ) : null}
    </div>
  );
}
