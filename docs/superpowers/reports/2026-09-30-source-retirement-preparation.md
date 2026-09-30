# Approved Chinese source retirement preparation

Status: **partial preparation, iteration 1**. The approved exact-source policy and cached term gates are implemented and locally tested. Official keyword classification, copied index/database reconciliation and the final native suite remain outstanding. This report is evidence for review, not release acceptance. No production assets were published or retired.

## Scope and baseline

Work started on `codex/review-answer-provenance` at clean HEAD `0abbdf96c16ce0355b3bccb821919ec19fbbb424`. The interpreter was verified as Python **3.9.1** at `D:/Project/py/RAG/.venv/Scripts/python.exe`; new annotated application code uses future annotations. The resumed objective supersedes the historical save-and-stop checkpoint. This worker does not commit, push, merge, deploy or manage the existing containers. Independent review and publishing belong to the host.

The frozen inventory is `D:/Project/py/RAG/db_sources/release-check-20260930/fan-source-inventory.json`. It approves 27 remaining translated/unverified Chinese PDFs, three orphan fan caches and retention of the existing Votann retirement. The two June points/balance files, Imperial Agents Chinese and Grey Knights Chinese have official-style layouts without verified original download provenance. Their exclusion does **not** assert proven fan authorship. All 35 retained root English and 34 manifest-backed official Chinese input paths passed the source-policy retention regression. Black Library remains eligible.

## Implemented policy and consumers

`corpus_policy.json` now records 31 exact raw/refined stems and 31 exact metadata book labels. These include the prior Votann source, the 27 approved inputs and the three orphan caches. The labels were derived from the existing `ingest.get_book_name` implementation, then checked against every recorded retiring index book. No substring match or guessed version-family exclusion was added.

`is_excluded_source` continues to match exact path components/raw PDF stems. The separate `is_excluded_book` API additionally matches whole metadata labels. Short labels such as `千子军团` are consequently excluded when they identify a retired book, while official paths, canonical unit names and IDs are not treated as metadata exclusions. Synthetic retention tests include similarly named official paths and distinct stems. Policy loading validates both exclusion lists and still fails on missing/malformed policy.

The shared metadata gate is applied before cached pairs enter `wiki_compile.terms.load_term_aliases` or `db_compile.entity_resolver._load_term_pairs`. Term generation filters both paired and unmatched entries without mutating its input. Restored `entities.json` entries are filtered before pairing/faction votes. Existing database-name restoration and wiki synthesis guards now use the metadata-aware API. Existing PDF ingestion, refinement, refined chunk loading, alias harvesting and entity extraction path guards remain in place.

No database aliases were deleted based on their aggregated `data_refined` attribution. The synthetic collision regression proves that an excluded cached pair cannot override a surviving Black Library alias. The actual database tests independently verify the Black Library source rows for Shadowsun and Farsight and their continued exact resolution through the canonical database. Legacy terms-only resolver expectations were updated to require rejection of the retired Tau Chinese pilot and preservation of the official English Tiger Shark pair.

## Tests and evidence

All local evidence is under `D:/Project/py/RAG/db_sources/release-check-20260930/retirement-preparation/iteration-01/`.

| Check | Result | Evidence |
| --- | --- | --- |
| New initial regressions against unmodified application baseline | 39 failed, 1 passed; restored sources and cached pairs bypassed retirement | `baseline-red.log` |
| First implementation focused check | 165 passed, 3 failed; one test inventory-key typo and two legacy retired-pilot expectations were corrected | `focused-first.log` |
| Final policy/terms/resolver/pair/build/aliases/synthesis focused check | **189 passed**, no skips; 9 dependency/source deprecation warnings | `focused-final.log` |
| Existing ingestion/vector reuse/refined chunk/refinement/extraction/keyword check | **77 passed**, no skips; 8 deprecation warnings | `existing-guards-and-keywords.log` |
| Changed Python syntax compilation | Passed without writing compilation artifacts | Checked directly with the project interpreter |
| `git -c core.whitespace=cr-at-eol diff --check` | Passed | Checked after implementation and documentation |
| Production file preservation | **20,099 before = 20,099 after**, zero changed/added/removed files | `production-before.json`, `production-after.json`, `production-preservation.json` |

The two passing groups comprise 266 distinct focused tests. A new full native suite has **not** been run in this iteration; the earlier 2,814-pass checkpoint is historical evidence only. Ruff is unavailable in the project environment (`No module named ruff`), and no replacement tool/interpreter was installed. The actual diff was inspected, including removal of incidental line-ending churn. Independent host review remains pending.

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

1. Replace `wiki_engine/keyword_index.py`'s direct quick-reference PDF dependency with deterministic extraction from the retained official Core Rules. Reuse the direct-PDF numbered-section parser, preserve official glossary names and exercise actual parameterized families/transitional PISTOL text. Reject retired explicit keyword inputs and replace omission-based legacy expectations with official-source coverage tests. The current quick-reference code remains unchanged and still reads the active retiring PDF; the passing existing keyword tests do not validate a replacement.
2. Stage copied vector index/database artifacts under `D:/Project/py/RAG/db_sources/release-check-20260930/retirement-preparation/`. Dry-run exact inventory attribution: expected 5,905 documents minus 2,501 retiring documents = 3,404 retained, including all 1,128 Black Library documents. Verify exact retained document/vector hashes and incremental processed-key cleanup. These counts remain projected from the inventory, not reconciled by this iteration.
3. On a database copy, compare the filtered alias/name rebuild before deciding any removal. Reconcile the 705 `data_refined`, 961 `blackforum` and 19 `community` aliases with independently sourced rows; preserve canonical/official rows with full row snapshots. Aggregated attribution alone is insufficient. No copied database trial was run here.
4. Run the final full native suite after the complete preparation changes, inspect the final diff and rerun production-preservation checks. Incorporate independent host release/source review and complete this report with exact copied-index/database results. Do not mark the loop stop condition met before these steps pass.

## Later asset apply, owned by the host

After independent review, back up the approved exact PDFs/refined caches, active index/database and generated terms. Move only the 27 approved raw inputs, 26 matching refined directories and three orphan caches into the approved excluded archive; maintain Votann's prior exclusion. Remove the tracked Tau pilot from publishing. Apply the reviewed exact index prune and processed-key cleanup, publish only the reviewed copied alias/name changes, replace cached term artifacts from verified filtered outputs and regenerate affected wiki artifacts through their normal commands. Reconcile retained document/vector/official/canonical snapshots again before deployment and application acceptance.

Official freshness/MFM staging is a separate unapplied task. The four wrong-identity Black Library responses, source completeness gaps and missing provenance in older artifacts remain limitations. Exact policy gates intentionally do not infer source provenance for missing or unfamiliar book labels. No absolute correctness or release readiness is claimed.
