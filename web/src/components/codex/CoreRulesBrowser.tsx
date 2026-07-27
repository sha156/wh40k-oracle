"use client";

import { useEffect, useMemo, useState } from "react";

import { Blocks } from "@/components/codex/Blocks";
import {
  fetchRuleChapter,
  fetchRuleChapters,
  WikiApiError,
  type CoreRuleChapter,
  type CoreRuleChapterSummary,
} from "@/lib/wiki";

/**
 * 图鉴 · 核心规则页签：24 章目录 → 章节全文（官方简体中文正文 + 每节英文原文折叠）。
 *
 * 正文块由后端从 wiki/core-rules/sections/*.md 编译好下发，这里只排版，不解析 markdown。
 * 导语（intro）必须画出来：里面是「中文由官方 PDF 文本层直提，判定规则以英文原文为准」
 * 这条披露——不画它，这一页看着就是一份官方中文规则定稿，而它其实是直提文本。
 */

/** 503 = wiki/ 卷没挂（部署问题），404 = 查无此章（数据问题）——两种话不一样，混在一起就没人修 */
function apiHint(e: unknown, what: string): string {
  const status = e instanceof WikiApiError ? e.status : 0;
  if (status === 503) {
    return `${what}没取到（503）：后端读不到核心规则产物。它是离线生成物 wiki/core-rules/sections/*.md，容器化部署要确认 wiki/ 只读卷挂上了。`;
  }
  if (status === 404) {
    return `${what}没取到（404）：后端查无此章节。`;
  }
  return `${what}没取到（${e instanceof Error ? e.message : String(e)}）。`;
}

/**
 * 锚点：有官方节号就用节号（"rule-24-core-abilities-24.03"），没有才退回序号。
 *
 * 节号由后端下发（`WikiSection.number`），不在前端从标题里抠——那条规则全仓库只有
 * 一处实现。用它当 id 的理由是**外部要能落点**：词条页「查看正文」跳的就是这个 id，
 * 而序号会随生成器重跑漂移。
 */
function anchorId(slug: string, section: { number: string | null }, i: number): string {
  return `rule-${slug}-${section.number ?? i}`;
}

interface CoreRulesBrowserProps {
  onError?: () => void;
  /**
   * 深链落点：从武器词条页「查看正文」进来时带的章 slug 与节号。
   *
   * 做成 initial* 而不是受控 prop：父页每次跳转都用新 key 重挂本组件（React 里
   * 「按 props 重置内部状态」的正规做法），这样这里不必在 effect 里 setState——
   * eslint 的 react-hooks/set-state-in-effect 也正好拦那种写法。
   */
  initialSlug?: string | null;
  initialSection?: string | null;
}

