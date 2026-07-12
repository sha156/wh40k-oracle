import type { ReactNode } from "react";

type PanelClip = "plate-10" | "plate-14" | "notch-18" | "none";
type PanelTone = "bone" | "dark";

const CLIP_CLASS: Record<PanelClip, string> = {
  "plate-10": "clip-plate-10",
  "plate-14": "clip-plate-14",
  "notch-18": "clip-notch-18",
  none: "",
};

interface ClipPanelProps {
  children: ReactNode;
  clip?: PanelClip;
  tone?: PanelTone;
  className?: string;
}

/**
 * 切角面板：bone = 骨白纸面（提问卡/判定卡底），dark = 暗色机械面板（trace/calc 底）。
 * 注意 clip-path 会裁掉 box-shadow，阴影由外层容器负责。
 */
export function ClipPanel({
  children,
  clip = "plate-14",
  tone = "bone",
  className = "",
}: ClipPanelProps) {
  const toneCls =
    tone === "bone"
      ? "bg-[linear-gradient(#f0f1ea,var(--color-bone))] text-ink"
      : "border border-panel-line bg-panel text-bone";
  return (
    <div className={`relative ${CLIP_CLASS[clip]} ${toneCls} ${className}`}>
      {children}
    </div>
  );
}
