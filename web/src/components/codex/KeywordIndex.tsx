"use client";

import { useEffect, useMemo, useState } from "react";

import {
  fetchKeywordDetail,
  fetchKeywords,
  type KeywordDetail,
  type KeywordGroup,
  type KeywordSummary,
  type KeywordWeapon,
} from "@/lib/keywords";

/** 三组分区的顺序与口径说明：只讲词条从哪来，规则正文留给后续的规则页 PR */
const GROUPS: ReadonlyArray<{ id: KeywordGroup; title: string; note: string }> = [
  {
    id: "universal",
    title: "通用词条",
    note: "11 版《核心规则》武器词条速查表在册：哪张兵牌印上它，都按同一条规则结算。",
  },
  {
    id: "transitional",
    title: "过渡期",
    note: "官方 11 版仍在册、但正被取代：[手枪]（24.27）与[近距离]（24.07）规则完全等同，官方注明手枪会随本版演进被取代——读到它按[近距离]理解，但它不是作废条目。",
  },
  {
    id: "unit-specific",
    title: "单位特有",
    note: "只长在某个单位的武器上，规则正文写在该单位自己的兵牌里，速查表查不到。",
  },
];

/** engine 是离线算好的字符串（非枚举），未知取值走兜底灰而不是崩掉 */
const ENGINE_STYLE: Record<string, string> = {
  数值建模: "border-tau/60 bg-[#0d2a30] text-cyan-glow",
  仅标注: "border-gold/40 bg-[#171509] text-gold",
  未纳入: "border-[#2b423d] bg-[#101b1e] text-[#7d8a86]",
};
const ENGINE_FALLBACK = "border-[#2b423d] bg-[#101b1e] text-[#7d8a86]";

/** 表头与数据行共用同一份列宽——各写一份必然对不齐 */
const COLS =
  "grid grid-cols-[minmax(0,1.15fr)_minmax(0,1.15fr)_54px_minmax(0,1.35fr)_104px_82px] items-center gap-2 px-3";

/**
 * 载荷里的档位是字符串序，"10" 会插进 "1" 和 "2" 中间（速射尤其明显）——
 * 展示前按数值排，D3/D6+3 这类非纯数字排到最后。
 */
function sortParams(params: string[]): string[] {
  const num = (p: string) => Number(p.replace(/\+$/, ""));
  return [...params].sort((a, b) => {
    const na = num(a);
    const nb = num(b);
    const aNum = Number.isFinite(na);
    const bNum = Number.isFinite(nb);
    if (aNum && bNum) return na - nb;
    if (aNum !== bNum) return aNum ? -1 : 1;
    return a.localeCompare(b);
  });
}

/** 携带单位多于 1 个时只报头一个 + 总数，全名单进 title（98 个单位平铺会撑爆行） */
function unitsLabel(units: string[]): string {
  if (units.length === 0) return "—";
  if (units.length === 1) return units[0];
  return `${units[0]} 等 ${units.length} 个单位`;
}

function unitsTitle(units: string[]): string {
  const head = units.slice(0, 30).join("、");
  return units.length > 30 ? `${head}… 共 ${units.length} 个单位` : head;
}

function EngineTag({ engine }: { engine: string }) {
  return (
    <span
      className={`clip-slant-8 inline-block border px-2 py-[1px] text-center font-cond text-[11px] tracking-[1px] ${
        ENGINE_STYLE[engine] ?? ENGINE_FALLBACK
      }`}
    >
      {engine}
    </span>
  );
}

interface DetailBodyProps {
  summary: KeywordSummary;
  detail: KeywordDetail | null;
}

