# Approved source retirement acceptance

Status: **recoverable archive verified and reviewed index/processed registry published on October 1; remaining source retirement and final active-asset acceptance are pending**. The active on-disk index now contains **3,404 documents**, after exact removal of 2,501 approved-source documents. Every retained document and vector is unchanged. Raw PDFs, refined caches, database aliases, terms and generated wiki artifacts remain unchanged; the 156 tracked Tau pilot files remain tracked. This report is an incremental checkpoint, not release acceptance or deployed runtime acceptance.

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

## Verification completed in the archive step

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

## October 1 reviewed index publication

This individually verified step began at `816e21173` with a clean working tree. It publishes only the previously reviewed prune and processed registry. Before replacing any file, the publication helper verified the immutable archive manifest, **all 8,305 recovery/evidence copy hashes**, and all **20,099 production file hashes and membership** against the original reviewed baseline. Inventory and policy hashes still matched, and the original active index's 5,905 complete snapshots matched the frozen dry run. The candidate was read from the archive's reviewed evidence and matched the preparation output hashes and all 3,404 retained snapshots. Preparation code and evidence were not altered.

Evidence root: **`D:/Project/py/RAG/db_sources/release-check-20260930/retirement-apply/iteration-02/`**. `publish_index.py`, `pre-publication-gates.json`, `publication-journal.json`, `index-publication.json`, `index-publication.log` and `production-after.json` make the input gates, exact replacements and verification independently reviewable. Each destination was resolved within `local_vector_store`, each original was checked immediately before replacement, and each candidate was copied to a temporary sibling and hash-checked before `os.replace`. The helper includes recovery from the immutable original copies if replacement or verification fails. The final journal records all three replacements with verification complete and no rollback. No embedding methods were permitted to run.

| Active asset/check | Verified result |
| --- | --- |
| Exact document removal | **5,905 − 2,501 = 3,404**; every removed ID is absent |
| Retained evidence | **3,404/3,404** IDs, relative order, complete metadata, text/document hashes and reconstructed vector-byte hashes equal reviewed originals |
| Retained Black Library | **1,128/1,128** documents and vectors; other 2,276 retained documents are English inputs |
| Processed registry | **61 − 27 = 34**; all retained keys and values equal the reviewed mapping; no excluded-source key remains |
| Changed production paths | Exactly `local_vector_store/index.faiss`, `index.pkl` and `processed_files.json` |
| Other production assets | **20,096 files unchanged**, with no added or removed files; this includes all SQLite bytes, official PDFs, Black Library caches, raw/refined inputs and term/wiki assets |
| Focused policy/cached restoration/ingestion/vector reuse/refinement/Black Library regression suite | **115 passed, zero skips, eight warnings, 15.82 seconds**; `index-policy-focused.log` and `.xml` |

The published hashes are:

| File/snapshot | SHA-256 |
| --- | --- |
| `index.faiss` | `1a62affa4fc1be566702ee964c965b3c88f3eac98f6c692555a5148e0c04fd38` |
| `index.pkl` | `bda0a66bc301cf5f2118f30f5f66fe4f60adc662132a085d2ef700392b5156ab` |
| `processed_files.json` | `f1345c04f4e05f2a715e0998b04ffdeeb89934fc8fa8d79774c7bfcd5d16285a` |
| Ordered retained document/vector snapshots | `12461cd08ab6f8d827013018c3b785539f6c2ba56ef64e35e30f21270534d094` |

The unchanged `blacklibrary-refresh.json` is historical evidence of the preceding 5,905-document refresh, not a current prune report. Use `index-publication.json` for the applied result. The retained terrain PDF still has no indexed documents or processed key, matching the documented baseline; this step does not claim full retained-PDF ingestion. The known Pydantic `dict()` warning preserves the frozen document-fingerprint convention; the focused suite's warnings are existing dependency deprecations.

After the focused suite, a fresh audit rehashed all 20,099 production files against `production-after.json`, reopened the active index to compare all 3,404 retained snapshots again, and rehashed all 8,305 archive copies. All comparisons passed. `post-tests-verification.json` and `.log` record these results and the XML-confirmed zero skips/failures/errors. SQLite remains byte-identical to the original recovery database, SHA-256 `af4c651da438d1d0c48c22462f1bfde0c236a2e859b81ccc7b2b61c1bdc73069`; canonical identities, all 1,202 Chinese names and every official/Black Library database table therefore remain unchanged in this step.

