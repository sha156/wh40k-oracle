# Python dependency security acceptance — September 30, 2026

## Complete actual Linux family — October 1, iteration 4

**The entire selected CPU family now installs and passes its framework,
provider, Streamlit and native-extension compatibility checks on Linux.
All four actual Linux inventories and complete audits reconcile. The full
native suite retains one missing-PDF fixture failure; the 43 existing Windows
SQLite/cleanup failures remain in this isolated dependency worktree. Native
recovery is now separately merged into main; its passing available Windows CI
does not replace this candidate's integrated final-family rerun. The loop stop
condition is not met.** No application source, package version or production
asset changes in this iteration. The shared constraint header now describes
the verified Linux installation rather than a metadata-only projection.

### Actual installation and reproducible platform policy

The rehearsal uses the existing `python:3.11-slim-bookworm` image, with its
exact image ID/digest saved in every command record. The actual environment is
**CPython 3.11.16 / Linux x86_64 / glibc 2.36**. No image is built, retagged or
published. The required archival/capacity handoff for a disk-backed build has
not arrived. Instead, the existing image runs finite containers with a
read-only root, dropped capabilities, no public ports and no production
mounts. Validation containers have network disabled. Only the CPU installation
uses the configured build proxy, `http://host.docker.internal:7897`.

All persistent Linux environments, installer scratch, wheel downloads and
cache writes are confined to the newly created resource child:

`D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-linux-rehearsal-iteration4/`.

The native runtime/dev interpreter is the Linux executable `venv/bin/python`
inside that directory, mounted as **`/rehearsal/venv/bin/python`**. The separate
server and CI interpreters are **`/rehearsal/server-venv/bin/python`** and
**`/rehearsal/ci-venv/bin/python`**. They require the recorded Linux base image
and mount mapping; they are not runnable Windows virtualenvs. Every environment
starts in a nonexistent directory with `/usr/local/bin/python -m venv --copies`.
No retained subset environment, main `.venv`, credential file, other checkout,
model or index is modified or executed.

The credential-free source snapshot contains **5,861 tracked files /
34,786,190 bytes**, copied from this checkout. Every copied snapshot hash still matches
after all checks. The wheelhouse contains **132 artifacts / 507,176,729 bytes**,
each checked against saved primary metadata SHA-256 values. It includes the
non-yanked Transformers 5.10.4 wheel, the source-only jieba archive and the
previously downloaded official CPU wheel. The preparer rejects an existing
environment and saves complete source/artifact manifests.

The actual sequence follows the final Dockerfile dependency declarations:

1. Install **pip 26.2.1 / setuptools 83.0.0** from `requirements-bootstrap.txt`.
2. Install `requirements-torch-cpu.txt` with
   `--build-constraint requirements-bootstrap.txt`. This step retains the
   **official CPU index only**, shared constraints and exact `torch==2.14.0+cpu`.
   Although the local verified wheel is offered through `--find-links /cpu`,
   pip selects the official remote CPU wheel; the successful download/report
   is retained. Its SHA-256 is exactly
   `673dbf5c9bbadfffab7a386b6dd7a0c219f1408a328b7b4e86d0ae551cdafa42`.
3. Install `requirements-docker.txt` from the hash-verified local wheelhouse,
   using `--no-index --find-links /rehearsal/wheelhouse` and the same build
   constraints. This installs the complete runtime declaration, including UI
   and optional reranking packages. Linux successfully builds **jieba 0.42.1**
   from its verified source archive under the patched isolated build tooling.
4. Capture the runtime inventory, install `requirements-dev.txt`, then capture
   the dev inventory. Separately create/bootstrap/install the server and CI
   sets from their actual requirement files and the same wheelhouse.

All **20 installer/check/inventory commands exit 0**. The CPU and complete
runtime installs take **734.686 / 1,586.485 seconds** on the Windows-backed
bind mount. These include slow file writes and are not production Linux
startup/inference benchmarks. Local `pip.conf` files omit optional bytecode
compilation in these new rehearsal environments; global pip/cache settings
are untouched. Every final environment passes `pip check`. The build-constrained
native `requirements.txt` dry-run requires **zero changes**. All install reports,
build logs, commands, exact pins and package metadata are retained.

| Actual Linux scope | Installed distributions | Difference from actual Windows scope |
|---|---:|---|
| Runtime | 129 | Add hf-xet/uvloop; remove colorama/tzdata |
| Native dev | 132 | Add hf-xet/uvloop; remove colorama/tzdata |
| Lightweight server | 26 | Add uvloop; remove colorama |
| Model-free CI | 79 | Add uvloop; remove colorama |

All four actual inventories exactly match the complete Linux projections.
Every shared Windows/Linux package has the same selected version; equal
distribution totals do not imply identical platform membership. Bootstrap
tooling and every final transitive remain counted. No CUDA/Triton, audit-tool,
retired ZhipuAI SDK or PyJWT distribution enters these application sets.
The previously documented Windows `platform_machine=""` qualification remains.

| Selected supported family | Actual Linux version |
|---|---|
| LangChain / core / community / classic | 1.3.9 / 1.4.6 / 0.4.2 / 1.0.8 |
| Experimental / text-splitters | 0.4.2 / 1.1.2 |
| HuggingFace integration / OpenAI integration | 1.2.2 / 1.1.14 |
| OpenAI SDK | 2.54.0 |
| Transformers / SentenceTransformers | 5.10.4 / 5.7.0 |
| CPU torch / NumPy / FAISS | 2.14.0+cpu / 1.26.4 / 1.15.1 |
| FlashRank / ONNX Runtime | 0.2.10 / 1.30.0 |
| Streamlit | 1.59.0 |
| Linux hf-xet / uvloop | 1.6.0 / 0.22.1 |

The exact complete inventories and shared **134-pin** constraints supply the
remaining transitive versions. This iteration selects no additional direct
package patch and needs no production framework import/API edit.

### Actual compatibility checks and exact test reconciliation

- The complete import probe loads every selected LangChain family module,
  Transformers, SentenceTransformers, FlashRank, ONNX Runtime, FAISS, Streamlit,
  PyMuPDF, jieba, hf-xet, uvloop and the actual application/ingestion/refinement
  modules. CPU torch reports **2.14.0+cpu / `torch.version.cuda is None`**.
  Actual torch/NumPy/FAISS operations produce finite normalized **2 x 1024
  synthetic tensors**, return the two correct FAISS nearest-neighbor identities,
  and complete a real **`torch.load(weights_only=True, map_location='cpu')`**
  tensor round trip. A tiny ONNX Add graph executes through the actual
  **CPUExecutionProvider** and returns **[4.0, 6.0]**. These are genuine native
  extension operations, explicitly synthetic inputs, not text-model inference.
- The same seven meaningful framework/ingestion/retrieval/provider/refinement
  suites pass **85 tests / zero skips / three warnings in 121.32 seconds**.
  JUnit case identities exactly match the preceding 85-case Windows run.
  Actual semantic chunking, FAISS serialization/retrieval, BM25, RRF/rules-floor
  behavior, citations and streaming chain APIs remain supported.
- Both actual SDK protocol probes pass DeepSeek and GLM streaming, structured
  response/citations, benchmark response, 400 format fallback and 429 propagation.
  The real `app.main()` Streamlit AppTest passes both provider selections,
  streamed output, citation records/display and history reruns, with zero
  AppTest exceptions. HTTP resources remain synthetic and network is disabled;
  these results do not claim paid-provider or browser/service acceptance.
- The **entire available native suite** runs with explicit `tests/` collection:
  **2,561 passed / 336 skipped / one failed / zero errors**, ten warnings,
  **430.60 seconds**; JUnit has **2,898 cases**. Every case identity and every
  skipped identity/reason exactly matches the preceding complete Windows run.
  All 336 existing asset skips remain visible. Exactly **43 Windows failures/
  errors become passed**: 40 SQLite lock failures/errors and three archive
  cleanup assertion failures. The source is unchanged; this is Linux platform
  evidence, not a repair of Windows connection lifetime/cleanup behavior.
- The model-free CI command follows the existing workflow's explicit
  **`--ignore=tests/test_app_retrieval.py`** boundary. Those local application
  tests are exercised in the complete native run. CI reports **2,549 passed /
  342 skipped / one failed / zero errors**, nine warnings, **372.66 seconds**;
  JUnit has **2,892 cases**. Every case and skipped identity matches the prior
  Windows CI run. Four skipped messages differ only in the actual interpreter
  path; their missing-jieba reason is unchanged. All other skip messages match
  exactly. The same 43 Windows failures/errors become passed, with no new
  failure, error or skip identity in either Linux suite.
- The pure **26-package server** enters the actual API lifespan and processes
  direct ASGI requests on its installed **uvloop**. Health/OpenAPI/invalid-chat
  statuses are **200 / 200 / 422**; no torch, Transformers, SentenceTransformers,
  FAISS, Streamlit or LangChain module is imported. The absent structured DB is
  reported by preflight. No TestClient dependency is added to the runtime set.

The only Linux suite failure is the unchanged
`tests/test_wiki_keyword_index.py::test_parse_quickref_too_few_entries_raises`:

```text
FileNotFoundError: Official Core Rules PDF missing:
data/官方中文/chi_01-06_warhammer40k_new40k_core_rules-gihrxgzhgo-iickazpeog.pdf
```

It remains a **failure**, not an added skip or suppressed test. The negative
fixture still reaches the untracked official PDF dependency before its intended
too-few-entries assertion. Source owners retain the fixture fix, Windows SQLite
fixes and full Windows rerun. No production PDF is copied to make this test green.

The final-family real **bge-m3 / 5,905-document archived FAISS / BM25/hybrid/RRF /
local FlashRank** evidence remains the exact successful **iteration 3 Windows**
probe: actual finite normalized English/Chinese 1024-d embeddings, unchanged
model/index hashes and document identities, weights-only model loading and
zero PT2 loads. No declaration/application source affecting that result changes.
Linux mounts no production model/index/reranker assets, so no Linux text-model,
archived-index or pretrained-reranker inference result is invented. Integrated
asset-backed Docker/live/browser acceptance remains host-owned.

### Complete installed-tree audits and retained residuals

The separately inventoried **30-distribution auditor environment** uses
pip-audit **2.10.1**, exact actual Linux installed pin files,
`--no-deps --disable-pip --format json`, a new confined audit cache and **no
advisory exclusions**. All seven audit commands exit 0. The reconciler checks
set equality, every version, all findings/fixes and every raw skipped row.

| Actual Linux scope | Raw exact PyPI audit | CPU-mapped complete audit |
|---|---|---|
| Runtime, 129 distributions | zero findings; one explicit torch +cpu skip | 129 / zero findings / zero skips |
| Dev, 132 distributions | zero findings; one explicit torch +cpu skip | 132 / zero findings / zero skips |
| Server, 26 distributions | 26 / zero findings / zero skips | not needed |
| CI, 79 distributions | 79 / zero findings / zero skips | not needed |

Only the installed, official-hash-verified **torch 2.14.0+cpu** maps to upstream
**2.14.0** for the registry query. The separate fresh exact **+cpu OSV audit**
reports **one package / zero findings / zero skips**. Raw exact-PyPI CPU skips
are retained and are not described as clean exact-PyPI audits. No CPU/model,
bootstrap or final transitive package disappears from the denominator.

Registry-zero remains qualified by all earlier inspected residuals: Streamlit
array sampling, vendored distutils Unicode exclusions, torch PT2 unsafe-pickle
behavior, and the selected Transformers conversion/nested-configuration scope.
No advisory suppression, unsupported package substitution, remote-code/pickle
safety guarantee or new fix claim is introduced. Existing source import logs
also retain their hf-mirror TLS-warning text; network-disabled probes make no
mirror request, and no certificate/global credential setting is changed here.

