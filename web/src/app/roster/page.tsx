"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { SiteHeader } from "@/components/chat/SiteHeader";
import { CritiquePanel } from "@/components/roster/CritiquePanel";
import {
  RosterUnitRow,
  type RosterUnitState,
} from "@/components/roster/RosterUnitRow";
import { ValidationPanel } from "@/components/roster/ValidationPanel";
import {
  fetchFactions,
  fetchUnits,
  type FactionRow,
  type UnitRow,
} from "@/lib/codex";
import {
  fetchDetachments,
  fetchEnhancements,
  fetchUnitWeapons,
  postCritique,
  postValidate,
  SIZE_LABELS,
  type CritiqueReport,
  type Detachment,
  type Enhancement,
  type RosterPayload,
  type RosterSize,
  type ValidationReport,
} from "@/lib/roster";

const BACKEND_HINT =
  "无法连接后端。请确认 web_api 已启动：.venv\\Scripts\\python.exe -m uvicorn web_api.main:app --port 8000";

function toPayload(
  factionId: string,
  detachmentId: string | null,
  size: RosterSize,
  units: RosterUnitState[],
): RosterPayload {
  return {
    factionId,
    detachmentId,
    size,
    units: units.map((u) => ({
      canonicalId: u.canonicalId,
      nameEn: u.nameEn,
      models: u.models,
      isWarlord: u.isWarlord,
      enhancement: u.enhancement,
      loadout: Object.entries(u.loadout)
        .filter(([, c]) => c > 0)
        .map(([w, c]) => [w, c] as [string, number]),
    })),
  };
}

