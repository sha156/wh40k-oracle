"use client";

import { useCallback, useEffect, useState } from "react";

import { SiteHeader } from "@/components/chat/SiteHeader";
import { SimResults } from "@/components/sim/SimResults";
import { UnitPicker } from "@/components/sim/UnitPicker";
import {
  fetchFactions,
  fetchUnits,
  type FactionRow,
  type UnitRow,
} from "@/lib/codex";
import { postSimulate, type SimOptions, type SimResponse } from "@/lib/sim";

const BACKEND_HINT =
  "无法连接后端。请确认 web_api 已启动：.venv\\Scripts\\python.exe -m uvicorn web_api.main:app --port 8000";

/** 一侧（攻/守）的阵营+单位选择状态 */
function useSideUnits(onError: (msg: string) => void) {
  const [factionId, setFactionId] = useState<string | null>(null);
  const [units, setUnits] = useState<UnitRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [unit, setUnit] = useState<UnitRow | null>(null);

  useEffect(() => {
    if (!factionId) return;
    const ctrl = new AbortController();
    fetchUnits(factionId, ctrl.signal)
      .then(setUnits)
      .catch((e) => {
        if ((e as Error).name !== "AbortError") onError(BACKEND_HINT);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [factionId, onError]);

  const selectFaction = (id: string) => {
    if (id === factionId) return;
    setUnits([]);
    setUnit(null);
    setLoading(true);
    setFactionId(id);
  };

  return { factionId, units, loading, unit, setUnit, selectFaction, setFactionId, setLoading };
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-1.5 text-[13px] text-[#a9bcb6] select-none hover:text-bone">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 accent-[#175966]"
      />
      {label}
    </label>
  );
}

/**
 * 模拟器页（Stage 4）：攻/守单位选择 + 姿态开关 → POST /simulate →
 * KPI/漏斗/击杀分布可视化。多武器单位先按后端返回的武器池装配再模拟（不猜默认装备）。
 */
export default function SimulatorPage() {
  const [factions, setFactions] = useState<FactionRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const onError = useCallback((msg: string) => setError(msg), []);
  const atk = useSideUnits(onError);
  const dfd = useSideUnits(onError);

  // 姿态与守方 opt-in（射击/近战各自的开关，语义与后端白名单一致）
  const [phase, setPhase] = useState<"shooting" | "melee">("shooting");
  const [stationary, setStationary] = useState(false);
  const [halfRange, setHalfRange] = useState(false);
  const [cover, setCover] = useState(false);
  const [indirect, setIndirect] = useState(false);
  const [charge, setCharge] = useState(false);
  const [stealth, setStealth] = useState(false);
  const [fnp, setFnp] = useState(0); // 0 = 无
  const [dmgReduction, setDmgReduction] = useState(false);
  const [aModels, setAModels] = useState("");
  const [dModels, setDModels] = useState("");

  const [loadout, setLoadout] = useState<Record<string, number>>({});
  const [resp, setResp] = useState<SimResponse | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchFactions(ctrl.signal)
      .then((fs) => {
        setFactions(fs);
        if (fs[0]) {
          atk.setLoading(true);
          atk.setFactionId(fs[0].id);
          dfd.setLoading(true);
          dfd.setFactionId(fs[0].id);
        }
      })
      .catch((e) => {
        if ((e as Error).name !== "AbortError") setError(BACKEND_HINT);
      });
    return () => ctrl.abort();
    // atk/dfd 的 setter 引用稳定（useState），仅首载执行一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 换攻方单位：装配与结果作废（武器池是单位私有的）
  const pickAttacker = (u: UnitRow) => {
    atk.setUnit(u);
    setLoadout({});
    setResp(null);
  };
  // 换阶段：装配也作废——近战/射击武器池不同，跨阶段沿用会被引擎静默滤成空手 0 伤
  const switchPhase = (p: "shooting" | "melee") => {
    if (p === phase) return;
    setPhase(p);
    setLoadout({});
    setResp(null);
  };
  const pickDefender = (u: UnitRow) => {
    dfd.setUnit(u);
    setResp(null);
  };

  const buildOptions = (): SimOptions => {
    const opts: SimOptions = { phase };
    if (phase === "shooting") {
      if (stationary) opts.stationary = true;
      if (halfRange) opts.half_range = true;
      if (cover) opts.cover = true;
      if (indirect) opts.indirect = true;
      if (stealth) opts.stealth = true;
    } else if (charge) {
      opts.charge = true;
    }
    if (fnp) opts.fnp = fnp;
    if (dmgReduction) opts.damage_reduction = 1;
    const am = parseInt(aModels, 10);
    if (am > 0) opts.attacker_models = am;
    const dm = parseInt(dModels, 10);
    if (dm > 0) opts.defender_models = dm;
    const picked = Object.entries(loadout).filter(([, c]) => c > 0);
    if (picked.length > 0) opts.loadout = picked.map(([w, c]) => [w, c]);
    return opts;
  };

  const run = () => {
    if (!atk.unit || !dfd.unit || running) return;
    setRunning(true);
    setError(null);
    postSimulate(atk.unit.id, dfd.unit.id, buildOptions())
      .then(setResp)
      .catch((e) => {
        setError(e instanceof Error && e.message.includes("后端返回")
          ? `模拟失败（${e.message}）`
          : BACKEND_HINT);
      })
      .finally(() => setRunning(false));
  };

  const needLoadout = resp != null && !resp.ok && resp.reason === "loadout_required";
  const failedOther = resp != null && !resp.ok && resp.reason !== "loadout_required";
  const atkLabel = atk.unit ? (atk.unit.nameZh ?? atk.unit.nameEn) : "";
  const dfdLabel = dfd.unit ? (dfd.unit.nameZh ?? dfd.unit.nameEn) : "";

  return (
    <>
      <SiteHeader context="模拟器 · SIMULATOR" active="模拟器" />
      <main className="mx-auto max-w-[1100px] px-5 pt-[22px] pb-20 max-tablet:px-2.5 max-tablet:pt-4">
        {error ? (
          <p className="mb-4 border border-redfont/40 bg-[#1a0d0d] px-4 py-3 font-mono text-[12.5px] break-all text-[#d99]">
            {error}
          </p>
        ) : null}

        {/* 攻守选择 */}
        <div className="grid grid-cols-2 gap-4 max-tablet:grid-cols-1">
          <UnitPicker
            label="攻方"
            accent="red"
            factions={factions}
            factionId={atk.factionId}
            units={atk.units}
            loadingUnits={atk.loading}
            selected={atk.unit}
            onFaction={atk.selectFaction}
            onUnit={pickAttacker}
          />
          <UnitPicker
            label="守方"
            accent="cyan"
            factions={factions}
            factionId={dfd.factionId}
            units={dfd.units}
            loadingUnits={dfd.loading}
            selected={dfd.unit}
            onFaction={dfd.selectFaction}
            onUnit={pickDefender}
          />
        </div>

        {/* 姿态与开关 */}
        <section className="clip-plate-10 mt-4 border border-panel-line bg-panel px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2.5">
            <div className="flex">
              {(["shooting", "melee"] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => switchPhase(p)}
                  className={`clip-slant-8 px-4 py-1 font-cond text-[13px] tracking-[2px] uppercase ${
                    phase === p
                      ? "bg-[linear-gradient(var(--color-gw-red),#6e0505)] text-white"
                      : "bg-[#16211f] text-[#97a4a0] hover:text-bone"
                  }`}
                >
                  {p === "shooting" ? "射击" : "近战"}
                </button>
              ))}
            </div>
            {phase === "shooting" ? (
              <>
                <Toggle label="未移动" checked={stationary} onChange={setStationary} />
                <Toggle label="半程" checked={halfRange} onChange={setHalfRange} />
                <Toggle label="目标在掩体" checked={cover} onChange={setCover} />
                <Toggle label="间瞄" checked={indirect} onChange={setIndirect} />
                <Toggle label="守方隐身" checked={stealth} onChange={setStealth} />
              </>
            ) : (
              <Toggle label="冲锋" checked={charge} onChange={setCharge} />
            )}
            <label className="flex items-center gap-1.5 text-[13px] text-[#a9bcb6]">
              守方无痛
              <select
                value={fnp}
                onChange={(e) => setFnp(Number(e.target.value))}
                className="border border-[#2b423d] bg-dark px-1.5 py-0.5 text-[12.5px] text-bone outline-none"
              >
                <option value={0}>无</option>
                <option value={4}>4+</option>
                <option value={5}>5+</option>
                <option value={6}>6+</option>
              </select>
            </label>
            <Toggle label="守方减伤 1" checked={dmgReduction} onChange={setDmgReduction} />
            <label className="flex items-center gap-1.5 text-[13px] text-[#a9bcb6]">
              攻方模型数
              <input
                type="number"
                min={1}
                value={aModels}
                onChange={(e) => setAModels(e.target.value)}
                placeholder="默认"
                className="w-[58px] border border-[#2b423d] bg-dark px-1.5 py-0.5 text-[12.5px] text-bone outline-none placeholder:text-[#5c6f6a]"
              />
            </label>
            <label className="flex items-center gap-1.5 text-[13px] text-[#a9bcb6]">
              守方模型数
              <input
                type="number"
                min={1}
                value={dModels}
                onChange={(e) => setDModels(e.target.value)}
                placeholder="默认"
                className="w-[58px] border border-[#2b423d] bg-dark px-1.5 py-0.5 text-[12.5px] text-bone outline-none placeholder:text-[#5c6f6a]"
              />
            </label>
            <button
              type="button"
              onClick={run}
              disabled={!atk.unit || !dfd.unit || running}
              className="clip-slant-14 ml-auto bg-[linear-gradient(var(--color-gw-red),#6e0505)] px-7 py-1.5 font-cond text-[14px] font-bold tracking-[3px] text-white uppercase [text-shadow:0_1px_2px_#000] not-disabled:hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {running ? "解算中…" : "开始模拟"}
            </button>
          </div>
        </section>

        {/* 多武器单位：先装配（后端不猜默认装备，武器池来自权威表） */}
        {needLoadout ? (
          <section className="mt-4 border border-gold/40 bg-[#141207] px-4 py-3">
            <div className="mb-1 font-cond text-[13px] tracking-[2px] text-gold uppercase">
              需先装配攻方武器
            </div>
            <p className="mb-2.5 text-[12.5px] text-[#b8ab88]">
              {resp?.note || "该单位有多把可选武器，指定每把带几件再模拟（不猜默认装备）。"}
              {resp?.modelTiers?.length ? (
                <span className="ml-1 font-mono text-[11.5px] text-[#8a7f60]">
                  点数档位：
                  {resp.modelTiers
                    .map((t) => `${t.models} 模型${t.cost != null ? ` ${t.cost} 分` : ""}`)
                    .join(" / ")}
                </span>
              ) : null}
            </p>
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {(resp?.weaponPool ?? []).map((w) => (
                <label key={w} className="flex items-center gap-1.5 text-[13px] text-[#d8cba6]">
                  <input
                    type="number"
                    min={0}
                    value={loadout[w] ?? ""}
                    onChange={(e) =>
                      setLoadout((prev) => ({
                        ...prev,
                        [w]: parseInt(e.target.value, 10) || 0,
                      }))
                    }
                    placeholder="0"
                    className="w-[52px] border border-[#4a4326] bg-dark px-1.5 py-0.5 text-[12.5px] text-bone outline-none placeholder:text-[#5c6f6a]"
                  />
                  ×{w}
                </label>
              ))}
            </div>
          </section>
        ) : null}

        {failedOther ? (
          <p className="mt-4 border border-redfont/40 bg-[#1a0d0d] px-4 py-3 text-[13px] text-[#d99]">
            {resp?.note || "模拟失败"}
          </p>
        ) : null}

        <div className="mt-4">
          {resp?.ok && resp.report ? (
            <SimResults resp={resp} attackerLabel={atkLabel} defenderLabel={dfdLabel} />
          ) : !resp ? (
            <div className="border border-dashed border-panel-line bg-[#0d1517] px-4 py-14 text-center font-cond text-[14px] tracking-[1px] text-[#5c6f6a] uppercase">
              选择攻守单位，设定姿态，开始逐骰蒙特卡洛解算
            </div>
          ) : null}
        </div>
      </main>
    </>
  );
}
