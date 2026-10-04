# Rebuild preservation companion acceptance

## Iteration 2: attributed Black Library retrieval documents

Newly rendered Black Library documents now expose the exact accepted source ID,
English source name/source faction and canonical ID/name/faction. The private
full-copy proof emits source 2863 exactly once for GK `000000397`, with no AdM
`000000847` document. Historical Armour155/Pedro80 preservation remains
unfinished; this is a bounded companion slice, not final project acceptance.

The actual clean parent is `588fde50afaf6f042f4a654f6c6c29c96484fab6`.
Inspection of its Git diff confirms that GNHF committed the prior five-binding
implementation and report in that commit, despite its knowledge-handoff summary.
This iteration changes only `db_compile/blacklibrary.py`, the new narrow
`tests/test_blacklibrary_document_identity.py` and this report. No manual Git
staging/commit/push occurred; GNHF owns the new candidate commit.

Consumer inspection covered the real ingestion and private refresh renderer
callers, detail/card/wiki readers, current-membership and weapon-name readers,
and the source-reconcile translation guard. Accepted source attribution is
stored in the companion `blacklibrary_detail_identity` table within the same
explicit transaction as Chinese detail/name replacement. The existing detail
schema and all its readers retain their contracts. Rendering checks that the
stored canonical name/faction still match the current canonical row and that
the detail's source faction matches its attribution. Legacy nonempty projections
without attribution, missing source identities and canonical drift raise an
actionable error requiring repopulation; the renderer does not guess source IDs
from Chinese names. Its existing official-revision guard and ability projection
remain unchanged. No numerical source cell is promoted by these metadata.

Evidence is under
`D:/Project/py/RAG/db_sources/rebuild-preservation-owned/20261004/iteration-02/`.
`source-freeze.json` pins exact committed parent bytes and separately frozen
final candidate bytes. `paired_render.py` runs them in independent processes;
each starts from its own AFB copy, performs the real full CSV build without
terms, restores normal offline authority layers with an empty private inventory
and the real retained details, then repeats the complete build/restoration.
Both produce identical outputs across their repeated builds. Parent and
candidate render **1,125 documents** with exact matching text and every prior
metadata value; the candidate adds exactly six identity metadata fields. Its
new companion table records **1,142 accepted projections**. All five reviewed
sources emit once with their exact canonical targets. The four existing
wrong-response targets remain absent.

All **19 original tables** are identical by key/content. Eighteen are also
identical in row order. The unchanged 87-row keyword glossary uses process-local
insertion order: one initial comparison of its rowid sequence failed, while
the subsequent exact `ORDER BY term_en` comparison confirms all 87 rows and
values are unchanged. The original diagnostic failure is retained in
`verification.log`; the final keyed comparison is in `verification-final.log`
and `verification.json`. No glossary generator or unrelated consumer was edited.
All **3,635 official ledger rows** and price/numerical/body/alias/archive values
remain exact between parent and candidate. Historical Armour/Pedro still expose
mirror140/90 after rebuild, with `current:false`; that outstanding failure is
retained in the final verification price anchors rather than claimed repaired.

The **115 frozen forensic inputs** remain hash-identical, including active
`index.pkl` and `index.faiss`, source/raw inputs, policies and retained source
manifests. Thus this slice makes no change to any active UUID/text/metadata/vector.
It does not assign either legacy Servitor UUID to AdM or publish a replacement
index. This is the recorded input-set preservation proof, not a new full recovery
inventory audit. The real strict inventory-policy replay remains **32 accepted /
62 reopened** of 94. No active database, cache, wiki, PDF, manifest or service was
written and no model was loaded, dependency installed or network request made.

| Final XML-confirmed selection | Collected | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|---:|
| Frozen parent, new document cases | 10 | 0 | 10 | 0 | 0 |
| Final candidate, new document cases | 10 | 10 | 0 | 0 | 0 |
| Frozen parent, relevant existing controls | 602 | 552 | 0 | 0 | 50 |
| Final candidate, same existing controls | 602 | 552 | 0 | 0 | 50 |

