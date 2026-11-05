# Docker acceptance and runtime fixes — 2026-09-22

Status: PAUSED at the user's request on September 22. Final API build was interrupted; final deployment acceptance remains pending.

The user requested project tests and fixes with Docker already running. Source work was coordinated with the existing “Connect project to GitHub” task, with explicit user approval. This task owns Docker, runtime projection and deployed acceptance; the companion task owns source fixes/reviews and the project/knowledge handoff.

## Reproduced runtime fault and fix

The initial dependency build failed with `SSLCertVerificationError: unable to get local issuer certificate`. Setting the configured build proxy to `http://host.docker.internal:7897` restored the build without disabling TLS verification.

After deploying the rebuilt image, real chat returned HTTP 200 but `degraded=true`, a `Connection error.` from the LLM client and a formatting failure. Unauthenticated container HTTPS probes reproduced certificate failure on the direct route; the same DeepSeek request through the existing Clash proxy returned HTTP 401, establishing successful TLS transport without exposing a credential.

`docker-compose.yml` now accepts optional `DOCKER_RUNTIME_PROXY`, passed only to the API through `HTTP_PROXY` and `HTTPS_PROXY`, with local/service addresses in `NO_PROXY`. `.env.example` documents the setting. The ignored local `.env` configures both build and runtime proxy addresses. TLS checks remain enabled. Chat recovered after API recreation.

## Historical archive projection

A copied-database trial projected 2 explicitly deleted records from the existing 1,072-entry Black Library details cache. All 17 preexisting tables were compared by complete sorted row hashes and remained unchanged, including 1,721 canonical units.

A SQLite backup was saved at `D:/Project/py/RAG/archive/runtime-backups/wh40k-before-source-archive-20260922-182506.sqlite`, then the projection was applied to the runtime database. The same full-table comparisons passed, and `PRAGMA integrity_check` returned `ok`.

Evidence: [archive projection](2026-09-22-archive-projection.json). The cache timestamp is filesystem modification time, not a rules publication or verification date. No current points were changed.

Direct tools distinguish ordinary Calgar (third-party deleted historical record, 200 points, no canonical ID/current points) from Armour of Antilochus (canonical ID 000004183, 155 points) and Guilliman (000000138, 355 points). The current official points snapshot is dated September 14; this pass does not refresh official sources.

## Checks completed before final source freeze

- Initial native suite: 2,599 passed / 2 failed. Both failures concerned archive preservation/validation during database rebuild and were fixed by the companion task; subsequent focused archive suite passed.
- Initial frontend: 18 unit tests, TypeScript and lint passed. The companion task is validating subsequent additions.
- Existing deployed browser suite: 8/8 passed (codex, roster calculation/loadout/critique, simulator input errors and phase/loadout transitions).
- Four post-proxy fresh HTTP chats: comparison 9.875s, ordinary Calgar 6.250s, armour Calgar 3.625s, Guilliman 4.906s. All returned HTTP 200, `degraded=false`, with no retrieval fallback. Historical 200 and cached official 155/355 remained distinct, with separate provenance.
- Chat UI streamed and rendered the historical answer without a fabricated current datasheet. Markdown panel displayed the full answer, citations and JSON archive snapshot.
- Dark mobile layout inspected at 390x844 and 320x740. Document widths matched viewport widths exactly; no horizontal overflow. Header controls and composer remained usable.

Failed HTTP outputs are retained in `2026-09-22-live-comparison.json` and `2026-09-22-live-ordinary-calgar.json`. Recovered outputs use the distinct `-proxy.json` suffix; they do not overwrite the failed evidence.

## Explicit limits

The in-app browser reported “copied”, but its clipboard API returned empty text; a Markdown download event was not observed within ten seconds. The Markdown panel content is verified; clipboard/file delivery is not claimed. Chrome was unavailable through the computer-use connector. The existing native Chrome E2E suite ran successfully separately.

No new full 115-question AI benchmark, external official-source refresh, host/Docker Desktop restart durability test, cloud deployment or PR merge is claimed.

## Paused checkpoint — save and stop

The user requested “save and stop do it later” during the final API build. The build command was interrupted; the existing API was not replaced. Docker services are left running.

