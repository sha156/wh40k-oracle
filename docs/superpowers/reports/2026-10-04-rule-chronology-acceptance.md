# October 4 rule chronology acceptance checkpoint

## Iteration 1 scope and result

This iteration supplies a read-only validation seam for preexisting official unit
source history. It does **not** implement or accept the dated Sentinel reversal.
The original complete proposal remains rejected, with every proposal retained.
This is a preparatory engine change for the isolated chronology objective.

Launch was clean on `codex/release-rule-chronology` at
`07430047db0ad192ff65a342d000c539e4d54e5c`. The orchestrator notes were read first
and were not edited. No commits, publication, service startup, network requests,
package installation or production restoration were performed.

## Engine contract

`db_compile/source_reconcile.py` now exposes the private
`_read_source_history(conn, uid)` seam and uses it from `_restore_sources`.
The reader performs SELECT statements only. It tolerates absent metadata tables
as absent history and returns an undated current list separately from dated
snapshots. It neither creates tables nor anchors a legacy list to any incoming
date. Existing snapshot dates, source JSON and source declarations are validated;
duplicate current rows or history dates are rejected. A dated history requires
the current list to equal its newest exact snapshot. Existing source chronology
is validated independently before the restoration merger considers incoming
snapshots.

Restoration still validates legacy adoption, same-date identity conflicts and the
combined source chronology before writing metadata. Its writes remain in the
existing transaction. The `apply_patches(db_path, manifest=None, *, manifests=None)`
signature and all six `RowChain` fields are unchanged. Compiler state equality,
union-field construction, transitions and suffix selection are unchanged.
Application does not yet call this seam before selecting a row suffix; that is
remaining work, not an acceptance claim of this checkpoint.

## Verified actual inputs

Evidence is under the owned directory:

`D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-01/`

`inspect_inputs.py` reads the retained full provisional envelope and records its
390 September 14 baseline patches and 121 September 30 cumulative proposed
patches. The original September 30 revision has no Sentinel `unit_sources` entry.
Both the launch and final compile attempts retain the exact failure:

```text
Ambiguous or duplicate reviewed state: units/{'id': '000000759'}
```

`probe_actual_history.py` uses a read-only SQLite URI against
`D:/Project/py/RAG/db/wh40k.sqlite`. The live Sentinel Powerlifter row matches the
exact original September 14 `to.keywords_json` string (state B, including FRAME).
Its current official source list equals the single September 14 source-history
snapshot and the corresponding retained manifest declaration. There is no
Sentinel `official_rule_revisions` row. All observed statements are SELECTs and
`total_changes` is zero. The database hash before and after the probe is:

```text
afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855
```

`inputs-before.json` and `inputs-after.json` preserve **9,259 exact file hashes**,
including all **545** retained field-audit input bindings, the live AFB database,
the preserved 3fd baseline, the original source manifest, the full proposal,
current MFM/Black Library files and FAISS assets. There are zero missing paths and
zero changed protected files. This check proves preservation during this
iteration; it does not certify whole-source-body parity or other owners' audits.

## Validation

Fifteen new parameterized controls cover read-only behavior with absent/present
tables, undated legacy lists, valid checkpoints, unknown units, malformed dates,
malformed/empty source JSON, duplicate dates, missing/drifted/duplicate current
provenance, revisited snapshots, immutable version conflicts and source-date
downgrades. Reader tests use SQLite `mode=ro`, inspect SQL traces where applicable,
and require byte-exact database preservation.

The test-first run failed all fifteen new controls because the private reader
did not exist (`red.log`, `red.xml`). The first broader run had 137 passes and one
new fixture failure: its two rule patches both declared `old -> new`, causing
`Contradictory revision continuity: abilities/{'id': 'rule'}`. The fixture's second
revision was changed to a metadata-only revision; the evidence is retained in
`green.log` and `green.xml` rather than overwritten.

