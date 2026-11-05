# Paused review and Black Library capture — 2026-09-22

The user requested **save and stop; continue later**. Source changes and capture output are saved locally. No push, merge or new release is claimed. The active checkout is `D:/Project/py/RAG`, branch `codex/review-answer-provenance`, draft PR #75. HEAD is `641d95b67a2efdd3514399d3e7561c153bbc8f75`; the September 21 final theme/readability revisions and September 22 review fixes remain uncommitted. Preserve them. The separate app checkout at `C:/Users/Administrator/Documents/ChatGPT/RAG` is not the active asset/runtime checkout.

## Implemented and checked

- Historical source archive: ordinary Calgar is found by verified English/Chinese names as a deleted third-party record with historical 200 points, separately from current Armour of Antilochus. The archive survives a canonical DB rebuild with validation before replacement. Exact current canonical and official-ledger prices take precedence; ambiguous current official prices never fall back to a historical price. Historical citations remain distinct from canonical datasheets and official points.
- Runtime projection: the coordinated Docker task backed up the database and added two explicitly deleted records. All 17 preexisting tables, including 1,721 canonical units, were unchanged by complete row-hash comparison; integrity check passed. See `2026-09-22-archive-projection.json`.
- Malformed model `sources` objects/integers and Unicode or oversized page values no longer crash answer formatting. A real card citation and usable answer survive malformed optional PDF references.
- Roster validation rejects unknown factions and incompatible known detachments, discloses unverified ally compatibility, and excludes removed enhancements. Invalid infinite counts no longer raise an API 500. Unknown weapon names cannot silently bypass per-weapon official charges; verified free options remain valid.
- Simulator model counts use the shared composition parser, including named mixed-model units; equipment surcharges do not become unit sizes.
- Frontend request ownership prevents stale codex, points, import, roster-validation and simulator results from replacing current state. Streaming payloads are validated, empty/incomplete streams are rejected, and unverified rosters display `未完全校验`. Original Warhammer appearance and DeepSeek Flash are preserved.
- Docker optional runtime proxy restores verified TLS transport through the existing local proxy. TLS verification remains enabled. Build/runtime settings contain no credentials in tracked files.

## Verification boundaries

- Full native suite: **2,628 passed**, 19 warnings, 137.27 seconds (`pytest-review-20260922.log`). This preceded the last five official-ledger precedence regressions, nine surcharge regressions and four crawler refinements; do not call it a final-tree full-suite run.
- Final official-ledger/archive/tools/provenance focused suite: **133 passed**; all five new precedence cases failed before their fix.
- Final surcharge/roster/import/critique/API focused suite: **69 passed**; six newly added cases failed before their fix. Independent surcharge/import review rerun: **16 passed**.
- Snapshot downloader: **17 passed**. Independent review of downloader and application changes completed without remaining actionable findings in the reviewed boundaries.
- Frontend: **22 unit tests**, TypeScript and ESLint passed. The coordinated Docker task built/deployed the final web image and verified rapid unit/language switches, rapid official-points queries and changed import text during an outstanding request.
- Earlier live deployed checks returned HTTP 200 without degradation for ordinary Calgar, Armour Calgar, Guilliman and their comparison. Historical 200 and September 14 official-snapshot 155/355 remained distinct. Earlier browser suite: 8/8. The final API build was interrupted before deployment on the stop request; the latest source fixes are NOT in the running API image. API remains healthy at image `sha256:344f58db1bedb3ef0f4a50073a8ec962e828b380564572758e75c7a7a4c136ba`, and final web is `sha256:5156e1f53e6792b1f3de10da01106b885c5ba36e790c2a50cdaa48b2997cedda`. Both were left running. Exact evidence: `2026-09-22-docker-acceptance.md`.
- Dark mobile layouts at 390x844 and 320x740 had no horizontal overflow. Markdown preview content was verified; automatic clipboard/download delivery remains unconfirmed.
- `git diff --check` passed at save. No new full 115-question AI benchmark, official-source refresh, Docker Desktop restart-durability test or cloud deployment occurred.

## Black Library snapshot

