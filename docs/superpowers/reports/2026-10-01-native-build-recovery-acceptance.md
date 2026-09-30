# Native build recovery acceptance checkpoint

Iteration 1 repairs the shared SQLite builder lifecycle and verifies **all 43 original diagnosed build/archive IDs pass without skips** under genuine Windows Python 3.11.9. This is incremental isolated recovery, uncommitted and independently unreviewed. The complete 44-ID/full-available-CI stop condition is **not met**: the paired keyword negative fixture remains unchanged, full CI remains unrun, and broader validation exposed three newer CLI fixture failures.

Assigned checkout: `C:/Users/Administrator/.codex/worktrees/release-native-build-recovery/RAG`. Starting HEAD: `1cdb85f7605a5f36b833e1423f7136b4e2c449bf`. GNHF owns commits; root owns independent review, integration and publication. No manual staging, commit, push, merge, service startup or production asset write occurred.

## Correction and ownership

`db_compile/build.py::build_database` initializes its owned cursor before acquisition, closes that cursor before the connection, and attempts both closes even if either close raises. Cleanup preserves an existing build exception, including `KeyboardInterrupt`. Without an existing build exception, the first close error is raised and prevents publication. All closes finish before atomic `os.replace` or the existing failure tempfile cleanup.

CSV/table builders continue to share the same single cursor. `preserve_archived_units` already releases its separate read-only source connection before validation; its implicit queries fetch their results and are not retained across connection closure. Its source/archive validation, destination transaction, commit order and rebuild identity are unchanged. No retries, sleeps, garbage collection, skip/xfail additions or changed authority semantics were introduced.

Eleven new lifecycle cases retain strong references to real SQLite connections/cursors so cleanup cannot rely on object disposal. They verify committed replacement, original target bytes before replacement, failures at connection/cursor/schema/archive/commit/replace, removal of temporary files, close order, continued connection close after cursor close errors, original exception identity, and failure to publish when close fails. Injected close errors occur after real handle closure; permanently unclosable OS handles are not claimed to be recoverable.

Diff review caught an edge case in the first candidate: `sys.exc_info()` can report an unrelated exception handled by the caller even when this build succeeded, incorrectly suppressing a close failure. A dedicated case failed that candidate (`first-candidate-caller.{log,xml}`). The final correction uses a flag scoped to this build attempt, set successful only after commit. All eleven final cases are also tested against the frozen builder.

The only tracked implementation/test changes in this iteration are the builder and `tests/test_db_compile_build_lifecycle.py`; this report is the sole project documentation change. Requirements, constraints, Dockerfile, source-reconcile/update/CLI authority logic, application/frontend/gold and all production PDFs, caches, SQLite, indexes and wiki assets remain outside the changed set.

## Paired evidence

Evidence root: `C:/Users/Administrator/.codex/worktrees/release-native-build-recovery/RAG/db_sources/native-build-recovery/iteration-01/` (ignored, disposable assets only).

Read-only test interpreter:

`D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-ci/Scripts/python.exe`

Verified runtime: Python 3.11.9, MSC v.1938 AMD64, Windows build 26200. This completed environment was not installed into, upgraded or removed. Dependency/platform replacements remain another owner's gate. Test runs set offline Hugging Face/Transformers flags and did not call models/providers or install dependencies.

| Invocation | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Exact frozen c021 builder, original 43 IDs | 0 | 28 | 15 | 0 |
| Same 43 IDs, corrected builder | 43 | 0 | 0 | 0 |
| New lifecycle tests, unchanged builder | 2 | 9 | 0 | 0 |
| New lifecycle tests in corrected broader run | 11 | 0 | 0 | 0 |
| Broader build/archive/authority run, 151 collected | 147 | 3 | 0 | 1 |

The original 40 replacement and three archive-error cleanup IDs are selected directly from the retained triage `classification.json`; both XMLs have exactly the same 43 IDs, independently reconciled by `verify_evidence.py`. The baseline runner asserts newline-normalized current builder text equals the exact c021 Git blob before loading that frozen module. It does not replace latest source with a historical checkout.

Original diagnosed failures now pass their existing assertions, including all three invalid archived records preserving original DB bytes and removing `.tmp.sqlite`, valid archive retention across rebuilds, and idempotent rebuilds. Full baseline/candidate stdout, XML, node IDs and interpreter/source metadata are saved as `before-43.*`, `after-43.*` and `*-metadata.json`. The negative fixture is deliberately not included in this 43-ID result.

Frozen base builder SHA-256 (Git blob): `e905ec3db08294d2ea8741c60d382c9cde7a869273a94d77a0e413ef55386248`.

Candidate builder SHA-256 (working-file bytes): `d6367b9c70c678efac6d2c43d19cb9985f26a4346b0337c03463b3172045640f`.

New lifecycle test SHA-256: `1fc2251b9270eff1eb6bf0ef63b757adacd3c74cbea34188e062e1f5b2044d2d`.

