# API reliability implementation acceptance

Status: **partial, iteration 2 — vector readiness and JSON parsing**. Two of the four assigned reliability defects are resolved with current-base reproductions and paired passing regressions. This report does not establish release acceptance; independent host review, integration and asset-dependent/live acceptance remain required.

## Isolated scope and baseline

Worktree: `C:/Users/Administrator/.codex/worktrees/release-api-reliability/RAG`. Branch: `codex/release-api-reliability`. Iteration 1 clean starting HEAD: `b90e8610d` (the saved source-retirement preparation handoff). Iteration 2 clean starting HEAD: `45aa36ffe`, which includes the readiness fix and its handoff. Current source retirement policy and consumers were preserved. No main-checkout edits, production asset writes, dependency installs, manual commits, pushes, merges or deployment were performed. The GNHF orchestrator owns iteration commits.

Tests execute with `D:/Project/py/RAG/.venv/Scripts/python.exe`, verified as Python **3.9.1**. A direct import check confirmed `web_api.preflight.__file__` resolves to this worktree. New tests retain future annotations. No model settings or credentials were changed or printed.

All local evidence for this slice is under:

`C:/Users/Administrator/.codex/worktrees/release-api-reliability/RAG/db_sources/release-check-20260930/api-reliability/iteration-01/`

## Defect 3: incomplete FAISS store reported ready

The unchanged implementation used `index.faiss.exists()` alone. The temporary-root reproduction supplied a nonempty `index.faiss`, omitted `index.pkl`, and satisfied the existing other required presence checks. Before implementation, `summary(root)` returned **ready=true** and `vector_store.ok=true`; after implementation the identical setup returned **ready=false** and `vector_store.ok=false`, with `index.pkl` explicitly named in the detail. Evidence: `reproduce_preflight.py`, `preflight-before.json`, `preflight-after.json`. The reproduction exercises presence checks and does not claim its dummy index bytes are loadable.

`check_assets` now requires both `index.faiss` and `index.pkl` to be regular, nonempty files. The existing asset name, path, required flag and mounting hint remain intact. All failed components are named in the diagnostic, which flows through the existing summary and startup report. No FAISS unpickling or model loading was added to preflight.

The paired positive test now generates both files through real `FAISS.save_local` with model-free `FakeEmbeddings`, reopens them through `FAISS.load_local`, and verifies both the vector count and the stored document. Deserialization is enabled only for artifacts the test just created in its temporary directory. The previous positive test incorrectly used an empty index with no pickle; its readiness assertions remain intact, with a valid vector fixture substituted.

Six independent negative cases remove, empty or replace with a directory each of the two required components. Each checks readiness, the vector required flag, the failing filename in both asset detail and formatted report, and continued success of all other asset checks. Additional cases verify default startup still returns an honest false readiness/log, strict startup rejects the partial store, and retrieval-off deployment remains ready while reporting the vector store absent and optional. Existing missing-asset, mount/configuration, retrieval toggle and rate-limit checks continue to pass.

This is a file presence/type/size guard, not an arbitrary-corruption audit. Nonempty damaged files can still fail loading; existing warmup/error reporting remains responsible for runtime loading failures and was not changed. The positive fixture validates the vector store, not a real embedding model or database.

## Iteration 1 validation evidence

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

## Defect 4: quoted braces broke noisy JSON extraction

Iteration 2 reproduces both parsers on unchanged application HEAD `45aa36ffe`. The agent input `prefix: {"type": "final", "content": "Literal } in content"} trailing` raised `JSONDecodeError: Unterminated string starting at: line 1 column 30 (char 29)`. The equivalent structurer input with nested `verdict.lede` raised `JSONDecodeError: Expecting ',' delimiter: line 1 column 45 (char 44)`. Both objects are valid JSON; the manual brace counter extracted a truncated substring because it counted the closing brace inside the string.

Before/after inputs, expected/actual objects and exact exceptions are preserved in `json-before.json` and `json-after.json`, produced by the same `reproduce_json.py` script. These files are in this worktree's ignored evidence directory:

`C:/Users/Administrator/.codex/worktrees/release-api-reliability/RAG/db_sources/release-check-20260930/api-reliability/iteration-02/`

Both parsers retain the full-text `json.loads` path and existing fence removal. When surrounding noise requires extraction, they now call `JSONDecoder.raw_decode` at the first object delimiter. This delegates quoted strings/escaping to the JSON decoder and ignores only trailing content after the decoded object. It does not search subsequent delimiters to salvage an invalid first object. The agent's required `type` field, both object-type checks, formatter slot validation/prose fallback and existing one-retry policy for genuinely invalid agent output are preserved. Parser exceptions remain `ValueError` subclasses; the decoder now supplies the precise malformed-JSON diagnostic.

