# Approved source retirement acceptance

Status: **recoverable archive, exact raw/refined retirement, index/processed registry and approved alias-only database publication verified on October 1; term/wiki publication and final active-asset acceptance remain pending**. The active on-disk index has **3,404 unchanged retained documents/vectors**, after removing 2,501 approved-source documents. All 27 approved raw PDFs and 29 refined-cache directories are absent from active storage and recoverable from verified originals. The **156 Tau pilot files (78 Markdown + 78 metadata)** were removed from Git in `85892fa2a`. The active database now has **982 alias rows**, after removing exactly 703 traced refined-source rows; all 17 other tables and all 1,202 canonical Chinese names are unchanged. Terms and generated wiki artifacts remain unpublished. This is an incremental disk-asset checkpoint, not release or deployed-runtime acceptance.

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

## October 1 exact raw/refined retirement

This bounded step started at clean `82e3c31af`, after reading the preceding iteration notes and the host's frozen index-publication review snapshot. It retires only the exact inventory raw/cache paths, including the tracked Tau pilot inside the named Tau refined directory. No application/test source, reviewed preparation correction, alias database candidate, term asset or generated wiki asset was changed.

Evidence root: **`D:/Project/py/RAG/db_sources/release-check-20260930/retirement-apply/iteration-03/`**. `retire_sources.py`, `pre-retirement-gates.json`, `pre-retirement.log`, `retirement-journal.json`, `source-retirement.json`, `source-retirement.log` and `production-after.json` record the exact input gates, removal identities, recovery journal and resulting active baseline. The helper first completed a read-only gate run; the apply invocation repeated every gate before removal. The previous publication helper and `iteration-02/production-after.json` hashes match the host's independently frozen review snapshot.

Both gate runs verified the immutable archive manifest and all **8,305 copied files**, current inventory/policy hashes, and every active file against the **20,099-file post-index baseline**. All 27 raw paths, 26 matching directories and three orphan directories equal the inventory and archive manifest, without glob/substr selection. Every retiring file matched its independent archived copy immediately before removal. Absolute targets were resolved within the intended `data` or `data_refined` root, equality with the root was rejected, and every descendant was checked for symlinks and resolution outside that root. Structured `Path.unlink` and `shutil.rmtree` calls removed only those exact targets. No recursive operation targeted the archive, and no historical original was moved, deleted or rewritten.

The immutable original copies remain under **`D:/Project/py/RAG/archive/source-retirement-20260930/pre-apply/`**, with original relative paths and hashes in `archive-manifest.json`. The journal records all 56 attempted paths, verification complete and no rollback. If an in-process removal or verification fails, the helper restores missing files from their already-verified original copies, including partial directory removals; the saved journal and copies also support recovery after interruption. This is a completed recoverable removal, not a claim of atomic multi-directory filesystem publication.

| Asset group | Verified result |
| --- | --- |
| Approved remaining raw PDFs | **27 removed**, all **96,175,729 bytes** recoverable in verified originals |
| Refined directories | **26 matching + three orphan removed**, exactly **3,176 files** archived |
| Complete production-file change | Exactly **3,203 files removed**; **16,896 retained files unchanged**, no additions or changed bytes |
| Tau pilot | Exactly **156 tracked path deletions: 78 Markdown + 78 metadata**; every original remains archived; no placeholders |
| Retained official sources | All **35 root English + 34 manifest-backed GW Chinese PDFs** match their reviewed hashes |
| Retained index | All **3,404 IDs/order/metadata/text/document/vector hashes** match reviewed snapshots; **1,128 Black Library documents/vectors** retained; zero embedding calls |
| Database/canonical/official preservation | Original SQLite bytes unchanged: `af4c651da438d1d0c48c22462f1bfde0c236a2e859b81ccc7b2b61c1bdc73069`; all 18 tables, 1,721 canonical units and 1,202 Chinese names therefore unchanged |
| Black Library/cache/term/wiki preservation | Every retained production file matches the previous baseline, including all Black Library caches/history, term/pairing/entity artifacts and generated keyword/wiki assets |
| Archive preservation | All **8,305 copied files** still match their byte sizes/SHA-256 records; both manifest hashes remain unchanged |

The four raw PDFs with unverified original download provenance retain that distinction; their retirement does not establish fan authorship. The prior named Votann exclusion and historical archives are preserved. Gates and regressions reject the retired sources at their original/restored and archived entry paths, so recovering a file does not authorize its ingestion or cached-term reuse.

