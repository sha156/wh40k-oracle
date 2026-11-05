# Paused evidence-preservation fix — 2026-09-26

The coordinated Docker task received an explicit **save and stop** request. This source task stopped immediately. No build, deployment, crawl, commit, push or merge was performed here. Existing Docker services remain owned by the Docker task.

## Reproduced regression

The final-image comparison asked for ordinary Calgar versus Guilliman. `calc_points` successfully returned historical Calgar 200 and current official-snapshot Guilliman 355, and `get_datasheet('卡尔加')` returned the scoped historical record. A later `entity_resolver('卡尔加 维克特里克斯卫队')` miss triggered the loop's automatic `rag_search` fallback. That fallback discarded prior successful evidence, and the final answer falsely said Guilliman's current points were unavailable. Evidence: `docs/superpowers/reports/2026-09-26-live-comparison.json`.

## Saved source changes

- `agent/loop.py`: adds a narrow usable-evidence predicate. Verified current/historical points, datasheets, entity pages, wiki results and found keyword definitions survive a later empty tool response. The empty response and a scope-preservation instruction are returned to the model so it answers supported parts and marks only the unresolved name. A name-to-ID mapping alone is intentionally not usable rules/points evidence, so an evidence-free path still performs the existing honest retrieval fallback.
- `tests/test_agent_loop.py`: adds a Calgar/Guilliman-shaped regression and a negative paired case proving that a successful ID mapping alone does not suppress fallback. The positive test failed before the source fix and passed after it.
- `web/e2e/simulator-errors.spec.ts`: updates the stale H2 browser expectation to the current reviewed UI contract. Models=200 is rejected with `aria-invalid`, the stale damage result disappears, and correcting to 10 permits a fresh report. H3 backend `errors` rendering remains separately covered through an intercepted response.

## Completed checks before stop

- New paired loop tests before implementation: **1 failed / 1 passed**, reproducing the evidence-loss fallback.
- New paired loop tests after implementation: **2 passed**.
- Focused agent loop/archive/lookup suite: **56 passed**, 5 existing warnings, 3.79 seconds.
- Frontend TypeScript: `npx tsc --noEmit` passed.
- Frontend ESLint: `npm run lint` passed.
- `git diff --check` for the three changed files passed.

An independent review had been dispatched but was interrupted on the stop instruction before a verdict. No Playwright E2E was run here; the Docker task explicitly owns that rerun and asked this task not to run it concurrently. An initial combined command was issued from `web/` with incorrect Python path and a nonexistent `npm run typecheck` script; those two command invocations failed without changing files. The correct Python command, `npx tsc --noEmit`, lint and whitespace checks then passed as listed above.

## Remaining work

1. Independently review the saved `agent/loop.py`, `tests/test_agent_loop.py` and `web/e2e/simulator-errors.spec.ts` diffs.
2. Rerun the updated simulator error E2E through the deployment task.
3. Rebuild/deploy the API, then repeat the live Calgar/Guilliman comparison. Acceptance requires retaining historical Calgar 200 and current Guilliman 355 while marking only the unresolved composite alias; the trace must not show automatic `rag_search` caused by that later miss.
4. Reconcile the final full suite and deployment report before release. Do not infer completion, commit or PR readiness from this paused checkpoint.
