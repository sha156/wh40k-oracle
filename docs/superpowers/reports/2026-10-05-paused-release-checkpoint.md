# October 5 release work saved and stopped

The user requested **save and stop**. All owned GNHF process trees and active
review agents were stopped. After stopping those jobs, only state verification
and the documentation handoff continued. Existing Docker
services remain running. This is a pause checkpoint, not release acceptance.

## Published application state

The application branch is `codex/review-answer-provenance`. Before this
documentation-only checkpoint, its clean, pushed HEAD was
`b30ad297dfcfac76797a630e7318c1444b517745`. PR
[75](https://github.com/sha156/wh40k-oracle/pull/75) remains a draft and unmerged.
The checkpoint commit can be identified from Git; no future commit ID is assumed.

Completed and integrated slices:

- Reviewed setup, chronology and rebuild foundations reached `642d0a0e9`;
  the root combined check passed 400 tests with zero failures, errors or skips.
- The Unicode coverage correction was narrowly cherry-picked to `fff4d974c`,
  excluding the then-blocked runtime ancestry. Its combined check passed 444
  tests; the four hosted Python/frontend checks for that revision succeeded.
- Nested calculation and archive qualifications reached merge `41dc49895`.
  Independent host review closed the HIGH defect. Root checks passed 649 tests
  on the exact candidate and 696 on the merged branch, without failures,
  errors or skips. Frontend verification passed 22 unit tests, TypeScript,
  lint and production build. This preserves complete source/identity warnings
  through answers, recovery, bounded history, digest and visible formatting.
- Snapshot replacement resilience and portable controls reached merge
  `349e4c6ec`. Root snapshot checks passed 140 tests with no failures, errors
  or skips. Native Windows controls and the declared-platform controls remain
  distinct; actual Linux/current hosted CI acceptance remains outstanding.
  The spontaneous production PermissionError cause is still **unknown**.
- The approved Daemons/Necrons report-only deltas reached `6552314b5` and
  `b30ad297d`. All 75 literal decisions and the separate 25-row/27-cell delta
  received host semantic review. Five unsupported storage/carrier gaps remain
  explicit. This did not promote rules, Chinese bodies, DSL or active assets.

The latest full actual-asset native run was the **intermediate** `fff4d974c`
run: **5,385 passed / 14 failed / zero errors / zero skips**, 5,399 XML nodes,
418.63 seconds. Its evidence is preserved at
`D:/Project/py/RAG/db_sources/release-check-20260930/host/native-intermediate-fff4-20261005/`.
No later full-suite success is claimed. The later focused and frontend checks
do not substitute for final full native, deployed browser or live benchmark acceptance.

## Saved worktrees

All paths below remain on disk. Do not reset, clean, archive or recreate a dirty
checkout when resuming. Worker reports describe their own evidence; pending
root review and integration must still be completed.

| Worktree under `C:/Users/Administrator/.codex/worktrees/` | Saved state | Remaining gate |
| --- | --- | --- |
| `release-native-build-recovery/RAG` | `codex/release-authority-rebuild`, HEAD `a522c820c8eb5dc584bc4dbf1c67e9838077f411`; modified `db_compile/retained_metadata.py`, `db_compile/update.py`; untracked `db_compile/authority_rebuild.py` | Finish and verify one whole-authority private rebuild/publication boundary, caller-owned retained metadata, bootstrap/latest history and complete localized-body contract. Earlier witness helpers are foundations, not complete rebuild acceptance. |
| `release-native-regressions/RAG` | Clean `codex/release-native-regressions`, HEAD `41e578add1b0fbaef20dbb55cf93ff1db5bdff6e`; six test files and one report committed | Worker evidence pairs the same 314 nodes: 302 passes/12 failures before, 314 passes after. Host review and narrow integration are pending. The two actual-data failures remain unsuppressed. |
| `release-final-integration/RAG` | `codex/release-chinese-name-recovery`, HEAD `41dc49895e849f864bb061875e5fb81311d7d08a`; modified `db_compile/blacklibrary.py`, `tests/test_zh_weapons.py`; untracked recovery report, fixture and `tests/test_blacklibrary_detail_names.py` | Preserve the unfinished missing-name and exact English weapon-fallback work. No new source matching, borrowed translation, guard relaxation or active projection is authorized by its partial state. |
| `release-field-sororitas-deathguard/RAG` | Clean HEAD `cf72f4e1b8d08635b5c663946d8bc0d2336fe20a`; report-only continuation committed | Saved report now covers all 33 Sororitas and 19 Death Guard records with worker semantic review. Root semantic reconciliation/integration remains pending; no active promotion. |
| `release-official-revisions/RAG` | Clean HEAD `abccf9d60722d59154a984c861716ab2f8fdaa3a` | Seven Thousand Sons decisions are committed; remaining Thousand Sons and Imperial Agents preparation is incomplete. Preserve ignored evidence from the interrupted continuation. |
| `release-rule-chronology/RAG` | Clean `codex/release-context-points`, HEAD `2a2e4bc16a1f33537b195e2742550e06d71452ae` | Complete Black Templars per-row chapter price/context work is saved. Host review evidence includes an APPROVE binding at this exact revision, but final orchestration reconciliation and merge were interrupted. No active price promotion. |
| `release-api-reliability/RAG` | Clean HEAD `4e820136ae9b7f16bc01b6829a4c605874e5d1dd` | Host REQUEST_CHANGES remains open: staged restoration omits the retained aliases history. Complete the combined input/consumer closure after accepting the rebuild/context work. Earlier 173 passes do not establish final staged fidelity. |

The native test-only candidate preserves strict archive identity/rollback checks,
the enhancement boundary crossing, all Helbrute faction identities, five reviewed
Chinese bindings, denial of the wrong-faction Servitor projection, and rejection
of stale 95-point Barge composition. It does not modify prices, gold or application
guards. See its saved `2026-10-05-native-regression-reconciliation.md` report.

## Data and deployment at pause

The active SQLite SHA-256 was rechecked at stop:
`afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`.
No staged source/body/Chinese/wiki/vector promotion was performed in this pause.
Active retrieval retains 3,404 documents, including 1,128 Black Library documents.

The copied-only normal Chinese restoration audit changed 1,139 to 1,144 detail
rows and 3,317 to 3,330 Chinese ability items, while preserving 4,041 English
abilities. The 3,330 count excludes two wrong-faction Servitor abilities. These
are copied audit results, not active-library or final-overlay acceptance.
The Rukkatrukk missing name and Captain on Bike's two unavailable Chinese weapon
names remain a separate guarded restoration/fallback task. Do not invent labels.

Docker is running the earlier images:

- API: `f1224f123ec38f06e17f52f735978032fe95658cfb4b3c9e0f2dd73544d34ddb`;
  `rag-api-1` was healthy.
- Web: `5156e1f53e6792b1f3de10da01106b885c5ba36e790c2a50cdaa48b2997cedda`;
  `rag-web-1` was running.

These images do not contain the latest accepted branch changes. No new Docker
build, final browser/real SSE/recall/export acceptance or 115-question live
benchmark was completed. No full-current-Codex or complete Black Library parity
is claimed. The 47 unsupported historical names remain unproven, and the four
wrong-identity Black Library responses remain quarantined.

## Resume order and evidence

1. Read this checkpoint and verify Git/worker status before starting anything.
   Resume the two dirty worktrees from their saved edits; do not discard them.
2. Finish whole-authority rebuild and Chinese-name/fallback acceptance, review
   the committed native test correction and chapter-context candidate, and
   reconcile the remaining field preparation without repeating approved slices.
3. Close the staged aliases-history and complete restoration/consumer/input
   closure using the accepted rebuild/context contract. Require successful,
   failed and interrupted copied controls before any active publication.
4. Perform reviewed active source/data/DSL/Chinese/wiki/index publication, then
   full native XML accounting, normal wiki lint, final frontend/model checks,
   fresh final CI, new Docker images, real browser/chat/export/recall checks and
   the unchanged-gold live benchmark before PR readiness or merge.

The stop evidence folder is
`D:/Project/py/RAG/db_sources/release-check-20260930/host/stop-20261005/`.
It contains verified stopped process IDs, exact worktree HEAD/status, runtime/DB
receipt, binary patches and copies of every untracked file from both dirty
worktrees, plus a hash/size manifest. No GNHF processes remained in the final
process snapshot. Existing assets, ignored proofs and unrelated shared-note
edits/staging were preserved. Root handoff records are in
`D:/Project/devlog/wh40k-oracle/`, with existing learning and underlying error
records updated rather than duplicated.
