# Docker acceptance saved after the September 26 source stop

Status: **paused; final acceptance incomplete**. The coordinated source task reported the user's save-and-stop request. No further implementation, build, test or crawl followed that request. Docker services were left running. This is a working-tree checkpoint, not an application commit explanation.

## Current deployment and verified work

- Runtime: `D:/Project/py/RAG`, branch `codex/review-answer-provenance`, HEAD `641d95b67a2efdd3514399d3e7561c153bbc8f75`. Source changes remain uncommitted. Draft PR #75 was not inspected, updated or merged in this resume.
- API image: `sha256:23855c9fe28aa210e11960005719c556180334f128d6a4cb54812df50020e999`.
- Web image: `sha256:5156e1f53e6792b1f3de10da01106b885c5ba36e790c2a50cdaa48b2997cedda`.
- API health, all five reported assets and model warmup passed. All 111 checked runtime Python files matched the local source byte-for-byte. Evidence: `2026-09-26-grounded-source-verification.json`.
- Final native run: **2,662 passed**, 19 warnings, 174.90 seconds (`pytest-grounded-final-20260926.log`). The reviewed grounding change passed 112 focused tests; independent review approved it with zero findings and independently passed 53 tests.
- Corrected browser suite: **9/9 passed**, 45.2 seconds (`e2e-deployed-final-20260926.log`) against the prior reviewed evidence-retention API image `36879bbd...`. Latest changes only affect agent prompts/formatting; no browser rerun on image `23855c9f...` is claimed. The backend-error rendering case uses interception; the other eight use the local API. Frontend unit/type/lint remained the earlier passing 22-test result; no frontend change followed it.
- Live API roster coverage remains 22/22 assertions: overflow, faction/detachment disclosure, all 27 retired enhancements excluded, paid/free/unknown equipment and model tiers. Roster UI showed 230 for Dominus + Ferrumite Disintegrator, exposed an invalid model tier as incomplete and recovered after correction. Mobile 390/320 layouts had no horizontal overflow. One transient in-app-browser `Failed to fetch` recovered after an edit; its cause is unverified.

## Fixed and deployed

The agent now preserves substantive earlier evidence when a later lookup misses, including at the normal step limit. Identity-only and title-only results do not count as factual evidence. A bounded emergency answer retains actual facts with historical/current and ambiguity qualifications. This was independently reviewed, fully tested and verified through three live comparison repeats on image `36879bbd...`.

The two generation prompts now forbid absence claims based on missing fields and unsupported new variant names. The formatter rejects narrow unsupported historical-absence and dotted-name additions, retains original prose on rejection, and drops unsupported optional followups. Regressions cover negation, subject isolation and shared name prefixes. These guards are deliberately limited; they do not prove arbitrary prose is factual.

## Remaining defect: diagnosed, not implemented

Seven fresh responses from image `23855c9f...` are saved as `2026-09-26-grounded-live-*.json`, with their manual-review summary. Six passed the scoped checks; comparison 2 remained unacceptable. It retained historical Calgar 200 and official-snapshot Guilliman 355, but returned `degraded=true` and claimed `缓存中未区分安提洛库斯铠甲版本与普通版本`.

Read-only diagnosis found that the `calc_points` archive summary supplies source id 6, its name, historical 200 and a verified alias but strips the raw composition and does not expose the already-verified ordinary-card identity. The retained source record explicitly identifies Calgar plus two Victrix Honour Guard. The model inferred uncertainty from an omitted fact. This is an evidence-projection gap, not a need for new crawling.

Proposed next change: project the source-backed ordinary-card composition/variant scope into the archived points-tool summary, preserve authority warnings, add positive and negative regressions, obtain independent review, then rebuild and repeat live checks. **No code for this correction was written before the stop.** The saved response does not contain the discarded structurer draft or exception; the exact formatting-rejection reason is unknown.

## Resume order and limits

1. Read this checkpoint and `2026-09-26-final-docker-acceptance.md`; preserve all dirty source and failed/mixed artifacts. Coordinate source ownership with the existing “Connect project to GitHub” task before edits.
2. Implement/review the narrow identity projection described above; no new source fetch is necessary for this defect.
3. Run appropriate final tests, rebuild API, verify deployed hashes/health/warmup, then repeat the exact comparison in fresh sessions plus ordinary/armour/Guilliman questions. Inspect full prose and citations as well as top-level `degraded`.
4. Finish final local acceptance before application publication or merge decisions. No new full 115-question benchmark or host-restart durability test has run.

Official points remain the September 14 snapshot. No canonical database or source cache changed in this resume. The separate Black Library snapshot remains partial with 98 unresolved detail records; Fiddler was offered but not needed or used. No cloud deployment, app commit/push/merge or harness-rule promotion occurred. Credentials are not recorded in the handoff.

## Knowledge handoff

Updated project devlog checkpoint/roadmap and the existing cumulative-evidence learning decision; added one verified underlying-error record after duplicate inspection. Published devlog `73a43a2`, learn-notes `8d81a5c`, error-notes `6788180`; pushes succeeded with 0 ahead/behind verified. Unrelated staged and unstaged note changes were preserved. No unresolved-error placeholder or harness promotion was added.
