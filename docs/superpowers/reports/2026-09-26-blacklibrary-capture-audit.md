# Black Library snapshot and detail-route audit

Date: 2026-09-26. Status: **partial capture, verified storage; no canonical promotion**.

The user opened Black Library and authorized use of Fiddler to investigate the remaining detail gaps. The September 22 snapshot was copied to `db_sources/blacklibrary/snapshots/20260926-resume` before resuming the reviewed downloader. This run reused verified captures; it is not a fresh complete September 26 crawl. The original manifest hash remains `3027c3df8dc998c52ba32d9f1fccba8646e38f248449ac775019180600996309`.

## Reconciled results

| Measure | Verified result |
| --- | ---: |
| Inventory records | 1,171 |
| Full detail records | 1,071 |
| Explicit empty detail responses | 2 |
| Unresolved detail records | 98 |
| Faction/subfaction names | 38 |
| Stored raw hashes checked | 1,180 |
| Compiled output hashes checked | 7 |
| Hash mismatches | 0 |

All inventory records are accounted for: 1,071 + 2 + 98 = 1,171. Across all request types, the manifest has 1,168 captured, eight source-empty and 98 failed requests. The resume correctly classifies the two previously pending empty army-rule responses. The downloader exits nonzero for the remaining gaps instead of reporting full success. Machine-readable evidence is in [the capture audit](2026-09-26-blacklibrary-capture-audit.json); the ignored runtime log is `blacklibrary-resume-20260926.log`.

## Observed detail lookup and remaining gaps

Fiddler captured the actual full datasheet request after the user opened its attributes, weapons and abilities. `POST /app/unit/detail` supplies `gameId`, `topName` and a lowercase English `unitName`; the observed Aestred Thurga and Agathae Dolan response matched its listed id 574. Only game-content request/response bodies were retained in the ignored snapshot probes. Request headers, credentials and account traffic were not retained.

Ninety-four unresolved inventory rows have no English lookup name. Chinese-name probes returned null data; id/unitId-only probes were rejected. Neither establishes an alternate valid route or that the source rules are empty. Four entries return a different record even when the observed lowercase format is used:

| Requested record | Returned record |
| --- | --- |
| Imperial Agents Ministorum Priest, 992 | Sororitas record 577 |
| Watch Captain Artemis, 1001 | Record 122 |
| Watch Master, 1002 | Record 121 |
| Lord of Change in the additional faction list, 1094 | Record 238 |

These responses remain rejected. Matching a name alone would silently substitute another identity. Resolving the gaps requires a verified detail route or corrected upstream metadata; guessing English names or accepting mismatched ids is not a resolution.

## Authority and next action

This is a third-party community snapshot. Existing canonical caches, SQLite tables, official point prices and generated wiki pages were not replaced by it. The ordinary historical Calgar archive projected earlier remains separate. The snapshot must not override official points or be described as complete current rules coverage. A future importer should compare identities and content on a database copy and retain per-record provenance before any selective promotion. No new usable records were established by this resume, so no promotion was performed.
