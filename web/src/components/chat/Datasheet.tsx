import type { EntityCard, WeaponRow } from "@/lib/answer";
import { KwBar } from "../ui/KwBar";
import { Rich } from "../ui/Rich";
import { SlotBadge } from "../ui/SlotBadge";
import { StatBox } from "../ui/StatBox";

interface WeaponTableProps {
  caption: string;
  sig: string; // 表头符号 ➶ / ⚔
  skillHead: "BS" | "WS";
  rows: WeaponRow[];
}

function WeaponTable({ caption, sig, skillHead, rows }: WeaponTableProps) {
  return (
    <>
      <div className="flex items-center gap-2 bg-dark px-2.5 py-1 font-cond text-[12.5px] font-bold tracking-[2px] text-[#fefefe] uppercase">
        <span className="text-[13px] text-cyan-glow">{sig}</span> {caption}
      </div>
      <div className="mb-3 overflow-x-auto">
        <table className="tbl-wp">
          <thead>
            <tr>
              <th>武器</th>
              <th>射程</th>
              <th>A</th>
              <th>{skillHead}</th>
              <th>S</th>
              <th>AP</th>
              <th>D</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((w) => (
              <tr key={w.name} className={w.hot ? "hot" : undefined}>
                <td>
                  {w.name}
                  {w.kw ? <span className="kw">{w.kw}</span> : null}
                </td>
                <td className="num">{w.range}</td>
                <td className="num">{w.a}</td>
                <td className="num">{w.skill}</td>
                <td className="num">{w.s}</td>
                <td className="num">{w.ap}</td>
                <td className="num">{w.d}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

interface DatasheetProps {
  card: EntityCard;
}

/** E6 官方版式兵牌（Wahapedia datasheet 复刻） */
export function Datasheet({ card }: DatasheetProps) {
  return (
    <div className="relative mb-[18px] border border-black bg-bone text-ink shadow-[0_8px_30px_rgba(0,0,0,.55)]">
      <SlotBadge id="E6" />
      {/* 头部横幅：阵营渐变 + 噪纹 */}
      <div className="relative overflow-hidden bg-[linear-gradient(100deg,var(--color-tau-ban)_0%,#10424d_55%,var(--color-dark)_100%)] px-[18px] pt-3 pb-2.5 text-[#fefefe] after:pointer-events-none after:absolute after:inset-0 after:bg-[repeating-linear-gradient(115deg,rgba(255,255,255,.03)_0_2px,transparent_2px_6px)] after:content-[''] max-tablet:px-3 max-tablet:pt-2.5 max-tablet:pb-2">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="font-body text-[24px] font-extrabold tracking-[2px] [text-shadow:0_1px_3px_rgba(0,0,0,.5)] max-tablet:text-[19px]">
            {card.nameZh}
          </span>
          <span className="font-cond text-[14px] tracking-[2.5px] text-[#bcd6d4] uppercase max-tablet:text-[12px] max-tablet:tracking-[1.5px]">
            {card.nameEn}
          </span>
          <span className="ml-auto border border-bone/25 bg-[rgba(11,23,27,.65)] px-3 py-[3px] font-cond text-[15px] font-bold tracking-[1px] max-tablet:mt-1 max-tablet:ml-0 max-tablet:flex-[1_1_100%] max-tablet:text-center">
            <small className="mr-1.5 font-normal tracking-[2px] opacity-75">
              PTS
            </small>
            {card.pts}
          </span>
        </div>
        <div className="relative z-[1] mt-2.5 flex gap-3.5 max-wide:flex-wrap max-tablet:justify-center max-tablet:gap-2">
          {card.stats.map((s) => (
            <StatBox key={s.lab} lab={s.lab} val={s.val} />
          ))}
        </div>
      </div>
      {/* 主体：武器表 + 技能侧栏 */}
      <div className="grid grid-cols-[1fr_320px] max-wide:grid-cols-1">
        <div className="min-w-0 border-r-2 border-tau-ban px-3.5 pt-3 pb-3.5 max-wide:border-r-0 max-wide:border-b-2 max-tablet:px-2.5 max-tablet:pt-2.5 max-tablet:pb-3">
          <WeaponTable
            caption="远程武器 · Ranged Weapons"
            sig="➶"
            skillHead="BS"
            rows={card.ranged}
          />
          <WeaponTable
            caption="近战武器 · Melee Weapons"
            sig="⚔"
            skillHead="WS"
            rows={card.melee}
          />
        </div>
        <aside className="min-w-0 bg-[#eef0e8] px-3.5 pt-3 pb-3.5 max-tablet:px-2.5 max-tablet:pt-2.5 max-tablet:pb-3">
          <h4 className="mb-2 border-b-2 border-tau-ban pb-[3px] font-cond text-[12.5px] tracking-[2px] text-tau-ban uppercase">
            技能 · Abilities
          </h4>
          {card.abilities.map((a) => (
            <div
              key={a.name}
              className="border-b border-dotted border-ink py-1.5 text-[12.8px] text-[#23261f] last:border-b-0"
            >
              {a.tag ? (
                <span className="mr-[5px] font-cond text-[10.5px] font-bold tracking-[1.5px] text-gw-red uppercase">
                  {a.tag}
                </span>
              ) : null}
              <b className="text-ink">{a.name}</b>
              {a.text ? <>：{a.text}</> : null}
            </div>
          ))}
          <div className="mt-3">
            <h4 className="mb-2 border-b-2 border-tau-ban pb-[3px] font-cond text-[12.5px] tracking-[2px] text-tau-ban uppercase">
              单位构成
            </h4>
            {card.composition.map((line, i) => (
              <p key={i} className="py-[3px] text-[12.5px] text-[#3a3e34]">
                <Rich text={line} numClass="font-cond font-bold" />
              </p>
            ))}
          </div>
        </aside>
      </div>
      <KwBar faction={card.faction}>{card.keywords}</KwBar>
      <div className="flex flex-wrap gap-3.5 bg-[#10191c] px-3.5 py-1 font-mono text-[11px] text-[#7a8f89] max-tablet:gap-1.5 max-tablet:text-[10px]">
        <span>{card.src}</span>
        <span>{card.wiki}</span>
      </div>
    </div>
  );
}
