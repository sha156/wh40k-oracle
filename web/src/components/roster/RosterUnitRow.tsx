"use client";

import { LoadoutPanel } from "@/components/sim/LoadoutPanel";
import type { Enhancement } from "@/lib/roster";

export interface RosterUnitState {
  uid: number;
  canonicalId: string;
  nameEn: string;
  nameZh: string | null;
  models: number;
  isWarlord: boolean;
  enhancement: string | null;
  loadout: Record<string, number>;
  weaponPool: string[] | null; // 懒加载
  expanded: boolean;
}

interface RosterUnitRowProps {
  unit: RosterUnitState;
  enhancements: Enhancement[];
  onModels: (uid: number, v: number) => void;
  onWarlord: (uid: number, v: boolean) => void;
  onEnhancement: (uid: number, v: string | null) => void;
  onToggleExpand: (uid: number) => void;
  onLoadout: (uid: number, weapon: string, count: number) => void;
  onRemove: (uid: number) => void;
}

export function RosterUnitRow({
  unit,
  enhancements,
  onModels,
  onWarlord,
  onEnhancement,
  onToggleExpand,
  onLoadout,
  onRemove,
}: RosterUnitRowProps) {
  const loadoutCount = Object.values(unit.loadout).filter((c) => c > 0).length;
  return (
    <div className="border border-panel-line bg-[#0f191c]">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3 py-2">
        <span className="min-w-[120px] flex-1 text-[13px] text-bone">
          {unit.nameZh ?? unit.nameEn}
          {unit.isWarlord ? (
            <span className="ml-1.5 font-cond text-[10px] tracking-[1px] text-gold uppercase">
              ★ 军阀
            </span>
          ) : null}
        </span>

        <label className="flex items-center gap-1 text-[12px] text-[#a9bcb6]">
          模型
          <input
            type="number"
            min={1}
            value={unit.models}
            onChange={(e) => onModels(unit.uid, parseInt(e.target.value, 10) || 1)}
            className="w-[48px] border border-[#2b423d] bg-dark px-1.5 py-0.5 text-[12.5px] text-bone outline-none"
          />
        </label>

        <label className="flex items-center gap-1 text-[12px] text-[#a9bcb6] select-none">
          <input
            type="checkbox"
            checked={unit.isWarlord}
            onChange={(e) => onWarlord(unit.uid, e.target.checked)}
            className="h-3.5 w-3.5 accent-[#8a6d17]"
          />
          军阀
        </label>

        <select
          value={unit.enhancement ?? ""}
          onChange={(e) => onEnhancement(unit.uid, e.target.value || null)}
          className="max-w-[190px] border border-[#2b423d] bg-dark px-1.5 py-0.5 text-[12px] text-bone outline-none"
        >
          <option value="">无强化</option>
          {enhancements.map((en) => (
            <option key={en.id} value={en.name}>
              {en.name}
              {en.cost != null ? `（${en.cost}）` : ""}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={() => onToggleExpand(unit.uid)}
          className={`clip-slant-8 px-2.5 py-0.5 font-cond text-[11px] tracking-[1px] uppercase ${
            loadoutCount > 0
              ? "bg-[#0e3b44] text-cyan-glow"
              : "bg-[#16211f] text-[#97a4a0] hover:text-bone"
          }`}
          title="装配武器（点评用）"
        >
          装配{loadoutCount > 0 ? ` ·${loadoutCount}` : ""}
        </button>

        <button
          type="button"
          onClick={() => onRemove(unit.uid)}
          className="px-1.5 font-mono text-[15px] text-[#7d5a5a] hover:text-redfont"
          title="移除"
        >
          ×
        </button>
      </div>

      {unit.expanded ? (
        unit.weaponPool === null ? (
          <p className="border-t border-panel-line px-3 py-2 font-mono text-[11.5px] text-sage">
            载入武器池…
          </p>
        ) : (
          <LoadoutPanel
            title="装配武器（用于点评强度）"
            weaponPool={unit.weaponPool}
            loadout={unit.loadout}
            onChange={(w, c) => onLoadout(unit.uid, w, c)}
            accent="cyan"
          />
        )
      ) : null}
    </div>
  );
}
