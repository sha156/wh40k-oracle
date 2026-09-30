# Approved source retirement acceptance

Status: **recoverable pre-apply archive verified on October 1; production retirement and final active-asset acceptance remain pending**. This report is an incremental checkpoint, not release acceptance. No active PDF, cache, database, index, term or wiki artifact has been removed or published in this iteration. The 156 tracked Tau pilot files remain tracked until the retirement step.

## Approved baseline and scope

Work began on clean `codex/review-answer-provenance` at the exact approved launch commit `c68b73550d8b0a7812d6ad499e4e0dc6973969d0`. The human's launch gate approves final preparation `b412a4756f0a7edd84f962069d8362ddb7b602f0` and its independent Python/code reviews. Their verdicts were read and copied into the recovery archive. The preceding host/preparation suites are historical evidence; this iteration does not claim to have rerun them.

The exact approved inventory remains `D:/Project/py/RAG/db_sources/release-check-20260930/fan-source-inventory.json`. It names 27 raw PDFs, 26 matching refined directories and three orphan refined directories. Four PDFs retain the inventory's **unverified original download provenance** classification despite official-style layouts; retirement does not establish fan authorship. All 35 root English PDFs and 34 manifest-backed official Chinese PDFs remain present and match their reviewed hashes. The earlier named Votann retirement and all historical archives were left in place.

The production baseline is the frozen 20,099-file manifest from preparation iteration 1, covering `data`, `data_refined`, `db`, `local_vector_store`, `wiki`, `wiki_build` and `db_sources/blacklibrary`. Every file's bytes and the complete file membership matched before copying and again after copying. The active database, original/staged index, original terms/pairing/entities, all inventory PDFs and both staged database trials were also checked against their respective saved input/output hashes. Only the approved **alias-only** database candidate was copied into the publication evidence; the diagnostic name trial was not copied there.

## Recoverable archive

Archive root: **`D:/Project/py/RAG/archive/source-retirement-20260930/`**. Existing `archive/` Git exclusion applies; `git check-ignore --no-index` confirmed it. The destination was required to be absent before creation. Source and target absolute paths were resolved and confined to the intended workspace/archive; source symlinks were rejected. Structured `Path`/`shutil.copy2` operations copied files without moves, recursive deletion or overwriting existing recovery files. No SQLite WAL, journal or shared-memory sidecar was present when the original database was copied.

`pre-apply/` preserves original relative paths. It contains **8,276 files / 157,214,944 bytes**:

| Recovery group | Files | Preservation |
| --- | ---: | --- |
| Exact approved raw PDFs | 27 | All original bytes; 96,175,729 bytes total |
| Exact 26 matching + three orphan refined caches | 3,176 | Every current file in the 29 inventory directories |
| Active SQLite | 1 | Original `db/wh40k.sqlite`, all schema and table rows |
| Active index and processed registry | 4 | Original FAISS/pickle plus both existing sidecars |
| Generated wiki and existing wiki files | 4,984 | Full current wiki copy, including original terms and keyword artifacts |
| Pairing/entity/build cache artifacts | 81 | Full current `wiki_build` copy |
| Black Library alias history | 1 | Original history document and its provenance fields |
| Corpus manifest and approved policy | 2 | Exact current files |

All **156 tracked Tau pilot originals (78 Markdown + 78 metadata)** are included, verified against their current bytes, and enumerated individually in the manifest. No empty replacement files were created.

`reviewed-evidence/` contains **29 additional files / 82,849,871 bytes**, including the inventory, preparation report, original/filtered/generated term copies, original production manifest, complete database/index dry-run snapshots, alias-only database candidate, its row snapshot, pruned index candidate and review verdicts. These copies preserve the original evidence; they do not constitute publication.

The archive also contains its two manifest files, for **8,307 total files**. Verification reconciled all 8,305 copied files with their manifest paths, byte sizes and SHA-256 values, with no missing or unlisted copy files.

| Manifest | SHA-256 |
| --- | --- |
| `archive-manifest.json` | `e4e41c2e51bc614f95b6e9502474dce59c1132153ed4451b3d015ff8d8db1c37` |
| `production-pre-apply.json` | `1b64a7d56348f624eae611fc6d0de50db616fe0ee8eecfaebaab577a5403e709` |

The recovery database's SHA-256 remains `af4c651da438d1d0c48c22462f1bfde0c236a2e859b81ccc7b2b61c1bdc73069`. Each other file's independent hash is recorded in `archive-manifest.json`; the production manifest additionally records unchanged retained official and Black Library files that are not themselves recovery copies.

For recovery, first verify both manifest hashes and the selected file records, then use the originals under `pre-apply/` and their recorded relative paths. Do not use `reviewed-evidence/` as an original-asset restore tree: it also contains proposed cleaned candidates. Restoring a retired source path does not remove its source-policy exclusion. Keep this archive immutable during later publication and record subsequent evidence outside it.

## Verification completed in this iteration

