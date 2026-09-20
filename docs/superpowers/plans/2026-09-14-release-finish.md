# Official points sync and release finish

## Current September 20 local scope

Use the [reconciled local roadmap](2026-09-20-local-completion.md), which supersedes stale paused/open checkboxes below. Both Docker services are running; live codex, points, simulator, roster and final chat checks passed. Card citations and named-table retention are fixed; manual Markdown export is added. Exact tests and browser limitations are recorded in the [acceptance report](../reports/2026-09-20-lookup-deployment-acceptance.md). PR #74 carries the release and its GitHub status records the merge. Public-source Ork gaps and Docker restart durability remain open; cloud is deferred.

## September 20 optimized runtime acceptance

- [x] User started Docker Desktop; deploy final optimized API image and verify health/warmup and matching source hashes.
- [x] Complete live question 63 HTTP check (51.881s, no degradation, six order effects) and inspect the rendered Titan codex.
- [ ] Finish latest PR checks, merge PR #74 and synchronize checkouts.
- [ ] Improve per-field citation precision: one new response cites the general orders page for card-specific details. Preserve this limitation rather than claiming complete provenance enforcement.

Evidence: [deployment acceptance](../reports/2026-09-20-lookup-deployment-acceptance.md). Public-source Ork and Docker startup-durability work remains open. Earlier blocked status below is historical.

## September 20 release follow-through

