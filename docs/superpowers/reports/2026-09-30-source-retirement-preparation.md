# Approved Chinese source retirement preparation

Status: **partial preparation, iteration 3**. The approved exact-source policy, cached term gates and official keyword classifier are implemented and locally tested. Copied vector-index and cached-term reconciliation are complete; copied database alias/name reconciliation and the final native suite remain outstanding. This report is evidence for review, not release acceptance. No production assets were published or retired.

## Scope and baseline

Work started on `codex/review-answer-provenance` at clean HEAD `0abbdf96c16ce0355b3bccb821919ec19fbbb424`. The interpreter was verified as Python **3.9.1** at `D:/Project/py/RAG/.venv/Scripts/python.exe`; new annotated application code uses future annotations. The resumed objective supersedes the historical save-and-stop checkpoint. This worker does not commit, push, merge, deploy or manage the existing containers. Independent review and publishing belong to the host.

The frozen inventory is `D:/Project/py/RAG/db_sources/release-check-20260930/fan-source-inventory.json`. It approves 27 remaining translated/unverified Chinese PDFs, three orphan fan caches and retention of the existing Votann retirement. The two June points/balance files, Imperial Agents Chinese and Grey Knights Chinese have official-style layouts without verified original download provenance. Their exclusion does **not** assert proven fan authorship. All 35 retained root English and 34 manifest-backed official Chinese input paths passed the source-policy retention regression. Black Library remains eligible.

## Implemented policy and consumers

`corpus_policy.json` now records 31 exact raw/refined stems and 31 exact metadata book labels. These include the prior Votann source, the 27 approved inputs and the three orphan caches. The labels were derived from the existing `ingest.get_book_name` implementation, then checked against every recorded retiring index book. No substring match or guessed version-family exclusion was added.

`is_excluded_source` continues to match exact path components/raw PDF stems. The separate `is_excluded_book` API additionally matches whole metadata labels. Short labels such as `千子军团` are consequently excluded when they identify a retired book, while official paths, canonical unit names and IDs are not treated as metadata exclusions. Synthetic retention tests include similarly named official paths and distinct stems. Policy loading validates both exclusion lists and still fails on missing/malformed policy.

The shared metadata gate is applied before cached pairs enter `wiki_compile.terms.load_term_aliases` or `db_compile.entity_resolver._load_term_pairs`. Term generation filters both paired and unmatched entries without mutating its input. Restored `entities.json` entries are filtered before pairing/faction votes. Existing database-name restoration and wiki synthesis guards now use the metadata-aware API. Existing PDF ingestion, refinement, refined chunk loading, alias harvesting and entity extraction path guards remain in place.

No database aliases were deleted based on their aggregated `data_refined` attribution. The synthetic collision regression proves that an excluded cached pair cannot override a surviving Black Library alias. The actual database tests independently verify the Black Library source rows for Shadowsun and Farsight and their continued exact resolution through the canonical database. Legacy terms-only resolver expectations were updated to require rejection of the retired Tau Chinese pilot and preservation of the official English Tiger Shark pair.

## Tests and evidence

Iteration 1 evidence is under `D:/Project/py/RAG/db_sources/release-check-20260930/retirement-preparation/iteration-01/`.

| Check | Result | Evidence |
| --- | --- | --- |
| New initial regressions against unmodified application baseline | 39 failed, 1 passed; restored sources and cached pairs bypassed retirement | `baseline-red.log` |
| First implementation focused check | 165 passed, 3 failed; one test inventory-key typo and two legacy retired-pilot expectations were corrected | `focused-first.log` |
| Final policy/terms/resolver/pair/build/aliases/synthesis focused check | **189 passed**, no skips; 9 dependency/source deprecation warnings | `focused-final.log` |
| Existing ingestion/vector reuse/refined chunk/refinement/extraction/keyword check | **77 passed**, no skips; 8 deprecation warnings | `existing-guards-and-keywords.log` |
| Changed Python syntax compilation | Passed without writing compilation artifacts | Checked directly with the project interpreter |
| `git -c core.whitespace=cr-at-eol diff --check` | Passed | Checked after implementation and documentation |
| Production file preservation | **20,099 before = 20,099 after**, zero changed/added/removed files | `production-before.json`, `production-after.json`, `production-preservation.json` |

