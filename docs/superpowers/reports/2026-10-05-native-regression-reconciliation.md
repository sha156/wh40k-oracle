# Native regression reconciliation, October 5

The twelve independently diagnosed test defects at `fff4d974ceabb2d8b45126e42f346ec1f975a417` are corrected without changing application behavior. Identical selected checks on frozen actual inputs changed from **302 passed / 12 failed** to **314 passed / zero failures / zero errors / zero skips**. All 302 preceding positives remain present and passing. This is a scoped test reconciliation, not full-native release acceptance: two actual-data failures remain visible. GNHF owns the eventual scoped commit; root owns integration and shared knowledge handoff with its real commit ID.

## Scope and evidence

Only these six test files and this English report are changed: `test_source_archive.py`, `test_roster_validate.py`, `test_web_api_roster.py`, the actual Helbrute test in `test_agent_tools.py`, the actual bridge test in `test_db_compile_zh_coverage.py`, and the actual composition test in `test_web_api_stage3.py`. Production code, gold, source history, source bindings, other tests and original assets remain unchanged. No selected test is newly skipped or deselected.

Proof output is **`D:/Project/py/RAG/db_sources/native-regression-owned/20261005/`**. `reconciliation.json` contains all 314 exact XML node identities with paired outcomes, mutation outcomes, source/asset hashes and triage evidence hashes. `base.xml`/`base.log` run the unchanged real `fff4d974` checkout; `final-exact.xml`/`final-exact.log` run the final candidate with the same arguments and inputs. The earlier `candidate.xml`/log preserve one new assertion mistake: the provenance table stores source IDs as decimal text, while the reviewed JSON fixture uses integers. Correcting that representation produced the passing `final.xml`/log. The final exact candidate additionally requires the complete canonical composition string, preventing a count check from accidentally matching the digit 1 in price 100; preliminary attempts are not final acceptance.

The independent diagnosis is retained under `D:/Project/py/RAG/db_sources/release-check-20260930/host/native-triage-20261005/`: `REPORT.md`, `archive-base-and-fixture-proof.json`, and `roster-live-input-proof.json`. The original broad run is `host/native-intermediate-fff4-20261005/accepted.xml`/log: 5,385 passed and 14 failed, zero errors/skips. Its exact failure bodies and evidence hashes are indexed in `accepted-failures.json`; twelve are owned here and two are not.

## Corrected invariants

| Diagnosed defects | Correction and retained controls |
| --- | --- |
| Four archive rebuild nodes | Pass an explicitly nonexistent temporary `historical_mfm_snapshot` to the archive-only synthetic fixture. Assert `unavailable` on the positive path. Preserve historical 200-point evidence, exact archive rows, unrelated-table exclusion, all three invalid-value exceptions, byte-identical rollback and absence of `.tmp.sqlite`. |
| Four simple live roster/API totals | Use pinned unit costs Apothecary 60 and Intercessor five models 85, plus the reviewed canonical Eye cost 10: legal totals 155, unpriced-enhancement base 60, API legal 155, critique 145. Keep legal/error, enhancement warning, camelCase, assessed and surfaced behavior assertions. |
| One enhancement boundary | Use the independently proven real composition `22 * 85 + 2 * 60 = 1990`, with one warlord. Hero cost 20 makes 2010. Assert bare legal/absence of `points_over`, enhanced illegal/presence of `points_over`, exact 20-point difference, and surfaced `rot_exempt_uncapped` warnings on both sides. The old bare `24 * 85 + 60 = 2100` already exceeded the limit. |
| One actual Helbrute expectation | Preserve all four exact faction identities and require CSM 125 / DG 105 / TS 110 / WE 120. Synthetic Helbrute fixtures keep their original synthetic prices. No benchmark/gold or price data changes. |
| One actual bridge expectation | Restore the five reviewed bindings from the existing fixture, verify each actual source record equals its frozen reviewed record, and assert exact Chinese text plus source ID/name/faction and canonical name/faction. Explicitly deny Grey Knights source 2863 on AdM `000000847`, and verify that wrong-faction detail row is absent. |
| One actual Barge composition expectation | Preserve Annihilation Barge identity, localized Gauss loadout, authoritative 100-point numerics and Chinese-hidden/English-retained legend. Verify retained community prose still contains one ship/95, require the composition helper to reject it, and require canonical one-model/100 output with neither 95 nor the stale ship prose. |

The archive-only fixture reuses real Armour ID `000004183` without its reviewed historical identity metadata. The strict historical helper correctly rejects that incomplete identity before archive preservation. Its guard is unchanged. The **true pre-history parent is `db494903696fe301da34d309010de92ba0562939`**, not an inferred earlier branch. The existing independent proof exercised its actual unchanged builder, the current default failure, and the current explicitly absent-history path on the same four cases. This iteration verifies the proof's baseline and candidate builder hashes against their actual Git objects; it does not claim a new full suite run on that parent. The new paired 314-node comparison uses actual `fff4d974` as the test-defect baseline.