### Preserved probe failures, resource limits and independent handoff

Every unsuccessful preparation/probe attempt remains separately reviewable:

- The initial preparer expected CPU metadata in the ordinary PyPI metadata
  directory. Its FileNotFoundError is saved; the corrected preparer consumes
  the dedicated verified official-CPU record before downloading any wheel.
- The first import helper lacked `/app` on `sys.path`. All third-party imports
  completed before `ModuleNotFoundError: No module named 'app'`; adding the
  project path fixes this helper, with no production import/API edit.
- Linux pytest capture could not truncate its unlinked temporary file on the
  Windows D: bind mount. A separate benign standard-library reproduction proves
  **FileNotFoundError / errno 2** on that share and successful identical
  write/read/truncate on Linux tmpfs. Tests therefore use a private **1 GiB
  tmpfs `/tmp/rehearsal-tests`**; installer environments/cache/scratch and durable
  evidence remain on D:. Standard pytest capture and test assertions are retained.
- Concurrent output collection briefly copied an older control script over
  its edited source, producing `ValueError: validate-native-rest`. Collection
  now excludes `.py` control files; the failed wrapper and original installer
  body/hash are saved. No environment or package installation is repeated.
- A server probe incorrectly requested TestClient's absent **httpx2** test
  extra in the deliberately lightweight runtime. The corrected direct-ASGI
  probe tests the same application/lifespan on uvloop without adding packages.
- An initial CI command omitted the workflow's existing local-app exclusion
  and failed collection on missing jieba. The corrected command matches the
  actual workflow; complete native testing covers the excluded local app tests.
- Streamlit's initial **60-second** AppTest budget expired during cold imports
  from the slow bind-mounted environment. With the explicit **300-second**
  probe budget, all original functional assertions pass; the full UI process
  takes **144.616 seconds**. No production timeout or UI behavior changes.

The original installer observer had a 40-minute limit, shorter than this
Windows-backed file installation. After a second finite observer attached to
the exact named/id-verified container, only the original owned Python observer
was terminated. Its observed exit **1**, command/PID, original installer
body/hash and the replacement wait are preserved. **The same installer/container
continues unchanged and exits 0**; no environment or install step is restarted.
The longer observer and all validation/audit subprocesses have finished.

Observed C: free space changes from **4,227,817,472** before rehearsal to
**2,915,205,120 bytes** after validation; D: remains **185,149,440,000 bytes**
free. These observations do not substitute for the missing archival/capacity
handoff. No Docker build, storage relocation, prune, production service command
or model replacement is attempted. All uniquely named finite containers are
removed; no browser, server, watcher or other run-owned background process remains.

New evidence is local/ignored under the absolute directory:

`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/full-stack/iteration4/`.

It includes complete source/wheel manifests, every installed inventory/pin file,
all installation reports/logs, seven raw audit bodies/exits, the separately
inventoried auditor, probe scripts/results, failed-attempt prefixes, JUnit,
per-case platform/skip reconciliation and `verification-summary.json`.
`prepare-linux.py`, the hash-preserved original installer body,
`linux-rehearsal.py`, `run-linux.py`, `audit-linux.py` and
`reconcile-linux.py` record the exact finite calls and ownership guards.
For a fresh install choose a new resource-root child; completed environment
directories must not be reused. This is dependency-layer execution using the
final Dockerfile declarations, not a built-image/non-root deployment claim.

Host handoff remains: review the entire scoped candidate independently, combine
it with the separately merged Windows SQLite/cleanup and PDF-fixture fixes,
rerun the complete final-family native suite, integrate concurrent API/frontend/
source changes, and perform actual
asset-backed/live/browser/remote-CI/deployment acceptance. The existing workflow
still selects **Python 3.10** and an unpinned bootstrap upgrade; its obsolete
3.9 comment and supported-interpreter/bootstrap alignment are reported for the
host, outside this dependency worker's file ownership. No workflow, external
knowledge repository, orchestrator notes, manual staging/commit or publication
is changed here. Root can record the verified NTFS/tmpfs, probe-budget and
control-file preservation lessons without duplicating earlier knowledge notes.

Final validation inspects the actual two-file diff and passes
`git -c core.whitespace=cr-at-eol diff --check`. All **11** retained finite
Python probe/reconciliation scripts parse successfully; the auditor's complete
30-package membership/versions exactly match iteration 3. Final Docker and
Windows process checks find no run-owned container, Python helper or Docker
observer remaining. Package pins and all tracked application/test sources
are unchanged; only this report and the verified constraint-header comments
change in Git. No manual commit is made.

## Non-yanked complete Windows family — October 1, iteration 3

**Transformers 5.10.4 replaces the yanked 5.10.0 candidate and passes a new
clean installation and the complete Windows compatibility checks. Actual full
Linux installation and the existing source-owned test fixes remain gates.**
This section supersedes the replacement gate in the preceding iteration;
the earlier installation, raw audits and failure evidence are preserved below.
The loop stop condition is **not met**.

### Final declarations and fresh installation

`requirements-runtime.txt` and `constraints-python311.txt` now pin
**Transformers 5.10.4**. Fresh primary release bodies confirm that its wheel
and source archive are both non-yanked, require Python >=3.10, and have exactly
the same dependency declarations as 5.10.0. The selected wheel's PyPI SHA-256
is `8c5b99b141b53619435a76629b0284f04d27ff46d788b463fc0ecb23b8ff130e`;
the install report records that hash. Linux-compatible wheel metadata separately
matches its simple-index metadata hash. This is a supported replacement based
on release status and actual feature validation, not a newly invented advisory
fix claim. No application import shim, provider change or feature removal was
needed. All other family, CPU, bootstrap and transitive pins are retained.

The new interpreter is
`D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`.
It was created from the prescribed Windows **CPython 3.11.9** executable into
a previously nonexistent directory. It contains the entire runtime, followed
by the separately declared dev tools; it does not upgrade the earlier complete
environment or any retained subset environment. The actual sequence is:

1. Base Python's `-m venv` creates the fresh target.
2. Target Python's `-m pip install -r requirements-bootstrap.txt` installs
   **pip 26.2.1 / setuptools 83.0.0**.
3. Target Python's `-m pip install --build-constraint requirements-bootstrap.txt
   --report <cpu-install.json> -r requirements-torch-cpu.txt` installs CPU torch
   through the dedicated official index only.
4. The equivalent build-constrained commands install
   `requirements-runtime.txt`, capture the exact runtime inventory, then install
   `requirements-dev.txt` and capture the exact dev inventory.

Both installed scopes pass `-m pip check`. The final build-constrained
`-m pip install --dry-run -r requirements.txt --report <final-dry-run.json>`
requires **zero changes**. Bootstrap/CPU/runtime installation exits are all 0,
with elapsed times **12.141 / 63.968 / 172.641 seconds**. The runtime has
**129 distributions**, dev **132**. Membership and every version are compared
against the earlier complete inventories: **only Transformers changes from
5.10.0 to 5.10.4**. Bootstrap and CPU/model/transitive packages remain counted;
no CUDA/Triton, auditor or retired ZhipuAI SDK package enters the application.

The CPU report uses the official index's
`download-r2.pytorch.org/whl/cpu/` wheel endpoint. The Windows torch wheel hash
is `8e2c47c6556c7d5a85848634372bb2252907d411e9cad669c99406856d536eb5`,
identical to the previously verified official **2.14.0+cpu** artifact.
The installer, download cache and scratch remain confined to the authorized D:
resource root, with process-local proxy, UTF-8, `PIP_CACHE_DIR` and `TEMP/TMP`.
No global cache configuration or production environment is changed.

The existing separately created **26-package server / 79-package CI**
environments are inventoried again. Their membership and every version are
unchanged; final requirement dry-runs require zero changes and `pip check`
passes. Their no-model boundary remains the one proven in the earlier clean
installs. No second full CI test run is claimed in this iteration; its dependency
closure and tracked test/application sources have no changes.

### Complete feature and full-suite verification

The same seven framework, ingestion, retrieval, provider and refinement suites
pass **85 tests / zero skips / two warnings in 32.84 seconds**. These exercise
the installed LangChain 1.x family, semantic chunking, actual FAISS operations,
BM25 and streaming chains; no expectation or skip marker is changed.

The real readonly bge-m3 probe loads the same complete absolute snapshot with
CPU, `local_files_only=True`, `trust_remote_code=False` and the actual
**`torch.load(weights_only=True, map_location=cpu)`** boundary. PT2 loading is
guarded and **zero PT2 loads** occur. Real English/Chinese vectors are finite,
**2 x 1024**, with norms **1.0000000368799877 / 0.9999999686587795**.
The trusted immutable pre-retirement index opens with **5,905 documents/vectors**,
dimension **1024**; document objects and id mapping remain identical. Actual
BM25/hybrid/RRF retrieval has zero errors, includes the rules floor and assembles
the real prompt context. The existing local FlashRank/ONNX model returns three
finite passage scores. Model weights, tokenizer/modules and both index-file
hashes are unchanged before/after and equal to the earlier probe's hashes.
The probe's measured feature portion takes **20.203 seconds**; its encompassing
process, including imports/hashing, takes 50.234 seconds. No download, production
re-embedding or model replacement occurs.

Both real SDK provider protocol probes pass again: DeepSeek and GLM streaming,
structured agent response/citations, benchmark response, 400 format fallback
and 429 propagation. The actual Streamlit `app.main()` AppTest passes both
provider selections, streamed text, citation display/records and history reruns.
Synthetic resources and in-memory HTTP responses remain explicit; these are
framework compatibility checks, not paid-provider, production browser or live
service acceptance.

The **entire available native suite** runs again with explicit `tests/`
collection: **2,518 passed / 336 skipped / 29 failed / 15 errors**, nine warnings,
**197.06 seconds** (202.875 seconds for the encompassing command). JUnit contains
**2,898 cases**. A separate reconciler proves that **every individual test
identity/status and every skipped test identity/reason exactly matches the
earlier complete run**, not merely its totals. All 336 existing skips remain
the absent DB/CSV/PDF/refined/cache assets recorded earlier. No dependency
import failure is disguised as a new skip. The same 44 failures/errors remain:
40 Windows SQLite replacement errors, three archive cleanup assertions and
one missing-Chinese-fixture quick-reference negative case. Their source owners
still need to apply the documented fixes; this iteration neither edits those
files nor calls the application suite green.

Fresh selected-wheel source inspection and the benign LightGlue configuration
probe preserve the previous residual qualification: the X-CLIP conversion
script is absent, nested registered configuration stays local, unknown nested
architecture is rejected, and zero nested remote config calls occur. The raw
OSV no-fix records are fetched again without exclusions. This does not establish
image-model inference or universal safety of conversion/remote-code/pickle
paths. The earlier Streamlit array-sampling, vendored distutils Unicode and
torch PT2 unsafe-pickle residuals remain unchanged.

### Exact complete audits and Linux preparation

The separate **30-distribution** auditor environment runs pip-audit **2.10.1**
with exact installed pin files, `--no-deps --disable-pip --format json`, a new
confined D: HTTP cache, and **no advisory exclusions**. Set equality, each version
and every raw skip are reconciled against the new actual inventories.

| Actual Windows scope | Raw exact PyPI audit | CPU-mapped complete audit |
|---|---|---|
| Runtime, 129 distributions | zero findings; one explicit torch +cpu skip | 129 / zero findings / zero skips |
| Dev, 132 distributions | zero findings; one explicit torch +cpu skip | 132 / zero findings / zero skips |
| Server, 26 distributions | 26 / zero findings / zero skips | not needed |
| CI, 79 distributions | 79 / zero findings / zero skips | not needed |

Only the installed, hash-verified **torch 2.14.0+cpu** maps to registry upstream
**2.14.0**. A fresh separate exact-CPU OSV audit also reports **one package /
zero findings / zero skips**. All seven audit commands exit 0. The raw PyPI
CPU skips are preserved and not called clean exact-PyPI results. Bootstrap,
models and final transitives remain in the denominator. Registry-zero is
qualified by the inspected library residuals above.

The complete Linux metadata preflight is rerun against the final pins. It
reconciles **all 134 constraint versions** and every activated dependency edge;
**none of the selected wheels/source releases is yanked**. Runtime/dev/server/CI
projections remain **129 / 132 / 26 / 79**, with the same documented platform
membership differences (hf-xet/uvloop versus Windows colorama/tzdata).
These remain **metadata projections, not Linux installed inventories or audits**.
The previous actual Linux four-package additions probe and downloaded official
CPU wheel are retained; neither substitutes for the full Linux installation.

The required host archival/free-space handoff has not arrived. An October 1
observation records **5,777,776,640 bytes free on C:** and
**191,499,456,512 bytes on D:**, but that observation is not a verified archival
map or Docker-VHD capacity approval. No Linux build or container is started,
and no Docker image/compose service is changed. The final-Dockerfile full Linux
install, jieba build, finite compatibility tests, exact actual platform closures
and full audits are the next dependency unit after that handoff.

### Evidence, retained limitations and host handoff

All new source-side evidence is isolated under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/full-stack/iteration3/`:
primary release bodies/comparison, installation commands/logs/reports, exact
runtime/dev/server/CI/auditor inventories and pins, all seven raw audits and
exits, complete JUnit and per-case reconciliations, model/UI/provider/residual
scripts and outputs, hashed Linux metadata/projections, and
`verification-summary.json`. `clean-install.py`, `audit.py` and `reconcile.py`
record the precise finite calls; the installer rejects an existing target.
For a repeat installation choose a new confined resource-root child and update
the installer's target constants, rather than reusing this completed environment.

