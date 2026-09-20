# Optimized lookup deployment acceptance — September 20

## Final local application pass

The user explicitly prioritized the local Docker app over cloud deployment. The [current roadmap audit](../plans/2026-09-20-local-completion.md) separates completed implementation from public-source and host limits. Earlier observations below are retained as before-fix evidence.

Changes: `b7dde5bdc` adds merged-card citations, keeps source-scope disclosure in the formatting digest, fixes the stale roster critique description and introduces Markdown export. `ea84ff1bf` adds a guard against losing named Markdown table rows and clarifies that rule effects belong in the answer body even without a calculation. `da57a429c` restores existing source line endings. `d38a2fe7a` adds a visible, selectable Markdown panel when browser downloads are unavailable.

### Verification

- Full native suite before the two final table-guard tests: **2,532 passed**, 19 warnings, 157.71 seconds. Final focused formatter/lookup suite: **40 passed**, 6 warnings, 2.39 seconds. These are overlapping counts. A mistyped test filename caused one collection-only attempt; it is excluded from passing evidence.
- Export tests: **2 passed**. TypeScript, ESLint and production Next.js builds passed. Push and PR Python/frontend checks all passed for `d38a2fe7a` (runs 35509699139 and 35509700740).
- Both Docker images rebuilt and deployed. API image: `sha256:50f1c48ec49a2ab41416c5a50c4524e65d08a7d8f337b0694bdcfa5c398ca273`. Final web image after the shield fix: `sha256:c585e1ff167eb14a9a2056f71393a033a4f1e7ea221969331508ecd4d83c0be9`. API assets ready; warmup complete without error. A web rebuild initially hit Docker Hub token-service EOF; the unchanged build succeeded on retry. No certificate, credential or host-security changes were made.
- [Local functional evidence](2026-09-20-local-functionality.json): four Titan cards; keyword and core-rule browsing; changelog; 3,893 cached official rows and both Warlord prices at 3,500; valid simulation (500 seeded trials, mean damage 4.074); invalid shooting weapon rejected; roster parse/validate/critique at 150 points; unknown unit line explicitly unresolved.
- [Final fresh-session chat](2026-09-20-final-chat-http.json): HTTP 200 in **55.215 seconds**, no degradation. All six command effects are present. General effects cite codex page 1; the Leman Russ command count/range cite its dedicated L3 card source. This is one checked web answer, not a full September 20 benchmark or latency distribution.
- Earlier [citation-only response](2026-09-20-card-provenance-http.json) correctly separates the L3 source but omits the six effects. Its upstream prose was not recorded, so that observation alone cannot locate the omission to one model. The formatter's independently verified vulnerability was that valid JSON could silently discard an entire answer table.
- [Controlled formatting replay](2026-09-20-formatting-replay.json) uses the same saved September 18 prose for both prompts. The old prompt retained the table in this trial; the revised prompt put the list inside `verdict.calc` instead of top-level `calc`. The deterministic guard rejects this loss at the rendered boundary and retains original prose. This replay does not establish that a prompt alone fixes stochastic content loss. Regression tests cover both omitted rows and correctly reformatted rows; arbitrary paraphrase equivalence is outside this guard.
- Browser chat in both the in-app browser and Edge produced four-datasheet Titan answers with the official shared-rule reference. The download button rendered and was clicked, but automated download completion was not confirmed; no successful file delivery is claimed. The deployed copy panel passed: selecting/copying produced **4,551 characters**, including the AI label, official citation and complete JSON snapshot. Collapsing it restored the normal chat layout. Visual inspection then exposed a clipped four-character verdict shield; commit `397d5d10f` reduces long-label typography and subtitle spacing.

The September 18 agent benchmark remains **115 correct / 0 partial / 0 wrong** with unchanged gold; it was not rerun in full for these web-formatting changes. No database, source-cache, generated wiki or benchmark-gold edits were made. The official price cache remains dated September 14.

Final visual verification after deploying `397d5d10f`: the four-character `4张兵牌` verdict and `FOUR DATASHEETS` subtitle both fit inside the shield without clipping. The answer body and export controls remain intact. This was desktop screenshot inspection; no new exhaustive mobile/browser matrix is claimed.

