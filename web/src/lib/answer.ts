/**
 * 结构化回答契约（BUILD-PLAN Stage 3）：
 * 回答不是 markdown 长文，而是按 E1-E9 槽位结构化返回，前端零解析直接映射组件。
 * Stage 2 静态版先用本文件类型 + fixture 固定数据；Stage 3 由后端
 * response_formatter 按同一契约产出。
 */

/** 行内富文本片段——避免前端解析 markdown，后端直接给结构 */
export type Inline =
  | { t: "text"; s: string }
  | { t: "num"; s: string } // 数值强调（窄体加粗）
  | { t: "kw"; s: string } // 规则关键词，如 [重型]
  | { t: "strong"; s: string } // 结论强调（红）
  | { t: "cite"; n: number }; // 引用角标 [n]

export type RichText = Inline[];

/** E3 机魂运转记录 */
export interface TraceStep {
  fn: string;
  args: string;
  result?: string;
  status: "ok" | "degraded";
  note?: string;
}

/** E4 判定 */
export interface Verdict {
  label: string; // 盾章大字，如「值得带」
  labelEn: string; // 盾章小字，如 Sanctioned
  lede: RichText;
}

/** E5 计算依据（单条） */
export interface CalcStep {
  n: number;
  text: RichText;
}

/** E6 兵牌武器行 */
export interface WeaponRow {
  name: string;
  kw?: string; // 武器关键词，如 [重型，毁灭伤害]
  range: string;
  a: string;
  skill: string; // BS 或 WS
  s: string;
  ap: string;
  d: string;
  hot?: boolean; // 本次问答焦点武器高亮
}

export interface Ability {
  tag?: string; // 如 Faction:
  name: string;
  text?: string;
}

/** 受损档（载具/巨兽血量降到阈值时的减值） */
export interface DamagedProfile {
  w: string; // 触发血量区间，如 "1-5"
  text: string;
}

/** E6 官方版式兵牌（Wahapedia datasheet 复刻） */
export interface EntityCard {
  nameZh: string;
  nameEn: string;
  pts: string; // 如 "80 / 170 / 270"
  role?: string; // 战场角色
  stats: { lab: string; val: string }[];
  invuln?: string; // 无效保护值，如 "5+"
  ranged: WeaponRow[];
  melee: WeaponRow[];
  abilities: Ability[]; // 能力（核心/阵营/兵牌，带规则文本）
  loadout?: string; // 默认装备
  damaged?: DamagedProfile; // 受损档
  leads?: string; // 可依附/带领的单位说明
  composition: RichText[];
  keywords: string; // 单位关键词
  factionKeywords?: string; // 阵营关键词
  legend?: string; // 背景文案
  faction: string;
  src: string; // 数据来源
  wiki: string; // wiki 路径
}

/** E7 封蜡引用：红色高亮位 = page（p.44）或 term（词条名） */
export interface Cite {
  n: number;
  book: string;
  page?: number;
  section?: string; // 词条分类前缀，如 "武器技能"
  term?: string; // 无页码时红色高亮的词条名，如 "重型"
  wiki: string;
}

/** E8 CTA */
export interface Cta {
  kind: "simulator" | "roster" | "wiki";
  ready: boolean;
  label: string;
  mini?: string;
}

/** E8 敏感性 */
export interface Sensitivity {
  title: string;
  text: RichText;
}

/** 一次完整回答（按槽位映射 E3-E9） */
export interface Answer {
  summary: string; // 应答头右侧短语，如 "检索 4 步 · 引用 3 条 · 期望值粗算"
  trace: TraceStep[]; // E3
  traceWarn?: string; // E3 折叠头右侧警示
  verdict: Verdict; // E4
  calc: CalcStep[]; // E5
  entityCard?: EntityCard; // E6
  cites: Cite[]; // E7
  sensitivity?: Sensitivity; // E8
  cta?: Cta; // E8
  followups: string[]; // E9 chips
  degraded: boolean;
}

/** 一次对话（E2 + 回答） */
export interface Exchange {
  question: string;
  context: string; // 当前语境，如 "钛帝国 T'AU EMPIRE"
  answer: Answer;
}
