# Black Library ability projection and faction identity acceptance

Last updated: 2026-09-30. Runtime: `D:/Project/py/RAG`. Branch: `codex/review-answer-provenance`. Implementation and tracked evidence commit: `a9057ec97` (`Guard Chinese rule projection by reviewed ability and faction identity`). Delivery target: local Docker. [PR #75](https://github.com/sha156/wh40k-oracle/pull/75) remains a draft. Publication and hosted CI are separate from this completed local acceptance.

Status: scoped local acceptance passed. The checked database, index and wiki projection are published locally. The final API image is deployed and healthy; 2,814 native tests, 11 live card checks, two fresh chat checks and the scoped browser check pass. Remaining source-coverage and freshness limits are recorded below; this is not complete-site or latest-rules parity.

## Result and scope

Guilliman's five grouped Chinese source entries previously failed a count-only comparison with seven official ability rows, causing the entire card to select English. The reviewed projection now preserves all seven official ability identities: five verified Chinese fragments and two unchanged official English fallbacks. It reaches the API card, agent datasheet tool and generated wiki through the same projector. The search index receives only the reviewed Chinese fragments under the Black Library citation; official English text is not relabelled as Black Library content.

Four known wrong-identity community responses also exposed an older name-only import problem: shared names were projected into the wrong factions. The cleanup restricts these four reviewed name families to exact source and canonical identities. Five unsafe Chinese rows are removed, while their canonical units and English rules remain available. The original cached source bodies remain retained as evidence.

The browser check then found another authority bypass: Guilliman's card header used 355 points but its Chinese composition paragraph still said 340. Community composition is now used only for one plain authoritative model-count tier, one source paragraph, one explicit source quantity and one explicit price, with exact quantity and price agreement. Multiple tiers, extra model quantities, conditional authoritative descriptors, missing counts/prices and changed official rules fall back to canonical composition. Matching price totals alone cannot establish which price belongs to which model count. Guilliman now displays `1 个模型 — 355 分` in this database snapshot; the [actual base comparison](2026-09-30-blacklibrary-projection-evidence/composition-base-comparison.json) preserves the before/after result.

The composition check reconciles model count and price. Any other surrounding prose in an accepted community paragraph has not undergone a complete official-rule comparison; matching that tier does not verify every narrative restriction in the paragraph.

## Reviewed Guilliman abilities

Canonical unit: `000000138`, Roboute Guilliman. Chinese capture: source record 24, captured on 2026-09-22 at 09:36:28 UTC. The English side is the existing ordered official database ability snapshot, not a claim of globally latest rules.

| Official ability identity | Displayed source | Result |
| --- | --- | --- |
| Author of the Codex | Black Library | 圣典权威; only its reviewed introductory paragraph |
| Ultramarines Bodyguard | Black Library | 极限战士卫队 |
| Armour of Fate | Black Library | 命运战甲 |
| Primarch of the XIII (Aura) | Black Library | 十三军团原体【光环】, split from the grouped source entry |
| Master of Battle | Black Library | 战争之主, split from the grouped source entry |
| SUPREME COMMANDER | Official English database | No verified Chinese counterpart |
| Supreme Strategist | Official English database | Preserve the official battle-round frequency |

The faction-ability name-only entry and the extra Chinese movement claim are not promoted into official unit ability rows. The ambiguous Chinese Supreme Strategist fragment is excluded from the active reviewed projection without rewriting the source cache.

The policy is in `db_compile/ability_localization.json`. Its Chinese fingerprint hashes every original field, and its English fingerprint hashes the ordered `name_en`/text pairs. Both use UTF-8 canonical JSON with sorted object keys and retained list order:

- Chinese SHA-256: `9f092b1c50003aa65a2177d261fa59af9d82147f5ceea590dceb2c1f31a805d1`.
- English SHA-256: `577c94389bee249bdab77e606a9f6a952888e20402867797b7110b8933df279e`.

Any source-body or official-ability change, addition, removal or reordering invalidates the reviewed mapping and returns the complete current English list. Existing whole-unit official-rule freshness guards still take precedence. Other units retain their existing completeness policy; this is one reviewed ability-level pilot.

The actual base comparison reproduced five source entries and an English first ability name before the change, versus seven projected entries and 圣典权威 after it. The rejected Chinese frequency was present in the base Black Library search chunk and absent from the candidate chunk. Saved evidence: [base comparison](2026-09-30-blacklibrary-projection-evidence/base-comparison.json).

## Wrong-identity records and canonical fallbacks

The four targeted public detail requests still returned different source IDs/factions on September 30. The importer now scopes these reviewed families using source ID, normalized English name, source faction, canonical ID and canonical faction. Known suspect records require a new capture that passes the endpoint identity checks; unverified retained bodies cannot become active Chinese details.

| Requested source identity | Wrong returned identity | Chinese detail retained for the valid identity | Canonical English fallback |
| --- | --- | --- | --- |
| 992, Imperial Agents Ministorum Priest | 577, Adepta Sororitas | `000001553`, Adepta Sororitas Priest | `000003812`, Imperial Agents Priest; `000001394`, Astra Militarum Priest |
| 1001, Imperial Agents Watch Captain Artemis | 122, Deathwatch | `000003872`, Space Marines/Deathwatch Artemis | `000003814`, Imperial Agents Artemis |
| 1002, Imperial Agents Watch Master | 121, Deathwatch | `000003871`, Space Marines/Deathwatch Watch Master | `000003815`, Imperial Agents Watch Master |
| 1094, Scintillating Legions Lord of Change | 238, Chaos Daemons | `000001120`, Chaos Daemons Lord of Change | `000004124`, Thousand Sons Lord of Change |

The Astra Militarum Priest row was also contaminated by the name-only fan-out; it is not a fifth newly failed detail request. This explains why four source mismatches require five Chinese-row removals. The valid Sisters Priest and Chaos Daemons Lord of Change rows also regain their correct source-faction metadata.

The legacy detail fetcher now validates HTTP success, API success, expected ID, game ID, faction and normalized English name before parsing/caching a body. Failed, empty or absent responses preserve previous cache records with explicit retained provenance. Atomic replacement and the repeated-failure circuit breaker preserve the last usable cache. These changes do not manufacture the four missing source details.

## Data reconciliation

The staged projection was checked before publication. The [projection report](2026-09-30-blacklibrary-projection-evidence/projection-report.json) records 1,085 retained cache records, 950 English-name matches, seven Chinese-name bridge matches, 133 unmatched records, two records without details and four identity rejections.

| Asset or invariant | Before | After | Interpretation |
| --- | ---: | ---: | --- |
| Chinese detail rows | 1,150 | 1,145 | Five unsafe cross-faction rows removed |
| Canonical units | 1,721 | 1,721 | Canonical units retained |
| Aliases | 1,685 | 1,685 | Existing aliases retained |
| Active Chinese weapon names | 4,971 / 4,971 | 4,971 / 4,971 | Localization coverage retained |
| All Chinese weapon names | 8,356 / 9,337 | 8,356 / 9,337 | Overall coverage retained |
| Search chunks | 5,910 | 5,905 | Five contaminated Black Library chunks removed |
| Black Library chunks | 1,133 | 1,128 | Three changed texts embedded; 1,125 unchanged texts reused |
| Other search documents and vectors | 4,777 | 4,777 | Preserved exactly |

All 18 database tables were compared: only `unit_zh_detail` changed. Official numerical fields, English ability bodies, canonical membership, official points tables, aliases and weapon rows are unchanged. The source caches `details.json`, `units.json`, `aliases_history.json` and `weapon_names_history.json` are unchanged. The retired Votann PDF remains excluded. The [independent final preservation check](2026-09-30-blacklibrary-projection-evidence/final-preservation.json) confirms these invariants; the published database SHA-256 is `af4c651da438d1d0c48c22462f1bfde0c236a2e859b81ccc7b2b61c1bdc73069`.

The five removed rows contained 17 Chinese ability entries and four keyword spans, as recorded in the [ability reconciliation](2026-09-30-blacklibrary-projection-evidence/ability-reconciliation.json). The real-corpus coverage baseline therefore changes from 3,349 entries / 184 spans to 3,332 entries / 180 spans; the English baseline remains 4,041 entries / 445 spans. This is a reconciled removal of unsafe source claims, not a weakened coverage expectation.

Normal wiki commands regenerated the five fallback unit pages and Guilliman's page, followed by unit crosslinks, indexes and keyword pages. The tracked content change is six unit pages plus their generation hashes. Wiki lint reported zero errors, one existing aggregated alias warning and 691 information entries.

## Verification status

- The first native suite passed 2,794 tests, with 19 warnings, in 266.03 seconds. It predates the final composition guard and is retained as intermediate evidence in `full-native.log`.
- The price-multiset composition draft was rejected in independent review because it could accept swapped prices for different model counts. A later 2,812-pass full run also predates the last additional-quantity guard and is preserved in `full-native-pre-final-quantity.log`; it is intermediate evidence, not final acceptance.
- The corrected composition guard passed 20 focused tests. The final native suite passed **2,814 tests**, with 19 warnings, in 264.66 seconds. The [validation summary](2026-09-30-blacklibrary-projection-evidence/validation.json) preserves final counts; the full local log is `db_sources/blacklibrary/staged-20260930/full-native-accepted.log`.
- Independent code and Python reviews approved the shared projection, identity/fetcher changes and final corrected composition guard. Both reviewers independently passed 50 focused tests, including the compound-quantity case.
- Final deployed API image: `sha256:f1224f123ec38f06e17f52f735978032fe95658cfb4b3c9e0f2dd73544d34ddb`. Health reports ready and retrieval true; warmup is done with no error. All eight changed runtime code/config files match their host SHA-256 hashes. Evidence: [deployment verification](2026-09-30-blacklibrary-projection-evidence/deployed-verification.json).
- Eleven final live card checks passed: Guilliman shows a 355-point header and the canonical one-model 355-point composition, with five Chinese abilities and two official English abilities. Five scoped fallback cards use their canonical English abilities; four valid base-faction cards retain Chinese. Counts are in the [validation summary](2026-09-30-blacklibrary-projection-evidence/validation.json); full local responses are in `db_sources/blacklibrary/staged-20260930/final-live-cards.json`.
- Fresh Guilliman chat completed in 38.971 seconds with one successful structured lookup, two citations and no degraded fallback. It correctly answers once per battle round and explains that the two players' turns share that frequency limit. Evidence: [Guilliman chat](2026-09-30-blacklibrary-projection-evidence/chat-guilliman-final.json). This is a scoped live observation, not a rerun of the 115-question benchmark.
- Fresh Imperial Agents Priest chat completed in 63.169 seconds with three citations and no degraded fallback. Its first lookup returned the Sisters namesake with an explicit faction warning; it then rechecked `Ministorum Priest (AoI)` and answered Holy Hatred as melee Sustained Hits 1, with the Agents faction and 40-point tier. It explicitly distinguished the Sisters +1-to-wound ability. Evidence: [Priest chat](2026-09-30-blacklibrary-projection-evidence/chat-priest-final.json).
- The final visible browser check confirms five Chinese abilities, two labelled official English abilities and the one-model 355-point composition. Saved screenshots: [card header](2026-09-30-blacklibrary-projection-evidence/guilliman-card-header.jpg) and [abilities and composition](2026-09-30-blacklibrary-projection-evidence/guilliman-abilities-composition.jpg). These images show the local project's browser output; the separately labelled cached Chinese source evidence remains in the September 26 comparison directory. This is a scoped browser check, not a full E2E run.
- The initial Docker candidate exposed the stale 340-point composition in the browser. Its `live-cards.json` remains intermediate evidence, superseded by the final card/browser evidence.
- Frontend source is unchanged. The earlier 22 frontend tests and 12 Chrome journeys are historical release evidence, not a new full frontend/E2E run for this change.

## Rule history and freshness limits

The official June 4, 2025 update explicitly changed Guilliman's Supreme Strategist frequency from each player turn to each battle round. In the 11th-edition core rules, a battle round includes one turn for each player. The amendment therefore reduces potential activations across both players' turns from two to one per battle round, subject to the ability's other conditions. The translator's intended meaning of 每个回合一次 remains unconfirmed. See the [source comparison and evidence images](2026-09-26-guilliman-source-comparison/README.md) and the [official June 2025 announcement](https://www.warhammer-community.com/en-gb/articles/bk58priy/the-warhammer-40000-balance-dataslate-june-2025/).

The saved English Faction Pack is v1.2, legal for matched play from August 26, 2026; page 63 preserves the battle-round frequency. The database's existing ability wording is not claimed to be byte-identical to every word of that PDF. On September 14, 2026, GW previewed a forthcoming Space Marines Codex with further Guilliman changes. The [preview](https://www.warhammer-community.com/en-gb/articles/paxsnmde/first-look-space-marines-datasheets/) is incomplete, has not been imported, and does not establish verification of a released full Codex in this task.

The earlier 98 raw unresolved listings now mean 94 user-reviewed empty exclusions and four actionable wrong-identity responses. The exclusions comprise 49 empty duplicates, 36 empty Legends listings and nine other empty listings. They remain guarded by the exact whole-inventory fingerprint and reopen when that source inventory changes. This cleanup does not resolve the four upstream responses or claim full-site, AoS, Kill Team or globally latest-rule parity.

The retained 40K snapshot contains 1,171 inventory records and 1,071 full detail captures across 38 faction/subfaction names. The canonical merged cache contains those verified captures plus 14 retained older records. September 30 changes their safe projection and fetch validation; they do not add new successful details for the four mismatched requests or turn the snapshot into a complete copy of the source service.

Official prices remain the September 14 snapshot. Remaining official Ork rule gaps, retirement scope for other fan-translated PDFs, cloud deployment and host reboot durability remain as previously documented. No additional PDF retirement is implied by this change.

## Recovery and reproducibility

Pre-change database, full index and wiki are preserved under `archive/blacklibrary-projection-20260930/`. `before.json` records the source/index hashes and all 18 database-table digests. The checked staged database, index and comparison reports are in `db_sources/blacklibrary/staged-20260930/`. These runtime assets are ignored by Git and remain necessary local assets.

The normal offline database restoration consumes the guarded Chinese detail policy; keep the canonical source caches and history caches in place. Generate pages through `python -m wiki_engine.from_db`, then `python -m wiki_engine crosslinks --units-only`, `python -m wiki_engine build`, `python -m wiki_engine keywords` and `python -m wiki_engine lint`, using the full project virtual-environment executable. Refresh retrieval through `python -m scripts.refresh_blacklibrary_index` with a new output directory and the existing complete local BGE-M3 snapshot. After any future asset rebuild, compare authority tables and retained non-Black-Library vectors before publishing staged assets, then rebuild/restart the API and repeat the scoped runtime checks documented above.
