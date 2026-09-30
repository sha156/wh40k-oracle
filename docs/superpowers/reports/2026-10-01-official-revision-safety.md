# Official revision restoration safety

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
