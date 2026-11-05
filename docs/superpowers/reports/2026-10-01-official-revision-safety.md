# Official revision restoration safety

Latest checkpoint: iteration 3 completes guarded provenance chronology and
write-free replay alongside the retained exact row-state and critical-abort
contracts. Final scoped validation is **232 passed / 1 existing asset skip**.
The implementation is ready for independent host review and copied-input source
promotion rehearsal. Actual source publication, integrated production-asset
acceptance, Python 3.11/Linux checks and deployment belong to the host and are
not claimed. The earlier iteration accounts remain historical paired evidence.

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

## Iteration 3 — atomic exact provenance chronology

### Reproduction and result

This iteration's individually verifiable scope was the unfinished provenance
contract. The initial 44-test disposable suite produced **42 failures / 2
passes** before application edits. It reproduced older replay replacing newer
rule dates and sources, `INSERT OR REPLACE` rewriting unchanged provenance,
malformed sources being accepted, same-date identity conflicts being overwritten
and the real restore/update pipelines continuing after those accepted conflicts.
One fixture originally repeated a row transition within an ordered chain; it
was corrected to a metadata-only revision, without weakening the assertion.

The final 62-test metadata suite was also paired against the exact
saved `HEAD:db_compile/source_reconcile.py` baseline. It produced **60 failures /
2 passes**; current code passes all 62. This expanded comparison includes new
chronology-table assertions, so not all failures represent previously callable
behavior. The original downgrade, rewrite, malformed-source and continuation
failures do. The baseline CLI subprocess also loads the saved reconciler while
using the real current CSV builder/restore dispatch and unrelated asset spies.
Its malformed-provenance build returns **0**; current code returns **1**.

### Contract and transaction semantics

The public `apply_patches` signatures, envelope, `compile_revision_chain`,
`UpdateConfig.source_reconcile_manifest` and transition counters remain as
documented above. Undated legacy patches without provenance remain supported.
Provenance declarations require an ISO calendar `source_date`; metadata-only
dated revisions with an empty patch list are supported. Ordered dates remain
strictly increasing and unique, rather than being silently sorted.

All incoming metadata is checked before SQLite is opened. Invalidation IDs must
be unique nonempty canonical strings; `unit_sources` must map canonical IDs to
nonempty source lists. Primary and additional patch citations use the same
validation. Sources require an HTTPS URL with a host and no embedded credentials,
lowercase 64-character SHA256 and a positive integer one-based page. Optional
`title`, `kind`, `version` are nonempty strings; `published`, `source_date`, `date`
are real ISO calendar dates; `article` is an HTTPS URL. These are the supported
source fields; unknown fields are rejected. Duplicate `(url,page)` citations and
inconsistent hashes/dates/versions across pages of one URL fail closed. Conflicts
between different unit citations and patch citations within the same reviewed
revision also fail before SQLite access. Coverage
metadata is explicitly unsupported, rather than silently accepted or published.

The existing `official_rule_revisions(unit_id,source_date)` and
`official_unit_sources(unit_id,sources_json)` reader schemas remain unchanged.
The reconciler adds `official_unit_source_revisions(unit_id,source_date,
sources_json)`, keyed by `(unit_id,source_date)`, to store each complete reviewed
source-list snapshot. This is created only on the supplied target; no production
database or global metadata was changed. Consumers were inspected in
`db_compile/datasheet.py`, `wiki_engine/from_db.py`, translation guards and tests;
they continue to read the same current-source contract.

Current sources must equal the exact latest stored snapshot before any new
declaration can authorize a change. Every same-date incoming snapshot must
equal its stored snapshot, including URL, hash, page, dates, version and other
supported fields. Thus an older replay cannot hide an identity conflict behind
a newer date. A legacy current list with no chronology is adopted only when it
exactly matches a supplied reviewed snapshot; otherwise the call rejects it.
Including the reviewed earlier manifest in an ordered envelope gives the later
promotion run that exact adoption anchor. A unit's rule date, PDF URL spelling
or largest publication date is never used to guess a source list's identity.

After validating exact stored and incoming snapshots, the last chronological
reviewed snapshot becomes current. Older known replay retains the newer rule
date and source list without writing. A repeated complete apply changes neither
rows nor provenance; disposable SQLite files remain byte-identical. Equal
legacy JSON content retains its original bytes/key ordering. Earlier snapshots
remain in history. A declaration cannot reintroduce a superseded complete list
or a superseded hash at an unchanged URL by adding another citation. Identical
source bytes cannot acquire conflicting or lose known publication/date/version
metadata; a changed hash at the same URL cannot regress a known source date.
Contradictions among incoming declarations fail before a connection; conflicts
against existing history fail within the guarded transaction. Version labels
are compared exactly, without guessing a numerical rank.

Metadata targets must resolve to exactly one canonical `units.id` after the row
suffix has run. Missing/ambiguous targets, malformed touched current provenance
or history, history/current-list drift and conflicts roll back all row updates,
insertions, provenance-table creation, rule dates and source snapshots from the
call. Unrelated provenance rows are preserved. Unknown extra citations in a
touched current list cause rejection rather than being erased. Row changes and
all three provenance tables share the single existing `BEGIN IMMEDIATE`.
Counters continue to describe rule transitions, not metadata writes.

The retained real restore/update ordering tests now also cover metadata
conflicts: `UpdateReport.ok` is false, `aborted_at` is
`stage_source_reconcile`, and no MFM/Chinese/DSL/alias downstream stage runs.
The actual CSV-build subprocess rejects malformed metadata with exit **1** even
after producing CSV rows. Its legacy success path still exits **0**. Optional
stages and network-warning policy remain unchanged.