The same focused suite ran before and after this slice using `D:/Project/py/RAG/.venv/Scripts/python.exe` (Python 3.9.1). It covers exact policy/restored-cache rejection, terms/name/source guards, active/original/cleaned preparation states, independently sourced Tau identities, vector reuse, refinement and actual official keyword inputs/CLI generation outside cwd. Tests write temporary outputs. Before removal: **161 passed, zero skips, eight warnings, 53.40 seconds** (`before-focused.log` / `.xml`). After removal: **161 passed, zero skips, eight warnings, 47.29 seconds** (`after-focused.log` / `.xml`). XML independently confirms both totals and zero failures/errors/skips. These are focused checks, not the pending final full native suite. The warnings are existing dependency deprecations. The first test-launch attempt failed at PowerShell output redirection because the new evidence directory had not yet been created; pytest never started. Creating that directory and rerunning produced the complete before log. No application defect or asset mutation resulted from this setup failure.

After the passing suite, `verify_after_tests.py` rehashed all **16,896 retained production files** against the new active manifest, verified all **8,305 archive copies** again, reopened the index to compare all **3,404 retained document/vector snapshots**, confirmed the original database hash and checked the 156 Git deletion paths independently against the archive pilot list. Every check passed. `post-tests-verification.json` and `.log` preserve the results. The active `production-after.json` SHA-256 is **`d0a2ae5d191bc367fd93f81e05a7fb7216ae29a4ece408a6a456822df0b7d218`**. The original immutable archive manifest remains **`e4e41c2e51bc614f95b6e9502474dce59c1132153ed4451b3d015ff8d8db1c37`**. The actual report diff and representative pilot Markdown/metadata deletions were inspected; the complete deletion-path equality check confirms no other tracked source was removed. `git -c core.whitespace=cr-at-eol diff --check` passed. No formatter or application-source lint change is needed for these generated-file deletions and documentation changes.

Only the tracked Tau deletions and this report are intended for the orchestrator's automatic commit. No manual staging/commit/push/merge occurred. No server, browser, watcher, crawl or other long-running background service was started; the existing Docker services were untouched. The raw/cache step does not establish deployed behavior. Global hook knowledge repositories remain host-owned in this iteration, and the orchestrator's `notes.md` is unchanged.

## Remaining bounded retirement and host work

The next publication step must recheck the relevant term/pairing/entity inputs and approved filtered copies, then publish **125 ordered retained pairs**, **1,471 unmatched entries** and **1,596 entities** through the normal pipeline. Raw/refined retirement, all **156 tracked Tau pilot deletions**, the **3,404-document prune**, processed-key cleanup and the **982-row alias-only database** are now published. Normal official keyword and affected wiki generation remain pending. The diagnostic name-trial database remains unapproved. Use **`iteration-04/production-after.json`** for later full active-file comparisons: it records all **16,896 active files**, incorporating the single database replacement in this iteration. Its SHA-256 is **`856e69ae91cfe6b7f1174b95e33fccb33bcfedb2a774371c21e58e1bf9ff8806`**. The original 20,099-file recovery manifest and preceding active manifests remain immutable historical evidence.

After publication, run the required meaningful cached-resurrection, alias/name, keyword/temp-cwd and preservation regressions; inspect active references; regenerate affected pages through normal commands; run the **final active-asset full native suite and wiki lint**; and record exact legitimate retired-input skips. No final native/wiki result or full retained-PDF ingestion is claimed here. The retained terrain PDF's prior absence from the index/processed registry remains the preparation's documented baseline limitation.

Host integration/publication, Docker/browser acceptance, knowledge repositories and the separately staged official refresh remain outside this iteration. During the archival iteration, no application/test code, API reliability files, frontend dependencies, benchmark gold, other repositories or isolated worktrees were changed. No manual commit/push/merge, crawl, official refresh, container rebuild/restart/deployment or long-running service was started. All finite hash, copy, verification and pytest processes completed; the existing Docker services were left running. The orchestrator's `notes.md` was read and left untouched.

## Explicit post-iteration knowledge handoff

