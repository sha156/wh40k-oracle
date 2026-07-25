"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { SectionList } from "@/components/codex/Blocks";
import type { FactionRow } from "@/lib/codex";
import {
  fetchDetachmentDetail,
  fetchDetachments,
  WikiApiError,
  type DetachmentDetail,
  type DetachmentSummary,
  type EnhancementBrief,
  type StratagemBrief,
} from "@/lib/wiki";

/** 0 CP 是真值（确有 0 CP 战略），null 才是未知——`cp || "未知"` 会把 0 说成未知 */
function cpLabel(cp: number | null): string {
  return cp === null ? "CP 未知" : `${cp} CP`;
}

/** 同理：0 分是真值，null 是库里本来就没这项（照实说未知，不写 0） */
function costLabel(cost: number | null): string {
  return cost === null ? "分数未知" : `${cost} 分`;
}

/**
 * 阶段串是官方英文原文，复合写法（"Your Shooting phase or the Fight phase"）花样太多，
 * 只对完全命中的常见值配中文，其余原样显示——猜一半的翻译比英文原文更误导。
 */
const PHASE_ZH: Record<string, string> = {
  "Command phase": "指挥阶段",
  "Movement phase": "移动阶段",
  "Shooting phase": "射击阶段",
  "Charge phase": "冲锋阶段",
  "Fight phase": "战斗阶段",
  "Any phase": "任意阶段",
};

/**
 * stratagem_type 形如「Bully Boyz – Strategic Ploy Stratagem」，在本分队页里前缀是废话。
 * 只在前缀与本分队英文名一致时剥掉（分隔符见过 en dash / hyphen 两种），剥不掉就原样留。
 */
function shortType(type: string, detachmentEn: string): string {
  const en = detachmentEn.trim().toLowerCase();
  for (const sep of [" – ", " — ", " - "]) {
    const i = type.indexOf(sep);
    if (i > 0 && type.slice(0, i).trim().toLowerCase() === en) {
      return type.slice(i + sep.length);
    }
  }
  return type;
}

/**
 * 「阶段 · 类型」副标题。要拼而不是直接写 `{a} · {b}`：实测 1647 条战略里有 200 条
 * 库里没有 stratagem_type，硬拼会在行尾留一个孤零零的「 · 」，看着像内容没加载完。
 */
function metaLine(...parts: string[]): string {
  return parts.filter((p) => p.trim() !== "").join(" · ");
}

/**
 * 名字两行：中文名在上、英文名压在下面。
 *
 * 中文名缺失是常态而非例外（实测分队 0/324、战略 759/1647、增强 381/1058 有中文名），
 * 此时上行已经回落成英文名——再无脑画一遍下行，就是把同一个名字原样印两遍。
 * 所以下行只在**确有中文名**时出现。
 */
function NameLines({ nameZh, nameEn }: { nameZh: string | null; nameEn: string }) {
  return (
    <>
      <span className="block truncate text-[13.5px] text-bone">{nameZh ?? nameEn}</span>
      {nameZh === null ? null : (
        <span className="block truncate font-cond text-[11px] tracking-[1px] text-[#6f827c] uppercase">
          {nameEn}
        </span>
      )}
    </>
  );
}

function toggled(set: ReadonlySet<string>, id: string): Set<string> {
  const next = new Set(set);
  if (!next.delete(id)) next.add(id);
  return next;
}

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/** 503 = wiki/ 卷没挂（部署问题），404 = 查无此页（数据问题）——两种话不一样，混在一起就没人修 */
function apiHint(e: unknown, what: string): string {
  const status = e instanceof WikiApiError ? e.status : 0;
  if (status === 503) {
    return `${what}没取到（503）：后端读不到 wiki/ 目录。分队页是离线生成物 wiki/factions/*/detachments/*.md，容器化部署要确认 wiki/ 只读卷挂上了。`;
  }
  if (status === 404) {
    return `${what}没取到（404）：后端查无此阵营/分队。`;
  }
  return `${what}没取到（${errText(e)}）。`;
}

interface StratagemRowProps {
  s: StratagemBrief;
  detachmentEn: string;
  open: boolean;
  onToggle: (id: string) => void;
}