Final validation used the authorized stable Python 3.11 interpreter:

```text
D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe
```

The complete selected files were run with no test exclusions:

```text
-X utf8 -m pytest tests/test_official_revision_chains.py tests/test_official_revision_metadata.py tests/test_official_restore_failures.py tests/test_source_reconcile.py tests/test_corpus_policy.py -q -p no:cacheprovider --basetemp=D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-01/final-tmp --junitxml=D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-01/final.xml
```

Result: **167 passed, zero failures, zero errors, zero skips**, independently
counted from XML. Existing controls include union-field drift, both revision
envelope forms, input immutability, metadata conflict/rollback, older write-free
metadata replay, restore/update critical abort and actual CLI process exit codes.
AST syntax parsing and `git diff --check` pass. Logs, XML, temporary databases,
probe scripts and verification JSON stay in the owned evidence directory. No
background processes remain from this iteration.

## Remaining acceptance and handoff

The read seam now distinguishes an exact preexisting dated checkpoint from an
undated source list without manufacturing authority. A fresh CSV state A without
history still has no demonstrated checkpoint. Invalidation dates alone cannot
supply one: the actual live B checkpoint exists despite an absent rule-revision
row. Preserve this distinction when wiring suffix selection.

The pinned September 30 English PDF still needs independent literal/name/date
inspection and a separately owned, reviewable Sentinel source-anchor augmentation.
Do not derive that anchor from the patch citation, URL, version or invalidation
date, and do not rewrite the other owner's original missing-anchor envelope.

Next engine work must restrict supported repeated states to explicitly anchored,
strictly dated canonical unit rows; retain all guarded union fields and dates;
validate preexisting history before suffix selection; reject unsupported or
unavailable checkpoints; and prevent an older standalone replay from changing
fields under retained newer provenance. No such support is claimed here.
The single legacy no-op and rejection of unsupported cycles remain unchanged.

Full anchored 121-row/168-cell application/replay, the exact 25-row addition,
Sentinel B-to-A/repeated-A byte-exact replay, older/history/union-field controls,
last-guard rollback, metadata/BaseException rollback and handle release,
critical-abort checks with the new reversal, and independent host generic/Python
review remain pending. GNHF owns the intended source/test/report commit. No full
rebuild acceptance, overlay completion, active promotion, deployment or project
completion is claimed.

## Stop-hook knowledge handoff

The explicit stop hook requested the repository handoff after the bounded source
iteration. Existing notes were searched before writing. The local wh40k-oracle
`CHECKPOINT.md` and `ROADMAP.md` under `D:/Project/devlog/wh40k-oracle/` now record
this increment, why preexisting authority matters, the 167-test acceptance and
the remaining dated-cycle/anchor/replay/rollback/review work. The existing
`C:/Users/Administrator/learn-notes/decisions/20261001-authenticate-source-chronology-with-exact-snapshots.md`
was extended rather than duplicated. The corrected metadata-only fixture issue
is recorded with its retained full error and reproduction in
`C:/Users/Administrator/error-notes/rag/20261004-error-11-provenance-fixture-contradictory-transitions.md`,
with an appended README index entry. This resolves the fixture error only.

`knowledge-handoff-verification.json` in the owned evidence directory confirms
all five note changes, byte-preserved prior note bodies, unchanged Git indexes
for devlog/learn-notes/error-notes and XML-confirmed test accounting. Unrelated
existing edits remain intact. No commit explanation was created because the
candidate has no new real commit; no harness promotion, manual staging, commit or
publication occurred. GNHF/root ownership remains as specified above.

## Iteration 2 dated reversal implementation and copied acceptance

This increment implements the dated Sentinel reversal, with a separately owned
explicit source anchor. It supersedes the earlier cycle-pending statements only;
exact empty-name model support and complete 220-row/308-cell acceptance remain
pending. Launch was clean at `5a38ba2db07efdc1b3e4ddd8847bae2f976470c0`.
The empty orchestrator iteration log was read first and remains untouched.
No staging, commits, publication, service startup or production restoration occurred.