One ad-hoc inventory print initially omitted UTF-8 when reading the installer
JSON under the base interpreter, producing a GBK `UnicodeDecodeError`. The exact
reproduction/error/exit are retained; the verified scripts use explicit UTF-8
and process-local UTF-8 settings. An initial broad evidence filename search also
traversed old rehearsal directory entries unnecessarily; it read no package
bodies and executed or modified no old environment. Subsequent file enumeration
is confined to `full-stack`. No claim is made that this initial traversal
respected the requested directory-access boundary.

Only the two dependency declarations and this report change in Git. Actual
diff inspection and `git -c core.whitespace=cr-at-eol diff --check` pass. All finite
installer/test/probe/audit subprocesses have exited; no server, watcher or browser
is started or left running. No manual commit, staging, publication, deployment,
external knowledge-repository update or orchestrator-notes edit occurs.
Root can record this verified dependency result without duplicating the existing
knowledge notes. Root retains independent review, the SQLite/PDF fixture fixes,
full native rerun after those fixes, integration and final live/CI/deployment
acceptance. The new non-yanked complete Windows family is reviewable; the
complete bounded Windows-and-Linux objective remains unfinished.

## Complete-family platform preflight — October 1, iteration 2

**The candidate still requires a supported Transformers replacement, complete
Linux installation/audit, and the existing host-owned application fixes.** The
previous Windows installation and real model evidence remain valid observations
for their exact versions; they do not establish support for a yanked release.
This iteration validates the complete declared dependency graph across platform
markers, rather than upgrading another direct package in isolation.

### Newly verified gates and platform constraints

- **Transformers 5.10.0 is yanked.** Both its wheel and source archive are yanked
  in the original saved `metadata-transformers.json` as well as the fresh PyPI
  body. The maintainer's reason is: “We pushed from a week old main branch. It
  does include the latest model but uncertain its gonna be working properly
  and mostly it is missing a bunch of fixes!” The previous report omitted this
  status. Exact pins allow pip to install yanked versions, so installation,
  `pip check`, successful bge-m3 probes and registry-zero audits do not clear
  this support gate. No version has been silently substituted. Fresh metadata
  lists non-yanked 5.10.1/5.10.2/5.10.4 and later releases; selecting and verifying
  a replacement requires another clean complete installation, real probes and
  reconciled audits. These are available candidates, not verified replacements.
- **The current Windows interpreter reports `platform_machine=""`**, despite
  being 64-bit Windows Python 3.11.9. Hugging Face Hub 1.33.0 therefore does not
  activate its architecture-marked `hf-xet>=1.6.0,<2` dependency in this environment.
  Linux x86_64 does. A normal Windows AMD64 marker also activates it. This explains
  its absence from the exact earlier 129/132 inventories; it is a marker
  difference, not an audit exclusion. The actual local marker body is retained.
- Shared constraints now additionally pin **hf-xet 1.6.0** and **uvloop 0.22.1**.
  Uvicorn's `standard` extra requires uvloop on Linux CPython. Constraints do
  not force either package into sets whose markers do not request it. The
  complete Linux closure remains uninstalled; the constraint header says so.
- The **official Linux torch 2.14.0+cpu wheel** has no CUDA/Triton dependencies.
  Its metadata differs from the installed Windows CPU wheel, whose Linux-only
  metadata branches list CUDA packages. The official CPU index's metadata hash
  matches the Linux sidecar and the actual downloaded wheel's METADATA.
  `pip download --no-deps --only-binary=:all: --platform manylinux_2_28_x86_64
  --implementation cp --python-version 3.11 --abi cp311 --index-url
  https://download.pytorch.org/whl/cpu torch==2.14.0+cpu` succeeds. The
  **196,227,330-byte** wheel has SHA-256
  `673dbf5c9bbadfffab7a386b6dd7a0c219f1408a328b7b4e86d0ae551cdafa42`.
  This is wheel preparation, not a Linux torch installation or inference claim.
  Raw urllib requests to the index's `download-r2` URL returned 403, while the
  official `download.pytorch.org` alias worked; the actual pip download succeeded
  without a declaration, credential, certificate or index change. The endpoint
  errors and successful pip log are both retained.

### Complete graph and bounded Linux execution

The existing `python:3.11-slim-bookworm` image reports **CPython 3.11.16,
Linux x86_64, glibc 2.36**. A finite, network-disabled, read-only container captures
its actual PEP 508 marker environment and compatible wheel tags. The preflight
then checks **all 134 exact constraint versions**, including bootstrap and the
two new marker additions, against primary release bodies and compatible wheel
metadata. Wheel metadata hashes reconcile to the PyPI simple index; torch uses
the official CPU index. Every activated dependency edge satisfies an exact pin
and Python version constraint, including requested extras. No CUDA/Triton edge
is activated. **Jieba 0.42.1 is source-only**: its source metadata is retained,
and a successful Linux build is still required. Transformers' yanked status is
explicitly retained in both full model scopes.

| Projected Linux scope | Distributions | Changes from the actual saved Windows scope |
|---|---:|---|
| Runtime | 129 | Add hf-xet/uvloop; remove colorama/tzdata |
| Native dev | 132 | Add hf-xet/uvloop; remove colorama/tzdata |
| Lightweight server | 26 | Add uvloop; remove colorama |
| Model-free CI | 79 | Add uvloop; remove colorama |

**These are complete metadata projections, not installed Linux inventories or
Linux application audits.** Equal counts conceal different members. Each
scope has its exact projected pins, dependency edges, extras, source-only/yanked
records and set differences saved separately for later installed-tree comparison.

The two new native wheels are actually installed in a fresh **RAM-backed Linux
venv** with patched pip 26.2.1/setuptools 83.0.0. It has exactly **four**
distributions. `pip check` passes; uvloop runs eight concurrent async tasks on
its native loop; hf-xet imports its Rust extension and exposes the genuine
download/upload functions. No Xet network request or model download occurs.
The entire container filesystem is read-only except a **128 MiB tmpfs**; only
the four hash-verified wheels are mounted read-only from the run-owned resource
directory. The separate auditor reconciles all **four installed distributions**
with **zero findings/zero skips**, exit 0, without exclusions. This is explicitly
an additions/bootstrap probe, **not the complete application audit**.

Initial probe harness failures are preserved: a default non-executable tmpfs
prevented native `.so` mapping, and a read-only default Xet log directory produced
an extra console JSON record. The final probe uses executable tmpfs, a fresh
venv, and a tmpfs-local HF cache; its output and stderr are clean. Early graph
checks also retained the yanked-release and previously unconstrained hf-xet
failures before producing the final reconciled projection.

### Validation, artifacts and next work

With the final additional constraints, the existing complete Windows environment
requires **zero package changes** in the build-constrained requirements dry-run;
`pip check` passes. The same seven compatibility suites pass again:
**85 passed / zero skips, 37.87 seconds**. JUnit and exact exits are retained.
The earlier full-suite **44 failures/errors** and **336 missing-asset skips**
are not reclassified or claimed fixed; no corresponding application code changed.

Evidence remains under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/full-stack/`:
`linux-preflight.py`, `linux-preflight/` (raw compressed simple-index bodies,
release bodies, hashed metadata and complete projections),
`linux-marker-wheel-probe.py`, its command/log/inventory/audit bodies,
`linux-cpu-wheel-verified.json`, CPU download/endpoint logs,
`iteration2-windows-*` checks and `iteration2-platform-handoff.json`.
New wheels are confined to the authorized D: resource root's
`full-stack-linux-marker-wheels/` and `full-stack-linux-cpu-wheels/`; cache/temp
remain in that root's existing owned children. The retained `.venv`, earlier
rehearsal environments, production assets and other checkouts are untouched.

The host archival/free-space handoff is still pending. **No image build, image
retag, service restart, production mount, manual commit or publication occurs.**
All finite probe containers are removed. Observed free space is not substituted
for the required archival confirmation. Next work should first replace the
yanked Transformers candidate and verify the entire resolved family, then
perform the actual Linux rehearsal with the final Dockerfile, complete installed
inventories/audits and available compatibility tests after that handoff. Preserve
the existing Windows SQLite/PDF fixture reproductions for their source owners.
Independent review, full native rerun after owned fixes and final integration,
live/CI/deployment acceptance remain host-owned. **The loop stop condition is
not met.**

The explicit user stop hook subsequently authorizes the local knowledge handoff.
After duplicate checks, `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and
`ROADMAP.md` record this iteration, its evidence and remaining gates. One raw
learning decision in `C:/Users/Administrator/learn-notes/decisions/` records
platform membership/release-support checks; two resolved probe-harness records
in `C:/Users/Administrator/error-notes/common/` record tmpfs native mapping and
Xet read-only logging/JSON output. Both indexes are updated. All pre-existing
note bodies and Git indexes are byte/hash-preserved; no nonexistent commit
explanation, harness promotion, staging, commit or publication is made.
`hook-knowledge-handoff.json` records the exact local paths and verification;
root retains independent review, integration and knowledge publication ownership.

## Complete-family Windows candidate — October 1, 2026

**The complete CPU family is installed and exercised on clean Windows Python
3.11.9; this is not yet a Linux-verified or fully passing application candidate.**
This continuation starts from `c021868c976ebfae8e7db879dcdc59935d2ad438`.
It preserves the earlier paired security evidence and all library limitations
below. Linux installation, independent review and the application issues listed
here remain gates; the overall stop condition is **not met**.

