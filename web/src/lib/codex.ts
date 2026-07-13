/** 图鉴（Codex）后端只读 API 客户端（Stage 4）。 */
import type { EntityCard } from "./answer";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

export interface FactionRow {
  id: string;
  name: string;
  nameZh: string | null;
  count: number;
}

export interface UnitRow {
  id: string;
  nameEn: string;
  nameZh: string | null;
  pts: string | null;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { signal });
  if (!resp.ok) throw new Error(`后端返回 ${resp.status}`);
  return (await resp.json()) as T;
}

export function fetchFactions(signal?: AbortSignal): Promise<FactionRow[]> {
  return getJson<{ factions: FactionRow[] }>("/codex/factions", signal).then(
    (d) => d.factions,
  );
}

export function fetchUnits(
  factionId: string,
  signal?: AbortSignal,
): Promise<UnitRow[]> {
  return getJson<{ units: UnitRow[] }>(
    `/codex/factions/${encodeURIComponent(factionId)}/units`,
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