Owned proof directory:

`D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-02/`

### Explicit field-evidence anchor

`sentinel-explicit-source-anchor.json` records independent local literal
inspection of both retained PDFs. Their exact keyword lists on one-based pages
86 and 87 match the original reviewed guards, with case normalization only for
the PDF's `Frame` spelling. The actual JSON field values remain unchanged.
Both PDFs name **Sentinel Powerlifter**. The retained September 14 document is
`b8fccdf9cfcd37dc538a1f49d84871e6b184e01c54e9fa83bef8372aa6190601`;
the September 30 document is
`909c055003341a6f45088825b84648adce72f69e97701e744cbe3b0fb41bfc8c`.

The new PDF cover explicitly states `FACTION PACK: VERSION 1.3` and
`Legal for matched play from 30th September 2026`, and lists Sentinel Powerlifter
under `FRAME removed from the following Legends datasheets:`. The date was
therefore read from the PDF itself, rather than adopted from its URL or an
invalidation declaration. Cover and card renders are retained as
`sep30-page-1.png`, `sep30-page-86.png` and `sep30-page-87.png`; the cover was
visually inspected. Literal texts for all three pages are in the anchor file.

The augmentation declares the exact title, version, public asset URL, raw hash,
one-based pages and source date for `unit_sources["000000759"]`. It is explicitly
**field-evidence only**, not certification of the entire source body. Root's
independent generic/source-anchor review remains pending.

`separately-anchored-envelope.json` adds only that source entry to a copied
envelope. All 390 original September 14 patches, all 121 proposed September 30
patches and other metadata are retained exactly. The other owner's original
missing-anchor proposal is not rewritten and still rejects. Its SHA-256 is
`8351e159b846b3d09380eb7a9e12672944f0202904f1c36de4357bc9887734c2`;
the separately anchored copy is
`2370bc7de8d97e50749e52e44339459cff2cd4bb22c5e54783182520a0e5dda8`.

### Compiler and application behavior

Only canonical `units` chains may revisit an earlier complete guarded state.
Every transition in such a chain must belong to a strictly increasing dated
revision with explicit matching unit sources. Each primary/additional patch
citation must match a declared source, including all of its supplied metadata;
an explicit source date must equal the revision date. Same-revision,
undated, non-unit and adjacent no-op cycles remain rejected. Ordinary
contradictory/duplicate declarations retain their existing rejection behavior.
The single legacy no-op contract is unchanged.

Before choosing a suffix, application reads and validates preexisting source
history and checks combined incoming conflicts without writing metadata. A
repeated unit state requires the latest preexisting exact source snapshot to
identify one declared post-transition position that also matches **all** guarded
union fields. An undated list cannot authorize that position. No last-equal-state
shortcut or incoming-history adoption is used for a reversal. Missing history,
unknown checkpoints, mismatched checkpoint/fields, malformed/duplicate/drifted
history and same-date conflicts fail closed. Existing reader chronology guards
continue to apply.

An older standalone unit transition cannot change fields beneath retained newer
source history. Older replay remains write-free when the supplied final fields
are already present. The public `apply_patches` signature, all six `RowChain`
fields, guarded values and union-field backfill are unchanged. Models' identity
validation is unchanged in this increment.

### Actual copied acceptance and preserved failure

`frozen-parent-source_reconcile.py` is the exact Git blob from the launch commit,
SHA-256 `9ab1938ac56f130efe9e6d3507c73dcd1e22c639402e1c6c23f52509c4c8d68a`.
It rejects even the explicitly anchored complete envelope with
`Ambiguous or duplicate reviewed state: units/{'id': '000000759'}`.
The candidate compiles all 511 transitions.

