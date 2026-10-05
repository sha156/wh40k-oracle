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

## Follow-up iteration 1: authorized Origin fixtures on CPython 3.11

This follow-up began clean at `347f50ce9734c5fb4bd3d46b54e0295c26b63305`
on `codex/release-supported-setup`. Its individually verifiable scope is the
fifteen confirmed authorized-request fixture failures, new strict body-contract
controls and this report. README correction remains a separate next increment.
No application, Origin middleware, provider, dependency, launcher, CI or
collection configuration is changed. GNHF owns the automatic scoped commit;
root owns independent review and release publication.

### Request contract and unchanged execution boundary

The actual frontend sends `Content-Type: application/json` and serialized JSON
in `web/src/lib/api.ts`, `web/src/lib/sim.ts` and `web/src/lib/roster.ts`.
The original positive fixtures instead sent the same JSON through `content=`
without Content-Type. On the unchanged supported stack, FastAPI correctly
rejects those bodies with 422 before invoking the substituted handler.

`tests/test_web_api_origin_boundary.py` now explicitly types only the original
six authorized chat requests and nine authorized compute requests. Their
payload, invocation, stream, CORS-header and legitimate handler-error assertions
are preserved. In particular, compute handlers still return their intentional
409 error with exactly one invocation and the original error detail. No status
assertion is relaxed and no application parsing setting is changed.

The two foreign chat requests and three foreign compute requests remain raw
JSON bytes with **no Content-Type**. Each verifies 403 and zero handler calls;
the compute cases now also explicitly verify the absent request header.
Malformed/duplicate Origin rejection, forged Host quota classification,
preflight quota and the direct ASGI no-body-read/no-inner-app assertion remain
unchanged. The existing selected deployment/body-limit controls also pass.

Two new parametrized tests compare identical serialized payloads across all
five real routes (`/chat`, `/chat/sync`, `/simulate`, `/roster/critique`,
`/roster/validate`), both allowed UI origins and no Origin:

| Request body contract | Cases | Required result |
| --- | ---: | --- |
| Explicit `application/json` | 15 | HTTP 200; exactly one harmless handler invocation |
| Content-Type absent | 15 | HTTP 422 body-validation error; zero handler invocations |
| `text/plain` with the same JSON bytes | 15 | HTTP 422 body-validation error; zero handler invocations |

All 45 cases assert the actual request Content-Type and expected CORS response
header. Typed chat controls check the SSE completion event or degraded answer;
typed compute controls check their synthetic contract-valid result fields.
The compute fixtures use only a temporary empty file to satisfy the existing
database-presence gate, with engines substituted; no production DB or numerical
simulation is exercised. This proves body parsing and Origin authorization
remain separate controls, rather than claiming a real provider or asset pass.

### Paired baseline and complete selected regression accounting

The unchanged parent test file was copied before any edit. Its fresh exact
module run gives **26 passed / 15 failed / zero errors / zero skips**, exit 1,
in 1.44 seconds, matching all 41 module case identities and outcomes in the
retained iteration-1 full-selection XML. The failures are the six chat and nine
compute authorized controls; the original failed XML and earlier probe are
preserved. The supported interpreter and dependencies are unchanged:
CPython **3.11.9**, FastAPI **0.133.0**, Starlette **1.3.1**, HTTPX **0.28.1**,
pytest **9.1.1**.

The candidate reruns the exact previous selection, with only the additional
45 strict Content-Type cases:

```powershell
$owned = 'D:/Project/py/RAG/db_sources/supported-setup-owned/20261004/iteration-03'
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
  -o "cache_dir=$owned/candidate-focused-cache" `
  --basetemp "$owned/candidate-focused-temp" `
  --junitxml "$owned/candidate-focused.xml"
```

The baseline command uses the same interpreter/environment and
`-m pytest -q -rs tests/test_web_api_origin_boundary.py`, with separate
`parent-origin-cache`, `parent-origin-temp` and `parent-origin.xml` paths.

| Selected module | Passed | Failed / errors / skipped |
| --- | ---: | ---: |
| SQLite build lifecycle | 11 | 0 / 0 / 0 |
| PDF ingestion / vector reuse | 11 | 0 / 0 / 0 |
| Framework / provider protocol | 4 | 0 / 0 / 0 |
| API Origin and strict body contract | 86 | 0 / 0 / 0 |
| API deployment / preflight / body limits | 44 | 0 / 0 / 0 |
| Strict benchmark JSON | 67 | 0 / 0 / 0 |
| Offline benchmark qualification | 13 | 0 / 0 / 0 |
| Negative keyword-parser fixture | 1 | 0 / 0 / 0 |
| **Total** | **237** | **0 / 0 / 0** |

