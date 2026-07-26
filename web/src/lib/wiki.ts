/**
 * 分队 / 战略 / 增强 wiki 页契约真源（唯一真源）：后端 web_api/contract.py 的
 * Wiki 与 Detachment 系列模型逐字段镜像本文件
 * （model_dump(by_alias=True) 出 camelCase，前端零解析）。
 *
 * 正文由后端把 wiki markdown 编译成块（WikiBlock）后下发：前端不引任何 markdown 库
 * （运行时依赖只有 next/react/@fontsource），wikilink 的转义竖线 `\|`、表格、引用块
 * 都在后端拆完——解析规则只留一份，前端再解一次必然与后端漂移。
 *
 * 数据来自离线生成物 wiki 下各阵营的 detachments / stratagems / enhancements 页，
 * 容器 324 个但战略 1681 条，故详情把子条目**内联**返回：前端一次请求拿全，不打 N 次。
 */
import type { Inline } from "./answer";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

/**
 * 块级正文：七种块覆盖 wiki 全部排版（段落/列表/表格/小标题/引用/折叠）。
 *
 * `details` 是**可嵌套**的块（里面还是一串 WikiBlock）——核心规则页每节「中文正文 +
 * 官方英文原文折叠」就是它。summary 本身携带信息（142 节写「官方英文原文」、14 节写
 * 「官方英文原文（英文由 PDF 直提）」），照实显示，不要归一化成一句固定话术。
 */
export type WikiBlock =
  | { t: "p"; inline: Inline[] }
  | { t: "ul"; items: Inline[][] }
  | { t: "ol"; items: Inline[][] }
  | { t: "table"; head: string[]; rows: string[][] }
  | { t: "h"; level: number; text: string } // level 2/3/4，小节内标题
  | { t: "quote"; inline: Inline[] } // > 引用（页面里的诚实披露用它）
  | { t: "details"; summary: string; blocks: WikiBlock[] };

export interface WikiSection {
  title: string;
  /**
   * 官方节号（"16.01"）。**只有核心规则页会有**，其余页型（战略/增强/分队/变更清单）
   * 的小节名本来就没编号，为 null。由后端从小节名尾部取——那条规则全仓库只有
   * web_api/core_rules_browse.section_number 一处实现，前端不要再抠一遍。
   */
  number: string | null;
  blocks: WikiBlock[];
}

export interface StratagemBrief {
  id: string;
  slug: string;
  nameEn: string;
  nameZh: string | null;
  /** 0 CP 是真值（存在 0 CP 战略），null 才是未知——前端不许 `cp || "未知"` */
  cp: number | null;
  phase: string;
  stratagemType: string;
  /** 使用时机 / 使用对象 / 效果 / 限制（限制常缺） */
  sections: WikiSection[];
}

export interface EnhancementBrief {
  id: string;
  slug: string;
  nameEn: string;
  nameZh: string | null;
  /** 同 cp：0 分是真值，null 是库里没这项（1058 条里 131 条缺，照实留空不猜） */
  cost: number | null;
  sections: WikiSection[];
}

export interface DetachmentSummary {
  slug: string;
  nameEn: string;
  nameZh: string | null;
  /** 分队规则名（≠ 分队名）：页面 name_en 是容器名 Awakened Dynasty，规则名是 Command Protocols */
  ruleName: string | null;
  stratagemCount: number;
  enhancementCount: number;
}

export interface DetachmentDetail extends DetachmentSummary {
  factionId: string;
  factionZh: string | null;
  ruleSections: WikiSection[];
  enhancements: EnhancementBrief[];
  stratagems: StratagemBrief[];
}

export interface DetachmentListResponse {
  items: DetachmentSummary[];
}

/**
 * 带状态码的错误：503（wiki/ 卷没挂上）和 404（阵营/分队查无此页）要给不同的话，
 * 否则用户看到的永远是「后端返回 xxx」，最该修的部署问题被埋在数字里。
 */
export class WikiApiError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`后端返回 ${status}`);
    this.name = "WikiApiError";
    this.status = status;
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { signal });
  if (!resp.ok) throw new WikiApiError(resp.status);
  return (await resp.json()) as T;
}