No application/test source, database, PDF/cache, wiki generation or API/frontend dependency work was changed in this step. Docker was not reloaded, rebuilt, restarted or checked; the on-disk publication does not establish deployed retrieval behavior. No long-running service, crawl, browser or watcher was started. Full native and wiki acceptance remain required after all remaining assets are reconciled. The orchestrator's notes remain untouched, and no manual Git commit/push/merge occurred.

## Remaining bounded retirement and host work

The next publication step must recheck its relevant inputs against archived/frozen reviewed hashes, then retire the exact inventory files and remove the exact tracked pilot from future Git publishing. Active originals still exist. The **3,404-document prune and processed-key cleanup are now published**. The **982-row alias-only database**, filtered **125 ordered term pairs**, filtered unmatched/entities and normal keyword/wiki generation have not been published. Canonical names and the other 17 database tables must remain unchanged; the name-trial database remains diagnostic and unapproved. For a complete production comparison in later steps, use `iteration-02/production-after.json`: the original 20,099-file baseline is still the recovery record, but its three index/registry hashes have intentionally been replaced by the exact approved candidate hashes.

After publication, run the required meaningful cached-resurrection, alias/name, keyword/temp-cwd and preservation regressions; inspect active references; regenerate affected pages through normal commands; run the **final active-asset full native suite and wiki lint**; and record exact legitimate retired-input skips. No final native/wiki result or full retained-PDF ingestion is claimed here. The retained terrain PDF's prior absence from the index/processed registry remains the preparation's documented baseline limitation.

Host integration/publication, Docker/browser acceptance, knowledge repositories and the separately staged official refresh remain outside this iteration. During the archival iteration, no application/test code, API reliability files, frontend dependencies, benchmark gold, other repositories or isolated worktrees were changed. No manual commit/push/merge, crawl, official refresh, container rebuild/restart/deployment or long-running service was started. All finite hash, copy, verification and pytest processes completed; the existing Docker services were left running. The orchestrator's `notes.md` was read and left untouched.

## Explicit post-iteration knowledge handoff

The subsequent user-invoked lifecycle hook requested the local knowledge handoff. `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` now record this archive checkpoint, verification and remaining publication/final-test work. The existing learning decision `C:/Users/Administrator/learn-notes/decisions/20260915-guarded-rules-and-derived-consumers.md` was extended and its README entry updated. The recurring GBK diagnostic was added to the existing `common/20260921-error-41-python-stdout-gbk.md`; the resolved history-container assumption is recorded separately at `C:/Users/Administrator/error-notes/rag/20261001-error-07-history-document-shape.md`, with its README entry. Existing unrelated/staged edits are preserved. No manual staging/commit/push or cross-project harness promotion occurred; the archive/report commit explanation awaits the real GNHF commit.

## October 1 index-publication knowledge handoff

The user-invoked lifecycle hook extended the existing source-retirement decision instead of adding a duplicate. `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` now record the verified 3,404-document disk index, 34 processed keys, 115 focused passes without skips, unchanged recovery/database assets and the new explicit post-publication baseline. The learning decision and its README describe candidate publication gates, advancing active manifests, historical sidecars and the runtime verification boundary.

Real archive documentation commit `816e21173` is explained at `D:/Project/devlog/wh40k-oracle/commits/20261001-816e21173-source-retirement-archive.md`; its actual diff contains only the preceding archive checkpoint report. The current index-publication report remains uncommitted, so no commit explanation for it is invented. This step resolved no new underlying error and warrants no new error note or cross-project harness promotion. Unrelated edits/staged work are preserved; no manual staging, commit, push or publication occurred.

Handoff verification preserved the prior content of five edited files, 21 unrelated dirty files byte-for-byte and six pre-existing staged statuses. The host concurrently committed separate knowledge records in all three note repositories; one unrelated error note now matches its exact committed host version (`56546b6`). An initial raw-index checksum assertion consequently failed; raw Git-index byte equality is not claimed or restored. The corrected verification checked content/staged statuses and retained the concurrent commits. `iteration-02/handoff-preservation.json` records the observed heads and exact scope. Active index, database and archive-manifest hashes remain unchanged by this handoff; all whitespace checks passed. No long-running process was started.
