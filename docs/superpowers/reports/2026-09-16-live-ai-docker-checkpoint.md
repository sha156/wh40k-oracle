# Tasks 3–4 acceptance checkpoint — September 16

Stopped at the user's explicit request to save and stop. Work branch: `codex/live-ai-docker-acceptance`, based on main `57b73d5da` (README artwork PR #72 merged). Canonical runtime workspace: `D:/Project/py/RAG`.

## Completed evidence

- Docker Desktop startup repaired. Preserved the inaccessible inference and Secrets Engine socket directories, backed up settings, and disabled `EnableDockerAI`. Engine 29.0.1 now responds. Desktop executable version: 4.53.0.211793. No volumes, images or WSL distributions were reset. The exact error and repair are saved in error-notes commit `4acb195`.
- Both images built using `DOCKER_BUILD_PROXY=http://host.docker.internal:7897` and `docker compose --progress plain build`. An initial registry EOF cleared on a subsequent pull/build; no certificate or credential changes were made.
- `docker compose up -d --no-build` started API and web. API became healthy; `/healthz` reported ready, all five assets present, and warmup done with no error. Bind mounts for opt, vector store, database and wiki were all read-only; API runs as appuser. Published ports bind to 127.0.0.1 only.
- Container `pip check`: no broken requirements. Container pytest: **85 passed** across qa_bench, sessions, web roster and simulation tests. Native qa_bench/session tests: **53 passed**. This was targeted acceptance, not a new full-suite run.
- Real HTTP checks: frontend `/` and all eight API paths in the JSON evidence returned 200. Warlord Titan datasheet, keywords, core rules, changelog, simulation (expected damage 3.098), roster validation (legal, 150 points), and critique (four assessed target profiles) worked.
- DeepSeek balance availability and a real chat completion succeeded. Credentials and account balance are excluded from these artifacts. Requested model alias was deepseek-chat; the direct smoke response reported deepseek-flash.
- Full native agent benchmark: **113 correct / 2 partial / 0 wrong**, 115 questions, 98.3%, 193.3 seconds, 33 classic fallbacks. Partial #63: tank-command answer clarification; partial #116: refused to assert the exact Titan datasheet total despite listing four. Preserve these as findings, not passes.
- Gold v3.6 changes only #117 and metadata: FRAME now exists in Warlord Titan's structured keyword list. Its official PDF/page/hash evidence is in the question note. v3.5 is preserved unchanged. A read-only comparison of 113 numeric model fields found zero differences; that comparison is consistency evidence, not an independent new source audit.

## Live conversation recall failed — next action

`2026-09-16-live-session-acceptance.json` contains the exact synthetic requests and responses:

1. Session A remembered Tau Empire and nickname Copper Lantern 742: non-degraded acknowledgment.
2. Same session asked to recall them: **failed**, degraded into rag_search and said no history was available.
3. Separate session B correctly had no record of them: non-degraded, no cross-session disclosure.

Session history is passed by `web_api/main.py::_run_answer` to `AgentLoop.run`, and `agent/loop.py::_run_tool_loop` includes the bounded history in model messages. The likely failure is the zero-tool verification gate/classifier routing a conversation-only recall question into source retrieval; fallback does not preserve conversation context. This is a diagnosis to confirm, not a verified underlying fix. Existing fake tests classify recall as idle chat and therefore do not cover the observed live route. **No production code fix was made before stopping.**

Resume by reproducing the recall classification/tool path, add a regression that reproduces the observed gate, preserve fresh verification for current rules/points, and rerun same-session recall plus isolation and a current-data query. Do not claim task 3 complete until recall passes. Do not weaken fact verification globally to make memory pass.

## Artifacts and operating state

- `benchmarks/v3_edition11/qa_agent_results_20260916.json`: complete live benchmark.
- `benchmarks/v3_edition11/qa_gold_v3.5.json`: original expectations.
- `docs/superpowers/reports/2026-09-16-docker-api-acceptance.json`: actual HTTP requests/results.
- `docs/superpowers/reports/2026-09-16-live-session-acceptance.json`: failed recall and isolation evidence.
- Ignored local logs: `docker-acceptance-build.log`, `live-benchmark.log`.
- Socket backups: `%LOCALAPPDATA%/Docker/run.stale-20260916-150039`, `run.stale-20260916-150405`, and `%LOCALAPPDATA%/docker-secrets-engine.stale-20260916-150405`. Settings backup has suffix `.before-socket-repair-20260916-150405`. Preserve them.
- Docker MCP CLI lists Playwright enabled. Its tools were not exposed in this running Codex tool inventory; Docker CLI was used successfully.
- Stop the two project containers at handoff; keep images and mounts. Resume with `docker compose up -d --no-build` in the canonical workspace. Docker Desktop itself can remain running. Reboot persistence and browser visual acceptance of the container build remain untested.

## Remaining scope

Task 4 build/start and API acceptance passed; task 3 benchmark completed but live recall remains open. Existing source-only Ork records and partial benchmark answers remain disclosed. No merge is claimed for this checkpoint.