### Validation and evidence

Final command, using the designated read-only **Python 3.9.1** interpreter:

```powershell
& 'D:/Project/py/RAG/.venv/Scripts/python.exe' -X utf8 -m pytest `
  tests/test_official_revision_metadata.py tests/test_official_revision_chains.py `
  tests/test_official_restore_failures.py tests/test_source_reconcile.py `
  tests/test_db_compile_update_stages.py tests/test_db_compile_build.py `
  tests/test_db_compile_dsl_apply.py tests/test_mfm_sync.py `
  tests/test_source_archive.py -q -ra --tb=short
```

Result: **232 passed / 1 skipped / 5 existing dependency deprecation warnings**
in **14.02 seconds**. All 170 retained passes and 62 new metadata passes are
included. The sole skip is unchanged:
`tests/test_db_compile_dsl_apply.py:242` needs the unavailable real database for
its DSL payload fingerprint audit. No assertion was weakened or new skip added.
Source compilation, test compilation and
`git -c core.whitespace=cr-at-eol diff --check` passed. Ruff, Black and Flake8
remain unavailable; nothing was installed. The actual September 14 manifest
passed declaration-only compilation at **390 rows / 390 transitions** and
remains byte-identical with SHA256
`29b0838504b1e5e1486646f6dcb4466c46d2c68513bcd06e963e4ed174ae34f7`.

Ignored paired evidence remains confined to the absolute evidence directory
given above:

- `iteration-3-red.log`: initial pre-edit 44-test trial, 42 failures / 2 passes.
- `iteration-3-base-source_reconcile.py`: exact Git HEAD baseline source.
- `iteration-3-paired-baseline.py`: repeatable baseline module loader, including
  the actual CLI subprocess; it does not replace tracked files.
- `iteration-3-complete-paired-red.log`: final 62-test suite against that saved
  baseline, 60 failures / 2 passes.
- `iteration-3-green.log`: final focused suite, 232 passes / 1 existing skip.

All source declarations in these tests are explicitly synthetic
`example.com` sources and all database writes are disposable. The extra history
tests distinguish schema absence in the baseline from the original defects.
Tests inspect full SQL dumps after failures and database bytes after replay,
including legacy provenance adoption and later metadata failure after earlier
row/rule/source changes have run.

### Host handoff and remaining publication work

The scoped implementation contracts now meet this loop's stop condition and
are ready for independent host review. Source files were inspected locally;
no independent review pass is claimed. The CSV build and the whole authority
pipeline are still not globally atomic: a failed restoration can leave a
previously replaced CSV target or earlier committed stages. Publication must
use copied inputs and a disposable target, then require a successful structured
report/process status before separately reviewed promotion.

For legacy-source adoption, supply the unchanged reviewed September 14 manifest
plus the host's separately reviewed later manifests in order through the
existing callable/envelope configuration. Rehearse A/B/C row states, replay and
intentional drift on copies before production use. A legacy manifest alone
still cannot recognize row values outside its exact known states; on that drift
it fails and leaves all provenance unchanged. Successful older-only metadata
replay requires its rows to remain an exact known state and the source history
to authenticate the newer current list.

The review date orders reviewed snapshots; it does not establish content
currency, effective-date correctness or PDF authenticity. The host must verify
actual promoted PDF hashes and source context, perform integrated asset and
Python 3.11/Linux acceptance, and publish/deploy separately. No September 30
rule patches, coverage rows, PDF/DB/index publication, real-current-data claim
or release completion was made here.

Reusable learning for the host's existing note templates: a latest date cannot
authenticate a source list. Store exact reviewed snapshots, validate current
identity against them, reject same-date conflicts, and update only when the
guarded chronological successor is established. The resolved error is metadata
replay replacing newer provenance and rewriting unchanged records; paired
baseline/green logs above record its reproduction and resolution. External
devlog, learning/error notes and harness repositories remain owned by the host;
this report is the scoped handoff, without duplicate external records.

Only the reconciler, synthetic metadata tests and this report changed in this
iteration. No other checkout, production assets, dependency requirements,
benchmark gold, hook repositories or separately owned application source was
modified. No network access, services, watchers or browsers were started; all
test subprocesses completed. No manual commit, push or merge was performed.
GNHF owns the eventual commit; commit explanations must use its actual hash.

### Follow-up knowledge hook handoff

The explicit follow-up hook requested local knowledge-repository updates after
the implementation turn. A fresh duplicate check found the host's existing
critical-abort decision, error 08 and real `e5795f021` commit explanation. Those
records were preserved; no matching source-chronology/replay record existed.

The hook's requested local handoff is now recorded in:

- `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`: isolated
  candidate behavior, verification, publication limits and pending host work.
- `C:/Users/Administrator/learn-notes/decisions/20261001-authenticate-source-chronology-with-exact-snapshots.md`:
  raw reusable decision using the repository's frontmatter/template.
- `C:/Users/Administrator/error-notes/rag/20261001-error-09-official-provenance-replay-downgrade.md`:
  underlying provenance error, saved red diagnostic, synthetic reproduction,
  actual fix and verified resolution.
- The learning/error README indexes link those new records.

These are local Markdown handoff updates explicitly requested by the later
hook, distinct from the preceding implementation scope. Existing dirty/staged
note edits were preserved. No application code, production assets or harness
rules changed during this handoff; no manual staging, commit or push occurred.
The new implementation commit explanation remains pending its actual GNHF
hash. Independent review and note/source publication remain host work.
