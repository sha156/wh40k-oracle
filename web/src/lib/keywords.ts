/**
 * 武器词条（keyword）契约真源：后端 web_api/contract.py 的 Keyword* 模型逐字段镜像本文件
 * （model_dump(by_alias=True) 出 camelCase，前端零解析）。
 *
 * 数据来自离线生成物 wiki/indexes/keywords.json——分组与计数都在离线阶段算完，
 * 请求时后端不读 sqlite 也不碰 PDF（容器只挂 wiki/、db/、opt/、local_vector_store/ 只读卷，
 * data/ 压根没挂，任何"临时算一下"的实现上线即空）。
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

/** universal=官方核心规则在册；transitional=在册但正被取代（手枪→近距离）；
 *  unit-specific=某单位专属 */
export type KeywordGroup = "universal" | "transitional" | "unit-specific";

export interface KeywordSummary {
  /** "rapid-fire" / "anti-infantry" / "c-tan-power" */
  slug: string;
  /** 英文基础词条（大写），如 "RAPID FIRE" */
  base: string;
  nameZh: string;
  group: KeywordGroup;
  /** 速查表节号，如 "24.30"；速查表漏印时为 null——显示成「—」，不许补号 */
  section: string | null;
  /** 速查表译名，与 nameZh 不同时展示「另译」 */
  quickrefZh: string | null;
  /** 档位变体（["1","2","D6+3"]），无参词条为 [] */
  params: string[];
  /** 数值建模 | 仅标注 | 未纳入；离线算好的字符串而非枚举，未知取值走兜底样式 */
  engine: string;
  /** 规则正文页路径（"core-rules/rapid-fire.md"），无页为 null */
  rulePage: string | null;
  /** 现役口径武器数（去重武器名） */
  currentWeapons: number;
  totalWeapons: number;
  currentUnits: number;
  totalUnits: number;
}

export interface KeywordWeapon {
  name: string;
  /** 携带该武器的单位（现役口径） */
  units: string[];
}

export interface KeywordDetail extends KeywordSummary {
  /** 反查清单：只含现役口径，条数与 currentWeapons 一致（全库数另见 totalWeapons） */
  weapons: KeywordWeapon[];
}

export interface KeywordIndexResponse {
  items: KeywordSummary[];
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { signal });
  if (!resp.ok) throw new Error(`后端返回 ${resp.status}`);
  return (await resp.json()) as T;
}

/** 索引不带 weapons 字段（全量反查清单 364KB，列表页用不上） */
export function fetchKeywords(signal?: AbortSignal): Promise<KeywordSummary[]> {
  return getJson<KeywordIndexResponse>("/codex/keywords", signal).then((d) => d.items);
}

export function fetchKeywordDetail(
  slug: string,
  signal?: AbortSignal,
): Promise<KeywordDetail> {
  return getJson<KeywordDetail>(
    `/codex/keywords/${encodeURIComponent(slug)}`,
    signal,
  );
}
