# Docker acceptance paused after live regression discovery

Date: 2026-09-26. The user requested **save and stop**. Implementation, builds and tests are stopped; the coordinated source task has been instructed to stop and preserve its edits. Docker services remain running.

Runtime: `D:/Project/py/RAG`. Branch: `codex/review-answer-provenance`. Existing HEAD: `641d95b67a2efdd3514399d3e7561c153bbc8f75`. All saved source/configuration changes remain uncommitted. This task did not commit, push, merge or resume the separate Black Library crawl.

## Deployment completed before stopping

Docker Desktop was open but its Linux engine was initially unavailable. `docker desktop start` reported it already running; a subsequent `docker info` succeeded. No socket-directory workaround, host restart or certificate change was performed.

The September 22 source snapshot was rebuilt and deployed successfully with the existing saved build/runtime proxy configuration. The API health endpoint returned `ready=true`, all five reported assets available, and warmup `done=true`, `error=null` before live chat checks.

Running image IDs verified at stop:

- API: `sha256:c8841e4eaa8c376c8e6cd502b5738707a7aa4cdc802b756f9c975b45f55d6201`.
- Web: `sha256:5156e1f53e6792b1f3de10da01106b885c5ba36e790c2a50cdaa48b2997cedda`.

The later September 26 agent-loop draft is **not** in this API image. Models, canonical database, official prices and source caches were not modified during this resume.

## Completed checks

- Full native suite: **2,646 passed**, 19 warnings, 184.44 seconds. Log: `pytest-final-20260926.log`. This run preceded the newly discovered regression and its draft fixes; it is not final-tree acceptance of those edits.
- Frontend: **22 unit tests**, TypeScript and ESLint passed. Production web source was not changed in this resume; the deployed image is the previously verified final September 22 build.
- API build succeeded; dependency layers were reused. Log: `docker-build-api-20260926.log`.
- Live roster baseline: legal, 150 points. Both positive and negative overflowing equipment counts (`1e999`, `-1e999`) returned HTTP 200 on validation and critique. Critique correctly disclosed discarded equipment instead of claiming no equipment had been supplied.
- Unknown factions and known wrong-faction detachments were rejected. Unknown detachment and cross-faction compatibility remained explicitly unverified.
- All **27** removed enhancements were absent from all **11** affected detachment endpoint responses.
- Real Skorpius Disintegrator pricing: Ferrumite cannon 170, Belleros energy cannon 160; misspelled equipment stayed unpriced with a surfaced warning. The deliberately minimal one-unit price probes also had the expected missing-warlord error; they were not legal-roster claims.
- Simulator responses exposed Gretchin tiers 10/20, Crusader Squad 10/20 and Wolf Guard Terminators 5/10, each with `loadout_required` rather than a fabricated damage report.
- Evidence for these requests: [API acceptance JSON](2026-09-26-api-acceptance.json).
- Browser roster import recognized Tech-priest Dominus plus Skorpius Disintegrator. With the tank's paid equipment unresolved, the actual UI showed **未完全校验**, 60 known points, and a warning that the tank was not included in the total. The import text was then changed to include `Ferrumite cannon:1`; that new preview was not applied or accepted before the stop request.

## Live chat results and discovered failure

All requests used fresh session IDs. Point values below are from the existing September 14 official snapshot or explicitly historical third-party cache, not a September 26 source refresh.

| Request | HTTP | Seconds | Result |
| --- | --- | --- | --- |
| Ordinary Calgar | 200 | 7.967 | `degraded=false`; historical deleted record at 200, no claim of current official price |
| Armour of Antilochus Calgar | 200 | 3.581 | `degraded=false`; official-snapshot 155 |
| Guilliman | 200 | 3.254 | `degraded=false`; official-snapshot 355 |
| Ordinary Calgar versus Guilliman | 200 | 44.151 | **Failed semantic acceptance**, `degraded=true`; falsely said Guilliman's current points were unavailable |

Raw outputs are saved separately as `2026-09-26-live-{ordinary-calgar,armour-calgar,guilliman,comparison}.json`. The failed comparison is retained and must not be overwritten by a passing rerun.

The failed trace called `calc_points` successfully, then found Calgar's historical datasheet. A subsequent `entity_resolver('卡尔加 维克特里克斯卫队')` miss triggered automatic `rag_search` fallback, discarding earlier useful numeric evidence. The final reply retained historical 200 but incorrectly reported Guilliman's official points unavailable.

