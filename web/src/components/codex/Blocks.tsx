import { Rich } from "@/components/ui/Rich";
import type { Inline } from "@/lib/answer";
import type { WikiBlock, WikiSection } from "@/lib/wiki";

/**
 * wiki 正文的块级渲染器：后端已把 markdown 编译成 WikiBlock，这里只负责映射到标签。
 * 前端不引 markdown 库（运行时依赖只有 next/react/@fontsource），也不再做二次解析。
 */

/* wiki 正文里的 **加粗** 是普通强调（最常见的是「**分数**：20 分」），不是判定结论——
   用 Rich 默认的 GW 红（#990000）压在暗面板上既糊又像报警，改成骨白加粗 */
const STRONG_CLASS = "font-bold text-bone";

/* *斜体* 在 wiki 正文里几乎只有一种用法：核心规则每节紧跟中文标题的英文小节名
   （`*ARMIES*`，实测 165 处里 164 处是整行）。全站的英文副名都是窄体 sage 不斜
   （单位列表、分队列表都这么画），这里跟着走——全大写的窄体斜体在暗面板上很难读 */
const EM_CLASS = "font-cond tracking-[1px] text-sage not-italic";

function InlineRow({ inline }: { inline: Inline[] }) {
  return <Rich text={inline} strongClass={STRONG_CLASS} emClass={EM_CLASS} />;
}

function TableBlock({ head, rows }: { head: string[]; rows: string[][] }) {
  // 后端为对齐列数会把表头补成 ["", ""]（源表本就没有表头行，如机械修会
  // Haloscreed 的档位表）。这时候画 thead 就是一条空白横条，看着像渲染坏了——
  // 有字才画。判「有没有字」而不是 head.length：长度只说明列数补齐了
  const hasHead = head.some((h) => h.trim() !== "");
  return (
    // 表格自带横滚容器：分队规则里的「战斗规模 → 可选单位数」档位表在窄屏放不下，
    // 不给它自己的 overflow 就会顶得整页横滚（页面本体不许横滚）
    <div className="my-2 overflow-x-auto border border-[#1d3238]">
      <table className="w-full border-collapse text-[12.5px]">
        {hasHead ? (
          <thead>
            <tr className="bg-[#101b1e]">
              {head.map((h, i) => (
                <th
                  key={i}
                  className="border-b border-[#1d3238] px-2.5 py-1 text-left font-cond text-[11px] tracking-[1px] whitespace-nowrap text-sage uppercase"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
        ) : null}
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-[#1a2624] last:border-b-0 odd:bg-[#0d1517]">
              {r.map((c, j) => (
                <td key={j} className="px-2.5 py-1 align-top text-[#c7d2cd]">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BlockView({ block }: { block: WikiBlock }) {
  switch (block.t) {
    case "p":
      return (
        <p className="my-1.5 text-[13px] leading-[1.85] text-[#c7d2cd]">
          <InlineRow inline={block.inline} />
        </p>
      );
    case "ul":
      return (
        <ul className="my-1.5 list-disc pl-5 text-[13px] leading-[1.8] text-[#c7d2cd] marker:text-[#4d5854]">
          {block.items.map((it, i) => (
            <li key={i}>
              <InlineRow inline={it} />
            </li>
          ))}
        </ul>
      );
    case "ol":
      return (
        <ol className="my-1.5 list-decimal pl-5 text-[13px] leading-[1.8] text-[#c7d2cd] marker:text-[#4d5854]">
          {block.items.map((it, i) => (
            <li key={i}>
              <InlineRow inline={it} />
            </li>
          ))}
        </ol>
      );
    case "table":
      return <TableBlock head={block.head} rows={block.rows} />;
    case "details":
      return (
        // 折叠默认收起：核心规则页每节都挂一个英文原文，全展开会让中文正文被英文冲淡一倍。
        // summary 原样显示——它是页面上唯一能看出英文来源的地方（14 节写的是
        //「官方英文原文（英文由 PDF 直提）」，那是 refine 丢了节号、改用英文 PDF 兜底的）
        <details className="my-2 border border-[#1d3238] bg-[#0b1315]">
          <summary className="cursor-pointer px-2.5 py-1.5 font-cond text-[11.5px] tracking-[1.5px] text-sage uppercase select-none hover:text-bone">
            {block.summary || "展开"}
          </summary>
          <div className="border-t border-[#1d3238] px-2.5 py-1">
            <Blocks blocks={block.blocks} />
          </div>
        </details>
      );
    case "h": {
      // 契约承诺 2/3/4 三级（折叠里的英文原文自带 `## ` 标题）；越界值夹回 h4，
      // 别让后端某天多给一级就渲出非法标签
      const Tag = block.level <= 3 ? "h3" : "h4";
      const size = block.level <= 3 ? "text-[13.5px] text-bone" : "text-[12.5px] text-[#a9bcb6]";
      return (
        <Tag className={`mt-2.5 mb-1 font-cond tracking-[1.5px] uppercase ${size}`}>
          {block.text}
        </Tag>
      );
    }
    case "quote":
      return (
        <blockquote className="my-2 border-l-2 border-gold/50 bg-[#0f191c] px-3 py-1.5 text-[12.5px] leading-[1.8] text-[#a9bcb6]">
          <InlineRow inline={block.inline} />
        </blockquote>
      );
    default:
      // 契约新增块类型时宁可少渲一块，也不要整页崩在用户脸上
      return null;
  }
}

export function Blocks({ blocks }: { blocks: WikiBlock[] }) {
  return (
    <>
      {blocks.map((b, i) => (
        <BlockView key={i} block={b} />
      ))}
    </>
  );
}

interface SectionListProps {
  sections: WikiSection[];
  /** compact=战略/增强条目内的四段正文（标题当小标签）；否则=分队规则那种独立小节 */
  compact?: boolean;
  /** 无正文时的兜底话术：区分「源里没有」与「没取到」，由调用方给 */
  emptyHint?: string;
}

export function SectionList({ sections, compact = false, emptyHint }: SectionListProps) {
  if (sections.length === 0) {
    return emptyHint ? (
      <p className="my-1.5 font-mono text-[11.5px] text-[#5c6f6a]">{emptyHint}</p>
    ) : null;
  }
  // 小节标题在页面层级里：分队规则那种是 h3（与「增强」「战略」分组同级），
  // 战略条目内的四段是 h4（挂在分组之下）
  const Tag = compact ? "h4" : "h3";
  return (
    <>
      {sections.map((s, i) => (
        <section key={i} className={compact ? "mb-1.5 last:mb-0" : "mb-3 last:mb-0"}>
          <Tag
            className={
              compact
                ? "font-cond text-[11px] tracking-[1.5px] text-gold uppercase"
                : "mb-1 border-b border-[#1d3238] pb-1 font-cond text-[13px] tracking-[2px] text-sage uppercase"
            }
          >
            {s.title}
          </Tag>
          <Blocks blocks={s.blocks} />
        </section>
      ))}
    </>
  );
}
