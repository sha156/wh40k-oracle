# Official points sync and release finish

User request: complete the five-step finish plan, with local points agreeing with the official Munitorum Field Manual.

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
- [ ] Complete live LLM conversation recall and refreshed benchmark acceptance after provider availability is restored.
- [x] Run full tests and record concrete host/provider blockers.
- [ ] Complete an actual Docker build/start after WSL is working.
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