On a private copy of actual AFB
`afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`,
application reports **121 applied / 390 already / zero inserted / 511 total**.
Every final guarded union field matches its compiled state, including the exact
Sentinel B-to-A transition. Its current list becomes the explicit September 30
anchor; the exact September 14 and September 30 history snapshots are retained.
Replay reports **zero applied / 511 already** and preserves every database byte
at `b9cc8948446f6acda131186e38b675edc3564036b15ee03b9d66f686a28b825c`.
The older standalone September 14 Sentinel patch rejects instead of re-adding
FRAME, with the same byte-exact preservation.

The first proof attempt incorrectly expected the preserved 3fd baseline to have
the same dated history as AFB. It has the exact September 14 **undated current
list and no source-history snapshots**. The initial assertion log/script are
retained as `copied-reversal.log` and `proof-attempt-01.py`. The corrected proof
treats copied 3fd as a fail-closed control: it rejects for missing preexisting
dated history and stays byte-exact at
`3fd7d812807517dae290dc1eb7477537b7e1a490493b3352dcc49ab6885e1e49`.
No checkpoint is invented, and fresh CSV rebuild reconciliation is not claimed.

`copied-reversal-acceptance.json` and `copied-reversal-02.log` contain the complete
results. `actual-atomic-failure-acceptance.json` additionally verifies separate
AFB copies with a last-row prior-value mismatch, an exception after all metadata
writes, and a `KeyboardInterrupt` after all metadata writes. Each restores the
whole database byte-exactly, including schema/history/rows, and permits Windows
file replacement afterward. The production AFB remains unchanged.

### Scoped validation and remaining work

Twenty-five new reversal controls cover exact suffix selection, full union
guards, history/checkpoint failures, source binding, unsupported cycles, older
standalone rejection, older final-field no-op, and rollback/handle release.
Three new caller controls exercise the actual restore/update critical abort and
real build CLI. The CLI builds exact unanchored CSV state A, exits with status 1
for absent preexisting history, and leaves no invented official metadata.

The first broader run passed 191 tests. A subsequent expanded run passed 192
and failed three new caller tests because their fixture helper import omitted
the `tests.` package prefix. That test wiring was corrected; `second.log` and
`second.xml` preserve the original failures. The caller-only check passed all 16.
Final validation uses the same authorized stable full-stack Python 3.11 and the
following complete files, with no exclusions or new skips:

```text
-X utf8 -m pytest tests/test_official_dated_reversals.py tests/test_official_revision_chains.py tests/test_official_revision_metadata.py tests/test_official_restore_failures.py tests/test_source_reconcile.py tests/test_corpus_policy.py -q -p no:cacheprovider --basetemp=D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-02/final-tmp --junitxml=D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-02/final.xml
```

Result: **195 passed / zero failures / zero errors / zero skips**, with exact XML
node accounting. AST parsing and `git diff --check` pass. Of the 9,259 monitored
files, 9,258 remain exact with zero missing paths, including production assets,
all frozen PDFs/proposals, original manifest and both source databases. The only
changed monitored path is the concurrent field owner's report in
`release-official-revisions/RAG/docs/superpowers/reports/2026-10-01-official-field-preflight-acceptance.md`;
its before/after hashes are retained in `inputs-after.json`, and this iteration
did not write that file. The initial aggregate verifier rejected that external
report change; its verifier is retained as `input-verifier-attempt-01.py`.
Evidence includes the originals, frozen parent and failed attempts.
No background processes were started. Only owned engine/tests and this appended
report are intended for the orchestrator's commit.

Next increment: implement exact `models(unit_id,name="")` support against the
actual unique composite key and owner source evidence, without accepting missing
or null names, then run the complete independently anchored **220-row/308-cell**
proposal and its exact rollback/no-op/identity controls. Root's generic/Python
reviews and GNHF's intended commit remain pending. No full-source parity, full
13-overlay completion, active promotion, rebuild repair, deployment or project
completion is claimed.

