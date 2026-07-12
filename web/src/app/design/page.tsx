import type { ReactNode } from "react";
import { ClipPanel } from "@/components/ui/ClipPanel";
import { KwBar } from "@/components/ui/KwBar";
import { PlateButton } from "@/components/ui/PlateButton";
import { Rich } from "@/components/ui/Rich";
import { StatBox } from "@/components/ui/StatBox";
import { VerdictShield } from "@/components/ui/VerdictShield";
import { WaxSeal } from "@/components/ui/WaxSeal";

const COLORS: { name: string; varName: string; hex: string }[] = [
  { name: "dark", varName: "--color-dark", hex: "#0b171b" },
  { name: "ink", varName: "--color-ink", hex: "#101010" },
  { name: "bone", varName: "--color-bone", hex: "#e7e9e1" },
  { name: "bone-dim", varName: "--color-bone-dim", hex: "#d8dbd2" },
  { name: "zebra", varName: "--color-zebra", hex: "#dfe0da" },
  { name: "tau-ban", varName: "--color-tau-ban", hex: "#175966" },
  { name: "tau", varName: "--color-tau", hex: "#2e5a6a" },
  { name: "gw-red", varName: "--color-gw-red", hex: "#990000" },
  { name: "redfont", varName: "--color-redfont", hex: "#a31317" },
  { name: "first", varName: "--color-first", hex: "#cc0000" },
  { name: "gold", varName: "--color-gold", hex: "#b08d3f" },
  { name: "amber", varName: "--color-amber", hex: "#c9930a" },
  { name: "grey-head", varName: "--color-grey-head", hex: "#b2b2b2" },
  { name: "panel", varName: "--color-panel", hex: "#0d1517" },
  { name: "panel-line", varName: "--color-panel-line", hex: "#22332f" },
  { name: "sage", varName: "--color-sage", hex: "#9fb4ae" },
  { name: "cyan-glow", varName: "--color-cyan-glow", hex: "#6fc3d4" },
];

const CLIPS = [
  "clip-plate-10",
  "clip-plate-14",
  "clip-notch-18",
  "clip-slant-8",
  "clip-slant-14",
  "clip-slant-l-12",
  "clip-statbox",
  "clip-parchment",
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="mb-4 border-b border-panel-line pb-1 font-cond text-[16px] tracking-[3px] text-sage uppercase">
        {title}
      </h2>
      {children}
    </section>
  );
}

