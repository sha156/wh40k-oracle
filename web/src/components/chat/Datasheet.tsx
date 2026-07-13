import type { Ability, EntityCard, WeaponRow } from "@/lib/answer";
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
  if (rows.length === 0) return null;
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

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="mb-2 border-b-2 border-tau-ban pb-[3px] font-cond text-[12.5px] tracking-[2px] text-tau-ban uppercase">
      {children}
    </h4>
  );
}

function AbilityRow({ ability }: { ability: Ability }) {
  return (
    <div className="border-b border-dotted border-[#c2c6b8] py-[7px] text-[12.8px] leading-[1.55] text-[#23261f] last:border-b-0">
      {ability.tag ? (
        <span className="mr-[6px] inline-block bg-gw-red/12 px-[5px] py-px font-cond text-[10.5px] font-bold tracking-[1.2px] text-gw-red uppercase">
          {ability.tag}
        </span>
      ) : null}
      <b className="text-ink">{ability.name}</b>
      {ability.text ? <span className="text-[#3a3e34]">：{ability.text}</span> : null}
    </div>
  );
}

interface DatasheetProps {
  card: EntityCard;
  /** EN 模式：头部主名显英文、副名显中文（数据本身由后端按 lang 装配） */
  primaryEn?: boolean;
}

/** E6 官方版式兵牌（Wahapedia datasheet 复刻：属性/武器/能力/装备/关键词全档） */
export function Datasheet({ card, primaryEn = false }: DatasheetProps) {
  const bigName = primaryEn ? card.nameEn : card.nameZh;
  const smallName = primaryEn ? card.nameZh : card.nameEn;
  return (
    // @container：内部双栏/单栏按「容器」宽度切换（图鉴详情栏 ~740px 单栏免横滑，
    // 聊天页 ~1060px 双栏），不看视口
    <div className="@container relative mb-[18px] border border-black bg-bone text-ink shadow-[0_8px_30px_rgba(0,0,0,.55)]">
      <SlotBadge id="E6" />
      {/* 头部横幅：阵营渐变 + 噪纹 */}
      <div className="relative overflow-hidden bg-[linear-gradient(100deg,var(--color-tau-ban)_0%,#10424d_55%,var(--color-dark)_100%)] px-[18px] pt-3 pb-2.5 text-[#fefefe] after:pointer-events-none after:absolute after:inset-0 after:bg-[repeating-linear-gradient(115deg,rgba(255,255,255,.03)_0_2px,transparent_2px_6px)] after:content-[''] max-tablet:px-3 max-tablet:pt-2.5 max-tablet:pb-2">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="font-body text-[24px] font-extrabold tracking-[2px] [text-shadow:0_1px_3px_rgba(0,0,0,.5)] max-tablet:text-[19px]">
            {bigName}
          </span>
          <span className="font-cond text-[14px] tracking-[2.5px] text-[#bcd6d4] uppercase max-tablet:text-[12px] max-tablet:tracking-[1.5px]">
            {smallName}
          </span>
          {card.role ? (
            <span className="border border-bone/25 px-2 py-px font-cond text-[11px] tracking-[1.5px] text-[#bcd6d4] uppercase">
              {card.role}
            </span>
          ) : null}
          <span className="ml-auto border border-bone/25 bg-[rgba(11,23,27,.65)] px-3 py-[3px] font-cond text-[15px] font-bold tracking-[1px] max-tablet:mt-1 max-tablet:ml-0 max-tablet:flex-[1_1_100%] max-tablet:text-center">
            <small className="mr-1.5 font-normal tracking-[2px] opacity-75">PTS</small>
            {card.pts}
          </span>
        </div>
        <div className="relative z-[1] mt-2.5 flex flex-wrap items-center gap-3.5 max-tablet:justify-center max-tablet:gap-2">
          {card.stats.map((s) => (
            <StatBox key={s.lab} lab={s.lab} val={s.val} />
          ))}
          {card.invuln ? (
            <span className="flex items-center gap-1.5 border border-bone/30 bg-[rgba(11,23,27,.55)] px-2.5 py-1.5 font-cond text-[13px] tracking-[1px]">
              <span className="tracking-[2px] opacity-75">INV SV</span>
              <b className="text-[16px]">{card.invuln}</b>
            </span>
          ) : null}
        </div>
      </div>

      {/* 主体：左 = 武器 + 能力；右 = 装备/构成/关键词侧栏 */}
      <div className="grid grid-cols-[1fr_300px] @max-4xl:grid-cols-1">
        <div className="min-w-0 border-r-2 border-tau-ban px-3.5 pt-3 pb-3.5 @max-4xl:border-r-0 @max-4xl:border-b-2 max-tablet:px-2.5 max-tablet:pt-2.5 max-tablet:pb-3">
          <WeaponTable caption="远程武器 · Ranged Weapons" sig="➶" skillHead="BS" rows={card.ranged} />
          <WeaponTable caption="近战武器 · Melee Weapons" sig="⚔" skillHead="WS" rows={card.melee} />

          {card.abilities.length > 0 ? (
            <div className="mt-3">
              <SectionTitle>技能 · Abilities</SectionTitle>
              {card.abilities.map((a, i) => (
                <AbilityRow key={`${a.name}-${i}`} ability={a} />
              ))}
            </div>
          ) : null}

          {card.damaged ? (
            <div className="mt-3 border-l-4 border-gw-red bg-[#f3e6e6] px-3 py-2 text-[12.5px] leading-[1.55] text-[#23261f]">
              <b className="font-cond tracking-[1px] text-gw-red uppercase">
                受损 · Damaged {card.damaged.w}
              </b>
              <span>：{card.damaged.text}</span>
            </div>
          ) : null}
        </div>

        <aside className="min-w-0 bg-[#eef0e8] px-3.5 pt-3 pb-3.5 max-tablet:px-2.5 max-tablet:pt-2.5 max-tablet:pb-3">
          {card.loadout ? (
            <div className="mb-3">
              <SectionTitle>默认装备 · Loadout</SectionTitle>
              <p className="text-[12.5px] leading-[1.55] text-[#3a3e34]">{card.loadout}</p>
            </div>
          ) : null}

          <SectionTitle>单位构成</SectionTitle>
          {card.composition.map((line, i) => (
            <p key={i} className="py-[3px] text-[12.5px] text-[#3a3e34]">
              <Rich text={line} numClass="font-cond font-bold" />
            </p>
          ))}

          {card.leads ? (
            <div className="mt-3">
              <SectionTitle>可依附 · Leader</SectionTitle>
              <p className="text-[12px] leading-[1.5] text-[#3a3e34]">{card.leads}</p>
            </div>
          ) : null}

          {card.legend ? (
            <p className="mt-3 border-t border-dotted border-[#b7bbad] pt-2 text-[11.5px] leading-[1.5] text-[#6a6f5f] italic">
              {card.legend}
            </p>
          ) : null}
        </aside>
      </div>

      <KwBar faction={card.faction}>{card.keywords}</KwBar>
      {card.factionKeywords ? (
        <div className="flex flex-wrap items-baseline gap-2 bg-[#0e1619] px-3.5 py-1.5 font-cond text-[11.5px] tracking-[1px] text-[#8fa39d]">
          <span className="text-[10.5px] tracking-[2px] text-[#5e716b] uppercase">
            阵营关键词
          </span>
          {card.factionKeywords}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-3.5 bg-[#10191c] px-3.5 py-1 font-mono text-[11px] text-[#7a8f89] max-tablet:gap-1.5 max-tablet:text-[10px]">
        <span>{card.src}</span>
        <span>{card.wiki}</span>
      </div>
    </div>
  );
}