The existing English checkpoint, roadmap and exact-snapshot decision note were
extended with this verified increment rather than replaced. The package-helper
import failure has one new resolved error record and README entry.
`knowledge-handoff-verification.json` confirms prior note bodies and the three
knowledge repositories' Git indexes are preserved. No commit explanation was
invented, and no knowledge publication or harness promotion occurred.

## Complete exact empty-model and 220-row acceptance

This increment completes copied application acceptance of the entire reviewed
**220-row/308-cell** proposal, including the three exact empty-name model keys.
The clean launch was `42e6c528c`, with the preceding dated reversal implementation
already present. The orchestrator's iteration notes were read first and remain
untouched. Changes are restricted to the owned reconciler, its relevant tests,
and this appended report; GNHF retains commit ownership.

Evidence is under:

`D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-03/`

### Exact identity and independently checked field evidence

The exception permits the actual string `name=""` only for `models`, with a
nonempty string `unit_id`. Missing/null names, extra identity fields and nonstring
or blank owner IDs remain invalid. The actual retained `models` schema has TEXT
identity columns and **no unique index**. Application therefore checks the
schema, exactly one stored composite row and exactly one stored owner in the
transaction. Binary comparisons prevent schema collation from broadening the
lookup or update. Empty-name models cannot be invented through absent-state
insertion; named sibling models and other owners remain untouched. Other tables'
identity rules, public application API and `RowChain` fields are unchanged.

`exact-empty-model-source-binding.json` binds the three exact actual owner rows,
blank model rows, unchanged proposal declarations and the existing field owner's
amendment ledger. Independent literal inspection of pinned CSM English PDF
`237a44973f019f0bf72def98f747a0fcf2d5644a559b815a64987bdb468a7cf9`,
one-based page 38, verifies Kravek Morne (`000004205`) at **T6**, and Red Corsairs
Raiders (`000004191`) and Red Corsairs Reave-Captain (`000004192`) at **T5**. Their
actual prior values are T5/T4/T4 respectively. The cover explicitly supplies the
September 30 legal date. This evidence certifies those field recipients only.
Runtime source syntax checks do not independently interpret PDFs or establish
new identity mappings from their prose.

### Complete retained proposal and copied application

`complete-separately-anchored-envelope.json` retains the exact original 390-patch
manifest and all 220 proposed patches/308 field values from the field owner's
`batch-03-ac-csm/verified-01/cumulative-provisional-revision.json`. All preceding
121 proposed patches are retained exactly. Only the independently explicit
Sentinel source anchor from iteration-02 is added to the copied September 30
revision. The other owner's original missing-anchor proposal is unchanged and
still rejects. No reviewed values, identities or metadata are silently dropped
or coerced.

The frozen launch code, retained as `frozen-launch-source_reconcile.py`, rejects
the complete anchored proposal with `A complete canonical identity is required`.
The candidate compiles all **610 transitions**. `prove_complete.py` and
`complete-first.log` preserve the executable copied acceptance.

Actual AFB remains byte-exact at
`afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`.
On its private copy, application returns **220 applied / 390 already / zero
inserted / 610 total**. Every compiled guarded union field reaches its exact
final state. Whole nonmetadata-table snapshots show that only the reviewed field
values changed, preserving every other row and field. Sentinel has exactly the
reviewed B-to-A transition; its current list equals the explicit September 30
snapshot, both exact September 14/30 snapshots remain, and its invalidation date
is September 30.

Replay returns **zero applied / 610 already** and preserves every database byte:

`e13c668b4c0e94a4e0c631c83788319ffdf73bec9bf9a330bf99bc6506c6cd8b`

The older standalone September 14 Sentinel change rejects rather than restoring
FRAME under newer provenance. An older supplied-final-field model replay remains
write-free. The original preserved 3fd database still has only an undated current
list, rejects this reversal, and remains byte-exact. No fresh CSV rebuild repair
or invented history is claimed.

