"use client";

import { useRef, useState } from "react";
import { SlotBadge } from "../ui/SlotBadge";

interface ComposerProps {
  followups: string[];
  placeholder?: string;
}

/** E9 输入区：追问 chips + 提问输入 + 发送（静态版仅本地状态，不发请求） */
export function Composer({
  followups,
  placeholder = "问规则、查单位、判对局……支持中文/英文/俗名",
}: ComposerProps) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const pickChip = (chip: string) => {
    setValue(chip);
    inputRef.current?.focus();
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-20 bg-[linear-gradient(transparent,rgba(6,10,12,.88)_26%,#060a0c_70%)] px-5 pt-[26px] pb-3 max-tablet:px-2.5 max-tablet:pt-[18px] max-tablet:pb-2.5">
      <div className="relative mx-auto max-w-[1100px]">
        <SlotBadge id="E9" className="top-0.5" />
        <div className="mb-2 flex flex-wrap gap-2 max-tablet:scrollbar-none max-tablet:flex-nowrap max-tablet:overflow-x-auto max-tablet:pb-0.5">
          {followups.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => pickChip(chip)}
              className="clip-slant-8 cursor-pointer border border-[#2b423d] bg-[#101b1e] px-4 py-1 text-[12.5px] text-[#a9bcb6] hover:border-tau hover:bg-[#14262a] hover:text-bone max-tablet:flex-none max-tablet:whitespace-nowrap"
            >
              {chip}
            </button>
          ))}
        </div>
        <form className="flex" onSubmit={(e) => e.preventDefault()}>
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
            className="flex-1 border border-[#2b423d] border-r-0 bg-panel px-4 py-3 font-body text-[14px] text-bone outline-none placeholder:text-[#5c6f6a] focus:border-tau focus:shadow-[0_0_0_1px_var(--color-tau-ban)] max-tablet:px-3 max-tablet:py-[11px] max-tablet:text-[16px]"
          />
          {/* 手机端 16px 防 iOS 聚焦缩放 */}
          <button
            type="submit"
            className="clip-slant-l-12 cursor-pointer border-0 bg-[linear-gradient(var(--color-gw-red),#6e0505)] px-[34px] font-cond text-[14px] tracking-[3px] text-white uppercase transition-[filter] duration-150 hover:brightness-125 max-tablet:px-[22px] max-tablet:tracking-[2px]"
          >
            发 送
          </button>
        </form>
        <div className="mt-2 text-center font-mono text-[10.5px] tracking-[.5px] text-[#57655f] max-tablet:text-[9.5px]">
          回答由 LLM 基于本地规则库生成
          <span className="mx-2 text-redfont">☠</span>
          引用页码可溯源
          <span className="mx-2 text-redfont">☠</span>
          模拟为期望值/蒙特卡洛估算
        </div>
      </div>
    </div>
  );
}
