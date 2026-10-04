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
