# API reliability implementation acceptance

Status: **partial, iteration 1 — vector readiness only**. One of the four assigned reliability defects is resolved with a current-base reproduction and paired passing regressions. This report does not establish release acceptance; independent host review, integration and asset-dependent/live acceptance remain required.

## Isolated scope and baseline

Worktree: `C:/Users/Administrator/.codex/worktrees/release-api-reliability/RAG`. Branch: `codex/release-api-reliability`. Clean starting HEAD: `b90e8610d` (the saved source-retirement preparation handoff). Current source retirement policy and consumers were preserved. No main-checkout edits, production asset writes, dependency installs, commits, pushes, merges or deployment were performed.

Tests execute with `D:/Project/py/RAG/.venv/Scripts/python.exe`, verified as Python **3.9.1**. A direct import check confirmed `web_api.preflight.__file__` resolves to this worktree. New tests retain future annotations. No model settings or credentials were changed or printed.

All local evidence for this slice is under:

`C:/Users/Administrator/.codex/worktrees/release-api-reliability/RAG/db_sources/release-check-20260930/api-reliability/iteration-01/`

## Defect 3: incomplete FAISS store reported ready

The unchanged implementation used `index.faiss.exists()` alone. The temporary-root reproduction supplied a nonempty `index.faiss`, omitted `index.pkl`, and satisfied the existing other required presence checks. Before implementation, `summary(root)` returned **ready=true** and `vector_store.ok=true`; after implementation the identical setup returned **ready=false** and `vector_store.ok=false`, with `index.pkl` explicitly named in the detail. Evidence: `reproduce_preflight.py`, `preflight-before.json`, `preflight-after.json`. The reproduction exercises presence checks and does not claim its dummy index bytes are loadable.

`check_assets` now requires both `index.faiss` and `index.pkl` to be regular, nonempty files. The existing asset name, path, required flag and mounting hint remain intact. All failed components are named in the diagnostic, which flows through the existing summary and startup report. No FAISS unpickling or model loading was added to preflight.

The paired positive test now generates both files through real `FAISS.save_local` with model-free `FakeEmbeddings`, reopens them through `FAISS.load_local`, and verifies both the vector count and the stored document. Deserialization is enabled only for artifacts the test just created in its temporary directory. The previous positive test incorrectly used an empty index with no pickle; its readiness assertions remain intact, with a valid vector fixture substituted.

Six independent negative cases remove, empty or replace with a directory each of the two required components. Each checks readiness, the vector required flag, the failing filename in both asset detail and formatted report, and continued success of all other asset checks. Additional cases verify default startup still returns an honest false readiness/log, strict startup rejects the partial store, and retrieval-off deployment remains ready while reporting the vector store absent and optional. Existing missing-asset, mount/configuration, retrieval toggle and rate-limit checks continue to pass.

This is a file presence/type/size guard, not an arbitrary-corruption audit. Nonempty damaged files can still fail loading; existing warmup/error reporting remains responsible for runtime loading failures and was not changed. The positive fixture validates the vector store, not a real embedding model or database.

## Validation evidence

| Check | Result | Local evidence |
| --- | --- | --- |
| New paired checks against unchanged application code | **8 failed, 1 passed**, 35 deselected | `preflight-baseline-red.log` |
| Deployment/preflight suite after implementation | **44 passed**, no skips, 8 FAISS/SWIG deprecation warnings | `preflight-focused-green.log` |
| Native suite excluding the existing local-model retrieval suite | **2,549 passed, 328 skipped, 16 warnings**, exit 0, 130.40 seconds | `native-suite.log`, `native-summary.json` |
| Syntax compilation of both changed Python files, without writing bytecode | Passed | Direct interpreter check |
| Actual source diff and `git -c core.whitespace=cr-at-eol diff --check` | Inspected and passed | Direct Git check |
| Ruff availability | Unavailable (`find_spec('ruff')` returned None); no dependencies installed | Direct interpreter check |

The native command was `D:/Project/py/RAG/.venv/Scripts/python.exe -m pytest -q --ignore=tests/test_app_retrieval.py -ra` from this worktree. The summary reconciles all **328** skipped cases against their log entries, preserves each exact test location and groups counts by file. These are existing skip guards for absent canonical SQLite/Black Library data, local PDF/refined/official-name/cache/inventory inputs and local application dependencies; no new skip or weakened assertion was added. The two skipped simulator-panel cases depend on absent SQLite, and a local retrieval import in the audit suite remains local-only. The explicitly ignored app retrieval suite requires the local model/application assets and is outside this model-free run; this is not a full production-asset test claim.

