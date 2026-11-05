# Actual source coverage declaration preparation

## Iteration 1: exact source-only inventory and two private declarations

Two actual, source-bound price-only declarations are prepared for independent semantic review: `KAIUS KONORIUS` and ordinary `MARNEUS CALGAR`, both from the `space-marines` MFM page. Their exact saved primary-source prices are 100 and 180 respectively. Neither declaration certifies a rules body, faction keywords, composition, equipment, eligibility or an effective/legal date. Nothing was promoted into the active database.

This is an incremental publication-prerequisite result. The complete canonical SM/chapter inventory, authenticated unavailable-newer declarations, actual retained-body/history preservation and final host review remain outstanding. Prior registry implementation tests remain structural/synthetic evidence; they are not actual source declarations. This report does not certify the whole project, all current bodies, tournament legality or deployment.

The worktree began clean on `codex/release-coverage-declarations` at `21e0b60075c85206742a4a437a9b36682938030f`. Only this new report is a tracked change. Private scripts, inventories, bindings and trial databases are under the authorized ignored directory:

`D:/Project/py/RAG/db_sources/real-coverage-declarations-owned/20261004/`

GNHF owns the scoped report commit. No manual commit, stage, push, merge, network request, provider/model call, install, Docker operation or service change was performed. Orchestrator notes and other owners' reports/code were not edited. The manifest date records this preparation review; it does not imply independent host approval.

## Actual inputs and provenance boundary

The read-only production database is `D:/Project/py/RAG/db/wh40k.sqlite`, 16,273,408 bytes, SHA-256 `afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`. It has 19 tables and no `source_coverage_registry` or `source_coverage_history` table. Every original table's exact schema, row count and content digest is recorded in `source-only-trial-results.json`.

The MFM receipt is `db_sources/mfm/snapshots/fetch-jtgkljt3/manifest.json`, SHA-256 `0360b2af61a41efeb5a5be3936b55dc2f1b35b9e13aedb0aaf2b1143a640a629`. Its saved capture is **2026-10-03T19:00:56.192123+00:00** (October 4 local). All 30 saved page hashes were checked, every page was parsed using the lossless source-ledger parser, and the complete resulting **3,635 rows exactly equal** the AFB `official_mfm_points` table, including kind, section, name, tier, model/option text, cost, source URL, raw hash and capture timestamp. The September 30 3,627-row preparation is not used as current price provenance.

For both selected declarations:

- Exact source URL: `https://mfm.warhammer-community.com/en/space-marines`.
- Actual saved HTML: `D:/Project/py/RAG/db_sources/mfm/snapshots/fetch-jtgkljt3/space-marines.html`.
- Raw SHA-256: `b18e876a8e2e796aa00869aa074262dfa29e5a2aee69685a011964383ea89fbe`.
- Capture: the exact timestamp above. `source_date` and points/body `effective_date` are null; no source publication date, printed date or legal-start date was inferred from URL, filename, capture, version or price.

Authentication here means exact binding to the existing saved primary-source receipt and its actual bytes. No new retrieval or signature verification was performed. Registry validation alone does not establish the source's truth; separate raw literal bindings establish the limited claims made here.

The supplied 29-PDF freshness receipt was also hash-checked at `db_sources/release-check-20260930/host/source-freshness-20261004/raw-verification-20261004T143516/final-verification.json`, SHA-256 `aee72aa39ad92165620e29bdbdbf8e8e5d024e8f5acbf8bc7213cedeeb5aef64`. Its 29 original staged PDFs remained exact against that receipt. This is preservation evidence only: this iteration performed no new PDF semantic/body certification.

## Complete exact-name source-head inventory

`all-unit-heads.json` contains **1,346** `(source faction slug, complete source unit name)` heads, with every kind=`unit` ledger row and its zero-based page ordinal retained. It does not collapse occurrence tiers, conditional prices, options, chapter reprints or ally sections into a base cost. Enhancement rows remain in the complete 3,635-row ledger and are not proposed as unit declarations.

Exactly **1,323** heads have at least one same-faction exact case-insensitive canonical-name match; **23** do not. Those 23 are **13** distinct `(canonical faction ID, complete source name)` keys after preserving chapter occurrences. Matching in this inventory is exact name/faction accounting, **not** full chapter identity validation or source-book binding. Exact-name matches may still have chapter overlap/availability conflicts; the next canonical inventory must check their complete ordered faction-keyword arrays.

The six SM source slugs below are `space-marines`, `black-templars`, `blood-angels`, `dark-angels`, `deathwatch` and `space-wolves`; all map to faction ID `SM`. Rows retain their exact source slug, source hash and ledger locators in `classified-missing-heads.json`.