### Release limits

Public official rules for Gunwagon, Runtherd and 28 Ork enhancement keys remain unacquired. Docker restart durability remains unverified. Cloud work is deferred. Automatic AI writing into the official wiki is intentionally unwired; manual export is explicitly unreviewed. Per-sentence citation correctness outside the inspected examples is not guaranteed.

The separate devlog write/publish was previously blocked by automatic approval review. Project-local documentation contains this handoff; the prepared external-note bundle is pending permission rather than silently bypassing that block.

## Earlier deployment observation, before the web fixes

PR: https://github.com/sha156/wh40k-oracle/pull/74. Application implementation: `39c16a2f91807c551ad90bd457101031dd65cefc`; documentation head before this report: `06711ebd0`.

## Deployed and verified

The user started Docker Desktop. Engine 29.0.1 responded; no host repair or Docker configuration change was needed in this continuation. Recreated the API with `docker compose up -d --no-build api`, using the already-built image `sha256:87926bbb23b0f0ffc4876f6ac2be419b38bdc0be51f7c648a4aab101a9cfb45b`. An immediate health request ended prematurely during startup; the next health check passed, and model warmup subsequently completed with no error. This startup observation is not a persistent service failure.

SHA-256 values for `agent/tools.py`, `agent/llm_client.py`, `db_compile/faction_units.py` and `wiki_engine/operations/query_op.py` match between the running container and branch files. Health reports required assets present, retrieval available and ready true.

A fresh-session question 63 (`坦克指挥官的坦克命令有什么效果？`) completed through `/chat/sync`: **HTTP 200, 51.881 seconds, degraded false**, three tool steps (`get_entity`, faction-qualified `get_entity`, `rag_search`). The answer discloses the Astra Militarum identity, explains all six orders, and covers timing, duration, range and limitations. Raw request/response: [HTTP evidence](2026-09-20-lookup-optimized-http.json). This is one complete API observation, not a latency distribution; do not compare its whole-request time directly with the earlier isolated lookup micro-timings.

The browser codex loaded all four Titan entries and rendered Warlord Titan at 3,500 with its stat line, weapons and FRAME keyword. Accessibility text and a screenshot were inspected after loading completed; the visible layout was intact. No frontend code changed.

## Citation limitation retained

Manually checked local `data/星界军10版中文老湿腐版1.27.pdf`, pages 1 and 33. Page 1 supports the six general order effects, timing and ordinary 6-inch range; page 33 supports the Rogal Dorn card details. The new API answer also attaches page 1 to the Leman Russ card-specific two-order/12-inch claims. Those page citations are too broad: page 1 alone does not support the card-specific numbers. The source-scope instruction improves guidance but does not enforce per-field provenance. This observed limitation is retained for follow-up; the API functional check is not claimed as perfect citation acceptance, and no benchmark gold was changed to conceal it.

## Existing automated evidence

- September 18 full unchanged-gold benchmark: 115 correct / 0 partial / 0 wrong. No full benchmark rerun on September 20; failed earlier runs remain committed.
- Full native suite: 2,527 passed before the last three added tests. Final focused suite: 124 passed. Counts overlap.
- Hosted checks on pre-report head `06711ebd0`: four push/PR checks passed in runs 35508264139 and 35508262305. Previously reviewed hosted Python result: 2,193 passed / 331 skipped; frontend type/lint/build passed.
- Source review found no further release-blocking implementation issue. CRLF-aware branch whitespace check passed. This continuation adds evidence/documentation only; container application code remains the reviewed code.

## Release and remaining work

Final image deployment and functional HTTP/browser verification are complete. Require fresh checks for the documentation/evidence commit before merging PR #74, then fast-forward both project checkouts. Keep the running services and local model/database assets.

Remaining: improve citation precision for merged-card fields, obtain suitable public official rules for Gunwagon/Runtherd and 28 enhancement keys, and establish Docker startup durability. No new source scrape or database synchronization is claimed. The separate devlog repository update was previously rejected by automatic approval review and remains pending; project checkpoint and roadmap contain the current handoff.