The previous native lower bounds and Docker/CI LangChain 0.3 pins are replaced
by one family declaration. `requirements-framework.txt` supplies the model-free
document, splitter, provider and vector APIs. `requirements-runtime.txt` adds
the complete CPU model, ONNX reranker, PDF, retrieval and Streamlit application.
Native `requirements.txt` includes that runtime plus `requirements-dev.txt`;
Docker includes only the runtime. Test/auditor packages are separate. Server
retains its no-LangChain/no-model boundary; CI retains its no-model boundary.
`constraints-python311.txt` records **every distribution in the 132-package
Windows runtime/dev closure**, including pip/setuptools and all transitives.
Constraints restrict resolution without installing unused packages in a
lightweight set. Docker copies the shared declarations and constraints before
its existing, separate official-CPU-index install step. No CUDA/Triton package
is installed. The constraint file's header explicitly leaves Linux closure and
platform-marker verification outstanding; no identical-platform claim is made.

| Family | Actually installed versions |
|---|---|
| LangChain | langchain 1.3.9; core 1.4.6; community 0.4.2; classic 1.0.8; experimental 0.4.2; text-splitters 1.1.2 |
| Model/provider integrations | langchain-huggingface 1.2.2; langchain-openai 1.1.14; OpenAI 2.54.0 |
| CPU model/retrieval | torch 2.14.0+cpu; SentenceTransformers 5.7.0; Transformers 5.10.0; FAISS CPU 1.15.1; NumPy 1.26.4 |
| Optional reranking | FlashRank 0.2.10; ONNX Runtime 1.30.0; tokenizers 0.22.2 |
| Numerical/model transitives | SciPy 1.17.1; scikit-learn 1.9.1; safetensors 0.8.0; huggingface-hub 1.33.0 |
| UI/data transitives | Streamlit 1.59.0; Pillow 12.3.0; pandas 3.0.6; pyarrow 25.0.1 |
| Framework transitives | LangSmith 0.14.2; LangGraph 1.2.4; HTTPX 0.28.1 and httpx2 2.13.1; aiohttp 3.14.3 |
| Preserved security pins | FastAPI 0.133.0; Starlette 1.3.1; Requests 2.33.0; urllib3 2.8.0; PyMuPDF 1.26.7; dotenv 1.2.3; pip 26.2.1; setuptools 83.0.0 |
| Development tools | pytest 9.1.1; pluggy 1.6.0; iniconfig 2.3.0 |

Saved primary PyPI metadata verifies the selected family requirements rather
than assuming candidate compatibility. OpenAI's latest overall release is
3.22.1, but the selected LangChain integration requires OpenAI **<3**, and pip
actually resolves **2.54.0**. LangSmith separately introduces httpx2/httpcore2;
the existing HTTPX client boundary remains installed and tested. The eight
family imports already use supported package boundaries, so **no production
Python compatibility shim, import fallback, provider-routing change or feature
removal was needed**. An AST inventory inspects all **280 tracked Python files**
and finds **24 files** with relevant framework/model/provider imports. Upstream
community and experimental packages emit sunset/deprecation warnings; their
required features remain installed and exercised, not silently disabled.

### Clean installation and resource confinement

The new application interpreter is
`D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows/Scripts/python.exe`.
It was created with
`C:/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe -m venv`
and did not reuse the readonly checkout `.venv` or any iteration-1..10 environment.
The resource root above contains this run's new cache, scratch, auditor, server
and CI environments only. `PIP_CACHE_DIR`, `TEMP` and `TMP` point to its
`full-stack-cache` and `full-stack-temp` children in each installation shell;
proxy is `http://127.0.0.1:7897` with localhost bypass. Global settings are unchanged.

The actual clean sequence installs `requirements-bootstrap.txt`, then
`requirements-torch-cpu.txt` with `--build-constraint requirements-bootstrap.txt`,
then `requirements-runtime.txt` with the same build constraint. Development
tools are added separately from `requirements-dev.txt`. The CPU requirement
uses **only** the official CPU index and an exact `+cpu` pin. All four steps,
including `pip check`, exit **0**. Bootstrap/CPU/runtime take **21.078 / 122.344 /
268.812 seconds**. One interrupted CPU download resumes from 37.7 MB; its full
log is retained. Installer JSON reports record actual wheel URLs/hashes.

The complete exact constraints were derived from that installation, and a final
`-m pip install --dry-run --build-constraint requirements-bootstrap.txt -r
requirements.txt` requires **zero package changes**. Final `pip check` passes.
This is one newly created complete environment, followed by three test-tool
additions; it is not an incrementally repaired legacy/subset environment.
New **26-package server** and **79-package CI** environments install the final
tracked requirements with the shared constraints and build constraint; both
pass `pip check`. Exact inventories and import-spec probes confirm they contain
no torch, Transformers, SentenceTransformers, Streamlit or HF integration.
Server additionally contains no LangChain/FAISS packages.

### Actual feature and test evidence

- **85 focused compatibility tests pass, zero skips**, in **35.43 seconds**:
  `test_dependency_framework.py`, `test_app_retrieval.py`, `test_ingest_pages.py`,
  `test_ingest_vector_reuse.py`, `test_llm_client.py`, `test_llm_refine.py` and
  `test_md_chunker.py`. Four new cases exercise real FAISS serialization/vector
  identity and metadata filtering, BM25, semantic/recursive splitting, and both
  OpenAI-compatible streaming prompt chains. Synthetic vectors are explicitly
  synthetic; the real model evidence is separate below.
- Actual provider clients also pass the prior genuine-client protocol probe:
  DeepSeek and GLM, structured agent response/citations, streaming, benchmark
  response, 400 response-format fallback and 429 propagation. It now records
  the full installation's transitive model imports instead of asserting the
  earlier subset-only no-model-import condition. No real credential, paid
  request, endpoint routing change or remote-provider acceptance is involved.
- Streamlit **AppTest runs the actual `app.main()` chat shell**, with finite
  synthetic FAISS resources and in-memory HTTP responses. Both provider choices,
  streamed text, citation records/display and history across reruns pass.
  Resource/provider fixtures are explicit; this is native framework/UI
  compatibility, not a production browser or live service acceptance.
- The readonly **complete local bge-m3 snapshot**
  `D:/Project/py/RAG/opt/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181`
  loads with `local_files_only=True`, CPU and `trust_remote_code=False`.
  Real English/Chinese embeddings have shape **2 × 1024**, all finite, with
  norms **1.0000000369 / 0.9999999687**. The complete snapshot has trusted
  `pytorch_model.bin`; the other snapshot contains only a safetensors file and
  is not substituted. Instrumentation observes the genuine loader call with
  **`weights_only=True`, `map_location=cpu`**, and guards PT2 export loading;
  **zero PT2 loads** occur during construction/embedding. No model is downloaded,
  replaced or written. This is stronger evidence than an application AST scan.
- The trusted immutable pre-retirement archive at
  `D:/Project/py/RAG/archive/source-retirement-20260930/pre-apply/local_vector_store`
  opens with the new FAISS/LangChain classes: **5,905 vectors/documents**, dimension
  **1024**, identical document objects and id mapping. Actual BM25/hybrid/RRF
  retrieval has **zero recorded errors**, preserves source/page metadata and
  includes the rules floor. Real prompt/context assembly succeeds. SHA-256 of
  model weights, tokenizer/modules and both index files is unchanged before/after.
  No production vectors are re-embedded or assets projected into this checkout.
- Actual FlashRank inference uses the existing local MiniLM ONNX cache through
  the application's cache resolver. All three passages receive finite scores.
  Embedding/index/hybrid/reranker probe completes in **21.594 seconds**. Default
  reranking policy remains unchanged.

The **full available native suite was executed**, with retrieval/warmup off and
explicit `tests/` collection: **2,518 passed / 336 skipped / 29 failed / 15 errors**,
**189.12 seconds**. JUnit reconciles **2,898 cases** and records every skip name
and reason without changing tests, expectations or skip markers. All 336 skips
are absent local DB/CSV/PDF/refined/cache assets. They are not model import skips.
The unchanged model-free CI collection excludes its established six
`test_app_retrieval.py` cases and executes **2,892 cases**: **2,506 passed / 342
skipped / 29 failed / 15 errors**, **163.37 seconds**. The extra six skips are
unchanged local-only app checks (two declared local-only, four missing app
imports); their exact identities/reasons are retained. Neither full run is green.

**Two root-owned issues explain the 44 failures/errors; no failures are hidden:**

1. **40** directly report Windows SQLite replacement failures in the unchanged
   `db_compile/build.py:440`: `PermissionError: [WinError 32] ... units.tmp.sqlite
   -> units.sqlite` (analogous fixture filenames are retained). A tiny two-CSV
   reproduction fails both on the prescribed base Python 3.11.9 interpreter and
   on the complete dependency environment, including a short 115-character
   destination. Base-revision hashes prove the builder is unchanged from
   `c021868c9`. An **in-memory copy** of that exact base function succeeds on both
   interpreters when it explicitly calls `cur.close()` before `conn.close()`.
   This diagnoses an outstanding cursor/file handle, not a package-resolution
   failure or long-path issue. **Three more** archive-negative cases leave the
   temporary SQLite file behind after the expected validation exception; the
   cleanup catches an OSError, and the lingering-file assertion fails. These
   are included in the 43 builder/archive cases, not described as direct
   WinError exceptions. No builder/source-archive/API source is edited.
   Root should review the cursor lifetime, apply its owned fix, then rerun these
   suites and the full native suite without excluding them.
2. `test_parse_quickref_too_few_entries_raises` expects an incomplete-English-PDF
   ValueError, but its unchanged implementation first requires the absent
   official Chinese PDF and raises FileNotFoundError. Parser and test hashes
   match the actual base revision. Source-retirement/test ownership should
   provide an explicit temporary Chinese fixture for that negative test; no
   production PDF or test expectation is substituted here.

Initial harness errors are also retained. A new FAISS test initially compared
documents without explicit ids against FAISS's assigned ids; the fixture now
uses explicit stable ids and three documents (avoiding the two-document BM25
zero-IDF tie). One broad pytest invocation unintentionally discovered old
rehearsal site-packages and failed collection. It was stopped by pytest's normal
collection failure, recorded, and corrected to explicit `tests/`. No installer
ran in those environments; bytecode writes were disabled. That invocation did
read old rehearsal library files and should **not** be described as respecting
the intended read boundary. The previous provider verifier's final no-model
assertion failed after all protocol assertions; its full-runtime replacement
retains the protocol assertions and records the loaded-module list.

### Complete Windows audits and bounded residuals

The separate auditor interpreter is the resource root's
`full-stack-auditor/Scripts/python.exe`, with **30 tool distributions**; none
are included in application counts. It uses pip-audit **2.10.1**, exact inventory
files, `--no-deps --disable-pip --format json`, no advisory exclusions. A
reconciler checks set equality and every installed version against raw bodies,
not just totals or direct declarations.

| Complete installed scope | Raw PyPI audit | CPU-mapped full audit |
|---|---|---|
| Native runtime, **129** distributions | zero findings; **one explicit torch +cpu skip** | **129 / zero findings / zero skips** |
| Native dev, **132** distributions | zero findings; **one explicit torch +cpu skip** | **132 / zero findings / zero skips** |
| Server, **26** distributions | **26 / zero findings / zero skips** | not needed |
| CI, **79** distributions | **79 / zero findings / zero skips** | not needed |