Separate system-stdlib probe interpreter: `C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe`, verified 3.11.9. The exact frozen builder fails with `PermissionError: [WinError 32]`, retaining original target bytes and leaving its locked tempfile. The corrected builder returns one faction/datasheet/unit, replaces the original target, reads back the expected unit and leaves no tempfile. `stdlib-before/after.{json,log}` retain full evidence; the baseline's deliberately leaked disposable directory is cleaned by the parent after the probe process exits. No GC/retry workaround is used in application code.

Reproduce the exact diagnosed candidate run from the assigned checkout:

```powershell
& 'D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-ci/Scripts/python.exe' 'db_sources/native-build-recovery/iteration-01/run_diagnosed.py' after
```

The baseline assertion intentionally prevents running its `before` mode against an already changed builder. Retained frozen source, pre-fix XML/logs and original metadata remain available for review.

## Broader validation and newly exposed fixture boundary

The broader command uses the same stable interpreter and runs:

```text
-m pytest -q tests/test_db_compile_build_lifecycle.py tests/test_db_compile_build.py
tests/test_source_archive.py tests/test_agent_source_archive.py
tests/test_official_restore_failures.py tests/test_source_reconcile.py
tests/test_db_compile_update_stages.py tests/test_db_compile_dsl_apply.py
tests/test_mfm_sync.py --tb=short -rs
--junitxml=db_sources/native-build-recovery/iteration-01/broader.xml
```

The unchanged legitimate skip is exactly:

`tests/test_db_compile_dsl_apply.py::TestMaterialize::test_real_payload_projection_counts`

Reason: `需要 db/wh40k.sqlite（真源 payload 指纹对账）` — real SQLite payload fingerprint audit requires the ignored production database. No asset is copied into this worktree to turn it into an actual-asset acceptance run. One pre-existing invalid-escape DeprecationWarning in the simulator spike is retained.

Three failures remain visible:

```text
tests/test_official_restore_failures.py::test_build_cli_process_status[True-False-1]
tests/test_official_restore_failures.py::test_build_cli_process_status[False-False-0]
tests/test_official_restore_failures.py::test_build_cli_process_status[True-True-0]
```

Their parent fixture creates `trial.sqlite` with `with sqlite3.connect(db) as conn:` and never explicitly closes it. A SQLite connection context commits/rolls back but does not close the connection. The child builder now closes its own temporary handles correctly, but Windows rejects replacement of the still-open parent target:

```text
File "db_compile/build.py", line 456, in build_database
    os.replace(str(tmp_path), str(db_path))
PermissionError: [WinError 5] 拒绝访问。: '.../trial.tmp.sqlite' -> '.../trial.sqlite'
```

The ignored `cli_fixture_probe.py` saves complete child stdout/stderr and tests an in-memory fixture-only `conn.close()` before subprocess launch. All original assertions then pass for all three modes: drift exit 1 with real prior-value failure and stopped downstream stages; successful restoration exit 0 with real reconciled rows; explicit no-restore exit 0. Unrelated asset stages are the existing test's spies, not actual source layers. The probe retains and explicitly closes its parent handles before disposing files. **No tracked fixture correction or passing whole-broader-suite claim is made yet.**

These tests were added after c021 (180 lines in a new test file). Since c021, the current branch also carries reviewed CLI restoration failure handling, update criticality and source-reconcile revisions. Those newer modules remain intact; the builder itself was identical to c021 before this correction. The 43 original cases use current tests and current unrelated source for both paired runs, holding them constant. The preserved fresh-build authority tests and diagnostic CLI results do not establish full real-cache authority restoration.

## Inspection and next iteration

`git diff --check` passes. Exact builder diff and new test source were inspected. Python 3.11 compilation and Python 3.9 grammar parsing pass; grammar compatibility is not a Python 3.9 runtime suite result. Ruff/Black are unavailable in the read-only environment, and neither was installed. No persistent background process was started; all pytest/probe subprocesses exited.

Next smallest work: explicitly release the newly identified parent fixture connection, preserving all authority/CLI assertions; rerun the three affected cases and the broader suite. Then provide the tiny genuine Chinese companion for the original negative English-PDF fixture, run all 44 diagnosed IDs, and run available full native CI with XML-confirmed counts and exact unchanged missing-asset skip reasons. Expand testing only as subsequent corrections/failures require.

Remaining gates: independent host code/Python review, full available CI and copied real-asset authority acceptance where available; separate supported dependency/transformers/platform candidate acceptance, production source coverage/official refresh, Docker/browser/benchmark and hosted CI/integration/publication. No third-party dependency regression, final release, source-retirement completion or deployment acceptance is claimed. Local knowledge handoff records this lifecycle resolution and the newly isolated parent-fixture boundary; GNHF/root retain ownership of commits/publication.