The two iteration-1 passing groups comprise 266 distinct focused tests. A new full native suite has **not** been run in either preparation iteration; the earlier 2,814-pass checkpoint is historical evidence only. Ruff is unavailable in the project environment (`No module named ruff`), and no replacement tool/interpreter was installed. The actual diff was inspected, including removal of incidental line-ending churn. Independent host review remains pending.

The preservation manifests hash every file under `data`, `data_refined`, `db`, `local_vector_store`, `wiki`, `wiki_build` and `db_sources/blacklibrary`. Tests and staging wrote to temporary/ignored preparation paths. Active PDFs, refined caches, database, vector index, generated wiki/terms and Black Library caches are byte-identical to the pre-test snapshot. No official assets were refreshed and no server/browser/watcher was started. The short-lived hash/test commands all completed.

## Copied term artifact reconciliation

Original copies, filtered copies and terms generated through `write_terms` are staged under the evidence directory's `terms/`. `terms-reconciliation.json` enumerates every removed row, the retained ordered-row SHA-256 snapshots, source/output file hashes and all tracked pilot paths. Generation was verified against the exact retained input pairs; the active artifacts remain unchanged.

| Artifact/group | Before | Excluded rows | Retained rows |
| --- | ---: | ---: | ---: |
| `wiki/terms.json` pairs | 187 | 62 | 125 |
| `wiki_build/pairing.json` pairs | 187 | 62 | 125 |
| `wiki_build/pairing.json` unmatched | 1,516 | 45 | 1,471 |
| `wiki_build/entities.json` entities | 1,703 | 107 | 1,596 |

All excluded rows above have the exact retiring Tau pilot attribution. The 125 retained term pairs are unchanged records in their original order. This establishes copied cached-term reconciliation only; it does not establish the provenance or removability of every database alias/name.

There are **156 tracked files**, including **78 Markdown pages**, under `data_refined/钛帝国十版CODEX-20251112/`. They must be removed from future publishing in the later reviewed asset-apply stage. Their exact Git paths are recorded in `terms-reconciliation.json`; no tracked pilot file was removed here.

## Remaining bounded preparation

1. Copied vector-index reconciliation is completed in iteration 3 below. Keep the verified staged artifacts unpublished until the database trial, final suite and host review pass. Do not substitute the active index or infer database-alias provenance from document removals.
2. On a database copy, compare the filtered alias/name rebuild before deciding any removal. Reconcile the 705 `data_refined`, 961 `blackforum` and 19 `community` aliases with independently sourced rows; preserve canonical/official rows with full row snapshots. Aggregated attribution alone is insufficient. No copied database trial was run here.
3. Run the final full native suite after the complete preparation changes, inspect the final diff and rerun production-preservation checks. Incorporate independent host release/source review and complete this report with exact copied-index/database results. Do not mark the loop stop condition met before these steps pass.

## Iteration 2 official keyword classifier

`wiki_engine/keyword_index.py` now reads the retained English Core Rules (`data/Core Rules - New 40K Core Rules.pdf`) and official Chinese Core Rules (`data/官方中文/chi_01-06_warhammer40k_new40k_core_rules-gihrxgzhgo-iickazpeog.pdf`). It uses the existing `pdf_sections.split_sections` parser directly, pairs exact official section numbers and normalizes typographic hyphens in headings. No LLM cache or retiring quick-reference text is used. Both inputs pass the shared source-policy guard before file access.

Both official PDFs contain 38 chapter-24 sections. Sections 24.01 (ABILITIES), 24.02 (DUPLICATED ABILITIES) and 24.32 (SCOUT MOVE) are structural explanations/procedures rather than separate named datasheet abilities. The remaining **35 named abilities** come from their actual headings. The bounded completeness check requires the retained snapshot's 24.01–24.38 section set in both languages; future section additions/deletions require source review and fail visibly. A synthetic unfamiliar heading proves that identities are not a guessed keyword whitelist. Numbered cross-reference prefixes are stripped from the combined LEADER 24.22 / SUPPORT heading, including the Chinese parser's preceding app-footer fragment, without guessing the target name.

