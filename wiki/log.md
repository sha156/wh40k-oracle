# Operations Log

> 追加式操作日志。每次 Ingest/Lint/Archive/Rebuild 操作追加一行。
> 格式自动生成，勿手动编辑。

| Timestamp | Operation | Description | Affected Pages | Cascade Updates |
|-----------|-----------|-------------|----------------|-----------------|
| 2026-07-05 11:33 UTC | rebuild | 全量流水线重建 （阵营: WE） | - | - |
| 2026-07-05 16:03 UTC | rebuild | 全量流水线重建 （阵营: WE） | - | - |
| 2026-07-11 07:50 UTC | manual-edit | 11版迁移S6首批：core-rules 11 个术语页升级至11版口径（deep-strike/scouts/infiltrators/lone-operative/pistol/deadly-demise/leader/melta/sustained-hits/ignores-cover/stealth） | core-rules/*.md ×11 | build+lint |
| 2026-07-11 10:10 UTC | manual-edit | 11版迁移S6收官：core-rules 其余 53 个术语页升级至11版口径（武器技能16+核心技能计谋5+阶段结构13+判定概念14+阵营机制5；大改项：indirect-fire/heavy/lethal-hits/blast/hazardous/fly/hover/fire-overwatch/fight-phase/fall-back/strategic-reserves/benefit-of-cover/invulnerable-save/mortal-wounds/engagement-range/oath-of-moment/for-the-greater-good） | core-rules/*.md ×53 | build+lint |
| 2026-09-21 11:39 UTC | manual-edit | Correct Oath of Moment current conditions and explicit historical baselines; remove unsupported Black Templars benefit and newly-added detachment claims. | core-rules/oath-of-moment.md | build, lint: 0 errors |
| 2026-09-21 12:06 UTC | manual-edit | Clarify Oath comparison for readers: define the official points table, group independent changes, and retain version and ability-possession limits without repeated audit wording. | core-rules/oath-of-moment.md | build, lint: 0 errors |

- 2026-09-26: Refreshed 228 generated unit pages from the verified Black Library snapshot merge; official numerical fields retained. See 2026-09-26-blacklibrary-import-acceptance report.
| 2026-09-30 11:19 UTC | rebuild | Reviewed Guilliman ability fragments and scoped four Black Library identity families; rebuilt six changed cards with official English fallback for unsafe translations | factions/千子/units/lord-of-change.md, factions/帝国特勤/units/ministorum-priest.md, factions/帝国特勤/units/watch-captain-artemis.md, factions/帝国特勤/units/watch-master.md, factions/星界军/units/ministorum-priest.md, factions/星际战士/units/roboute-guilliman.md | crosslinks --units-only, build, keywords, lint: zero errors |
| 2026-09-30 19:25 UTC | Rebuild | Approved source retirement: retain 125 ordered official term pairs; retire 62 Tau pairs, 45 unmatched entries and 107 cached entities. Recoverable originals: archive/source-retirement-20260930/pre-apply. | terms.json, terms.md, review_needed.md | - |
| 2026-09-30 20:04 UTC | rebuild | Source retirement: official Core Rules keyword classification; numerical/unit/weapon fields unchanged; full native and page reconciliation pending. | indexes/keywords.md, indexes/keywords.json | - |
| 2026-09-30 21:24 UTC | rebuild | Curated retained-source rules: cleave, dark-pact, oath-of-moment | core-rules/cleave.md, core-rules/dark-pact.md, core-rules/oath-of-moment.md | - |
