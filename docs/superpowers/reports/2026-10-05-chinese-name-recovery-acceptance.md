# Chinese display-name recovery and finite English fallback acceptance

## Release integration status (2026-11-03)

Decision C (the narrow empty-cell name-restore change to `populate_zh_details`) needs explicit user approval and is **unanswered**. The release therefore integrates the tests, fixture and this report **without** that `db_compile/blacklibrary.py` change. In the release:

- The nine names in the table below are **not** restored; `units.name_zh` stays empty for all nine. The fixture keeps them as `pending_name_recoveries` with their accepted source evidence.
- `ORK/000001542 Rukkatrukk Squigbuggy` is a registered, reviewed **English unit-name fallback** (`fallback_units` in the fixture). Current-name coverage passes only when the missing current unit names equal exactly that list.
- Captain on Bike's two English weapon-name fallbacks are unchanged.
- The guard change is saved verbatim as `db_sources/release-check-20260930/host/finish/R4/decision-C-guard.patch` (SHA-256 `dc77a4594991dd96124bf7cb2532dd6271df2fdf64d8246d738454ccb11189c3`). Approving C means applying that patch and reverting the declined-path test expectations.

The sections below describe the reviewed **candidate** (with the guard) as accepted on 2026-10-05. Statements that the projection "now restores" names describe that candidate, not this release.

Normal copied language projection now restores the missing current display name `ORK/000001542 Rukkatrukk Squigbuggy` to retained source 464's **跳跳送餐车**. The complete copied current inventory has no missing unit display names and exactly two source-proven English weapon-name fallbacks: **Hand flamer** and **Twin boltgun** on `SM/000002702 Captain on Bike`. This is name projection and localization-gap acceptance, not current full-body, Black Library, Codex or tournament verification. No active assets are promoted.

The real starting commit is `41dc49895e849f864bb061875e5fb81311d7d08a`. The saved parent implementation is checked against that Git blob. GNHF owns the eventual scoped commit; no manual staging, commit, push, provider/network operation or service change occurs. Exact commit and subsequent clean-worktree verification remain pending, so the entire loop's stop condition is not yet met.

## Inputs and implementation

The starting supported-native evidence is `D:/Project/py/RAG/db_sources/release-check-20260930/host/native-intermediate-fff4-20261005/accepted.log` and `.xml`: **14 failures / 5,385 passes**, including missing current unit names. The separate root copied-stage audit is `D:/Project/py/RAG/db_sources/native-regression-owned/20261005/chinese-projection-audit/proof.json`. Its five accepted spelling bindings restore 1,139 → 1,144 detail rows and 3,317 → 3,330 ability items; the formerly counted two wrong-faction AdM Servitor abilities stay denied. These are preceding source/count facts, not a new full-native acceptance result.

Only four actual inputs were frozen and copied into this private worktree/candidate. Their main, frozen and private-input hashes still agree after validation:

| Input | SHA-256 |
| --- | --- |
| `db/wh40k.sqlite` | `afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855` |
| `db_sources/blacklibrary/units.json` | `a497c85edbc0f6ada3f7492e7a743e2948d42877f7d168d3ef96d925b132fc76` |
| `db_sources/blacklibrary/details.json` | `665c54c74f13b9ba29b7eb7d93df98c0b5982a9d5afd9907fede439bcf0bedbc` |
| `db_sources/blacklibrary/weapon_names_history.json` | `d62eb339627ad99a650c1f60052c64b652bdebbb36a90b72f08298a9503f1fb3` |

`populate_zh_details` already accepts source 464 by its exact normalized English identity and records its canonical/source attribution. The newer inventory lists plural source 2984 as `RUKKATRUKK SQUIGBUGGIES`, so inventory name filling cannot restore the singular canonical display name. Previously, accepted details could fill missing canonical names only when they were one of the five frozen spelling bindings.

The change fills `units.name_zh` from a nonblank string on an **already accepted detail**, only where the canonical cell is null or empty. It adds no candidate lookup or matching path and changes no identity, faction, canonical, ambiguity, hash, quarantine or binding guard. Supplied names, including whitespace-only supplied cells, remain intact. The existing transaction contains both the name update and detail/identity projection, so an insertion failure rolls them back together. Source stats are never copied into official columns.

