"use client";

import { useEffect, useState } from "react";

import { Blocks, SectionList } from "@/components/codex/Blocks";
import {
  fetchChangelog,
  fetchChangelogFaction,
  WikiApiError,
  type ChangelogFactionPage,
  type ChangelogFactionSummary,
  type ChangelogIndex,
} from "@/lib/wiki";

/**
 * 图鉴 · 规则变更清单页签：28 个阵营包的官方「规则更新」章节 + 通用规则更新。
 *
 * 两条口径必须写在页面上，不然这页很容易被读成"11 版全部改动"：
 *   · 只收官方**自己列出**的文字改动（逐条照抄，不作推断）；
 *   · 🆕 = v1.1 增量，判据是官方 PDF 的**红色高亮**，不是 diff 两版猜的（手上只有 v1.1）。
 * 后端下发的 intro / noteSections 里就是这两条，照实渲染即可。
 */

/**
 * 条目标题里的 🆕 是**数据**（生成器按官方红色高亮打的标记），照抄渲染。
 * 但界面自己的徽标/统计不拿 emoji 当图标（本项目 UI 约定），一律用「新增」二字：
 * 暗面板上的 emoji 还常因字体回退变成灰底方块，反倒不如文字清楚。
 */
const NEW_LABEL = "新增";

function apiHint(e: unknown, what: string): string {
  const status = e instanceof WikiApiError ? e.status : 0;
  if (status === 503) {
    return `${what}没取到（503）：后端读不到变更清单，或清单与阵营页对不上账（后端日志里有点名）。它是离线生成物 wiki/changelog/，容器化部署要确认 wiki/ 只读卷挂上了。`;
  }
  if (status === 404) {
    return `${what}没取到（404）：后端查无此阵营包。`;
  }
  return `${what}没取到（${e instanceof Error ? e.message : String(e)}）。`;
}

/** 增量数量标：0 条时不画（画个灰色的 0 只会让人以为它没加载出来） */
function NewTag({ n }: { n: number }) {
  if (n <= 0) return null;
  return (
    <span
      className="clip-slant-8 flex-none border border-gold/50 bg-[#171509] px-1.5 py-[1px] font-cond text-[11px] tracking-[1px] text-gold"
      title="官方红色高亮标出的修订：阵营包初版发布之后新增（页面上标 🆕）"
    >
      {NEW_LABEL} {n}
    </span>
  );
}

function FactionRow({
  f,
  active,
  onPick,
}: {
  f: ChangelogFactionSummary;
  active: boolean;
  onPick: (slug: string) => void;
}) {
  // slug 为 null = 真没有明细页（首版无更新章节 / 官方本次未列改动）。
  // 画成不可点的一行并把原因写出来，不造一个空页面让人点进去看「0 条改动」
  const body = (
    <>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13.5px] text-bone">{f.name}</span>
        <span className="block truncate font-mono text-[10.5px] text-[#6f827c]">
          {f.slug === null ? f.detail : `${f.version} · ${f.total} 条`}
        </span>
      </span>
      <NewTag n={f.newCount} />
      {f.slug === null ? null : (
        <span className="flex-none font-cond text-[12px] text-[#8fa19b]">{f.total}</span>
      )}
    </>
  );
  if (f.slug === null) {
    return (
      <li className="flex items-baseline gap-2 border-b border-[#1a2624] px-3 py-2 opacity-60">
        {body}
      </li>
    );
  }
  const slug = f.slug;
  return (
    <li>
      <button
        type="button"
        onClick={() => onPick(slug)}
        className={`flex w-full items-baseline gap-2 border-b border-[#1a2624] px-3 py-2 text-left hover:bg-[#14262a] ${
          active ? "bg-[#16303550]" : ""
        }`}
      >
        {body}
      </button>
    </li>
  );
}