PowerShell redirection garbled Chinese text from the subprocess output. English results and test locations/counts remain intact; `native-summary.json` also records the exact UTF-8 skip declarations read from the relevant test sources for host inspection. Those declarations are identified as source declarations rather than misrepresented as runtime messages. No tests failed. The final Git status contains only the preflight implementation, its deployment tests and this report; no generated wiki or source-retirement diff appeared. The test process completed and was reaped before delivery.

## Remaining iteration scope and host acceptance

Defects 1 (loop exception/evidence retention), 2 (capability fallback and SDK transport amplification/timeouts), and 4 (quoted-string-safe JSON extraction) remain unimplemented and have not been recreated in this worktree by this iteration. Future slices must reproduce each on their current base before changing the owned code, retain paired positive/negative evidence, and append exact results here. Real SDK request counts and chosen timeout bounds are consequently **not yet measured or selected** here. The host baseline `db_sources/release-check-20260930/host/structurer-fallback-baseline.json` was not edited.

No server, browser, watcher or other persistent process was started. Temporary fixture assets are confined to pytest/temporary directories; evidence writes are confined to this worktree's ignored evidence directory. The host owns knowledge-repository updates and publication. Integration must preserve concurrent source-retirement work and obtain independent review, full production-asset acceptance, readiness/warmup checks and fresh deployed HTTP behavior. The four-defect stop condition is not met.

## Scoped knowledge handoff to the host

The stop-hook handoff audit read the existing `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`, the learning/error repository templates, and searched Markdown records in the project devlog, learn-notes and error-notes/rag for `index.pkl`, `FAISS readiness`, `incomplete FAISS`, `api-reliability` and `release-api-reliability`. No matching record was found at this audit. Recheck before publishing because another worker may add records later. The implementation objective explicitly assigns those repositories to the host; this worker leaves their current files and unrelated edits untouched.

For the host's checkpoint/roadmap update, record defect 3 as locally implemented and tested, with the before/after false-readiness evidence and exact suite results above. Keep the other three defects, real SDK transport counting/timeout selection, independent review and production-asset/live integration open. No implementation commit exists yet: the orchestrator creates it after this handoff. A later explanation under `commits/` must name that actual commit, not starting HEAD `b90e8610d` as if it contained this fix.

Reusable learning candidate for `learn-notes/wins/` or `decisions/`: asset readiness must enumerate every file consumed by the actual loader; test a genuine saved/reopened artifact positively and damage each required component independently. A fixture consisting only of an empty file can encode the bug rather than establish readiness. Use template metadata `date: 2026-09-30`, `project: wh40k-oracle`, `status: raw`, and an empty `promoted_to` until the host chooses a verified destination. This observation is evidenced here; no cross-project rule or skill promotion is claimed.

Resolved underlying error candidate for `error-notes/rag/`: **FAISS preflight reports ready without its docstore pickle**. Environment: Windows/PowerShell, shared Python 3.9.1 interpreter, isolated worktree, model-free FAISS fixture, no provider/network calls. Reproduce by saving a temporary FAISS store, satisfying the other preflight presence checks, removing `index.pkl`, and calling `preflight.summary(root)`. The unchanged-base regression reports:

```text
test_preflight_rejects_incomplete_vector_store[missing-index.pkl]
>       assert info["ready"] is False
E       assert True is False
tests\test_web_api_stage5_deploy.py:218: AssertionError
```

The complete failure context is retained in `preflight-baseline-red.log`. The attempted fix was the narrow two-component regular/nonempty-file guard; it passed on the first application implementation, with all eight previously failing regression cases resolved and the real saved/reopened positive fixture retained. No unrelated repair or invented attempt should be added. The final resolution, reproduction command, limitations and evidence paths are recorded above. Choose the record number only after inspecting the host repository's current index, then update that index and publish only the intended note changes under its own instructions. PowerShell output encoding is a separate observed handoff limitation; it was handled by preserving locations/counts and reading UTF-8 source declarations, and is not claimed as a resolved general subprocess encoding defect.
