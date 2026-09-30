# Official revision restoration safety

Latest checkpoint: iteration 2 implements exact row-state revision chains and
staged-manifest selection. Final focused validation is **170 passed / 1 existing
skip**. Metadata chronology, shape validation and write-free provenance replay
remain unfinished; the full objective is not complete. The iteration 1 account
below is retained as historical paired evidence.

## Iteration 1 — critical restoration and build status

This is an incremental implementation checkpoint in the isolated
`C:/Users/Administrator/.codex/worktrees/release-official-revisions/RAG`
worktree. It resolves critical restoration failure propagation and standalone
build status. Exact multi-revision compilation and provenance chronology remain
unfinished. No September 30 rule data has been published or applied, and no
independent review, integrated asset acceptance or deployment is claimed.

### Reproduced failures and resulting behavior

Before changing application code, eleven new disposable regressions produced
**3 failures / 8 passes**. The real source reconciler updated the first synthetic
ability inside its transaction, encountered drift on the second, and rolled back
both. `restore_authority_layers` nevertheless continued through MFM, official
Chinese names, DSL, aliases, Chinese details and weapon names. Its report was
unsuccessful but `aborted_at` remained unset. An explicit unsuccessful critical
stage had the same continuation defect. The standalone build CLI ignored the
unsuccessful restoration report and exited **0**.

Restoration now derives criticality from the existing `_PIPELINE` declarations,
preserving `_RESTORE_STAGES`' legacy `(title, function)` tuples. A critical
exception or unsuccessful result is retained in `UpdateReport.stages`, sets
`aborted_at` to that failed result's name, and stops before all downstream stages.
Existing exception naming is preserved: a caught reconciler exception is named
`stage_source_reconcile`; an explicit result can be named `source_reconcile`.
Warnings remain attached to their results. `UpdateReport.ok` remains false for
any unsuccessful stage; an unsuccessful optional stage still allows later stages
to execute, while a successful stage with a warning remains successful.

The standalone `db_compile build` command checks the restoration report and
exits **1** when it is unsuccessful, even if CSV building produced rows. It
prints the failed stage and the partial-target limitation. Successful legacy
restoration still exits **0**. The existing explicit `--no-restore` path retains
its warning and exit **0**. Normal update already honored the critical flag;
paired ordering tests protect its existing behavior. Network implementations
and their warning policy were not modified.

### Validation and retained evidence

Interpreter: `D:/Project/py/RAG/.venv/Scripts/python.exe`, verified **Python 3.9.1**.
No dependency installation or external access was used.

Focused final command:

```powershell
& 'D:/Project/py/RAG/.venv/Scripts/python.exe' -m pytest `
  tests/test_official_restore_failures.py tests/test_source_reconcile.py `
  tests/test_db_compile_update_stages.py tests/test_db_compile_build.py `
  tests/test_db_compile_dsl_apply.py tests/test_mfm_sync.py `
  tests/test_source_archive.py -q -ra --tb=short
```

Result: **122 passed / 1 skipped / 5 dependency deprecation warnings**, in
**9.23 seconds**. This includes eleven new regressions and 111 existing passes.
The unchanged skip is
`tests/test_db_compile_dsl_apply.py:242`, a real-payload fingerprint audit requiring
the unavailable `db/wh40k.sqlite`. No new skips were added. Ruff, Black and
Flake8 are unavailable in the designated interpreter; no project Python formatter
configuration was found. Scoped Python compilation and
`git -c core.whitespace=cr-at-eol diff --check` passed.

Tests exercise both real pipeline entry points with the actual reconciler and a
synthetic two-row SQLite manifest. Other asset stages are spies retaining the
real pipeline order and critical flags. They verify exact downstream exclusion,
rollback of the first row, no leaked provenance tables, warning retention,
forced offline restoration, positive legacy restoration and optional-stage
continuation. CLI tests use a subprocess and the **actual CSV builder** to
replace the disposable database with two synthetic ability rows, then run actual
source reconciliation and restoration. Only unrelated asset stages are spies.
The failure and successful legacy paths return 1 and 0 respectively; the explicit
skip path returns 0. The actual populated rows are inspected after each process.

Evidence is ignored and confined to:

`C:/Users/Administrator/.codex/worktrees/release-official-revisions/RAG/db_sources/release-check-20260930/official-revision-safety/`

- `iteration-1-red.log`: pre-edit regressions, 3 failures / 8 passes, including
  full downstream continuation and the false-success process result.