The subsequent user-invoked lifecycle hook requested the local knowledge handoff. `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` now record this archive checkpoint, verification and remaining publication/final-test work. The existing learning decision `C:/Users/Administrator/learn-notes/decisions/20260915-guarded-rules-and-derived-consumers.md` was extended and its README entry updated. The recurring GBK diagnostic was added to the existing `common/20260921-error-41-python-stdout-gbk.md`; the resolved history-container assumption is recorded separately at `C:/Users/Administrator/error-notes/rag/20261001-error-07-history-document-shape.md`, with its README entry. Existing unrelated/staged edits are preserved. No manual staging/commit/push or cross-project harness promotion occurred; the archive/report commit explanation awaits the real GNHF commit.

## October 1 index-publication knowledge handoff

The user-invoked lifecycle hook extended the existing source-retirement decision instead of adding a duplicate. `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` now record the verified 3,404-document disk index, 34 processed keys, 115 focused passes without skips, unchanged recovery/database assets and the new explicit post-publication baseline. The learning decision and its README describe candidate publication gates, advancing active manifests, historical sidecars and the runtime verification boundary.

Real archive documentation commit `816e21173` is explained at `D:/Project/devlog/wh40k-oracle/commits/20261001-816e21173-source-retirement-archive.md`; its actual diff contains only the preceding archive checkpoint report. The current index-publication report remains uncommitted, so no commit explanation for it is invented. This step resolved no new underlying error and warrants no new error note or cross-project harness promotion. Unrelated edits/staged work are preserved; no manual staging, commit, push or publication occurred.

Handoff verification preserved the prior content of five edited files, 21 unrelated dirty files byte-for-byte and six pre-existing staged statuses. The host concurrently committed separate knowledge records in all three note repositories; one unrelated error note now matches its exact committed host version (`56546b6`). An initial raw-index checksum assertion consequently failed; raw Git-index byte equality is not claimed or restored. The corrected verification checked content/staged statuses and retained the concurrent commits. `iteration-02/handoff-preservation.json` records the observed heads and exact scope. Active index, database and archive-manifest hashes remain unchanged by this handoff; all whitespace checks passed. No long-running process was started.


## October 1 raw/cache-retirement knowledge handoff

The explicit lifecycle hook updated `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` with the exact 27 raw/29 refined-directory retirement, 156 tracked pilot deletions, verified 16,896-file active baseline, paired 161-pass/zero-skip checks and remaining alias/term/wiki/full-native/runtime work. The existing source-retirement learning decision and its README entry were extended rather than duplicated. Real index-publication report commit `82e3c31af48bb4844ed89665421ea2d738a2ea30` is explained in `D:/Project/devlog/wh40k-oracle/commits/20261001-82e3c31af-reviewed-index-publication.md`; the current retirement remains uncommitted and has no invented commit explanation.

No new underlying production error was resolved, so no new error record or harness promotion was made. Existing unrelated and staged knowledge edits are preserved. This hook performs no manual staging/commit/push, asset publication or runtime action; the existing GNHF commit ownership remains in force. Preservation verification is recorded separately in `iteration-03/handoff-preservation.json` after the note updates.

The completed handoff audit verified preservation of prior content in all five existing edited files, **20 unrelated dirty files byte-for-byte** and all **six pre-existing staged statuses**. The host concurrently added separate benchmark-learning/error records and changed their two README indexes. Those additions remain intact and are explicitly attributed in the audit; no blanket assertion that every unrelated file stayed byte-identical is made. Initial preservation assertions exposed these concurrent index additions, and the corrected audit verified the exact retained content and linked host records without reverting them. Database, active index/registry and immutable archive-manifest hashes remained unchanged. All repository whitespace checks passed; no background process was started.


## October 1 approved alias-only database publication

This bounded step began at clean **`85892fa2a3bc4d9726dc26f367018a3a33dd307c`**, after the three preceding archive/index/raw-retirement slices. Its exact source-retirement scope is the previously reviewed alias-only candidate. No application/test source, preparation correction, canonical name, official rule/number, term artifact or generated wiki artifact was edited. The tracked Tau pilot deletions are already committed by the orchestrator in the preceding commit; all local recovery copies remain intact.

Evidence root: **`D:/Project/py/RAG/db_sources/release-check-20260930/retirement-apply/iteration-04/`**. `publish_alias_database.py`, `pre-publication-gates.json`, `candidate-lookup-verification.json`, `publication-journal.json`, `database-publication.json` and their logs record the exact gates and publication. The helper has a read-only gate invocation and an explicit `--apply` invocation. Both independently rehashed **all 8,305 archive copy files** and checked the entire **16,896-file post-retirement active baseline** before publication. Original database/terms, Black Library inventory and curated name-override hashes match the frozen preparation inputs. The active policy matches the approved launch/archive hash and exact 228-spelling negative catalogue; its older hash in the historical database dry run is preserved as historical evidence. The relevant policy/resolver/alias/app/fixture committed blobs still equal the approved `c68b73550` launch.

