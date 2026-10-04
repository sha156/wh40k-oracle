# Supported setup and collection boundary — October 4, 2026

## Iteration 1: CI declaration and root collection

The CI declaration now selects CPython 3.11 and the reviewed dependency files.
Default repository-root pytest collection is restricted to `tests/` with no
added ignore, skip or deselection. On this exact candidate, default and explicit
collection have **4,574 identical ordered nodes**, zero collection errors and
zero collection skips. This is a verified configuration increment, not final
supported-setup or integrated application acceptance.

The managed checkout began clean on `codex/release-supported-setup`, head
`b887a351fec1ab54408d09df8a7e23dff3778a1d`. The orchestrator notes contained no
previous iterations. The host acceptance plan and actual dependency report,
requirements/bootstrap, Dockerfile and Compose configuration were read.
Only the workflow, new `pytest.ini` and this report are intended source changes.
No manual commit, installation, environment modification, asset mutation,
network request, model execution, service start or publication was performed.
GNHF owns commits; root owns independent review and final integration.

### Configuration changes and verification

- `.github/workflows/ci.yml` selects Python `3.11`, keys its pip cache on
  `requirements*.txt` and `constraints-python311.txt`, installs the exact
  `requirements-bootstrap.txt` first, then uses its build constraint and the
  shared constraints with `requirements-ci.txt`. All pip and pytest entry
  points use `python -m`; the install job also runs `python -m pip check`.
- The existing `--ignore=tests/test_app_retrieval.py` remains the sole explicit
  CI import boundary. No model package/download or local-asset substitution
  was added. Frontend steps, event triggers and Ubuntu runner are unchanged.
- `pytest.ini` contains only `[pytest]` and `testpaths = tests`. Explicitly
  requesting another path remains possible; retained snapshots are not deleted.

The workflow was parsed as YAML. A verification script asserts the exact four
Python job commands, cache inputs, unchanged frontend/triggers/runner, and the
minimal pytest configuration. It follows the five actual CI requirement files
and checks every direct pin against the unchanged **134-pin** constraints.
This is declaration consistency verification, not a repeated closure install
or installed-tree security audit. Previously retained complete-family results
remain in [the dependency report](2026-09-30-python-security-acceptance.md).

Actual installed SQLAlchemy **2.1.1** declares `Requires-Python: >=3.11`.
Its metadata accepts 3.11.9 and rejects 3.10.12, confirming the old CI version
was incompatible. No requirements, pins, runtime guards or capture report were
edited to make the workflow compatible.

### Exact collection accounting

All checks use the existing interpreter:

```text
D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe
```

It reports CPython **3.11.9**. All new temporary files, caches, logs, XML and
verification scripts are retained under:

```text
D:/Project/py/RAG/db_sources/supported-setup-owned/20261004/iteration-01/
```

Before editing, root `-m pytest --collect-only -q` collected **4,574 nodes**,
exit 0, in 29.97 seconds. The archived-review 187-error failure recorded in the
October 1 retirement report does **not** reproduce in this managed checkout.
It remains historical evidence rather than a claimed fresh failure.

After editing, root and explicit `tests/` collection both use
`--collect-only -q -rs`, distinct owned cache/basetemp paths and a read-only
collection-recording plugin. They exit 0 in 30.59 and 30.35 seconds. The plugin
records every node identity and each existing skip/skipif condition and reason.
Verification establishes exact ordered record equality, unique identities,
all paths under `tests/`, and equality to the pre-edit node list. No collected
node is lost or added. The **444 nodes with conditional skip marks** are not
444 executed skips: collection does not execute those conditions or fixtures.
No full native pass or full-suite runtime skip accounting is inferred.

A separate synthetic directory under the owned evidence path contains one
current test and one retained-snapshot module that raises during import.
Actual root pytest without the configuration exits **2** on that archived
module; copying the candidate `pytest.ini` makes root collection exit **0**
with exactly the current node. This is a paired configuration control, not
production source or additional application coverage.