- `iteration-1-green.log`: final focused suite, 122 passes / 1 existing skip.
- `iteration-1-real-cli-red.log` and `iteration-1-real-cli-green.log`: paired
  actual CSV build with the same two-row drift. Exact `HEAD` baseline modules
  loaded from saved source copies exit 0; current modules exit 1. Both retain
  the CSV-built rows after the source transaction rolls back.
- `iteration-1-base-update.py` and `iteration-1-base-__main__.py`: baseline
  source captured using `git show HEAD:<path>`, without changing tracked files.
- `iteration-1-cli-trial/`: synthetic manifests, CSV and disposable databases;
  these are not real official source evidence.

### Transaction boundaries and host integration

`source_reconcile.apply_patches` is unchanged in this iteration. Its current
single-call SQLite transaction still rolls back the tested row changes and table
creation on drift. The full CSV build plus authority restoration is **not** one
transaction: the CSV builder replaces its target before restoration starts, and
earlier restoration stages may already have committed when a critical stage
fails. An unsuccessful report or process exit must prevent publication; it does
not restore the pre-build target.

Host integration must rehearse on copied inputs and a disposable target, require
`restore_authority_layers(cfg).ok` / `run_update(cfg).ok` or a zero CLI exit as
applicable, then perform separately reviewed publication. Later stages must not
run after the critical failure. These checks are necessary but do not certify
the remaining revision-chain or metadata defects as fixed.

The reviewed September 14 manifest remains byte-identical:

`db_compile/source_reconcile_patches.json` SHA256
`29b0838504b1e5e1486646f6dcb4466c46d2c68513bcd06e963e4ed174ae34f7`.

No other checkout, production PDF/database/index, global metadata, dependency,
benchmark gold, application owner files or hook repositories were changed. No
services, crawlers or watchers were started. No manual commit, push or merge was
performed. GNHF owns committing this scoped implementation; host owns independent
review, integration, real source promotion and deployment.

### Remaining iteration scope

Next work should reproduce and implement exact multi-revision row-state chains
with complete union fields, strict insertions and fail-closed pre-transaction
declaration checks, retaining legacy single-manifest compatibility. Metadata
shape/date validation, exact chronology and non-downgrade replay must then be
guarded in the same transaction, with paired atomic rollback/idempotency tests.
This iteration does not satisfy the full loop stop condition.

### Knowledge handoff for the host

The handoff check searched existing Markdown records in
`D:/Project/devlog/wh40k-oracle`, `C:/Users/Administrator/learn-notes` and
`C:/Users/Administrator/error-notes` for this report, critical restoration,
restore failures and restoration exit-status findings. No matching record was
found. Those repositories were read only: this iteration's explicit ownership
assigns global knowledge repositories to the host and prohibits modifying other
checkouts. This report holds the scoped checkpoint, verification and remaining
roadmap for transfer without creating duplicate or out-of-scope records.

The reusable finding is that a derived stage list must preserve failure policy
as well as execution order, and a CLI must consume the structured failure result
to produce a truthful process status. The resolved underlying defect is the
loss of criticality in restoration, compounded by an ignored CLI report. The
red failure was `ValueError: Official patch prior-value mismatch:
abilities/{'id': 'two'}`; the defect was downstream execution and exit 0 after
that correctly rejected synthetic drift. The paired evidence above records
the reproduction, the targeted fix and verified exit 1. No unrelated fix or
unverified workaround was tried.

Host follow-through: use the existing note templates to record these findings
in the project checkpoint/roadmap, learning decisions and resolved-error notes
after checking again for intervening entries. A commit explanation under
`D:/Project/devlog/wh40k-oracle/commits/` must wait for the real GNHF commit hash:
this iteration is still uncommitted, and the existing HEAD belongs to earlier
work. No commit record, publication or cross-project rule promotion is claimed.

## Iteration 2 — exact complete row states

### Reproduction and implementation

The initial pre-edit chain suite produced **24 failures / 10 passes**. In the
legacy flat loop, starting at A or B reached C once but then failed on replay;
starting at C failed immediately during the earlier A-to-B pass:

```text
ValueError: Official patch prior-value mismatch:
models/{'unit_id': 'one', 'name': 'Synthetic model'}
```

The final expanded 46-test chain suite was also run against a saved, exact
`HEAD:db_compile/source_reconcile.py` baseline, loaded under its actual module
name without replacing any tracked code. It produced **32 failures / 14 passes**.
Some failures establish new API support; the three flat-chain failures establish
the original defect independently of that API. All sources in these trials are
synthetic `example.com` declarations and every SQLite database is disposable.

