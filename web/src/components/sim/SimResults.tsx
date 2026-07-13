import type { SimReport, SimResponse } from "@/lib/sim";

/** 漏斗四段（同单位「次」，damage/kills 不同量纲不混轴，走 KPI） */
const FUNNEL_ROWS: { key: string; label: string }[] = [
  { key: "attacks", label: "攻击次数" },
  { key: "hits", label: "命中" },
  { key: "wounds", label: "致伤" },
  { key: "unsaved", label: "失防" },
];

function fmt(v: number, digits = 2): string {
  return Number.isInteger(v) ? String(v) : v.toFixed(digits);
}

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function Kpi({ v, unit, k, amber }: { v: string; unit?: string; k: string; amber?: boolean }) {
  return (
    <div className="min-w-[118px] flex-1 border border-panel-line bg-[#0f191c] px-3 py-2">
      <div
        className={`font-cond text-[24px] leading-[1.1] font-bold ${amber ? "text-amber" : "text-cyan-glow"}`}
      >
        {v}
        {unit ? <small className="ml-0.5 text-[12px] font-normal text-sage">{unit}</small> : null}
      </div>
      <div className="mt-0.5 font-cond text-[11px] tracking-[1px] text-[#7d8a86]">
        {k}
      </div>
    </div>
  );
}

/** B 方向稿复活的攻击解算漏斗：单色调横条，按攻击次数归一化 */
function Funnel({ report }: { report: SimReport }) {
  const base = report.funnel["attacks"] || 1;
  return (
    <div>
      <div className="mb-2 font-mono text-[10px] tracking-[2px] text-[#4f8e9c] uppercase">
        ◢ 攻击解算漏斗 · 期望值
      </div>
      {FUNNEL_ROWS.map(({ key, label }) => {
        const v = report.funnel[key] ?? 0;
        const w = Math.max(0, Math.min(100, (v / base) * 100));
        return (
          <div
            key={key}
            className="my-[7px] grid grid-cols-[72px_1fr_64px] items-center gap-2.5"
          >
            <span className="text-right text-[12px] whitespace-nowrap text-[#8fa19b]">
              {label}
            </span>
            <div
              className="relative h-3 border border-[#1d3238] bg-[rgba(111,195,212,.06)]"
              title={`${label}：期望 ${fmt(v)} 次`}
            >
              <i
                className="block h-full bg-[linear-gradient(90deg,rgba(111,195,212,.25),rgba(111,195,212,.75))] shadow-[0_0_8px_rgba(111,195,212,.3)]"
                style={{ width: `${w}%` }}
              />
            </div>
            <span className="font-mono text-[12px] whitespace-nowrap text-cyan-glow">
              {fmt(v)}
            </span>
          </div>
        );
      })}
      <div className="mt-2.5 border-t border-dashed border-[#1d3238] pt-2 font-mono text-[11px] text-[#5c6f6a]">
        失防后 → 期望伤害 <b className="font-normal text-amber">{fmt(report.expectedDamage)}</b>{" "}
        · 期望击杀 <b className="font-normal text-amber">{fmt(report.expectedKills)}</b> 个模型
      </div>
    </div>
  );
}

/** 击杀数离散直方图：单系列细柱，选择性标注（≥10% 的柱标百分比） */
function KillsHistogram({ report }: { report: SimReport }) {
  const entries = Object.entries(report.distribution.histogram ?? {})
    .map(([k, p]) => ({ k: Number(k), p }))
    .sort((a, b) => a.k - b.k);
  if (entries.length === 0) return null;
  const maxP = Math.max(...entries.map((e) => e.p));
  const d = report.distribution;
  return (
    <div>
      <div className="mb-2 font-mono text-[10px] tracking-[2px] text-[#4f8e9c] uppercase">
        ◢ 击杀数分布 · {report.iterations.toLocaleString()} 次模拟
      </div>
      <div className="flex h-[120px] items-end gap-[2px]">
        {entries.map(({ k, p }) => (
          <div
            key={k}
            className="flex min-w-0 flex-1 flex-col items-center justify-end self-stretch"
            title={`击杀 ${k} 个：${pct(p)}`}
          >
            {p >= 0.1 ? (
              <span className="mb-0.5 font-mono text-[9.5px] text-[#5c6f6a]">
                {Math.round(p * 100)}%
              </span>
            ) : null}
            <div
              className="w-full max-w-[38px] bg-[linear-gradient(rgba(111,195,212,.8),rgba(111,195,212,.3))]"
              style={{ height: `${Math.max(2, (p / maxP) * 82)}%` }}
            />
          </div>
        ))}
      </div>
      <div className="flex gap-[2px] border-t border-[#1d3238] pt-1">
        {entries.map(({ k }) => (
          <span
            key={k}
            className="min-w-0 flex-1 text-center font-mono text-[10px] text-[#7d8a86]"
          >
            {k}
          </span>
        ))}
      </div>
      <div className="mt-2 font-mono text-[11px] text-[#5c6f6a]">
        击杀分位 p10/p50/p90：
        <span className="text-cyan-glow">
          {fmt(d.p10, 1)} / {fmt(d.p50, 1)} / {fmt(d.p90, 1)}
        </span>
        　伤害分位：
        <span className="text-cyan-glow">
          {fmt(d.damage?.p10 ?? 0, 1)} / {fmt(d.damage?.p50 ?? 0, 1)} /{" "}
          {fmt(d.damage?.p90 ?? 0, 1)}
        </span>
      </div>
    </div>
  );
}