Evidence root: **`D:/Project/py/RAG/db_sources/release-check-20260930/retirement-apply/iteration-01/`**. All commands used `D:/Project/py/RAG/.venv/Scripts/python.exe` (the configured Python 3.9.1).

| Check | Result | Evidence |
| --- | --- | --- |
| Production input membership and SHA-256 before/after archive | **20,099 unchanged**, zero changed/added/removed files | Archive production manifest; `archive-summary.json` |
| Recovery-file manifest reconciliation | **8,305 copied files verified**, plus two manifest files | `archive-verification.json`, `archive-verification.log` |
| Exact source gates on archived paths and original/restored entry paths | All **56** raw/cache entries excluded in both forms | `archive-verification.json` |
| Source-policy regression suite | **11 passed, zero skips, five warnings**, 0.51 seconds | `policy-focused.log`, `policy-focused.xml` |
| Read-only recovery database integrity/schema/complete row snapshots | `integrity_check = ok`; all **18 tables** and schema exactly equal frozen original | `archive-verification.json`; archived database dry run |
| Canonical recovery data | **1,721 units, all 1,202 Chinese names, 1,685 original alias rows** preserved | Same row-snapshot verification |
| Black Library history | All **925 pairs** and original authority/source fingerprint preserved | Original-byte check plus history structure verification |
| Reopened original recovery index | All **5,905 IDs/order/metadata/text/vector-byte hashes** equal original dry run | `archive-verification.json`, `archive-verification.log` |
| Reopened archived reviewed prune candidate | All **3,404 IDs/order/metadata/text/vector-byte hashes** equal retained dry run; **1,128 Black Library documents/vectors** retained | Same index verification |
| Embedding activity | **Zero embedding calls**; both embedding methods raised if invoked | Same index verification |
| Tracked pilot recovery | **156/156** paths and current file bytes preserved | Manifest and verification JSON |

Verification used a new read-only SQLite connection and reopened both trusted local FAISS copies. Index checks compared each reconstructed float32 vector hash and complete serialized document fingerprint, not merely counts. This verifies recoverability and the archived candidate; **the active index still contains 5,905 documents**.

Two audit-harness assumptions were corrected without changing preparation or production. The initial pre-copy check mistakenly required preparation iteration 4's older policy hash (`75ffcca4…`). It stopped before creating the archive. The current policy instead matches the approved iteration-5 negative-identity catalogue hash `f3760ed1f9c86432ac2f28384c2cec97ebc80ca5196193685ff135490c2c2d6d` and the launch commit's parsed policy exactly. The first archive verifier also assumed `aliases_history.json` was a top-level list; it is a document with `authority`, `source_units_sha256`, `description` and **`pairs`**. Its failed log is retained as `archive-verification-first-failed.log`; the complete corrected verification passed. The document remains unchanged and is not treated as a retiring-alias inventory. The index verifier emits the known Pydantic `dict()` deprecation warning to preserve the frozen fingerprint convention.

## Remaining bounded retirement and host work

The next publication step must recheck current inputs against the archived/frozen reviewed hashes, then retire the exact inventory files and remove the exact tracked pilot from future Git publishing. Active originals still exist. The copied **3,404-document** prune, processed-key cleanup, **982-row alias-only database**, filtered **125 ordered term pairs**, filtered unmatched/entities and normal keyword/wiki generation have not been published. Canonical names and the other 17 database tables must remain unchanged; the name-trial database remains diagnostic and unapproved.

After publication, run the required meaningful cached-resurrection, alias/name, keyword/temp-cwd and preservation regressions; inspect active references; regenerate affected pages through normal commands; run the **final active-asset full native suite and wiki lint**; and record exact legitimate retired-input skips. No final native/wiki result or full retained-PDF ingestion is claimed here. The retained terrain PDF's prior absence from the index/processed registry remains the preparation's documented baseline limitation.

Host integration/publication, Docker/browser acceptance, knowledge repositories and the separately staged official refresh remain outside this iteration. During the archival iteration, no application/test code, API reliability files, frontend dependencies, benchmark gold, other repositories or isolated worktrees were changed. No manual commit/push/merge, crawl, official refresh, container rebuild/restart/deployment or long-running service was started. All finite hash, copy, verification and pytest processes completed; the existing Docker services were left running. The orchestrator's `notes.md` was read and left untouched.

## Explicit post-iteration knowledge handoff

The subsequent user-invoked lifecycle hook requested the local knowledge handoff. `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` now record this archive checkpoint, verification and remaining publication/final-test work. The existing learning decision `C:/Users/Administrator/learn-notes/decisions/20260915-guarded-rules-and-derived-consumers.md` was extended and its README entry updated. The recurring GBK diagnostic was added to the existing `common/20260921-error-41-python-stdout-gbk.md`; the resolved history-container assumption is recorded separately at `C:/Users/Administrator/error-notes/rag/20261001-error-07-history-document-shape.md`, with its README entry. Existing unrelated/staged edits are preserved. No manual staging/commit/push or cross-project harness promotion occurred; the archive/report commit explanation awaits the real GNHF commit.