Every existing node status and skip reason matches exactly in `verification.json`.
The 50 skips are the previous 46 missing retirement-preparation asset/inventory
checks plus four pre-existing real-cache Chinese-coverage checks unavailable in
this checkout. There are **zero new skips**. The selection includes all 89
five-binding regressions, native builder lifecycle/Windows handle and real CLI
restoration controls, identity/quarantine/listing policies, source reconciliation,
official dates/revision chains, MFM/price/history/archive, aliases and retirement
controls. The ten new cases cover exact source rendering, name/faction drift,
legacy repopulation, invalid/missing source IDs, transactional identity/schema
rollback, repeated/empty behavior and actual Windows renames. An earlier focused
selection passed 101 cases before the final four new cases were added; its XML
is retained and is not the final count.

Python 3.11 compilation, Python 3.9 grammar parsing and `git diff --check` pass.
Ruff/Black remain unavailable and were not installed. Initial full-copy trials
stopped at the existing Windows GBK console encoding of a success glyph; their
logs remain intact. UTF-8 output reruns used fresh independent source copies
and completed successfully. This was a harness-output correction, not an
application/source-policy change. All finite test/rebuild children exited; no
persistent background process was started.

Remaining gates are eligible dated historical-price preservation, final combined
copied acceptance, GNHF's scoped candidate commit/clean-tree check and independent
host review. Scheduled stage-only implementation remains a separate run. The
old duplicate vector attribution remains unresolved. Root owns shared knowledge
indexes and publication; existing local checkpoint/roadmap/learning/error records
are extended in place with these verified results.

## Iteration 1: five source-bound Chinese identities

The five reviewed Black Library Chinese identities now survive a clean copied CSV rebuild and normal offline authority restoration without term pairs, inventory Chinese names or previous `units.name_zh`. Source 2863 remains available for Grey Knights `000000397` and cannot project into Adeptus Mechanicus `000000847`. This is one verified implementation slice, not final project acceptance. Historical-price preservation and new retrieval-document metadata remain unfinished.

Starting clean commit: `1c726e65a1c0e276c39b7584417a1e74f96e9c3e`, branch `codex/release-rebuild-preservation`. Only the Black Library identity/matching modules, a small binding file, narrow tests/real-source fixture and this new report are intended tracked changes. GNHF owns commits; no manual staging, commit, push or service operation occurred. Independent host review remains pending.

## Evidence and implementation boundary

Read-only forensic inputs are the October 4 automatic-update investigation under `D:/Project/py/RAG/db_sources/release-check-20260930/host/automatic-update-paths-20261004/`. Its lineage JSON SHA-256 is `f57f8c7f9bbba189cd1d82f69ec89d34c81145781a96266e492ae86bad109b87`. The five binding entries and real-source test records were extracted from that lineage and the retained cache, verifying every exact cached-record fingerprint and raw-capture hash. No English spelling, capture identity or hash was invented.

| Source ID | Exact canonical identity | Canonical faction |
|---|---|---|
| 9 | `000000121`, Uriel Ventris | SM / Ultramarines |
| 2863 | `000000397`, Servitors | GK / Grey Knights |
| 363 | `000000562`, Sentry Pylon | NEC / Necrons |
| 1085 | `000003836`, Death Company Marines with Boltguns | SM / Blood Angels |
| 678 | `000003916`, Ynnari Kabalite Warriors | AE / Ynnari |

The matcher checks exact source English name, faction, complete provenance and canonical-JSON record SHA-256, then exact canonical ID/name/faction/keyword JSON. The cached fingerprint binds the previously verified raw content and capture provenance; runtime matching does not reread or recertify raw endpoint files. Changed captures require review. Unknown or drifted records cannot evade these checks through the old Chinese-name fallback or English-family matching. Empty Chinese names are filled only for accepted bindings; existing separately supplied names are preserved. All writes remain in the existing projection transaction.

These bindings authorize community Chinese names/text only. They do not change official model/weapon cells, English bodies, current membership or price authority. The retained source GK base size remains distinct from the canonical base size. Existing four wrong-response quarantines, listing fingerprints, source-reconcile/source-coverage guards, price selectors, aliases and retirement policy were not edited.

## Paired reproduction and preservation

All new evidence, database copies, temporary files and test caches are under `D:/Project/py/RAG/db_sources/rebuild-preservation-owned/20261004/iteration-01/`. The stable existing executable is `D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`; no packages were installed and no network/provider call occurred.