The ad-hoc request runner initially inspected a nonexistent `meta.degraded` field. Manual inspection caught this: this API exposes **top-level `degraded`**, rich prose under `verdict.lede` / `calc`, and citations under `cites`. Resume assertions must require those real fields and inspect source/number separation; HTTP 200 is insufficient.

The explicitly authorized companion task, **Connect project to GitHub** (`01a080d3-afc3-77c1-92a9-e854ee8e1c3a`), owns a narrow fix. Saved edits observed at stop are in `agent/loop.py` and `tests/test_agent_loop.py`: retain already usable evidence after a later missing result, while allowing an identity-only lookup to fall back honestly. Its [source checkpoint](2026-09-26-paused-evidence-preservation-fix.md) confirms the positive regression failed before the fix; paired tests then passed 2/2 and the focused loop/archive/lookup suite passed 56. TypeScript, lint and scoped whitespace checks passed. Independent review was interrupted before a verdict. No agents remain doing source work. Review, final-tree full tests and deployed acceptance remain pending.

## Browser suite and pending test update

The existing eight-test E2E suite ran against the deployed Docker services: **7 passed / 1 failed**, 41.8 seconds. Log: `e2e-final-20260926.log`; detailed failure files are under `web/test-results/` until the next run replaces them.

The failed assertion in `web/e2e/simulator-errors.spec.ts` expected a damage report after entering 200 models. The reviewed frontend now intentionally rejects values outside 1–100 and removes the stale report. The failure is an obsolete expectation, not evidence that invalid input was accepted. The companion has saved a draft test update covering rejection, disappearance of the old report, correction/recovery and a separate backend-errors rendering case. That edited suite has **not** been accepted here. One concrete review item remains: its H3 draft intercepts `**/simulate/combat`, while the actual client posts to `/simulate`. Correct/review that fixture on resume before claiming backend-error UI coverage. No test/source correction was made after the stop request.

Mouse actions in the in-app browser did not activate the import disclosure; keyboard Enter did. No app JavaScript console errors were observed. The earlier September 22 responsive inspection remains historical; no fresh mobile-layout acceptance was completed today.

## Resume order

1. Inspect current Git state and the companion task's final stop report. Preserve every unrelated/source edit. Source task owns application fixes; Docker task owns deployment and this acceptance evidence.
2. Complete focused regression tests and independent review for preserving useful evidence after a later lookup miss. Keep no-evidence fallback and historical/current authority boundaries intact. Finish/review the simulator E2E update.
3. Rebuild and deploy the API only after source is stable; verify actual image, readiness and warmup. Current running image still contains the comparison failure path.
4. Rerun the exact failed comparison with fresh sessions; require top-level `degraded=false`, historical Calgar 200 separated from official-snapshot Guilliman 355, and correct citations. Recheck individual identities. Retain failed and fixed evidence separately.
5. Run the updated browser suite and appropriate final native tests after the source change. Repeat relevant API checks if affected; do not reinterpret the earlier 2,646 pass count as coverage of the later draft.
6. Update the final acceptance report, project checkpoint/roadmap and prepared knowledge handoff. Source/PR publication remains a separate pending step; PR #75 was not inspected or changed in this resume.

## Knowledge handoff and limits

Existing project, learning and error notes were checked for duplication. The runtime-proxy finding already has local September 22 records; no duplicate was added. The newly discovered evidence-loss defect is not yet recorded as resolved. Its reproduction and attempted fix are retained above for a later verified error record. No new cross-project rule is justified before resolution is confirmed.

The earlier external-handoff rejection is historical. During the subsequent explicit documentation-only stop hook, duplicate checks found that the coordinated task had already published its source checkpoint and raw learning decision. The Docker task supplemented the same devlog and existing runtime-proxy notes, preserved unrelated staged edits, and successfully published only its intended documentation: devlog `6a708f9`, learn-notes `0e135f3`, error-notes `dc6a0a6`. The new evidence-loss defect remains unresolved pending review/live acceptance; no resolved-error placeholder or harness promotion was created. Application work stayed stopped.

Unchanged limits: no new full 115-question model benchmark, official-source refresh, database rebuild, host-restart durability test, cloud deployment, full Black Library capture or PR merge. Clipboard/download delivery remains unconfirmed. The separate partial Black Library snapshot remains as saved September 22.
