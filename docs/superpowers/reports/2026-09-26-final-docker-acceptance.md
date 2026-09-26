# Final Docker acceptance after evidence-preservation review

This historical report is superseded by [the current local cleanup acceptance](2026-09-26-local-cleanup-acceptance.md). Its paused and unimplemented statements describe earlier checkpoints.

Date: 2026-09-26. Status: **paused; final acceptance incomplete**. This report continues the saved September 26 Docker and source checkpoints. Preserve the earlier failed comparison and 7/8 browser result as before-fix evidence.

The user resumed the coordinated project test/fix task. Source fixes and independent review remain owned by the existing “Connect project to GitHub” task; this task owns Docker deployment, final native/HTTP/browser verification and this report. The user also made Black Library/Fiddler available for a crawl if needed. No new crawl is needed for the reproduced bug because the required values already exist in the runtime database.

## Reproduced defect and repair boundary

The failed combined Calgar/Guilliman answer first retrieved usable points, then lost them when an extra alias lookup missed and triggered automatic RAG fallback. The failed response is retained in `2026-09-26-live-comparison.json`.

The source review covers preserving substantive evidence after a later miss, keeping identity-only/empty search results distinct from facts, retaining evidence when the normal tool-step budget ends, and avoiding loss of historical/current scope in an emergency answer. The corrected simulator E2E test targets `/simulate` and tests the current client-side invalid-model rejection behavior. Final source review and deployment results will be recorded below only after completion.

## Verification completed in this resume

- Existing deployed API was healthy, with all five reported assets available and model warmup complete.
- Corrected browser suite: **9 passed**, 33.0 seconds (`e2e-evidence-fix-20260926.log`). It covers bilingual codex cards, roster points/loadout/critique, points badges, invalid model-count rejection and recovery, explicit backend-error rendering, phase-specific weapons and clearing obsolete loadouts. The backend-error rendering test uses a deliberately intercepted response; the other eight use the local API. This run preceded deployment of the final agent-loop fix.
- The real roster UI imported Tech-priest Dominus plus Skorpius Disintegrator with one Ferrumite cannon, producing **230 points** and a valid result (60 + 170). A two-model Dominus was explicitly unpriced and marked incomplete; restoring one model recovered the correct total.
- A transient in-app-browser validation request displayed `Failed to fetch`. The direct API remained healthy and returned HTTP 200 with the expected CORS origin, and editing the roster recovered validation. No source fix or underlying-cause claim is made for this transient event. The native Chrome E2E suite passed.
- Responsive roster screenshots at 390x844 and 320x740 showed no horizontal overflow. Document widths were 375 and 305 respectively, within viewport widths of 390 and 320 (vertical scrollbar present). Temporary viewport overrides were reset.
- The earlier full native run passed **2,646**, and the earlier live API artifact contains **22/22 passing assertions** for overflow, faction/detachment disclosure, all 27 removed enhancements and paid/free/unknown weapon charges. These remain pre-final-loop-fix evidence; the final native run is pending.

## Pending final gate

The first reviewed evidence-preservation candidate was deployed as API image `sha256:36879bbdd31a51735878f29916f435eab54584d55323cc38b59dba0c85b74ee7`. All 111 checked runtime Python files matched the local source exactly (`2026-09-26-deployed-source-verification.json`). Assets and warmup passed. Full native suite: **2,654 passed**, 19 warnings, 193.19 seconds (`pytest-evidence-fix-20260926.log`). Final deployed browser suite: **9/9**, 45.2 seconds (`e2e-deployed-final-20260926.log`). Independent backend review approved the source with zero remaining findings in its reviewed scope; focused suite passed 74.

Three exact live comparisons now retained historical Calgar 200 and official-snapshot Guilliman 355 with top-level `degraded=false`, in 35.248 / 6.238 / 7.585 seconds. The first used model-requested `rag_search` after later misses and still retained earlier facts; the presence of `rag_search` alone is therefore not an automatic-fallback failure. Individual ordinary/armour/Guilliman calls returned HTTP 200, `degraded=false`, in 5.721 / 3.927 / 3.559 seconds with the expected 200 historical / 155 / 355 values. Outputs use the separate `2026-09-26-fixed-live-*.json` names.

**Manual prose review prevented premature acceptance:** although scalar assertions passed, the ordinary-Calgar response invented the unasked comparator `卡尔加·无畏机甲`, and comparison 3 asserted Guilliman had no historical cached points without establishing that absence. These are not accepted as grounded facts. The source task is investigating a narrow generation/formatting correction; no new source crawl is required by these failures. Preserve these responses as mixed results rather than calling all six answers fully accepted.

1. Obtain the reviewed source freeze and final focused-test results.
2. Run the full native suite on that fixed tree, build/deploy API, verify image identity and health/warmup.
3. Repeat the exact failed comparison in fresh sessions, requiring top-level `degraded=false`, historical Calgar 200 separated from official-snapshot Guilliman 355, and corresponding citations. Recheck ordinary Calgar, armour Calgar and Guilliman individually.
4. Verify the deployed source matches the checked files, finish the acceptance summary and update project/knowledge records without including unrelated staged changes.

## Scope limits

The official point snapshot remains September 14; no current-date source refresh is claimed. No canonical data, source caches, database projections or model assets were changed in this resume. The separate Black Library snapshot remains partial. No new full 115-question model benchmark, host reboot/durability test, cloud deployment, application commit, push or merge has occurred. Markdown preview content was verified earlier; clipboard and file-download delivery are not established by the current checks.

## Second reviewed deployment: a remaining identity claim

The grounding candidate passed 112 focused tests and independent review with zero findings (reviewer independently passed 53 focused tests). It was deployed as API `sha256:23855c9fe28aa210e11960005719c556180334f128d6a4cb54812df50020e999`; all 111 checked runtime Python files matched source. All assets and completed warmup passed (`2026-09-26-grounded-source-verification.json`). The web image was unchanged.

Seven fresh chat responses are retained as `2026-09-26-grounded-live-*.json`, with a separate summary. Six passed scalar and scoped prose checks. The previous invented variant and unsupported Guilliman-history absence did not recur. Comparison 2, however, returned `degraded=true` and included the upstream claim `缓存中未区分安提洛库斯铠甲版本与普通版本`. This conflicts with the separate ordinary-Calgar historical archive identity. It still retained historical 200 and official-snapshot 355 with citations; neither the correct numbers nor the formatter fallback makes that identity claim acceptable. The response is retained for read-only diagnosis before further changes. This batch is **not full final acceptance**.

The full native suite on this exact grounding candidate passed **2,662 tests**, 19 warnings, 174.90 seconds (`pytest-grounded-final-20260926.log`). Read-only diagnosis then established a source projection gap: `calc_points` retained the archived source id/name/value but removed raw composition and did not expose the ordinary-card identity that was already verified in the archive. The retained raw cache identifies Calgar with two Victrix Honour Guard. A narrow projection correction is being reviewed; no crawl is required. The saved answer lacks the discarded structured draft and validator exception, so the precise formatting-rejection reason is not established and must not be invented.

## Saved stop state

The coordinated source task received the user's save-and-stop request before implementing the archive identity projection. Testing and implementation are stopped. Docker remains on `23855c9f...` API and `5156e1f5...` web. The proposed projection is **not implemented**. Latest native suite is 2,662 passed; latest live batch is explicitly mixed 6/7, not accepted as a complete release. Resume from [the final paused Docker checkpoint](2026-09-26-paused-final-docker-checkpoint.md). Earlier pending lists and deployments in this report are historical steps, superseded by that checkpoint.
