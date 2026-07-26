"use client";

import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/** SSR 时 useLayoutEffect 会告警（服务端没有布局）。浮层只在交互后才开，服务端永远不跑到那 */
const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

import type { KeywordRef } from "@/lib/answer";

/**
 * 一个可查解释的规则词条（兵牌武器行的 USR、技能正文里内嵌的【致命一击】共用它）。
 *
 * 三条不明显但必须这么做的事：
 *
 * 1. **浮层必须 portal 到 body**。武器表在 `overflow-x-auto` 里，绝对定位的浮层
 *    会被那层裁掉——最后一行的词条尤其明显（弹出来只剩一条边）。而外层兵牌带
 *    `@container`（`container-type: inline-size` 会产生 layout containment），
 *    它本身就是 fixed 定位的包含块，所以就地 `position: fixed` 也**不是**视口坐标。
 *    portal 到 body 是这两条约束下唯一不用改版式的解。
 * 2. **不能只做 `:hover`**。触屏没有 hover，键盘用户也够不着。三条通道都开：
 *    鼠标悬停 / 键盘聚焦 / 点击（触屏）钉住，钉住时点别处或按 Esc 关闭。
 * 3. **查不到真源的词条渲染成纯文本**，连按钮都不给——给了按钮却弹出一句
 *    「暂无解释」，只是把数据缺口伪装成功能。
 */

/** 浮层宽度上限；窄屏按视口收窄。跟 GROUP_NOTE 的行长匹配，太宽读起来会串行 */
const TIP_MAX_W = 340;
const GAP = 6;

/** 分档说明。查不到规则正文时**只**说清它为什么查不到，不代打解释 */
const GROUP_NOTE: Record<string, string> = {
  "unit-specific":
    "单位特有词条：11 版通用技能速查表查无此条，规则正文写在该单位自己的兵牌上。",
  universal: "通用词条，但核心规则页未收录该节正文。",
  transitional: "过渡期词条，但核心规则页未收录该节正文。",
};

interface TipPos {
  left: number;
  top: number;
  width: number;
}

function computePos(rect: DOMRect): TipPos {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const width = Math.min(TIP_MAX_W, vw - 16);
  const left = Math.max(8, Math.min(rect.left, vw - width - 8));
  // 下方放不下就翻到上方；两边都不够时仍放下方并由自身滚动条兜底
  const below = vh - rect.bottom;
  const top = below < 160 && rect.top > below ? rect.top - GAP : rect.bottom + GAP;
  return { left, top, width };
}

interface KeywordChipProps {
  kw: KeywordRef;
  /** 上一条与本条之间的分隔符（词条串里的「，」），由调用方给，避免各处各写一套 */
  className?: string;
}

