# October 4 Black Library snapshot merge boundary acceptance

Iteration 1 fixes the incomplete snapshot merge boundary and preserves usable complete partial captures. It does **not** implement filesystem failure diagnostics or resolve the original `PermissionError`. The broader objective remains open.

Initial clean checkout: `D:/Project/py/RAG`, branch `codex/review-answer-provenance`, HEAD `21e0b60075c85206742a4a437a9b36682938030f`. This iteration changes only `db_compile/blacklibrary_snapshot.py`, `tests/test_blacklibrary_snapshot_merge.py`, and this report. GNHF owns the commit; no manual commit, publication, merge, service operation, network request, dependency installation, model load, active data write, or full-project test run was performed.

Evidence root: `D:/Project/py/RAG/db_sources/blacklibrary-snapshot-boundary-owned/20261004/iteration-01/`.

## Proven failure and bounded resolution

The original `db_sources/blacklibrary-listing-review-owned/20261004/host-tests.log` records **101 passed / one failed**. Its retained `host-pytest-tmp/test_duplicate_previous_source0/snapshot/manifest.json` has reconciled units, `status: partial`, `error: PermissionError`, and no `details.json` output. The former merge implementation blindly indexed that missing output and raised `KeyError('details.json')`. The original filesystem operation, errno/winerror, and traceback were not retained. Later successful runs do not identify its cause or establish that it is resolved.

A read-only comparison of that exact retained snapshot against the frozen parent module and current module confirms:

| Module | Actual merge result |
| --- | --- |
| Exact parent implementation | `KeyError('details.json')` |
| Candidate implementation | `ValueError('Snapshot manifest or required outputs are incomplete or invalid')` |

`paired-retained-and-xml.json` preserves that comparison. Neither call writes the snapshot or imports its records.

The merge now validates the manifest object, exact integer schema/game/expected-count fields, reconciliation/status, request mapping, required `units.json` and `details.json` declarations, known optional output names, exact output metadata keys, lowercase SHA-256 format, nonnegative integer counts, parsed list/object shapes, consumed detail/unit fields, capture references, and matching inventory ID sets. Missing files, malformed JSON, and incomplete declared outputs fail with the fixed boundary message before consulting the prior cache. Available raw capture files and required raw envelope shapes are still checked before existing provenance and identity comparisons.

Partial status alone remains neither a rejection nor an acceptance criterion. A producer-generated partial snapshot with every detail-status row remains mergeable, including failed/empty rows, unavailable English lookup names, and requests that fail before storing raw content. The producer declares a path before requesting; an entry with `status: failed` and **no `sha256` key** represents no declared stored capture and cannot support an accepted detail. A declared hash is always checked, including failed captures. Captured details require a materialized path/hash; references to an unmaterialized failure are rejected. This closes the former `KeyError` on complete partial captures containing unmaterialized failed requests.

Original duplicate-source-ID rejection, reviewed-listing policy checks, raw inventory equality, detail request method/payload verification, source identity/faction/game checks, and compiled detail equality remain in place. Retained previous cache fields remain exact; existing intentional retention provenance is still added. Caller inputs and snapshots are not mutated by merge.

## Meaningful checks and exact accounting

Interpreter: `D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`. All runs use UTF-8, disabled bytecode writes, `-p no:cacheprovider`, and a fresh literal owned `--basetemp` directory.

Final focused command:

```powershell
& 'D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe' -m pytest tests/test_blacklibrary_snapshot.py tests/test_blacklibrary_snapshot_merge.py tests/test_blacklibrary_scope.py tests/test_blacklibrary_identity.py -q -p no:cacheprovider --basetemp='D:/Project/py/RAG/db_sources/blacklibrary-snapshot-boundary-owned/20261004/iteration-01/accepted-pytest-tmp' --junitxml='D:/Project/py/RAG/db_sources/blacklibrary-snapshot-boundary-owned/20261004/iteration-01/accepted.xml'
```

| Evidence | Tests | Passed | Failed | Errors | Skips |
| --- | ---: | ---: | ---: | ---: | ---: |
| `accepted.log` / `accepted.xml` | 125 | 125 | 0 | 0 | 0 |
| New checks using exact frozen parent merge, `parent-accepted.log` / XML | 59 | 4 | 55 | 0 | 0 |
| Intermediate `reviewed.log` / XML, retained without alteration | 125 | 121 | 4 | 0 | 0 |

