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
  reverse?: boolean; // 守方幸存反打开关（多武器守方未指明 loadout → defender_loadout_required）
  /** 守方反打装配（近战武器）；reverse 开启且守方多武器时必填 */
  defender_loadout?: [string, number][];
  reverse_phase?: "shooting" | "melee"; // 反打阶段，默认 melee
  n?: number;
  seed?: number;
  // ── P7 攻方阵营 DSL（钛帝国试点）──
  guided?: boolean; // FTGG：假设本单位受引导且目标已被标记
  markerlight_observer?: boolean; // 观察员带 Markerlight 关键词
  detachment?: string; // 分队名（Kauyon / Mont'ka，撇号直弯均可）
  detachment_rounds?: boolean; // 假设处于分队规则生效轮次（Kauyon 3-5 / Mont'ka 1-3）
  stratagems?: string[]; // 战略点名（id/英文名/中文名）；一次性 opt-in，CP 不结算
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

/** 攻方阵营 DSL 可用条目（P7-PR3 回显）：surface 供渲染开关组与战略点名回传 */
export interface SimDslEntry {
  table: string; // abilities（军规/分队规则）| stratagems（须点名 options.stratagems）
  id: string;
  nameEn: string;
  nameZh: string | null;
  status: string; // encoded | partial
  detachment: string | null; // null=军队级；非空=仅该分队（options.detachment 匹配）
  requiresToggles: string[]; // 需同开的态势开关名（guided / detachment_rounds …）
}

export interface SimResponse {
  ok: boolean;
  /** ok=false 时：not_found | loadout_required | defender_loadout_required | error
   *  （loadout_required=攻方装配，defender_loadout_required=守方反打装配，都附 weaponPool） */
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
  /** 攻方阵营 DSL 可用条目（空数组=该阵营无已编码条目） */
  dslAvailable: SimDslEntry[];
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
