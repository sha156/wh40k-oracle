# Rebuild preservation companion acceptance

## Iteration 3: reviewed historical official price preservation

Armour of Antilochus **155** and Pedro Kantor **80** now survive the actual
full copied CSV rebuild and normal offline authority restoration, independently
of current price membership. Both remain `current:false`, with their exact
September 14 capture provenance and retained official source rows. This is a
bounded companion implementation result, not final project or production acceptance.

Actual clean parent: `db494903696fe301da34d309010de92ba0562939`. Its Git diff
confirms that GNHF committed iteration 2's document-attribution implementation,
tests and report, despite the generic knowledge-handoff subject. This iteration
owns only the narrow build/update seam, new `mfm_history.py` and reviewed binding
data, `test_mfm_rebuild_history.py`, and this report. No manual Git staging,
commit, push or publication occurred. The candidate remains uncommitted for GNHF;
independent host review is pending.

### Verified source and restoration boundary

The binding data were extracted from the verified old `3fd7d812...` database's
two exact canonical rows/official ledger entries and the AFB database's exact
mirror price fields. Only these fields were read from the old database; the
old database was never restored wholesale. `binding-extraction.json` records
the complete database paths/hashes and output binding hash.

| Canonical ID | Exact canonical name | Mirror from-price | Retained historical price | Source ordinal |
|---|---|---:|---:|---:|
| `000002713` | Pedro Kantor | 90 | 80 | 244 |
| `000004183` | Marneus Calgar in Armour of Antilochus | 140 | 155 | 255 |

Both bind SM plus their exact canonical keyword JSON and datasheet
name/faction/source-ID/link. Actual retained source:
`db_sources/mfm/snapshots/2026-09-14/space-marines.html`, SHA-256
`99f45a5032c4862df89529f02a66122897429ccea7280b0fb318335cf23ad884`;
the exact manifest SHA-256 is
`29062f70c0b6848c0ea321b9be816df25cedec4242e81a4331ea09634c06939b`.
Source URL is `https://mfm.warhammer-community.com/en/space-marines`;
capture timestamp is `2026-09-14T05:51:23.572407+00:00`.
This timestamp remains a capture date. No effective date or Legends status is
inferred from the capture or later absence of headings.

The builder validates retained raw bytes/manifest, parses the complete page
through the existing lossless parser, and checks both exact official ledger rows
and prior price tiers. It checks the new skeleton's exact identity and CSV
price from-fields, then the previous target identity, price/provenance and
any retained ledger rows. Only the verified narrow batch is written in the
existing builder transaction before atomic replacement. The original
price/items/tiers/capture fields are retained; `source_sha256` and
`historical_source_rows` add the exact historical raw/row provenance. No table,
Chinese name, alias, numerical body, source-coverage declaration or current ledger
is copied from the older database.

The exact AFB mirror/check-only blocks and a genuinely clean missing prior row
can recover from these reviewed source bindings; changed prior price/history
fails closed. Available evidence drift aborts replacement and preserves the old
database. Missing raw evidence grants no historical authority and is reported
by the build result/update warning. The retained snapshot can be supplied through
the new optional `historical_mfm_snapshot` builder/config field; the default is
the existing relative September 14 snapshot directory. A later current block
requires matching independently retained current ledger tiers/date/source before
the helper defers restoration to the normal current MFM stage. An advanced
timestamp alone cannot evade the historical source guard. New current publication
wins; the existing MFM application/reconciliation policy was not changed.

Consumer inspection included the builder CLI/update callers, MFM application,
current membership, datasheet historical notes, agent source projection, roster
prices, catalogue/card readers, wiki price readers and source-coverage price
checks. Existing `current:false` handling keeps these two histories out of
current picker/roster pricing. No public grammar, consumer, numeric/simulator,
source reconciliation, alias/retirement, dependency, CI or generator was edited.

### Paired actual-source proof and preserved assets

Evidence root:
`D:/Project/py/RAG/db_sources/rebuild-preservation-owned/20261004/iteration-03/`.
`source-freeze.json` binds actual committed parent build/update bytes and
separately frozen candidate bytes. The newly added helper/data are absent from
the parent implementation; the parent test fixture can read their binding data
but its real builder/update does not invoke the helper. `paired_history.py`
executes separate processes and independent AFB copies with real full CSV,
no term pairs, an empty private inventory, the retained details and normal offline
authority restoration. The candidate uses a private copy of the exact retained
historical raw page/manifest. Both repeat the full build/restoration/rendering
twice and are internally identical. Successful Windows renames confirm handle
release after each full run.