The new regression suite checks closing/opening braces and escaped quotes/backslashes inside strings across three noisy/fenced wrappers, nested objects and citation arrays; truncated strings/objects, invalid escapes/trailing commas, an invalid first object followed by a valid object, absent JSON, nonobjects and missing agent type. Injected-client integration checks preserve complete final sources and structured slots, and establish that a valid noisy agent response requires **one application call**, without a parse retry. A wrong verdict shape still yields the original prose through the formatter. These application counts do **not** measure SDK transport retries or resolve defect 2.

The unchanged-code regression run produced **21 failed, 25 passed** in 2.49 seconds (`json-baseline-red.log`). After the narrow implementation, the JSON/client/loop/formatter focused suite produced **126 passed, 9 skipped, 5 warnings** in 1.58 seconds (`json-focused-green.log`). All nine skips are existing `wh40k.sqlite` absence guards in `tests/test_web_api_stage3.py`; no new skips or weakened prior assertions were added. Exact direct reproductions now return both expected objects successfully.

Syntax compilation of the two runtime files and new regression file passed without writing bytecode. Direct import checks resolve both runtime modules to this worktree. Source inspection confirms the application diff only replaces the two manual balancing loops with decoder calls; no provider/model/thinking settings, source-retirement code or active assets were changed.

## Iteration 2 native validation and handoff

The available model-free native suite passed **2,595 tests, 328 skipped, 15 warnings**, exit 0, in **171.70 seconds**. Command: `D:/Project/py/RAG/.venv/Scripts/python.exe -m pytest -q --ignore=tests/test_app_retrieval.py -ra --junitxml=<iteration-02>/native-junit.xml`, run from this isolated worktree. The ignored retrieval suite requires local model/application assets and is not claimed as tested. `run_validation.py` records the full command and working directory in `native-summary.json` and captures subprocess bytes directly in `native-suite.log`, avoiding the earlier PowerShell encoding loss. `native-junit.xml` and the JSON summary preserve every actual UTF-8 runtime skip message and test identity; all **328** XML skips reconcile to the suite count.

| Existing skip category | Count |
| --- | ---: |
| Absent canonical SQLite, including combined DB/Black Library or DB/wiki dependencies | 290 |
| Absent local CSV caches | 8 |
| Absent pre-retirement inventory | 1 |
| Absent official PDF/manifest inputs | 19 |
| Absent core-rule refined output | 6 |
| Absent quick-reference PDF | 4 |
| **Total** | **328** |

The new parser regressions add **46 passing cases** relative to iteration 1, with the same skip count. Ruff remains unavailable in the shared environment; no formatter/linter dependencies were installed. Syntax compilation, actual source/new-test/report inspection and `git -c core.whitespace=cr-at-eol diff --check` passed. Final scoped changes are the two parser implementations, `tests/test_llm_json_parsing.py` and this report. All test subprocesses finished and were reaped; no persistent server/browser/watcher was started. Fixtures/evidence remain within temporary test output and this worktree, with production database/wiki/index/source inputs untouched.

Host knowledge handoff addition: record quoted-string brace balancing as the second resolved underlying defect, citing the exact before/after decoder errors and paired regressions above. The reusable lesson is to let the JSON decoder determine the end of an object rather than count syntax characters in text. Preserve the existing first-object and schema boundaries when tolerating noise; otherwise a parser fix can silently begin accepting invalid responses. Formal independent review, host integration, asset-dependent checks and fresh deployed HTTP acceptance remain pending.

The iteration 2 stop-hook audit read the current shared checkpoint/roadmap and both repository templates, then searched all Markdown records under `D:/Project/devlog/wh40k-oracle`, `C:/Users/Administrator/learn-notes` and `C:/Users/Administrator/error-notes/rag` for `raw_decode`, quoted braces, brace counting, `Unterminated string starting`, `api-reliability` and `JSONDecoder`. It found **zero matching lines**. This is a point-in-time duplicate check, not a guarantee against concurrent host additions. Shared repository writes/publication remain assigned to the host by this task's isolated ownership boundary.

For a learning record in `learn-notes/wins/`, use the repository template with `date: 2026-09-30`, `project: wh40k-oracle`, `status: raw` and empty `promoted_to`. Suggested title: **Decode noisy JSON with the JSON parser to preserve quoted delimiters**. Background, reusable procedure and verification are recorded in the defect 4 section. The actionable recipe is to keep full-document validation first, decode noisy responses at the intended object delimiter, and separately test schema checks and malformed/incomplete rejection. No harness rule or skill promotion is warranted for this localized implementation repair.

