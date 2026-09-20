# Lookup completeness checkpoint

## Current September 20 local completion pass

The Docker startup/deployment gate below is cleared. Both rebuilt services are running. Final command answer passed all six effects with separate database/PDF citations; simulator and roster checks passed. Follow-on commits `b7dde5bdc`, `ea84ff1bf`, `da57a429c` and `d38a2fe7a` cover web provenance, named-table retention and manual Markdown export. See the [current roadmap](../plans/2026-09-20-local-completion.md) and [acceptance report](2026-09-20-lookup-deployment-acceptance.md) for actual verification and remaining limits. PR #74 is the release vehicle; consult its GitHub status for the merge record. Cloud is deferred by the user's explicit local-first decision. Earlier paused instructions below are historical, not an instruction to stop this resumed work.

## September 20 follow-through: optimized runtime verified

The user started Docker Desktop; the final optimized image is now deployed, healthy and warm. Question 63 returned HTTP 200 in 51.881s without degradation; the browser Titan codex rendered correctly. See [deployment acceptance](2026-09-20-lookup-deployment-acceptance.md) and [raw response](2026-09-20-lookup-optimized-http.json). Preserve the report's citation-precision limitation; functional acceptance does not certify every page citation. Current next step: latest PR checks, merge PR #74, then synchronize checkouts. The prior startup blocker below is resolved by the user's action.

## September 20 resume: draft PR ready, Docker startup blocked