| Complete source name | Source slug occurrences | Count | Decision |
| --- | --- | ---: | --- |
| VYPER | aeldari | 1 | Normalized candidate `Vypers`; deferred, not a new source-only identity |
| INVADER ATVS | All six SM slugs | 6 | Normalized candidate `Invader ATV`; chapter reprints/options retained separately, deferred |
| MYPHITIC BLIGHT-HAULERS | death-guard | 1 | Normalized candidate `Myphitic Blight-hauler`; deferred |
| RUKKATRUKK SQUIGBUGGIES | orks | 1 | Normalized candidate `Rukkatrukk Squigbuggy`; deferred |
| ERADICATOR SQUAD WITH MELTA RIFLES | All six SM slugs | 6 | Exact equipment variant without exact canonical name; generic/chapter occurrences deferred |
| CHAOS REAVER TITAN | chaos-titan-legions | 1 | Existing shared-datasheet mapping candidate; primary body relation not certified here |
| CHAOS WARBRINGER NEMESIS TITAN | chaos-titan-legions | 1 | Same boundary |
| CHAOS WARHOUND TITAN | chaos-titan-legions | 1 | Same boundary |
| CHAOS WARLORD TITAN | chaos-titan-legions | 1 | Same boundary |
| GUNWAGON | orks | 1 | Exact source-only candidate deferred to another bounded review; option/occurrence rows retained |
| RUNTHERD | orks | 1 | Exact source-only candidate deferred; no composition or eligibility inference |
| KAIUS KONORIUS | space-marines | 1 | Selected actual price-only declaration |
| MARNEUS CALGAR | space-marines | 1 | Selected actual price-only declaration, distinct from Armour and archived ordinary Calgar |
| **Total** | | **23** | **9 normalized candidates + 6 equipment/reprint occurrences + 4 shared Titan candidates + 2 deferred names + 2 selected names** |

Fuzzy suggestions are explicitly labeled `suggestions_not_identity` in the inventory. They are not bindings or canonical IDs. Shared Titan mappings are classified using existing code, without turning that code into primary-source body proof. Source-head sections and all individual rows remain available for separate ally/reprint/conditional review. No extra ally-only missing head was assigned an invented canonical identity.

The full exact chapter-keyword inventory and source-book availability row decisions are **pending**, including unknown/overlap conflicts. No book was inferred from `source_id` adjacency, and `datasheets.legend` was not treated as a Legends flag.

The independent SQL binding verifier identified **five additional registry spelling conflicts** among the 1,323 casefold-matched heads. SQLite's default `lower()` does not lowercase these accented capitals, while Python `casefold()` does. Thus the exact current registry SQL name predicate misses 28 heads: the 23 accounted above plus these five existing canonical identities. `registry-sql-name-conflicts.json` preserves their complete source rows and exact ordered canonical faction keywords. They remain deferred identity-guard conflicts, never proposed as new source-only bodies:

| Complete source name | Exact canonical ID/name | Source slug |
| --- | --- | --- |
| BEREHK STORNBRÖW | 000004201 / Berehk Stornbröw | leagues-of-votann |
| BRÔKHYR IRON-MASTER | 000002597 / Brôkhyr Iron-master | leagues-of-votann |
| BRÔKHYR THUNDERKYN | 000002603 / Brôkhyr Thunderkyn | leagues-of-votann |
| KÂHL | 000002594 / Kâhl | leagues-of-votann |
| KHÂRN THE BETRAYER | 000002622 / Khârn The Betrayer | world-eaters |

This is an actual binding finding, not authorization to change the registry/consumer code here. A later owner must review how to preserve exact source and canonical spellings across that predicate. The selected ASCII names pass the actual predicate unchanged. No body category is certified by the canonical matches above.

## Proposed actual declarations and literal bindings

Both records use the reviewed schema version 1 with exactly `identity`, `reviewed_on`, `body` and `points`. Identity is `(unit_id=null, full source name, faction_id=SM, faction_slug=space-marines, faction_keywords=[])`. The empty keyword array makes no body/keyword claim for an absent canonical identity; neither source section text nor a chapter name was converted into invented keywords.

`body.status=source_only_price`, empty scope, null effective date and null retained snapshot accompany `points.status=current_published`, null effective date and the exact raw web receipt. Body and points cite the same price evidence. No canonical ID, model, weapon, ability, loadout, composition or eligibility was created. Current publication is supported by the exact complete current ledger; no nonexistent canonical `mfm.current` flag was fabricated. Canonical declarations will separately require the registry's explicit current/non-current projection guards.