For one underlying error record in `error-notes/rag/`, use the existing error template and the title **Agent and structurer truncate valid JSON at quoted braces**. Include Windows/PowerShell, Python 3.9.1, unchanged application base `45aa36ffe`, the exact errors in `json-before.json`, and complete tracebacks from `json-baseline-red.log`. Reproduce with the saved script on the base or the new tests against unchanged parser code. The attempted application fix was replacement of both manual counters with `JSONDecoder.raw_decode`; it passed on its first implementation. Do not invent additional failed repair attempts. Record the 21 failing/25 passing baseline, 46 now-passing new cases, focused/native results, continued invalid/schema rejection and the SDK-count limitation. Select the actual dated error number and update the index only after rechecking the host repository. Any commit explanation must wait for the real GNHF JSON implementation commit; `45aa36ffe` contains the readiness slice, not this parser fix.

## Remaining iteration scope and host acceptance

Defects 1 (loop exception/evidence retention) and 2 (capability fallback and SDK transport amplification/timeouts) remain unimplemented and have not been recreated in this worktree by these iterations. Future slices must reproduce each on their current base before changing the owned code, retain paired positive/negative evidence, and append exact results here. Real SDK request counts and chosen timeout bounds are consequently **not yet measured or selected** here. The host baseline `db_sources/release-check-20260930/host/structurer-fallback-baseline.json` was not edited.

No server, browser, watcher or other persistent process was started. Temporary fixture assets are confined to pytest/temporary directories; evidence writes are confined to this worktree's ignored evidence directory. The host owns knowledge-repository updates and publication. Integration must preserve concurrent source-retirement work and obtain independent review, full production-asset acceptance, readiness/warmup checks and fresh deployed HTTP behavior. The four-defect stop condition is not met.

## Scoped knowledge handoff to the host

The stop-hook handoff audit read the existing `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`, the learning/error repository templates, and searched Markdown records in the project devlog, learn-notes and error-notes/rag for `index.pkl`, `FAISS readiness`, `incomplete FAISS`, `api-reliability` and `release-api-reliability`. No matching record was found at this audit. Recheck before publishing because another worker may add records later. The implementation objective explicitly assigns those repositories to the host; this worker leaves their current files and unrelated edits untouched.

For the host's checkpoint/roadmap update, record defects 3 and 4 as locally implemented and tested, with their before/after evidence and exact suite results. Keep defects 1 and 2, real SDK transport counting/timeout selection, independent review and production-asset/live integration open. The orchestrator committed the readiness slice as `45aa36ffe`; the JSON slice awaits its own iteration commit. A later explanation under `commits/` must name the actual implementation commit, not starting HEAD `b90e8610d` as if it contained either fix.

Reusable learning candidate for `learn-notes/wins/` or `decisions/`: asset readiness must enumerate every file consumed by the actual loader; test a genuine saved/reopened artifact positively and damage each required component independently. A fixture consisting only of an empty file can encode the bug rather than establish readiness. Use template metadata `date: 2026-09-30`, `project: wh40k-oracle`, `status: raw`, and an empty `promoted_to` until the host chooses a verified destination. This observation is evidenced here; no cross-project rule or skill promotion is claimed.

Resolved underlying error candidate for `error-notes/rag/`: **FAISS preflight reports ready without its docstore pickle**. Environment: Windows/PowerShell, shared Python 3.9.1 interpreter, isolated worktree, model-free FAISS fixture, no provider/network calls. Reproduce by saving a temporary FAISS store, satisfying the other preflight presence checks, removing `index.pkl`, and calling `preflight.summary(root)`. The unchanged-base regression reports:

```text
test_preflight_rejects_incomplete_vector_store[missing-index.pkl]
>       assert info["ready"] is False
E       assert True is False
tests\test_web_api_stage5_deploy.py:218: AssertionError
```

The complete failure context is retained in `preflight-baseline-red.log`. The attempted fix was the narrow two-component regular/nonempty-file guard; it passed on the first application implementation, with all eight previously failing regression cases resolved and the real saved/reopened positive fixture retained. No unrelated repair or invented attempt should be added. The final resolution, reproduction command, limitations and evidence paths are recorded above. Choose the record number only after inspecting the host repository's current index, then update that index and publish only the intended note changes under its own instructions. PowerShell output encoding is a separate observed handoff limitation; it was handled by preserving locations/counts and reading UTF-8 source declarations, and is not claimed as a resolved general subprocess encoding defect.
