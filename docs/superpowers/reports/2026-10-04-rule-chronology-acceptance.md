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