| Full source identity | Exact source ledger locator | Literal price | Original raw header byte range | Original raw price-span byte range |
| --- | --- | --- | --- | --- |
| KAIUS KONORIUS | space-marines ordinal 214; kind unit; ULTRAMARINES; YOUR UNIT COSTS; 1 model | `100 pts` | `[140665, 140750)` | `[161407, 161466)` |
| MARNEUS CALGAR | space-marines ordinal 215; same kind/section/tier/model text | `▲ (+25) 180 pts` | `[140903, 140955)` | `[161532, 161601)` |

Locators use UTF-8 byte offsets with exclusive ends, not character indexes. `source-only-bindings.json` preserves the complete literal HTML, literal hashes, exact row data/ordinals, raw/manifest hashes, parser/resolver hashes and resolved owning-card byte ranges/hashes. Source HTML streams the header and price in separate hidden RSC segments. The binding verifies both original raw literals and their association in the existing deterministic resolved card; it does not claim that the reconstructed complete card existed contiguously in the raw receipt.

The `1 model` phrase is retained as a **price-tier literal**, not certified unit composition. Ordinary Calgar's current 180 source head is not the archived ordinary 200 identity and does not change the Armour of Antilochus identity. Canonical historical 155/80 declarations await the independently reviewed rebuild-owner 61b restored copy and exact provenance/marker review. The current AFB mirror is not permission to assert those historical flags or restore an old DB wholesale.

## Actual private transaction verification

The two private databases began as byte-exact copies of the AFB file. Existing registry APIs and consumer semantics were used unchanged. Every apply used an explicit caller transaction and an aligned `expected_records` list; initial positive apply used `[None, None]`.

| Trial | Actual result |
| --- | --- |
| Strict manifest validation and first positive apply | Two records applied; exact source-only resolutions equal the proposed records |
| Original table preservation | All 19 schemas/counts/content digests unchanged, including body, prices, official authorities, aliases and archive records |
| New registry/history | Two registry records and their exact content-addressed JSON history preserved |
| Exact full replay | File SHA-256 byte-identical to the first positive result |
| One-record subset replay | Other actual record and all history JSON bytes/digests unchanged; complete DB byte-identical |
| Late wrong identity in the second declaration | `ValueError: Exact published price provenance mismatch`; caller transaction remains active; registry/history and DB bytes unchanged after rollback |
| Controlled in-apply cancellation after history insertion | `KeyboardInterrupt: controlled private-trial cancellation after history insertion`; savepoint restores all 19 original tables and removes newly created registry/history; caller transaction remains active |
| Caller rollback after successful apply | Fresh-copy DB byte-identical to original AFB |
| Body-dependent consumer support | `body_support(required_fields={models,weapons,abilities})` returns unsupported for both actual price-only records |

Positive private DB SHA-256: `0bf61136525aed4ee219775a31c79b319979c0288e943a58c5c514cb5273ddbe`. The positive subset/replay verifies preservation of an unmentioned real registry declaration, not a retained full-body snapshot. This iteration does **not** claim an actual historical transition or authenticated retained-full-body preservation trial. Such a claim requires actual reviewed body/history evidence and remains a later gate.

No redundant synthetic registry suite, model audit or environment install was run. The supplied full Python 3.11 executable was used:

`D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`