/** 展开区：反查清单（武器 —— 携带单位）+ 规则页标记 */
function DetailBody({ summary, detail }: DetailBodyProps) {
  if (!detail) {
    return (
      <p className="border-t border-panel-line bg-[#0a1214] px-3 py-2 font-mono text-[11.5px] text-sage">
        载入反查清单…
      </p>
    );
  }
  const weapons: KeywordWeapon[] = detail.weapons;
  return (
    <div className="border-t border-panel-line bg-[#0a1214] px-3 py-2.5">
      <div className="mb-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 font-mono text-[11.5px] text-[#8fa19b]">
        <span>
          现役武器{" "}
          <b className="font-cond text-[13px] text-bone">{detail.currentWeapons}</b>
          <span className="text-[#5c6f6a]">（全库 {detail.totalWeapons}）</span>
        </span>
        <span>
          现役单位{" "}
          <b className="font-cond text-[13px] text-bone">{detail.currentUnits}</b>
          <span className="text-[#5c6f6a]">（全库 {detail.totalUnits}）</span>
        </span>
        {/* 规则正文页在后续 PR 才做，这里只给路径文本——做成链接就是个 404。
            没挂页时只对单位特有词条解释去处（通用词条缺页是数据缺口，不替它编理由） */}
        <span className="text-[#5c6f6a]">
          {detail.rulePage
            ? `规则页 ${detail.rulePage} · 正文页待上线`
            : summary.group === "unit-specific"
              ? "未挂规则页（规则正文写在该单位兵牌上）"
              : "未挂规则页"}
        </span>
      </div>

      {weapons.length === 0 ? (
        <p className="font-mono text-[11.5px] text-[#7d8a86]">
          现役单位里查不到携带此词条的武器
          {detail.totalWeapons > 0
            ? `（全库另有 ${detail.totalWeapons} 件，不在现役口径内）`
            : ""}
        </p>
      ) : (
        <div className="max-h-[320px] overflow-y-auto border border-[#16211f]">
          {weapons.map((w) => (
            <div
              key={w.name}
              className="flex items-baseline justify-between gap-3 border-b border-[#16211f] px-2.5 py-[3px] last:border-b-0 odd:bg-[#0d1517]"
            >
              <span className="min-w-0 flex-1 truncate text-[12.5px] text-bone">
                {w.name}
              </span>
              <span
                className="min-w-0 flex-1 truncate text-right text-[12px] text-[#8fa19b]"
                title={unitsTitle(w.units)}
              >
                {unitsLabel(w.units)}
              </span>
            </div>
          ))}
        </div>
      )}
      {/* 说清列的是什么口径：不写的话「148 件」会被当成全库数，而全库是 158。
          单位数也要说：表里按单位「名字」合并，而上方的现役单位数按 id 去重，
          同名不同 id 的单位（各阵营都有的兰德掠袭者之类）在表里并成一行，两个数天然对不上 */}
      <p className="mt-1.5 font-mono text-[10.5px] text-[#4d5854]">
        反查只列现役口径的武器，{summary.base} 各档位合并统计；武器名与单位名均已去重合并，
        故行数少于上方计数
      </p>
    </div>
  );
}

interface KeywordIndexProps {
  /** 后端错误横幅由 /codex 页统一渲染（BACKEND_HINT 文案只留一份，不在组件里复制） */
  onError: () => void;
}

/**
 * 图鉴 · 武器词条页签：46 个词条按通用 / 过渡期 / 单位特有 分区，
 * 点行展开该词条的武器反查清单（详情单独取，索引不驮 364KB 的 weapons）。
 */
