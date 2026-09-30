# Python dependency security acceptance — September 30, 2026

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
The complete CPU application stack, full native suite, Docker/Linux installation
and final audit remain outstanding.
No integration, deployment, source retirement or main-environment changes occurred.

## Latest increment: python-dotenv patch and Windows text verification — October 1, 2026

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