Reproduction, from the owned evidence directory, with bytecode disabled:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
$coveragePython = 'D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe'
& $coveragePython 'D:/Project/py/RAG/db_sources/real-coverage-declarations-owned/20261004/inventory_sources.py'
& $coveragePython 'D:/Project/py/RAG/db_sources/real-coverage-declarations-owned/20261004/prepare_source_only.py'
& $coveragePython 'D:/Project/py/RAG/db_sources/real-coverage-declarations-owned/20261004/verify_evidence.py'
```

Scripts write only private outputs; copies are bounded to two 16 MB SQLite files. The preparation script rejects protected-input drift against its retained baseline before rerunning. No model, Git tree, virtual environment, 17k-asset tree or release archive was copied.

Two failed raw-locator assertions occurred before the final successful binding: Kaius uses a div header rather than a span, and RSC stores the price span separately from its reconstructed li. The assertions were corrected to bind the actual tag and actual raw price span plus resolved card. There was no parser/production change, fabricated source literal or exception bypass. The final bound locators and successful trials supersede those intermediate script assertions.

The separate verifier initially exposed the five Unicode/SQLite differences above; the inventory now explicitly accounts for both casefold matches and the actual SQL predicate. Printing those accented names also reproduced the host's GBK stdout limitation. Reproduction uses UTF-8 stdout; the JSON evidence was already written as UTF-8, and no source bytes or name spellings were changed.

## Preservation and evidence anchors

The identical `protected-inputs-before.json` / `protected-inputs-after.json` inventories cover **82 files / 413,900,574 bytes**: AFB DB, all 30 MFM raw receipts and their manifest, existing Black Library JSON inputs, retrieval index/metadata files, corpus manifest/policy, the saved chapter ledger/summary/evidence manifest, two saved public catalogues, the 29-PDF freshness receipt and its 29 original PDFs, and the five reviewed registry/consumer/build/schema/update modules. Every listed input remains byte-exact. This is a bounded preservation check, not a new full active-asset or immutable-8,305-copy audit. Other owners' original archives and services were not touched.

| Owned evidence | SHA-256 |
| --- | --- |
| source-only-manifest.json | `dd70041f64f693f756e1a4487c95caebb7d6aa7cbed51f0402297b8af2793dd4` |
| source-only-bindings.json | `cb62accf0bd038dae27ea2923e173f244d1cbc385c8081ae5d06ee1a38c64a87` |
| source-only-trial-results.json | `c37648ea0cace2c60ece54fd71ad2e632744af03cb1d61b161c92e256615d5dc` |

`inventory-summary.json`, `all-unit-heads.json`, `missing-canonical-heads.json`, `classified-missing-heads.json`, `registry-sql-name-conflicts.json` and `source-only-summary.json` retain exact accounting and explicit deferred decisions. The ignored JSON manifest and bindings must accompany later review/publication; this tracked report is not itself an automatically loaded registry.

`verify_evidence.py` independently checks the raw header/price bytes and owning-card hashes, current SQL row/provenance bindings, complete 1,346-head inventory, the 23 missing exact-casefold heads plus five SQL conflicts, all protected hashes, manifest/report evidence digests, script AST syntax and `PRAGMA integrity_check` on both private databases. Its completed result and artifact hash inventory are saved in `final-binding-verification.json`. Final scoped diff/whitespace checks pass. No application code/build was changed; full runtime/native tests are not newly claimed by this iteration.

## Read-only persistence finding and bounded restoration plan

The reviewed source shows a real persistence gap: `build_database` builds a fresh SQLite file from `schema.ALL_DDL` and CSV imports, preserves `source_archived_units`, then atomically replaces the destination. Neither coverage table is in `ALL_DDL`, the archive-preservation helper nor the authority restoration pipeline. `restore_authority_layers` runs the declared writing stages, including source reconciliation, MFM and other authorities, but does not load reviewed coverage declarations/history. A successful fresh build therefore has no guarantee of retaining coverage metadata. The comments describing old unlink behavior are not the current build implementation; current replacement is atomic, while the subsequent multi-stage authority restoration is not one global transaction.

Proposed implementation-owner plan, **not implemented here**:

1. Freeze a reviewed recovery bundle with the exact accepted manifest, raw receipt bindings, protected source digests, full ordered canonical identities, accepted registry JSON bytes, and every history JSON byte/digest. Include the exact base/rebuilt DB fingerprints and authority-ledger expectations. A price-only subset must never reconstruct body verification from current table existence.
2. Before replacement, read registry/history using a read-only connection and validate every record/key/digest. Fail on corrupt or missing expected history. Keep the original DB and bundle recoverable; never restore the old semantic-prior DB wholesale.
3. Build into a private candidate, restore reviewed source corrections and the correct MFM/authority layers, then verify exact identities and source chronology. Coverage restoration occurs **after those authority writes**, before acceptance/consumer exposure. A later changed ledger cannot silently keep a current-price declaration whose exact source hash/capture no longer matches.
4. For the two source-only records here, verify the full `kind=unit` ledger name/slug/faction and raw binding, no exact canonical body, and exact provenance. Apply the reviewed manifest in an explicit transaction with exact expected prior records. If a new exact canonical body now exists, reject and request a separately reviewed canonical declaration; do not attach by fuzzy match.
5. For future canonical records, guard complete ordered faction keywords, identity, required current/non-current projection and actual source/category bindings. A whole `BODY_FIELDS` category means the entire consumer category: one T or weapon S amendment cannot certify all models, weapons or abilities. Changed body/identity requires semantic re-review. Source dates/captures must not become effective dates.
6. Preserve the original accepted history bytes/digests through a separately reviewed bounded history-restoration operation; `apply_coverage` alone only knows its supplied declarations and existing history. Do not replace a multi-record accepted history with one current snapshot. Verify the reviewed history **before** any body-equality shortcut; retained source footprints and dates must not downgrade or recertify unavailable newer bodies.
7. Copied-fixture acceptance must cover the actual reviewed subset: fresh missing tables, exact restore, byte-exact replay, unmentioned record/history preservation, late identity/source/capture/current-marker mismatch, corrupt/missing history and cancellation. Compare every unrelated table/row, retained archive/source and original input hash. Publish the candidate only after all authorities and these checks pass; retain the original DB on failure.

The separate SourceReconcileSentinel checkpoint-preservation implementation is still a dependency; it is neither changed nor declared complete here.

## Remaining finite gates and knowledge handoff

Next bounded work is the complete actual canonical SM/chapter inventory, including exact complete ordered faction keywords and unknown/overlap conflicts, then primary catalogue/announcement/preview bindings for the six unavailable newer full Codex bodies. Use `newer_full_unavailable` with no retained snapshot unless an entire historical body has independently verified literal/category evidence and a proven effective date. The three Legends revisions and individual overlay cell amendments must remain limited to their real evidence; model existence, mirror profiles, Black Library text, source code and price consistency cannot certify full bodies or whole consumer categories.

Dependencies remain explicit: independently reviewed rebuild-owner 61b historical copies/markers; primary body/category/history semantic review; 13 finished overlay ledgers integrated by the final publication owner; source chronology, setup/stage/runtime and SourceReconcileSentinel preservation; normal wiki/curated six-pin generation and retrieval rules. This iteration does not wait for those owners or label their preparations complete.

Verified handoff lessons are recorded here: raw streaming HTML requires both original literal locators and a deterministic owning-card association; exact-name absence must be classified before proposing source-only identities; Unicode casefold agreement can still fail the registry's SQLite name predicate; and fresh build/archive preservation does not currently preserve coverage registry/history. The initial iteration left external notes to the publication owner under the task's restricted ownership. The subsequent explicit stop-hook authorized the duplicate-checked local handoff below; application/source ownership and publication limits remain intact.

The hook appended this finite result and remaining gates to `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`, extended the existing learning decision at `C:/Users/Administrator/learn-notes/decisions/20261001-separate-transactional-source-coverage.md` and its README index, added the resolved locator record `C:/Users/Administrator/error-notes/rag/20261004-error-16-raw-mfm-locator-dom-assumption.md` and index, and extended the existing `common/20260921-error-41-python-stdout-gbk.md` recurrence. The unresolved SQLite mismatch is not recorded as a resolved error. All seven original/new note outcomes, prior-body recovery bytes and unchanged three Git indexes are bound in `knowledge-handoff/verification.json` under the owned evidence root. A later shared error-README append changed its whole-file hash; `knowledge-handoff/final-verification.json` confirms the six original bodies and our appended sections remain exact prefixes, preserving that concurrent addition and all three indexes. No commit explanation was invented, no manual staging/commit/push occurred, and no new harness rule/skill promotion was warranted; root publishes intended notes after writers finish.

The overall stop condition is **not met**. Only the two source-only declarations are concretely bound and privately trial-verified; the canonical/retained-body/history gates and host-reviewed clean report commit remain outstanding. No background process was started.

## Canonical availability continuation: complete finite inventory and bounded declarations

This continuation starts from clean `codex/release-coverage-declarations` at `d030b4b15b9b3af268067e045276c681e5222066`. It completes the finite actual SM inventory and prepares **140 canonical unavailable-newer declarations**, with **159 explicitly deferred canonical rows**. All **299** `units.faction_id='SM'` rows are included exactly once, with their canonical ID, exact English name, faction, complete ordered faction-keyword array, original keyword/points JSON, all exact six-slug source-head occurrences and decision reasons. No canonical identity, unit membership, rules category or price was changed.

The prior two source-only records, inventories, bindings, scripts and trial databases stay frozen. Their trials were not rerun. The positive/cancellation seeds for this continuation are copies of the prior validated `source-only-positive.sqlite`, SHA-256 `0bf61136525aed4ee219775a31c79b319979c0288e943a58c5c514cb5273ddbe`: its original 19 AFB tables plus the two existing declarations/history. Both old registry JSON rows and both content-addressed history rows remain byte-exact in the new trials. No real active registry was promoted.

Only this report is appended as a tracked change. New ignored evidence is confined to:

`D:/Project/py/RAG/db_sources/real-coverage-declarations-owned/20261004/canonical-availability/`

The earlier report text is preserved byte-for-byte as `report-prefix-original.md` and verified as the exact prefix after this append. GNHF owns the eventual scoped report commit; no manual stage/commit/push/merge occurs here. Orchestrator notes, other owners' files/indexes and active assets/services are untouched.

### Canonical and source-occurrence accounting

Book routing here uses the complete exact canonical faction-keyword array, not `source_id`, source-row adjacency, flavour prose or price membership. A generic-only Astartes array is a `space-marines` candidate; one exact requested chapter keyword selects that chapter route only when no additional faction/chapter keyword conflicts. This is routing of the requested availability limitation, not a literal inventory of every unit in a newer Codex or a current inclusion/eligibility assertion. Other-chapter and mixed-faction routes remain unproven.

| Requested source/book route | Canonical candidates | Prepared declarations | Deferred candidates | Exact source unit heads |
| --- | ---: | ---: | ---: | ---: |
| space-marines | 157 | 67 | 90 | 87 |
| black-templars | 19 | 12 | 7 | 75 |
| blood-angels | 26 | 14 | 12 | 83 |
| dark-angels | 19 | 16 | 3 | 85 |
| deathwatch | 10 | 10 | 0 | 76 |
| space-wolves | 41 | 21 | 20 | 88 |
| Other-chapter/mixed route unproven | 27 | 0 | 27 | Not assigned a book |
| **Total** | **299** | **140** | **159** | **494** |

The prior chapter ledger's **116** five-chapter keyword candidates reconcile exactly: 115 now have a non-conflicting chapter route, while one Deathwatch/Adeptus Astartes/Agents of the Imperium row is explicitly mixed. The other 26 unproven rows contain other chapter keywords. All keyword orders and casing are retained, including reversed chapter/Astartes arrays and the uppercase generic Astartes array. No strict identity or fuzzy normalization was widened. Generic/chapter duplicate names remain separate canonical IDs distinguished by their full keyword identity and exact source route; no identical-name row is merged or attached by adjacency.

The 494 source heads preserve every tier/option/occurrence row and zero-based source-page ordinal, including chapter reprints. `six-slug-head-occurrences.json` is checked against fresh offline parsing of just those six unchanged saved pages. The five previously recorded Unicode/SQLite conflicts are outside this finite SM inventory and remain separate, frozen and unresolved.

All **31** exact primary Legends identities from the prior chapter ledger are represented and deferred rather than relabeled as unsupported newer non-Legends Codex bodies. Their actual front/reverse PDF citations remain attached to their canonical inventory rows. This continuation does not recertify their models, weapons, abilities, equipment, composition, keywords or historical full bodies; `datasheets.legend` is never used as a Legends flag.

### Six authenticated availability decisions and their limits

`book-availability.json` records one decision for each requested route: **newer full body unavailable in the inspected saved primary inputs**, empty scope, null retained snapshot and no newer-full effective date. The declarations cite two separately bound saved primary representations:

- The October 4 English download catalogue receipt, `db_sources/release-check-20260930/host/source-freshness-20261004/download-catalogue.json`, exact source URL `https://www.warhammer-community.com/en-gb/downloads/warhammer-40000/`, captured **2026-10-04T04:47:32.996149+00:00**. The complete `/documents` list contains **37** entries and no complete Codex entry. Every route's matching title/document JSON pointer and literal byte locator is preserved. This is the saved renderer catalogue representation; it is not represented as raw HTML bytes. Catalogue absence establishes this bounded input limitation, not universal public/app unavailability, unit deletion or lack of legal rules elsewhere.
- The actual saved primary announcement at `https://www.warhammer-community.com/en-gb/articles/rylbvfnv/warhammer-40000-balance-update-emboldened-astartes/`, raw HTML SHA-256 `9599fba6a752dd7785d25f9a4cfb0503e390b7f5212af15b223ba0ff0b361946`, captured **2026-09-30T13:51:05.500712+00:00**. The literal paragraph starts `With the impending release of <em>Codex: Space Marines</em>, Astartes of every ilk` and describes limited characteristic/weapon-option changes. Its original UTF-8 byte ranges and the printed `30 Sep 26` locator are retained. That publication date does not become a legal/effective date. This announcement supports the general Astartes limitation; it does not prove six separate chapter release dates or complete chapter contents.