- [x] Review final optimization/checkpoint hosted CI: Python and frontend passed; 2,193 hosted tests passed and 331 asset-dependent checks skipped.
- [x] Open draft [PR #74](https://github.com/sha156/wh40k-oracle/pull/74), preserving unchanged-gold benchmark evidence and failed candidate runs.
- [ ] Start Docker Desktop, deploy the already-built optimized image and verify live question 63 answer/latency. Engine unavailable; automatic approval review blocked startup, so user action is pending.
- [ ] Require final deployed acceptance and current PR checks before merge, then synchronize checkouts.

No new application/data changes. Public official Ork rules and Docker startup durability remain open. See the updated [lookup checkpoint](../reports/2026-09-18-lookup-checkpoint.md); earlier statements about running services are historical.

## Latest continuation paused — September 18

The user requested save and stop after the lookup benchmark reached **115 correct / 0 partial / 0 wrong** with unchanged gold. Implementation through `39c16a2f9` is pushed on `codex/benchmark-lookup-completeness`. Canonical identity, faction inventory, source-scope disclosure and identity-first handling are implemented; question 118 base comparison did not reproduce a regression. Full native pytest passed 2,527 before the final three added tests; final focused tests passed 124. API/browser checks passed on `60fdee85b`, and the final I/O optimization image built successfully. Remaining release steps are deployment and HTTP acceptance of that final image, final CI review, PR/merge and checkout synchronization. See the [lookup checkpoint](../reports/2026-09-18-lookup-checkpoint.md). The running app remains available; Ork source and Docker startup-durability limits are unchanged.

User request: complete the five-step finish plan, with local points agreeing with the official Munitorum Field Manual. Historical working states below describe earlier checkpoints; the latest branch and runtime state above supersede them.

## Working state

- Implementation workspace: `D:/Project/py/RAG`, branch `codex/official-sync-finish`.
- GitHub/main baseline: `90de241112d000c93e06eff2e39ce2e3bfed0d48`.
- Existing work: 28 modified files and two untracked files, preserved before edits.
- Backup: `C:/Users/Administrator/AppData/Local/Temp/wh40k-finish-20260914-ac9pmgp_` (32 files, SHA-256 manifest and binary Git patch).
- The Codex checkout at `C:/Users/Administrator/Documents/ChatGPT/RAG` now contains the verified implementation on the same branch. The running app and local model/database/source assets remain in `D:/Project/py/RAG`.

## Acceptance checklist

- [x] Preserve and review existing changes; run baseline tests.
- [x] Repair MFM card boundaries; reject incomplete/conflicting source parses.
- [x] Fetch every official faction page, retain provenance and reconcile coverage in both directions.
- [x] Trial database sync on a copy; apply verified points; regenerate wiki through its supported commands; verify no current tier remains stale.
- [x] Refresh available official rules/datasheets and record exactly what changed or lacks an authoritative accessible source.
- [x] Implement conservative free-text roster parsing with explicit unresolved lines.
- [x] Connect bounded conversation history to agent requests.
- [x] Replace stale landing-page example; repair citations and stream/error handling.
- [x] Build the current frontend; verify API, UI, retrieval and representative roster workflows.
- [x] Complete live LLM conversation recall and refreshed benchmark acceptance (September 16 benchmark: 113 correct / 2 partial / 0 wrong; September 18: recall 6/6, API isolation and fresh fact verification passed).
- [x] Run full tests and record concrete host/provider blockers.
- [x] Complete an actual Docker build/start after WSL is working (September 16: both images built, containers started, API healthy and 85 targeted container tests passed).
- [x] Review final diff; produce source-linked sync and acceptance reports; consolidate the verified checkout.

## Sync definition

Official current prices are authoritative. Historical/Legends records must not be silently presented as current official entries. Matching prices on a reduced comparison subset is insufficient: every official source row must be accounted for, including chapter/conditional/repeated-unit tiers and units for which a full datasheet is unavailable. Unknown datasheet values must never be invented to make coverage look complete.

## Initial findings

- A new plain coloured Ork heading was missed; its prices leaked into the previous unit. A parser correction tested in memory recovered six names while the row count remained 113.
- Preliminary corrected comparison: 176 mismatched tier comparisons, 1,306 comparable entries across 30 faction pages. This is not an applied sync or a unique-unit count.
- Existing static frontend export predates current codex tabs.
- API session history is stored but not passed into the agent.
- Existing chat roster tools are explicit stubs; engine-based roster validation and critique already work.

## Verified checkpoint

- Full tests: 2,496 passed. Frontend lint/build: passed. Wiki: 0 errors, 1 alias warning, 691 informational notices.
- Official ledger 3,893/3,893; operational tiers 1,322/1,322; no missing/extra tiers or enhancement differences. Fresh database rebuild reproduces the ledger and prices.
- 40 official PDF downloads; 28 documents applied/refined; 1,256 text pages verified, one empty-text page explicitly skipped. Index saved with 5,770 chunks. Real retrieval through the web wrapper finds Universal Rules Updates page 1.
- Browser and API roster import validates 150 points as legal; critique evaluates the configured unit against four targets.
- Final real-provider memory/benchmark checks are blocked by DeepSeek HTTP 402. Docker build/start is blocked by WSL reporting that a required file cannot be found. These acceptance boxes remain open.
- Latest structured rules/DSL reconciliation and authoritative new datasheets remain next work; refreshed PDFs do not prove every database field is current.
- Detailed evidence and reproducible commands: `docs/superpowers/reports/2026-09-14-release-acceptance.md`.
- Index backup before ingestion: `C:/Users/Administrator/AppData/Local/Temp/wh40k-index-before-refresh-0ep8yrk9`. PDF/refined backup: `C:/Users/Administrator/AppData/Local/Temp/wh40k-before-rules-refresh-4odzp3jx` (earlier original backups also retained). Applied sync reports and database backup paths are in ignored `db_sources/mfm/sync-report-*.json`.
- Codex Stop note hook installed locally and saved in private claude-harness commit `c2d95c3`; its definition still requires native hook review before activation.

## GitHub and knowledge handoff

- Source implementation: `826127ca4`; generated wiki: `69b5a1b5a`; earlier work preserved in `709836f48`. Branch pushed as `codex/official-sync-finish`; both checkouts follow it.
- Private knowledge repositories updated and pushed: claude-harness `c2d95c3`, learn-notes `eabf36a`, error-notes `37e92f2`, project-devlog `29d11fd`.
- Final app check: health is ready and model warmup completed; the rebuilt UI displays the dated rules notice outside the source disclosure, and official search returns Nazdreg at 175 points with its MFM link.


## September 15 source follow-through

Tasks 1–2 now have a reviewed patch pipeline, six added datasheets, refreshed DSL and generated consumers. See [reconciliation acceptance](../reports/2026-09-15-structured-source-reconciliation.md). The unmatched list fell from 12 to 2 unit names and from 67 to 28 enhancement keys. Released Ork codex access and preview verification remain explicit source gaps.

## September 16 pause

[Live AI and Docker checkpoint](../reports/2026-09-16-live-ai-docker-checkpoint.md): benchmark 113 correct / 2 partial / 0 wrong. Docker acceptance passed. Same-session live recall failed by falling back to retrieval; task 3 remains open. User requested save and stop before a code fix.

## September 18 completion

[Live recall fix and acceptance](../reports/2026-09-18-live-recall-fix.md): JSON protocol history fixes the reproduced blank-response/fallback path. Full native tests: 2,518 passed. Rebuilt Docker API passed live recall, isolation and a points lookup that ignored stale draft context. Tasks 3–4 application acceptance is complete. The two partial benchmark answers and released Ork source gaps remain separate follow-up work. Docker startup required the socket-directory workaround again; do not treat it as a permanent host repair.