function StratagemRow({ s, detachmentEn, open, onToggle }: StratagemRowProps) {
  return (
    <li className="border-b border-[#1a2624] last:border-b-0">
      <button
        type="button"
        onClick={() => onToggle(s.id)}
        aria-expanded={open}
        className={`flex w-full items-baseline gap-3 px-3 py-2 text-left hover:bg-[#14262a] ${
          open ? "bg-[#16303550]" : ""
        }`}
      >
        <span className="min-w-0 flex-1">
          <NameLines nameZh={s.nameZh} nameEn={s.nameEn} />
        </span>
        {/* 阶段/类型在手机上藏起来（三列挤成一坨），展开区补一行给它 */}
        <span
          className="min-w-0 flex-1 truncate text-right text-[11.5px] text-[#8fa19b] max-tablet:hidden"
          title={s.stratagemType}
        >
          {metaLine(PHASE_ZH[s.phase] ?? s.phase, shortType(s.stratagemType, detachmentEn))}
        </span>
        <span
          className={`clip-slant-8 flex-none border px-2 py-[1px] font-cond text-[11.5px] tracking-[1px] ${
            s.cp === null
              ? "border-[#2b423d] bg-[#101b1e] text-[#7d8a86]"
              : "border-gold/50 bg-[#171509] text-gold"
          }`}
        >
          {cpLabel(s.cp)}
        </span>
      </button>
      {open ? (
        <div className="border-t border-panel-line bg-[#0a1214] px-3 py-2">
          <p className="mb-1.5 hidden font-mono text-[11px] text-[#5c6f6a] max-tablet:block">
            {metaLine(PHASE_ZH[s.phase] ?? s.phase, s.stratagemType)}
          </p>
          <SectionList
            sections={s.sections}
            compact
            emptyHint="未收录分段正文（WHEN/TARGET/EFFECT 未拆出）"
          />
        </div>
      ) : null}
    </li>
  );
}

interface EnhancementRowProps {
  e: EnhancementBrief;
  open: boolean;
  onToggle: (id: string) => void;
}

function EnhancementRow({ e, open, onToggle }: EnhancementRowProps) {
  return (
    <li className="border-b border-[#1a2624] last:border-b-0">
      <button
        type="button"
        onClick={() => onToggle(e.id)}
        aria-expanded={open}
        className={`flex w-full items-baseline gap-3 px-3 py-2 text-left hover:bg-[#14262a] ${
          open ? "bg-[#16303550]" : ""
        }`}
      >
        <span className="min-w-0 flex-1">
          <NameLines nameZh={e.nameZh} nameEn={e.nameEn} />
        </span>
        <span
          className={`clip-slant-8 flex-none border px-2 py-[1px] font-cond text-[11.5px] tracking-[1px] ${
            e.cost === null
              ? "border-[#2b423d] bg-[#101b1e] text-[#7d8a86]"
              : "border-gold/50 bg-[#171509] text-gold"
          }`}
        >
          {costLabel(e.cost)}
        </span>
      </button>
      {open ? (
        <div className="border-t border-panel-line bg-[#0a1214] px-3 py-2">
          <SectionList sections={e.sections} compact emptyHint="未收录分段正文" />
        </div>
      ) : null}
    </li>
  );
}

interface GroupProps {
  title: string;
  /** 详情里内联返回的条数 */
  shown: number;
  /** 清单页声明的条数——与 shown 对不上要当场说，静默差额是最难查的那种 bug */
  declared: number;
  allOpen: boolean;
  onToggleAll: () => void;
  children: ReactNode;
}

function Group({ title, shown, declared, allOpen, onToggleAll, children }: GroupProps) {
  return (
    <section className="clip-plate-10 mt-4 border border-panel-line bg-panel">
      <div className="flex flex-wrap items-baseline gap-x-3 border-b border-panel-line bg-[#0f1c1f] px-3.5 py-1.5">
        <h3 className="font-cond text-[13.5px] tracking-[2px] text-bone uppercase">
          {title}
        </h3>
        <span className="font-cond text-[13px] text-gold">{shown}</span>
        {declared !== shown ? (
          <span className="font-mono text-[11px] text-[#d99]">
            清单声明 {declared} 条，实际取到 {shown} 条
          </span>
        ) : null}
        {shown > 0 ? (
          <button
            type="button"
            onClick={onToggleAll}
            className="ml-auto font-cond text-[11.5px] tracking-[1px] text-[#8fa19b] uppercase hover:text-bone"
          >
            {allOpen ? "全部收起" : "全部展开"}
          </button>
        ) : null}
      </div>
      {children}
    </section>
  );
}

