/** 图鉴（Codex）后端只读 API 客户端（Stage 4）。 */
import type { EntityCard } from "./answer";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

export interface FactionRow {
  id: string;
  name: string;
  nameZh: string | null;
  /** 现役单位数（includeLegacy 时为含传承的总数） */
  count: number;
  /** 该阵营被归档的传承条目数（Legends/福基世界/退环境） */
  legacyCount?: number;
}

export interface UnitRow {
  id: string;
  nameEn: string;
  nameZh: string | null;
  pts: string | null;
  /** true=传承条目（比赛摆不上桌，默认不列；归档不是删除，直链仍可看） */
  legacy?: boolean;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { signal });
  if (!resp.ok) throw new Error(`后端返回 ${resp.status}`);
  return (await resp.json()) as T;
}

export function fetchFactions(
  signal?: AbortSignal,
  includeLegacy = false,
): Promise<FactionRow[]> {
  const q = includeLegacy ? "?include_legacy=1" : "";
  return getJson<{ factions: FactionRow[] }>(`/codex/factions${q}`, signal).then(
    (d) => d.factions,
  );
}

export function fetchUnits(
  factionId: string,
  signal?: AbortSignal,
  includeLegacy = false,
): Promise<UnitRow[]> {
  const q = includeLegacy ? "?include_legacy=1" : "";
  return getJson<{ units: UnitRow[] }>(
    `/codex/factions/${encodeURIComponent(factionId)}/units${q}`,
    signal,
  ).then((d) => d.units);
}

export type CodexLang = "zh" | "en";

export function fetchUnitCard(
  unitId: string,
  lang: CodexLang = "zh",
  signal?: AbortSignal,
): Promise<EntityCard> {
  return getJson<{ card: EntityCard }>(
    `/codex/units/${encodeURIComponent(unitId)}?lang=${lang}`,
    signal,
  ).then((d) => d.card);
}