## Exact copied data reconciliation

Both parent and candidate run the normal `stage_zh_details` then `stage_zh_weapons` offline on separate copies of the same frozen database. Both produce **1,144 detail rows / 3,330 ability items**, and reconcile **1,010 current-MFM units / 4,835 current weapons**. Root owns final language/count accounting after the separate 13 official source changes; these copied counts must not replace that acceptance.

The complete parent/candidate comparison finds exactly **nine additional null-to-Chinese display-name cells**, not only the current Squigbuggy. Every one already has the same accepted identity/detail on the parent. The eight other names are outside this snapshot's current MFM membership; restoring their names does not make their bodies current or establish legality.

| Canonical ID / faction | Canonical name | Accepted source ID | Restored display name | Current MFM membership in copy |
| --- | --- | --- | --- | --- |
| `000000019 / ORK` | Burna Boyz | 405 | 烧烤小子 | No |
| `000000044 / ORK` | Lootas | 420 | 拾荒小子 | No |
| `000001538 / ORK` | Kustom Boosta-blasta | 462 | 魔改爆裂车 | No |
| `000001539 / ORK` | Shokkjump Dragsta | 465 | 折跃飚速车 | No |
| `000001540 / ORK` | Boomdakka Snazzwagon | 461 | 爆裂靓车 | No |
| `000001541 / ORK` | Megatrakk Scrapjet | 463 | 超霸拖垃圾 | No |
| `000001542 / ORK` | Rukkatrukk Squigbuggy | 464 | 跳跳送餐车 | Yes |
| `000000103 / SM` | Eradicator Squad | 68 | 根除者小队 | No |
| `000002285 / SM` | Death Company Marines with Bolt Rifles | 480 | 装备爆弹步枪的死亡连小队 | No |

All other logical table rows equal the parent's, including language bodies/identities, weapon names/profiles, aliases, source archives and official ledgers. The glossary's insertion order can differ between processes, but every term/translation/observation row is identical. The original database → candidate normal stages have **14** missing name restorations: the preceding five bindings plus these nine. All **1,168 originally supplied nonempty canonical name cells** remain exact. Every official unit/weapon column and all other protected original tables remain unchanged by the normal language stages. This preserves the existing 47 unsupported historical canonical names without recertifying their provenance. GK source 2863 still never projects to AdM `000000847`; governed drift remains final denial, and all four wrong-identity quarantines remain enforced.

Evidence: `D:/Project/py/RAG/db_sources/chinese-name-recovery-owned/20261005/paired-data-reconciliation.json`, both `parent/proof.json` and `candidate/proof.json`, and `final-accounting.json`. The small actual-source fixture pins all nine incremental accepted lineages and their record fingerprints.

## English fallback evidence and acceptance

The current Captain on Bike inventory row is source **3030**, Chinese display name **摩托连长**, with an English identity and no inline body. It is not a reviewed empty-listing exclusion. There is no exact Captain on Bike record in the retained details cache, no accepted `unit_zh_detail` for canonical `000002702`, and no guarded history weapon-name record for that unit. The source's Shield-captain on Dawneagle Jetbike is a different unit/faction and supplies no mapping for this card.

| Exact weapon identity | Range / A / BS / S / AP / D | Official keywords | Supported disposition |
| --- | --- | --- | --- |
| `000002702_w4`, Hand flamer | `12 / D6 / N/A / 3 / 0 / 1` | `ignores cover, pistol, torrent` | Preserve exact English name |
| `000002702_w9`, Twin boltgun | `24 / 2 / 2 / 4 / 0 / 1` | `twin-linked` | Preserve exact English name |

Other real stored Hand flamer profiles use **喷火手枪** and **手持喷火器**. Their complete 19-row identity/profile evidence is frozen; it does not authorize choosing a global glossary winner for Captain on Bike. No retained details weapon-profile name is the literal **双联爆弹枪**. A broader text search does find it in source **1265**, `【Legends】Land Raider Helios`, solely as optional-loadout prose; that record's actual ranged profiles instead include 风暴爆弹枪. That prose does not identify a Captain on Bike profile or establish its translation.

