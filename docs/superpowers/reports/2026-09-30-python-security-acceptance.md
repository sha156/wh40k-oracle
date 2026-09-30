# Python dependency security acceptance — September 30, 2026

Status: **incremental candidate, not release acceptance**. The shared
FastAPI/Starlette boundary, Requests, PyMuPDF and installation tooling are patched
and verified in isolation, with the setuptools legacy-path limitation below.
The unused ZhipuAI SDK requirement is retired while both GLM provider paths are
preserved and verified with synthetic responses through real provider clients.
The complete CPU application stack, full native suite, Docker/Linux installation
and final audit remain outstanding.
No integration, deployment, source retirement or main-environment changes occurred.

## Latest increment: unused provider SDK and PyJWT boundary — October 1, 2026

`requirements.txt` and `requirements-docker.txt` no longer install the unused
**zhipuai 2.1.5.20250825** SDK. The native declaration was previously unbounded;
the auditor found that exact version in both actual native and Docker inventories.
CI/server sets already omit it and are unchanged. GLM remains available through
the existing OpenAI-compatible clients: `app.py::get_llm` uses `ChatOpenAI`,
`agent/llm_client.py` uses `openai.OpenAI`, and `scripts/qa_bench.py` uses the
same provider endpoint. No provider choice, model, endpoint, application source,
test expectation or reliability-owned file changed.

