interface SlotBadgeProps {
  id: string; // E1–E9 功能槽位编号，用户按编号反馈
  onLight?: boolean; // 亮底卡片上用深色角标
  className?: string;
}

/** 槽位角标：设计反馈期保留，手机上隐藏让位内容 */
export function SlotBadge({ id, onLight = false, className = "" }: SlotBadgeProps) {
  return (
    <span
      className={`pointer-events-none absolute top-1 right-1.5 z-[5] rounded-[2px] border px-1 py-px font-mono text-[10px] leading-none max-tablet:hidden ${
        onLight
          ? "border-ink/20 text-ink/40"
          : "border-bone/20 text-bone/40"
      } ${className}`}
    >
      {id}
    </span>
  );
}