export function CoreRulesBrowser({
  onError,
  initialSlug = null,
  initialSection = null,
}: CoreRulesBrowserProps) {
  const [chapters, setChapters] = useState<CoreRuleChapterSummary[] | null>(null);
  const [slug, setSlug] = useState<string | null>(initialSlug);
  const [chapter, setChapter] = useState<CoreRuleChapter | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  // 带着深链进来时正文马上就在取：初值给 false 会先闪一下"← 选择左侧章节"
  const [loading, setLoading] = useState(Boolean(initialSlug));

  useEffect(() => {
    const ctrl = new AbortController();
    fetchRuleChapters(ctrl.signal)
      .then((items) => {
        setChapters(items);
        setListError(null);
        setSlug((cur) => {
          if (cur) return cur;
          // 默认选中第一章：loading 在这里开（取数回调里，不是 effect 体内——
          // effect 里同步 setState 会触发级联渲染，lint 也拦）
          if (items[0]) setLoading(true);
          return items[0]?.slug ?? null;
        });
      })
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        setChapters([]);
        setListError(apiHint(e, "章节目录"));
        onError?.();
      });
    return () => ctrl.abort();
  }, [onError]);

  // 选章：从属状态在事件里重置（见上面 setLoading 的注释）
  const pick = (next: string) => {
    if (next === slug) return;
    setChapter(null);
    setDetailError(null);
    setLoading(true);
    setSlug(next);
  };

  useEffect(() => {
    if (!slug) return;
    const ctrl = new AbortController();
    fetchRuleChapter(slug, ctrl.signal)
      .then((c) => setChapter(c))
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        setDetailError(apiHint(e, "章节正文"));
        onError?.();
      })
      .finally(() => {
        // abort 后不要收 loading：这次请求是被下一次选章取代的，
        // 由那一次自己的 setLoading(true) 接管，否则会闪一下"没有内容"
        if (!ctrl.signal.aborted) setLoading(false);
      });
    return () => ctrl.abort();
  }, [slug, onError]);

  // 深链滚动：正文到位后才滚（章节是异步取的，挂载时那个 id 还不存在）。
  // 这里只碰 DOM 不 setState，故不触发级联渲染。滚过一次就够——依赖里带 chapter，
  // 用户随后自己翻章时 initialSection 已经不属于新章，findIndex 落空自然不滚。
  useEffect(() => {
    if (!chapter || !initialSection || chapter.slug !== initialSlug) return;
    const hit = chapter.sections.find((s) => s.number === initialSection);
    if (!hit) return;
    document
      .getElementById(anchorId(chapter.slug, hit, chapter.sections.indexOf(hit)))
      ?.scrollIntoView({ block: "start" });
  }, [chapter, initialSlug, initialSection]);

  const totalSections = useMemo(
    () => (chapters ?? []).reduce((n, c) => n + c.sectionCount, 0),
    [chapters],
  );

  return (
    <div>
      <div className="mb-1.5 flex flex-wrap items-baseline gap-x-3">
        <span className="font-mono text-[11.5px] text-[#8fa19b]">
          {chapters === null
            ? "载入章节目录…"
            : `${chapters.length} 章 · ${totalSections} 节`}
        </span>
      </div>

      {/* 这一页的口径必须写在明面上：正文是官方中文，但它来自 PDF 文本层直提，
          判定以英文为准。折叠里就是对应的英文原文，一节一个 */}
      <p className="mb-3 font-mono text-[11px] text-[#5c6f6a]">
        正文为 GW 官方简体中文（11 版），由官方 PDF 文本层直提，表格与版式会有失真；
        每节可展开对照官方英文原文，判定规则以英文原文为准。
      </p>

      {listError ? (
        <p className="mb-3 border border-redfont/40 bg-[#1a0d0d] px-4 py-3 font-mono text-[12.5px] break-all text-[#d99]">
          {listError}
        </p>
      ) : null}

      <div className="grid grid-cols-[300px_1fr] gap-4 max-wide:grid-cols-1">
        <section className="clip-plate-10 border border-panel-line bg-panel">
          <ul className="max-h-[68vh] overflow-y-auto max-wide:max-h-[34vh]">
            {chapters === null ? (
              <li className="px-3 py-4 font-mono text-[12px] text-sage">载入章节……</li>
            ) : (
              chapters.map((c) => (
                <li key={c.slug}>
                  <button
                    type="button"
                    onClick={() => pick(c.slug)}
                    className={`flex w-full items-baseline gap-2 border-b border-[#1a2624] px-3 py-2 text-left hover:bg-[#14262a] ${
                      c.slug === slug ? "bg-[#16303550]" : ""
                    }`}
                  >
                    <span className="flex-none font-cond text-[12px] tracking-[1px] text-gold">
                      {c.number}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13.5px] text-bone">
                        {c.nameZh}
                      </span>
                      <span className="block truncate font-cond text-[11px] tracking-[1px] text-[#6f827c] uppercase">
                        {c.nameEn}
                      </span>
                    </span>
                    <span className="flex-none font-mono text-[10.5px] text-[#5c6f6a]">
                      {c.sectionCount} 节
                    </span>
                  </button>
                </li>
              ))
            )}
            {chapters !== null && chapters.length === 0 && !listError ? (
              <li className="px-3 py-4 font-mono text-[12px] text-sage">
                后端没有返回任何章节
              </li>
            ) : null}
          </ul>
        </section>

        {/* min-w-0：正文里的表格靠自己的 overflow-x 横滚，栅格子项不收窄会顶得整页横滚 */}
        <section className="min-w-0">
          {detailError ? (
            <div className="border border-redfont/40 bg-[#1a0d0d] px-4 py-6 font-mono text-[12.5px] break-all text-[#d99]">
              {detailError}
            </div>
          ) : loading ? (
            <div className="border border-panel-line bg-panel px-4 py-10 text-center font-mono text-[13px] text-sage">
              载入章节正文……
            </div>
          ) : chapter ? (
            <div className="clip-plate-10 border border-panel-line bg-panel">
              <div className="flex flex-wrap items-baseline gap-x-3 bg-[linear-gradient(var(--color-tau-ban),#0e3b44)] px-3.5 py-2">
                <span className="font-cond text-[13px] tracking-[2px] text-[#e8ddd0]">
                  第 {chapter.number} 章
                </span>
                <span className="font-cond text-[15px] font-bold tracking-[2px] text-white uppercase [text-shadow:0_1px_2px_#000]">
                  {chapter.nameZh}
                </span>
                <span className="font-cond text-[12.5px] tracking-[1px] text-[#cfe3e8] uppercase">
                  {chapter.nameEn}
                </span>
                <span className="ml-auto font-cond text-[12px] tracking-[1px] text-[#e8ddd0]">
                  {chapter.sections.length} 节
                </span>
              </div>

              {/* 导语（含诚实披露），必须显示 */}
              {chapter.intro.length > 0 ? (
                <div className="border-b border-panel-line px-3.5 py-2">
                  <Blocks blocks={chapter.intro} />
                </div>
              ) : null}

              {/* 节号跳转条：第 24 章有 38 节，靠滚动找一节太远。用原生锚点，不接 JS */}
              {chapter.sections.length > 3 ? (
                <div className="flex flex-wrap gap-1 border-b border-panel-line bg-[#0b1315] px-3.5 py-2">
                  {chapter.sections.map((s, i) => (
                    <a
                      key={i}
                      href={`#${anchorId(chapter.slug, s, i)}`}
                      className="border border-[#2b423d] px-1.5 py-[1px] font-mono text-[10.5px] text-[#8fa19b] hover:border-tau hover:text-bone"
                    >
                      {s.title}
                    </a>
                  ))}
                </div>
              ) : null}

              <div className="px-3.5 py-2.5">
                {chapter.sections.map((s, i) => (
                  <section
                    key={i}
                    id={anchorId(chapter.slug, s, i)}
                    className={`mb-4 scroll-mt-4 last:mb-0 ${
                      // 深链进来的那一节高亮一下，否则跳过去只是"页面滚了一段"，
                      // 24 章有 38 节，读者认不出到底该看哪一条
                      initialSection && s.number === initialSection
                        ? "border-l-2 border-gold pl-2"
                        : ""
                    }`}
                  >
                    <h3 className="mb-1 border-b border-[#1d3238] pb-1 font-cond text-[13.5px] tracking-[2px] text-sage uppercase">
                      {s.title}
                    </h3>
                    <Blocks blocks={s.blocks} />
                  </section>
                ))}
              </div>
            </div>
          ) : (
            <div className="border border-dashed border-panel-line bg-[#0d1517] px-4 py-16 text-center font-cond text-[14px] tracking-[1px] text-[#5c6f6a] uppercase">
              ← 选择左侧章节查看全文
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