`source-freeze.json` / `source-freeze-final.json` record exact Git-parent module bytes and separately frozen candidate hashes. `paired_runner.py` / `paired_runner_final.py` load those modules in separate processes while holding all other source constant. Each actual trial starts from its own copy of the frozen AFB database, uses the real full CSV builder and unmodified `restore_authority_layers`, and repeats the build/restoration. Terms are absent and the private list is deliberately empty to eliminate the mutable name bridge. This stringent fixture is not an active-production language-coverage acceptance run.

The parent produces zero of the five target projections; the candidate produces exactly five and no AdM reuse. Both repeated candidate builds are table-identical. Parent/candidate Chinese detail totals are 1,137/1,142 under these deliberately restricted inputs. Every one of the parent's 1,137 retained detail rows is exact. All four quarantined canonical targets remain absent.

`language-only-preservation.json` proves the actual population seam changes only five `units.name_zh` cells and adds the five detail rows; every other table and every official numerical/body column is exact. `actual-preservation.json` separately accounts for normal downstream generation: five unit-name changes, five added details, 36 weapon-name changes and changed values in the 87-row Chinese keyword glossary. Only language outputs differ. The first diagnostic comparison used the wrong glossary table spelling; that failed diagnostic is retained in the tool transcript, and the corrected script/log names the actual `zh_keyword_glossary` table. It was not a failed application implementation.

All 3,635 official ledger records match the complete October snapshot in both copied trials, including conditional/equipment/occurrence rows and provenance. The current ledger's ordinary Calgar 180, Guilliman 415, Kaius 100 and Helbrute source anchors remain independent. The separate deleted-source archive is restored by the unchanged archive stage. This slice does **not** repair historical Armour 155/Pedro 80: copied rebuilds still show mirror 140/90 with `current:false`; `anchor-prices.json` preserves that outstanding failure visibly.

The 115 forensic input files match their original investigation hashes before and after these checks, including retained cache/raw snapshots, policies and active index evidence. No production database, wiki, PDF, vector, source cache, recovery copy or manifest was written. This is preservation of the recorded input set, not a new full 8,305-recovery-copy or full-project asset audit. The strict listing replay still accepts 32 of 94 records and reopens the other 62; no fingerprint relaxation occurred.

## Validation

| XML-confirmed run | Collected | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|---:|
| Frozen parent, final new regression suite | 89 | 6 | 83 | 0 | 0 |
| Frozen parent, existing relevant controls | 502 | 456 | 0 | 0 | 46 |
| Final candidate, both selections | 591 | 545 | 0 | 0 | 46 |

`verification.json` contains every XML node ID/status/skip reason and verifies that all 502 existing parent results are identical in the candidate. Thus all 89 new cases pass without skips and no pre-existing check regresses. The 46 unchanged skips concern unavailable active/original/cleaned retirement-preparation assets and the missing pre-retirement inventory in this isolated checkout. They are not replaced with guessed evidence. The selected controls include native builder lifecycle/real Windows handles, real build CLI restoration, source reconciliation, official revision/date guards, price/source-only identities, archive history, alias/weapon history and retirement policies. This is not a full native or native583 rerun claim.

Tests cover repeated clean rebuilds, exact five restorations, source/canonical/name/faction/keyword and individual provenance-field drift, shared-name AdM denial, projection rollback, empty-input behavior, input immutability and successful Windows rename after normal/error exits. Earlier 108-test focused and 64-case paired runs remain retained. Python 3.11 compilation, Python 3.9 grammar parsing and `git diff --check` pass. Ruff and Black are unavailable in the unchanged environment; neither was installed. All finite child processes exited and no background service was started.

## Next bounded work

Preserve eligible reviewed historical official prices/provenance before skeleton replacement, validate them against the actual dated retained September 14 source, and let new current prices take precedence. Then attach exact source/canonical/faction identities to newly generated Black Library documents and prove copied rendering emits the legitimate GK source once. Existing Servitor UUID attribution remains unresolved: neither active UUID was assigned to AdM, deleted or retagged. Scheduled stage-only implementation remains a separate run. Full copied objective acceptance, scoped GNHF commits/clean-tree verification, independent host review and publication remain pending.

Duplicate-checked local learning/error handoff records accompany this slice; shared repository indexes and commit explanations remain for root publication after the actual GNHF commit exists. No commit ID for this uncommitted candidate is invented.