The helper reads **`database-alias-trial.sqlite` only** from the immutable archive's reviewed evidence and requires equality with the original preparation copy, approved output SHA-256 and complete cleaned row snapshot. The diagnostic **`database-name-trial.sqlite` was not applied**. Original active SQLite bytes, schema and every original table row match the archived database dry run. Exact row comparison proves that removing the 703 enumerated, individually traced retired-source alias rows produces the candidate without adding any alias or changing other rows. All 703 rows have frozen heading/file evidence entirely within the approved retired sources; aggregated `data_refined` attribution alone was not used to authorize removal.

The candidate was copied to a confined temporary sibling of `db/wh40k.sqlite`, hash-checked, and published by `os.replace` only after rechecking the original hash and absence of WAL/journal/shared-memory sidecars. The original remains independently recoverable at **`D:/Project/py/RAG/archive/source-retirement-20260930/pre-apply/db/wh40k.sqlite`**. The helper includes rollback from that verified original if replacement or validation fails. The saved journal records replacement and verification complete with **no rollback**. Read-only SQLite integrity/schema/full-row checks and actual lookups were repeated on the published file.

| Check | Verified result |
| --- | --- |
| Exact alias publication | **1,685 − 703 = 982 rows**; no new aliases |
| Retained alias sources | **961 Black Library (`blackforum`) + 19 community + two retained refined** rows, every row equal original |
| Canonical/official preservation | **17/17 other tables**, complete schema/row snapshots unchanged; **1,721 units and all 1,202 Chinese names** preserved |
| Historical identity checks | **1,206 original exact queries** checked; **989 surviving exact results unchanged**, **217 unsupported spellings unresolved**, **11 wrong-target cases blocked** |
| Distinct retained database alias spellings | **981**, exactly equal the frozen cleaned fixture; row count and lookup count are different measures |
| Community mappings | All **11** checked under the reviewed precedence/confidence rules; independently retained exact aliases win before indirection |
| Independent Tau names | `影阳指挥官` → Shadowsun `000000407`; `远见指挥官` → Farsight `000000406`, both **exact**, with unchanged source captures **365/366** and Black Library alias rows |
| Retained retrieval evidence | All **3,404 IDs/order/metadata/text/document/vector hashes** unchanged; **1,128 Black Library documents/vectors** preserved; zero embeddings |
| Production change | Exactly **`db/wh40k.sqlite`** replaced; **16,895 other active files** unchanged; no additions/removals |
| Retained official/Black Library assets | All **35 root English + 34 official Chinese PDFs**, Black Library caches and **925-pair alias history** unchanged through full file hashing |
| Recovery preservation | All **8,305 archived copy files** and both archive manifests unchanged |
| Native focused suite before apply | **146 passed, zero skips, 11 warnings, 5.24 seconds**, `before-focused.log` / `.xml` |
| Same suite on applied assets | **146 passed, zero skips, 11 warnings, 5.58 seconds**, `after-focused.log` / `.xml` |
| Normal alias rebuild on temporary copy | `populate_aliases(copy, retained_data_refined)` reports **two harvested/two matched/zero unmatched/zero collisions**; **entire rebuilt database snapshot equals the published candidate** |

Both suites use **`D:/Project/py/RAG/.venv/Scripts/python.exe` (Python 3.9.1)** and cover restored-source/cache blocking, frozen original/cleaned/active assets, exact aliases, community confidence/ambiguity, datasheet boundaries and real independently sourced Tau aliases. XML confirms zero failures/errors/skips in both runs. Tests and the rebuild write disposable copies/temporary outputs. Warnings are existing dependency deprecations. These are **focused checks**; no final full native or wiki lint result is claimed in this iteration.

