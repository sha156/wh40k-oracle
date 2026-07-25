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

/** 块级正文：六种块覆盖 wiki 实体页的全部排版（段落/列表/表格/小标题/引用） */
export type WikiBlock =
  | { t: "p"; inline: Inline[] }
  | { t: "ul"; items: Inline[][] }
  | { t: "ol"; items: Inline[][] }
  | { t: "table"; head: string[]; rows: string[][] }
  | { t: "h"; level: number; text: string } // level 3/4，小节内标题
  | { t: "quote"; inline: Inline[] }; // > 引用（页面里的诚实披露用它）

export interface WikiSection {
  title: string;
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