Rows now compile by table and complete canonical identity, including both model
key components. Each compiled row contains the union of touched fields and every
complete reviewed state. The first prior value of a later-touched field fills
earlier states. For `t:4->5`, then `t:5->6,m:6->8`, the only accepted states are
`(4,6)`, `(5,6)` and `(6,8)`. Mixtures such as `(6,6)`, `(4,8)` and `(5,8)`, and
unrelated drift within that union, are rejected. Fields outside the union are
preserved and are not claimed to have been validated.

Declaration compilation happens before opening SQLite, hence before
`BEGIN IMMEDIATE`. It rejects incomplete identities, identity writes, unsafe
fields, non-scalar/non-finite values, non-explicit absent states, overlapping
continuity contradictions, duplicate transitions, revisited/ambiguous states
and later insertion declarations. A single legacy no-op keeps its previous
already-current behavior. Explicit ordered revision lists require real ISO
calendar dates in strictly increasing, unique order; inputs are never silently
sorted. These dates order declarations, not source provenance chronology.

Application reads the entire union in one row query and selects the exact
reviewed suffix. A/B/C start states converge to the same final reviewed fields;
only remaining transition fields are updated. Report counters retain their
legacy meanings: `applied`, `already`, `inserted` and `total` count transitions,
not distinct canonical rows. An absent-state insertion followed by updates
converges from absent/intermediate/final states and rejects an existing wrong
row. If a field first appears in a later update, its later `from` value is also
used in the reconstructed inserted state. Actual SQLite insertion constraints
remain enforced; conflicts roll back earlier changes.

All row changes, provenance-table creation and existing metadata writes still
share one `BEGIN IMMEDIATE` transaction per `apply_patches` call. Later missing,
drifted or ambiguous targets and insertion constraint failures roll back earlier
changes across tables and retain unrelated provenance. This is not global
rollback for the CSV builder or other authority stages.

### Callable contract for the later host rehearsal

The existing default `apply_patches(db)` and single-manifest
`apply_patches(db, manifest)` callers remain supported. A legacy flat manifest's
patch order is its explicit transition order. New callers can use:

```python
from pathlib import Path
from db_compile.source_reconcile import apply_patches, compile_revision_chain
from db_compile.update import UpdateConfig, restore_authority_layers

# reviewed_manifests must come from the host's separately reviewed source work.
# These are API examples, not actual promoted revision declarations.
compiled_rows = compile_revision_chain(reviewed_manifests)  # No SQLite access.
report = apply_patches(copied_db, manifests=reviewed_manifests)

# Alternatively store {"revisions": reviewed_manifests} in a staged JSON file.
cfg = UpdateConfig(
    db=Path(copied_db),
    source_reconcile_manifest=Path(staged_manifest_path),
    offline=True,
)
restored = restore_authority_layers(cfg)
if not restored.ok:
    raise RuntimeError(f"Do not publish: restoration failed at {restored.aborted_at}")
```

`compile_revision_chain` returns independent `RowChain` records with `table`,
canonical `key`, `fields`, `states` and `transitions`, and validates ordered
declarations without any database connection. `apply_patches` also accepts a
single `{"revisions": [...]}` envelope. Supplying both legacy and ordered
arguments or mixing envelope and legacy keys is rejected. Empty ordered lists
are rejected; an empty legacy patch list retains compatibility.

`UpdateConfig.source_reconcile_manifest` is optional and appended to existing
config fields to preserve prior positional construction. `None` retains the
built-in September 14 manifest; a staged path selects a legacy manifest or
revision envelope in the real restore/update pipelines without replacing the
built-in manifest or changing global module configuration. A malformed staged
file is a critical restoration failure. No new CLI flag was added in this
iteration; use the callable configuration for staged host rehearsal. Existing
standalone build CLI success/failure behavior remains tested.

### Validation and evidence

Final command uses the designated read-only **Python 3.9.1** interpreter:

```powershell
& 'D:/Project/py/RAG/.venv/Scripts/python.exe' -m pytest `
  tests/test_official_revision_chains.py tests/test_official_restore_failures.py `
  tests/test_source_reconcile.py tests/test_db_compile_update_stages.py `
  tests/test_db_compile_build.py tests/test_db_compile_dsl_apply.py `
  tests/test_mfm_sync.py tests/test_source_archive.py -q -ra --tb=short
```