/** Stage 1 kitchen-sink：tokens 与六基础组件一页过目（不进导航，仅 /design 直达） */
export default function DesignPage() {
  return (
    <main className="mx-auto max-w-[1100px] px-5 py-8">
      <h1 className="mb-1 font-cond text-[28px] tracking-[3px] text-bone uppercase">
        设计系统 · <em className="text-redfont not-italic">Kitchen Sink</em>
      </h1>
      <p className="mb-8 font-mono text-[11px] text-[#57655f]">
        tokens 与基础组件总览 · 来源 v2-warhammer.html 定稿 · 字体已换自托管
        Barlow Condensed + Noto Sans SC
      </p>

      <Section title="色板 Tokens">
        <div className="grid grid-cols-4 gap-3 max-tablet:grid-cols-2">
          {COLORS.map((c) => (
            <div
              key={c.name}
              className="border border-panel-line bg-panel p-2 font-mono text-[11px]"
            >
              <div
                className="mb-1 h-10 w-full border border-black/40"
                style={{ background: `var(${c.varName})` }}
              />
              <div className="text-bone">{c.name}</div>
              <div className="text-[#57655f]">{c.hex}</div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="字体 Typography">
        <div className="flex flex-col gap-2">
          <p className="font-cond text-[24px] font-bold tracking-[3px] uppercase">
            Barlow Condensed 700 — WARHAMMER 40K RULES COPILOT
          </p>
          <p className="font-cond text-[16px] tracking-[2px]">
            Barlow Condensed 400 — 窄体标题/数值/铭牌（替代 Bahnschrift）
          </p>
          <p className="font-body text-[15px]">
            Noto Sans SC 400 — 正文中文字体：炮击战斗服的重型磁轨枪打帝国骑士
          </p>
          <p className="font-body text-[15px] font-extrabold">
            Noto Sans SC 800 — 兵牌大字：炮击战斗服小队
          </p>
          <p className="font-mono text-[12.5px] text-[#8ea39d]">
            Consolas mono — entity_resolver(&quot;炮击战斗服&quot;) → ok
          </p>
        </div>
      </Section>

      <Section title="切角 / 盾形 Clip-paths">
        <div className="flex flex-wrap items-end gap-4">
          {CLIPS.map((clip) => (
            <div key={clip} className="flex flex-col items-center gap-1">
              <div
                className={`${clip} flex h-16 w-28 items-center justify-center bg-tau-ban text-[11px] text-bone`}
              />
              <span className="font-mono text-[10px] text-[#57655f]">
                {clip}
              </span>
            </div>
          ))}
          <div className="flex flex-col items-center gap-1">
            <div className="clip-shield flex h-16 w-14 bg-tau-ban" />
            <span className="font-mono text-[10px] text-[#57655f]">
              clip-shield
            </span>
          </div>
        </div>
      </Section>

      <Section title="PlateButton 切角按钮">
        <div className="flex flex-wrap items-center gap-4">
          <PlateButton clip="slant-14" className="px-[30px] py-3 text-[15px]">
            ⚔ 在模拟器中打开此对局
          </PlateButton>
          <PlateButton clip="slant-l-12" className="px-[34px] py-3 tracking-[3px]">
            发 送
          </PlateButton>
          <PlateButton clip="slant-8" className="px-[22px] pt-2 pb-[9px]">
            页签态
          </PlateButton>
        </div>
      </Section>

      <Section title="ClipPanel 切角面板">
        <div className="grid grid-cols-2 gap-4 max-tablet:grid-cols-1">
          <ClipPanel tone="bone" clip="plate-14" className="p-4">
            <div className="mb-1 font-cond text-[11.5px] font-bold tracking-[2.5px] text-gw-red uppercase">
              指挥官 · 呈问
            </div>
            骨白纸面 · clip-plate-14（提问卡底）
          </ClipPanel>
          <ClipPanel tone="dark" clip="none" className="p-4">
            暗色机械面板 · trace/calc 底（不切角，带描边）
          </ClipPanel>
        </div>
      </Section>

      <Section title="StatBox 属性格 + KwBar 关键词条">
        <div className="mb-4 flex gap-3.5 bg-dark p-4">
          <StatBox lab="M" val={'5"'} />
          <StatBox lab="T" val="6" />
          <StatBox lab="SV" val="2+" />
          <StatBox lab="W" val="8" />
          <StatBox lab="LD" val="7+" />
          <StatBox lab="OC" val="2" />
        </div>
        <KwBar faction="阵营: 钛帝国">载具，机甲，战斗服，炮击</KwBar>
      </Section>

      <Section title="WaxSeal 封蜡章 + VerdictShield 判定盾">
        <div className="flex items-center gap-8">
          <div className="flex gap-3">
            <WaxSeal>1</WaxSeal>
            <WaxSeal>2</WaxSeal>
            <WaxSeal>3</WaxSeal>
          </div>
          <VerdictShield label="值得带" sub="Sanctioned" />
          <VerdictShield label="不建议" sub="Censured" />
        </div>
      </Section>

      <Section title="Rich 行内富文本">
        <p className="border border-panel-line bg-panel p-4 text-[13.5px] text-[#c3cdc7]">
          <Rich
            text={[
              { t: "kw", s: "[重型]" },
              { t: "text", s: "：未移动 +1 命中 → " },
              { t: "num", s: "3+" },
              { t: "text", s: " 命中（" },
              { t: "num", s: "67%" },
              { t: "text", s: "），" },
              { t: "strong", s: "值得带" },
              { t: "cite", n: 2 },
            ]}
            numClass="font-cond text-[14.5px] font-bold text-bone"
          />
        </p>
      </Section>
    </main>
  );
}
