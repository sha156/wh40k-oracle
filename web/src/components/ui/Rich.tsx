import type { RichText } from "@/lib/answer";

interface RichProps {
  text: RichText;
  /** 数值强调样式（各槽位字号/颜色不同，由调用方定） */
  numClass?: string;
  kwClass?: string;
  strongClass?: string;
  /** *斜体*：核心规则页每节紧跟中文标题的英文小节名（*ARMIES*）走这条 */
  emClass?: string;
  citeClass?: string;
}

/** 行内富文本渲染：契约给结构，前端零解析 */
export function Rich({
  text,
  numClass = "font-cond font-bold",
  kwClass = "font-semibold text-cyan-glow",
  strongClass = "font-bold text-gw-red",
  emClass = "italic",
  citeClass = "font-mono text-[10.5px] text-[#7a8f89]",
}: RichProps) {
  return (
    <>
      {text.map((seg, i) => {
        switch (seg.t) {
          case "num":
            return (
              <span key={i} className={numClass}>
                {seg.s}
              </span>
            );
          case "kw":
            return (
              <span key={i} className={kwClass}>
                {seg.s}
              </span>
            );
          case "strong":
            return (
              <b key={i} className={strongClass}>
                {seg.s}
              </b>
            );
          case "em":
            return (
              <em key={i} className={emClass}>
                {seg.s}
              </em>
            );
          case "cite":
            return (
              <span key={i} className={citeClass}>
                {" "}
                [{seg.n}]
              </span>
            );
          default:
            return <span key={i}>{seg.s}</span>;
        }
      })}
    </>
  );
}
