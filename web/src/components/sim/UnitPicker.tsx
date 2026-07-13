"use client";

import { useMemo, useState } from "react";

import type { FactionRow, UnitRow } from "@/lib/codex";

interface UnitPickerProps {
  label: string; // 攻方 / 守方
  accent: "red" | "cyan"; // 攻红守青
  factions: FactionRow[];
  factionId: string | null;
  units: UnitRow[];
  loadingUnits: boolean;
  selected: UnitRow | null;
  onFaction: (id: string) => void;
  onUnit: (u: UnitRow) => void;
}

/** 模拟器单位选择面板：阵营下拉 + 筛选 + 单位列表（复用图鉴数据源） */
export function UnitPicker({
  label,
  accent,
  factions,
  factionId,
  units,
  loadingUnits,
  selected,
  onFaction,
  onUnit,
}: UnitPickerProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return units;
    return units.filter(
      (u) =>
        u.nameEn.toLowerCase().includes(q) ||
        (u.nameZh ?? "").toLowerCase().includes(q),
    );
  }, [units, query]);

  const accentBar =
    accent === "red" ? "bg-[linear-gradient(var(--color-gw-red),#6e0505)]" : "bg-[linear-gradient(var(--color-tau-ban),#0e3b44)]";

  return (
    <section className="clip-plate-10 border border-panel-line bg-panel">
      <div
        className={`flex items-baseline gap-3 px-3.5 py-2 ${accentBar}`}
      >
        <span className="font-cond text-[14px] font-bold tracking-[2px] text-white uppercase [text-shadow:0_1px_2px_#000]">
          {label}
        </span>
        <span className="min-w-0 flex-1 truncate text-right font-cond text-[12.5px] tracking-[1px] text-[#e8ddd0]">
          {selected ? (selected.nameZh ?? selected.nameEn) : "未选择"}
        </span>
      </div>
      <div className="flex gap-2 border-b border-panel-line p-2.5">
        <select
          value={factionId ?? ""}
          onChange={(e) => {
            setQuery("");
            onFaction(e.target.value);
          }}
          className="min-w-0 flex-1 border border-[#2b423d] bg-dark px-2 py-1.5 font-body text-[13px] text-bone outline-none focus:border-tau"
        >
          {factions.map((f) => (
            <option key={f.id} value={f.id}>
              {f.nameZh ?? f.name}（{f.count}）
            </option>
          ))}
        </select>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="筛选"
          className="w-[92px] border border-[#2b423d] bg-dark px-2 py-1.5 font-body text-[13px] text-bone outline-none placeholder:text-[#5c6f6a] focus:border-tau max-tablet:text-[16px]"
        />
      </div>
      <ul className="h-[218px] overflow-y-auto">
        {loadingUnits ? (
          <li className="px-3 py-3 font-mono text-[12px] text-sage">
            载入单位……
          </li>
        ) : (
          filtered.map((u) => (
            <li key={u.id}>
              <button
                type="button"
                onClick={() => onUnit(u)}
                className={`flex w-full items-baseline gap-2 border-b border-[#1a2624] px-3 py-1.5 text-left hover:bg-[#14262a] ${
                  u.id === selected?.id ? "bg-[#16303550]" : ""
                }`}
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] text-bone">
                    {u.nameZh ?? u.nameEn}
                  </span>
                  {u.nameZh ? (
                    <span className="block truncate font-cond text-[10.5px] tracking-[1px] text-[#6f827c] uppercase">
                      {u.nameEn}
                    </span>
                  ) : null}
                </span>
                {u.pts ? (
                  <span className="flex-none font-cond text-[11px] text-gold">
                    {u.pts}
                  </span>
                ) : null}
              </button>
            </li>
          ))
        )}
        {!loadingUnits && filtered.length === 0 ? (
          <li className="px-3 py-3 font-mono text-[12px] text-sage">
            无匹配单位
          </li>
        ) : null}
      </ul>
    </section>
  );
}