/** 同名分队跨阵营存在（Infestation Swarm 在 GC 与 TYR 各一个），路由必须带 faction_id */
export function fetchDetachments(
  factionId: string,
  signal?: AbortSignal,
): Promise<DetachmentSummary[]> {
  return getJson<DetachmentListResponse>(
    `/codex/factions/${encodeURIComponent(factionId)}/detachments`,
    signal,
  ).then((d) => d.items);
}

export function fetchDetachmentDetail(
  factionId: string,
  slug: string,
  signal?: AbortSignal,
): Promise<DetachmentDetail> {
  return getJson<DetachmentDetail>(
    `/codex/factions/${encodeURIComponent(factionId)}/detachments/${encodeURIComponent(slug)}`,
    signal,
  );
}

/* ── 核心规则全文（GET /codex/rules[/{slug}]）───────────────────────── */

export interface CoreRuleChapterSummary {
  slug: string;
  /** 官方章号，两位前导零（"01".."24"）——它同时是排序键，别 parseInt 再拼回去 */
  number: string;
  nameZh: string;
  nameEn: string;
  sectionCount: number;
}

export interface CoreRuleChapter extends CoreRuleChapterSummary {
  /**
   * 导语块。**必须渲染**：里面是「正文为官方简体中文版；中文由 PDF 文本层直提，
   * 表格与版式会有失真——判定规则以英文原文为准」这条披露。不显示它，这一页看起来
   * 就是一份官方中文规则定稿，而它其实是直提文本。
   */
  intro: WikiBlock[];
  /** 小节标题自带官方节号（"执行行动 16.01"），原样显示，前端不去拆 */
  sections: WikiSection[];
}

export interface CoreRuleChapterListResponse {
  items: CoreRuleChapterSummary[];
}

export function fetchRuleChapters(signal?: AbortSignal): Promise<CoreRuleChapterSummary[]> {
  return getJson<CoreRuleChapterListResponse>("/codex/rules", signal).then((d) => d.items);
}

export function fetchRuleChapter(
  slug: string,
  signal?: AbortSignal,
): Promise<CoreRuleChapter> {
  return getJson<CoreRuleChapter>(`/codex/rules/${encodeURIComponent(slug)}`, signal);
}

/* ── 规则变更清单（GET /codex/changelog[/{slug}]）───────────────────── */

export interface ChangelogFactionSummary {
  /**
   * null = 真没有明细页可点（deathwatch 首版无更新章节、混沌恶魔官方本次未列改动）。
   * 这两行的原因写在 detail 里，照实显示；不要造一个空页面让人点进去看「0 条改动」。
   */
  slug: string | null;
  name: string;
  version: string;
  total: number;
  newCount: number;
  /** 明细列原文：有明细页时是「查看」，没有时是不存在明细的原因 */
  detail: string;
}

export interface ChangelogIndex {
  intro: WikiBlock[];
  /** 《通用规则更新》：跨全部阵营生效，与阵营明细分开显示，免得被当成某个阵营的改动 */
  generalSections: WikiSection[];
  /** 兜底桶：index 里其余的节（此刻是「数值层的 10→11 漂移」那条口径说明） */
  noteSections: WikiSection[];
  factions: ChangelogFactionSummary[];
  total: number;
  newCount: number;
}

export interface ChangelogFactionPage {
  slug: string;
  nameZh: string;
  nameEn: string;
  version: string;
  total: number;
  newCount: number;
  intro: WikiBlock[];
  /** 小节名是官方自己的分组（数据表 / 军队规则 / 各分遣队名） */
  sections: WikiSection[];
}

export function fetchChangelog(signal?: AbortSignal): Promise<ChangelogIndex> {
  return getJson<ChangelogIndex>("/codex/changelog", signal);
}

export function fetchChangelogFaction(
  slug: string,
  signal?: AbortSignal,
): Promise<ChangelogFactionPage> {
  return getJson<ChangelogFactionPage>(
    `/codex/changelog/${encodeURIComponent(slug)}`,
    signal,
  );
}
