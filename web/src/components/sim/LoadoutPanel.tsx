"use client";

/** 武器装配面板：多武器单位模拟前，逐把武器指定数量（后端不猜默认装备）。
 *  攻方（gold）与守方反打（cyan）复用同一组件，accent 决定配色。 */

interface LoadoutPanelProps {
  title: string;
  note?: string | null;
  weaponPool: string[];
  modelTiers?: { models: number; cost: number | null }[] | null;
  loadout: Record<string, number>;
  onChange: (weapon: string, count: number) => void;
  accent: "gold" | "cyan";
  /** 「全员」一键填入的件数（= 该侧模型数）；每个模型各带 1 件 */
  fillCount: number;
}

const PALETTE = {
  gold: {
    box: "border-gold/40 bg-[#141207]",
    title: "text-gold",
    note: "text-[#b8ab88]",
    tier: "text-[#8a7f60]",
    label: "text-[#d8cba6]",
    input: "border-[#4a4326]",
    row: "border-[#3a3520] bg-[#0f0d06]",
    fill: "border-gold/50 text-gold hover:bg-gold/15",
  },
  cyan: {
    box: "border-tau/40 bg-[#081416]",
    title: "text-cyan-glow",
    note: "text-[#8fb4bb]",
    tier: "text-[#5f8a92]",
    label: "text-[#bfe0e6]",
    input: "border-[#264a52]",
    row: "border-[#1d3b41] bg-[#061013]",
    fill: "border-tau/50 text-cyan-glow hover:bg-tau/15",
  },
} as const;

export function LoadoutPanel({
  title,
  note,
  weaponPool,
  modelTiers,
  loadout,
  onChange,
  accent,
  fillCount,
}: LoadoutPanelProps) {
  const c = PALETTE[accent];
  const fill = fillCount > 0 ? fillCount : 1;
  const picked = weaponPool.reduce((sum, w) => sum + (loadout[w] || 0), 0);
  return (
    <section className={`mt-4 border ${c.box} px-4 py-3`}>
      <div className={`mb-1 font-cond text-[13px] tracking-[2px] uppercase ${c.title}`}>
        {title}
      </div>
      <p className={`mb-2.5 text-[12.5px] ${c.note}`}>
        {note || "该单位有多把可选武器，指定每把带几件再模拟（不猜默认装备）。"}
        {modelTiers?.length ? (
          <span className={`ml-1 font-mono text-[11.5px] ${c.tier}`}>
            点数档位：
            {modelTiers
              .map((t) => `${t.models} 模型${t.cost != null ? ` ${t.cost} 分` : ""}`)
              .join(" / ")}
          </span>
        ) : null}
      </p>
      <div className="flex flex-wrap gap-2">
        {weaponPool.map((w) => (
          <div
            key={w}
            className={`flex items-center gap-2 border ${c.row} px-2 py-1`}
          >
            <label className={`text-[13px] ${c.label}`} htmlFor={`lo-${accent}-${w}`}>
              {w}
            </label>
            <input
              id={`lo-${accent}-${w}`}
              type="number"
              min={0}
              value={loadout[w] ?? ""}
              onChange={(e) => onChange(w, parseInt(e.target.value, 10) || 0)}
              placeholder="0"
              aria-label={`${w} 件数`}
              className={`w-[52px] border ${c.input} bg-dark px-1.5 py-0.5 text-[12.5px] text-bone outline-none placeholder:text-[#5c6f6a]`}
            />
            <span className={`text-[11.5px] ${c.tier}`}>件</span>
            <button
              type="button"
              onClick={() => onChange(w, fill)}
              aria-label={`${w} 全员装配`}
              title={`全员携带：${fill} 件（每个模型各 1 件）`}
              className={`clip-slant-8 border ${c.fill} px-2 py-0.5 font-cond text-[11.5px] tracking-[1px]`}
            >
              全员
            </button>
          </div>
        ))}
      </div>
      <p className={`mt-2 text-[11.5px] ${c.tier}`}>
        点武器右侧的「全员」= 每个模型各带 1 件（{fill} 件），也可直接填件数；
        填好后点右上「开始模拟」。当前共选 {picked} 件。
      </p>
    </section>
  );
}