### Focused regressions and preserved failures

The selected native run executes SQLite build lifecycle, synthetic PDF/vector
ingestion, framework/provider protocols, API Origin and deployment controls,
strict benchmark JSON, offline qualification, and the formerly asset-dependent
negative keyword-parser fixture. The command is:

```powershell
$owned = 'D:/Project/py/RAG/db_sources/supported-setup-owned/20261004/iteration-01'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:TEMP = $owned
$env:TMP = $owned
$checkedPython = 'D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe'
& $checkedPython -m pytest -q -rs `
  tests/test_db_compile_build_lifecycle.py `
  tests/test_ingest_pages.py tests/test_ingest_vector_reuse.py `
  tests/test_dependency_framework.py tests/test_web_api_origin_boundary.py `
  tests/test_web_api_stage5_deploy.py tests/test_benchmark_strict_json.py `
  tests/test_qa_benchmark_boundaries.py `
  tests/test_wiki_keyword_index.py::test_parse_quickref_too_few_entries_raises `
  -o "cache_dir=$owned/focused-cache" --basetemp "$owned/focused-temp" `
  --junitxml "$owned/focused.xml"
```

| Focused module | Passed | Failed |
| --- | ---: | ---: |
| SQLite build lifecycle | 11 | 0 |
| PDF ingestion / vector reuse | 11 | 0 |
| Framework / provider chain | 4 | 0 |
| API Origin boundary | 26 | 15 |
| API deployment / preflight controls | 44 | 0 |
| Strict benchmark JSON | 67 | 0 |
| Offline benchmark qualification | 13 | 0 |
| Negative keyword-parser fixture | 1 | 0 |
| **Total** | **177** | **15** |

There are **zero skips, zero errors and three deprecation warnings**, exit 1,
23.76 seconds. The original configuration is represented by an external empty
`[pytest]` file passed with `-c` and the explicit current repository `--rootdir`.
The same selected paths on unchanged HEAD application/test code give **177
passed / 15 failed / zero skips / zero errors**, exit 1, 32.23 seconds. XML
comparison establishes exact case identity, outcome and skip-reason equality.
All 15 failures are in the existing Origin tests; nothing was ignored or
weakened to obtain a green result.

The failing tests send raw JSON via `content=...` without an application/json
Content-Type. A direct, in-process `/chat/sync` probe with a synthetic handler
reproduces HTTP **422**, zero handler calls and:

```text
type: model_attributes_type
loc: [body]
msg: Input should be a valid dictionary or object to extract fields from
```

The otherwise identical request with `Content-Type: application/json` returns
HTTP **200** and one handler call. The failure is therefore not introduced by
test discovery; API/test-contract reconciliation belongs to root integration.
This increment does not alter those tests or the API and does not claim the
broader focused run passed. No real provider or server was used by the probe.

### Evidence, preservation and remaining work

The evidence directory contains `baseline-root.log`/`.exit`, both
`collect-*.json`/`.log`/`.exit`, `configuration-verification.json`,
`collection-control.json`, paired `control-*.log`, `focused.xml`/`.log`/`.exit`,
`focused-baseline.xml`/`.log`/`.exit`, `focused-comparison.json`, and
`origin-content-type-probe.json`/`.log`. The scripts preserve exact failed
case identities and existing conditional skip reasons for review.

`readonly-inputs-before.json` binds **35 files**: the 10 requirement files,
constraints, dependency report, and 23 retained iteration5 evidence/tool files.
All 35 remain byte-identical. No working environment, production asset,
concurrent checkout, orchestrator notes or shared knowledge index was changed.
The actual diff and whitespace checks pass. All tool-started pytest processes
have completed; no background service or watcher was started.

Verified learnings for the next handoff: the clean managed checkout already
collects its current real nodes successfully, although archived snapshot
collection remains reproducibly unsafe without `testpaths`; existing Origin
fixtures expose a raw-body Content-Type mismatch on the supported stack,
independently of the new configuration. These are finite recorded findings,
not new full-stack acceptance claims.