Result: **170 passed / 1 skipped / 5 existing dependency deprecation warnings**,
in **11.24 seconds**. This adds 46 row-chain tests and two real restore/update
ordering tests to the retained 122 passes. The sole skip remains the real DSL
fingerprint audit at `tests/test_db_compile_dsl_apply.py:242`, which requires
the unavailable production database. No assertions were weakened and no new
skips added. Both configured and default manifest paths are exercised. Real
restore/update entry points stop before every downstream stage when a mixed
union state fails; unrelated stages are ordering spies. The real CSV-build CLI
regressions still verify nonzero failed restoration and zero successful legacy
restoration, including the already-written disposable CSV target limitation.

Scoped Python compilation and whitespace validation passed. Ruff, Black and
Flake8 remain unavailable in this interpreter; none were installed. The actual
September 14 manifest passed compile-only validation: **390 rows / 390
transitions**. This checked declarations without opening or modifying a
production database and did not verify promoted PDF bytes.

Ignored evidence in the same absolute directory recorded above:

- `iteration-2-red.log`: original 34-test pre-edit trial, 24 failures / 10 passes.
- `iteration-2-base-source_reconcile.py`: exact baseline saved from Git HEAD.
- `iteration-2-complete-paired-red.log`: final 46-test suite against that saved
  baseline, 32 failures / 14 passes. Pipeline config comes from current code;
  the baseline comparison isolates the row reconciler.
- `iteration-2-green.log`: final focused suite, 170 passes / 1 existing skip.

Replayed final row states with empty provenance declarations are checked both
by full SQLite dumps and byte-identical database files. **Write-free metadata
replay is not yet implemented or claimed.** Existing `INSERT OR REPLACE`
metadata processing can still rewrite records or downgrade an independently
replayed older manifest. Malformed metadata validation and exact source-list
chronology remain required in the next iteration, in the same transaction.
Actual source hash verification, coverage schema/publication, integrated asset
tests, Python 3.11/Linux validation and independent review belong to later host
work; no current-data or release acceptance is claimed here.

The September 14 manifest remains byte-identical with the SHA256 recorded
above. Scoped edits are the row compiler/reconciler, optional staged-manifest
pipeline selection, disposable tests and this report. No production asset,
other checkout, hook repository, requirements, benchmark gold or separately
owned application file was modified. No services, watchers, crawlers or browser
processes were started; all test subprocesses completed. No manual Git commit,
push or merge occurred. The full loop stop condition remains unmet because of
the pending metadata contract.

### Iteration 2 knowledge handoff and next checkpoint

The final handoff check searched existing Markdown in
`D:/Project/devlog/wh40k-oracle`, `C:/Users/Administrator/learn-notes` and
`C:/Users/Administrator/error-notes` for this report, `compile_revision_chain`,
revision-union/multi-revision findings and `source_reconcile_manifest`. No
matching entries were found. The task expressly assigns external knowledge
repositories to the host and prohibits other-checkout writes; they remain read
only. This scoped report is the implementation checkpoint and roadmap handoff,
not a claim that external records have been published.

Reusable decision for the host's learning template: revision restoration needs
complete row states across the union of reviewed fields. Per-transition guards
alone cannot recognize a final state during an earlier pass. Later first-touch
guards reconstruct fields that earlier transitions did not change. Selecting a
unique complete state before applying its suffix preserves strictness and
idempotency without accepting per-field mixtures. Keep this project-specific
finding in learning notes; no cross-project harness promotion is established.

Resolved-error record for the host: the exact red error and reproduction are in
the iteration 2 reproduction section. The attempted fix was the row-state
compiler and suffix application, with explicit insertion-state handling; the
saved real baseline fails 32 of the final 46 chain tests and current code passes
all 46. The full focused suite passes 170 tests with the one existing asset skip.
No failed alternative implementation or production-data correction is claimed.

Next implementation unit: reproduce metadata downgrade and malformed-metadata
failures on disposable SQLite, then validate source identities, dates/versions
and exact chronology and make provenance replay write-free in the same guarded
transaction. Preserve the completed row-state and critical-abort tests. Require
copied-input host rehearsal and independent review before real source promotion;
publication and deployment remain outside this worktree's ownership.

Commit explanations must use the eventual real GNHF commit for these changes.
Current HEAD `e5795f021` is the earlier handoff commit, not this row-chain
implementation. No commit explanation or manual staging/commit/push was created.