An AST scan of **all 280 tracked Python files**, including scripts and tests,
found **zero zhipuai, jwt or pyjwt imports**. The accompanying textual scan
records provider references and dynamic import calls; the latter import `app`
or `re`, not these SDKs. The provider's
[official OpenAI compatibility guide](https://docs.bigmodel.cn/cn/guide/develop/openai/introduction)
and saved registry metadata support the existing client boundary. This change
removes an unused implementation dependency, not GLM functionality.

The SDK's exact metadata requires **PyJWT>=2.8,<2.9**. A real pip dry-run against
the clean provider subset still selects **PyJWT 2.8.0**, along with the SDK and
cachetools. It therefore cannot accept the reported 2.12/2.13/2.14 fixes. No
incompatible PyJWT constraint or forced `--no-deps` installation was introduced.
Both auditor baselines contain **15 PyJWT records / 11 underlying alias groups**
at 2.8.0. All full bodies and connected alias groups are saved; duplicate records
are not counted as distinct issues. Removing this dependency path is the scoped
resolution, not a claim that PyJWT itself is fixed.

**No-fix qualification:** **PYSEC-2025-183 / CVE-2025-45768** still has no fixed
version in the saved OSV record, which says the supplier disputes the weak-key
classification. The primary
[maintainer discussion](https://github.com/jpadilla/pyjwt/issues/1080) confirms
that position and links the later
[2.11.0 release](https://github.com/jpadilla/pyjwt/releases/tag/2.11.0), which adds
weak-key warnings and opt-in strict enforcement. The
[tagged implementation](https://github.com/jpadilla/pyjwt/blob/2.11.0/jwt/api_jws.py)
confirms `enforce_minimum_key_length` defaults to **False**. This is not evidence that the
registry's no-fix classification has been cleared. The application has no JWT
signing/verifying path; both clean installed subsets below contain **neither
PyJWT nor zhipuai**. No advisory was suppressed. The final full dependency tree
must still confirm absence or explain any new transitive JWT consumer.

Validation completed for this increment:

- New `clean-provider-venv`, created with the prescribed **Python 3.11.9**
  interpreter: bootstrap, then `requirements-server.txt` plus **openai 2.54.0,
  langchain-openai 1.1.14 and langchain-core 1.4.6**, installs successfully with
  the shared build constraint and passes `pip check`. Resolved **langsmith is
  0.14.2**. This has **51 distributions**, including pip/setuptools and no pytest,
  PDF or model dependencies. The explicit provider versions are **experimental
  subset pins**, not edits to the remaining full-stack LangChain requirements;
  this does not complete the LangChain migration or full install.
- Real `OpenAI` and `ChatOpenAI` calls through an in-memory HTTPX transport pass
  for **both DeepSeek and GLM**: exact endpoint/model, synthetic Bearer-key
  serialization, classification, JSON final content and citations, benchmark
  judging and streaming chunks. The unchanged `get_llm` function is compiled
  directly from its AST; no fake production SDK is installed. The agent and
  benchmark modules are imported normally. Real SDK **400 BadRequestError**
  triggers the existing retry without `response_format`; **429 RateLimitError**
  propagates after one transport call with SDK retries disabled for that probe.
  GLM receives no DeepSeek thinking field. All responses and keys are synthetic;
  no external inference, full app import, retrieval or model-quality claim is made.
  JWT, zhipuai, torch, sentence-transformers, FAISS and Streamlit stay unloaded.
- Project `.venv`: unchanged `test_llm_client.py`, `test_llm_refine.py` and the
  four API suites named in the earlier FastAPI increment pass **122 tests,
  28 skips, two warnings in 4.63 seconds**. The fresh provider environment,
  after separate **pytest 9.0.3 / PyMuPDF 1.26.7** test additions, passes the
  same **122 tests, 28 skips, one warning in 5.43 seconds** and `pip check`.
  JUnit attributes every skip to absent canonical SQLite. Existing deprecation
  warnings remain. No asset, source, expectation or skip changed.
- Isolated **pip-audit 2.10.1** queries every exact installed pin before test
  additions (**51**) and afterward (**56**): both exit **0**, with **zero findings
  and zero skipped packages**. Full raw JSON and alias-group outputs are saved.
  Tool-environment packages are separate. These are **clean provider-subset
  audits**, not a clean full native/Docker application audit. The test subset adds
  five distributions; production requirements gain no test dependencies.

Evidence is ignored and local under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-6/`:
source scan/probe scripts, official guide HTML and SDK README, exact registry
metadata, original auditor provider bodies and alias groups, OSV/maintainer
discussion/release/tagged-source evidence, bootstrap/provider/test installation reports and
logs, SDK dry-run report, before/after test-addition inventories and audit pins,
raw audits/logs/exit codes, both test logs/JUnit XML, provider-probe JSON and
`verification-summary.json`. `inspect-provider.py` and `summarize-evidence.py`
reproduce the scan, metadata, grouping and assertions. An initial incorrect SDK
repository URL returned **404**; retrieval from the verified official repository
`MetaGLM/zhipuai-sdk-python-v4` succeeded. An unrelated issue 1050 lookup was not
used as evidence; the cited no-fix discussion is issue 1080.

Reproduce by creating a new environment with the prescribed base interpreter,
installing `requirements-bootstrap.txt`, then using its **full executable path**
with `-m pip install --build-constraint requirements-bootstrap.txt -r
requirements-server.txt openai==2.54.0 langchain-openai==1.1.14
langchain-core==1.4.6`. Run `provider-probe.py` with a new JSON output path.
For the six named suites, separately install pytest 9.0.3 and PyMuPDF 1.26.7.
Use `-m pip check`, UTF-8 output, retrieval/warmup disabled for API tests, and the
authorized proxy with localhost bypass. Disable LangSmith tracing for synthetic
provider probes (`LANGSMITH_TRACING=false`, `LANGCHAIN_TRACING_V2=false`).
Audit with the separate tool interpreter
and the complete exact installed inventory using `--no-deps --disable-pip`.

**Host integration:** recreate environments and images from the final complete
requirements; installing an updated requirements file into an existing environment
does not automatically remove old zhipuai/PyJWT distributions. The actual old main
and Docker inventories remain untouched. Full CPU/LangChain/Streamlit dependency
resolution, complete native tests, Docker/Linux and live GLM checks remain gates.
This subset supplies useful provider/core compatibility evidence for that next
work but does not establish retrieval compatibility. Diff inspection and
`git -c core.whitespace=cr-at-eol diff --check` pass. No background process,
commit, push, deployment, main asset/environment change or external handoff edit
occurred; project knowledge handoff is contained in this report.

## Earlier increment: installation tooling — October 1, 2026

`requirements-bootstrap.txt` now pins **pip 26.2.1** and **setuptools 83.0.0**.
Native, Docker and lightweight server requirements include it; CI inherits it
through the server requirements. Docker installs bootstrap first, replacing its
unbounded pip upgrade, then passes the same file as `--build-constraint` for the
application install's separate PEP 517 build environments. No Python application
source, permanent test, asset or reliability-owned behavior was edited.
The old torch 2.8.0 Docker pin remains **unresolved**.

| Distribution | Actual legacy native | Actual deployed Docker | Fresh Python 3.11.9 bootstrap | Verified candidate |
| --- | --- | --- | --- | --- |
| pip | 25.3 | 26.2.1 | 24.0 | 26.2.1 |
| setuptools | 49.2.1 | 79.0.1 | 65.5.0 | 83.0.0 |

The first two columns come from the auditor's read-only installed inventories;
neither environment changed. Project `.venv` already had pip 26.2.1 and its
setuptools was 65.5.0. Both candidates declare Python **>=3.10** and platform-neutral
wheels. Windows **3.11.9** was exercised; Linux/Docker installation remains unrun.

The previous eight setuptools records represent four underlying groups:
**GHSA-r9hx-vwmv-q579 / CVE-2022-40897** (fix 65.5.1),
**GHSA-cx63-2mw6-8hw5 / CVE-2024-6345** (70.0.0),
**GHSA-5rjg-fvgr-3xxf / CVE-2025-47273** (78.1.1), and
**GHSA-h35f-9h28-mq5c / CVE-2026-59890** (83.0.0 in registry/tagged notes).
The newest maintainer advisory's `patched_versions` field is blank and its
affected range ends at 82.0.1; the
[tagged maintainer changelog](https://github.com/pypa/setuptools/blob/v83.0.0/NEWS.rst)
and executed behavior independently establish the normal-build fix. The old
vulnerable `setuptools.package_index` module is absent from 83.0.0.

A fresh environment initially retained pip 24.0 and produced **12 records / six
underlying groups** despite patched setuptools: **GHSA-4xh5-x5gv-qwph**,
**GHSA-6vgw-5pg2-w6jp**, **GHSA-58qw-9mgm-455v**,
**GHSA-jp4c-xjxw-mgf9**, **GHSA-wf93-45jw-7689** and
**GHSA-qwm4-qh6w-59xr**, with reported fix releases 25.3, 26.0, 26.1, 26.1,
26.1.2 and 26.2 respectively. Full bodies and alias groups are retained. The
[pip maintainer's tagged changelog](https://github.com/pypa/pip/blob/26.2.1/NEWS.rst)
documents the fixes, including **CVE-2026-13346**'s double URL decoding and tar
symlink traversal protections. 26.2.1 also restores virtualenv keyring behavior
while installing build dependencies. No installer finding was excluded as tooling.

**Setuptools fix boundary:** identical offline probes show all four Unicode
exclusion directives (`exclude`, `global-exclude`, `recursive-exclude`, `prune`)
failing with 65.5.0 and passing with 83.0.0 in normal
`setuptools.command.egg_info.FileList`. Real temporary `setup.py sdist` builds
confirm that 65.5.0 packs an NFD filename excluded by an NFC rule, while 83.0.0
omits it. The public file remains and the ASCII exclusion passes in both.
All files contain synthetic text and temporary build outputs are removed.
**The vendored `setuptools._distutils.filelist.FileList` still fails all four
direct Unicode probes in 83.0.0.** The normal setuptools build passes; direct
legacy-class callers remain outside the verified fix. A tracked Python-source
search found no application use of setuptools, distutils, pkg_resources or sdist
building. This residual behavior is evidenced, not silently called fixed.

Setuptools 82 removed `pkg_resources`. Tagged
[jieba 0.42.1 source](https://github.com/fxsjy/jieba/blob/v0.42.1/jieba/_compat.py)
already catches its absence and loads resources by the installed module's path.
Before/after probes retain the **same dictionary SHA-256, Chinese tokens,
stopword removal and BM25 scores**, including dictionary loading from an unrelated
working directory. The probe extracts the two unchanged tokenizer definitions
from `app.py` with AST; it is **not a full app import or retrieval-quality test**.
No shim is needed. An uncached jieba source build with pip 26.2.1 and
`--build-constraint requirements-bootstrap.txt` selects setuptools **83.0.0** in
its isolated build environment. Installing that real wheel repeats the checks.

Validation completed for this increment:

- Fresh `clean-runtime-venv`, created with the prescribed Python **3.11.9**
  executable: bootstrap, then `requirements-server.txt` with the build constraint,
  installs successfully and passes `pip check`. Its **26 distributions** comprise
  **24 server runtime packages + pip/setuptools**, with no pytest, PDF, provider
  or model dependencies. Exact install reports and inventory are saved.
- Fresh `clean-server-venv` with separate test/PDF/BM25 additions: the four unchanged
  API suites named below pass **69 tests, 28 skips, two warnings in 1.58 seconds**.
  The first attempt failed in conftest's unconditional `fitz` import; its log and
  exit code are retained. Installing PyMuPDF 1.26.7 **only in the test subset**
  resolves it. No PDF dependency was added to server requirements. All 28 skips
  are absent canonical SQLite; existing Starlette/AnyIO warnings remain.
- Project `.venv`: the four API suites plus the previous increment's six PDF
  suites pass **175 tests, 56 skips, two warnings in 5.98 seconds**. JUnit identifies
  absent canonical SQLite, official PDFs/manifests and refined core-rule output.
  No skip/expectation changed and no asset was copied or linked. This is a focused
  run, **not the full native suite**.
- The clean test subset's API lifespan smoke returns health **200**, OpenAPI
  **200** and invalid chat input **422**, loading no torch, sentence-transformers,
  FAISS, LangChain or Streamlit. Retrieval/warmup are disabled; preflight reports
  the missing canonical database honestly. TestClient closes normally.
- Completed **pip-audit 2.10.1** queries against every exact installed pin in
  final runtime (**26**), clean test (**36**) and project test (**41**) inventories
  each exit **0**, with **zero findings and zero skips**. Bootstrap and dev additions
  are included; audit-tool packages are separate. The clean test subset adds ten
  distributions to the runtime/tooling set. These are **clean subset audits, not a
  clean full-application audit**. The initial pip-24.0 findings remain saved.

Evidence is ignored and local under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-5/`:
advisories/tagged metadata, install reports/logs, inventories/pins, raw audits/exit
codes/alias groups, initial failed test log, final test logs/JUnit XML,
`compatibility-probe.py` with four outputs, `sdist-probe.py` with before/after
outputs, jieba source-build log/wheel, API smoke and `verification-summary.json`.
`inventory.py` and `summarize-evidence.py` reproduce inventories, grouping and
evidence assertions. Two old setuptools advisories and the latest pip advisory
have no repository-local advisory endpoint (404); GitHub's global reviewed
advisory endpoint supplied their bodies. No failed query became a clean claim.

Reproduce with the prescribed base interpreter's `-m venv`, then the new
interpreter's **full executable path** with `-m pip install -r
requirements-bootstrap.txt`, followed by `-m pip install --build-constraint
requirements-bootstrap.txt -r requirements-server.txt` and `-m pip check`.
Native/CI installs should also bootstrap first and pass the build constraint;
including the bootstrap requirements alone does **not** constrain a separate
PEP 517 build environment. Docker now applies this sequence, but was not built
or run here. Use the authorized proxy, localhost bypass and `PYTHONUTF8=1` for
external requests and Windows CLI evidence.

Actual scoped diff inspection and `git -c core.whitespace=cr-at-eol diff --check`
pass. No background service, commit, push, deployment, hook-repository edit or
orchestrator-notes edit occurred. Full CPU torch/model/LangChain/provider/Streamlit
resolution, complete CI/native/Docker sets, full native tests, final audit/no-fix
review and Linux/asset acceptance remain outstanding. The vendored distutils
limitation must remain visible in final-stage and host integration review.

## Earlier increment: PyMuPDF patch — October 1, 2026

The deployed PyMuPDF **1.26.5** pin is replaced by **1.26.7**, identically in
`requirements.txt`, `requirements-docker.txt` and `requirements-ci.txt`.
The lightweight server requirements remain model/PDF-free. No application source,
test expectation, Dockerfile, asset or reliability-owned behavior changed.
The project interpreter already had 1.26.7 as a test dependency; this increment
verifies it and makes the release/CI declarations reproducible for this package.

The baseline contains two identical **PYSEC-2026-3001** records whose aliases
are **CVE-2026-3029** and **GHSA-cxqh-p2w9-fmr7**: one underlying issue, not two.
The [GitHub advisory](https://github.com/advisories/GHSA-cxqh-p2w9-fmr7) bounds the
affected versions to `>=1.26.5,<1.26.7`. The primary
[maintainer fix commit](https://github.com/pymupdf/PyMuPDF/commit/603cafe38a183b8bab34f16d05043b4185d8d40a)
and [tagged changelog](https://github.com/pymupdf/PyMuPDF/blob/1.26.7/changes.txt)
confirm that `pymupdf embed-extract` now refuses stored filenames outside the
current directory and existing destinations by default. Explicit `-output` or
`-unsafe` opts out of those defaults; no blanket safety claim is made for those
options or every embedded-file API. A source search found no application use of
`embedded_get`, `embed-extract`, `embfile_get` or `pymupdf.__main__`.

PyPI metadata confirms Python **>=3.10**, no additional declared runtime
dependencies, and `cp310-abi3` wheels for Windows amd64 and Linux x86_64
(`manylinux_2_28`, compatible with the Debian bookworm Docker baseline).
The tagged changelog identifies the Python support change in **1.26.6** and
MuPDF **1.26.12** in 1.26.7. Only Windows Python **3.11.9** installation and
behavior were executed here; Linux wheel availability is metadata evidence,
not a completed Linux installation. No compatibility shim was necessary.

An offline before/after probe constructed a PDF with traversal, overwrite and
safe embedded filenames inside one temporary directory. With **1.26.5**, the
CLI wrote `../outside.txt` and replaced the existing sentinel. With **1.26.7**,
both calls exited **1**, no outside file appeared and the sentinel was unchanged;
the safe filename still extracted successfully in both versions. The nested
working directory and all possible destinations remained under that temporary
root, which was removed on exit. No real source or shared file was overwritten.
This verifies the upstream patch, not application reachability of the CLI.

Validation completed for this increment:

- A new isolated environment at
  `C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-4/clean-pdf-venv/`
  was created with the prescribed Python **3.11.9** executable. A clean install
  of `requirements-server.txt` plus PyMuPDF **1.26.7**, pytest **9.0.3**, HTTPX
  **0.28.1** and tqdm **4.67.3** succeeded. Install reports and exact inventories
  are saved. Both this environment and project `.venv` pass `pip check`.
  This is the server/PDF/test subset, not a complete native, Docker or CI install.
- Project `.venv`: **106 passed, 28 skipped in 5.95 seconds**, running unchanged
  `test_llm_refine.py`, `test_wiki_core_rules.py`, `test_wiki_core_rules_zh.py`,
  `test_wiki_changelog.py`, `test_db_official_zh.py` and
  `test_db_official_zh_apply.py`.
- Fresh environment: the five wiki/official-Chinese suites above passed
  **83 passed, 28 skipped in 1.99 seconds**. The LLM-refinement test file ran in
  project `.venv`, which includes its OpenAI SDK dependency; the clean subset
  intentionally contains no provider SDK. Direct PDF extraction itself also
  passed in the clean subset. JUnit evidence attributes all 28 skips in both
  runs to absent official PDFs/manifest, refined core-rule output or canonical
  SQLite. No skips were changed or bypassed with copied assets.
- Identical temporary-PDF compatibility probes passed in both environments:
  `llm_refine.extract_pages()` preserves one-based physical page numbering,
  empty pages and SHA-256 of exact extracted text; `pdf_sections.page_texts()`
  preserves column ordering; `raw_page_text()` preserves original block order;
  changelog and official-Chinese extraction retain span text/font size, with
  the changelog retaining the exact red **0xA31418**, bold flag and page number.
  No model or LangChain imports occurred. An initial synthetic fixture put both
  columns on identical baselines and PyMuPDF grouped them in one block on both
  **1.26.5 and 1.26.7**. The corrected fixture creates distinct blocks with offset
  baselines. That fixture correction is not an application regression fix.
- Fresh **pip-audit 2.10.1** audited every exact installed distribution in the
  clean subset (**35**) and project test environment (**39**). Both queries
  completed with **zero skips**, exit **1**, and **eight records / four underlying
  advisories**, all in bootstrap setuptools **65.5.0**. PyMuPDF **1.26.7** has
  zero findings. Full alias-connected groups and raw JSON are retained. No
  runtime or bootstrap package was excluded; the separate audit tool environment
  is not counted. These inventories include bootstrap pip/setuptools and test
  dependencies, so they are not production-only counts. The setuptools findings
  remain exactly those recorded in earlier increments and are not resolved here.

Evidence is ignored and local under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-4/`:
advisory JSON, primary fix commit JSON, tagged changelog, registry metadata,
clean/baseline installation reports and logs, `pdf-security-probe.py` and three
before/after outputs, `pdf-compatibility-probe.py` and both outputs, initial
fixture block evidence, both test logs/JUnit XML, inventories, audit pins,
raw audits/logs/exit codes/alias groups, and `verification-summary.json`.
`inventory.py` and `summarize-evidence.py` reproduce the inventory and grouping.

Reproduce the clean subset with the prescribed base interpreter's `-m venv`,
then that environment's full `Scripts/python.exe` path with `-m pip install -r
requirements-server.txt pymupdf==1.26.7 pytest==9.0.3 httpx==0.28.1 tqdm==4.67.3`.
Run `-m pip check`, the five named suites with `-m pytest -q`, and either probe
with a new JSON output path. The baseline CLI probe uses a separate environment
with only `pymupdf==1.26.5`. Audits use the separate audit interpreter, exact
inventory pin files and `--no-deps --disable-pip --format json`. Set the authorized
proxy for external access, bypass localhost and use `PYTHONUTF8=1` on Windows.
There were no background services; all CLI subprocesses exited and temporary
files were removed. No commit or orchestrator-notes edit was made.

The actual scoped requirement/report diff and
`git -c core.whitespace=cr-at-eol diff --check` passed. Full dependency resolution,
CPU torch, LangChain/model/provider/Streamlit compatibility, full native suite,
runtime/dev separation and Linux/Docker validation remain outstanding. Host
integration and final acceptance gates below still apply.

## Earlier increment: Requests patch — October 1, 2026

Requests **2.32.5 → 2.33.0** is installed in the isolated project `.venv` and
a second newly created Python **3.11.9** server environment. The exact pin is
shared by `requirements.txt`, `requirements-docker.txt` and
`requirements-server.txt`; CI inherits it through `requirements-server.txt`.
There are no production source, test, Dockerfile or other dependency changes in
this increment. Existing HTTP behavior required no compatibility shim.

The upstream [maintainer advisory GHSA-gc5v-m9x4-r6x2](https://github.com/psf/requests/security/advisories/GHSA-gc5v-m9x4-r6x2)
and [tagged 2.33.0 release history](https://github.com/psf/requests/blob/v2.33.0/HISTORY.md)
confirm the fix for **CVE-2026-25645**, insecure temporary-file reuse in
`requests.utils.extract_zipped_paths()`. Those two audit records describe one
underlying issue. The advisory explicitly limits affected usage to direct calls
to that utility; an application Python-source search found none. The finding is
fixed by upgrading rather than suppressed based on that observation. Registry
metadata confirms Python **>=3.10**, a platform-neutral wheel, and unchanged
dependency ranges for charset-normalizer, idna, urllib3 and certifi. This remains
a supported Python 3.11 candidate; legacy Python 3.9 is not supported.

An offline probe used a temporary ZIP and temporary directory containing a
pre-created attacker file with the same basename as the archive member. With
2.32.5 the utility returned that file and its attacker contents; with 2.33.0 it
returned the trusted archive contents from a separate location. The pre-created
file remained unchanged in both cases. All inputs and outputs were temporary;
no actual shared temporary file or source asset was overwritten. This proves the
upstream fix, not that the application exposes the affected utility.

Validation completed for this increment:

- A clean install of `requirements-server.txt` succeeded in
  `C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-2/clean-server-venv/`,
  created with the prescribed Python 3.11 executable. Its installation report and
  exact resolved inventory are saved. Both this environment and the updated
  project `.venv` pass `pip check`.
- Seven unchanged focused suites passed: **111 passed, 28 skipped, 2 warnings in
  2.84 seconds**. These comprise the four API suites listed in the earlier
  increment below plus `test_db_compile_blacklibrary.py`,
  `test_fetch_blacklibrary_details.py` and `test_blacklibrary_snapshot.py`.
  JUnit evidence confirms every skip reports missing `wh40k.sqlite`. Existing
  Starlette/AnyIO test-client deprecation warnings remain; no expectation was
  weakened and no new asset was installed.
- A real Requests/urllib3 loopback HTTP probe called the existing downloader's
  `new_session()` and `fetch_detail()` with a synthetic, identity-valid response.
  JSON request/response handling, `trust_env=False` bypass of an unusable
  environment proxy, and `raise_for_status()`/`requests.HTTPError` behavior pass.
  The temporary server was shut down, closed and its thread joined in `finally`.
- The actual API lifespan smoke again returned health **200**, OpenAPI **200**
  and invalid chat input **422**, loading no torch, sentence-transformers, FAISS,
  LangChain or Streamlit. Retrieval and warmup were disabled; missing canonical
  database readiness was reported honestly. TestClient closed normally.
- Fresh **pip-audit 2.10.1** runs completed against every exact installed pin
  in the clean server tree (**26 distributions**) and project test tree
  (**34 distributions**), with **zero skipped packages** and exit code **1**
  for each. Requests 2.33.0 has no findings. Each result contains **eight records
  representing four underlying advisories, all in bootstrap setuptools 65.5.0**:
  GHSA-r9hx-vwmv-q579, GHSA-5rjg-fvgr-3xxf, GHSA-cx63-2mw6-8hw5 and
  GHSA-h35f-9h28-mq5c. These are the unchanged tooling findings described below;
  this increment does not resolve or suppress them.

The clean inventory consists of **24 server runtime distributions plus pip and
bootstrap setuptools**. Neither tooling package is excluded from the raw audit.
The larger inventory additionally covers separately installed test dependencies;
the isolated audit tool's own environment is not counted in either inventory.
Thus the enumerated server runtime and test additions have no current findings,
while the installation environment still has the four setuptools issues.
This is **not a clean complete-application audit**: model, Streamlit and provider
dependencies are not yet installed, and their existing requirements still need
reconciliation. The full native suite and Linux/Docker installation were not run
in this increment. The full-stack Requests constraints are declared consistently,
but only the lightweight server install has been resolved and tested so far.

Evidence is ignored and local under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-2/`:

- Maintainer advisory JSON, tagged `requests-history.md`, PyPI metadata,
  `requests-install.json` and install log.
- `zip-extraction-probe.py`, before/after JSON, `http-compatibility-probe.py` and
  `http-compatibility.json`.
- `clean-server-install.json`, installation/bootstrap logs,
  `clean-server-installed.json`, `clean-pip-check.log`,
  `test-environment-installed.json`.
- Both scopes' exact audit pin files, raw audit JSON/log/exit-code files, grouped
  alias reports and `verification-summary.json`; `summarize-evidence.py` records
  the grouping and skip-reason derivation.
- Focused test log/JUnit XML and fresh lightweight smoke script/log/JSON.

Reproduce with the full project interpreter and `-m pip check`, then `-m pytest
-q` with the seven named suites. Run either probe with that interpreter; the ZIP
probe prints its result and the HTTP probe writes only its ignored evidence.
For the lifespan smoke, set `WEB_API_RETRIEVAL=off`, `WEB_API_WARMUP=0` and
`PYTHONIOENCODING=utf-8`. Audits use the separate
`db_sources/python-security/audit-venv/Scripts/python.exe -m pip_audit`, exact
inventory pin files, `--no-deps --disable-pip --format json` and a new output path;
the flags preserve the enumerated installed tree rather than re-resolving it.
Use the authorized proxy for external requests and bypass localhost.

Actual scoped diff inspection and
`git -c core.whitespace=cr-at-eol diff --check` passed. No background process is
left running, no git commit was made, and the orchestrator-owned notes were not
modified. Host integration and final acceptance gates below remain unchanged.

## Earlier increment: FastAPI/Starlette scope and installed versions

Workspace: `C:/Users/Administrator/.codex/worktrees/release-python-security/RAG`,
branch `codex/release-python-security`. New interpreter:
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/.venv/Scripts/python.exe`,
created with the existing **CPython 3.11.9** executable. Main's legacy environment
and running Docker services were untouched. This iteration installed the lightweight
server set, then separate test dependencies; the full model stack is not installed.

| Distribution | Deployed audit baseline | Installed candidate | Reason |
| --- | --- | --- | --- |
| FastAPI | 0.128.8 | 0.133.0 | First upstream release supporting Starlette 1.x |
| Starlette | 0.52.1 | 1.3.1 | Includes all five distinct deployed Starlette advisory fixes |
| Pydantic | 2.12.5 | 2.12.5 | Existing server pin remains compatible |
| Uvicorn | 0.39.0 | 0.39.0 | Existing server pin remains compatible |
| Requests | 2.32.5 | 2.32.5 | Unresolved finding retained for the next bounded patch |
| setuptools | 79.0.1 | 65.5.0 | Candidate version is Python 3.11 venv bootstrap tooling; unresolved |

FastAPI and Starlette are pinned identically in `requirements.txt`,
`requirements-docker.txt` and `requirements-server.txt`. `requirements-ci.txt`
inherits the server pins. No application imports or API behavior were edited.
Other requirements remain at their previous declarations; this is **not yet a
fully pinned or fully audited reproducible application dependency set**.

The [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/#01330-2026-02-24)
identify 0.133.0 as the first release supporting Starlette 1.0.0+; registry metadata
confirms `starlette>=0.40.0` with no `<1.0.0` ceiling. This smaller upgrade avoids
unrelated changes in the newer 0.142.2 candidate. Both patched packages require
Python >=3.10; Python 3.9 is unsupported. Their published wheels are platform-neutral,
but the Linux application install has not been run here.

## Advisory evidence and reachable behavior

The deployed audit has ten Starlette records representing **five underlying
advisories**, after grouping duplicate GHSA/CVE alias records. Maintainer advisory
JSON was fetched using the existing authenticated GitHub CLI. Tagged
[Starlette release notes](https://github.com/Kludex/starlette/blob/1.3.1/docs/release-notes.md)
independently confirm the fixes.

| Underlying advisory | Fix release | Application evidence |
| --- | --- | --- |
| [GHSA-86qp-5c8j-p5mr](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr), CVE-2026-48710 | 1.0.1 | `web_api/ratelimit.py` reads `request.url.path`; forged Host bypass reproduced before and prevented after |
| [GHSA-jp82-jpqv-5vv3](https://github.com/Kludex/starlette/security/advisories/GHSA-jp82-jpqv-5vv3), CVE-2026-54282 | 1.3.0 | Direct ASGI Request probe confirms malformed path cannot replace URL hostname after upgrade |
| [GHSA-wqp7-x3pw-xc5r](https://github.com/Kludex/starlette/security/advisories/GHSA-wqp7-x3pw-xc5r), CVE-2026-48818 | 1.1.0 | No `StaticFiles` use found in `web_api`; package is patched without relying on that scope limitation |
| [GHSA-x746-7m8f-x49c](https://github.com/Kludex/starlette/security/advisories/GHSA-x746-7m8f-x49c), CVE-2026-48817 | 1.1.0 | No `HTTPEndpoint` use found in `web_api`; package is patched |
| [GHSA-82w8-qh3p-5jfq](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq), CVE-2026-54283 | 1.3.1 | No `request.form()` use found in `web_api`; package is patched |

Two isolated environments ran the same offline Host probe against the unchanged
application rate limiter. With FastAPI 0.128.8 / Starlette 0.52.1, normal requests
returned **200, 429**, while Host `testserver/healthz?ignored=` returned **200, 200**
and reported URL path `/healthz` for actual path `/protected`. With FastAPI 0.133.0 /
Starlette 1.3.1, both sequences returned **200, 429**, and the forged request reported
`/protected`. The direct malformed ASGI path `@attacker.invalid` changed hostname
to `attacker.invalid` before; after, hostname stays `localhost` and the URL path is
`/@attacker.invalid`. This direct ASGI probe does not establish what a particular
HTTP server accepts as a malformed request target.

Starlette 1.0 removed several registration APIs. The application already uses a
lifespan context manager; FastAPI's `@app.middleware("http")` compatibility wrapper
still works in the installed candidate. No compatibility shim was needed.

## Validation actually completed

- Clean server install into the new Python 3.11.9 `.venv` succeeded; installed
  inventory and pip installation report are retained. `pip check` passed both
  before and after installing test dependencies.
- Existing focused suite: **69 passed, 28 skipped, 3 warnings in 2.94 seconds**:
  `test_web_api_stage3.py`, `test_web_api_stage4_sim.py`,
  `test_web_api_stage5_deploy.py`, `test_web_api_round3_audit_fixes.py`.
  All skips are missing `db/wh40k.sqlite` assets; no copied database or asset
  junction was introduced. Tests and expectations were unchanged.
- Test-only additions to the candidate environment: pytest **9.0.3**, HTTPX
  **0.28.1**, PyMuPDF **1.26.7**, plus their resolved dependencies. These installs
  do not constitute production requirement updates. Starlette emits a deprecation
  warning for HTTPX TestClient usage; functionality passed, so no HTTPX2 migration
  was introduced solely to remove the warning.
- A fresh-process lightweight smoke entered the actual application lifespan,
  returned `/healthz` **200**, `/openapi.json` **200**, invalid `/chat` input **422**,
  and loaded none of torch, sentence-transformers, FAISS, LangChain or Streamlit.
  `WEB_API_RETRIEVAL=off`, `WEB_API_WARMUP=0`; no inference or LLM calls ran.
  Preflight correctly reported the absent canonical database.
- Initial Windows stdout encoding was GBK and preflight printing raised
  `UnicodeEncodeError` for U+21B3. Repeating with `PYTHONIOENCODING=utf-8` passed.
  No reliability-owned file was changed; this is a terminal environment limitation,
  not evidence of a dependency regression.
- Actual requirement diff inspected; `git -c core.whitespace=cr-at-eol diff --check`
  passed. No background services were started; in-process TestClients closed.

No full native suite, complete CPU installation, asset-backed retrieval test,
Docker build, Linux install, benchmark or browser acceptance is claimed.

## Fresh audit and remaining scope

Audit tool **pip-audit 2.10.1** lives in a separate ignored environment,
`db_sources/python-security/audit-venv`. It audited all **26 distributions** in the
server install inventory, including pip and bootstrap setuptools, using exact
installed pins with `--no-deps --disable-pip`. These flags prevent re-resolution
of an already enumerated tree; no runtime dependency or advisory was excluded.
The tool's own packages were not counted as application dependencies.

The audit completed with **zero skipped packages**, exit code **1**, and **ten
records in two affected packages**, grouped into **five underlying advisories**:

- Requests 2.32.5: GHSA-gc5v-m9x4-r6x2 / CVE-2026-25645 (two records), reported
  fix 2.33.0. The advisory concerns direct `extract_zipped_paths()` use; this
  iteration retains the finding rather than claiming an application exemption.
- Bootstrap setuptools 65.5.0: GHSA-r9hx-vwmv-q579 / CVE-2022-40897,
  GHSA-5rjg-fvgr-3xxf / CVE-2025-47273,
  GHSA-cx63-2mw6-8hw5 / CVE-2024-6345,
  GHSA-h35f-9h28-mq5c / CVE-2026-59890 (eight records). This package was supplied
  by venv bootstrap, not `requirements-server.txt`; a patched installation
  tooling policy still needs verification alongside jieba/other full-stack imports.

FastAPI 0.133.0 and Starlette 1.3.1 have no findings in that completed audit.
This is a scoped result, **not a clean application audit**. The post-test environment
inventory is retained separately; its added test packages have not been audited
in this iteration. CPU torch suffix mapping, LangChain migration, Transformers
and PyJWT no-fix records, Streamlit/Pillow compatibility, remaining transitives,
dev/runtime separation and full constraints are still outstanding.

## Evidence and reproduction

All raw evidence is ignored and local under the absolute directory
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-1/`:

- `server-install.json`, `server-install.log`, `server-installed.json`,
  `server-freeze.txt`, `server-audit-pins.txt`.
- `server-audit.json`, `server-audit-grouped.json`, `server-audit.log`,
  `server-audit.exit-code.txt`, `audit-tool-install.log`.
- All five `GHSA-*.json` maintainer advisories; FastAPI/Starlette PyPI metadata;
  downloaded release notes. Initial unauthenticated GitHub API requests hit a
  shared-proxy rate limit; authenticated CLI requests succeeded. The Starlette
  website failed TLS, so tagged upstream source supplied the release notes.
- `host_probe.py`, `host-probe-before.json`, `host-probe-after.json`,
  `baseline-install.log`; baseline environment is under `baseline-venv/`.
- `api-tests.log`, `api-tests.xml`, `test-tools-install.json`,
  `test-environment-installed.json`, `lightweight_probe.py`,
  `lightweight-smoke.json`, `lightweight-smoke.log`.

Use the full interpreter path above for `-m pip check` and `-m pytest -q` followed
by the four listed test files. Run `host_probe.py` with the new interpreter or
`db_sources/python-security/iteration-1/baseline-venv/Scripts/python.exe`, passing
a new temporary JSON output path. Use the proxy `http://127.0.0.1:7897` for external
requests and bypass localhost. Raw inventories record resolved transitive versions;
they are evidence, not a finalized portable lockfile.

## Remaining integration gates

Next iterations must finish shared runtime/build constraints and clean installs,
then validate supported ingestion, embedding, FAISS loading, optional reranking,
Streamlit and provider APIs without editing reliability-owned behavior. They must
run the available full native suite with honest asset skips and audit the final
runtime/dev trees, including upstream CPU torch version and no-fix advisory evidence.

Host independently reviews the scoped diff, resolves concurrent worker integration,
recreates the supported native environment, runs Linux/Docker and final asset/live/CI
acceptance, and maintains project/hook repositories. This worktree makes no commits,
pushes, merges or service changes. No permanent regression test was added in this
iteration; the before/after behavior evidence and existing tests support this
increment, and durable dependency regressions remain part of final-stage work.
