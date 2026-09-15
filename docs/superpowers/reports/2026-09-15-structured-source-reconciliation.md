# Structured source reconciliation acceptance

Tasks 1 and 2 were implemented against the September 14 official snapshot. The available-source corrections are applied to the local database and reproducible after a clean build. Complete released Ork codex coverage remains source-blocked; public previews are explicitly labeled and are not certified as the released codex.

## Applied work

- 390 guarded patches, each carrying the source URL, SHA-256 and page. Exact prior-value checks abort and roll back the entire patch transaction on drift.
- Table coverage: 252 unit records, 54 abilities, 23 weapons, 22 stratagems, 14 enhancements, 9 detachments, 9 datasheet metadata records and 7 model records. Counts describe patch records, including inserts; they are not counts of whole datasheets independently certified.
- Audited the front-page changes across 28 Faction Packs and their highlighted rule changes. Corrected Support transitions, resurrection/arrival wording, targeting exclusions, distances, army rules, and affected defensive/offensive effects. The 541-item text extraction is diagnostic, not proof that every historical rule clause has been independently re-audited.
- Restored FRAME from printed keyword blocks and explicit named update lists: all 208 printed FRAME pages resolved; the resulting database contains 242 units with FRAME. Named removals were checked against current printed source membership. The independent single-model profile comparison covered 425 profiles and found one real numerical discrepancy: Karanak OC 1 -> 3. Four formatting-only Heldrake changes were removed.
- Imported full available Faction Pack datasheets for Dragon Knights, Leystalker, Stonesinger, Clanblade, and Eradicator Squad With Heavy Bolters. The Eradicator variant is a separate datasheet, not a price alias.
- Added Nazdreg from its July 20 official preview, and Extra Sneaky, Minefield Detail, Supa-glowy Fing, Targetin’ Squigs and Blitzboss from the August 17 official preview. Preview status is retained in rule text/source metadata, wiki output and the Nazdreg API card. Current prices do not certify preview rules as current codex rules.
- Mapped four Chaos Titans to their explicitly shared Adeptus Titanicus datasheets, with a fail-closed price-conflict check. Added 28 enhancement identity aliases guarded by canonical faction, detachment, name and ID; corrected two official names, imported three Space Marine enhancements, and handled repeated publisher type suffixes.
- Re-reviewed changed DSL: Masters of Camouflage now enforces Astra Militarum, shooting and non-TITANIC eligibility; Storm of Darkness separates shooting Stealth from melee hit -1; Aggressive Anticipation rerolls failed hits. Other unsupported clauses remain disclosed. Total payload: 2,901 entries (219 encoded, 580 partial, 2,102 not modeled).
- Added target-group conditions for Anti-Monster/Vehicle, Anti-non-Monster/Vehicle, conditional Lethal Hits and conditional Devastating Wounds. Index links retain the conditional identity while pointing at the shared core rule. Composite Chinese labels use existing rule-name translations; they are UI labels, not claimed new official translations.
- Prevented older Chinese abilities and keywords from overriding the reviewed source. Eighteen unit IDs invalidate older translations; 16 matching cached retrieval chunks were removed with a backup, leaving 5,754 chunks. Future full rebuilds exclude these obsolete Chinese documents.
- Regenerated 1,721 unit pages and the entity/index/link outputs. The generated catalog has 328 detachment pages, 1,684 stratagem pages, 1,066 enhancement pages and 50 keyword identities. Seven current unit names and twenty weapon rows lack verified Chinese names and deliberately retain English.

## Reconciliation result

| Measure | Before | After |
|---|---:|---:|
| Official ledger rows | 3,893/3,893 | 3,893/3,893 |
| Comparable unit-price rows in agreement | 1,322/1,322 | 1,333/1,333 |
| Unmatched official unit names | 12 | 2 |
| Unmatched enhancement keys | 67 | 28 |
| Enhancement database rows matched | 840 | 879 |

The ledger retains every official source tuple, including the unresolved entities. Operational price agreement and complete datasheet coverage are separate assertions. The machine-readable companion report contains every remaining enhancement key.

## Remaining source gaps

Gunwagon and Runtherd have public current points but no verified full datasheet was acquired. Twenty-eight Ork enhancement keys remain points-only:

