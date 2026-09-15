# Official data sync and release acceptance

The application runs locally with the refreshed frontend, database and retrieval index. Current official prices are reconciled. Full release acceptance remains open for the latest structured rule patches, funded live AI checks and an actual Docker build.

## Five-step status

| Step | Result | Evidence or remaining boundary |
|---|---|---|
| 1. Preserve work and reconnect GitHub | Complete | Previous 30 source changes preserved in `709836f4`; implementation on `codex/official-sync-finish` against `sha156/wh40k-oracle`. |
| 2. Make local points agree with the official source | Complete for the fetched snapshot | All 3,893 official rows retained; 1,322/1,322 comparable unit tiers agree, no missing/extra tiers, no enhancement price differences. |
| 3. Refresh official rules and datasheets | PDFs and retrieval refreshed; structured patch review remains | 40 official PDFs downloaded and hashed; 27 changed Faction Packs plus Universal Rules Updates applied locally. Existing unit/weapon/ability/DSL fields have not all been re-audited against these newer patches. |
| 4. Roster text and conversation memory | Implemented; live recall recheck blocked | Exact-name text parser, visible unresolved lines, equipment/model counts, engine validation/critique, bounded expiring session history and current-fact verification gate. Final real-provider recall check cannot finish while DeepSeek returns HTTP 402. |
| 5. Frontend, citations and release verification | Local checks pass; Docker acceptance blocked | 2,496 tests pass, frontend lint/build pass, wiki lint has 0 errors. Docker Desktop cannot start its WSL backend on this host. |

## Official points