The five retained chapter supplement covers are hash-checked directly against the old ledger and their actual PDF page-1 text. They explicitly supplement a Codex; their real printed matched-play dates are recorded only for those older supplements. Their exact capture timestamp is absent from the inspected old receipt, so they are contextual bindings rather than fabricated timestamped manifest sources. They certify no complete retained Codex body.

The three actual current Blood Angels/Dark Angels/Space Wolves Legends PDFs are independently reopened and bound to the unchanged **29-PDF actual-GET receipt**. Their page-1 literals say `Non-Legends content removed (see the Warhammer 40,000 app for this faction’s rules support)`. The real printed legal date is September 30, 2026 **for those Legends packs only**. Their contents are Legends-only, not newer complete chapter Codex bodies. Black Templars and Deathwatch have no matching replacement full book in the inspected current catalogue. No MFM price URL is used as rules-body evidence.

No additional complete primary preview body was supplied in the inspected inputs. No individual preview, profile amendment, old model/Wahapedia/Black Library/DSL row, count, price or source-code fact is promoted to a complete body or whole `BODY_FIELDS` category. All 140 manifest records use `body.status=newer_full_unavailable`, `scope=[]`, `effective_date=null` and `retained_snapshot=null`. Their stored body rows remain unverified; the declaration is an availability limitation, not a newer-content or whole-category certification.