Only the verified installed **torch 2.14.0+cpu** is mapped to upstream **2.14.0**.
The exact CPU wheel also has a separate OSV query: **one package / zero findings /
zero skips**, exit 0. All seven audits exit **0**. The raw CPU skips are retained,
and CPU/model/bootstrap/transitive packages remain in the denominators. Native
129/132 are now the **complete declared application/runtime and dev closures**;
the earlier 61/68/69/75-package results remain historical subsets.

Baseline family advisories and primary metadata are preserved. Native LangChain
0.3.28 has three raw records, core 0.3.84 five, and Transformers 4.57.3 eight;
raw records may share aliases. Latest complete installed audits find no matches.
Two Transformers baseline records have **no declared fix version**:
`PYSEC-2025-217 / CVE-2025-14929` (X-CLIP conversion) and
`PYSEC-2026-2290 / CVE-2026-5241 / GHSA-fgcw-684q-jj6r` (nested LightGlue config).
Fresh unmodified OSV bodies bound them respectively through **5.0.0-rc0** and
**5.2.0** with `last_affected`, not a named fix release; this explains their
absence for selected 5.10 without inventing a patch claim or exclusion.
The installed 5.10 wheel has no X-CLIP conversion script. Its inspected
LightGlue config uses local `CONFIG_MAPPING`, not nested remote AutoConfig
loading: a benign config probe preserves the local SuperPoint config, rejects
an unknown nested architecture and observes **zero remote config calls**.
That is a configuration-boundary check, **not image-model inference**. The real
application uses the trusted bge-m3 weights-only path above; no tracked consumer
imports either affected architecture/converter. Unsafe user-opted remote code,
arbitrary pickle weights or conversion utilities are not declared universally
safe. Earlier **Streamlit deterministic array sampling**, **setuptools vendored
distutils Unicode exclusion**, and **torch PT2 unsafe-pickle behavior** remain
qualified exactly as below despite registry-zero results.

### Evidence, next iteration and host gates

All new raw evidence is under the ignored absolute directory
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/full-stack/`:
primary metadata, unchanged baseline family bodies, source scan/hashes, clean
installation reports/logs/commands, exact runtime/dev/server/CI/auditor inventories,
raw/mapped audits and CPU OSV body, JUnit and reconciled full skip/failure lists,
model/provider/UI/LightGlue verifiers and outputs, SQLite base/candidate
reproductions, failed attempts, and `verification-summary.json`.
Reproduce finite probes with the new complete interpreter, **never** a moved
iteration-1..10 environment. `install.py`, `lightweight-install.py`,
`inventory.py`, `model-probe.py`, `provider-probe.py`, `ui-probe.py`,
`inspect-model-residuals.py`, `lightglue-boundary-probe.py`,
`sqlite-lock-diagnosis.py` and `reconcile.py` preserve the actual calls. The
lightweight installer requires fresh target names; do not rerun it onto existing
environments. Use `-m pytest -q tests` for full collection, not bare discovery.

Next bounded dependency work is **actual Linux installation with this final
Dockerfile**, complete platform inventories/constraints and audits, and finite
import/no-asset tests. No Linux build is started before the host's required
verified archival/free-space map arrives. C: had **2.1 GiB** free at entry and
temporarily fell below **1 GiB** during concurrent work before recovering above
**6 GiB**; observation alone is not the required archival confirmation or a
Docker-VHD capacity guarantee. No Docker image is built/retagged, compose service
restarted, environment deleted/moved, source crawled, model replaced, credential
copied or external checkout modified by this iteration. The Linux closure may
have real platform variants such as Uvicorn's conditional uvloop; reconcile the
actual installation rather than treating the Windows lock as proof.

Independent review, the two owned application fixes and a passing complete
native rerun remain host gates. The older workflow's Python 3.9/local-baseline
comment and Python 3.10 CI target are outside this dependency-file ownership;
root should synchronize its Python 3.11/bootstrap/build-constraint commands in
the integration review. Final integrated Docker/assets/browser/live/provider/CI
acceptance, production deployment and publication remain **host-owned**.
No commit, push, merge, global knowledge-note edit or manual service was made.
The scoped tracked diff and whitespace checks are required again at handoff.

---

The sections below are retained historical security-increment evidence.

Status: **incremental candidate, not release acceptance**. The shared
FastAPI/Starlette boundary, Requests, PyMuPDF and installation tooling are patched
and verified in isolation, with the setuptools legacy-path limitation below.
The unused ZhipuAI SDK requirement is retired while both GLM provider paths are
preserved and verified with synthetic responses through real provider clients.
Streamlit is pinned and verified at 1.59.0, including its actual palette-hashing
fix; deterministic large-array sampling remains explicitly qualified below.
CPU PyTorch is pinned and verified at **2.14.0+cpu**, including the actual JIT
crash correction absent from the registry's claimed 2.13.0 fix. PT2's unsafe
pickle behavior remains evidenced and outside the inspected application paths.
python-dotenv is now synchronized at **1.2.3**, with its symlink-write fix and
Windows BOM/backslash behavior verified against actual older installations.
urllib3 is synchronized at **2.8.0**, including three September maintainer
advisories absent from the supplied baseline matches; 2.7.0 is insufficient.
The complete CPU application stack, full native suite, Docker/Linux installation
and final audit remain outstanding.
No integration, deployment, source retirement or main-environment changes occurred.

## Latest increment: urllib3 transport pin and September advisory verification — October 1, 2026

Native, Docker and lightweight-server requirements now explicitly pin **urllib3
2.8.0**. CI inherits the server pin. Requests remains **2.33.0** and its real
transport/session behavior passes the probes below. The actual native baseline
contains **2.6.0**; Docker already resolved **2.8.0**, with no original match.
The project candidate also previously resolved 2.8.0. This increment prevents
unconstrained resolution or retention of an older native transport: it does not
claim a Docker version change. Only three requirements files and this report
change. No production Python, test expectation, source policy, asset, generated
page, API reliability-owned file or Docker installation step changed.

**The supplied snapshot is incomplete for current urllib3 advisories.** Its
native entry has **six records / three underlying groups**. A fresh exact query
of that same **2.6.0** returns **eight records / five groups**, adding the HTTPS
proxy and chunk-size-line issues below. A fresh query of intermediate **2.7.0**
returns **three records / three groups**, all requiring **2.8.0**. The additional
Deflate issue starts at 2.6.2, so it is not an extra finding on native 2.6.0.
These are query results, not altered baseline records. The
[tagged 2.8.0 release notes](https://github.com/urllib3/urllib3/blob/2.8.0/CHANGES.rst)
and all six fetched maintainer advisories support the selected branch. Registry
metadata publishes **2.8.0 on September 15, 2026**, requires **Python>=3.10** and
provides a **py3-none-any** wheel. Verification uses **Python 3.11.9**; Linux
installation or a Docker build is not claimed.

| Underlying issue | Actual evidence and candidate outcome |
|---|---|
| PYSEC-2026-1996 / CVE-2026-21441 / [GHSA-38jv-5279-wg99](https://github.com/urllib3/urllib3/security/advisories/GHSA-38jv-5279-wg99), compressed redirect | Patched from 2.6.3. Toy 2.6.0 redirect decodes all **262,144 bytes** before the final read; 2.8.0 decodes **zero** redirect bytes. |
| PYSEC-2026-141 / CVE-2026-44431 / [GHSA-qccp-gfcp-xxvc](https://github.com/urllib3/urllib3/security/advisories/GHSA-qccp-gfcp-xxvc), low-level proxy redirect headers | Patched from 2.7.0. Real `ProxyManager.connection_from_url().urlopen()` forwards toy Authorization, Cookie and Proxy-Authorization across origins on 2.6.0; 2.8.0 strips all three and retains an ordinary header. |
| PYSEC-2026-142 / CVE-2026-44432 / [GHSA-mf9v-mfxr-j63j](https://github.com/urllib3/urllib3/security/advisories/GHSA-mf9v-mfxr-j63j), partial decoding then drain / Brotli reads | Patched from 2.7.0. After a 16-byte gzip read, 2.6.0 decodes **262,128 additional bytes** during drain; 2.8.0 decodes **zero**. The optional Brotli-specific security reproduction is **not claimed**; see its qualification below. |
| CVE-2026-97687 / [GHSA-8988-9cw3-xx77](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77), HTTPS proxy TLS policy | Patched from 2.8.0. A real TLS policy-helper call on 2.7.0 changes the proxy context from **CERT_REQUIRED to CERT_NONE** because the destination disables verification; 2.8.0 preserves **CERT_REQUIRED** and the proxy hostname/context. The probe stops immediately before the actual handshake. |
| CVE-2026-97689 / [GHSA-vxq7-64xx-v4gw](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw), chunk-size line buffering | Patched from 2.8.0. A real stdlib HTTPResponse/urllib3 streaming call on a finite toy malformed line requests unlimited input and reads **100,000 bytes** on 2.7.0; 2.8.0 caps that read at **65,537 bytes** and rejects it. |
| CVE-2026-97688 / [GHSA-gh4c-6fx4-qh6g](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g), chunked Deflate trailing-byte loop | A **4,096-byte** toy decoded stream with trailing compressed input hangs on 2.7.0 in an owned subprocess; the verifier kills and reaps it after **three seconds**. 2.8.0 completes, exits **0** and preserves every decoded byte. This issue affects >=2.6.2,<2.8.0. |

**These checks exercise real installed libraries.** Decoder instrumentation
records the output of the original decoder, without replacing its behavior.
The header/redirect probes use a local toy HTTP proxy; `.invalid` target names
are served by that proxy without external DNS or destination requests. The
TLS probe instruments only the socket-wrapping boundary after the actual policy
helper runs; it establishes context mutation, not a live TLS interception
exploit. Chunked probes use real stdlib HTTPResponse objects over disposable
in-memory wire bytes. No large decompression bomb, external credential target,
source refresh, model download or application service was used.

The Requests probe preserves same-origin Authorization, strips cross-origin
Authorization, retains an ordinary header, delivers the exact streamed gzip
body and raises HTTPError for 503. Low-level urllib3 pools also strip credentials
on same-origin proxy redirects after patching; do not mistake that observation
for the application Requests contract. A separate actual
`scripts.fetch_blacklibrary_details.fetch_detail()` call against a local toy
POST endpoint preserves the expected identity/detail and `trust_env=False`
proxy bypass. No real capture or cache write runs. Partial read followed by an
unlimited gzip read preserves the exact complete byte stream.

An AST scan covers **all 280 tracked Python files**. Production Requests imports
are in ingestion, Black Library compilation and the two capture scripts. The
only direct urllib3 import is ingestion's existing warning-control call. No
tracked direct ProxyManager/PoolManager, drain, chunked-reader or iter_content
call was found; four recorded `urllib.request.urlopen()` consumers use the
stdlib, not urllib3. The inspected ingestion mirror TLS exception and HTTP Clash
proxy remain unchanged. Plain HTTP proxies do not have the HTTPS-proxy TLS
vulnerability described above. This bounds inspected direct reachability, not
the full future third-party HTTP call graph, and does not justify retaining
matched vulnerable versions.

**Optional decoder qualification:** neither clean runtime/test inventory nor
the project subset installs Brotli or brotlicffi. A separate **eight-package**
environment verifies small incremental Brotli reads using actual **Brotli 1.2.0**
and urllib3 2.8.0, passes pip check and audits clean. urllib3's declared Brotli
extra requires **Brotli>=1.2.0** on CPython; tagged code warns and falls back to
unbounded decoding on older optional decoder libraries. No optional decoder is
added to production merely for this probe. The original larger Brotli sample
did not establish the expected advisory reproduction and is excluded from that
claim; its verifier error is retained. Host/final-stack resolution must retain
the declared decoder floor if an optional Brotli extra is enabled.

Validation actually completed:

- A **new clean-final-venv** installs tracked bootstrap and the **tracked server
  requirements**, using the shared build constraint. Its **26-distribution**
  runtime inventory passes `pip check`, has no pytest/model/retrieval libraries
  and retains the server no-model contract. The project `.venv` also passes
  `pip check`. Both install/use urllib3 **2.8.0** with Requests **2.33.0**.
- Fresh compatibility probes pass in **0.585 seconds**, September advisory
  probes in **0.406 seconds**; project **0.577 / 0.420 seconds** respectively.
  The real application HTTP probe passes in both. Every toy server is shut down,
  closed and joined; each owned subprocess completes or is killed and reaped.
- Separate **pytest 9.0.3 / PyMuPDF 1.26.7 / HTTPX 0.28.1** test additions produce
  a **34-distribution** fresh test subset with a passing `pip check`. The five
  simulator/API suites named in the preceding increment plus
  `test_db_compile_downloads.py`, `test_fetch_blacklibrary_details.py` and
  `test_blacklibrary_snapshot.py` pass **118 / skip 30 / two warnings in 3.87
  seconds** fresh; project **118 / skip 30 / two warnings in 2.74 seconds**.
  JUnit verifies all 30 skips are missing `wh40k.sqlite`; no asset, fixture,
  expectation or skip was changed. Retrieval/warmup are disabled.
- Isolated **pip-audit 2.10.1** audits complete **26-runtime**, **34-test** and
  **eight-optional-decoder** inventories: **zero findings / zero skips**, exit 0.
  The complete project **75-distribution** exact inventory has zero findings
  with one explicit CPU torch PyPI skip. Mapping only **2.14.0+cpu to 2.14.0**
  yields **75 / zero findings / zero skips**; an OSV query of the exact installed
  CPU version yields **one / zero findings / zero skips**. Both exit 0. Tool-only
  packages are excluded; no runtime package or advisory is suppressed. Earlier
  PT2, Streamlit sampling and setuptools limitations remain despite registry
  results. These are still application **subsets**, not the full release tree.

Ignored raw evidence and executable verifiers are at
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-10/`:
unaltered baseline selections, current baseline/intermediate audits and alias
groups, six maintainer bodies, tagged changelogs/source, registry metadata,
clean/install reports and logs, exact runtime/test/project/optional inventories,
raw audits and CPU supplement, source scan, probes and before/after JSON,
test logs/JUnit, `evidence.py`, `summarize-evidence.py` and
`verification-summary.json`. Initial verifier errors are retained: an unsupported
Brotli assertion, a wrong same-origin expectation, a missing method on a toy
stdlib response, missing explicit chunk decoding and a mistyped CPU audit input
path. Corrected calls use real library APIs; no production exception handling or
test relaxation hides these mistakes.

