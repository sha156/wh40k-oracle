"use client";

import { useEffect, useMemo, useState } from "react";

import { Datasheet } from "@/components/chat/Datasheet";
import { SiteHeader } from "@/components/chat/SiteHeader";
import type { EntityCard } from "@/lib/answer";
import {
  fetchFactions,
  fetchUnitCard,
  fetchUnits,
  type FactionRow,
  type UnitRow,
} from "@/lib/codex";

const BACKEND_HINT =
  "无法连接后端。请确认 web_api 已启动：.venv\\Scripts\\python.exe -m uvicorn web_api.main:app --port 8000";

/**
 * 图鉴页（Stage 4）：阵营 → 单位列表 → 兵牌（复用 Datasheet 组件）。
 * 数据只读自 L3 结构库（/codex/*），零 LLM。
 */
export default function CodexPage() {
  const [factions, setFactions] = useState<FactionRow[]>([]);
  const [factionId, setFactionId] = useState<string | null>(null);
  const [units, setUnits] = useState<UnitRow[]>([]);
  const [query, setQuery] = useState("");
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null);
  const [card, setCard] = useState<EntityCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingUnits, setLoadingUnits] = useState(false);
  const [loadingCard, setLoadingCard] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchFactions(ctrl.signal)
      .then((fs) => {
        setFactions(fs);
        if (fs[0]) {
          setLoadingUnits(true);
          setFactionId(fs[0].id);
        }
      })
      .catch((e) => {
        if ((e as Error).name !== "AbortError") setError(BACKEND_HINT);
      });
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    if (!factionId) return;
    const ctrl = new AbortController();
    fetchUnits(factionId, ctrl.signal)
      .then(setUnits)
      .catch((e) => {
        if ((e as Error).name !== "AbortError") setError(BACKEND_HINT);
      })
      .finally(() => setLoadingUnits(false));
    return () => ctrl.abort();
  }, [factionId]);

  // 切换阵营：在事件里重置从属状态 + 开 loading（不在 effect 同步 setState，避免额外渲染）
  const selectFaction = (id: string) => {
    if (id === factionId) return;
    setUnits([]);
    setCard(null);
    setSelectedUnit(null);
    setQuery("");
    setLoadingUnits(true);
    setFactionId(id);
  };

  const pickUnit = (uid: string) => {
    setSelectedUnit(uid);
    setCard(null);
    setLoadingCard(true);
    fetchUnitCard(uid)
      .then(setCard)
      .catch((e) => {
        if ((e as Error).name !== "AbortError") setError(BACKEND_HINT);
      })
      .finally(() => setLoadingCard(false));
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return units;
    return units.filter(
      (u) =>
        u.nameEn.toLowerCase().includes(q) ||
        (u.nameZh ?? "").toLowerCase().includes(q),
    );
  }, [units, query]);

  const activeFaction = factions.find((f) => f.id === factionId);
  const context = activeFaction
    ? `图鉴 · ${activeFaction.nameZh ?? activeFaction.name}`
    : "图鉴 · CODEX";

  return (
    <>
      <SiteHeader context={context} active="图鉴" />
      <main className="mx-auto max-w-[1100px] px-5 pt-[22px] pb-20 max-tablet:px-2.5 max-tablet:pt-4">
        {error ? (
          <p className="mb-4 border border-redfont/40 bg-[#1a0d0d] px-4 py-3 font-mono text-[12.5px] break-all text-[#d99]">
            {error}
          </p>
        ) : null}

        {/* 阵营选择 */}
        <div className="mb-4 flex gap-2 overflow-x-auto scrollbar-none pb-1">
          {factions.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => selectFaction(f.id)}
              className={`clip-slant-8 flex-none whitespace-nowrap px-3.5 py-1.5 font-cond text-[13px] tracking-[1px] uppercase ${
                f.id === factionId
                  ? "bg-[linear-gradient(var(--color-tau-ban),#0e3b44)] text-bone"
                  : "border border-[#2b423d] bg-[#101b1e] text-[#a9bcb6] hover:border-tau hover:text-bone"
              }`}
            >
              {f.nameZh ?? f.name}
              <span className="ml-1.5 text-[11px] opacity-60">{f.count}</span>
            </button>
          ))}
        </div>

        <div className="grid grid-cols-[300px_1fr] gap-4 max-wide:grid-cols-1">
          {/* 单位列表 */}
          <section className="clip-plate-10 border border-panel-line bg-panel">
            <div className="border-b border-panel-line p-2.5">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="筛选单位（中/英名）"
                className="w-full border border-[#2b423d] bg-dark px-3 py-2 font-body text-[13px] text-bone outline-none placeholder:text-[#5c6f6a] focus:border-tau max-tablet:text-[16px]"
              />
            </div>
            <ul className="max-h-[62vh] overflow-y-auto max-wide:max-h-[38vh]">
              {loadingUnits ? (
                <li className="px-3 py-4 font-mono text-[12px] text-sage">
                  载入单位……
                </li>
              ) : (
                filtered.map((u) => (
                  <li key={u.id}>
                    <button
                      type="button"
                      onClick={() => pickUnit(u.id)}
                      className={`flex w-full items-baseline gap-2 border-b border-[#1a2624] px-3 py-2 text-left hover:bg-[#14262a] ${
                        u.id === selectedUnit ? "bg-[#16303550]" : ""
                      }`}
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13.5px] text-bone">
                          {u.nameZh ?? u.nameEn}
                        </span>
                        {u.nameZh ? (
                          <span className="block truncate font-cond text-[11px] tracking-[1px] text-[#6f827c] uppercase">
                            {u.nameEn}
                          </span>
                        ) : null}
                      </span>
                      {u.pts ? (
                        <span className="flex-none font-cond text-[11.5px] text-gold">
                          {u.pts}
                        </span>
                      ) : null}
                    </button>
                  </li>
                ))
              )}
              {!loadingUnits && filtered.length === 0 ? (
                <li className="px-3 py-4 font-mono text-[12px] text-sage">
                  无匹配单位
                </li>
              ) : null}
            </ul>
          </section>

          {/* 兵牌详情 */}
          <section className="min-w-0">
            {loadingCard ? (
              <div className="border border-panel-line bg-panel px-4 py-10 text-center font-mono text-[13px] text-sage">
                载入兵牌……
              </div>
            ) : card ? (
              <Datasheet card={card} />
            ) : (
              <div className="border border-dashed border-panel-line bg-[#0d1517] px-4 py-16 text-center font-cond text-[14px] tracking-[1px] text-[#5c6f6a] uppercase">
                ← 选择左侧单位查看兵牌
              </div>
            )}
          </section>
        </div>
      </main>
    </>
  );
}