Parent ends with mirror Pedro90/Armour140 and only the October membership check;
candidate ends with Pedro80/Armour155 plus exact September capture/raw/ledger
provenance and the same October check. The full SQL comparison finds **exactly
two changed `units.points_json` cells** among all **20 baseline tables**.
Every other value is exact by key, including all numerical/English body fields,
names, aliases, the source archive and the 87-row glossary. Process-local glossary
row order is accounted for separately. All **1,127 documents** have identical
text and metadata between this iteration's parent/candidate; this count is the
fresh paired baseline, not a reuse of iteration 2's 1,125 count.

All five source-bound Chinese mappings still emit once. GK2863 retains GK397
attribution and no AdM847 document exists. The four quarantined canonical targets
remain absent. The checkout's strict inventory replay remains **32 accepted /
62 reopened** out of 94, with no fingerprint relaxation or restoration of the
47 unsupported historical names.

All **3,635 complete current official ledger rows** remain exact, including
conditional/equipment/occurrence rows. Ordinary Calgar180 and Kaius100 are
ledger-only identities in this baseline, not new canonical datasheets. Armour155
remains separate from both ordinary Calgar180 and deleted-source ordinary Calgar200.
Guilliman415 and Helbrute CSM125/DG105/TS110/WE120 remain exact. No body coverage
or effective date is inferred from any price heading.

All **117 starting input hashes** remain unchanged, including active pickle/FAISS,
recorded raw/cache/recovery inputs and the two additionally read September source
files. One external input already differed from the forensic manifest at the
start: production's `blacklibrary_listing_policy.json` had SHA-256
`37b52cf122278a243951e9229f2a16365ff2e0e450a5b611dddf571f1dc2e864`,
versus forensic `4308772b82c623bf084629311526ec3be858913ddc90c5cea8ed550f879b6376`.
Both hashes and the initial freeze rejection are retained. That external policy
was left untouched and is not certified by the checkout's 32/62 result. The
other 114 original forensic inputs remain exact. This is recorded-input
preservation, not a fresh full recovery/production inventory acceptance audit.

### Validation and open gates

| Final XML-confirmed selection | Collected | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|---:|
| Frozen parent, new history regressions/controls | 30 | 3 | 27 | 0 | 0 |
| Final candidate, same new cases | 30 | 30 | 0 | 0 | 0 |
| Frozen parent, existing identity/history/price/coverage/retirement selection | 772 | 722 | 0 | 0 | 50 |
| Final candidate, same existing selection | 772 | 722 | 0 | 0 | 50 |
| Frozen parent, native recovery selection | 105 | 99 | 0 | 0 | 6 |
| Final candidate, same native selection | 105 | 99 | 0 | 0 | 6 |

Every shared XML node status/skip reason is identical. The native row overlaps
the broader selection and is not additive. Its six unchanged skips require
actual official keyword assets; the broader 50 are the preceding 46 missing
retirement-preparation assets/inventory and four unavailable real-cache Chinese
coverage checks. There are **zero new skips**. This is the relevant native
recovery/CLI/handle/PDF selection, not a claim to rerun an entire historical
native583 or full release suite.

New source fixtures are explicitly synthetic small HTML/CSV inputs; they prove
the real builder/update/MFM seams and guards, while the separate full copied
trials establish actual retained-source behavior. Cases cover clean/AFB/prior
official history, source/manifest/row/price/canonical drift, unsupported advanced
capture dates, missing history, later current publication, repeated builds,
whole-build rollback, empty behavior and actual Windows rename controls. Initial
XML/logs remain retained. The first verification incorrectly expected ordinary
Calgar180 to exist in canonical units; its failure remains in `verification.log`.
The corrected assertion checks its actual ledger-only identity and invents no row.

Python 3.11 compilation, Python 3.9 grammar parsing and `git diff --check` pass.
Ruff/Black remain unavailable and were not installed. All finite children exited;
no persistent process, model, network call, package installation, service or
production asset write occurred. Local duplicate-checked checkpoint/roadmap,
learning and underlying-error records are maintained without changing shared
indexes. The real db494 document-attribution commit explanation is recorded;
the current candidate has no invented commit ID.

Remaining gates: GNHF's scoped historical-price commit and clean-checkout closure,
independent exact-candidate host review, and any final combined acceptance the
root requires. Existing active duplicate Servitor UUID attribution remains
unresolved; no vector was assigned, removed or retagged. Scheduled stage-only
implementation/publication remains a separate owner/run. No deployment or whole
project completion is claimed.

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


## Iteration 4: host-confirmed JSON-null prior-price guard