### Exact current price bindings and complete deferred accounting

Each of the 140 prepared rows has the exact canonical current marker `true`, the current snapshot capture, ordered MFM projection tiers equal to its exact full-name/source-slug ledger head, exact `kind=unit` ledger URL/raw hash/capture and literal header/price bindings in the unchanged saved HTML. The separate verifier checks **185 base unit-price tier literals** against canonical `items` descriptions/costs and top-level points, as well as every retained MFM tier/option. Cheap `per ...` options are not treated as a unit base price, and named mixed-model price tiers are not asserted as body composition.

The projection stores the MFM site root URL rather than a page hash. Exact page URL/hash/name/faction/capture are therefore joined through the actual unchanged ledger and raw receipt, and this storage limit is explicit in each binding. Points use `current_published` with `effective_date=null`; no capture/version/filename implies legal timing. Registry schema validation and current-marker checks alone do not establish the price projection's semantic agreement.

The 159 deferred rows reconcile without double counting:

| Exclusive disposition | Rows | Reason |
| --- | ---: | --- |
| Non-current canonical projections | 136 | No matching authenticated current-price evidence; mirror values are not official historical-price proof. This includes all 31 exact Legends identities and 11 unproven-route rows. |
| Current-priced, unproven book route | 16 | Other chapter keywords lack the exact requested book binding; no guessed default Codex attachment. |
| Current-marked Black Templars projection mismatch | 6 | Exact chapter ledger tiers/options differ from stored generic-page projections. |
| Current-marked name mismatch | 1 | Canonical `Invader ATV` differs from saved source `INVADER ATVS`; no identity normalization introduced. |
| **Total** | **159** | Every row retains its exact reasons and inspected source occurrences. |