export function KeywordIndex({ onError }: KeywordIndexProps) {
  const [items, setItems] = useState<KeywordSummary[] | null>(null);
  const [query, setQuery] = useState("");
  const [openSlug, setOpenSlug] = useState<string | null>(null);
  // 详情按 slug 缓存：折叠再展开不重复打后端（一个词条最大 283 条武器）
  const [details, setDetails] = useState<Record<string, KeywordDetail>>({});
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchKeywords(ctrl.signal)
      .then(setItems)
      .catch((e) => {
        const err = e as Error;
        if (err.name === "AbortError") return;
        // 就地报错而不是渲染成「共 0 个词条」——空列表看着像「本来就没词条」
        setFailed(err.message);
        setItems([]);
      });
    return () => ctrl.abort();
  }, []);

  const toggle = (slug: string) => {
    if (openSlug === slug) {
      setOpenSlug(null);
      return;
    }
    setOpenSlug(slug);
    if (details[slug]) return;
    fetchKeywordDetail(slug)
      .then((d) => setDetails((prev) => ({ ...prev, [slug]: d })))
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        setOpenSlug((cur) => (cur === slug ? null : cur)); // 别让「载入中」永远转下去
        onError();
      });
  };

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const hit = (k: KeywordSummary) =>
      !q ||
      k.base.toLowerCase().includes(q) ||
      k.slug.includes(q) ||
      k.nameZh.includes(q) ||
      (k.quickrefZh ?? "").includes(q);
    const rows = (items ?? []).filter(hit);
    return GROUPS.map((g) => ({ ...g, rows: rows.filter((k) => k.group === g.id) }))
      // 筛出空组整段收起：留一堆「无匹配词条」的空壳只是噪声（无筛选时三组都保留）
      .filter((g) => g.rows.length > 0 || !q);
  }, [items, query]);

  // 一条都没匹配上时 grouped 是空数组，三个分区全被上面筛掉——不单独兜一句，
  // 页面就只剩个搜索框，看着像加载坏了。组内的「无匹配词条」兜不到这一层。
  const shown = grouped.reduce((n, g) => n + g.rows.length, 0);

  if (failed) {
    return (
      <div className="border border-redfont/40 bg-[#1a0d0d] px-4 py-6 font-mono text-[12.5px] break-all text-[#d99]">
        {/* 整句写成表达式：JSX 把源码换行折成空格，中文句子中间会凭空多个空格 */}
        {`词条索引没取到（${failed}）。词条清单是离线生成物 wiki/indexes/keywords.json，后端缺这份载荷时返回 503——容器化部署要确认 wiki/ 卷挂上了。`}
      </div>
    );
  }
  if (items === null) {
    return (
      <div className="border border-panel-line bg-panel px-4 py-10 text-center font-mono text-[13px] text-sage">
        载入词条清单…
      </div>
    );
  }

  const total = items.length;
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="筛选词条（中/英名）"
          className="w-[260px] border border-[#2b423d] bg-dark px-3 py-1.5 font-body text-[13px] text-bone outline-none placeholder:text-[#5c6f6a] focus:border-tau max-tablet:w-full max-tablet:text-[16px]"
        />
        <span className="font-mono text-[11.5px] text-[#5c6f6a]">
          {query.trim() ? `匹配 ${shown} / 共 ${total} 个词条` : `共 ${total} 个词条`}
        </span>
        {/* 引擎状态是模拟器口径，不是规则效力——这行不写清楚就会被读成「未纳入=没这条规则」 */}
        <span className="font-mono text-[11.5px] text-[#5c6f6a]">
          引擎状态＝战斗模拟器对它的处理：数值建模（逐骰结算）· 仅标注（只披露不结算）·
          未纳入（未建模）
        </span>
      </div>

      {grouped.length === 0 ? (
        <p className="border border-panel-line bg-panel px-4 py-10 text-center font-mono text-[12.5px] text-sage">
          {`没有匹配「${query.trim()}」的词条`}
        </p>
      ) : null}

      {grouped.map((g) => (
        <section key={g.id} className="mb-4">
          <div className="flex flex-wrap items-baseline gap-x-3 border border-panel-line border-b-0 bg-[#0f1c1f] px-3 py-1.5">
            <h2 className="font-cond text-[14px] tracking-[2px] text-bone uppercase">
              {g.title}
            </h2>
            <span className="font-cond text-[12px] text-gold">{g.rows.length}</span>
            <span className="text-[12px] text-[#8fa19b]">{g.note}</span>
          </div>

          <div className="overflow-x-auto border border-panel-line bg-panel">
            <div className="min-w-[700px]">
              <div
                className={`${COLS} border-b border-panel-line bg-[#101b1e] py-1.5 font-cond text-[11px] tracking-[1.5px] text-sage uppercase`}
              >
                <span>中文名</span>
                <span>英文</span>
                <span>节号</span>
                <span>档位</span>
                <span>现役武器 / 全库</span>
                <span>引擎</span>
              </div>

              {g.rows.length === 0 ? (
                <p className="px-3 py-3 font-mono text-[12px] text-sage">无匹配词条</p>
              ) : (
                <ul>
                  {g.rows.map((k) => {
                    const open = openSlug === k.slug;
                    return (
                      <li key={k.slug} className="border-b border-[#1a2624] last:border-b-0">
                        <button
                          type="button"
                          onClick={() => toggle(k.slug)}
                          aria-expanded={open}
                          className={`${COLS} w-full py-1.5 text-left hover:bg-[#14262a] ${
                            open ? "bg-[#16303550]" : ""
                          }`}
                        >
                          <span className="min-w-0 truncate text-[13.5px] text-bone">
                            {k.nameZh}
                            {k.quickrefZh && k.quickrefZh !== k.nameZh ? (
                              <span
                                className="ml-1.5 text-[11px] text-[#6f827c]"
                                title={`速查表另译：${k.quickrefZh}`}
                              >
                                另译 {k.quickrefZh}
                              </span>
                            ) : null}
                          </span>
                          <span className="min-w-0 truncate font-cond text-[12.5px] tracking-[1px] text-[#a9bcb6] uppercase">
                            {k.base}
                          </span>
                          {/* 速查表漏印节号的词条为 null：显示破折号，不许凭空补号 */}
                          <span className="font-mono text-[11.5px] text-[#8fa19b]">
                            {k.section ?? "—"}
                          </span>
                          <span className="flex min-w-0 flex-wrap gap-1">
                            {k.params.length === 0 ? (
                              <span className="font-mono text-[11.5px] text-[#5c6f6a]">
                                无参
                              </span>
                            ) : (
                              sortParams(k.params).map((p) => (
                                <span
                                  key={p}
                                  className="border border-[#2b423d] px-1 font-cond text-[11px] text-[#c7d2cd]"
                                >
                                  {p}
                                </span>
                              ))
                            )}
                          </span>
                          <span className="font-mono text-[11.5px] text-[#8fa19b]">
                            <b className="font-cond text-[13.5px] text-bone">
                              {k.currentWeapons}
                            </b>
                            <span className="text-[#5c6f6a]"> / {k.totalWeapons}</span>
                          </span>
                          <EngineTag engine={k.engine} />
                        </button>

                        {open ? (
                          <DetailBody summary={k} detail={details[k.slug] ?? null} />
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}
