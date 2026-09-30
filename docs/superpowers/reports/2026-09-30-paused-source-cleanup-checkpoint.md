# Paused source cleanup and local acceptance

The user requested **save and stop** on September 30, 2026. Application, source, crawling, testing and deployment work is stopped. Only this handoff was completed afterward. Docker remains running. The earlier request to finish the project resumes only when the user asks to continue.

## Saved baseline and authorization

- Runtime: `D:/Project/py/RAG`.
- Branch: `codex/review-answer-provenance`.
- Application/documentation baseline: `ad4cb29405c64c7aaf2f0f68b123ab557a95df06`; implementation baseline: `a9057ec97`.
- Draft [PR #75](https://github.com/sha156/wh40k-oracle/pull/75) remains unmerged.
- The application working tree was clean at the stop request. This continuation made no application or test source edits and did not alter the active database, index, PDFs or source caches. Official-source staging and browser artifacts are ignored local files.
- The user explicitly answered **Retire the other fan-translated rules PDFs**. This authorization is saved and does not require another scope question when resuming. The broader retirement has **not** been applied. The previously retired Votann PDF remains excluded by the existing policy.
- API image: `sha256:f1224f123ec38f06e17f52f735978032fe95658cfb4b3c9e0f2dd73544d34ddb`; web image: `sha256:5156e1f53e6792b1f3de10da01106b885c5ba36e790c2a50cdaa48b2997cedda`. A read-only `docker compose ps` at handoff showed API running/healthy and web running. No container restart or rebuild was performed in this continuation.

## Checks actually completed

The unchanged real-browser suite passed **12/12 tests in 35.817 seconds**, with no skips, retries or failures. It reused the running Docker API/web and system Chrome 154. It covers codex language switching, roster validation/critique, simulator selection/results, input/error presentation, and actual Markdown/clipboard delivery.

Trace reconciliation found eight live `/simulate` POST requests, two live `/roster/validate` POST requests and one live `/roster/critique` POST request, all HTTP 200. Export tests restore a fixture and do not test fresh LLM generation. One simulator response is deliberately intercepted to test error presentation. Ten obsolete fetches were cancelled while switching factions; selected-faction requests succeeded. The three extracted final frames were visually inspected without obvious overflow. One passing run does not establish a repeated-run flakiness benchmark.

Evidence under `D:/Project/py/RAG/db_sources/release-check-20260930/e2e/`:

- `REPORT.md`, `summary.json` and `first-run.json`.
- `first-run-html/index.html`.
- `codex-final.jpg`, `roster-critique-final.jpg`, `simulator-loadout-final.jpg`.
- Twelve original traces under `D:/Project/py/RAG/web/test-results/release-20260930-first/`.

No new native full suite, fresh-chat acceptance or unchanged-gold model benchmark was run in this continuation. The preceding accepted baseline still has 2,814 native passes; do not report those as a new run after the proposed retirement.

## Approved source retirement, not yet implemented

The read-only inventory is `D:/Project/py/RAG/db_sources/release-check-20260930/fan-source-inventory.json`. It identifies **27 remaining Chinese translated PDF candidates** contributing **2,501 of 5,905 active search chunks**. Exact pruning would leave **3,404**, including all **1,128 Black Library chunks**. These are projected results, not an applied cleanup.

Twenty-three inputs have translator markers or community Word/WPS evidence. The two June 2025 points/balance files, `帝国特勤中文.pdf` and `灰骑士中文.pdf` have official-style layouts but no verified original download provenance. Keep that uncertainty explicit rather than claiming all 27 are proven fan-authored. The user-approved policy is to keep verified official GW inputs and Black Library Chinese data active.

Retain 35 root English PDFs, including the two English codices, and all 34 GW-manifest-backed Chinese PDFs in `data/官方中文`. The inventory verified all 34 recorded hash prefixes and GW download URLs.

The 26 corresponding active refined-cache directories contain 1,521 Markdown pages. The quick reference has no refined cache. Also retire three orphan community caches whose raw PDFs were already archived: `10版40K通用技能速查表1.08` (five pages), `战锤40K总规则10版老湿腐版1.11` (39), and `规则注解中文` (18). No file has been moved yet.

Confirmed dependencies to address before publication:

1. `wiki_engine/keyword_index.py` directly reads `data/11版40K通用技能速查表.pdf` for keyword classification. Replace this dependency with verified official Core Rules section extraction before archiving/regenerating. Chinese glossary names already have a separate official source. No replacement has been coded or tested.
2. `wiki_compile/terms.py` and `db_compile/entity_resolver.py` read cached term pairs without the shared retirement filter. `wiki/terms.json` and `wiki_build/pairing.json` contain 62 Tau pairs attributed to the retiring Tau codex; `wiki_build/entities.json` contains 107 such entities. Add policy gates and reconcile cached artifacts without deleting independently sourced names.
3. The database has 705 aliases attributed to `data_refined`, 961 to Black Library (`blackforum`) and 19 to `community`. Compare a filtered alias/name rebuild on a copied database before removing rows. Existing attribution is aggregated and cannot prove every alias has only one source.
4. Extend `corpus_policy.json` beyond the named Votann source and cover normalized metadata book names as well as raw/cache stems. Preserve official and Black Library inputs. The existing ingestion/refinement/extraction/synthesis guards must remain effective for restored old caches.
5. Back up PDF/cache/index/database assets, prune exact attributed vectors, remove incremental processed keys, and verify every retained document/vector and official/canonical row. Regenerate pages through normal commands only.

No generated wiki page was found with an exact backlink to a retiring raw refined-cache path. That does not prove all derived names are independently sourced.

## Official freshness audit, staging only

Saved evidence is under `D:/Project/py/RAG/db_sources/release-check-20260930/official/`. The audit did not write active production assets and all its shell sessions completed before the handoff. No known audit process remains running.

The current English downloads catalogue contains 38 entries versus 40 on September 14: 22 unchanged, 13 changed, three added and five removed titles. `download-comparison.json` records downloaded-byte hashes, sizes, page counts and extracted text from the first three pages. PDF bytes were inspected in memory and were not promoted into active assets.

A complete 30-page MFM capture is preserved in `mfm/fetch-l5jy80op/`, including raw responses and the hash manifest. `mfm-baseline-diff.json` compares 3,893 September 14 rows with 3,627 fetched rows: **991 changed prices, 591 added keys, 857 removed keys**, across 28 factions. The fetched source lists Guilliman at 415 versus the active snapshot's 355. Ordinary Marneus Calgar 180 and Kaius Konorius 100 are added source-only keys; Armour of Antilochus 155 is removed from that source. These findings have **not** changed the running app.

`mfm-trial-report.json` has `applied: false`. A temporary-database trial matched 1,004 unit records and updated 339, with 22 enhancement-price changes. Its official ledger matches all 3,627 source rows, and its final 1,306 comparable unit tiers agree with zero mismatches. Seventy-two enhancement keys remain source-only. Trial convergence proves the available price pipeline, not current full-rule or canonical-membership coverage.

Effective-date/context reconciliation was interrupted. The saved downloads page labels MFM updated 30/09/2026, and several inspected Faction Pack covers say legal from September 30. A newly linked Balance Update: Emboldened Astartes article was not read. GW's [September 27 Sunday Preview](https://www.warhammer-community.com/en-gb/articles/zuwukdba/sunday-preview-might-of-the-ten-thousand/) says the Space Marines Codex releases on Saturday; October 3 is a calendar inference. Confirm how the new prices and PDFs relate to that release before promoting them. No complete new Ork rules were acquired. Read `download-catalogue.json`, `download-comparison.json`, `mfm-index.html` and `downloads-index.html` before resuming external retrieval.

## Resume order and remaining limits

1. Read this checkpoint and the saved inventory/audit; verify Git, runtime and active asset hashes against the stopped state. Preserve unrelated edits in the knowledge repositories.
2. Finish the official effective-date and source-context reconciliation. Stage and review price/PDF changes before applying; keep points-only entries distinct from acquired datasheets.
3. Implement the approved broad PDF retirement with the official keyword classifier and cached-term guards, then reconcile copied database aliases/names and exact index pruning.
4. Obtain independent code/Python review, run meaningful regressions and the final native suite, regenerate/lint wiki, deploy the reviewed result and rerun affected browser/fresh-chat/unchanged-gold acceptance.
5. Publish only the intended implementation, generated artifacts and evidence on the existing draft PR. Do not claim the current passing browser baseline covers future source changes.

Four upstream Black Library wrong-identity responses remain unresolved; 94 reviewed empty listings remain excluded under the existing inventory fingerprint. Released Ork full-rule gaps and Space Marines release coverage remain open. Host reboot durability is unverified, cloud is user-deferred, and automatic AI-answer publication into official wiki is intentionally unwired. No new resolved-error note or cross-project harness promotion is warranted for this read-only audit.