XML testcase accounting is verified in `final-verification.json`. The focused final run includes **66 existing checks and 59 new checks**; no new skips or exclusions were added. The paired parent run selects only the new checks and deselects 11 existing merge checks. Its failures demonstrate the former incidental exception or non-fixed boundary message, and four complete-partial controls already work on the parent. They are not a claim of 55 separately exploitable defects.

New coverage includes actual `Snapshot.run()` with an injected `PermissionError(13, ...)` at the details file replacement boundary followed by actual merge; 50 malformed/incomplete manifest, output, row, raw-envelope and reference controls, including hash-correct malformed bodies; one full two-ID partial snapshot with a wrong-identity failed row plus a captured row; four actual producer-to-merge exhausted request failure controls at detail/rule/power/catalog boundaries; and three producer-generated unavailable-name controls. Assertions check safe failure text, byte-preserved snapshot files, unchanged input records, exact previous field retention, and continued rejection of accepted references without provenance. The injected write failure does not reproduce or explain the original OS failure.

The intermediate run retained two ordinary fixture captures with `error: PermissionError`, reconciled units and no details declaration: `reviewed-pytest-tmp/test_valid_merge_retains_absen0/snapshot/` and `reviewed-pytest-tmp/test_malformed_or_incomplete_o0/snapshot/`. It also had two malformed-name test targeting mismatches: the independent raw-inventory equality guard rejected them before the intended consumed-field guard. The tests now keep raw and compiled inventories equal, with updated hashes, to reach that guard; malformed-case setup explicitly asserts a complete capture. No retry, fallback, or OS workaround was introduced. The fresh 125-pass run does **not** establish a flake-free filesystem or resolve either spontaneous failure's unknown cause.

Generic and Python reviewers independently identified the initial field/reference and legitimate-partial gaps, then approved the corrected boundary implementation. Python review also approved the final test targeting correction. AST parsing of both changed Python files and `git diff --check` pass. No project Python formatter/linter configuration was found; Ruff, mypy, pylint and Black are unavailable in the designated environment. No packages were installed.

## Preservation and source bindings

`before.json` freezes actual parent source bytes and **19,704 files** across the owned source/test bindings and selected asset/evidence directories. `after.json` and `final-verification.json` verify **19,702 unchanged files**, with exactly the two intended source/test files changed. All **19,700 frozen directory files** remain byte-identical: `db`, `data`, `data_refined`, `local_vector_store`, `wiki`, `wiki_build`, `opt`, active `db_sources/blacklibrary`, and the retained listing-review evidence tree. This includes **2,806 original listing-review evidence files**, including the original failure log/XML/partial snapshot. No frozen file was removed and no active directory file was added.

During the run, 39 additional files appeared in the separate `host-python-review-dd1d/` evidence directory. They were left untouched; their paths are recorded separately in `directory-and-policy-verification.json`. They are not outputs of this iteration and are not represented as frozen originals.

| Binding | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| Merge module | `2419808051dd7371bc76159fc781a8fcc0a871c4eb6c06e8687f4c2032daf687` | `ad71f5bf1edd76147e8a60328aa964859f71c17bffe5e4708560d6dc783a07d7` |
| Snapshot fetch script | `91e4ed7cdc825df57b0cb6554a004d74e718e586fba20df1c21af5ae05e36567` | unchanged |
| Existing policy implementation | `fa7f569187e139a3cacbf2ae913c7d82a2f15a1f053ef61418911785e000f785` | unchanged |

Current listing policy SHA-256 remains `37b52cf122278a243951e9229f2a16365ff2e0e450a5b611dddf571f1dc2e864`, matching the retained listing-review report. Git diff against the parent is empty for policy, scope, and identity modules. Existing merged-source evidence remains preserved; this iteration does not claim to rerun its broader checks. `intended-source-test.diff` preserves the reviewed patch. Test hashes and every frozen file binding are in the JSON evidence.

## Remaining work and publication handoff