/** 诚实披露：计入 / 未建模 / 偏差 / 守方未施加开关 / 阵营分队 */
function Honesty({ resp }: { resp: SimResponse }) {
  const rep = resp.report;
  if (!rep) return null;
  const detachments = resp.factionOptions?.detachments ?? [];
  return (
    <div className="border border-panel-line bg-[#0d1517] px-4 py-3">
      <div className="mb-2 font-cond text-[12px] tracking-[2px] text-sage uppercase">
        建模边界（诚实披露）
      </div>
      {rep.modeledEffects.length > 0 ? (
        <p className="my-1 text-[12.5px] text-[#8fa19b]">
          已计入：
          {rep.modeledEffects.map((e) => (
            <span
              key={e}
              className="mr-1.5 inline-block border border-[#1d3238] bg-[#0f191c] px-1.5 py-px font-mono text-[11px] text-cyan-glow"
            >
              {e}
            </span>
          ))}
        </p>
      ) : null}
      {rep.notModeled.length > 0 ? (
        <p className="my-1 text-[12.5px] text-[#8fa19b]">
          <span className="text-amber">未建模</span>（结果未计入这些能力）：
          {/* 引擎条目自带「未建模·」前缀，剥掉避免与标签重复 */}
          {rep.notModeled.map((s) => s.replace(/^未建模·/, "")).join("、")}
        </p>
      ) : null}
      {rep.biasNotes.length > 0 ? (
        <p className="my-1 text-[12px] text-[#6f827c] italic">
          {rep.biasNotes.join("；")}
        </p>
      ) : null}
      {resp.defenderToggles.length > 0 ? (
        <p className="my-1 text-[12.5px] text-[#8fa19b]">
          守方还有可选防守规则<span className="text-[#6f827c]">（未自动施加，条件满足时用左侧开关近似）</span>：
          {resp.defenderToggles.map((t) => t.name).join("、")}
        </p>
      ) : null}
      {detachments.length > 0 ? (
        <p className="my-1 text-[12.5px] text-[#6f827c]">
          守方阵营（{resp.factionOptions?.factionName}）的分队规则一律未建模：
          {detachments.join("、")}
        </p>
      ) : null}
      {resp.warning ? (
        <p className="my-1 text-[12.5px] text-[#d99]">{resp.warning}</p>
      ) : null}
      <p className="mt-2 border-t border-dashed border-[#1d3238] pt-1.5 font-mono text-[10.5px] text-[#4d5854]">
        蒙特卡洛 {rep.iterations.toLocaleString()} 次 · seed {rep.seed} · 同参数同种子结果可复现
      </p>
    </div>
  );
}

interface SimResultsProps {
  resp: SimResponse; // 调用方保证 ok === true 且 report 存在
  attackerLabel: string;
  defenderLabel: string;
}

/** 模拟结果：KPI 行 + 漏斗 + 击杀分布 + 建模边界 */
export function SimResults({ resp, attackerLabel, defenderLabel }: SimResultsProps) {
  const rep = resp.report;
  if (!rep) return null;
  const eff = rep.efficiency;
  return (
    <div className="flex flex-col gap-3">
      <div className="clip-plate-10 border border-panel-line bg-panel">
        <div className="flex flex-wrap items-baseline gap-2 border-b border-panel-line px-4 py-2">
          <span className="font-cond text-[15px] font-bold tracking-[1px] text-bone">
            {attackerLabel}
          </span>
          <span className="font-mono text-[12px] text-redfont">
            ▶ {resp.phase === "melee" ? "近战" : "射击"} ▶
          </span>
          <span className="font-cond text-[15px] font-bold tracking-[1px] text-bone">
            {defenderLabel}
          </span>
        </div>
        <div className="flex flex-wrap gap-2 px-4 py-3">
          <Kpi v={fmt(rep.expectedDamage)} unit="伤" k="期望伤害 / 轮" />
          <Kpi v={fmt(rep.expectedKills)} unit="个" k="期望击杀模型" />
          <Kpi v={pct(rep.wipeProbability)} k="整队团灭率" amber />
          {eff.damage_per_100 != null ? (
            <Kpi
              v={fmt(eff.damage_per_100)}
              unit="伤"
              k={`每 100 分（攻方 ${eff.points} 分）`}
            />
          ) : null}
        </div>
        <div className="grid grid-cols-2 gap-5 px-4 pt-1 pb-4 max-tablet:grid-cols-1">
          <Funnel report={rep} />
          <KillsHistogram report={rep} />
        </div>
      </div>

      {rep.reverse ? (
        <div className="border border-panel-line bg-panel px-4 py-3">
          <div className="mb-1.5 font-cond text-[12px] tracking-[2px] text-sage uppercase">
            守方幸存反打（串行）
          </div>
          <div className="flex flex-wrap gap-2">
            <Kpi v={fmt(rep.reverse.expectedDamage)} unit="伤" k="反打期望伤害" />
            <Kpi v={fmt(rep.reverse.expectedKills)} unit="个" k="反打期望击杀" />
            <Kpi v={pct(rep.reverse.wipeProbability)} k="反团灭率" amber />
          </div>
        </div>
      ) : null}

      <Honesty resp={resp} />
    </div>
  );
}