The candidate exits 0 in **32.52 seconds**, with the same three upstream
deprecation warnings. XML comparison confirms all **192 original selected
cases** remain present and pass; all **41 original Origin cases** pass. Exact
pytest node IDs, all 15 parent failures, per-case XML outcomes and the empty
skip-reason list are enumerated in `origin-fixture-verification.json`.
AST comparison confirms every original assertion remains and every original
function other than the two authorized-positive fixtures is unchanged,
including the foreign chat and direct no-body-read guards. No new skip, ignore,
deselection or changed regression module is introduced. The first evidence
summary script omitted the closing bracket when counting trailing JSON
parameter IDs; the corrected summary normalizes it and proves the 15/30 split.
The initial script is preserved; this did not affect any pytest result.

### Preservation and remaining gates

All temporary scripts, parent copies, caches, logs, exit records, XML and
verification JSON are confined to the iteration-03 evidence directory. All
**35** bound dependency/report/proof inputs remain byte-exact. The tracked-file
manifest confirms only this test file and this report change; all **5,743 other
tracked files** remain exact, including README, launcher, CI, requirements,
application/security source and tracked wiki. Orchestrator notes are unchanged.
Diff/whitespace and source syntax checks pass. Ruff and Black are unavailable in
the selected environment; no standalone formatter/linter result is claimed.
No installation, audit, full QA, provider/model execution, network
request, server start or production mutation is performed; pytest processes
have completed, and no background service was started.

The deduplicated project checkpoint/roadmap and existing Origin learning/error
records receive the actual fixture resolution and exact selected-suite result;
their original bodies, **464 unrelated Markdown files** and three shared Git
indexes are preserved, as recorded in `knowledge-handoff/verification.json`.
No duplicate placeholder,
manual stage/commit/push or cross-project harness promotion is introduced.
Root retains knowledge publication and independent generic/Python/security
review. Earlier sections describing these fifteen fixture failures as unresolved
are historical and superseded by this follow-up's paired evidence.

Next work remains the README's supported CPython 3.11 CPU bootstrap and full
asset acquisition/build prerequisites, source-authority and finite release
limits. Fresh hosted CI and integrated full native/actual-asset, Docker/browser
and 115-question benchmark acceptance remain root gates. This bounded fixture
pass does not establish whole-project acceptance, new source completeness,
deployment or publication. The supported-setup stop condition remains unmet.


## Iteration 4: README supported setup and acquisition reconciliation

The documentation-only follow-up begins at clean
`837db79fcfabe63b9c312686915af31258049b49` on
`codex/release-supported-setup`. It completes the previously pending README
work: only [README.md](../../../README.md) and this appended section are
intended repository changes. The earlier CI, launcher, fixture, application,
security, test and dependency work is retained unchanged. No manual staging,
commit, push, merge or publication is performed; GNHF owns the intended
README/report commit and clean-checkout closure, and root owns independent
host review and release integration.

### Supported commands and actual acquisition boundary

The obsolete Python 3.9 requirement, bare interpreter/installer commands,
unconstrained install and implication that PDF ingestion supplies the entire
website are replaced. Windows creates a new virtualenv with the known full
CPython 3.11 installation and then uses the absolute project executable with
`-m pip`; Linux explicitly uses `python3.11` and its absolute project executable.
Bootstrap is the existing pip 26.2.1/setuptools 83.0.0 declaration, followed by
the dedicated torch 2.14.0+cpu index step and the complete native set with build
constraints and shared CPython 3.11 constraints. The pip 25.3 minimum for the
build-constraint option explains why bootstrap comes first. These commands
were declaration-verified, **not newly installed or install-tested** here.

The README describes local native/Compose startup, locked `npm ci` and actual
package scripts. Next.js 16.3.7's lock metadata declares Node >=20.9.0;
Node 22 matches the existing frontend Dockerfile. The separate unit-test
strip-types flag requires an appropriate Node release beyond Next's minimum.
Native Uvicorn explicitly loads `.env`; the copy guard preserves an existing
local file. Only empty-key/template configuration is documented.

The canonical downloader's actual tuple contains exactly `Factions.csv` and
`Datasheets.csv`. The README adds a separate staging example for the other
nine exports using that same implemented Wahapedia base URL, including explicit
PowerShell proxy forwarding/basic parsing. The eleven actual `csv_dir` consumers
are enumerated with their purpose; no nonexistent composition or relationship
CSV is invented. Composition/count/loadout/leader/source-link prerequisites
are tied to the retained fields, costs and reviewed community details.
`Enhancements.csv` is a real build consumer but is absent from `EXPECTED_CSV`;
therefore the normal missing-file warning is insufficient to certify a full
build. `Wargear.csv` remains the implemented known-missing exception because
weapon data is inline in `Datasheets_wargear.csv`.

Full rebuild documentation also identifies retained official PDF/correction
proofs, terms, DSL, permitted refined inputs, community units/details/raw
provenance/identity and listing policies, mapping histories, complete MFM
source snapshot/raw HTML/manifests, BSData and download-catalogue baseline.
These ignored assets are not supplied by a code clone or the two-table fetch.
The native base build replaces SQLite only after a successful temporary-file
import, then restores authority layers offline. That broader restoration is
not one transaction; warnings/critical failures and partial table imports
remain visible. `update --offline` still rebuilds/writes. The documented
isolated-copy build/generation/retrieval sequence is not a claim that the
pending scheduled stage-only workflow is implemented or accepted.