Reproduce in a **new Python 3.11 environment** with full interpreter paths,
proxy/localhost bypass and UTF-8 output: install `requirements-bootstrap.txt`,
then `requirements-server.txt` with `--build-constraint
requirements-bootstrap.txt`; run `urllib3-probe.py`, `september-probe.py` and
`http-compatibility-probe.py` with new JSON output paths, then `-m pip check`.
Add the three test-only pins and run the eight named suites. Capture exact
inventories with `evidence.py inventory <scope>` and audit with the separate
tool using `--no-deps --disable-pip --format json`; query the CPU pin with OSV.
Before probes require separately installed **2.6.0** and **2.7.0**, never a
downgrade of the final candidate. Supplemental Brotli uses a separate environment.

Actual scoped diff inspection and whitespace validation pass. Host integration
must recreate the supported native environment, retain the transport pin and
finish the model/LangChain family, remaining transitive constraints and
production-test separation. Full native/asset/Linux/Docker/live acceptance still
remains; this increment does **not** meet the overall stop condition. No commit,
push, merge, Docker service/image change, external knowledge-repository edit,
main-environment mutation or deployment occurred.

## Earlier increment: python-dotenv patch and Windows text verification — October 1, 2026

Native, Docker and lightweight-server requirements now pin **python-dotenv
1.2.3**. CI inherits the same pin through its existing server include. This
replaces Docker's **1.2.1** and native's unconstrained requirement; server's
previously implicit Uvicorn-standard dependency is now explicit. Both actual
auditor inventories contain **1.2.1**. This increment changes three requirements
files and this report only; no production Python, test expectation, API
reliability-owned file, asset, source policy or Docker installation step changed.

