import Link from "next/link";
import { SlotBadge } from "../ui/SlotBadge";
import { Aquila } from "./Aquila";

const NAV_ITEMS = [
  { label: "聊天", href: "/", ready: true },
  { label: "模拟器", href: "/simulator", ready: true },
  { label: "军表实验室", href: "#", ready: false },
  { label: "图鉴", href: "/codex", ready: true },
];

interface SiteHeaderProps {
  context: string; // 当前语境铭牌文字
  active?: string; // 当前激活页签 label，默认「聊天」
}

/** E1 顶栏：品牌 + 语境铭牌 + 页签导航 */
export function SiteHeader({ context, active = "聊天" }: SiteHeaderProps) {
  return (
    <header className="relative border-b-2 border-gw-red bg-[linear-gradient(#141b1e,var(--color-ink))] shadow-[0_0_0_1px_#000,0_6px_24px_rgba(0,0,0,.6)]">
      <SlotBadge id="E1" />
      <div className="mx-auto flex max-w-[1100px] items-center gap-4 px-5 pt-3.5 pb-2.5 max-tablet:flex-wrap max-tablet:gap-[10px] max-tablet:px-3 max-tablet:pt-2.5 max-tablet:pb-2">
        <Aquila className="flex-none drop-shadow-[0_1px_2px_#000] max-tablet:h-[26px] max-tablet:w-[56px]" />
        <div className="flex flex-col">
          <span className="font-cond text-[24px] leading-[1.15] font-bold tracking-[3px] text-bone uppercase max-tablet:text-[18px] max-tablet:tracking-[2px]">
            40K <em className="text-redfont not-italic">规则专家</em>
          </span>
          <span className="font-cond text-[11.5px] tracking-[4px] text-[#7d8a86] uppercase max-tablet:text-[9.5px] max-tablet:tracking-[2.5px]">
            Warhammer 40K Rules Copilot
          </span>
        </div>
        <div className="clip-plate-10 ml-auto flex items-center gap-2 bg-[linear-gradient(100deg,var(--color-tau-ban),#0e3b44)] px-4 py-[7px] font-cond text-[13px] tracking-[1px] text-[#d9e6e4] max-tablet:ml-0 max-tablet:w-full max-tablet:justify-center max-tablet:px-2.5 max-tablet:py-[5px] max-tablet:text-[12px]">
          <span className="h-2 w-2 rounded-full bg-[#4fb7c9] shadow-[0_0_6px_#4fb7c9]" />
          {context}
        </div>
      </div>
      <nav className="mx-auto flex max-w-[1100px] gap-1 px-5 max-tablet:scrollbar-none max-tablet:overflow-x-auto max-tablet:px-2">
        {NAV_ITEMS.map((item) => {
          const isActive = item.label === active;
          const cls = `clip-slant-8 px-[22px] pt-2 pb-[9px] font-cond text-[14px] tracking-[2px] uppercase no-underline max-tablet:px-3.5 max-tablet:text-[13px] max-tablet:tracking-[1px] max-tablet:whitespace-nowrap ${
            isActive
              ? "bg-[linear-gradient(var(--color-gw-red),#6e0505)] text-white [text-shadow:0_1px_2px_#000]"
              : item.ready
                ? "bg-[#16211f] text-[#97a4a0] hover:bg-[#1d2b28] hover:text-bone"
                : "cursor-not-allowed bg-[#12191a] text-[#4d5854]"
          }`;
          return item.ready ? (
            <Link key={item.label} href={item.href} className={cls}>
              {item.label}
            </Link>
          ) : (
            <span key={item.label} className={cls} title="建设中（等后端页签解锁）">
              {item.label}
            </span>
          );
        })}
      </nav>
    </header>
  );
}