export function ChangelogBrowser({ onError }: { onError?: () => void }) {
  const [index, setIndex] = useState<ChangelogIndex | null>(null);
  const [slug, setSlug] = useState<string | null>(null);
  const [page, setPage] = useState<ChangelogFactionPage | null>(null);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchChangelog(ctrl.signal)
      .then((d) => {
        setIndex(d);
        setIndexError(null);
      })
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        setIndexError(apiHint(e, "变更清单"));
        onError?.();
      });
    return () => ctrl.abort();
  }, [onError]);

  /** 选阵营包：从属状态在事件里重置，不在 effect 体内同步 setState（会级联渲染，lint 也拦） */
  const pick = (next: string) => {
    if (next === slug) return;
    setPage(null);
    setPageError(null);
    setLoading(true);
    setSlug(next);
  };

  useEffect(() => {
    if (!slug) return;
    const ctrl = new AbortController();
    fetchChangelogFaction(slug, ctrl.signal)
      .then((p) => setPage(p))
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        setPageError(apiHint(e, "阵营包明细"));
        onError?.();
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false);
      });
    return () => ctrl.abort();
  }, [slug, onError]);

  return (
    <div>
      <div className="mb-1.5 flex flex-wrap items-baseline gap-x-3 font-mono text-[11.5px] text-[#8fa19b]">
        {index === null ? (
          <span>载入变更清单…</span>
        ) : (
          <>
            <span>
              阵营改动{" "}
              <b className="font-cond text-[13px] text-bone">{index.total}</b> 条
              <span className="text-[#5c6f6a]">（{index.factions.length} 个阵营包）</span>
            </span>
            <span title="判据是官方 PDF 的红色高亮，不是比对两个版本猜的">
              其中{NEW_LABEL}
              <b className="mx-1 font-cond text-[13px] text-gold">{index.newCount}</b>条
            </span>
          </>
        )}
      </div>

      {indexError ? (
        <p className="mb-3 border border-redfont/40 bg-[#1a0d0d] px-4 py-3 font-mono text-[12.5px] break-all text-[#d99]">
          {indexError}
        </p>
      ) : null}

      {/* 导语 + 口径说明（本页只收官方文字改动；数值漂移是另一条线）。
          后端把它们分成 intro / noteSections 下发，都要画——这是这一页的诚实披露 */}
      {index !== null ? (
        <div className="mb-3 border border-panel-line bg-[#0b1315] px-3.5 py-2">
          <Blocks blocks={index.intro} />
          {index.noteSections.length > 0 ? <SectionList sections={index.noteSections} /> : null}
        </div>
      ) : null}

      <div className="grid grid-cols-[300px_1fr] gap-4 max-wide:grid-cols-1">
        <section className="clip-plate-10 border border-panel-line bg-panel">
          <ul className="max-h-[68vh] overflow-y-auto max-wide:max-h-[34vh]">
            {index === null ? (
              <li className="px-3 py-4 font-mono text-[12px] text-sage">载入阵营包……</li>
            ) : (
              index.factions.map((f) => (
                <FactionRow
                  key={f.slug ?? f.name}
                  f={f}
                  active={f.slug === slug}
                  onPick={pick}
                />
              ))
            )}
          </ul>
        </section>

        <section className="min-w-0">
          {pageError ? (
            <div className="border border-redfont/40 bg-[#1a0d0d] px-4 py-6 font-mono text-[12.5px] break-all text-[#d99]">
              {pageError}
            </div>
          ) : loading ? (
            <div className="border border-panel-line bg-panel px-4 py-10 text-center font-mono text-[13px] text-sage">
              载入阵营包明细……
            </div>
          ) : page ? (
            <div className="clip-plate-10 border border-panel-line bg-panel">
              <div className="flex flex-wrap items-baseline gap-x-3 bg-[linear-gradient(var(--color-tau-ban),#0e3b44)] px-3.5 py-2">
                <span className="font-cond text-[15px] font-bold tracking-[2px] text-white uppercase [text-shadow:0_1px_2px_#000]">
                  {page.nameZh}
                </span>
                <span className="font-cond text-[12.5px] tracking-[1px] text-[#cfe3e8] uppercase">
                  {page.nameEn}
                </span>
                <span className="ml-auto font-cond text-[12px] tracking-[1px] text-[#e8ddd0]">
                  {page.version}
                </span>
              </div>
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-panel-line px-3.5 py-1.5 font-mono text-[11.5px] text-[#8fa19b]">
                <span>
                  改动 <b className="font-cond text-[13px] text-bone">{page.total}</b> 条
                </span>
                <span title="判据是官方 PDF 的红色高亮，不是比对两个版本猜的">
                  {NEW_LABEL}
                  <b className="mx-1 font-cond text-[13px] text-gold">{page.newCount}</b>条
                </span>
              </div>
              {page.intro.length > 0 ? (
                <div className="border-b border-panel-line px-3.5 py-2">
                  <Blocks blocks={page.intro} />
                </div>
              ) : null}
              <div className="px-3.5 py-2.5">
                <SectionList
                  sections={page.sections}
                  emptyHint="本阵营包没有「规则更新」章节（原因见上方说明）"
                />
              </div>
            </div>
          ) : (
            <div className="border border-dashed border-panel-line bg-[#0d1517] px-4 py-16 text-center font-cond text-[14px] tracking-[1px] text-[#5c6f6a] uppercase">
              ← 选择左侧阵营包查看官方改动明细
            </div>
          )}
        </section>
      </div>

      {/* 通用规则更新放在最后：它跨全部阵营生效，与上面某个阵营包的明细不是一回事 */}
      {index !== null && index.generalSections.length > 0 ? (
        <div className="mt-4 clip-plate-10 border border-panel-line bg-panel px-3.5 py-2.5">
          <SectionList sections={index.generalSections} />
        </div>
      ) : null}
    </div>
  );
}