Each baseline has **two records / one underlying issue**:
**PYSEC-2026-2270 / GHSA-mf9w-mj56-hr94 / CVE-2026-28684**. The
[maintainer advisory](https://github.com/theskumar/python-dotenv/security/advisories/GHSA-mf9w-mj56-hr94)
and [actual correction](https://github.com/theskumar/python-dotenv/commit/790c5c02991100aa1bf41ee5330aca75edc51311)
identify **1.2.2** as patched. The fetched advisory metadata unusually says
`<1.2.1`, omitting 1.2.1; the baseline audit and reproduction demonstrate that
1.2.1 is affected. Preserve that discrepancy rather than interpreting the range
literally as proof of safety.

**The security correction is reproduced through real installed library calls.**
On isolated **1.2.1**, both `set_key()` and `unset_key()` overwrite a synthetic
symlink target when `os.rename()` is made to raise **EXDEV**. The real library's
`shutil.move()` fallback performs the write; no replacement dotenv module is
used. On both **1.2.2** and final **1.2.3**, those same operations preserve the
target, replace the symlink entry and make **zero `os.rename()` calls**. The
final probe also verifies dangling-symlink writes do not create the target,
explicit `follow_symlinks=True` preserves intentional opt-in behavior, temporary
files share the target directory, `os.replace()` is used, and replacement errors
leave the original file unchanged, remove temporary files and propagate.
All inputs/targets are disposable toy files under this worktree. Windows
symlink creation succeeds on this host. EXDEV is simulated, so this establishes
the actual fallback behavior, not a physical Linux cross-filesystem trial.
POSIX file-mode preservation remains unverified on this Windows host.

**1.2.3 has a concrete Windows compatibility reason.** The
[1.2.3 release notes](https://github.com/theskumar/python-dotenv/releases/tag/v1.2.3),
published **August 16, 2026**, document UTF-8 BOM handling and backslash escaping.
Actual 1.2.1/1.2.2 probes lose the expected first BOM-prefixed key and change a
value containing repeated backslashes during `set_key()`/`dotenv_values()`
roundtrip; **1.2.3 preserves both**. This selects the small maintenance release
for demonstrated supported-platform behavior, rather than inventing an extra
security advisory. Registry metadata requires **Python>=3.10** and provides a
platform-neutral **py3-none-any** wheel. Every executed probe/install uses the
prescribed **Python 3.11.9**; Linux installation/execution is not claimed.

The AST scan of **all 280 tracked Python files** finds one dotenv consumer:
`scripts/refresh_official_rules.py::refresh()` imports and calls `load_dotenv()`.
There are **no tracked `set_key()` or `unset_key()` calls**. The existing Uvicorn
standard extra also uses dotenv for `--env-file`. Direct probes preserve
UTF-8 loading, variable interpolation, existing-environment precedence,
explicit override, local discovery and missing-file behavior without changing
the input file. A real `uvicorn.Config(env_file=...)` loads a toy file correctly;
no server or refresh/generation command is invoked. No application compatibility
shim or weakening of the safer write defaults is necessary.

Validation actually completed:

- A **new clean-final-venv** installs the tracked bootstrap followed by the
  **tracked server requirements**, with the shared build constraint. Its complete
  **26-distribution runtime subset** passes `pip check` and contains no pytest,
  LangChain, torch, Transformers, SentenceTransformers, FAISS or Streamlit.
  The server's no-model contract is preserved. Installer tooling is included in
  the recorded scope. The project `.venv` already resolved **1.2.3** and passes
  the same probe plus `pip check`; no main environment is touched.
- The final fresh dotenv probe passes in **0.151 seconds**, project **0.181
  seconds**; older installed-version probes retain the before/intermediate
  differences above. These are dependency behavior checks, not full retrieval,
  model, source-update or release acceptance.
- Separate test additions **pytest 9.0.3 / PyMuPDF 1.26.7 / HTTPX 0.28.1** produce
  **34 distributions** and pass `pip check`. Unchanged suites
  `test_simulator_panel.py`, `test_web_api_stage3.py`, `test_web_api_stage4_sim.py`,
  `test_web_api_stage5_deploy.py`, `test_web_api_round3_audit_fixes.py` and
  `test_db_compile_downloads.py` pass **82 / skip 30 / two warnings in 1.68
  seconds** on the fresh subset; project **82 / skip 30 / two warnings in 1.88
  seconds**. JUnit identifies every skip as absent `wh40k.sqlite`. Retrieval and
  warmup are disabled; no asset/fixture/expectation/skip was altered. The full
  native suite still awaits the remaining model/LangChain installation.
- Isolated **pip-audit 2.10.1** completes the full **26-runtime** and **34-test**
  subset inventories with **zero findings / zero skips**. The current project
  **75-distribution** exact inventory returns zero findings with one explicit
  **torch 2.14.0+cpu PyPI skip**. A second full query maps only that local CPU
  version to upstream **2.14.0**: **75 / zero findings / zero skips**. A separate
  OSV query of the **exact installed CPU version** passes **one / zero findings /
  zero skips**. All exit 0. Raw JSON, exact inventories, alias grouping, skips
  and failures are saved; auditor packages are excluded from app counts.
  Earlier PT2, Streamlit sampling and setuptools qualifications remain.

Ignored evidence and executable reproduction scripts are under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-9/`:
baseline bodies/groups, maintainer advisory/fix/releases, PyPI version metadata,
AST source scan, before/intermediate/final/project probes, clean install reports
and logs, runtime/test/project inventories and raw audits, CPU supplemental query,
test logs/JUnit, `dotenv-probe.py`, `inventory.py`, `collect-evidence.py`,
`summarize-evidence.py` and `verification-summary.json`.
The first backslash sample failed to distinguish the older release because it
used lone backslashes; that verifier assertion/error is retained. The corrected
sample uses repeated backslashes and proves the release difference. No production
exception handling or test relaxation was introduced to hide it.

Reproduce with a **new Python 3.11 environment**, full interpreter paths, the
authorized proxy/localhost bypass and UTF-8 output: install
`requirements-bootstrap.txt`, then `requirements-server.txt` with
`--build-constraint requirements-bootstrap.txt`; run the saved dotenv probe with
a new JSON output path and `-m pip check`. Add the three test-only pins above,
run the six named suites, capture an inventory and audit it using the separate
auditor with `--no-deps --disable-pip --format json`. The probe's 1.2.1/1.2.2
before cases require separate environments, not downgrading the candidate.

Host integration must preserve the shared pin, recreate the complete supported
environment, finish remaining family/transitive constraints and production-test
separation, and run full native/asset/actual Docker/live acceptance. Actual scoped
diff inspection and whitespace validation pass. No commit, push, merge, Docker
service/image change, external knowledge-repository edit or deployment occurred.
All owned subprocesses have exited; no background server was started. This
increment does **not** meet the overall release-stage stop condition.

## Earlier increment: CPU PyTorch patch and reproduced advisory discrepancy — October 1, 2026

Native and Docker requirements now require **torch 2.14.0+cpu**, replacing
Docker's **2.8.0** declaration and making native's previously implicit torch
dependency explicit. Both actual auditor inventories contain upstream **2.8.0**;
Docker's installed version is **2.8.0+cpu**. The new
`requirements-torch-cpu.txt` confines the official CPU index to a separate
installation step. Docker copies that file and installs it after bootstrap,
before the remaining application requirements, with the same build constraint.
Exact `+cpu` pins prevent a subsequent full install silently substituting a
PyPI CUDA wheel. Server/CI sets retain their no-model contract. No production
Python, permanent test, API reliability-owned file, source policy or asset changed.
Full-stack dependency synchronization is still outstanding; the remaining
LangChain/model-family pins are not claimed patched by this increment.

**Version selection is based on actual behavior, not the largest fix-list value.**
PyTorch 2.10 fixes the maintainer's checkpoint advisory. Registry metadata for
2.11/2.12 requires **setuptools<82**, incompatible with the patched **83.0.0**
bootstrap. 2.13 removes that cap, but its installed CPU wheel still crashes on
the JIT reproducer below. **2.14.0**, released **September 2, 2026**, contains and
passes the demonstrated correction. All selected wheels require **Python>=3.10**;
the actual verification baseline remains the prescribed **Python 3.11.9**.

The native audit and separate Docker CPU OSV audit each contain **eight records /
eight underlying torch alias groups**, representing the same issues across
environments. Docker's original PyPI skip is preserved, not counted as clean.

| Underlying issue | Evidence and candidate outcome |
|---|---|
| PYSEC-2025-195 / CVE-2025-3001, `lstm_cell` | Baseline service reports 2.10.0 fixed; candidate upstream and CPU service queries have no match. No invalid-input exploit reproduction is claimed. |
| PYSEC-2025-194 / CVE-2025-3000 / GHSA-rrmf-rvhw-rf47, JIT | Installed 2.13.0+cpu still crashes; 2.14.0+cpu rejects the exact reproducer. Registry discrepancy is retained below. |
| PYSEC-2025-193 / CVE-2025-2999, `unpack_sequence` | Baseline service reports 2.9.1 fixed; candidate queries have no match. No dedicated exploit reproduction is claimed. |
| PYSEC-2025-203 / CVE-2025-55551, `linalg.lu` | Baseline service reports 2.9.0 fixed; candidate queries have no match. |
| PYSEC-2025-204 / CVE-2025-55552, `rot90`/`randn_like` | Baseline service reports 2.9.0 fixed; candidate queries have no match. |
| PYSEC-2025-206 / CVE-2025-55554, integer overflow | Baseline service reports 2.9.0 fixed; candidate queries have no match. |
| PYSEC-2026-139 / CVE-2026-4538, PT2 | No fixed-version event in OSV; its range ends at 2.10.0. Unsafe pickle loading remains demonstrated in 2.14.0; application reachability is qualified below. |
| PYSEC-2026-2286 / PYSEC-2026-1856 / CVE-2026-24747 / GHSA-63cw-57p8-fm3p, weights-only checkpoint | [Maintainer advisory](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p) explicitly fixes >=2.10.0. Candidate passes tensor roundtrip and harmless custom-global rejection; these do not exhaustively exercise the malformed-opcode/storage exploits. |

**JIT discrepancy, independently reproduced:** the raw PYSEC record unusually
ends at `2.6.0-NA`, while pip-audit's service reports **2.13.0** fixed. The
[upstream issue #149623](https://github.com/pytorch/pytorch/issues/149623) provides
the bare-list scripted-class reproducer. Run in an owned subprocess, the clean
2.13.0+cpu candidate exits **3221225477 / 0xC0000005**, with no output. The same
unchanged child script on both upgraded and fresh 2.14.0+cpu exits **0** after
asserting the expected **"Attempted to use list without a contained type"**
RuntimeError. A JIT deprecation warning is retained. The actual correction is
[upstream PR #188779](https://github.com/pytorch/pytorch/pull/188779), landed by
commit `b90c94991cdf8b87c8f7439f79518e0ef2c4ca4f` on **July 2**. GitHub's tag
comparison shows the commit is an ancestor of 2.14.0, while 2.13.0 diverges;
tagged `ir_emitter.cpp` confirms the rejection helper absent in 2.13 and present
in 2.14. No main environment or production process was used for this reproduction.
Thus **2.14.0 is the first verified stable correction here**, rather than a
claim that the service's 2.13 pin was sufficient.

**PT2 limitation is actual, not just an empty fix list:** the OSV-linked
[PR #176791](https://github.com/pytorch/pytorch/pull/176791) is **closed without
merging**. Installed 2.14's `torch.export.load` has **no weights_only argument**;
its `_load_state_dict` still calls `torch.load(..., weights_only=False)` when an
archive marks a payload `use_pickle`. An in-memory toy model with an explicitly
pickled tensor-returning canary invokes our own harmless Python callable once
and still produces the expected output. It performs no shell, filesystem or
network action. This establishes the unsafe deserialization behavior persists,
even though current upstream/CPU service queries no longer match the record.
No universal PT2 fix or arbitrary untrusted-checkpoint safety is claimed.

An AST/text scan of **all 280 tracked Python files** found **zero direct torch
imports or torch load/JIT/export calls**. The application's torch dependency is
through SentenceTransformers/HuggingFace embeddings; actual app/ingestion source
selects the bge-m3 model and CPU device. There is no inspected PT2-loading or
checkpoint-upload path. The existing trusted local model/index boundary remains
required, in line with the [tagged PyTorch security policy](https://github.com/pytorch/pytorch/blob/v2.14.0/SECURITY.md),
which treats models as executable programs and warns against untrusted loads.
The cached main assets were neither read nor copied in this increment. This
qualifies inspected application reachability, not future consumers or the full
third-party call graph; the model integration step must recheck its actual path.

Validation actually completed:

- New **clean-final-cpu-venv**, created with the prescribed interpreter, installs
  bootstrap, the **tracked CPU requirement file**, then server requirements plus
  **streamlit 1.59.0**. Its complete runtime subset contains **61 distributions**,
  including installer tooling and torch, with **no pytest, LangChain,
  SentenceTransformers, Transformers, JWT, CUDA or Triton distributions**.
  `pip check` passes. The upgraded candidate and isolated project `.venv` also
  install the exact CPU pin successfully; project `pip check` passes. All are
  isolated under this worktree; the main venv is untouched.
- The fresh Windows **cp311 win_amd64** wheel's downloaded SHA-256 matches the
  official CPU index. That index also provides **cp311 manylinux_2_28 x86_64**;
  both platforms' PEP 658 metadata hashes match the index. Linux's actual CPU
  wheel metadata has **no CUDA/Triton dependencies**. Windows metadata includes
  Linux-only CUDA markers, which do not apply on Windows; the Linux CPU wheel
  metadata is the relevant Docker evidence. Both accept setuptools>=77.0.3,
  including the patched 83.0.0. This verifies publication/metadata, **not Linux
  installation, execution or a Docker build**.
- Both candidate and fresh environments pass real CPU tensor inference, fixed
  token embeddings, padding-aware mean pooling, L2 normalization against an
  independent NumPy reference, attention against an explicit softmax reference,
  CPU tensor serialization and weights-only custom-global rejection. Fresh
  probe time is **4.999 seconds**; upgraded probe **3.844 seconds**. Runtime
  reports `torch.version.cuda=None` and `cuda.is_available()=False`. This is
  synthetic torch-substrate acceptance; **no SentenceTransformer, bge-m3 model,
  FAISS, retrieval, reranker, ingestion or model-quality acceptance is claimed**.
- After separate test additions **pytest 9.0.3 / PyMuPDF 1.26.7 / HTTPX 0.28.1**,
  the fresh test subset has **68 distributions** and passes `pip check`.
  Unchanged `test_simulator_panel.py`, `test_web_api_stage3.py`,
  `test_web_api_stage4_sim.py`, `test_web_api_stage5_deploy.py` and
  `test_web_api_round3_audit_fixes.py` pass **74 / skip 30 / two warnings in
  1.56 seconds**. JUnit identifies all 30 skips as absent `wh40k.sqlite`.
  No fixture, expectation, asset or skip was altered. Full native tests await
  the complete model/LangChain installation.
- Isolated **pip-audit 2.10.1** completes the exact **61-distribution** runtime
  audit with **zero findings and one explicit torch +cpu PyPI skip**. A second
  full inventory query maps **only torch 2.14.0+cpu to upstream 2.14.0**: **61
  distributions, zero findings, zero skips**. The complete test subset mapped
  the same way passes **68 / zero findings / zero skips**. A separate OSV audit
  of the **exact installed 2.14.0+cpu** passes **one / zero findings / zero skips**.
  All exit 0; raw JSON, complete exact inventories, alias grouping and skips
  are saved. No package/advisory was suppressed, and auditor packages are
  excluded from these app subset counts. The PT2 and earlier Streamlit sampling
  qualifications remain despite these registry results.

Ignored evidence and executable reproduction scripts are under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-8/`:
baseline bodies/groups, fresh OSV records, maintainer advisory/security policy,
release metadata, JIT issue/timeline/fix/tag comparisons and tagged sources;
official CPU index, hash-verified platform metadata and install reports/logs;
`jit-regression.py`/child and before/after JSON; `cpu-compatibility-probe.py`,
installed PT2 source and scan; runtime/test inventories, exact/mapped/OSV raw
audits and grouping; test log/JUnit, `reconcile-evidence.py`,
`summarize-evidence.py` and `verification-summary.json`.

Harness issues are visible: unauthenticated GitHub requests hit rate limits;
authenticated `gh api` retrieves the primary records. The CPU index's `download-r2`
metadata host returned 403; the official `download.pytorch.org` path succeeds
and its content hash matches. The first PT2 canary returned a Tensor where a
Parameter was required, causing a verifier error and Windows temporary-file
cleanup error; the corrected probe returns a Parameter and uses in-memory
archives. The owned leftover temporary directory was removed after process exit.
The first test invocation named nonexistent suite files, ran zero tests and is
retained; the corrected invocation uses the five existing suites above. Evidence
reconciliation initially assumed skipped records had versions, and Windows text
newline conversion invalidated downloaded metadata hashes; exact byte writes
restore verified hashes. An initial default-GBK install-report read failed and
was corrected to explicit UTF-8. None required production compatibility edits.
The initial CPU download interrupted once, resumed and completed with a
hash-verified wheel; it is not hidden as an uninterrupted transfer.

Reproduce in a **new Python 3.11 environment** using full interpreter paths:
`-m pip install -r requirements-bootstrap.txt`, then `-m pip install
--build-constraint requirements-bootstrap.txt -r requirements-torch-cpu.txt`,
then the server/Streamlit subset above. Run both saved probe scripts with new
JSON output filenames, `-m pip check`, and the five named suites after separate
test additions. Use the authorized proxy with localhost bypass, UTF-8 output,
retrieval/warmup disabled for API tests, and the separate auditor with exact
inventory pins, `--no-deps --disable-pip --format json`. Map the CPU version only
for the supplemental PyPI query and separately query the exact suffix via OSV.

Host integration must retain the separate CPU install step, recreate the complete
environment, and verify Linux installation and the final resolved embedding/
LangChain stack, trusted model/index loading, optional reranking, full native
suite, actual API image inventory/audit and live acceptance. The current
remaining family pins and production pytest separation still need work.
Actual scoped requirements/Dockerfile/report diff inspection and whitespace
validation pass. No commit, push, merge, Docker build/service change, external
knowledge-repository edit or deployment occurred. All owned subprocesses have
exited; no background server was started. Project knowledge handoff is here;
this iteration does **not** meet the overall release-stage stop condition.

## Earlier increment: Streamlit patch and advisory discrepancy — October 1, 2026

Native and Docker requirements now pin **Streamlit 1.59.0**, replacing the
native `>=1.35.0` declaration and Docker `==1.35.0`. Both actual auditor baseline
inventories contain **1.35.0**. CI/server requirements still omit Streamlit and
retain their no-model contract. No application/helper import, test expectation,
API reliability-owned file, Dockerfile or asset changed in this increment.
Python **3.11.9** was used throughout; 1.59.0 requires Python **>=3.10** and
publishes a platform-neutral wheel. Linux/Docker installation remains unverified.

Each baseline has **six records / three underlying Streamlit advisory groups**:

- [GHSA-rxff-vr5r-8cj5 / CVE-2024-42474](https://github.com/streamlit/streamlit/security/advisories/GHSA-rxff-vr5r-8cj5):
  Windows static-file path traversal; maintainer fix **1.37.0**.
- [GHSA-7p48-42j8-8846 / CVE-2026-33682](https://github.com/streamlit/streamlit/security/advisories/GHSA-7p48-42j8-8846):
  Windows component-path resolution can initiate SMB/NTLM traffic before
  validation; maintainer fix **1.54.0**. The installed 1.59.0 component path
  helper rejects UNC, slash-based network paths, parent traversal and drive
  paths **before any `os.path.realpath()` call**. A spy that raises on every
  resolution call establishes the ordering without attempting SMB access.
  A trusted temporary local component path still resolves correctly. This
  verifies the helper, not every HTTP route or external Windows credential behavior.
- [GHSA-vqwp-45wm-r9r5 / CVE-2026-10804](https://github.com/advisories/GHSA-vqwp-45wm-r9r5):
  cache collisions involving image palettes and deterministic large-object
  sampling. The registry reports **1.53.1** as fixed, but that is insufficient
  evidence for a complete fix; see the reproduction and remaining limitation.

**Verified registry discrepancy:** the clean **1.54.0** installation still
hashes two P-mode PIL images with identical pixel indices and different RGB
palettes identically. The same in-memory probe on installed **1.59.0** gives
different hashes. The primary [palette-fix PR #15397](https://github.com/streamlit/streamlit/pull/15397),
merged **June 4, 2026**, explicitly describes the palette correction and says
sampling was removed from that PR for follow-up. Saved tagged **1.58.0** source
lacks the palette correction; **1.59.0**, published July 6, contains it and its
history includes the fix commit. This is the first stable release containing
that demonstrated fix, rather than an arbitrary upgrade to latest **1.64.0**.
No older full application or production environment was installed or modified
for the probe; the before case is the isolated 1.54.0 candidate.

**Remaining sampling limitation:** 1.59.0 still produces identical cache hashes
for a 600,000-element NumPy array and a copy modified at a position omitted by
the deterministic seed-zero sample. The arrays are synthetic; all inputs are
in memory. Even tagged **1.64.0** retains seed zero as its default; its new
`runner.cacheHashSeed` option is not a full-content hash. Thus the completed
registry audits below do **not** establish that every behavior in this advisory
is fixed. Tracked production Python has only two Streamlit cache decorators:
`app.py::load_resources()` takes no arguments, and `build_bm25(_vectorstore)`
explicitly excludes its trusted local-index argument from hashing. Neither
receives user-controlled images, arrays or dataframes as hashed inputs; there
is no production `cache_data` use. This bounds application reachability, not
the library's sampling behavior. Keep this qualification if caching inputs
change; no advisory suppression or artificial hash override was introduced.

Validation actually completed:

- A new **clean-final-venv**, created with the prescribed Python 3.11.9
  executable, installs bootstrap, then `requirements-server.txt` plus
  **streamlit==1.59.0**, with the shared build constraint. Its complete **55**
  distributions include pip/setuptools and no pytest, model stack, JWT or
  Tornado. `pip check` passes. The earlier fresh 1.54.0 subset upgraded to
  1.59.0 and the project `.venv` also pass `pip check`.
- The clean subset resolves **Pillow 12.3.0, protobuf 7.36.2, pandas 3.0.6,
  Altair 6.3.0, PyArrow 25.0.1, NumPy 1.26.4, cachetools 7.2.0**, with
  **Starlette 1.3.1 / Uvicorn 0.39.0**. These are installed-version evidence,
  not new transitive constraints. An upgrade from 1.54.0 retained pandas
  2.3.3/protobuf 6.33.6/cachetools 6.2.6 and unused Tornado 6.5.10; clean
  installation is materially different and is the authoritative subset here.
  Full-family constraint/lock reconciliation is still outstanding.
- Real Streamlit **AppTest** runs preserve the unchanged sidebar function,
  compiled from its actual AST: both provider selections, password widget,
  defaults, missing-index warning and reload/rerun behavior. Synthetic chat
  exercises session history, `chat_input`, `chat_message`, `status`, streaming
  output and citation expander. The actual `ui.simulator_panel::_render_report`
  renders synthetic metrics, the Altair chart, exact funnel table values and
  unmodeled/bias disclosures. All existing app Streamlit attributes exist.
  The resource-cache probe verifies shared identity, excluded underscore input
  and `.clear()` invalidation. Both the upgraded and clean subsets pass.
  No fake production dependency or inference result was introduced; this does
  not import the full app, load models, or establish visual/browser acceptance.
- A real temporary **headless Streamlit** server, using the installed default
  Starlette/Uvicorn backend and existing shared API pins, returned health
  **200 / `ok`** and HTML index **200** on **127.0.0.1**. Its app was synthetic,
  telemetry disabled, proxy bypassed, and the owned process terminated and
  waited in `finally`. No owned probe process remains; user Docker services
  were untouched.
- Unchanged `test_simulator_panel.py` and the four earlier API suites pass
  **74 tests / 30 skips / two warnings**, in **1.54 seconds** in the fresh
  subset and **1.84 seconds** in the project environment. All 30 skips are
  missing `wh40k.sqlite`; no assets, skips or expectations changed. Test-only
  installs add seven distributions, including **pytest 9.0.3, PyMuPDF 1.26.7,
  HTTPX 0.28.1**; the **62**-distribution test subset passes `pip check`.
- Separate **pip-audit 2.10.1** runs completed for the exact installed runtime
  subset (**55**), test subset (**62**) and project subset (**69**): each exits
  **0**, with **zero findings and zero skipped packages**. Full inventories,
  raw JSON, exit codes and connected alias-group outputs are retained. Audit
  tool dependencies are not counted. These are subset registry results, with
  the independently reproduced sampling limitation preserved above; they are
  not a clean complete native/Docker application audit.

Evidence and executable reproduction scripts are ignored and local under
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-7/`:
maintainer advisories, original baseline records/groups, registry metadata,
official release notes, tagged sources and fix history; clean/bootstrap/project/
test installation reports and logs; `inventory.py`, all three inventory/pin/audit
sets; `cache-security-probe.py` and before/after JSON;
`streamlit-compatibility-probe.py`, `server-smoke.py` and their outputs;
both test logs/JUnit XML; `summarize-evidence.py` and `verification-summary.json`.
AppTest failure logs are retained. Harness-only problems encountered include
an initial wrong upstream handler path returning 404, AppTest initially lacking
the repository import path, and the first chart assertion using the old internal
`arrow_vega_lite_chart` name (the real
1.59.0 type is `vega_lite_chart`). A final clean inventory exposed the probe's
incorrect assumption that Tornado remained installed. These harness-only
errors were corrected transparently; no production shim or test weakening
was needed. An initial PowerShell-quoted one-line inventory command failed
with `SyntaxError`; the saved standalone `inventory.py` replaced it.

Reproduce using the prescribed base interpreter's `-m venv`, the new
environment's **full executable path**, `-m pip install -r
requirements-bootstrap.txt`, then `-m pip install --build-constraint
requirements-bootstrap.txt -r requirements-server.txt streamlit==1.59.0`.
Run both compatibility/cache scripts with new JSON output paths, the server
smoke, and `-m pip check`. Separately install the three test pins above before
running the five named suites with `-m pytest -q`. Generate the complete exact
inventory with `inventory.py`; audit it with the separate tool interpreter,
`--no-deps --disable-pip --format json`. Use UTF-8, retrieval/warmup disabled
for API tests, and the authorized proxy with localhost bypass for downloads.

The actual two-requirement/report diff and
`git -c core.whitespace=cr-at-eol diff --check` pass. No commit, push, asset
generation, host knowledge-repository edit or deployment occurred. The project
knowledge handoff is contained here. Full CPU/LangChain/model dependency
resolution, runtime/dev separation, full native tests, Linux/Docker and final
asset/live/browser integration gates remain outstanding. Host should recreate
environments, verify the new Streamlit server backend and retained retrieval,
and preserve the sampling qualification rather than rely on a green registry.

## Earlier increment: unused provider SDK and PyJWT boundary — October 1, 2026

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


The iteration 3 explicit stop hook subsequently authorizes the deduplicated
local knowledge handoff. `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and
`ROADMAP.md` now record the supported replacement, exact checks and remaining
Linux/source/host gates. The existing platform-membership decision in
`C:/Users/Administrator/learn-notes/decisions/` is extended; the existing
`C:/Users/Administrator/error-notes/common/20260921-error-41-python-stdout-gbk.md`
is extended with this UTF-8 installer-input recurrence, exact failure and
verified explicit-encoding resolution. Both existing index lines are updated.
No duplicate note, empty entry, invented commit explanation or harness promotion
is created. Unrelated note bodies and Git indexes are preserved; no manual
staging, commit or publication occurs. `iteration3/hook-knowledge-handoff.json`
records exact paths, hashes and checks. Root retains knowledge publication.

## Iteration 4 knowledge handoff and concurrent native-owner status

The explicit post-implementation knowledge handoff updates only project checkpoint/roadmap, the existing platform-membership decision and its index, three distinct resolved rehearsal-error records and their index. Earlier tmpfs noexec, hf-xet read-only logging and GBK/UTF-8 records remain unchanged; no duplicate record or harness promotion is made. Full prior bodies and Git indexes are guarded/preserved. Paths and hashes are saved in `C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/full-stack/iteration4/hook-knowledge-handoff.json`. No package installation, application/test edit, manual staging/commit/push or publication is part of this handoff.

The latest concurrent native recovery supersedes historical pending-fix prose: the report now exists at `D:/Project/py/RAG/docs/superpowers/reports/2026-10-01-native-build-recovery-acceptance.md` and records **3,235 Windows CI passes / 418 unchanged skips / zero failures/errors**, all original44 passing and 238 broader passes/41 asset skips. Read-only actual main Git confirms merge **4092507822d699acafb513d05c07e5214357e58a**, titled "Merge reviewed native SQLite recovery and standalone source fixtures". The old assigned-worktree report path is no longer present; its current Git history belongs to subsequent coordinated work. Do not mutate/recreate that owner checkout or call its old snapshot the current branch.

This concurrent report/merge does not change the dependency candidate's preserved native/CI results, imply a combined final-family rerun, or extend independent review to this complete dependency candidate. The original fixture/lifecycle failures need integration here, rather than another overlapping implementation. Root retains integration/review/hosted CI and actual asset/build/live/browser/deployment gates. GNHF owns the current two-file scoped commit; no iteration-4 commit ID or explanation is invented. All run-owned processes remain stopped.