The unit-price proof reparses six retained October 3 official HTML pages and matches eight relevant rows exactly to their pinned ledger ordinals, costs, URLs, source hashes and capture `2026-10-03T19:00:56.192123+00:00`. See `sourcebound-price-proof.json`. Eye 10 and Hero 20 are independently pinned canonical Bastion enhancement rows confirmed by the host triage and `enhancement-canonical-proof.json`; these particular names do not appear in the inspected generic October 3 official ledger capture, so that capture is not claimed as their direct provenance. No new download or official promotion was performed.

The five source bindings are source 1085 → SM Death Company Marines with Boltguns `000003836`; 363 → NEC Sentry Pylon `000000562`; 9 → SM Uriel Ventris `000000121`; 2863 → GK Servitors `000000397`; and 678 → AE Ynnari Kabalite Warriors `000003916`. The old sixth AdM Servitor expectation represented wrong-faction fan-out. Existing independent rebuild tests still verify clean repeated CSV builds, provenance/canonical/source drift denials, rollback and Windows handle closure.

## Native verification

Interpreter: **`D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`**, verified Python 3.11.9. Working directory: **`C:/Users/Administrator/.codex/worktrees/release-native-regressions/RAG`**. Both runs set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.

The identical selected command is:

```powershell
& 'D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe' -m pytest `
  tests/test_source_archive.py tests/test_roster_validate.py tests/test_web_api_roster.py `
  tests/test_agent_tools.py tests/test_db_compile_zh_coverage.py tests/test_web_api_stage3.py `
  tests/test_mfm_rebuild_history.py tests/test_blacklibrary_rebuild_bindings.py -q `
  --junitxml='<evidence>/<base-or-final-exact>.xml' --basetemp='<evidence>/<base-or-final-exact>-tmp'
```

| Evidence | Exact outcome |
| --- | --- |
| `base.xml` | 314 nodes: 302 passed, twelve diagnosed failures, zero errors/skips. |
| `final-exact.xml` | Identical 314 nodes: all passed, zero errors/skips. Four dependency/escape deprecation warnings remain. |
| Five `exact-*` mutation XML/log pairs | Seven intended assertion failures, zero errors/skips. Enhancement omission, stale-composition admission, wrong-faction projection, archive-validation omission (three cases), and missing Helbrute faction each fail the final tests. |
| Existing historical MFM/rebuild-binding suites | Included without exclusions in the paired 314-node selection; corruption, positive restoration, archive isolation and rollback controls pass. |
| `pending.xml` | Exactly two unchanged actual-data test failures, zero errors/skips. No broad suite repetition. |
| `reconcile-evidence-accepted.log` / JSON | Exact node pairing, original/private input preservation, production-source preservation and Git-object baseline hash checks pass. |

Mutation controls use process-local monkeypatches only. The wrong-faction mutant changes the bridge test's temporary copied DB. No production file or original/private frozen asset is modified by any mutant. Compilation of the six changed Python files and `git diff --check` pass. This repository configures pytest for Python; it has no configured Python build/linter/formatter command requiring a separate run for these test-only changes.

`inputs-before.json` and `reconciliation.json` verify **14 frozen actual inputs** byte-for-byte against both host originals and private copies: DB, Black Library inventory/details, terms, MFM points cache, the two required September 14 history inputs, and October 3 manifest/six HTML pages. Existing tracked wiki inputs are used unchanged. The SQLite hash stays `afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`. All **5,341 tracked files outside tests/docs/orchestrator state** remain byte-identical to the initial worktree source manifest, including all application/source guards, source bindings, gold and generated wiki. No junctions, main asset writes, Docker/service changes, servers or browsers were created. Evidence preparation diagnostics for the parser signature, expected row count and enhancement schema are preserved in `reconcile-evidence*.log`; none are application failures or accepted results.

## Pending actual-data failures and handoff

The separately rerun unchanged `test_web_api_ability_keywords.py::test_whole_library_spans_lose_no_text_and_have_no_hollow_keywords` still sees **3,317 Chinese ability items versus expected 3,332**. The unchanged `test_zh_weapons.py::test_current_units_fully_localized` still reports **Ynnari Kabalite Warriors and Rukkatrukk Squigbuggy** missing Chinese unit names. These two failures require reviewed data projection by their owners; they were not suppressed, relabeled or included in a false full-native success claim.

Independent generic and Python review artifacts, exact candidate file hashes, and a hook handoff are kept in the owned evidence directory. The handoff must carry the real scoped commit ID after GNHF commits. The worker must not create that commit or modify orchestrator/shared notes. At this report's worker stage, commit existence and a clean committed worktree remain orchestration/integration acceptance requirements; no deployment, merge or complete release acceptance is claimed.