The previous unconditional all-Chinese assertion is replaced with complete current-inventory reconciliation: **every missing unit name fails**, and the complete missing-weapon rows must equal precisely these two registered slots. Registration includes weapon ID, canonical unit ID/faction/English and Chinese display names, all six profile fields, official keyword JSON and unit keyword identity. A new gap, changed profile/identity, newly supplied translation or newly accepted body reopens review. Three source input hashes and the exact listing-policy hash also gate the evidence. Nothing is skipped to make this acceptance pass, and no translation, override, profile borrowing or retired fan-PDF text is introduced.

The actual FastAPI `/codex/units/000002702?lang=en` and `?lang=zh` route is exercised with a closed `TestClient`, without model lifespan startup or an external service. Both responses are HTTP 200 and show the exact two English names. Their rendered range, attack count, hit skill, strength, AP and damage are equal between languages, with equal keyword identities. Copied card payloads are saved in both paired-stage proofs.

## Paired validation and handoff

Interpreter: `D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`, **Python 3.11.9**. The final identical seven-module selection covers the two owned test files plus existing rebuild bindings, identity, document identity, weapon history and Black Library tests. The parent substitution uses the verified starting source while preserving its real sibling-data paths; candidate runs the current implementation.

| XML-confirmed final result | Passed | Failed | Errors | Skipped |
| --- | --- | --- | --- | --- |
| Parent, 193 cases | 163 | 30 | 0 | 0 |
| Candidate, same 193 cases | 193 | 0 | 0 | 0 |

Parent failures are the two null/empty restoration positives, normal-stage restoration, complete current coverage, nine actual lineage/name checks, and 17 negative tests' explicit passing-baseline prerequisite. The latter fails because the parent still lacks the Squigbuggy name, before any mutation. On candidate, each negative starts from accepted coverage and then rejects the changed identity/profile or added missing name. No overwrite, blank-name/no-body, rollback, governed source/canonical/hash drift, wrong-faction, quarantine and historical fingerprint checks pass. Both actual fallback route probes pass even on the parent; the defect is name restoration, not card rendering.

Final logs/XML are `parent/final-selected-tests.*` and `candidate/final-selected-tests.*` under the owned proof directory. Syntax compilation and `git diff --check` pass. The required interpreter has no installed Ruff/Black/mypy/pylint, so no formatter/static-linter success is claimed. The sole pytest warning is the existing Starlette/AnyIO `BlockingPortal` deprecation. No broad full-native repeat, build/deployment/browser/benchmark/CI or universal accuracy claim is made.

The initial 48-case candidate check recorded **1 failure / 47 passes** because it searched whole details for 双联爆弹枪 rather than weapon-profile names. Its XML is retained as `candidate/initial-tests.xml`; source 1265's prose is now explicitly distinguished. Two preliminary inspection assumptions also failed: the input DB has no `blacklibrary_detail_identity` until the normal stage creates it, and the rendered card field is `skill`, not `bsWs`. These were audit-helper corrections, not relaxed source guards or runtime fixes. The intermediate 184-pass selected run remains preserved but is superseded by the final 193-case paired run.

Independent generic and Python reviews cover code, all nine actual name deltas, finite fallback evidence and paired validation. Their owned records are `D:/Project/py/RAG/db_sources/chinese-name-recovery-owned/20261005/generic-review.md` and `python-review.md`; final report consistency is checked before delivery.

Only `db_compile/blacklibrary.py`, `tests/test_zh_weapons.py`, `tests/test_blacklibrary_detail_names.py`, `tests/fixtures/chinese_name_recovery.json` and this report belong to the eventual scoped commit. The six other native-regression test files, official-field owners' files, matcher/binding/reconciliation/history/name-override/application/gold files, orchestrator notes and shared knowledge indexes are untouched. All finite commands have ended; no long-running process was started. Root must integrate with the separately reviewed official overlay and own final immutable language accounting/promotion. GNHF must create the exact scoped commit before a later clean-worktree/commit check can close the loop.
