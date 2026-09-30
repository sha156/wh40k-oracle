# Security boundary correction acceptance

Iteration 1 corrects the supplied-Origin execution boundary and its adjacent raw-Host rate-limit classification defect. The model argument boundary, provider exception disclosure and invalid wiki NUL path remain open. This report is an incremental checkpoint, not release acceptance.

The owned worktree is `C:/Users/Administrator/.codex/worktrees/release-official-revisions/RAG`, branch `codex/release-security-boundaries`, starting at exact commit `ee8df0bc0ba360594452a3cdc70ddcae6ff93909`. These changes are uncommitted at handoff; GNHF owns the automatic commit. No new commit ID is asserted. The original official-revision branch, main checkout, services, assets, gold and dependency manifests were not changed. Note repositories received only the subsequent explicit stop-hook documentation additions described below.

## Result and preserved behavior

`OriginBoundaryMiddleware` is a body-independent ASGI gate outside CORS and rate limiting. It rejects any supplied Origin that is absent from the exact configured UI allowlist, as well as duplicate Origin headers, with HTTP 403 and a stable response that does not reflect header input. Empty, wildcard and `null` entries cannot grant access. It consumes no request body and invokes no protected handler. No-Origin requests retain their existing local CLI/service behavior. The same `_ALLOWED_ORIGINS` configuration feeds CORS and this boundary; no wildcard or regex origin acceptance was added.

Paired tests exercise the real registered `/chat/sync`, `/chat`, `/simulate`, `/roster/critique` and `/roster/validate` routes with harmless substitute handlers. Foreign-Origin requests with JSON bytes and no Content-Type never invoke those handlers after the fix. Both default UI origins and no-Origin clients still invoke them. Session ID, context and question reach the chat handler unchanged; SSE content type, done event and stream headers are retained. Handler error responses retain their status, body and allowed-Origin CORS headers. Custom configured origins work by exact match; unconfigured defaults are rejected. Allowed preflights execute no handler and consume no quota. Allowed-Origin 429 responses retain CORS and Retry-After headers.

Rate-limit routing now uses `request.scope['path']`. On the baseline Starlette distribution, raw Host values `localhost/healthz?` and `localhost/ordinary?` previously changed exempt/heavy classification, while `[invalid` raised a URL parsing exception. After the fix, `/simulate` consistently uses its heavy quota and `/healthz` remains exempt for all tested Host values. This preserves existing route prefixes and X-Forwarded-For policy.

This boundary is not client authentication: a caller able to omit or forge Origin remains outside its browser-Origin purpose. Browser local-network permission behavior was neither bypassed nor certified. No cloud authentication, real prompt-injection execution, universal security or deployed acceptance is claimed.

## Environment and evidence

Independent source evidence came from `D:/Project/py/RAG/db_sources/release-check-20260930/host/security-boundaries/85892fa2a/`. Its report and six probe scripts/results were copied into the owned ignored directory `db_sources/security-boundaries/iteration-01/frozen/`; `copy-manifest.json` confirms all seven SHA-256 source/copy pairs match. Only synthetic credentials occur in those frozen probes. Their reported source commit `85892fa2a3bc4d9726dc26f367018a3a33dd307c` is distinct from this implementation baseline.

The authorized read-only interpreter `C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/.venv/Scripts/python.exe` is Python 3.11.9 with FastAPI 0.133.0, Starlette 1.3.1, HTTPX 0.28.1, pytest 9.0.3 and OpenAI 2.54.0. FastAPI 0.133.0 rejects absent Content-Type with 422 on the unchanged app; it therefore does not reproduce the frozen distribution's exact simple-POST behavior. JSON Content-Type requests still reproduced foreign-Origin handler execution. The other authorized full-stack-windows-server interpreter lacked HTTPX, pytest, OpenAI and retrieval test packages when checked; it was not modified.

To reproduce the actual retained distribution without weakening any route setting, a confined disposable Python 3.11.9 environment was created at:

`D:/Project/py/RAG/db_sources/release-check-20260930/security-boundary-worktree-environments/origin-baseline-py311/`

Its full executable is `Scripts/python.exe` under that directory. Only FastAPI 0.128.8 and Starlette 0.49.3 were installed there with `--no-deps`, using the required proxy. These match the retained dependency manifest and locally observed baseline distribution. A local `.pth` file adds the authorized frozen interpreter's site-packages as a read-only fallback for pytest, HTTPX, Pydantic and other test dependencies. Neither shared environment was installed into or changed. No project dependency file was modified; this is a targeted test environment, not a full production dependency rehearsal. Processes ran with `-B`/`PYTHONDONTWRITEBYTECODE=1`, `WEB_API_WARMUP=0`, and `WEB_API_RETRIEVAL=off`.

The final test file `tests/test_web_api_origin_boundary.py` has SHA-256:

`e329aa27f049e6eb5920f0f5347e8c5d81036a1bdc464bb6115089bbab1dfefc`

The final immutable comparison uses the same file and same interpreter on both sides. The ignored `recheck_baseline.py` extracts exact baseline `web_api/main.py` and `web_api/ratelimit.py` blobs into a confined package overlay, checks the actual imported file paths, and uses unchanged worktree supporting modules. The newly added middleware module is available for its direct unit tests in that overlay, but is absent from the original main middleware stack. Thus the 18 baseline integration failures establish the execution/classification defects; direct tests of the new class are not described as old-code failures.

