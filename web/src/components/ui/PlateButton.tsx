import type { ReactNode } from "react";

type PlateClip = "slant-14" | "slant-l-12" | "slant-8";

const CLIP_CLASS: Record<PlateClip, string> = {
  "slant-14": "clip-slant-14",
  "slant-l-12": "clip-slant-l-12",
  "slant-8": "clip-slant-8",
};

interface PlateButtonProps {
  children: ReactNode;
  href?: string;
  clip?: PlateClip;
  type?: "button" | "submit";
  className?: string;
}

/** 切角红铭牌按钮（GW 红渐变 + 官方切角） */
export function PlateButton({
  children,
  href,
  clip = "slant-14",
  type = "button",
  className = "",
}: PlateButtonProps) {
  const cls = `${CLIP_CLASS[clip]} inline-block cursor-pointer border-0 bg-[linear-gradient(var(--color-gw-red),#6e0505)] font-cond tracking-[2px] text-white uppercase transition-[filter] duration-150 hover:brightness-125 ${className}`;
  if (href !== undefined) {
    return (
      <a href={href} className={cls}>
        {children}
      </a>
    );
  }
  return (
    <button type={type} className={cls}>
      {children}
    </button>
  );
}
