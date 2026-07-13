/**
 * 模拟器契约（BUILD-PLAN Stage 4）：POST /simulate 请求/响应类型。
 * 本文件是唯一真源，后端 web_api/contract.py 的 Sim* 模型逐字段镜像它
 * （model_dump(by_alias=True) 出 camelCase，前端零解析）。
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

/** 姿态与守方 opt-in 开关（与后端 sanitize_options 白名单一致） */
export interface SimOptions {
  phase?: "shooting" | "melee";
  charge?: boolean;
  half_range?: boolean;
  cover?: boolean;
  stationary?: boolean;
  long_range?: boolean;
  indirect?: boolean;
  stealth?: boolean;
  attacker_models?: number;
  defender_models?: number;
  fnp?: number; // 守方无痛 X+（2-6）
  damage_reduction?: number;
  loadout?: [string, number][]; // [[武器名, 数量], ...]
  n?: number;
  seed?: number;
}

/** 守方可 opt-in 的防守开关（后端只披露，不自动施加） */
export interface SimToggle {
  name: string;
  note: string;
  parsed?: unknown;
}

/** 守方阵营分队清单（诚实披露未建模的分队/军队规则） */
export interface SimFactionOptions {
  factionId: string | null;
  factionName: string | null;
  detachments: string[];
}

export interface SimDistribution {
  p10: number;
  p50: number;
  p90: number;
  /** 击杀数直方图 {击杀数: 概率}——JSON 键为字符串数字 */
  histogram: Record<string, number>;
  damage: { p10: number; p50: number; p90: number };
}

export interface SimReport {
  expectedDamage: number;
  expectedKills: number;
  wipeProbability: number;
  distribution: SimDistribution;
  /** attacks → hits → wounds → unsaved → damage → kills（期望值） */
  funnel: Record<string, number>;
  /** { points, damage_per_100, kills_per_100 }，无点数时为空对象 */
  efficiency: { points?: number; damage_per_100?: number; kills_per_100?: number };
  modeledEffects: string[];
  notModeled: string[];
  biasNotes: string[];
  iterations: number;
  seed: number;
  reverse: SimReport | null;
}

export interface SimResponse {
  ok: boolean;
  /** ok=false 时：not_found | loadout_required | ambiguous | error */
  reason?: string | null;
  note?: string | null;
  warning?: string | null;
  attacker?: string | null;
  defender?: string | null;
  phase?: string | null;
  report?: SimReport | null;
  defenderToggles: SimToggle[];
  factionOptions?: SimFactionOptions | null;
  /** loadout_required 时的武器池（英文权威名，回填 options.loadout） */
  weaponPool?: string[] | null;
  /** points 档位 [{models, cost}]，选模型数用 */
  modelTiers?: { models: number; cost: number | null }[] | null;
  errors: string[];
}

/** 发起一次模拟。未知单位 id 后端 404 → 抛错；其余失败以 ok=false 结构化返回。 */
export async function postSimulate(
  attackerId: string,
  defenderId: string,
  options: SimOptions,
  signal?: AbortSignal,
): Promise<SimResponse> {
  const resp = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ attackerId, defenderId, options }),
    signal,
  });
  if (!resp.ok) throw new Error(`后端返回 ${resp.status}`);
  return (await resp.json()) as SimResponse;
}