Actual headings supply LEADER 24.22, PISTOL 24.27 and SUSTAINED HITS 24.36, which were omitted or unnumbered in the retiring table. PISTOL is transitional only when its official English body/asides state both equivalence with CLOSE-QUARTERS and replacement by it. The classifier does not assign that status when the source entry or either statement is absent. Core Rules 24.01 explicitly permits conditional keyword suffixes on weapon abilities; family lookup now handles these generically, including the source's SUSTAINED HITS 1: INFANTRY/BEASTS example. Existing target identities and weapon statistics remain separate. Parameterized ANTI, CLEAVE and RAPID FIRE regressions retain their official section identities.

The public `parse_quickref`, `QuickRefEntry` and report `quickref_entries` names remain compatibility shims; `core_rules_entries` reports the new source count explicitly. The JSON field set stays compatible. `nameZh` still comes from the existing official glossary; the old `quickrefZh` field is now null because its frontend label describes a retiring secondary translation. Generated Markdown no longer publishes the fan-table translation-difference section. The legacy API null-section fallback is tested with an explicit temporary legacy payload, while a newly generated temporary payload verifies PISTOL's actual 24.27 section and API rule link.

Evidence is under `D:/Project/py/RAG/db_sources/release-check-20260930/retirement-preparation/iteration-02/`:

| Check | Result | Evidence |
| --- | --- | --- |
| Initial new regressions on preceding implementation | **16 failed** as expected | `baseline-red.log` |
| Initial keyword/parser/API focused suite | **91 passed**, no skips | `focused-first.log` |
| Expanded final policy/terms/resolver/keyword/parser/API suite | **204 passed**, no skips, 9 deprecation warnings, 23.21 seconds | `focused-final.log` |
| Mistyped focused-test invocation | No tests ran; corrected paths were used for the passing suite | `focused-invocation-error.log` |
| Actual official section text, titles, physical pages and source hashes | 38 sections in each language; 35 named pairs | `official-keyword-evidence.json` |
| Staged generation and comparison to active keyword payload | 50 identities and all statistics/display names/groupings/links preserved; two official section numbers supplied; 36 secondary alias values cleared | `keyword-reconciliation.json`, `keywords/indexes/keywords.{md,json}` |
| Production preservation against the original preparation baseline | **20,099 before = 20,099 after**, zero changed/added/removed files | `production-after.json`, `production-preservation.json`; baseline `../iteration-01/production-before.json` |
| Changed Python syntax compilation and whitespace validation | Passed; compilation did not write artifacts | Direct `compile` checks and `git -c core.whitespace=cr-at-eol diff --check` |

The staged payload changes only `section` (PISTOL null → 24.27, SUSTAINED HITS null → 24.36) and the retired `quickrefZh` aliases. The 50-item distribution remains 36 universal, one transitional and 13 unit-specific. Every other payload field, including reverse lookup records, is equal to the active baseline. Normal generation wrote only to the ignored preparation directory. Active keyword artifacts still contain the historical table-derived payload until the reviewed apply stage regenerates them.

No final full native suite is claimed by this slice. No formatter was installed; Ruff's absence was established in iteration 1. Independent host code/source review is still pending. No external retrieval, commits, deployment or container changes occurred, and no long-running process was started. All test/hash commands completed. The original production manifest and the final snapshot cover `data`, `data_refined`, `db`, `local_vector_store`, `wiki`, `wiki_build` and `db_sources/blacklibrary`.

## Iteration 3 copied vector-index reconciliation

This slice changes no application or test source. It produces a complete exact-source dry run and a reload-verified prune on copied assets under `D:/Project/py/RAG/db_sources/release-check-20260930/retirement-preparation/iteration-03/`. The saved `audit_index.py` is an ignored, bounded evidence helper with no production-write mode. It requires fresh output directories, checks the frozen inventory and all 27 raw-PDF hashes, and writes the dry-run evidence before copying or pruning. It uses the existing FAISS delete/save/load APIs with an embedding implementation that raises on any embedding call; no model, network retrieval or substitute vectors are involved.