Source: [Munitorum Field Manual](https://mfm.warhammer-community.com/en), fetched **2026-09-14 05:51 UTC** across all **30** faction pages.

- The complete ledger includes chapter and conditional prices, repeated-unit tiers, equipment and enhancements. All **3,893 source/database tuples** agree, including provenance.
- Operational matching covers **1,014 faction/name keys**, represented by **1,024 current database unit rows**. **170** keys initially required updates; **11** top-level minima were subsequently corrected so an equipment surcharge cannot become a unit's base price.
- **203 enhancement database rows** changed. **840 database rows** match **907 unique source keys**; the **67 unmatched enhancement keys** remain visible in the full ledger.
- **348 detachment cards** were independently checked against the source and retained with their DP and disposition metadata.
- All **1,322 comparable unit tiers** now agree. Missing tiers, extra tiers, unparsed mapped units and enhancement mismatches are zero. Reapplying the snapshot makes no price changes.
- Unmatched historical records retain their old values for reference but are not exposed as current prices. Codex, translation coverage and keyword statistics use the same membership definition.

The twelve official unit names without an exact datasheet match are: Chaos Reaver Titan, Chaos Warbringer Nemesis Titan, Chaos Warhound Titan, Chaos Warlord Titan, Clanblade, Dragon Knights, Eradicator Squad with Heavy Bolters, Gunwagon, Leystalker, Nazdreg, Runtherd and Stonesinger. The four Chaos Titan entries and Eradicator equipment variant have known shared/variant modelling explanations. A price record does not establish a new complete datasheet.

See [the reconciliation report](2026-09-14-official-points.json) for unmatched enhancements, source hashes and comparison details. The app's **Official points** tab exposes the entire source ledger, including Nazdreg at **175** points.

## Source and retrieval refresh

The [official download catalogue](https://www.warhammer-community.com/en-gb/downloads/warhammer-40000/) yielded 40 verified English PDFs. Core Rules is unchanged. The applied refresh comprises 28 documents and 1,257 pages: **1,256 text pages have matching source-page hashes**, and Chaos Daemons page 13 has no text and is explicitly skipped.

[Universal Rules Updates](https://assets.warhammer-community.com/eng_wh40k_core&key_universal_rules_updates-lu3grocned-rphh78bl6k.pdf), effective August 26, is registered in the rules authority layer. The index contains **5,770 chunks**, including two from this new document. Incremental ingestion replaced 1,735 old chunks with 1,864 refreshed chunks; it reused vectors for 1,143 exact unchanged texts and encoded 721 texts using the same embedding model/settings. New source/page metadata replaces the old metadata even when a vector is reused.

The image-only Terrain Area Footprints sheet has no text layer and remains unavailable to text retrieval. PDFs, models, database and source caches remain local ignored assets. The checked download URLs and hashes are retained in `web/src/data/official-sources.json`.

The Chinese change list remains the **July 26 snapshot**, with 592 faction changes and four universal changes. Its date boundary is visible above the list, alongside links to the newer official English files. No new rules, weapon profiles or translated names were invented to fill gaps.

## Functional verification

- **Python:** 2,496 passed, 19 dependency/deprecation warnings.
- **Frontend:** ESLint and Next.js production build pass; `npm start` serves the standalone output with its static assets.
- **Wiki:** 1,715 unit pages regenerated, entity pages and indexes rebuilt through supported commands, then crosslinked. Lint: **0 errors, 1 alias-conflict warning, 691 informational notices**, no automatic fixes. Keyword index: 46 terms and 2,690 current keyword/weapon-name pairs.
- **Fresh database rebuild:** all ten authority-restoration stages succeed on a temporary database. The complete 3,893-row ledger and both unit/enhancement prices converge after restoration. MFM applies after patch-created enhancements so their frozen insertion prices cannot survive a rebuild.
- **Browser/API roster:** importing five Intercessors with five bolt rifles plus one Apothecary Biologis as warlord yields **150/2,000 points, legal, no issues**. Critique assesses the configured Intercessors against four targets and explicitly leaves the unspecified Biologis loadout unassessed.
- **Retrieval:** a real query retrieves Universal Rules Updates, page 1. A simulated provider outage through the actual web tracing wrapper still returns real retrieved passages and records its search step.
- **Conversation:** tests verify bounded history, isolation, expiry, transport to the next model request and preservation of the fresh-tool requirement for factual questions. The classifier distinguishes recall of a user's choice from rules lookup. Final live recall is **unverified** because the provider now returns **402 Insufficient Balance**. Historical 115-question benchmark scores are not a new acceptance result.

## Reproduction

Run from the repository root using its virtual environment; set the existing local proxy when fetching external sources. On Windows set `PYTHONIOENCODING=utf-8`.

```powershell
# Fetch a complete snapshot and trial/apply it, preserving a database backup.
.\.venv\Scripts\python.exe -m db_compile.mfm_sync --fetch --apply
.\.venv\Scripts\python.exe -m db_compile mfm --check

# Regenerate dependent wiki data in order.
.\.venv\Scripts\python.exe -m wiki_engine.from_db
.\.venv\Scripts\python.exe -m wiki_engine entities
.\.venv\Scripts\python.exe -m wiki_engine crosslinks
.\.venv\Scripts\python.exe -m wiki_engine build
.\.venv\Scripts\python.exe -m wiki_engine keywords
.\.venv\Scripts\python.exe -m wiki_engine lint

# For reviewed replacement PDFs and unchanged embedding settings:
.\.venv\Scripts\python.exe -m scripts.refresh_official_rules --comparison db_sources/downloads/2026-09-14/comparison.json
$env:INGEST_BATCH_SIZE='8'
.\.venv\Scripts\python.exe ingest.py --reuse-vectors
```

Text roster example:

```text
Faction: Space Marines
Detachment: Gladius Task Force
5x Intercessor Squad | weapons=Bolt rifle:5
Apothecary Biologis | models=1 | warlord
```

Unknown or ambiguous lines prevent applying the import. Unsupported optional compositions return an explicit unpriced result; the parser does not guess equipment or translate arbitrary third-party export formats.

## What remains before declaring the project finished

1. Audit the updated Faction Pack rules against structured ability/weapon/stratagem rows, write guarded source-backed patches, and recheck affected DSL fingerprints. Acquire authoritative datasheets for the unresolved new names when available.
2. Update affected current-points benchmark expectations and run the full live AI benchmark after provider credit is restored. The configured key remains local and is not in this report or Git.
3. Repair the host's WSL installation, then actually build and start Docker Compose. Docker reports `wslUpdateRequired`; `wsl --status`, `wsl --version` and the attempted update return “The system cannot find the file specified.” Native local startup is verified, container startup is not.

These are explicit acceptance gaps. The passing unit tests do not establish current official coverage for every structured rule or successful Docker deployment.