- blitz brigade / boss boomer
- blitz brigade / targetin' gizmos
- brute bosses / brutal but kunnin'
- brute bosses / da gobshot thunderbuss
- brute bosses / morgog's finkin' cap
- brute bosses / proper killy
- brute bosses / surly as a squiggoth
- bully boyz / tellyporta boss
- bully boyz / wimp-kickaz
- da big hunt / it came from da drops
- dread mob / cybork boosta
- dread mob / dreadherder
- flyboyz / flyboss
- flyboyz / impulsive recon
- green tide / 'ardboyz
- kult of speed / competitive streak
- kult of speed / smoky gubbinz
- madcap meks / enhanced runt-maw
- madcap meks / mekwaaagh! mastermind
- madcap meks / temperamental shokka
- taktikal brigade / kill kommanda
- taktikal brigade / throat-slittas
- war horde / da boss is watchin'
- wreckas / kaptin's hat
- wreckas / supa-snazz dakka
- wurrband / da krunch
- wurrband / 'eadbanger
- wurrband / warphead

The released Ork codex/app is the remaining rules authority. Public articles also preview other existing Ork units; this pass does not certify a complete replacement of the old Ork codex corpus. Do not describe the whole project's structured rules as universally current based only on the passing points comparison.

## Checks

- Fresh database: CSV build plus all 11 authority restoration stages; all 390 patches are idempotent afterwards, all 1,333 comparable prices agree, ledger 3,893/3,893, and 2,901 DSL entries apply without skips or fingerprint mismatches.
- Full test suite: 2,515 passed, 19 dependency/deprecation warnings, 133.13 seconds.
- Wiki lint: 0 errors, 1 existing alias-conflict warning, 691 informational notices.
- Live API: health ready; new unit cards return HTTP 200; Stonesinger shooting simulation completes; roster validation computes 60 points and correctly reports a missing Warlord for the one-unit test roster.
- Browser: codex loads and the new heavy-bolter Eradicator card opens with its weapons, rules and 80-point tier. The absent-invulnerable-save display was fixed after this check and verified through the API.
- Live AI benchmark and conversation recall were not rerun: the prior DeepSeek HTTP 402 balance blocker remains unverified. Docker acceptance was not rerun: the prior host WSL blocker remains unresolved.

## Reproduction

Run from the implementation checkout with the project interpreter and the existing ignored source/model assets:

```powershell
.\.venv\Scripts\python.exe -m db_compile build --db db_sources/reconcile-trial.sqlite
.\.venv\Scripts\python.exe -m db_compile.source_reconcile --prune-index local_vector_store
.\.venv\Scripts\python.exe -m db_compile.mfm_sync --snapshot db_sources/mfm/snapshots/2026-09-14 --apply --report db_sources/mfm/sync-report.json
.\.venv\Scripts\python.exe -m wiki_engine.from_db
.\.venv\Scripts\python.exe -m wiki_engine entities
.\.venv\Scripts\python.exe -m wiki_engine crosslinks
.\.venv\Scripts\python.exe -m wiki_engine build
.\.venv\Scripts\python.exe -m wiki_engine keywords
.\.venv\Scripts\python.exe -m wiki_engine lint
.\.venv\Scripts\python.exe -m pytest -q
```

The build command above targets a trial database. `source_reconcile --prune-index` applies the reviewed manifest to the normal database and removes only obsolete translation documents; it does not re-embed or rebuild PDFs. The September PDF index refresh had already completed in the preceding task. A full index rebuild must preserve the same source-authority filters.

Local backups and working diagnostics are outside Git. The final fresh build validates authority restoration, not byte-for-byte Chinese cache equality: current cached Chinese matching differs from the older operational database.

## Sources

- [Official downloads](https://www.warhammer-community.com/en-gb/downloads/warhammer-40000/); exact PDF URLs/pages/hashes are in `db_compile/source_reconcile_patches.json`.
- [Nazdreg official preview](https://www.warhammer-community.com/en-gb/articles/5vutonxu/the-baddest-bad-moon-is-coming-to-warhammer-40000-and-total-war/).
- [Ork detachment previews](https://www.warhammer-community.com/en-gb/articles/nbdkvr51/15-new-ork-detachments-let-you-build-your-perfect-waaagh/).
- [Released Ork points and codex/app availability](https://www.warhammer-community.com/en-gb/articles/x82yzzth/codex-orks-points-are-live-on-the-munitorum-field-manual/).