After the suite, `verify_after_tests.py` rehashed the entire active baseline and all archive copies, reopened the published SQLite and all retained FAISS snapshots, and regenerated aliases on a disposable copy through the existing builder. `post-tests-verification.json` and `.log` record the complete passing result. The resulting active database SHA-256 is **`3fd7d812807517dae290dc1eb7477537b7e1a490493b3352dcc49ab6885e1e49`**. Its original recovery SHA-256 remains **`af4c651da438d1d0c48c22462f1bfde0c236a2e859b81ccc7b2b61c1bdc73069`**. The new active production manifest SHA-256 is **`856e69ae91cfe6b7f1174b95e33fccb33bcfedb2a774371c21e58e1bf9ff8806`**. The immutable archive manifest remains **`e4e41c2e51bc614f95b6e9502474dce59c1132153ed4451b3d015ff8d8db1c37`**.

Two read-only audit-helper assumptions failed before apply; both logs are retained. `pre-publication-first-failed.log` shows that the earlier resolver-comparison JSON was not among the immutable recovery copies; the helper now uses the archived **later identity-guard reconciliation**, without changing preparation evidence. `pre-publication-second-failed.log` shows an overbroad audit assertion that every app nickname must equal its redirected target. Reviewed resolver behavior instead gives independently retained exact aliases precedence (including `卡巴利特战士` and `离子爆破者`). The corrected audit requires their exact original results and frozen IDs, and requires terminal result equality for the remaining indirect mappings. Neither failure changed production or required an application/preparation fix. All 11 actual mappings and all historical identity checks passed before and after publication.

Preserving a Chinese canonical name does not certify its translation provenance: the frozen audit's **47 names without retained exact support** remain unchanged, and absence of support is not treated as proof of exclusively fan origin. Existing retained identity quality is not broadly recertified. Query coverage is the frozen 1,206-spelling universe plus the 11 app mappings and representative independently sourced Tau checks; no LLM benchmark/chat/browser acceptance is claimed.

The actual tracked diff contains this report only. The ignored finite evidence helpers compile successfully; `git -c core.whitespace=cr-at-eol diff --check` passes. The orchestrator's `notes.md`, separately owned modules/worktrees, frontend dependencies, benchmark gold, official refresh and knowledge repositories are untouched. No manual staging/commit/push/merge occurred. No server, browser, watcher, crawl or background service was started; all finite hash/test/rebuild processes completed. Existing Docker services were neither rebuilt/restarted/deployed nor used for acceptance. Host independent review/integration, knowledge handoff and later runtime acceptance remain outstanding, along with filtered terms and normal wiki generation and the final full native/wiki checks.


## October 1 alias-publication knowledge handoff

The explicit lifecycle hook updated `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` with the verified 703-row removal/982-row result, unchanged 17 other tables/1,202 names, 989 preserved exact results/217 unresolved spellings, paired 146-pass suites without skips, real alias rebuild and new active baseline. The existing source-retirement learning decision and its index were extended instead of duplicated. Real raw/cache/pilot commit `85892fa2a3bc4d9726dc26f367018a3a33dd307c` is explained at `D:/Project/devlog/wh40k-oracle/commits/20261001-85892fa2a-exact-source-retirement.md`; current alias publication remains uncommitted and has no invented commit explanation.

The two resolved audit-helper assumptions are recorded separately in `C:/Users/Administrator/error-notes/rag/20261001-error-11-archive-evidence-member-assumption.md` and `20261001-error-12-exact-alias-priority-audit.md`, with full original diagnostics, reproduction, attempts and verified resolution. Both stopped before production publication; neither is attributed to a production source defect. Existing unrelated/staged notes are preserved, no harness promotion is warranted, and no manual staging/commit/push or runtime action occurs. Preservation verification is recorded at `iteration-04/handoff-preservation.json` after these note updates.


The hook's Unicode-heavy helper additionally reproduced a direct-file Python 3.9.1 source-decoding diagnostic despite valid UTF-8 bytes/in-memory compilation. An explicit UTF-8 source cookie restored real execution. Original source/log and the narrow verified workaround are recorded in `rag/20261001-error-13-python39-source-encoding-cookie.md`; the deeper tokenizer cause is unverified and no broad harness rule is inferred. The first launch failed before any note mutation.


The completed handoff audit confirms preservation of prior content in **six existing edited files**, **23 unrelated dirty files byte-for-byte** and all **six pre-existing staged statuses** across the three knowledge repositories. Repository heads remained unchanged; database, retained index/processed registry and immutable archive-manifest hashes are unchanged. All whitespace checks passed. One actual-commit explanation and three distinct resolved diagnostic records were added; no manual staging/commit/push, harness promotion or background process occurred.
