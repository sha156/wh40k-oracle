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

/** E6 官方版式兵牌（同 wiki frontmatter + 表结构） */
export interface EntityCard {
  nameZh: string;
  nameEn: string;
  pts: string; // 如 "80 / 170 / 270"
  stats: { lab: string; val: string }[];
  ranged: WeaponRow[];
  melee: WeaponRow[];
  abilities: Ability[];
  composition: RichText[];
  keywords: string;
  faction: string;
  src: string; // 书名 + 页码
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