The blocking available-prior JSON-null defect is corrected against the initially
clean exact parent `61b2231b575cb81b451c566e1df1a4c89ecdb373`. An existing canonical
row whose `points_json` is the JSON text `null` previously decoded to Python
`None`; `_prior_price` interpreted that as an absent identity and granted historical
restoration. `_identity` now requires existing-row decoded JSON to be an object,
raising `ValueError` before the sentinel can escape. Only a genuinely missing
canonical row returns `None`. No source authority is inferred from malformed
available evidence.

The runtime diff changes only `_identity` (five added lines, one replaced return).
The retained bindings, raw parser, canonical/datasheet/keyword guards, from-price
checks, prior/current ledger guards, transaction, builder, update, document
attribution and source boundary remain unchanged. New repository tests cover both
binding positions with JSON null, list, boolean, number, string, empty object,
SQL NULL, malformed MFM/items and invalid JSON. They invoke the actual builder,
require the original database to remain byte-exact, require temporary-file cleanup
and prove SQLite handles are released through actual Windows rename. Positive
controls remove either prior identity and restore the complete verified history.

All new frozen source, proof copies, caches and temporary trials are under
`D:/Project/py/RAG/db_sources/rebuild-preservation-owned/20261004/iteration-04-null-guard/`.
The original host proof remains byte-exact in its owned directory and in
`original-host-proof/`: 25 passed / one JSON-null failure / zero skips.
`parent-freeze.json` and `candidate-freeze.json` hold 62 source/test files from
exact 61b; their runtime difference is only `mfm_history.py`, and paired tests use
identical new test bytes. The real raw controls retain the exact September
manifest and HTML hashes documented above, parsing all 267 source rows. Tiny
trial CSVs/databases are explicit test inputs, not a new full-CSV/full-asset audit.

| Final XML evidence | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| `parent-new.xml`, same 54 history regressions | 52 | 2 (JSON null only) | 0 | 0 |
| `candidate-new.xml` | 54 | 0 | 0 | 0 |
| `parent-realraw.xml`, same 29 retained-raw controls | 28 | 1 (JSON null only) | 0 | 0 |
| `candidate-realraw.xml` | 29 | 0 | 0 | 0 |
| `focused-controls.xml`, existing lifecycle/critical restoration/MFM/update controls | 45 | 0 | 0 | 0 |

The actual-old-database JSON-null build rejects before atomic replacement and
leaves old bytes exact with handles released. Actual retained-raw positive controls
restore Pedro 80 / Armour 155 when either prior row is genuinely absent, and
preserve prior valid official history on two repeated builds. Newer current
ledger, payload/source fingerprint, caller transaction/rollback, cancellation,
missing-raw warning and critical-abort controls remain passing. The retained
initial 26-case raw run also passes; it is included in the final 29-case run,
not added to the final 128-check total. `verification.json` reconciles every XML
node, verifies null-only parent/candidate differences, unchanged frozen modules,
raw/proof immutability and the intended file scope.

Python 3.11 compilation and Python 3.9 grammar checks pass with the specified
existing full-stack interpreter. Ruff, Black, mypy and pylint are unavailable;
none was installed. Generic and Python reviews approve the exact changed guard
with no findings in `generic-review.md` and `python-review.md` under this proof
root. Reviewed helper SHA-256:
`f1592bf82334aef512103dd60e8d80bb55a7aad8c14a776aa52dcfcc3bc1577b`;
reviewed test SHA-256:
`6b1ef75541846f1894e9b559dde5f3233edadf818364be2b7840d5cac967d4b5`.

**Whitespace qualification of the earlier report:** plain complete-family
`git diff --check 1c726e65a1c0e276c39b7584417a1e74f96e9c3e` exits 2 with
2,272 CRLF trailing-whitespace diagnostics in the existing binding JSON files.
The complete family passes with explicit `git -c core.whitespace=cr-at-eol diff
--check` against that same parent. The immediate db494-to-61b family has 136
of those inherited diagnostics. The minimal new slice against 61b passes both
plain and explicit-policy checks. No binding byte normalization was performed;
the earlier unqualified whitespace-pass statement must be read with this policy.

The final intended GNHF commit contains only `db_compile/mfm_history.py`,
`tests/test_mfm_rebuild_history.py` and this appended report; the index is empty
and there are no untracked checkout files. GNHF owns the commit. No commit ID,
merge, push, deployment, full-project acceptance or fresh large asset audit is
claimed. All finite child processes exited; no background service was started.
Deduplicated learning/error additions append to the existing historical MFM
records; shared indexes and unrelated/concurrent notes remain untouched, with
publication reserved for root.
