# Black Library import and remaining source gaps

Date: 2026-09-26. Runtime: D:/Project/py/RAG. Branch: codex/review-answer-provenance. Local Docker is the delivery target; PR #75 remains a draft.

## Delivered

Validated the resumed 40K snapshot against all 1,180 raw capture hashes and seven output hashes, raw inventory identities and detail request/response identities. Imported 1,071 verified captures into a non-destructive merged cache: 383 existing records changed, 13 source IDs added, and 14 older records retained with explicit provenance. Merged cache: 1,085 records. The snapshot includes September 22 captures; this is not a claim of a wholly fresh September 26 crawl.

The active database now has 1,150 Chinese detail rows (previously 1,135), while canonical unit count remains 1,721. Ten previously empty Chinese unit names were filled. All 1,649 prior alias mappings survive; 36 new mappings bring the total to 1,685. Chinese weapon names cover 8,356/9,337 total rows and 4,971/4,971 active weapon rows. The 15-table authority comparison excludes only the intended Chinese name columns and confirms unchanged official numbers, English ability bodies, official prices and rule tables. No new canonical English datasheets were invented from community cards.

A partial cache refresh originally removed old aliases and 50 active Chinese weapon labels. The restoration stages now consume verified previous alias pairs and 70 weapon labels guarded by canonical identity and the complete combat profile. Changed official profiles cannot inherit old labels. The ignored history caches are required local rebuild assets, alongside the existing ignored source caches.

Refreshed the search index from 5,681 to 5,910 chunks: Black Library 904 to 1,133; all 4,777 other documents, metadata and vectors were retained exactly. Reused 945 exact-text vectors and embedded 188 changed/new texts. The retired Votann PDF remains excluded. Refreshed 228 unit pages relative to the previous commit, then rebuilt indexes and keyword pages. Scoped crosslink injection avoids touching unrelated entity prose; ordinary Chinese temporal wording no longer acquires the Ork stratagem link. Wiki generation now uses complete English abilities when the Chinese entry count is smaller, matching the existing API rule.

## Verification

- Final native suite: 2,712 passed, 19 warnings, 156.35 seconds. Log: blacklibrary-final-tests-20260926.log.
- Preserve the earlier failure evidence: blacklibrary-full-tests-20260926.log reported two failures / 2,703 passes (a reconciled ability-count baseline and the real weapon-name regression). Final focused history/wiki/data checks: 42 passed.
- Wiki lint: zero errors, one existing aggregated alias warning, 691 information entries.
- Final diff whitespace check passed using the repository's CRLF-aware check. Source, tests and generated changes reviewed locally; no independent agent review is claimed.
- API image: sha256:4c60f9f943e88290ad5b2810cbb38cc422726b4034fa6899b47884f6a75d2a49. Health ready and retrieval true; warmup complete with no error.
- Five fresh live card requests returned HTTP 200, including Stonesinger, Clanblade, Nazdreg, Warboss and Guilliman. Stonesinger browser card displayed the new Chinese names and all three English abilities including Support.
- Fresh Stonesinger chat returned HTTP 200 in 12.187 seconds, one successful datasheet lookup, four citations and 60 points. This is one scoped live observation, not a rerun of the 115-question benchmark.
- Frontend source was unchanged. Earlier 22 unit tests and 12 Chrome journeys are previous-release evidence, not a new full E2E run for this import.

Machine-readable evidence is in the adjacent database-verification, merge, ability-reconciliation, gap-section-audit, index-refresh, health, live-cards and live-chat JSON reports dated 2026-09-26.

## Remaining source gaps

A targeted September 26 refresh reconciled all 1,171 inventory rows and retried the 98 failed detail records. Zero resolved: 94 still lack the English lookup name required by the observed route; four requests still return a different identity. Two other source-empty responses remain separately accounted for. Some of the 98 entries are products, bundles or alternate listings, not distinct missing canonical units. See [all 98 records grouped by faction](2026-09-26-blacklibrary-unresolved-by-faction.md) and the adjacent CSV.

The captured rule sections include 36 army rules, two empty army responses, 2,514 powers and 271 nested detachments. The nested detachment content fields were empty. Thirty-nine gap records also occurred in embedded inventories, but none supplied detail content there. Observed Fiddler routes supplied no additional datasheet endpoint. These community rule captures remain separate from canonical official rule bodies. No complete-site, AoS or Kill Team coverage is claimed.

Guilliman already has Chinese data: five source entries versus seven English ability rows. The API's count-only completeness comparison therefore selects English, even though three Chinese effects are nested inside one entry. This is a known coarse heuristic, not a failed import. Cached Supreme Strategist also says once per turn while canonical English says once per battle round. A future ability-level mapping must verify content and freshness before allowing mixed/Chinese presentation. This diagnosis is recorded without bypassing the guard or inventing a translation.

The five requested Space Wolves examples have official Legends datasheets and existing English database rows. Official PDF availability does not verify every local field against the newest release. Gunwagon/Runtherd community captures do not close the outstanding official English rule gaps. Official prices remain the September 14 snapshot. Other fan-PDF retirement still awaits a scope decision. Cloud and host reboot durability remain deferred.

## Rebuild and recovery

Pre-import database, source caches, wiki and full index are preserved in ignored archive/blacklibrary-import-20260926/. Validated source snapshot: db_sources/blacklibrary/snapshots/20260926-resume/. Targeted retry: snapshots/20260926-gap-recheck/. Staged trial assets/reports: db_sources/blacklibrary/staged-20260926/.

Use python -m db_compile.blacklibrary_snapshot with --snapshot, --existing and a new --out staging directory. Inspect its report before publishing caches. Preserve aliases_history.json and weapon_names_history.json beside the canonical Black Library cache. The normal offline authority restoration stages consume them. Generate unit pages with python -m wiki_engine.from_db, followed by python -m wiki_engine crosslinks --units-only, build, keywords and lint. Use python -m scripts.refresh_blacklibrary_index with the current database, existing index, a new output directory and the same complete local BGE-M3 snapshot. Compare authoritative tables, retained aliases and non-Black-Library vectors before publishing staged assets. Restart the API after publishing.

## Subsequent user review

The 98 raw failures now resolve to 94 reviewed empty-listing exclusions and four actionable identity mismatches; see the reviewed-listings report. The original capture counts remain historical evidence. Chinese 每个回合一次 does not by itself prove a player-turn/battle-round discrepancy: the translator may use 回合 for a battle round. Official PDF and exact cached Chinese source images were prepared for expert review; no definitive translation-error claim is made.