[PR #74](https://github.com/sha156/wh40k-oracle/pull/74) is open as a draft and attached to the Codex task. Main has no intervening commits relative to this branch. Reviewed the source diff and hosted checks: final optimization run 35336818045 and checkpoint run 35337405606 both passed Python and frontend jobs. The latter reports 2,193 passed / 331 skipped / 10 warnings; skips concern unavailable local assets. CRLF-aware branch whitespace check passed. No new application code or tests changed on September 20.

The Docker engine is unavailable: its `dockerDesktopLinuxEngine` named pipe is absent, and no Docker processes were present on initial inspection. Automatic approval review rejected the direct hidden Desktop launch and a subsequent Docker startup-help command with only `blocked by policy`. No bypass, host configuration change or socket repair was attempted. The user has been asked to start Docker Desktop. This is not evidence of another stale-socket failure, and the September 18 statement that services were left running is historical, not current service availability.

The optimized image built on September 18 remains unverified through the deployed API. Once the engine is running, inspect the existing image, deploy it with the existing compose configuration, wait for health/warmup, then run final question 63 HTTP acceptance. Update the draft PR with that evidence and verify its current checks before marking ready and merging. Do not merge on hosted CI alone.

A bounded recheck of the [official downloads page](https://www.warhammer-community.com/en-gb/downloads/warhammer-40000/) and official Ork search results did not acquire complete rules for the two units or 28 enhancement keys. The extracted downloads page did not expose the full dynamic document list; this check does not prove no public source exists. Existing public-source limits remain unchanged.

The September 18 details below remain the implementation/test record.

Status: saved and stopped at the user's request on September 18. Implementation through `39c16a2f91807c551ad90bd457101031dd65cefc` is pushed on `codex/benchmark-lookup-completeness` in `D:/Project/py/RAG`. No PR or merge was performed for this branch. The app checkout at `C:/Users/Administrator/Documents/ChatGPT/RAG` remains on main `74544de81`.

## Changes and purpose

- `8c172ea22`: preserve canonical identity between the resolver and indexed wiki pages, refuse duplicate IDs, and retain a bounded compatibility path for older slug pages. Add read-only paginated faction inventory with separate database and official price-row counts. Expose the official shared Chaos Titan datasheet rule from Faction Pack Adeptus Titanicus page 2.
- `ff6bc6f6d`: retrieve referenced army rules when a datasheet supplies only the ability name/count/range. Identify merged structured cards explicitly: a patch in page frontmatter does not prove every field came from that patch. Preserve this source-scope disclosure after tool-output truncation.
- `60fdee85b`: resolve identity before numeric lookup when a question asks what a unit is or which faction it belongs to. Keep fuzzy suggestions provisional and the requested answer focused. Numeric-only questions retain their established datasheet path.
- `39c16a2f9`: reduce repeated filesystem metadata calls during canonical lookup on Docker's Windows bind mount. Reuse directory metadata only within one call, retain duplicate-ID refusal and symlink boundary checks, and observe regenerated pages on subsequent calls.
- No database, official price cache, generated wiki or gold-answer edits were made in this continuation. Existing fallback safeguards for questions 4 and 62 remain in place.

## Verified acceptance and limits

| Check | Actual result |
| --- | --- |
| Full native pytest before the final three added tests | 2,527 passed, 19 warnings, 184.44 seconds. |
| Final focused lookup/tool/client/loop tests | 124 passed, 8 warnings, 3.64 seconds, including regeneration and symlink checks. Counts overlap with the full suite; do not add them. |
| First full benchmark | 113 correct / 1 partial / 1 wrong. Retained in `benchmarks/v3_edition11/qa_agent_results_20260918_lookup.json`. |
| Final full benchmark | 115 correct / 0 partial / 0 wrong, unchanged gold, in `benchmarks/v3_edition11/qa_agent_results_20260918_lookup_r2.json`. Compared with September 16, only questions 63 and 116 changed verdict, both partial to correct. |
| Controls | Questions 63, 109, 118 and 119 passed, as did fallback-sensitive questions 4 and 62. This is one passing stochastic full run, not a guarantee for every future response. |
| Real base comparison for question 118 | Base `74544de81` and candidate tools returned identical dictionaries for the three tested Helbrute names. Both saved faction-disclosing answers passed the existing rubric. The suspected lookup regression was not reproduced. |
| Hosted CI | Python and frontend passed for `ff6bc6f6d` (run 35335823498) and `60fdee85b` (run 35336236595). CI for final I/O commit `39c16a2f9` has not been reviewed. |
| Container API before final I/O change | Healthy and warmup complete; questions 63, 116 and 118 returned HTTP 200 with inspected answers. Evidence: `2026-09-18-lookup-http-acceptance.json`. |
| Browser before final I/O change | Rendered four shared Titan datasheets; follow-up confirmed both Warlord prices at 3,500. Browser text/interaction inspected; no screenshot-based visual QA in this continuation. |
| Direct canonical lookup timing | Old Docker 105.022 seconds; candidate Docker 19.646; native candidate 0.952. Same canonical ID `000000680`. Single isolated-process observations, not a latency distribution or final API latency result. |
| Final API image | Build completed successfully, config `33f9faa4ccf5fec1de005a26823e20305dcc6c371c39e62ed85817ef4b00ff39`; it has not been deployed or tested through the API. |

The full benchmark preceded the final filesystem optimization; prompts and routing did not change afterward. The final focused tests and isolated Docker timing cover that optimization, but final deployed API acceptance remains open. The running API still has the earlier checked `60fdee85b` code; the web container is unchanged. Both services remain running. No build worker remains active.

Initial overlapping model/test processes exhausted Windows resources (`std::bad_alloc` and WinError 1450). Temporarily stopping this project's API model process and serializing heavy checks allowed the full suite and both full benchmarks to finish. The API was then restarted and verified. Interrupted logs are not counted as completed checks.

## Saved evidence

All paths below are relative to `docs/superpowers/reports/` unless otherwise stated.

- `2026-09-18-lookup-base-comparison.json`: actual base/candidate tool outputs.
- `2026-09-18-lookup-probe-judgments.json`, `2026-09-18-lookup-completion-probe.json` and `2026-09-18-lookup-completion-judgments.json`: intermediate failures retained rather than overwritten.
- Earlier baseline, initial-candidate and final-probe JSON files remain as historical observations; their former label "final" does not make every answer a judged pass.
- `2026-09-18-lookup-http-acceptance.json`: checked live API responses before the I/O change.
- `2026-09-18-canonical-lookup-timing.json`: method and single-call timings.
- Both complete benchmark files are under `benchmarks/v3_edition11/` as listed above. Gold was unchanged.
- Ignored local logs include `pytest-lookup-serial.log`, `benchmark-lookup-serial.log`, `benchmark-lookup-r2.log` and `docker-lookup-final-build.log`.

## Remaining source and host work

Use **public official sources only for now**, as the user requested. No additional complete authoritative rules were acquired for Gunwagon, Runtherd or the 28 remaining Ork enhancement keys. This is an acquisition limit, not proof that no public source exists. Labeled previews remain previews. No new September 18 points synchronization is claimed. Docker's recurring stale host sockets still have only a recovery workaround; startup durability is unverified.

## Resume order

1. Deploy the already-built API image from `D:/Project/py/RAG` using the existing compose configuration; wait for health and model warmup. Run final question 63 HTTP acceptance and inspect both the answer and latency. The prepared temporary script is `%TEMP%/wh40k-lookup-optimized-http.py`; it has not run and is not a durable repository dependency.
2. Review final-commit CI and the branch diff, then create a PR. Require final container acceptance and green checks before merge.
3. Synchronize the two checkouts after merge. Preserve local runtime/data assets.
4. Continue remaining Ork rules only with suitable public official evidence; keep Docker host durability separate.

No further implementation, model calls, deployment or merge should run until the user resumes. Existing application services are left running.