The next bounded iteration should implement only the authorized redacted local filesystem diagnostic seam in `scripts/fetch_blacklibrary_snapshot.py`: known phase/operation/controlled relative path plus whitelisted class/errno/winerror, preserving primary failure semantics and recovery even if diagnostics fail. It should add actual catalog/raw/details write failures through `Snapshot.run()`, actual merge and nonzero CLI controls, plus diagnostic-error precedence and recovery checks. Do not infer a scanner, handle, race, or other cause for the original or intermediate spontaneous `PermissionError`.

Commit completion and a clean intended source/test/report checkout remain GNHF's post-iteration responsibility. Independent host review/publication and the full objective's stop condition remain pending. No project, deployment, full-suite, or source-coverage completion is claimed.

The implementation iteration initially kept external notes untouched under its ownership restriction. The explicit subsequent stop hook authorizes the local knowledge handoff below. A dedup search in the existing project commit notes, RAG error notes and learning wins/deadends/decisions found no snapshot-boundary record; existing SQLite `PermissionError` records concern different verified seams and are not combined with this unknown failure.

## Explicit stop-hook knowledge handoff

The local English handoff appends this bounded outcome, evidence, checks and remaining diagnostic work to `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`. It adds `C:/Users/Administrator/learn-notes/decisions/20261004-validate-complete-partial-snapshot-manifests.md` and `C:/Users/Administrator/error-notes/rag/20261004-error-15-incomplete-snapshot-merge-keyerror.md`, with their README index entries. The error record includes the complete retained merge failure and records only the corrected merge boundary as resolved; the original and later spontaneous `PermissionError` causes remain unresolved.

Existing note bodies and repository Git indexes are preserved. No current implementation commit exists, so no new `commits/` explanation is created. GNHF retains implementation commit ownership; root publishes intended notes after writers finish. No manual staging/commit/push, harness promotion, new source/test change or repeated test run occurs during this handoff. Verification is retained under the evidence root's `knowledge-handoff/` directory. Orchestrator notes remain untouched.

## October 4 redacted filesystem diagnostic completion

This continuation starts from clean `db5cc0ea5fc8d1ee21897a0297e21dcaeb2d0355` and implements the previously pending diagnostic seam only. It changes `scripts/fetch_blacklibrary_snapshot.py`, adds `tests/test_blacklibrary_snapshot_diagnostics.py`, and appends this report. The existing merge, scope, identity, policy and source assets remain unchanged. The prior 125-test boundary proof above remains valid; no boundary reimplementation, full-project tests, network, models, dependencies, services or production writes were performed.

Evidence: `D:/Project/py/RAG/db_sources/blacklibrary-snapshot-boundary-owned/20261004/iteration-02/`. The same designated full-stack Windows Python interpreter, UTF-8, disabled bytecode and cacheprovider, and literal owned temporary directories are used. TEMP/TMP also point inside this iteration's evidence directory.

### Diagnostic contract and unchanged failure semantics

Actual `write_json` directory creation, temporary-file write and atomic replacement now observe `OSError` without changing the write sequence or retrying. The original exception object is re-raised even if the observer fails. Snapshot writes record the controlled pipeline phase and known operation; directory creation reports the actual relative parent directory (`.` means the snapshot root), temporary writes report the controlled `.json.tmp` path, and replacement reports the controlled destination. Known filenames, catalogue labels and generated hash/page paths are allowlisted. Other filesystem failures caught by the existing run boundary retain the known phase and codes without inventing an operation or path.

The optional manifest/CLI `filesystem_error` contains only an allowlisted phase, operation and relative path, a builtin class label, and exact integer errno/winerror when available. Custom exception class names, exception text, exception filenames, external cache paths, requests, responses, headers and account/credential fields are not diagnostics. The pre-existing CLI summary's user-selected output path is unchanged; it is separate from the new diagnostic object. A control whose filesystem exception `__str__` raises verifies that the diagnostic path never reads exception text. Noninteger codes and uncontrolled names are omitted.

The existing `run()` exception boundary, partial result, checkpoint recovery, nonzero CLI result and HTTP retry catch remain in place. Initial and final checkpoint failures retain their pre-existing propagation semantics. Diagnostic observer/builder failures cannot replace the primary error: phase-only fallback is used if available; if diagnostic construction entirely fails, the original safe class/partial manifest and CLI exit 1 still survive. Resume clears stale error/diagnostic state. No new retry, fallback for source content, or OS workaround is introduced.

### Actual filesystem and CLI acceptance