Output directory: `D:/Project/py/RAG/db_sources/blacklibrary/snapshots/20260922T093137Z`.

The snapshot is ignored by Git, retained on disk, and separate from `db_sources/blacklibrary/details.json` and the runtime database. `scripts/fetch_blacklibrary_snapshot.py` and its tests are saved source files. Requests are rate-limited, bounded retries are used, sanitized raw envelopes and SHA-256 hashes are retained, and resume reuses only verified stored captures. Fiddler authentication stays out of source and saved payloads.

At the stop checkpoint:

| Material | Saved result |
| --- | --- |
| Unit inventory | 1,171 unique records, all 24 pages reconciled against source pagination |
| Factions/subfactions | 38, union of unit inventory and observed faction catalogue |
| Full unit details | 1,071 with content; 2 explicit source-empty results; 98 unresolved |
| Unresolved details | 94 lack an English lookup name; 4 return a different source identity |
| Army-rule responses | 36 captured; 2 return the observed `1010 / 数据不存在 / null` response |
| Powers | 2,514 records across 34 nonempty faction responses; 4 explicitly empty responses |
| Catalogues | 40K faction catalogue, 55 universal-rule entries and the observed AoS faction catalogue |
| Integrity | 1,180/1,180 raw hashes and 7/7 normalized output hashes matched at save |

The first crawl completed under the earlier loaded script. The final script narrowly recognizes the two known army-rule empty responses, but its resume/reclassification had not run at this checkpoint. Therefore the saved manifest honestly remains `partial`, with 100 failed request records (98 detail gaps plus the two known army-rule empty responses). Do not relabel it complete or overwrite failed identity evidence.

The crawler is stopped; its first-pass process exited with code 1 for partial coverage. Manifest timestamp: `2026-09-22T09:40:27Z`; SHA-256: `3027c3df8dc998c52ba32d9f1fccba8646e38f248449ac775019180600996309`. The four wrong-identity records are source IDs 992, 1001, 1002 and 1094. Follow-up `id`/`unitId` probes and embedded army-rule/image inspection were not started after the stop request.

Both ordinary Calgar and Sicarius still appear with explicit deleted labels in the fresh inventory, so the separate disappeared-deleted carryforward file is empty. Ordinary Calgar's fresh detail remains historical 200; community Armour Calgar says 140 whereas the official snapshot says 155. This confirms why a source refresh must not overwrite official current prices.

Fiddler exposed the known army/power/catalogue routes, but no new unit-ID detail route or full core-rules-library route was observed after the user opened more pages. An opened screen can reuse cached responses. Do not claim all mini-program content was captured: the inaccessible detail records, additional unobserved sections, image-only content, AoS unit rules and Kill Team remain outside the completed capture. Preserve source links and exact limitations.

## Resume order

1. Read this checkpoint and the coordinated Docker report; inspect Git and running containers before acting. Do not launch competing builds or runtime DB projections.
2. Resume the existing snapshot directory with the saved downloader, retaining its hash checks. Classify the two proven empty army responses; resolve missing-name/wrong-identity detail requests only from verified endpoint behavior. Inspect fresh Fiddler game-content requests if available. Do not replay unrelated account/forum traffic.
3. Finish a source coverage report and a safe ingestion plan. The snapshot is not yet imported into canonical Chinese details, retrieval indexes or wiki pages. Preserve official authority, historical identity and source deletion status; trial any projection on a copied DB first.
4. Finish final API-image acceptance and the latest unverified roster/simulator journeys. Then run the final native suite and necessary targeted checks; preserve earlier failures as evidence.
5. Inspect intended diffs and sanitize evidence, commit source/tests/docs, update PR #75 to its final scope, push and inspect CI before considering readiness/merge. No current merge approval or completion is inferred from this paused checkpoint.
6. Finish the project knowledge handoff using the local pending bundle. External note publication was previously rejected by automatic approval review; do not bypass it. No new commit explanation may name an invented commit.

Remaining product limits are unchanged: suitable public official rules for Gunwagon, Runtherd and 28 Ork enhancement keys; Docker restart durability; automatic archive delivery; rolling model-quality evaluation; cloud deferred.