export default function RosterPage() {
  const [factions, setFactions] = useState<FactionRow[]>([]);
  const [factionId, setFactionId] = useState<string | null>(null);
  const [detachments, setDetachments] = useState<Detachment[]>([]);
  const [detachmentId, setDetachmentId] = useState<string | null>(null);
  const [enhancements, setEnhancements] = useState<Enhancement[]>([]);
  const [size, setSize] = useState<RosterSize>("strike_force");

  const [factionUnits, setFactionUnits] = useState<UnitRow[]>([]);
  const [query, setQuery] = useState("");
  const [units, setUnits] = useState<RosterUnitState[]>([]);

  const [validation, setValidation] = useState<ValidationReport | null>(null);
  // 点评带它算出时的军表签名，编制一变即视为过期（不用 effect 清）
  const [critique, setCritique] = useState<{ sig: string; report: CritiqueReport } | null>(
    null,
  );
  const [critiquing, setCritiquing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uidRef = useRef(1);
  const onErr = useCallback((e: unknown) => {
    if ((e as Error).name === "AbortError") return;
    setError(BACKEND_HINT);
  }, []);

  // 首载阵营
  useEffect(() => {
    const ctrl = new AbortController();
    fetchFactions(ctrl.signal)
      .then((fs) => {
        setFactions(fs);
        if (fs[0]) setFactionId(fs[0].id);
      })
      .catch(onErr);
    return () => ctrl.abort();
  }, [onErr]);

  // 换阵营：拉分队 + 单位（清空军表在 selectFaction 处理器里同步做）
  useEffect(() => {
    if (!factionId) return;
    const ctrl = new AbortController();
    Promise.all([
      fetchDetachments(factionId, ctrl.signal).then(setDetachments),
      fetchUnits(factionId, ctrl.signal).then(setFactionUnits),
    ]).catch(onErr);
    return () => ctrl.abort();
  }, [factionId, onErr]);

  // 换分队：拉强化清单（清空在 onChange 处理器里做，effect 只管异步取）
  useEffect(() => {
    if (!detachmentId) return;
    const ctrl = new AbortController();
    fetchEnhancements(detachmentId, ctrl.signal).then(setEnhancements).catch(onErr);
    return () => ctrl.abort();
  }, [detachmentId, onErr]);

  // 换阵营处理器：单位/分队/强化/旧阵营单位目录/校验结果都作废（阵营私有）
  const selectFaction = (id: string) => {
    if (id === factionId) return;
    setUnits([]);
    setDetachmentId(null);
    setEnhancements([]);
    setFactionUnits([]); // 清旧阵营单位目录，防搜索框加进跨阵营单位
    setQuery("");
    setValidation(null); // 清旧阵营校验结果，防加首个新单位时闪现旧阵营点数/合法性
    setFactionId(id);
  };
  // 换分队：强化目录换新 + 各单位已选强化作废（强化是分队私有的）
  const selectDetachment = (id: string) => {
    setDetachmentId(id || null);
    if (!id) setEnhancements([]);
    setUnits((prev) => prev.map((u) => ({ ...u, enhancement: null })));
  };

  // 实时校验（debounce）：军表编制相关状态变化即重算（不含 loadout——验表不用装配）
  const validationSig = useMemo(
    () =>
      JSON.stringify({
        d: detachmentId,
        s: size,
        u: units.map((u) => [u.canonicalId, u.models, u.isWarlord, u.enhancement]),
      }),
    [detachmentId, size, units],
  );
  // 点评额外依赖 loadout——单独签名，改装备后旧点评视为过期
  const critiqueSig = useMemo(
    () =>
      JSON.stringify({
        v: validationSig,
        l: units.map((u) => [u.canonicalId, u.loadout]),
      }),
    [validationSig, units],
  );
  useEffect(() => {
    if (!factionId || units.length === 0) return; // 空表不请求；显示层按 units.length 派生
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      postValidate(toPayload(factionId, detachmentId, size, units), ctrl.signal)
        .then((r) => {
          setValidation(r);
          setError(null); // 成功即清错误横幅，防一次瞬时失败后永久卡显
        })
        .catch(onErr);
    }, 300);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
    // validationSig 覆盖 units/detachment/size；factionId 稳定
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [validationSig, factionId, onErr]);

  const addUnit = (u: UnitRow) => {
    setUnits((prev) => [
      ...prev,
      {
        uid: uidRef.current++,
        canonicalId: u.id,
        nameEn: u.nameEn,
        nameZh: u.nameZh,
        models: 1,
        isWarlord: false,
        enhancement: null,
        loadout: {},
        weaponPool: null,
        expanded: false,
      },
    ]);
    setQuery("");
  };

  const patch = (uid: number, f: (u: RosterUnitState) => RosterUnitState) =>
    setUnits((prev) => prev.map((u) => (u.uid === uid ? f(u) : u)));

  const toggleExpand = (uid: number) => {
    patch(uid, (u) => ({ ...u, expanded: !u.expanded }));
    const target = units.find((u) => u.uid === uid);
    if (target && !target.expanded && target.weaponPool === null) {
      fetchUnitWeapons(target.canonicalId)
        .then((pool) => patch(uid, (u) => ({ ...u, weaponPool: pool })))
        .catch(onErr);
    }
  };

  const runCritique = () => {
    if (!factionId || units.length === 0 || critiquing) return;
    setCritiquing(true);
    setError(null);
    const sig = critiqueSig;
    postCritique(toPayload(factionId, detachmentId, size, units))
      .then((report) => setCritique({ sig, report }))
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        setError(
          e instanceof Error && e.message.includes("后端返回")
            ? `点评失败（${e.message}）`
            : BACKEND_HINT,
        );
      })
      .finally(() => setCritiquing(false));
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return factionUnits
      .filter(
        (u) =>
          u.nameEn.toLowerCase().includes(q) ||
          (u.nameZh ?? "").toLowerCase().includes(q),
      )
      .slice(0, 12);
  }, [factionUnits, query]);

  return (
    <>
      <SiteHeader context="军表实验室 · ROSTER" active="军表实验室" />
      <main className="mx-auto max-w-[1180px] px-5 pt-[22px] pb-20 max-tablet:px-2.5 max-tablet:pt-4">
        {error ? (
          <p className="mb-4 border border-redfont/40 bg-[#1a0d0d] px-4 py-3 font-mono text-[12.5px] break-all text-[#d99]">
            {error}
          </p>
        ) : null}

        {/* 阵营 / 分队 / 规模 */}
        <section className="clip-plate-10 mb-4 flex flex-wrap items-center gap-x-4 gap-y-2 border border-panel-line bg-panel px-4 py-3">
          <label className="flex items-center gap-1.5 text-[13px] text-[#a9bcb6]">
            阵营
            <select
              value={factionId ?? ""}
              onChange={(e) => selectFaction(e.target.value)}
              className="border border-[#2b423d] bg-dark px-2 py-1 text-[13px] text-bone outline-none focus:border-tau"
            >
              {factions.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.nameZh ?? f.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-1.5 text-[13px] text-[#a9bcb6]">
            分队
            <select
              value={detachmentId ?? ""}
              onChange={(e) => selectDetachment(e.target.value)}
              className="max-w-[240px] border border-[#2b423d] bg-dark px-2 py-1 text-[13px] text-bone outline-none focus:border-tau"
            >
              <option value="">未选（强化不校验）</option>
              {detachments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-1.5 text-[13px] text-[#a9bcb6]">
            规模
            <select
              value={size}
              onChange={(e) => setSize(e.target.value as RosterSize)}
              className="border border-[#2b423d] bg-dark px-2 py-1 text-[13px] text-bone outline-none focus:border-tau"
            >
              {(Object.keys(SIZE_LABELS) as RosterSize[]).map((s) => (
                <option key={s} value={s}>
                  {SIZE_LABELS[s]}
                </option>
              ))}
            </select>
          </label>
        </section>

        <div className="grid grid-cols-[1fr_380px] gap-4 max-tablet:grid-cols-1">
          {/* 左：搭表 */}
          <div>
            <div className="relative mb-3">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索单位加入军表…"
                className="w-full border border-[#2b423d] bg-dark px-3 py-2 text-[13px] text-bone outline-none placeholder:text-[#5c6f6a] focus:border-tau max-tablet:text-[16px]"
              />
              {filtered.length > 0 ? (
                <ul className="absolute z-10 mt-0.5 max-h-[260px] w-full overflow-y-auto border border-panel-line bg-[#0d1517] shadow-[0_8px_24px_rgba(0,0,0,.6)]">
                  {filtered.map((u) => (
                    <li key={u.id}>
                      <button
                        type="button"
                        onClick={() => addUnit(u)}
                        className="flex w-full items-baseline justify-between border-b border-[#1a2624] px-3 py-1.5 text-left hover:bg-[#14262a]"
                      >
                        <span className="text-[13px] text-bone">
                          {u.nameZh ?? u.nameEn}
                        </span>
                        {u.pts ? (
                          <span className="font-cond text-[11px] text-gold">{u.pts}</span>
                        ) : null}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>

            {units.length === 0 ? (
              <div className="border border-dashed border-panel-line bg-[#0d1517] px-4 py-12 text-center font-cond text-[13px] tracking-[1px] text-[#5c6f6a] uppercase">
                搜索并加入单位开始搭建军表
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {units.map((u) => (
                  <RosterUnitRow
                    key={u.uid}
                    unit={u}
                    enhancements={enhancements}
                    onModels={(uid, v) => patch(uid, (x) => ({ ...x, models: v }))}
                    onWarlord={(uid, v) => patch(uid, (x) => ({ ...x, isWarlord: v }))}
                    onEnhancement={(uid, v) =>
                      patch(uid, (x) => ({ ...x, enhancement: v }))
                    }
                    onToggleExpand={toggleExpand}
                    onLoadout={(uid, w, c) =>
                      patch(uid, (x) => ({ ...x, loadout: { ...x.loadout, [w]: c } }))
                    }
                    onRemove={(uid) =>
                      setUnits((prev) => prev.filter((x) => x.uid !== uid))
                    }
                  />
                ))}
              </div>
            )}
          </div>

          {/* 右：校验 + 点评 */}
          <div className="flex flex-col gap-3">
            <ValidationPanel report={units.length ? validation : null} />
            <button
              type="button"
              onClick={runCritique}
              disabled={units.length === 0 || critiquing}
              className="clip-slant-14 bg-[linear-gradient(var(--color-tau-ban),#0e3b44)] px-6 py-2 font-cond text-[13px] font-bold tracking-[2px] text-white uppercase not-disabled:hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {critiquing ? "点评解算中…" : "强度点评"}
            </button>
            <CritiquePanel
              report={critique && critique.sig === critiqueSig ? critique.report : null}
              loading={critiquing}
            />
          </div>
        </div>
      </main>
    </>
  );
}
