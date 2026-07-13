/**
 * 军表实验室契约（BUILD-PLAN Stage 4 / P6-PR3）：/roster/* 请求/响应类型。
 * 本文件是唯一真源，后端 web_api/contract.py 的 Roster/Out 模型逐字段镜像它。
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

export type RosterSize = "incursion" | "strike_force" | "onslaught";

export const SIZE_LABELS: Record<RosterSize, string> = {
  incursion: "突袭 1000",
  strike_force: "打击力量 2000",
  onslaught: "猛攻 3000",
};

export interface Detachment {
  id: string;
  name: string;
}

export interface Enhancement {
  id: string;
  name: string;
  cost: number | null;
}

/** 提交给后端的单位（loadout=[[武器名,数量],...]） */
export interface RosterUnitPayload {
  canonicalId: string;
  nameEn: string;
  models: number;
  isWarlord: boolean;
  enhancement: string | null;
  loadout: [string, number][];
}

export interface RosterPayload {
  factionId: string;
  detachmentId: string | null;
  size: RosterSize;
  units: RosterUnitPayload[];
}

export interface ValidationIssue {
  code: string;
  severity: "error" | "warn" | "info";
  message: string;
  anchor: string;
  surfacedOnly: boolean;
}

export interface ValidationReport {
  totalPoints: number;
  limit: number;
  legal: boolean;
  issues: ValidationIssue[];
}

export interface TargetScore {
  key: string;
  label: string;
  expectedDamage: number;
  damagePer100: number | null;
}

export interface UnitAssessment {
  canonicalId: string;
  nameEn: string;
  points: number | null;
  assessed: boolean;
  phase: string | null;
  scores: TargetScore[];
  note: string;
}

export interface CritiqueReport {
  totalPoints: number;
  assessments: UnitAssessment[];
  summary: string[];
  notModeled: string[];
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { signal });
  if (!resp.ok) throw new Error(`后端返回 ${resp.status}`);
  return (await resp.json()) as T;
}

async function postJson<T>(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok) throw new Error(`后端返回 ${resp.status}`);
  return (await resp.json()) as T;
}

export function fetchDetachments(
  factionId: string,
  signal?: AbortSignal,
): Promise<Detachment[]> {
  return getJson<{ detachments: Detachment[] }>(
    `/roster/detachments?faction=${encodeURIComponent(factionId)}`,
    signal,
  ).then((d) => d.detachments);
}

export function fetchEnhancements(
  detachmentId: string,
  signal?: AbortSignal,
): Promise<Enhancement[]> {
  return getJson<{ enhancements: Enhancement[] }>(
    `/roster/enhancements?detachment=${encodeURIComponent(detachmentId)}`,
    signal,
  ).then((d) => d.enhancements);
}

export function fetchUnitWeapons(
  unitId: string,
  signal?: AbortSignal,
): Promise<string[]> {
  return getJson<{ weaponPool: string[] }>(
    `/roster/units/${encodeURIComponent(unitId)}/weapons`,
    signal,
  ).then((d) => d.weaponPool);
}

export function postValidate(
  roster: RosterPayload,
  signal?: AbortSignal,
): Promise<ValidationReport> {
  return postJson<ValidationReport>("/roster/validate", roster, signal);
}

export function postCritique(
  roster: RosterPayload,
  signal?: AbortSignal,
): Promise<CritiqueReport> {
  return postJson<CritiqueReport>("/roster/critique", roster, signal);
}