Verified running image IDs at stop:
- API: `sha256:344f58db1bedb3ef0f4a50073a8ec962e828b380564572758e75c7a7a4c136ba` (healthy; earlier September 22 source snapshot with historical lookup and runtime proxy).
- Web: `sha256:5156e1f53e6792b1f3de10da01106b885c5ba36e790c2a50cdaa48b2997cedda` (final reviewed frontend deployed).

Additional completed checks:
- Final web production build, 22 frontend unit tests, TypeScript and lint passed.
- Rapid unit/language changes ended on English Guilliman at 355; rapidly replacing Calgar with Guilliman in official-point search ended on exactly one Guilliman row at 355.
- Editing roster import text while an old preview was in flight cancelled that preview; a fresh preview recognized only the latest one-unit input.
- Browser follow-up correctly recalled ordinary Calgar, with earlier answer retained. Mobile conversation at 390 pixels remained free of horizontal overflow.
- Companion source task reported full native 2,628 passed before its final pricing regressions. It subsequently reported source freeze and independently reviewed fixes for official-ledger precedence over archives (133 focused passed) and unknown/paid/free loadout surcharge handling (69 focused passed). These latest API changes are NOT deployed or HTTP-accepted here. Do not call the final tree fully tested from the earlier full-suite count.

Resume order:
1. Read this checkpoint and the companion task's latest source checkpoint; inspect current Git/source state because both tasks shared the checkout. Preserve all saved files.
2. Rebuild/deploy API with `docker compose build api` then `docker compose up -d --no-deps api`. Local ignored `.env` already configures build/runtime proxy. Verify running image, assets and model warmup.
3. Repeat final Calgar/Guilliman comparison and separate identity HTTP checks, requiring no fallback and historical/current source separation.
4. Test roster overflow (`1e999`) on validate/critique without HTTP 500, all 27 retired enhancements excluded, incomplete faction validation badge, and unknown/paid equipment price handling. Rerun the eight browser E2E tests against the final deployment; validate simulator model tiers and latest mobile layout.
5. Reconcile final native suite/source reviews with the companion task, finalize this report and project/knowledge handoff. Commit/push decisions remain with the source task. This task made no commit, push or merge.

Source/config changes, report and JSON evidence are saved locally. No ongoing test/build is intentionally left running by this task. No resume automation was created.

## Documentation-only stop-hook handoff

Duplicate searches checked the existing devlog, learn-notes and error-notes before writing. No existing Docker runtime-proxy record was found. The existing common/20260916-error-35-sqlite-context-manager-file-lock.md already documents the temporary SQLite cleanup error; no duplicate error was created.

The following complete local documents were successfully written before the companion task notified this task of its earlier automatic-approval rejection for external handoff publication:

- D:/Project/devlog/wh40k-oracle/CHECKPOINT.md
- C:/Users/Administrator/learn-notes/wins/20260922-test-container-egress-beyond-healthchecks.md
- C:/Users/Administrator/error-notes/rag/20260922-error-01-docker-llm-runtime-proxy.md

No note commit/push or index update was performed. Existing unrelated README/worktree edits were preserved. The reported rejection reason was only `blocked by policy`; this task did not retry the rejected publication through another route. Project-local source checkpoint/roadmap were updated by the companion task at docs/superpowers/reports/2026-09-22-paused-review-crawl-checkpoint.md and docs/superpowers/plans/2026-09-20-local-completion.md.

Pending documentation steps, for a later authorized handoff:
- Prepend the devlog ROADMAP with completed runtime-proxy recovery, backed-up archive projection, final web checks, and pending final API deployment/acceptance. Link CHECKPOINT.md; do not invent an application commit or create a commits/ explanation without a real commit.
- Add the two new note links to their README indexes, preserving unrelated edits and staging only the intended hunks.
- Optionally append the verified September 22 recurrence to the existing SQLite close note: TemporaryDirectory cleanup failed with WinError 32 after plain SQLite context-manager use; rerunning the copied-DB trial with contextlib.closing succeeded and preserved all 17 tables.
- Review/stage/publish only these intended note changes when the external publication block is resolved. No harness promotion is warranted because existing global guidance already covers proxy diagnosis before changing certificates or credentials.

Application work, builds and tests remained stopped throughout this documentation-only handoff.