export function KeywordChip({ kw, className }: KeywordChipProps) {
  const tipId = useId();
  const btnRef = useRef<HTMLButtonElement | null>(null);
  const tipRef = useRef<HTMLDivElement | null>(null);
  const [hover, setHover] = useState(false);
  const [focused, setFocused] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [pos, setPos] = useState<TipPos | null>(null);

  // 不需要 mounted 门：三个开关全部只由用户交互置位，服务端渲染里 open 恒为 false，
  // portal 那一支根本不会被求值——加个 mounted 只会在 effect 里同步 setState（lint 也拦）
  const open = hover || focused || pinned;

  const reposition = useCallback(() => {
    const el = btnRef.current;
    if (el) setPos(computePos(el.getBoundingClientRect()));
  }, []);

  // 先量再画，否则浮层会在 (0,0) 闪一帧
  useIsoLayoutEffect(() => {
    if (!open) return;
    reposition();
  }, [open, reposition]);

  useEffect(() => {
    if (!open) return;
    const onScroll = () => reposition();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
    };
  }, [open, reposition]);

  // 钉住后点别处关闭（触屏唯一的关闭手势）
  useEffect(() => {
    if (!pinned) return;
    const onDown = (e: MouseEvent | TouchEvent) => {
      const t = e.target as Node | null;
      if (btnRef.current?.contains(t as Node)) return;
      if (tipRef.current?.contains(t as Node)) return;
      setPinned(false);
    };
    document.addEventListener("pointerdown", onDown as EventListener);
    return () => document.removeEventListener("pointerdown", onDown as EventListener);
  }, [pinned]);

  // 查不到真源：纯文本，不挂任何交互（见文件头第 3 条）
  if (!kw.slug) {
    return <span className={className}>{kw.text}</span>;
  }

  const note = kw.brief ? null : (GROUP_NOTE[kw.group ?? ""] ?? "核心规则页未收录该节正文。");

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        aria-describedby={open ? tipId : undefined}
        aria-expanded={open}
        onPointerEnter={(e) => {
          if (e.pointerType === "mouse") setHover(true);
        }}
        onPointerLeave={(e) => {
          if (e.pointerType === "mouse") setHover(false);
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onClick={() => setPinned((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setPinned(false);
            setFocused(false);
            btnRef.current?.blur();
          }
        }}
        className={`cursor-help border-b border-dotted border-current underline-offset-2 hover:text-tau-ban focus-visible:outline focus-visible:outline-tau-ban ${
          className ?? ""
        }`}
      >
        {kw.text}
      </button>

      {open && pos && typeof document !== "undefined"
        ? createPortal(
            <div
              ref={tipRef}
              id={tipId}
              role="tooltip"
              style={{ left: pos.left, top: pos.top, width: pos.width }}
              className="fixed z-[80] max-h-[52vh] overflow-y-auto border border-tau/70 bg-[#0b1417] px-3 py-2 text-[12.5px] leading-[1.6] text-[#d8e2de] shadow-[0_10px_30px_rgba(0,0,0,.6)]"
            >
              <div className="mb-1 flex flex-wrap items-baseline gap-x-2 border-b border-[#1d3238] pb-1">
                <b className="text-[13.5px] text-bone">{kw.nameZh ?? kw.text}</b>
                <span className="font-cond text-[11.5px] tracking-[1px] text-[#8fa19b] uppercase">
                  {kw.base}
                </span>
                {kw.section ? (
                  <span className="ml-auto font-mono text-[11px] text-gold">
                    {kw.section}
                  </span>
                ) : null}
              </div>
              {kw.brief ? (
                <p className="whitespace-pre-line">{kw.brief}</p>
              ) : (
                <p className="text-[#8fa19b]">{note}</p>
              )}
              {/* 出处必须写明：这段是官方中文规则正文的逐字摘录，不是本站的解释 */}
              {kw.brief ? (
                <p className="mt-1.5 border-t border-[#16211f] pt-1 font-mono text-[10.5px] text-[#5c6f6a]">
                  {kw.section
                    ? `摘自 11 版核心规则 ${kw.section}（GW 官方简体中文）`
                    : "摘自 11 版核心规则（GW 官方简体中文）"}
                </p>
              ) : null}
            </div>,
            document.body,
          )
        : null}
    </>
  );
}

/**
 * 一串词条：`[针对步兵3+，手枪，精准，连击3]`，逐条可悬停。
 *
 * 方括号与分隔符留在这里、不进 KeywordChip：分隔符是**串**的属性不是**条**的属性，
 * 塞进单条组件就得再传一个 isLast，两处各判一次必然有一处判错。
 */
export function KeywordList({ items, className }: { items: KeywordRef[]; className?: string }) {
  if (items.length === 0) return null;
  return (
    <span className={className}>
      [
      {items.map((kw, i) => (
        <span key={`${kw.slug ?? kw.text}-${i}`}>
          {i > 0 ? "，" : null}
          <KeywordChip kw={kw} />
        </span>
      ))}
      ]
    </span>
  );
}