The app's complete bge-m3 snapshot is passed by absolute path for CPU loading;
missing snapshots can fall back to online model-name resolution. Ingestion
still uses a model name with the local cache, so no universal offline guarantee
is made. Optional FlashRank remains disabled by default. Both FAISS components
and trusted-own pickle provenance are required. Docker mounts the existing
model/index/SQLite/wiki assets read-only and both services use loopback ports
and non-root users. Four mounts cover **five** preflight entries: model, vector
store, structured DB, wiki and keyword index. The last two are optional for
`ready`, so the README separately requires them for full UI acceptance, plus
actual warmup/vectorstore loading and a retrieval/card check. HTTP liveness
alone is not readiness. Compose currently does not forward the reduced
`WEB_API_RETRIEVAL` mode automatically.

### Dated source and release limits

The README preserves project branding, both existing artwork references,
feature descriptions and the answer-export behavior. Historical checkpoint
figures are explicitly dated instead of being presented as current acceptance.
Official GW core/dated field patches/MFM authority is distinguished from the
retained verified community Chinese layer. Retired fan-translation PDF inputs
must not be revived. The unavailable latest complete Space Marines/chapter
Codex bodies, price-only entries, public Ork previews and 47 unproven historical
canonical names remain explicit limits; no assets, rules, rights or new license
are invented.

The separate host candidate `dd1d23d2f514feaa23284768102a58b96f76c06e` was read
without merging or modifying it. Its actual policy gives 43 duplicate listings,
36 empty Legends listings and 15 other empty listings; all 94 exclusions bind
the complete individual sanitized own row and reopen on source change.
The actual October 4 capture/listing review still records four wrong-identity
responses; quarantine is not released. This fresh reviewed policy is not the
policy in this private setup checkout. The separate staged-update report's
copied raw/cache reconciliation gives 30 pages/3,635 complete MFM ledger rows,
captured `2026-10-03T19:00:56.192123+00:00` (October 4 local), with September 30
source context. Capture/printed/legal dates remain distinct, and no active
promotion or effective-date proof is inferred.

Independent generic/Python/security supported-setup/source review, final
scheduled stage-only wiring, full integrated actual-asset native acceptance,
local Docker/browser checks, the 115-question benchmark, fresh hosted CI and
publication remain **root release gates**. Cloud is deferred. This finite
README task makes no ongoing maintenance or universal zero-mistake promise.
Earlier report sections saying README reconciliation remains pending are
superseded by this appendix; earlier executed-suite evidence remains dated.

### Static verification and preservation

All new proof files are confined to:

```text
D:/Project/py/RAG/db_sources/supported-setup-owned/20261004/iteration-04-readme/
```

The existing complete CPython 3.11.9 environment runs only local documentation
verification scripts. `static-verification.json` records **233 passed checks**:
actual requirement inclusion/pin consistency, bootstrap/CPU/build ordering,
JSON package/lock scripts and Node metadata, parsed Compose YAML, ports/mounts/
users/proxies, AST/static CLI declarations and consumed CSVs, restoration and
model/preflight/warmup behavior, all README local Markdown links, preserved
artwork/branding, required tracked prerequisites and empty-key configuration.
It binds the actual source/requirement files by SHA-256. Assertions are
consistency checks, not additional application test coverage or runtime proof.

All **nine** PowerShell fenced examples parse with zero errors under the actual
Windows PowerShell **5.1.26100.9549** and PowerShell **7.6.5** parsers.
`D:/download/Git/bin/bash.exe -n` parses the Linux example with exit 0.
No documented command is executed by those parsers. An initial verification
script used the wrong duplicate reason enum, and an initial Bash invocation
assumed an absent executable path. Those verification-only failures and the
invalid inherited initial Bash exit record are retained explicitly; the
corrected verifier uses actual `duplicate_listing` and the verified executable.
No passing result is inferred from either initial attempt.

`production-before.json` freezes all **5,745 tracked files**, the managed Git
index, head and orchestrator notes before editing. `production-after.json` and
`preservation-verification.json` confirm exactly README and this report change;
all **5,743 other tracked files** are byte-exact, including all code, tests,
CI, launcher, dependencies, tracked wiki and other reports. The original
**26,504-byte report prefix** remains exact, as do the managed Git index and
orchestrator notes. The actual diff was inspected and `git diff --check`
passes. No requirement install, full/model/provider/native suite, network
request, asset mutation, server/browser/watcher or background process was
started. No such process needs cleanup.

The existing project CHECKPOINT/ROADMAP receive one deduplicated English
append with the actual README change, prerequisite findings, static checks
and remaining gates. Their original bodies, **470 unrelated Markdown files**
and three shared Git indexes are preserved; `knowledge-handoff/verification.json`
records the bindings. No new learning/error placeholder or duplicate runtime/
fixture note is created. Root retains knowledge publication after concurrent
writers finish. The README/report are ready for the authorized GNHF commit;
this pre-commit iteration does not claim the committed-clean stop condition
or whole-project release acceptance.