Next setup work remains README correction for the actual CPython 3.11 bootstrap,
asset acquisition/build prerequisites and local-release limits, plus real
PowerShell launcher unsupported/missing-interpreter, argument-forwarding and
exit-code controls. Root must reconcile the API fixture failure, review the
candidate, and own fresh hosted CI and final integrated actual-asset/native,
Docker/browser/115-question benchmark acceptance. The current 3,404-document
index is separate from the dependency report's archived 5,905-document model
compatibility evidence. No current full-Codex parity, source promotion,
deployment or whole-objective completion is claimed. No manual commit or push
was made; the intended files are left for GNHF's automatic commit.

### Explicit stop-hook knowledge handoff

The hook's duplicate search found existing records for both archived-root
collection and FastAPI's strict Content-Type behavior. The project checkpoint
and roadmap at `D:/Project/devlog/wh40k-oracle/` now record this increment,
its exact checks and remaining setup/root gates. Two existing learning decisions
were extended: platform/dependency acceptance and Origin execution controls.
The existing archived-pytest error note records the verified persistent
`testpaths` correction and full synthetic-control error. The unresolved Origin
fixture failures remain open; no duplicate or falsely resolved issue was created.

All five original note prefixes, 456 unrelated Markdown files and three shared
Git indexes remain exact. Existing indexes already link the extended records;
none was rewritten. No manual staging, commit, push, fictional commit explanation
or harness promotion was performed. Before copies, appended-note hashes and
verification are retained in the evidence directory's
`knowledge-handoff/verification.json`. Root retains knowledge publication.

## Iteration 2: supported native launcher

The next individually verifiable increment changes only `run_streamlit.ps1`
and this report. The iteration began clean at `c681b75fb` after reading the
orchestrator notes. CI requirements, constraints, collection configuration,
application/test source, environments and runtime assets remain unchanged.
README setup/acquisition corrections and final root integration remain pending.

### Launcher behavior

The launcher requires a file at its existing project-relative
`.venv/Scripts/python.exe` path. Before importing Streamlit, it runs that
interpreter to check `sys.implementation.name` and the major/minor version.
Only working CPython 3.11 proceeds; missing executables, directory impostors,
failed probes and unsupported runtimes fail visibly with exit 1. It does not
fall back to another interpreter or use the preserved historical environment.

The application entry remains `-m streamlit run app.py`, with the project root
as its working directory and caller arguments following `app.py`. Explicit
Windows argument encoding preserves empty strings, whitespace, embedded quotes
and backslashes on both PowerShell generations. The child inherits its standard
streams, is awaited and disposed, and its actual exit code is returned. No
caller argument or environment value is included in the launcher's diagnostics.

### Real PowerShell controls and limits

All temporary fixtures, C# source/executable, scripts, argument records, logs,
JSON and pytest XML/cache/basetemp files are under:

```text
D:/Project/py/RAG/db_sources/supported-setup-owned/20261004/iteration-02/
```

`verify_launcher.py` uses installed Windows PowerShell **5.1** and PowerShell
**7.6.5**, with copied launcher scripts in directories containing spaces and
Chinese characters. Its small fake executable occupies only the fixture's
expected interpreter entry point. For the version probe it executes the exact
launcher-supplied Python code through the existing supported CPython **3.11.9**
interpreter listed above. Negative cases replace the version/implementation
attributes only within that subprocess, or return a probe error. The application
entry records received arguments/working directory and returns a chosen code;
it does not import Streamlit, start a server, load a model or contact a provider.
These are real launcher/process controls with synthetic application execution,
not full Streamlit or actual-asset startup acceptance.

The final harness exercises each case through an array-splat caller that
explicitly returns `$LASTEXITCODE`, and independently through direct
`powershell/pwsh -File run_streamlit.ps1`. The direct invocation is necessary:
a surrounding script can otherwise hide the nested script's exit code. Final
results are **40 passed / zero failed / zero skipped**:

| Control per shell and invocation | Result |
| --- | --- |
| Missing executable or a directory at that path | Exit 1; application never reached |
| CPython 3.9, 3.10 or 3.12; PyPy 3.11 | Exit 1; application never reached |
| Interpreter probe exits 19 | Launcher exits 1; application never reached |
| Supported interpreter, application exits 0 | Exact entry arguments and working directory; exit 0 |
| Supported interpreter, application exits 37 | Exact entry arguments and working directory; exit 37 |
| Supported interpreter, application exits 7 | Exit 7; caller's literal argument array preserved |

The literal array includes an empty string, `--`, a path with spaces, Chinese
text, embedded quotes, trailing backslashes, backslashes before quotes, a CRLF,
and literal `$`, semicolon and ampersand characters. Each is compared against
the argument received by the executable, without shell evaluation. Direct-file
controls use no additional arguments and independently verify exit propagation.

The unchanged HEAD launcher is copied from the preserved pre-edit fixture,
verified against its Git blob, and run through the same final controls. It has
**15 passed / 25 failed / zero skipped**. It starts the application for every
unsupported-runtime/probe-error case; direct-file execution incorrectly exits
0 when the application exits 7 or 37. Windows PowerShell 5.1 also loses the
empty argument/embedded quotes and merges later arguments in the literal test.
PowerShell 7's native forwarding passes that array, but still fails direct-file
exit propagation. Missing-interpreter controls already failed correctly before
the change; they are retained as positive guards.

The earlier harness attempts and their logs are retained separately. They used
an array expression as one script argument, then omitted the caller's explicit
exit, so their aggregate outcomes are not acceptance evidence. Correcting the
harness and adding direct-file controls produced the paired results above;
no launcher or application assertion was weakened to hide an actual failure.

### Focused checks, preservation and handoff

The existing supported interpreter ran unchanged SQLite build lifecycle,
framework/provider-chain tests and the standalone negative keyword-parser
fixture: **16 passed / zero failures / zero errors / zero skips**, with two
upstream LangChain deprecation warnings, in 26.56 seconds. The retained command
is `-m pytest -q -rs tests/test_db_compile_build_lifecycle.py
tests/test_dependency_framework.py
tests/test_wiki_keyword_index.py::test_parse_quickref_too_few_entries_raises`,
with owned cache/basetemp and `--junitxml` paths. The earlier 15 Origin fixture
failures remain recorded and unresolved; this launcher increment does not
reclassify the broader focused suite as passing.

PowerShell AST parsing and actual diff/whitespace review pass. No permanent test
skip, ignore, deselection or assertion change is introduced. The existing 4,574
node equality evidence remains the iteration-1 collection result; no fresh
full collection or full native suite is claimed here. All 35 previously bound
requirement/constraint/dependency-report/retained-evidence files remain exact.
All fixture processes completed; the final owned-process check found none.

The deduplicated handoff extends the project checkpoint/roadmap, the existing
platform acceptance learning decision, and the existing PowerShell quoting and
process-exit error records. Original note bodies and shared Git indexes are
preserved. No new placeholder note, manual staging/commit/push, harness change
or orchestrator-note edit is made. Verification and before copies are retained
in `iteration-02/knowledge-handoff/`; root owns knowledge publication.
The final recheck detected another owner's insertion into earlier rebuild
sections of both shared project notes and updates to its roadmap task statuses.
Those changes remain untouched; this iteration's appended sections remain
byte-exact. Shared indexes and all 35 read-only inputs are
still unchanged. The handoff manifest distinguishes this concurrent insertion
from the original byte-exact prefix verification at the time of writing.

Remaining setup work is the README's supported CPython 3.11 bootstrap,
acquisition/full-build prerequisites and accurate finite local-release limits.
Root still owns Origin fixture/API reconciliation, independent generic/Python
review, fresh hosted CI and integrated actual-asset/native/Docker/browser/
115-question benchmark acceptance. GNHF owns the automatic scoped commit.
The supported-setup stop condition and whole-project acceptance are not met.