Twenty new controls cover nine actual catalog/raw-inventory/details output failures at `Path.mkdir`, `Path.write_bytes` and `Path.replace`, with `PermissionError` errno 13/winerror 5; phase-only resumed raw reads and external historical-cache reads; observer/builder failures; an actual OS replacement failure on a directory; custom-class/text/path/code redaction; and three fresh-interpreter snapshot CLI controls. The CLI controls also invoke the actual merge CLI: incomplete snapshots fail with the existing fixed ValueError, exit 1, and create no staging directory. Each of the nine output-failure controls uses the real `Snapshot.run()` and merge path; recovery preserves completed output/raw bytes and previous cache fields. Synthetic active-cache files and caller inputs remain exact. The shared-root details-directory injection is one-shot so the partial manifest can use the same directory; other operation counts and request-attempt assertions independently verify absence of retries.

Final combined command:

```powershell
& 'D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe' -m pytest tests/test_blacklibrary_snapshot_diagnostics.py tests/test_blacklibrary_snapshot.py tests/test_blacklibrary_snapshot_merge.py tests/test_blacklibrary_scope.py tests/test_blacklibrary_identity.py -q -p no:cacheprovider --basetemp='D:/Project/py/RAG/db_sources/blacklibrary-snapshot-boundary-owned/20261004/iteration-02/reviewed-pytest-tmp' --junitxml='D:/Project/py/RAG/db_sources/blacklibrary-snapshot-boundary-owned/20261004/iteration-02/reviewed.xml'
```

| Retained evidence | Tests | Passed | Failed | Errors | Skips |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial `focused.log` / XML | 17 | 16 | 1 | 0 | 0 |
| Intermediate `accepted.log` / XML | 144 | 142 | 2 | 0 | 0 |
| Intermediate `final.log` / XML | 144 | 143 | 1 | 0 | 0 |
| Reviewed combined `reviewed.log` / XML | 145 | 145 | 0 | 0 | 0 |
| Final strengthened diagnostic controls `final-diagnostics.log` / XML | 20 | 20 | 0 | 0 | 0 |

The final diagnostic-only run follows a test-only strengthening: one-shot injection is restricted to the shared-root details-directory case, with independent request-attempt assertions. No source changed after the combined 145-pass run. XML accounting is verified in `verification.json`; no skips or exclusions were added. AST parsing and `git diff --check` pass. Generic and Python reviewers approve. Ruff, mypy, pylint and Black remain unavailable; no formatter/linter dependency was installed.

### Preserved failures and limits

The initial diagnostic test mis-targeted the shared root mkdir at the first manifest checkpoint; the intermediate version also injected it again during final recovery. The corrected fixture uses inline detail content to reach the actual details output and permits the final partial checkpoint. These are retained fixture failures, not diagnosed production defects.

Two existing complete-fixture setups also spontaneously returned partial during these runs. Their unchanged retained manifests now honestly identify `PermissionError`, errno 13/winerror 5, `replace`, and `manifest.json`: catalogs phase at `accepted-pytest-tmp/test_malformed_or_incomplete_o17/snapshot/`, and details phase at `final-pytest-tmp/test_incomplete_rows_and_captu3/snapshot/`. This newly identifies the failed operation/phase in those two captures; it does not identify the underlying OS cause. No scanner, handle, race or other explanation is asserted. Original and all intermediate spontaneous PermissionError causes remain unknown. The injected controls and later passing runs do not establish that those causes are resolved or that the filesystem is flake-free.

`before.json` and `verification.json` bind the clean parent, intended source/test/report changes, unchanged merge/policy/identity files, active SQLite and canonical Black Library JSON bytes, original failure log/manifest, and earlier XML. No large asset/model/archive copy was made. Earlier logs/XML/partial snapshots remain preserved. Local knowledge handoff appends this verified continuation to the existing boundary checkpoint/roadmap, learning decision and error record, preserving their old bodies and other owners' staged indexes. No duplicate error/learning record, invented implementation commit or manual Git staging/commit/publication is created.

The finite diagnostic implementation and narrow control acceptance are complete locally. GNHF still owns the intended commit and clean checkout; root owns independent host review/publication. The clean-commit stop condition cannot be claimed before that orchestrator step. No overall project, deployment or source-coverage completion is claimed, and no background process started by this continuation remains running.