`index-dry-run.json` records all 5,905 original document IDs and positions, complete metadata, document/content hashes and exact float32-vector byte hashes, partitioned into removed and retained lists. Each approved PDF's observed removal count equals its independently saved inventory count. Inventory attribution and the shared source/book policy agree for every indexed document; no extra policy-only removal was accepted. The earlier Votann and three orphan caches have no active indexed documents to remove. This verifies index attribution only, not whether every retained document is factually correct.

The original index and all sidecars are copied unchanged to `index-original/`. `index-pruned/` contains the trial result. Saving and reopening that result verifies every retained ID, serialized document, content hash, metadata record, relative order and vector-byte hash; all removed IDs are absent. The post-prune FAISS count, contiguous index mapping and docstore size agree. Exact processed-key filtering preserves every retained key/value and removes only approved PDF entries.

| Check | Result | Evidence |
| --- | --- | --- |
| Exact inventory/policy dry run | **5,905 before − 2,501 removed = 3,404 retained**, all 27 per-PDF counts match | `index-dry-run.json` |
| Copied save/reload preservation | **3,404/3,404 retained documents, IDs, order and vectors unchanged** | `index-reconciliation.json`, `index-trial.log` |
| Black Library preservation | **1,128/1,128 retained**; remaining 2,276 documents are retained English inputs | Retained snapshots in `index-dry-run.json` |
| Copied processed registry | **61 before − 27 removed = 34 retained**; every retained key/value unchanged | Removed and retained mappings in `index-dry-run.json` |
| Policy/restored-cache, ingestion/pruning, vector reuse and Black Library index guards | **96 passed**, zero skips, eight dependency deprecation warnings, 13.12 seconds | `focused.log` |
| Production preservation against the original iteration-1 baseline | **20,099 before = 20,099 after**, zero changed/added/removed files | `production-after.json`, `production-preservation.json` |
| Actual tracked diff and whitespace check | Report update only; passed | `git -c core.whitespace=cr-at-eol diff --check` |

The retained ordered document/vector snapshot SHA-256 is `12461cd08ab6f8d827013018c3b785539f6c2ba56ef64e35e30f21270534d094`. Staged `index.faiss` SHA-256 is `1a62affa4fc1be566702ee964c965b3c88f3eac98f6c692555a5148e0c04fd38`; staged `index.pkl` is `bda0a66bc301cf5f2118f30f5f66fe4f60adc662132a085d2ef700392b5156ab`. The complete input/output and registry hashes are in `index-reconciliation.json`. The script's Pydantic `dict()` use emits one deprecation warning; it does not affect the exact before/after comparison.

Two limits matter for later apply. First, the frozen inventory has 35 retained root English PDFs, but the baseline processed registry and index include only 34: `data/Misc - Terrain Area Footprints.pdf` has neither a processed entry nor indexed documents. This slice preserves that baseline absence and does not claim full retained-PDF ingestion. Second, the copied `blacklibrary-refresh.json` is unchanged historical evidence describing the earlier 5,905-document refresh; it is not a report of the 3,404-document prune. Use `index-reconciliation.json` as the authoritative trial report and keep that distinction visible during publication.

The complete production-file comparison covers the same seven roots as iterations 1–2. Active raw/refined inputs, index, SQLite, wiki/terms and Black Library caches remain byte-identical. The copied database alias/name trial and final native suite remain outstanding; no retrieval/browser acceptance or independent host review is claimed. No server, browser, watcher or container process was started or stopped. All short-lived audit, test and hash commands completed.

## Later asset apply, owned by the host

After independent review, back up the approved exact PDFs/refined caches, active index/database and generated terms. Move only the 27 approved raw inputs, 26 matching refined directories and three orphan caches into the approved excluded archive; maintain Votann's prior exclusion. Remove the tracked Tau pilot from publishing. Apply the reviewed exact index prune and processed-key cleanup, publish only the reviewed copied alias/name changes, replace cached term artifacts from verified filtered outputs and regenerate affected wiki artifacts through their normal commands. Reconcile retained document/vector/official/canonical snapshots again before deployment and application acceptance.

Official freshness/MFM staging is a separate unapplied task. The four wrong-identity Black Library responses, source completeness gaps and missing provenance in older artifacts remain limitations. Exact policy gates intentionally do not infer source provenance for missing or unfamiliar book labels. No absolute correctness or release readiness is claimed.