interface DetachmentBrowserProps {
  /** 阵营清单由 /codex 页统一取（避免同一份 /codex/factions 拉两遍） */
  factions: FactionRow[];
  /** 后端错误横幅由 /codex 页渲染，文案只留一份 */
  onError: () => void;
}

/**
 * 图鉴 · 分队页签：阵营 → 分队列表 → 分队详情（规则正文 + 增强 + 战略）。
 * 详情把下属战略/增强内联返回（容器 324 个但战略 1681 条，逐条拉会打爆后端），
 * 展开只是本地状态，不再发请求。
 */
export function DetachmentBrowser({ factions, onError }: DetachmentBrowserProps) {
  const [pickedFaction, setPickedFaction] = useState<string | null>(null);
  const [items, setItems] = useState<DetachmentSummary[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [slug, setSlug] = useState<string | null>(null);
  const [detail, setDetail] = useState<DetachmentDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [openStrat, setOpenStrat] = useState<ReadonlySet<string>>(new Set());
  const [openEnh, setOpenEnh] = useState<ReadonlySet<string>>(new Set());
  // 详情按「阵营/slug」缓存：同名分队跨阵营各有一个（Infestation Swarm 在 GC 与 TYR 都有），
  // 只用 slug 当键会串页
  const [cache, setCache] = useState<Record<string, DetachmentDetail>>({});
  // 连点两条分队时先发的请求可能后到——用序号丢弃过期响应，否则点 A 再点 B 会停在 A
  const reqSeq = useRef(0);

  // 阵营是外部异步灌进来的：派生首选而不是在 effect 里补 setState（少一次渲染）
  const factionId = pickedFaction ?? factions[0]?.id ?? null;

  useEffect(() => {
    if (!factionId) return;
    const ctrl = new AbortController();
    // 清错误放在回调里而不是 effect 体内：effect 体内同步 setState 会级联重渲染（lint 也拦）
    fetchDetachments(factionId, ctrl.signal)
      .then((rows) => {
        setItems(rows);
        setListError(null);
      })
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        // 就地报错而不是渲染成「共 0 个分队」——空列表看着像「这阵营本来就没分队」
        setListError(apiHint(e, "分队清单"));
        setItems([]);
      });
    return () => ctrl.abort();
  }, [factionId]);

  const selectFaction = (id: string) => {
    if (id === factionId) return;
    setPickedFaction(id);
    // 作废在途的详情请求：换阵营后它再回来会把上一个阵营的分队塞进详情区
    reqSeq.current += 1;
    setItems(null);
    setListError(null);
    setQuery("");
    setSlug(null);
    setDetail(null);
    setDetailError(null);
    // 作废在途请求后没人再关 loading 灯，这里手动关（否则详情区永远停在「载入中」）
    setLoadingDetail(false);
  };

  const pick = (s: string) => {
    if (!factionId) return;
    setSlug(s);
    setDetailError(null);
    setOpenStrat(new Set());
    setOpenEnh(new Set());
    const key = `${factionId}/${s}`;
    const hit = cache[key];
    if (hit) {
      setDetail(hit);
      setLoadingDetail(false);
      return;
    }
    const seq = ++reqSeq.current;
    setDetail(null);
    setLoadingDetail(true);
    fetchDetachmentDetail(factionId, s)
      .then((d) => {
        setCache((prev) => ({ ...prev, [key]: d }));
        if (reqSeq.current === seq) setDetail(d);
      })
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        if (reqSeq.current === seq) setDetailError(apiHint(e, "分队详情"));
        // 顶部横幅的话术是「无法连接后端，请确认 web_api 已启动」——后端答了 404/503
        // 恰恰说明它活着，这时候再挂横幅就是两条互相打架的错误信息，真正该修的
        // （卷没挂上）反而被"后端没起"盖过去。只有连接层真的失败才升到横幅。
        if (!(e instanceof WikiApiError)) onError();
      })
      .finally(() => {
        if (reqSeq.current === seq) setLoadingDetail(false);
      });
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = items ?? [];
    if (!q) return rows;
    return rows.filter(
      (d) =>
        d.nameEn.toLowerCase().includes(q) ||
        (d.nameZh ?? "").toLowerCase().includes(q) ||
        (d.ruleName ?? "").toLowerCase().includes(q),
    );
  }, [items, query]);

  const allStratOpen =
    detail != null && detail.stratagems.length > 0 && openStrat.size === detail.stratagems.length;
  const allEnhOpen =
    detail != null && detail.enhancements.length > 0 && openEnh.size === detail.enhancements.length;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2">
        {/* 阵营用下拉不用铺开按钮：25 个按钮会把列表挤下屏，且与「单位」页签的同名按钮
            在 DOM 里共存（两个页签都常驻），点选与 e2e 选择器都会歧义 */}
        <select
          value={factionId ?? ""}
          onChange={(e) => selectFaction(e.target.value)}
          className="min-w-[180px] border border-[#2b423d] bg-dark px-2 py-1.5 font-body text-[13px] text-bone outline-none focus:border-tau"
        >
          {factions.length === 0 ? <option value="">载入阵营…</option> : null}
          {factions.map((f) => (
            <option key={f.id} value={f.id}>
              {f.nameZh ?? f.name}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="筛选分队（中/英名、规则名）"
          className="w-[240px] border border-[#2b423d] bg-dark px-3 py-1.5 font-body text-[13px] text-bone outline-none placeholder:text-[#5c6f6a] focus:border-tau max-tablet:w-full max-tablet:text-[16px]"
        />
        <span className="font-mono text-[11.5px] text-[#5c6f6a]">
          {items === null
            ? // 阵营清单是父页给的：它没到（多半是后端没连上，横幅已在上方）时别说"载入分队"
              factionId
              ? "载入分队…"
              : "等待阵营清单…"
            : query.trim()
              ? `匹配 ${filtered.length} / 共 ${items.length} 个分队`
              : `共 ${items.length} 个分队`}
        </span>
      </div>

      {/* 两条口径先说清楚：分队名≠分队规则名（最容易搞反）；核心战略不挂分队，本页列不到 */}
      <p className="mb-3 font-mono text-[11px] text-[#5c6f6a]">
        列表里的名字是分队容器名，「规则」一行才是分队规则名（Awakened Dynasty
        的规则叫 Command Protocols）；不属任何分队的核心战略不在本页。
      </p>

      {listError ? (
        <p className="mb-3 border border-redfont/40 bg-[#1a0d0d] px-4 py-3 font-mono text-[12.5px] break-all text-[#d99]">
          {listError}
        </p>
      ) : null}

      <div className="grid grid-cols-[300px_1fr] gap-4 max-wide:grid-cols-1">
        <section className="clip-plate-10 border border-panel-line bg-panel">
          <ul className="max-h-[68vh] overflow-y-auto max-wide:max-h-[38vh]">
            {items === null ? (
              <li className="px-3 py-4 font-mono text-[12px] text-sage">
                {factionId ? "载入分队……" : "等待阵营清单……"}
              </li>
            ) : (
              filtered.map((d) => (
                <li key={d.slug}>
                  <button
                    type="button"
                    onClick={() => pick(d.slug)}
                    className={`w-full border-b border-[#1a2624] px-3 py-2 text-left hover:bg-[#14262a] ${
                      d.slug === slug ? "bg-[#16303550]" : ""
                    }`}
                  >
                    <NameLines nameZh={d.nameZh} nameEn={d.nameEn} />
                    <span className="mt-0.5 flex items-baseline gap-2">
                      <span className="min-w-0 flex-1 truncate text-[11.5px] text-[#8fa19b]">
                        规则 · {d.ruleName ?? "未标注"}
                      </span>
                      {/* 300px 的列放不下「N 战略 / M 增强」，缩成「略/增」并把全称挂 title */}
                      <span
                        className="flex-none font-mono text-[10.5px] text-[#5c6f6a]"
                        title={`${d.stratagemCount} 条战略 / ${d.enhancementCount} 条增强`}
                      >
                        {d.stratagemCount} 略 / {d.enhancementCount} 增
                      </span>
                    </span>
                  </button>
                </li>
              ))
            )}
            {items !== null && filtered.length === 0 ? (
              <li className="px-3 py-4 font-mono text-[12px] text-sage">
                {query.trim() ? "无匹配分队" : "该阵营没有收录的分队页"}
              </li>
            ) : null}
          </ul>
        </section>

        {/* min-w-0：详情里的表格靠自己的 overflow-x 横滚，栅格子项不收窄就会顶得整页横滚 */}
        <section className="min-w-0">
          {detailError ? (
            <div className="border border-redfont/40 bg-[#1a0d0d] px-4 py-6 font-mono text-[12.5px] break-all text-[#d99]">
              {detailError}
            </div>
          ) : loadingDetail ? (
            <div className="border border-panel-line bg-panel px-4 py-10 text-center font-mono text-[13px] text-sage">
              载入分队详情……
            </div>
          ) : detail ? (
            <>
              <div className="clip-plate-10 border border-panel-line bg-panel">
                <div className="flex flex-wrap items-baseline gap-x-3 bg-[linear-gradient(var(--color-tau-ban),#0e3b44)] px-3.5 py-2">
                  <span className="font-cond text-[15px] font-bold tracking-[2px] text-white uppercase [text-shadow:0_1px_2px_#000]">
                    {detail.nameZh ?? detail.nameEn}
                  </span>
                  {/* 同 NameLines：分队全库都没有中文名，副标题会与主标题一字不差 */}
                  {detail.nameZh === null ? null : (
                    <span className="font-cond text-[12.5px] tracking-[1px] text-[#cfe3e8] uppercase">
                      {detail.nameEn}
                    </span>
                  )}
                  <span className="ml-auto font-cond text-[12px] tracking-[1px] text-[#e8ddd0]">
                    {detail.factionZh ?? detail.factionId}
                  </span>
                </div>
                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-panel-line px-3.5 py-1.5 font-mono text-[11.5px] text-[#8fa19b]">
                  <span>
                    分队规则{" "}
                    <b className="font-cond text-[13px] text-bone">
                      {detail.ruleName ?? "未标注"}
                    </b>
                  </span>
                  <span>
                    战略 <b className="font-cond text-[13px] text-bone">{detail.stratagemCount}</b>
                    {" · "}增强{" "}
                    <b className="font-cond text-[13px] text-bone">{detail.enhancementCount}</b>
                  </span>
                </div>
                <div className="px-3.5 py-2.5">
                  <SectionList
                    sections={detail.ruleSections}
                    emptyHint="本页未收录分队规则正文"
                  />
                </div>
              </div>

              <Group
                title="增强"
                shown={detail.enhancements.length}
                declared={detail.enhancementCount}
                allOpen={allEnhOpen}
                onToggleAll={() =>
                  setOpenEnh(
                    allEnhOpen ? new Set() : new Set(detail.enhancements.map((x) => x.id)),
                  )
                }
              >
                {detail.enhancements.length === 0 ? (
                  <p className="px-3.5 py-3 font-mono text-[12px] text-sage">本分队无增强</p>
                ) : (
                  <ul>
                    {detail.enhancements.map((e) => (
                      <EnhancementRow
                        key={e.id}
                        e={e}
                        open={openEnh.has(e.id)}
                        onToggle={(id) => setOpenEnh((prev) => toggled(prev, id))}
                      />
                    ))}
                  </ul>
                )}
              </Group>

              <Group
                title="战略"
                shown={detail.stratagems.length}
                declared={detail.stratagemCount}
                allOpen={allStratOpen}
                onToggleAll={() =>
                  setOpenStrat(
                    allStratOpen ? new Set() : new Set(detail.stratagems.map((x) => x.id)),
                  )
                }
              >
                {detail.stratagems.length === 0 ? (
                  <p className="px-3.5 py-3 font-mono text-[12px] text-sage">本分队无战略</p>
                ) : (
                  <ul>
                    {detail.stratagems.map((s) => (
                      <StratagemRow
                        key={s.id}
                        s={s}
                        detachmentEn={detail.nameEn}
                        open={openStrat.has(s.id)}
                        onToggle={(id) => setOpenStrat((prev) => toggled(prev, id))}
                      />
                    ))}
                  </ul>
                )}
              </Group>
            </>
          ) : (
            <div className="border border-dashed border-panel-line bg-[#0d1517] px-4 py-16 text-center font-cond text-[14px] tracking-[1px] text-[#5c6f6a] uppercase">
              ← 选择左侧分队查看规则与战略
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