| Check | Actual result | Owned ignored evidence |
| --- | --- | --- |
| Final test file against verified exact baseline imports | 18 failed, 23 passed | `immutable-baseline-verified.log`, `immutable-baseline.xml`, `immutable-baseline-manifest.json` |
| Same final test file after correction | 41 passed | `immutable-after.log`, `immutable-after.xml` |
| Available focused API, limiter, simulation, roster, session and bounded agent recovery checks | 540 passed, 30 skipped, 9 deselected | `available-focused.log`, `available-focused.xml` |
| Selected boundary checks with frozen FastAPI 0.133 / Starlette 1.3.1 | 24 passed, 17 deselected | `newer-stack.log`, `newer-stack.xml` |

All paths in the evidence column are relative to `db_sources/security-boundaries/iteration-01/`. Existing deprecation warnings remain visible in the logs.

The available focused command selects these seven test modules: `test_web_api_origin_boundary.py`, `test_web_api_stage3.py`, `test_web_api_stage5_deploy.py`, `test_web_api_stage4_sim.py`, `test_web_api_roster.py`, `test_sessions.py` and `test_agent_loop_recovery.py`. Its `-k` excludes `preflight_detects_present_assets`, `preflight_rejects_incomplete_vector_store`, `preflight_incomplete_vector_store_refuses_strict_start` and `preflight_partial_index_is_optional_with_retrieval_off` (nine parameterized tests). Those require absent LangChain/FAISS dependencies. The 30 skips are the existing missing real database/asset guards; no tests were changed to add skips or to hide failures. No full asset suite result is claimed. Ruff is absent in the test environments; syntax/import execution and `git diff --check` provide the available source checks.

Earlier attempted runs are retained for audit: `before.log` used the newer distribution and exposed its Content-Type difference; `baseline.log` included three incorrect test assertions about the response's `meta` field, corrected to the actual public `degraded` field before implementation; `baseline-corrected.log` then recorded 18 failed/18 passed for the original 36 cases before the source fix. Five direct preservation tests were subsequently added. `focused.log` selected a nonexistent session test filename and collected nothing. `focused-valid.log` then recorded 112 passed/30 skipped plus nine missing-LangChain setup errors. An initial `immutable-baseline.log` incorrectly loaded the current package during test discovery and passed 41; it is not baseline proof. The runner now imports and asserts baseline module paths before discovery; the verified log is the acceptance evidence. These attempted outcomes were not relabeled as successful checks.

## Remaining work and host gates

1. Reproduce and correct arbitrary internal kwargs passed through model tool dispatch. Audit every registered tool against its intended public argument contract, retaining legitimate direct Python injection helpers and bounded evidence recovery.
2. Reproduce the real OpenAI SDK synthetic key echo with HTTPX MockTransport in this worktree. Correct public provider failure text across sync/SSE/steps/history/source metadata while preserving categorical failures, useful facts, citations and source notes.
3. Reproduce and correct `/wiki/%00` as a deliberate 404/422, with present positive fixtures and confinement regression checks.
4. Complete the combined focused/available checks and update this report with actual GNHF commit IDs after they exist. The worktree is intentionally dirty before the orchestrator's commit; clean status after that commit is not yet claimed.
5. Host/root code, Python and security reviews, deployed/browser/full-asset acceptance and CI remain required. Root owns final knowledge-note publication. The subsequent explicit stop hook authorizes the scoped local note handoff recorded below; no note staging/commit/push was performed.

No dev server, browser, watcher, container or persistent background process was started. TestClient portals were closed and command processes completed. No real provider call or credential read was needed for this iteration.

## Explicit stop-hook knowledge handoff

After the implementation, the explicit stop hook authorized local knowledge updates. Read-only duplicate searches covered `D:/Project/devlog/wh40k-oracle`, `C:/Users/Administrator/learn-notes` and `C:/Users/Administrator/error-notes`. The existing `rag/error-13-cors-origin-port-mismatch.md` concerns an omitted UI port and browser response-access failure; it does not duplicate the foreign-Origin execution defect. No existing Origin execution/Host classification entry or matching learning record was found. The installed learning/error templates were read before writing English entries.

The hook-only documentation scope adds a new top checkpoint/roadmap slice under `D:/Project/devlog/wh40k-oracle`, preserving all earlier owners' text; a learning decision at `C:/Users/Administrator/learn-notes/decisions/20261001-enforce-origin-before-handler-execution.md`; and two separate underlying issue records at `C:/Users/Administrator/error-notes/rag/20261001-error-15-cors-allows-foreign-origin-handler-execution.md` and `20261001-error-16-host-changes-rate-limit-classification.md`. Their README indices receive only those new entries. Each record states uncommitted/unreviewed/undeployed status and the exact checks/limits; no error record claims resolution of the remaining three findings.

Existing repositories contained unrelated modified/staged/untracked files before handoff. No index, commit or push was changed. No `commits/` explanation was invented: the implementation still has no GNHF commit. No harness rule/skill promotion is warranted before independent review. Root retains final publication responsibility. Original index/checkpoint/roadmap hashes and verification results are retained in this iteration's ignored evidence.

Handoff verification removes only this hook's additions in memory and checks against the saved original hashes, preserving existing mixed newline styles. During handoff, the concurrent source-retirement owner updated its own existing learn-notes index entry from alias-publication status to verified filtered-term publication. That newer entry is retained on disk; the verification accounts for the known before/after text in memory only. `handoff-verification.json` confirms all four shared documentation files preserve their pre-existing content, including that concurrent update. Scoped whitespace checks pass. Application/test hashes remain unchanged by the handoff, so the earlier executable checks remain applicable.