The six Black Templars rows are **Impulsor `000002786`, Gladiator Lancer `000002787`, Gladiator Valiant `000002788`, Gladiator Reaper `000002789`, Repulsor Executioner `000002790`, and Repulsor `000002791`**. Their stored `mfm.current=true` and correct capture do not make their chapter projection exact: missing Multi-melta options and, for Lancer/Valiant/Executioner, differing base/occurrence costs are preserved in the inventory. These are concrete semantic preparation blockers, not authorization to modify the price owner or consumer code.

Armour of Antilochus `000004183` and Pedro Kantor `000002713` remain explicitly deferred. The AFB mirror values 140/90 are not certified as official historical prices. Historical 155/80 still require the independently reviewed rebuild-owner 61b restored copy and its exact source provenance/non-current markers. No false historical status or alternate original AFB restoration is introduced to satisfy schema validation.

### Actual copied trial and local review

The authorized UTF-8 Python 3.11 interpreter is `D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`. Bytecode writes are disabled. No model/network/install/service operation or redundant synthetic/full-native suite is run.

The trial uses the real prior validated AFB-derived database seed and explicit caller transactions with aligned expected priors. Positive application adds exactly 140 registry/history records; the new positive database contains **142** of each, including the untouched two source-only declarations. All 19 original table schemas/counts/content digests remain exact, and both private databases pass `PRAGMA integrity_check`.

| Actual private check | Result |
| --- | --- |
| Positive apply with 140 aligned absent priors | Pass; exact canonical declarations resolve |
| Exact replay/no-op with all 140 aligned records | Pass; entire SQLite file byte-identical |
| Body-support checks for each of six categories on every declaration | **840 denials**, as required by empty verified scopes |
| Late wrong canonical identity | Rejected: `Exact canonical coverage identity mismatch`; registry/history and file exact |
| Late wrong price raw hash | Rejected: `Exact published price provenance mismatch`; registry/history and file exact |
| Historical full-body mutation without proven legal date | Rejected: `Invalid body effective date`; no historical certification |
| Current full-body recertification using unchanged unavailable evidence | Rejected: `Retained sources cannot recertify an unavailable newer body` |
| Cancellation on second registry write, after earlier history/registry work | Original interrupt propagates; savepoint restores original seed tables/records/history |
| Caller rollback after otherwise successful application | Entire seed SQLite file byte-identical |

Negative mutations are explicit rejection controls, never proposed source-authenticated declarations. No retained-full-body positive trial is claimed because no complete retained body has independent literal/category authentication in this slice. Original proofs remain untouched.

