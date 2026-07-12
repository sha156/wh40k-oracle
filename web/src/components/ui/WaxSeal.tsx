import type { ReactNode } from "react";

interface WaxSealProps {
  children: ReactNode; // 通常是引用编号
  className?: string;
}

/** 封蜡章：引用编号的红蜡圆章 */
export function WaxSeal({ children, className = "" }: WaxSealProps) {
  return (
    <div
      className={`flex h-8 w-8 items-center justify-center rounded-full bg-[radial-gradient(circle_at_35%_30%,#d33a3a,var(--color-gw-red)_60%,#4d0202)] font-cond text-[14px] font-bold text-[#ffd9d9] shadow-[0_2px_5px_rgba(0,0,0,.5),inset_0_0_0_3px_rgba(255,255,255,.12)] ${className}`}
    >
      {children}
    </div>
  );
}