Seventeen actual copied failure controls preserve every byte and release Windows
file handles: older Sentinel replay, missing incoming anchor, undated 3fd, absent
history/state A, undated A, September 14 A, September 30 B, unknown checkpoint,
malformed history, drifted current provenance, null/missing/duplicate blank model
rows, missing owner, the last compiled-row prior guard, and both ordinary and
`KeyboardInterrupt` failures after all row/schema/history metadata writes.
Results and exact failure messages are in `complete-copied-acceptance.json`.

### Tests, preservation and review

The test-first run preserves **11 failures / 12 passes** from the parent rejecting
the required blank keys; `red.log` and `red.xml` are retained. The first candidate
run passed 218 tests. Additional controls cover duplicate owners, binary identity
under a NOCASE schema, whole model union-field drift, real restore/update critical
abort, and real CSV/build CLI acceptance of an exact blank model or rejection of
its duplicate. Caller controls substitute unrelated asset stages explicitly;
they do not claim whole rebuild/source acceptance.

Final validation uses the unchanged authorized stable full-stack Python 3.11:

```text
-X utf8 -m pytest tests/test_official_empty_model_keys.py tests/test_official_dated_reversals.py tests/test_official_revision_chains.py tests/test_official_revision_metadata.py tests/test_official_restore_failures.py tests/test_source_reconcile.py tests/test_corpus_policy.py -q -p no:cacheprovider --basetemp=D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-03/final-tmp --junitxml=D:/Project/py/RAG/db_sources/rule-chronology-owned/20261004/iteration-03/final.xml
```

Result: **225 passed / zero failures / zero errors / zero skips**, with 225 unique
XML testcase identities and no filters or exclusions. AST parsing and
`git diff --check` pass. Ruff/Black/mypy/pylint/Bandit are unavailable in this
interpreter; no separate formatter/linter execution is claimed.

`verify_final.py` compares the prior retained 9,259-file binding set. The first
check found all 9,259 exact; the final check finds **9,258 exact / zero missing**.
The sole change is the concurrent field owner's report in the separate
`release-official-revisions` worktree, from hash `3cdcaa5a...` to `af662c6d...`;
full hashes and sizes are recorded in `final-verification.json`. This iteration
did not write that report. All production assets, original manifest/PDF/proposal
inputs, frozen 3fd baseline and actual AFB remain exact. Verification also confirms
the exact original 390 manifest, untouched full proposal and XML/diff accounting.
Only four intended paths in this worktree are changed. No background processes
were started; all foreground tests/proofs exited.

Independent Python and generic reviewers approve the implementation without
findings. The generic reviewer independently checked both Sentinel PDF hashes,
cover/name/keyword literals and explicit legal date, plus the pinned CSM page-38
recipients and actual blank rows. The reviewed engine SHA-256 is
`c509e1bd57bb1e00135299f40a0ba310dd1a8f3b2f84a7be44f5578577ad8250`.
`independent-reviews.json` retains both final review outcomes. The generic reviewer
independently reran the complete copied proof in `review-generic-03/`, obtained
the identical acceptance JSON, and independently passed all 225 tests with exact
XML accounting. Both reviewers confirm all started processes have exited.

Implementation and copied acceptance are complete within this scope. GNHF's
intended commit and root publication remain separate; no manual staging, commit,
push or merge occurred. There is no full-source parity, full 13-overlay,
production promotion, fresh rebuild repair, deployment or project-completion
claim. The existing English checkpoint/roadmap/learning note are updated by
appending this verified result, without inventing a commit or duplicating errors.
The final handoff initially rejected an authorized concurrent note append because
of a stale whole-document hash. Requiring the exact owned appendix once allowed
the correction while preserving all current text and Git indexes. The resolved
issue is indexed once as `20261004-error-17-concurrent-note-hash-guard.md`;
`knowledge-handoff-verification.json` retains the note/index reconciliation.