`verify_canonical.py` performs separate read-only accounting/source verification: every actual SM row and original JSON, all six raw source pages/494 heads/ordinals, header and price byte locators, owning-card hashes, projection/base tiers, catalogue pointers/literals, announcement bytes/dates, exact identity resolutions, history digests, table preservation, database integrity and scratch-script AST syntax. Its first attempt used the wrong parser signature and is preserved in `verification-attempt-01.txt`; inspection confirmed `parse_source_page(html)` returns a row-bearing object, and the corrected verifier explicitly supplies page ordinals. The final verifier passes. This harness correction changes no application API or source evidence.

Local generic review checked ownership, identity ambiguity, date semantics, whole-category claims, exact prices, transaction/cancellation behavior and complete/deferred accounting. The duplicate names are distinguished by exact chapter keywords/routes; the six chapter-price discrepancies and mixed Deathwatch row are deferred rather than forced through schema validation. This is local preparation review and a separate verifier, **not independent host semantic approval**. That external review remains a finite gate.

| New owned evidence | SHA-256 |
| --- | --- |
| canonical-inventory.json | `12104be8a9e65e789107cf11a20d0c0c43bd00830150839e6a923070ca367c51` |
| book-availability.json | `a8ba0a327a16c2e54ff7d6f2584284a2f3fea5ee66d15a65af3545a933a914e7` |
| canonical-manifest.json | `21b64589a1256ae5646a08fa44f168af7ec6bf97e99f16ea07d2e47f3dd1acd8` |
| canonical-bindings.json | `b66a0a4d442ee5263fe4a0809e6a9d037a354d90c7d8aa8e83caf0c6d0671eea` |
| canonical-trial-results.json | `5853d48144b4467a85ff358da9ac14e21693781b9bc00442b37ed98a08a3a5ff` |
| six-slug-head-occurrences.json | `e222b67baca8113af464f371ce0ea545e48bc337e3f92ab2c17f32f0c0bd943d` |
| input-freeze.json | `1298b97535172fd9eb29d8982010b9dd50d6e0e16dc31df9191644dcdc75a127` |

The freeze covers **111** bounded original inputs, including the exact active AFB database, prior source-only artifacts/trials, original primary receipts/PDFs, raw MFM pages, protected Black Library/vector inputs and reviewed boundary modules. All remain exact, with only this authorized report append excluded from whole-file equality and instead checked by its exact original prefix. This is not a new 19k-asset or immutable-archive audit. `final-verification.json` records artifact hashes and the completed independent checks within this local preparation.

### Finite handoff and remaining gates

The finite six-route/299-row availability preparation is now complete with a 140-record manifest, literal bindings, explicit blockers for every remaining row and actual copied-trial acceptance. The existing read-only fresh-build registry/history persistence finding and restoration plan above remain pending implementation by their owner; this continuation does not take over that work. The 47 unsupported historical canonical names, five Unicode SQL conflicts, 13 overlay-ledger integration, chronology/setup/stage/runtime/wiki/retrieval acceptance and active promotion/publication remain separately owned and unclaimed.

New verified learning for the existing checkpoint/roadmap/decision note is that a current marker plus exact ledger source metadata does **not** prove a chapter's projected tier semantics: six Black Templars copies retain generic-page values/options while their exact chapter ledger differs. Complete ordered keywords also expose a mixed Deathwatch/Agents row that a simple chapter-membership count would route unsafely. The tier verifier compares named multi-model price literals as well as plain model counts and excludes per-option charges from base cost. These verified facts are recorded here for root's deduplicated knowledge handoff, within the restricted report/evidence ownership.

Independent host semantic/generic review of this finite candidate, any resulting scoped correction, and GNHF's clean report commit remain outstanding. The full loop stop condition is therefore **not met** in this iteration. No project completion, full current Codex parity, release/deployment, legal-list eligibility or external publication is claimed. All started foreground checks exit; no background server/browser/watcher/service was started.

The subsequent explicit stop-hook authorized the duplicate-checked knowledge handoff. It appended this actual canonical result and remaining gates to `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`, extended the existing learning decision `C:/Users/Administrator/learn-notes/decisions/20261001-separate-transactional-source-coverage.md` and its README index, and added the resolved verifier-call record `C:/Users/Administrator/error-notes/rag/20261004-error-20-canonical-verifier-parser-call.md` with its README index. The six note outcomes and five exact prior-body recovery copies are bound in `canonical-availability/knowledge-handoff/verification.json`; all three Git indexes remain unchanged. The six chapter-price mismatches and body/book-review blockers are not recorded as resolved errors. No new harness rule, duplicate decision, invented commit explanation, manual staging/commit/push or publication was performed; root publishes intended notes after other writers finish.
