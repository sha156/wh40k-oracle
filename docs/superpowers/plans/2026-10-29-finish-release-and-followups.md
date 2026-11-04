# Finish plan: release PR #75, then all follow-ups

Written 2026-10-29 from the Oct 29 review (full native run, branch audit, data-drift
diff). It covers every open item from that review. Each step is self-contained:
read **Global context**, **Decisions**, **Invariants**, then only the step you run.

**Start with R0 today.** The weekly scheduled job runs again **Sun 2026-11-01 04:00**
and will overwrite the database again.

## Status

| ID | Step | Depends on | Parallel with | Model | Size | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R0 | Stop the drift, archive drifted state | — | — | default | S | done 2026-11-03 |
| R1 | Restore the frozen data baseline | R0 | R2 | default | S | done 2026-11-03 |
| R2 | Fix CI fixture + English-name lookup regression | R0 | R1 | strongest | M | done 2026-11-03 |
| R3 | Merge native-regressions + context-points | R1, R2 | — | default | M | todo |
| R4 | Chinese-name recovery (Decision C) + ability-count expectation | R3 | — | default | M | todo |
| R5 | Publish reviewed Chinese projection + regenerate wiki | R4 | — | default | M | todo |
| R6 | Full verification, push, CI green | R5 | — | default | M | todo |
| R7 | Docker images, browser suite, live chat checks | R6 | R8 | default (strongest judges answers) | L | todo |
| R8 | 115-question benchmark | R6 | R7 | default (strongest triages) | M | todo |
| R9 | Release: PR text, merge, handoff notes | R7, R8 | — | default | M | todo |
| F1 | Finish the authority rebuild | R9 | F5-prep, F6, F7 | strongest | XL | todo |
| F2 | Staged update + safe weekly job | R9 (F2.1–F2.3); F1 (rest) | F1 (F2.1–F2.3 only) | strongest | L | todo |
| F3 | Adopt current official data (re-baseline) | F2 | — | strongest | L | todo |
| F4 | New Adeptus Custodes codex content | F3 | F5 | strongest | XL | todo |
| F5 | Official field ledgers → promotion | R9 (prep), F3 (promote) | F1, F4 | strongest | L | todo |
| F6 | Long-tail data gaps and test quality | R9 | F1–F5 | default | M (many small PRs) | todo |
| F7 | Docker restart durability | R7 | anything | default | S | todo |
| F8 | Repo hygiene + CLAUDE.md trim | R9; F1, F2, F5 for their worktrees | — | default | M | todo |

Model tiers: **strongest** = Opus-class (or Codex's top tier) for design, review and
judgement; **default** = Sonnet-class for mechanical work. Sizes: S < 1 h,
M = a few hours, L = 1–2 days, XL = several days.

```
R0 ─┬─ R1 ─┐
    └─ R2 ─┴─ R3 ─ R4 ─ R5 ─ R6 ─┬─ R7 ─┬─ R9 ─┬─ F1 ─ F2(rest) ─ F3 ─┬─ F4
                                 └─ R8 ─┘      ├─ F2.1–F2.3 (parallel with F1)
                                               ├─ F5 prep ───────────┴─ F5 promote
                                               ├─ F6 (any time)
                                               └─ F7 (after R7)          F8 last
```

## Global context

**Repository.** `D:/Project/py/RAG`, GitHub `sha156/wh40k-oracle`, default branch
`main` at `1ae27136f`.
- Release branch: `codex/review-answer-provenance`, HEAD `6b8e6a8f8` plus this
  plan's commit. Draft PR #75 carries 139 commits and 732 files.
- On Oct 29, PR #75's Python CI job was red (one test, fixed in R2); the frontend
  job was green.

**Python.** `D:/Project/py/RAG/.venv/Scripts/python.exe` is 3.11.9. Always set
`PYTHONUTF8=1 PYTHONIOENCODING=utf-8`, because the console is GBK.

**Network.** Use this for `git push`, `gh`, MFM/Black Library fetches, npm and
Docker builds: `export HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897`.

**Full native suite** (about 6.5 min; always target `tests/`):

```bash
EV=db_sources/release-check-20260930/host/finish/<step-id>; mkdir -p "$EV"
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -m pytest tests/ -q \
  -p no:cacheprovider --junitxml="$EV/full.xml" --basetemp="$EV/tmp" > "$EV/full.log" 2>&1
grep -E "^(FAILED|ERROR) " "$EV/full.log"; tail -2 "$EV/full.log"
```

Oct 29 baseline: HEAD against the drifted database gave **18 failed / 5,496 passed /
0 errors**. Evidence lives in gitignored `db_sources/release-check-20260930/host/finish/`.

**One writer.** Do not let Codex, GNHF or the scheduled task write to this repo or its
assets while a step runs, unless that step is assigned to them. GNHF exits on a dirty
tree, so keep the main checkout clean between steps.

### Worktrees (all under `C:/Users/Administrator/.codex/worktrees/`)

| Path | Branch | HEAD | State | Used in |
| --- | --- | --- | --- | --- |
| `release-native-regressions/RAG` | `codex/release-native-regressions` | `41e578add` | clean, test-only | R3 |
| `release-rule-chronology/RAG` | `codex/release-context-points` | `2a2e4bc16` | clean, host-approved | R3 |
| `release-final-integration/RAG` | `codex/release-chinese-name-recovery` | `41dc49895` + 5 uncommitted files | **dirty** | R4 |
| `release-native-build-recovery/RAG` | `codex/release-authority-rebuild` | `a522c820c` + 3 uncommitted files | **dirty** | F1 |
| `release-api-reliability/RAG` | `gnhf/objective-finish-the-2621e6` | `4e820136a` | clean, review requested changes | F2 |
| `release-field-sororitas-deathguard/RAG` | `gnhf/objective-finish-eve-d1d51d` | `cf72f4e1b` | clean, report-only | F5 |
| `release-official-revisions/RAG` | `gnhf/objective-finish-onl-ce6398` | `abccf9d60` | clean, report-only | F5 |
| `release-python-security/RAG` | `gnhf/objective-finish-eve-e81d02` | `5f7cb19b9` | integrated | F8 |
| `release-web-security/RAG` | `codex/release-snapshot-resilience` | `6b3dabd40` | merged | F8 |

Recovery copies of both dirty worktrees are in
`db_sources/release-check-20260930/host/stop-20261005/`.

### Data facts (verified Oct 29)

**Frozen baseline.** All pending branch evidence pins these files:

| File | SHA-256 | Restore source |
| --- | --- | --- |
| `db/wh40k.sqlite` | `afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855` | `db_sources/chinese-name-recovery-owned/20261005/frozen/db/wh40k.sqlite` |
| `db_sources/blacklibrary/units.json` | `a497c85edbc0f6ada3f7492e7a743e2948d42877f7d168d3ef96d925b132fc76` | `…/20261005/frozen/db_sources/blacklibrary/units.json` |
| `db_sources/blacklibrary/details.json` | `665c54c74f13b9ba29b7eb7d93df98c0b5982a9d5afd9907fede439bcf0bedbc` | unchanged on disk (also in `frozen/`) |
| `db_sources/blacklibrary/weapon_names_history.json` | `d62eb339627ad99a650c1f60052c64b652bdebbb36a90b72f08298a9503f1fb3` | unchanged on disk (also in `frozen/`) |
| `db_sources/mfm/mfm_points.json` | `20f3c54d5435765d3b075cc608de81aa7371aa582ef38ebe16acf136f02f9040` | `db_sources/release-check-20260930/host/source-freshness-20261004/automatic-update-preserved/mfm_points.json` |

The baseline's raw MFM snapshot is `db_sources/mfm/snapshots/fetch-jtgkljt3`, fetched
2026-10-03T19:00:56Z.

**Drifted state.** The weekly job (scheduled task `wh40k-oracle-update` →
`scripts/run_db_update.bat` → online `db_compile update`) ran on Oct 18 and Oct 25.
It left:
- DB `7aedef12c629c42ffca2fc12d9f90070c179ec0e209344961f48c1b2702cb999`,
  `units.json` `52ae5cc1…`, `mfm_points.json` `47f4ad0c…`;
- new snapshots `fetch-xnquh5wv` (Oct 18) and `fetch-tkgj_vyr` (Oct 25);
- 995 → 1053 aliases;
- 51 Chinese unit names lost, 100 rewritten and 6 gained, all from unreviewed live
  Black Library data;
- current units 1010 → 997.
- **Nov 1 update (R0 finding, 2026-11-03):** the job ran again on 2026-11-01 before R0,
  overwriting the Oct 25 DB (no copy of `7aedef12…` survives). Current drifted state:
  DB `8f7b46cdf2f1e8be767f38d8b78311866211d1e5fb96bffaba52b95cfaea2228`, `units.json`
  `d824b6d3…`, `mfm_points.json` `bf6e7b60…`, new snapshot `fetch-6t362dci`; archived
  in `archive/drift-20261101/` with a manifest. The Oct 25 numbers above are historical.

**The drift also holds a genuine GW update.** Keep it for F3:
- a new Adeptus Custodes codex: 11 official units with no datasheet (e.g. Custodian
  Guard Sodality, Prosecutor Squad), 13 units retired, 16 repriced (e.g. Blade
  Champion 125 → 195);
- Exorcist 220 → 215;
- official ledger +26 / −35 rows;
- the downloads page reports 12 new, 26 revised and 8 removed PDFs.

**Lookup anchors.**
- At HEAD, `get_datasheet("Intercessor Squad")` returns `ambiguous` (regression R2).
- Pre-merge code `fff4d974c` resolves it exactly to `000001157`.
- `Helbrute` must stay ambiguous (four factions).
- `仲裁者小队`, `罗伯特·基里曼` and canonical IDs resolve today.

## Decisions (defaults apply unless the user says otherwise)

- **A — Baseline.** Default: restore the Oct 3 frozen inputs for the release (R1) and
  adopt current GW data afterwards (F3). Alternative: adopt now, which means running
  F3 before R3 and re-pinning all evidence first. That is much longer.
- **B — Release scope.** Default: the release is R0–R9; authority rebuild (F1) and
  staged update (F2) become follow-up PRs. They harden the update pipeline, aren't
  user-facing and are the least finished, and `main` already runs today's pipeline.
  Alternative: run F1 and F2 between R4 and R5, so R5 publishes through them.
- **C — Name-restore guard (R4).** This needs explicit approval. If approved, merge
  the narrow change: it fills empty `units.name_zh` cells only, from details the
  identity gate already accepted, and restores 9 names. If declined or unanswered,
  keep `db_compile/blacklibrary.py` unchanged and register Rukkatrukk Squigbuggy
  (`000001542`) as a reviewed English unit-name fallback.
- **D — Merge style for PR #75.** Default: a **merge commit** with a curated message.
  Reports and evidence cite dozens of SHAs (e.g. `41dc49895`, `fff4d974c`), and the
  F1/F2/F5 branches are built on this history; a merge keeps both reachable from
  `main`. Alternative: squash for a clean log, then move each follow-up branch with
  `git rebase --onto main <old-merge-base> <branch>`. This reverses the squash
  suggestion in the Oct 29 review, for those reasons.
- **Go-aheads.** The R8 paid benchmark run and the R9 merge each need the user's
  explicit go-ahead at that time.

## Invariants (check at the end of every step)

1. Dirty worktrees are never reset, cleaned or stashed away: the Chinese-name
   worktree until R4, the authority-rebuild worktree until F1. Their uncommitted
   files still exist.
2. Active assets change only in R1 (restore), R5 (publish) and F3/F4 (adopt), each
   with a backup and a hash receipt. Active assets are `db/wh40k.sqlite`,
   `db_sources/blacklibrary/*.json`, `db_sources/mfm/*`, `wiki/` and
   `local_vector_store/`. Elsewhere, `sha256sum db/wh40k.sqlite` stays unchanged.
3. Scheduled task `wh40k-oracle-update` stays **Disabled** until F2 exits.
4. `git status --short` in the main checkout is empty when a step ends.
5. No new skip, xfail or deselect.
6. Gold files (`qa_gold.json` = v3.6 `a402aed8…`, `benchmarks/v3_edition11/qa_gold_v3.*.json`)
   change only through the versioned-benchmark review.
7. From R2 onward the lookup anchors hold: Intercessor Squad, Captain and Drop Pod
   resolve by English name; Helbrute stays ambiguous; `罗伯特·基里曼` resolves.
8. No whole-file line-ending flips. Check `git diff --stat` before committing; see
   memory `worktree-crlf-vs-lf-blob`.
9. Before any push, the outgoing diff has no `sk-`, `ghp_` or `SESSDATA` values. The
   two known synthetic test values are allowed.

## Anti-patterns (each one already cost this project time)

- **Focused selections as acceptance.** Treating a focused test selection as
  acceptance let R2's two defects through the 649/696-test checks. Every merge into
  the release branch ends with the full native suite.
- **Online update on the main checkout.** Running `python -m db_compile update` online
  there is what drifted the baseline. Until F2 lands, use narrow offline stages on
  copies.
- **Full rebuild on the active DB.** Before F1, don't run `python -m db_compile build`
  on the active DB; retained-metadata preservation through a fresh rebuild is
  unproven.
- **Concluding from a stale branch.** The context-points worktree seemed to fix R2's
  regression only because it predates it. Always test the actual merge result.
- **Silent re-pinning.** Don't re-pin hashes or edit expectations without naming the
  reviewed fact that changed.
- **Hand edits.** Don't hand-edit SQLite rows or generated wiki pages; regenerate with
  the documented commands.
- **Frontend builds from Git Bash/MSYS.** MSYS rewrites `/api`; use PowerShell.

---

# Phase 1 — Release (PR #75)

## R0 — Stop the drift and archive the drifted state

- **Depends on:** none. **Model:** default. **Branch:** none (system change plus
  gitignored `archive/`).
- **Context:** the scheduled task runs an online, publishing `db_compile update` on
  this checkout every Sunday 04:00. Next run: 2026-11-01 04:00. The drifted files
  must be preserved, because F3 needs them as evidence of GW's October changes.

**Tasks**

1. Commit this plan file on the release branch (docs only) so the tree is clean.
2. Disable the task (PowerShell):
   ```powershell
   Disable-ScheduledTask -TaskName 'wh40k-oracle-update'
   (Get-ScheduledTask -TaskName 'wh40k-oracle-update').State   # Disabled
   ```
3. Copy the drifted state, deleting nothing:
   ```bash
   A=archive/drift-20261101; mkdir -p $A/db $A/blacklibrary $A/mfm
   cp -p db/wh40k.sqlite $A/db/
   cp -p db_sources/blacklibrary/units.json $A/blacklibrary/
   cp -p db_sources/mfm/mfm_points.json $A/mfm/
   cp -p db_update.log $A/
   (cd $A && find . -type f ! -name MANIFEST.sha256 -exec sha256sum {} + | sort -k2 > MANIFEST.sha256)
   ```
4. Write `$A/RECEIPT.md` with the date, the task state, the manifest, and a link to
   this plan.

**Verify:** the task is `Disabled`; `MANIFEST.sha256` lists DB `8f7b46cd…` (Nov 1 state; see Data facts);
`git status --short` is empty.

**Exit:** the task is disabled and the drifted state is archived with a manifest.

**Rollback:** `Enable-ScheduledTask -TaskName 'wh40k-oracle-update'`.

## R1 — Restore the frozen data baseline (Decision A)

- **Depends on:** R0. **Parallel with:** R2. **Model:** default. **Branch:** none
  (gitignored data).
- **Context:** the pending branches pin the frozen hashes (see the Data facts table):
  context-points (2 test files), the Chinese-name fixture, and the native-regression
  evidence. Docker is down, so nothing should hold the DB open; check anyway. The
  FAISS index already matches the frozen era, so leave it alone.

**Tasks**

1. Confirm nothing holds `db/wh40k.sqlite` open: no uvicorn, Streamlit or containers.
2. Verify the restore sources' hashes, then copy them back:
   ```bash
   F=db_sources/chinese-name-recovery-owned/20261005/frozen
   M=db_sources/release-check-20260930/host/source-freshness-20261004/automatic-update-preserved/mfm_points.json
   sha256sum $F/db/wh40k.sqlite $F/db_sources/blacklibrary/units.json $M   # must equal the Data facts table
   cp -p $F/db/wh40k.sqlite db/wh40k.sqlite
   cp -p $F/db_sources/blacklibrary/units.json db_sources/blacklibrary/units.json
   cp -p $M db_sources/mfm/mfm_points.json
   mkdir -p archive/drift-20261101/mfm/snapshots
   mv db_sources/mfm/snapshots/fetch-xnquh5wv db_sources/mfm/snapshots/fetch-tkgj_vyr archive/drift-20261101/mfm/snapshots/
   ```
3. Confirm `details.json` and `weapon_names_history.json` already equal their pinned
   hashes. Record `aliases_history.json`'s hash (unchanged since 2026-09-25).
4. Save before/after hashes to `db_sources/release-check-20260930/host/finish/R1/RECEIPT.json`.
5. Run the full native suite on HEAD.

**Verify**

```bash
sha256sum db/wh40k.sqlite db_sources/blacklibrary/{units,details,weapon_names_history}.json db_sources/mfm/mfm_points.json
ls db_sources/mfm/snapshots/          # exactly: 2026-09-14  fetch-jtgkljt3
```

**Exit:**
- All five hashes equal the frozen values.
- The full-suite failures are a subset of the Oct 5 set of 14 (listed in
  `db_sources/release-check-20260930/host/native-intermediate-fff4-20261005/accepted.log`)
  plus the three R2 targets.
- `test_web_api_round3_audit_fixes.py::test_points_badge_is_not_universally_empty_on_the_real_db`
  passes again (1010 current units).

**Rollback:** copy the files back from `archive/drift-20261101/` and move the two
snapshot folders back.

## R2 — Fix the CI fixture and the English-name lookup regression

- **Depends on:** R0; use R1's data for the real-data checks. **Parallel with:** R1.
- **Model:** strongest. **Branch:** `codex/review-answer-provenance`, one commit.

**Context: CI failure.** PR #75's Python job fails
`tests/test_historical_card_points.py::test_agent_datasheet_adapter_keeps_history_without_current_citation`
with `sqlite3.OperationalError: no such column: kind`:
- the fixture at line 38 creates a stand-in `official_mfm_points (faction_slug TEXT)`;
- since the runtime-pricing merge, `get_datasheet` reaches `web_api/official_points.py:98`
  (`exact_unit`), which reads `kind`.

**Context: regression.**
- `agent/tools.py:145 _source_price_result` returns early on any ambiguous price
  (line 177).
- Both callers inherit it: `get_entity` (line 275) and `get_datasheet` (line 710).
- Units reprinted on several MFM chapter pages (space-marines, black-templars,
  blood-angels, dark-angels, deathwatch, space-wolves) therefore can't be looked up by
  English name. That is 63 current SM units, e.g. Intercessor Squad, Captain,
  Apothecary, Drop Pod.
- Every candidate it offers is price-only, so no English-name path reaches the
  datasheet.
- It was introduced by the runtime-pricing merge (`aeba60290`/`da2f536b5` →
  `41dc49895`). Chinese names and IDs still work.
- Merging context-points does **not** fix it; verified with a trial merge on Oct 29.
- `tests/test_audit_leftovers_r1.py` (two tests) already fails on it with real data.

**Tasks**

1. **Fixture.** In `tests/test_historical_card_points.py:38`, replace the stand-in with
   the real empty ledger:
   `from db_compile.mfm_source import write_ledger` then
   `write_ledger(conn, {"fetched_at": "2026-09-14T12:00:00Z", "pages": {}})`.
   Check `tests/test_db_compile_dup_units.py:73` (`official_mfm_points (cost INTEGER)`)
   for the same latent problem; fix it the same way if that test can reach
   `exact_unit`.
2. **Regression fix**, in `_source_price_result`, for plain names only (reserved
   `@mfm:` and `@literal:` selectors keep today's behaviour):
   - when the price is `ambiguous`, resolve the name;
   - if the resolver returns `confidence == "exact"` with a canonical ID, keep the
     candidates that pass `_canonical_identity_matches(db_path, canonical_id, candidate)`;
   - if exactly one remains, `return None`, so the canonical body path continues. That
     is the same rule the function already applies to unambiguous prices;
   - otherwise return the ambiguous result unchanged.
3. **Tests**, in a new file `tests/test_source_price_ambiguity.py` (R3 also edits
   `tests/test_agent_tools.py`):
   - synthetic DB, one generic SM unit priced on two pages → `get_datasheet` returns
     the body and `get_entity` is exact;
   - the same name in two canonical factions → still ambiguous, with both candidates;
   - an `@mfm:black-templars:…` selector → still price-only evidence;
   - real-data anchors (`needs_db`): Intercessor Squad, Captain and Drop Pod resolve;
     Helbrute is ambiguous; `罗伯特·基里曼` resolves;
   - mutation check: with the fix reverted, the new tests fail (record it in the
     commit message).
4. Run the new file plus `tests/test_historical_card_points.py`,
   `tests/test_audit_leftovers_r1.py`, `tests/test_runtime_price_adapters.py`,
   `tests/test_price_selector_roundtrip.py`, `tests/test_agent_tools.py`, and every
   test file that imports `exact_unit` or `_source_price_result` (find them with grep).
5. Commit: `fix(agent): resolve chapter-reprinted unit names to their canonical body; real ledger schema in fixture`.

**Verify:** the commands in task 4, then this anchor probe:

```bash
PYTHONUTF8=1 ./.venv/Scripts/python.exe -c "from pathlib import Path; from agent.tools import get_datasheet as g; [print(q, g(q, db_path=Path('db/wh40k.sqlite')).get('found')) for q in ['Intercessor Squad','Captain','Drop Pod','Helbrute','罗伯特·基里曼']]"
# expect: True True True False True
```

**Exit:** the three previously failing tests pass; the anchors hold; nothing else
regresses in the selection.

**Rollback:** `git revert <sha>`.

## R3 — Merge native-regressions and context-points

- **Depends on:** R1 (hash pins), R2. **Model:** default; strongest if a conflict
  needs judgement.

**Context**

- **`codex/release-native-regressions`** (`41e578add`, based on `fff4d974c`) is
  test-only. It fixes the 12 stale expectations by pinning Oct 3 prices: Apothecary 60,
  Intercessor Squad 85, Eye 10, Hero 20, Helbrute CSM 125 / DG 105 / TS 110 / WE 120.
  Report: `docs/superpowers/reports/2026-10-05-native-regression-reconciliation.md` on
  that branch.
- **`codex/release-context-points`** (`2a2e4bc16`) adds exact SM chapter routing:
  - new `db_compile/mfm_context.py`;
  - per-row chapter pricing in `db_compile/mfm.py` (`_canonical_rows`,
    `_chapter_receipt`);
  - `engines/roster/points.py` and `web_api/official_points.py`;
  - a stricter `_canonical_identity_matches`.
  It has a host approval. On Oct 29 it merged into `6b8e6a8f8` with no conflicts. Its
  tests pin DB `afb9b99d`, so they need R1.

**Tasks**

1. `git merge --no-ff codex/release-native-regressions -m "Merge reviewed native test reconciliation (12 stale expectations)"`
2. `git merge --no-ff codex/release-context-points -m "Merge reviewed chapter price context (exact SM chapter routing)"`
3. Add the chapter-unit case to `tests/test_source_price_ambiguity.py`. A
   BLACK TEMPLARS-keyword unit priced on both SM and BT pages resolves to its body,
   because only the BT candidate passes `canonical_price_slug`. This case needs
   context-points' stricter identity, which is why it wasn't added in R2.
4. Re-run R2's anchor probe on the merged tree.
5. Run context-points' tests (`tests/test_mfm_chapter_context.py`,
   `tests/test_chapter_price_consumers.py`, `tests/test_db_compile_mfm.py`,
   `tests/test_roster_faction_validation.py`, `tests/test_source_only_price_identity.py`).
   Then run the native-regressions selection (314 nodes in its report):
   `tests/test_source_archive.py tests/test_roster_validate.py tests/test_web_api_roster.py tests/test_agent_tools.py tests/test_db_compile_zh_coverage.py tests/test_web_api_stage3.py tests/test_mfm_rebuild_history.py tests/test_blacklibrary_rebuild_bindings.py`.
   Then R2's tests, then the full native suite.

**Exit:** the full-suite failures are exactly
`test_web_api_ability_keywords.py::test_whole_library_spans_lose_no_text_and_have_no_hollow_keywords`
(3317 vs 3332) and `test_zh_weapons.py::test_current_units_fully_localized`. R4 and R5
own both.

**Rollback:** `git revert -m 1 <merge-sha>` for either merge.

## R4 — Chinese-name recovery (Decision C) and the ability-count expectation

- **Depends on:** R3. **Model:** default to integrate; strongest reviews the guard
  change.

**Context**

- Worktree `release-final-integration/RAG`, branch
  `codex/release-chinese-name-recovery` at `41dc49895`, which is already in the release
  branch. Five files are uncommitted:
  - `db_compile/blacklibrary.py` (`populate_zh_details`, near line 263);
  - `tests/test_zh_weapons.py`;
  - new `tests/test_blacklibrary_detail_names.py`;
  - new `tests/fixtures/chinese_name_recovery.json`;
  - new `docs/superpowers/reports/2026-10-05-chinese-name-recovery-acceptance.md`.
- The worker reports 193/193 passing.
- With the change, 9 names are restored from already-accepted details:
  - 7 Ork: Burna Boyz, Lootas, Kustom Boosta-blasta, Shokkjump Dragsta, Boomdakka
    Snazzwagon, Megatrakk Scrapjet, Rukkatrukk Squigbuggy;
  - 2 SM: Eradicator Squad, Death Company Marines with Bolt Rifles.
  - Only Rukkatrukk is current.
- Captain on Bike's Hand flamer and Twin boltgun (`000002702_w4`, `_w9`) stay
  registered English fallbacks.
- The rewritten `test_current_units_fully_localized` checks a normal-stage projection
  of a **copy**, so on its own it no longer catches a stale active DB. R5 adds the
  active-DB check.

**Tasks**

1. Get Decision C.
2. **If approved:** in the worktree, commit the five files with a descriptive message,
   then in the main checkout run
   `git merge --no-ff codex/release-chinese-name-recovery`.
3. **If declined or unanswered:** commit only the tests, fixture and report, with
   `db_compile/blacklibrary.py` unchanged:
   - add `000001542` as a reviewed English unit-name fallback in the fixture;
   - make `_assert_current_name_coverage` accept exactly the registered unit
     fallbacks;
   - fix the report's wording.
4. Change the expected count at `tests/test_web_api_ability_keywords.py:167` from
   3332 to 3330. Add a comment that the two abilities were removed because Grey
   Knights source 2863 no longer projects to AdM Servitors `000000847` (reviewed
   wrong-faction denial). This test reads the active DB, so it passes only after R5.
5. Run the worker's selection on the merged tree (193 cases):
   `tests/test_blacklibrary_detail_names.py tests/test_blacklibrary_document_identity.py tests/test_blacklibrary_identity.py tests/test_blacklibrary_rebuild_bindings.py tests/test_blacklibrary_weapon_history.py tests/test_db_compile_blacklibrary.py tests/test_zh_weapons.py`.

**Exit:** merged; the selection is green except the tests that read the active DB.

**Rollback:** revert the merge or commit.

## R5 — Publish the reviewed Chinese projection and regenerate the wiki

- **Depends on:** R4. **Model:** default.
- **Context:** the active DB is the restored `afb9b99d`. Running the normal offline
  language stages (`stage_zh_details`, then `stage_zh_weapons`) on a copy gives:
  - 1,144 detail rows (from 1,139) and 3,330 Chinese ability items;
  - 14 restored names: the 5 reviewed bindings `000003836`, `000000562`, `000000121`,
    `000000397`, `000003916` plus R4's 9, or only the 5 if C was declined;
  - the wrong-faction AdM Servitor detail (`000000847`) removed.
  Do **not** use `db_compile update` or `db_compile build`.

**Tasks**

1. Set up:
   ```bash
   EV=db_sources/release-check-20260930/host/finish/R5; mkdir -p $EV
   cp -p db/wh40k.sqlite $EV/pre-publish.sqlite
   cp -p db/wh40k.sqlite $EV/candidate.sqlite
   cp -p db_sources/blacklibrary/units.json db_sources/blacklibrary/details.json $EV/
   sha256sum $EV/* > $EV/before.sha256
   ```
2. Project onto the candidate:
   ```bash
   PYTHONUTF8=1 ./.venv/Scripts/python.exe - "$EV" <<'EOF'
   import sys; from pathlib import Path
   from db_compile.update import UpdateConfig, stage_zh_details, stage_zh_weapons
   ev = Path(sys.argv[1])
   cfg = UpdateConfig(db=ev/"candidate.sqlite", offline=True,
                      blacklibrary_cache=ev/"units.json", blacklibrary_details=ev/"details.json")
   assert stage_zh_details(cfg).ok and stage_zh_weapons(cfg).ok
   EOF
   ```
3. Compare the candidate with the pre-publish copy:
   ```bash
   PYTHONUTF8=1 ./.venv/Scripts/python.exe - $EV/pre-publish.sqlite $EV/candidate.sqlite <<'EOF'
   import sqlite3, sys
   A, B = (sqlite3.connect(f"file:{p}?mode=ro", uri=True) for p in sys.argv[1:3])
   T = lambda c: {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
   ok = {"unit_zh_detail", "blacklibrary_detail_identity", "zh_keyword_glossary", "units", "weapons"}
   for t in sorted(T(A) | T(B)):
       ra = sorted(map(repr, A.execute(f"SELECT * FROM [{t}]"))) if t in T(A) else None
       rb = sorted(map(repr, B.execute(f"SELECT * FROM [{t}]"))) if t in T(B) else None
       if ra != rb: print("EXPECTED" if t in ok else "UNEXPECTED", t, len(ra or []), len(rb or []))
   EOF
   ```
   - Any `UNEXPECTED` line stops the step.
   - `unit_zh_detail` must have 1,144 rows.
   - `zh_keyword_glossary` may differ in row order only.
   - The copied caches must be unchanged (compare with `$EV/before.sha256`).

   Then check `units` and `weapons` column by column:
   ```bash
   PYTHONUTF8=1 ./.venv/Scripts/python.exe - $EV/pre-publish.sqlite $EV/candidate.sqlite <<'EOF'
   import sqlite3, sys
   A, B = (sqlite3.connect(f"file:{p}?mode=ro", uri=True) for p in sys.argv[1:3])
   BIND = {"000003836", "000000562", "000000121", "000000397", "000003916"}
   RECOVERED = {"000000019", "000000044", "000001538", "000001539", "000001540",
                "000001541", "000001542", "000000103", "000002285"}   # drop if Decision C declined
   ALLOWED = {"units": BIND | RECOVERED, "weapons": BIND | {"000000847"}}
   def load(c, t):
       cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})")]
       return cols, {r[cols.index("id")]: dict(zip(cols, r)) for r in c.execute(f"SELECT * FROM {t}")}
   bad = 0
   for t, owner in (("units", "id"), ("weapons", "unit_id")):
       ca, ra = load(A, t); _, rb = load(B, t)
       assert ra.keys() == rb.keys(), f"{t}: row set changed"
       for k in ra:
           diff = sorted(c for c in ca if ra[k][c] != rb[k][c])
           if diff and (diff != ["name_zh"] or rb[k][owner] not in ALLOWED[t]):
               bad += 1; print("UNEXPECTED", t, k, rb[k][owner], diff)
   print("unexpected column changes:", bad)   # must be 0
   EOF
   ```
4. Publish: confirm nothing holds the DB, `cp -p $EV/candidate.sqlite db/wh40k.sqlite`,
   and record the new hash as the **release data baseline** in
   `db_sources/release-check-20260930/host/finish/R5/RECEIPT.json`.
5. Add an active-DB guard to `tests/test_zh_weapons.py`: a `needs_db` test that runs
   `_assert_current_name_coverage` on `db/wh40k.sqlite` itself. Then run
   `tests/test_zh_weapons.py`, `tests/test_web_api_ability_keywords.py`,
   `tests/test_db_compile_zh_coverage.py` and `tests/test_blacklibrary_detail_names.py`.
6. Regenerate the wiki with the documented commands only:
   ```bash
   PYTHONUTF8=1 ./.venv/Scripts/python.exe -m wiki_engine.from_db
   PYTHONUTF8=1 ./.venv/Scripts/python.exe -m wiki_engine crosslinks
   PYTHONUTF8=1 ./.venv/Scripts/python.exe -m wiki_engine build
   PYTHONUTF8=1 ./.venv/Scripts/python.exe -m wiki_engine keywords
   PYTHONUTF8=1 ./.venv/Scripts/python.exe -m wiki_engine lint      # 0 errors (1 known warning)
   git status --short wiki/ | head -50
   ```
   Changed pages must be limited to the affected units' pages (ORK, SM, NEC, GK, AE,
   AdM) plus indexes. Anything else stops the step.
7. Commit the regenerated wiki and the guard test.

**Exit:** the receipt holds the new baseline hash; the counts match; the tests pass;
lint has 0 errors; the wiki diff is limited to the expected pages. The FAISS index is
deliberately not rebuilt; R9's release notes state this, and F3 refreshes it.

**Rollback:** `cp -p $EV/pre-publish.sqlite db/wh40k.sqlite`, then revert the wiki
commit.

## R6 — Full verification, push, CI green

- **Depends on:** R5. **Model:** default.

**Tasks**

1. Run the full native suite. It must show **0 failed / 0 errors**, with no new skips
   (the Oct 5 actual-asset run had 0 skips).
2. Wiki lint: 0 errors.
3. Check the native environment: `./.venv/Scripts/python.exe -m pip check`. Start the
   API natively on a spare port and check `/healthz`:
   `./.venv/Scripts/python.exe -m uvicorn web_api.main:app --port 8001`, then
   `curl -s http://127.0.0.1:8001/healthz`. Stop it afterwards.
4. Frontend, in **PowerShell** from `web/` (npm may need the proxy):
   ```powershell
   npm ci; npm run test:unit; npx tsc --noEmit; npm run lint; npm run build; npm audit --omit=dev
   ```
   Expect 22 unit tests to pass and the build to succeed. Record the audit output.
5. Scan the outgoing diff for secrets:
   `git diff main...HEAD | grep -nE "sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|SESSDATA"`.
   Only the two known synthetic values may appear.
6. Push and watch CI (proxy set):
   ```bash
   git push origin codex/review-answer-provenance && gh pr checks 75 --watch
   ```

**Exit:** native, lint and frontend are green, and both CI jobs pass on the pushed
HEAD. Save the evidence in `finish/R6/`.

## R7 — Docker images, browser suite, live chat checks

- **Depends on:** R6. **Parallel with:** R8. **Model:** default; strongest judges the
  live answers.

**Context**

- `docker-compose.yml` runs:
  - `api` as `wh40k-oracle-api:local` on `127.0.0.1:8000`;
  - `web` as `wh40k-oracle-web:local` on `127.0.0.1:3000`;
  - both with `restart: unless-stopped`; assets are mounted read-only.
- Previous images: API `f1224f12…`, web `5156e1f5…` (Sept 30).
- Docker Desktop was not running on Oct 29, after a host reboot.
- Known snags:
  - a stale inference-socket error (Sept 18 workaround: preserve and replace the socket
    folders);
  - a broken WSL install (check `C:\Program Files\WSL\wsl.exe`);
  - build-time proxies must point at `host.docker.internal:7897`, not `127.0.0.1`.

**Tasks**

1. Start Docker Desktop (`docker desktop start`, or have the user start it) and check
   `docker info`.
2. Record `docker images` IDs for rollback.
3. `docker compose build && docker compose up -d`, then wait until
   `curl -s http://127.0.0.1:8000/healthz` reports ready with warmup complete.
4. Check that the container source matches the host for the runtime files changed
   since September (at least `agent/tools.py`, `agent/loop.py`,
   `web_api/official_points.py`, `web_api/formatter.py`, `db_compile/mfm.py`,
   `db_compile/mfm_context.py`, `engines/roster/points.py`). Use
   `docker compose exec api sha256sum /app/<file>` against the host `sha256sum`. The
   mounted DB hash must equal R5's baseline.
5. Run the browser suite (PowerShell, `web/`): `npx playwright test` against the
   deployed services. It should pass 12/12; record which tests are fixture-based or
   intercepted.
6. Manual checks, with screenshots in `finish/R7/`:
   - roster text import: preview and apply, with valid and unresolved lines;
   - simulator with defender retaliation enabled;
   - a new SSE chat answer, then Markdown download and clipboard copy;
   - mobile and desktop layouts: no overflow, readable.
7. Live chat checks in fresh sessions:
   - ordinary Calgar (source-only/historical) vs Armour of Antilochus identity;
   - Guilliman: battle-round frequency, composition, citations, and the Oct 3 points
     (415);
   - Agents Priest vs Sisters Priest;
   - Helbrute cross-faction ambiguity;
   - **English-name lookups for Intercessor Squad and Captain** (R2's regression);
   - a PDF-fallback path;
   - same-session recall and cross-session isolation;
   - 404, 422, 429, 503, network failure and interrupted SSE recovery. Never present
     injected failures as natural ones.

**Exit:** all checks pass, or each failure has evidence and a fix step inserted (see
the mutation protocol).

**Rollback:** `docker compose down`, re-tag the recorded previous images,
`docker compose up -d`.

## R8 — 115-question benchmark

- **Depends on:** R6 (native env; Docker not needed). **Parallel with:** R7.
- **Model:** default to run; strongest to triage.
- **Needs:** `DEEPSEEK_API_KEY` and the user's OK, because it is a paid run.

**Context**

- Command: `scripts/qa_bench.py --path agent --out <file> [--gold <file>] --workers 6`.
- The default gold is root `qa_gold.json`, which is v3.6 (`a402aed8…`).
- The source-cited candidate is `benchmarks/v3_edition11/qa_gold_v3.7_source_cited.json`
  (`aeed2af4…`). It updates #113 (415), #118 (CSM 125 / DG 105), #14, #34 and #93 for
  the Oct 3 sources; see `benchmarks/v3_edition11/README.md`.
- The agent runs on DeepSeek Flash and the judge on deepseek-chat.
- Known volatile questions: #41, #42, #86.

**Tasks**

1. Check v3.7's review status. If it isn't approved, review its changed clauses
   against the Oct 3 sources and record the approval.
2. Run the agent path with v3.7 (primary). Run v3.6 as well only if the user wants a
   continuity comparison; it is a second paid run, and differences are expected only
   on the README-listed clauses:
   ```bash
   PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/qa_bench.py --path agent --gold benchmarks/v3_edition11/qa_gold_v3.7_source_cited.json --out benchmarks/v3_edition11/qa_agent_results_20261xxx_v37.json
   PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/qa_bench.py --path agent --out benchmarks/v3_edition11/qa_agent_results_20261xxx_v36.json
   ```
3. Triage every hard-wrong answer:
   - compare per question with the last 115/115 run;
   - for a suspected regression, re-run with the suspect change reverted (the revert
     comparison method);
   - check `meta.tool_calls` for fallback fingerprints;
   - never edit gold to get a pass.

**Exit:** the v3.7 run has 0 hard-wrong, or each one has a root cause plus a fix step
or an accepted, documented limit. Commit the result files.

## R9 — Release

- **Depends on:** R7, R8. **Model:** default. **Needs:** the user's go-ahead to merge.

**Tasks**

1. Write the release notes as the new PR #75 body. Cover:
   - what's in: provenance, roster validation, Chinese source projection,
     source-qualified runtime pricing, chapter pricing, security and API reliability
     work, and the fixes from R2;
   - the data baseline: Oct 3 frozen inputs plus R5's projection, with the new hash;
   - test, benchmark and browser numbers, with links to the evidence;
   - known limits:
     - Custodes reflects the Oct 3 data; the new codex comes in F3/F4;
     - FAISS is not refreshed;
     - the 47 unsupported historical names remain unproven;
     - 4 Black Library identities stay quarantined;
     - Docker restart durability is unverified;
     - there is no full-Codex parity claim.
2. `gh pr edit 75 --title "<release title>" --body-file <notes.md>`, then `gh pr ready 75`.
3. With the user's go-ahead, merge per Decision D:
   `gh pr merge 75 --merge --subject "<curated>" --body "<curated summary>"`.
   For squash, use `--squash`; F1, F2 and F5 then rebase with `--onto`.
4. After merging:
   - `git checkout main && git pull`;
   - `git diff codex/review-answer-provenance main --stat` must be empty;
   - `gh run list --branch main -L 1` must be green.
5. Handoff:
   - **CLAUDE.md:** replace the top section with a short current status and a link to
     this plan (F8 does the full trim).
   - **Devlog:** update `D:/Project/devlog/wh40k-oracle/` (`CHECKPOINT.md`,
     `commits/`) and push it together with the main repo.
   - **error-notes (`C:/Users/Administrator/error-notes/rag/`):** one file each for
     the CI fixture regression, the English-name lookup regression and the
     weekly-task baseline drift. Fill every required field, update the README index,
     then commit and push once.
   - **learn-notes:** `decisions/` gets merge style and restore-then-update; `deadends/`
     gets "focused selections as acceptance".
   - **Memory:** update the plan pointer.

**Exit:** PR #75 is merged, `main` is green, and the notes are pushed.

---

# Phase 2 — Follow-ups (separate branches and PRs off `main`)

## F1 — Finish the authority rebuild

- **Depends on:** R9. **Model:** strongest.
- **Location:** worktree `release-native-build-recovery/RAG`, branch
  `codex/release-authority-rebuild`.

**Context**

- **Committed** (3 commits): body witnesses and retained metadata freeze (83 tests).
- **Uncommitted, untested and unwired** (about 570 lines):
  - `db_compile/authority_rebuild.py`, the outer private build → restore → verify →
    adopt → `os.replace` boundary;
  - in `db_compile/retained_metadata.py`: `capture_localized_witnesses`,
    `planned_source_rows`, `verify_source_rows`, `restore_retained_metadata`;
  - `UpdateConfig.source_reconcile_bootstrap_manifest` in `db_compile/update.py`.
- The worker's remaining list is at the end of
  `docs/superpowers/reports/2026-10-05-atomic-authority-rebuild-acceptance.md` on that
  branch.

**Tasks**

1. Preserve the work first. Compare the uncommitted files with the recovery copies in
   `stop-20261005/`, then commit them as-is (`wip: preserve Oct 5 authority-rebuild edits`).
2. Bring the branch up to date:
   - Decision D = merge: `git merge main`;
   - squash: `git rebase --onto main $(git merge-base HEAD codex/review-answer-provenance)`.
3. Fix the Oct 29 review findings:
   - `_verify_final` (`authority_rebuild.py:216`) must reuse `mfm._canonical_rows` and
     fail on `db_context_diffs` and `context_unmatched`; today it uses the old name
     matcher and checks only diffs, missing, extra and unparsed;
   - `capture_localized_witnesses` (`retained_metadata.py:484`) must validate bindings
     once, including when zero records are declared, and stop re-hashing five files
     per record;
   - `_RECOVERY_DDL` (`retained_metadata.py:528`) should import the five schemas from
     `source_reconcile.py` and `source_coverage.py` instead of copying them;
   - publication (`authority_rebuild.py:341`) should use a bounded Windows replace
     retry: extract the helper from `scripts/fetch_blacklibrary_snapshot.py` into a
     shared module and reuse it in both places.
4. Finish the remaining contract:
   - ledger, source, capture, current-marker, historical-receipt and localization
     witnesses;
   - caller-owned transactional source/coverage recovery and declaration deltas;
   - hash-pinned old390 bootstrap and the ordered-envelope integration;
   - a BUILD-only CLI route, e.g. `python -m db_compile build --authority-plan <plan.json>`.
5. Write tests for every new function, plus copied actual-asset acceptance:
   - fresh CSV A → Sept 14 B → anchored A;
   - B, A and source-only restoration reproduce the frozen retained metadata exactly;
   - late failure, cancellation, close and replace controls leave the destination
     byte-identical.
6. Run the full native suite, get an independent review, and open a PR.

**Exit:** merged to `main` with tests and review evidence.

## F2 — Staged update and a safe weekly job

- **Depends on:** R9 for F2.1–F2.3; F1 for the rest. **Model:** strongest.
- **Location:** worktree `release-api-reliability/RAG`, branch
  `gnhf/objective-finish-the-2621e6` (`4e820136a`). It supersedes
  `codex/release-staged-updates`.
- **Context:** `python -m db_compile update --stage-only` captures, rebuilds and
  reviews private copies and never publishes (981-line `db_compile/staged_update.py`,
  173 tests). The open review requested changes: the staged trial loses
  `aliases_history.json`, which direct restoration reads (`db_compile/update.py:382`).
  That is 925 alias pairs.

**Tasks**

1. Bring the branch up to date with `main` (see F1 task 2).
2. Add a `SnapshotInput` for `db_sources/blacklibrary/aliases_history.json` beside the
   `weapon_names_history.json` entry (`staged_update.py:621`). Add a regression test:
   staged restoration equals direct restoration, including all 43 removed spellings.
3. Fix the latent issue in context-points (review finding 7): `mfm_sync.apply_snapshot`
   must fail convergence when `context_unmatched` contains entries outside a reviewed
   allowlist. Measure the current set first: on the frozen DB, 0 current SM units are
   unresolved and 1 non-current one is.
4. After F1: extend the input closure to `mfm_history`, `source_coverage`,
   `authority_rebuild` and the external historical/bootstrap/bundle paths, with one
   shared private restore invocation.
5. Change `scripts/run_db_update.bat` to run `-m db_compile update --stage-only`, and
   document how to review and promote a staged result.
6. Re-enable the task with `Enable-ScheduledTask -TaskName 'wh40k-oracle-update'`.
   After the next Sunday run, verify that the active hashes are unchanged and a new
   evidence folder exists under `db_sources/staged-updates/`.

**Exit:** merged, and a scheduled run completes without touching active assets.

## F3 — Adopt current official data (re-baseline)

- **Depends on:** F2 (and so F1). **Model:** strongest.
- **Context:** `archive/drift-20261101/` (from R0/R1) and the two moved snapshots show
  GW's October changes; see Data facts. The weekly job reported 12 new, 26 revised and
  8 removed official PDFs. The live Black Library inventory grew from 1,717 to 1,886
  units.

**Tasks**

1. Triage `python -m db_compile downloads --check` (proxy). Run `--harvest` only after
   review.
2. Run a staged online capture (`update --stage-only`) and review its report:
   - price changes and ledger rows;
   - changes to the current set;
   - each of the 100 changed and 51 lost Chinese names: accept or reject;
   - alias changes: the reviewed alias set is not overwritten without approval.
3. Stop the API container first (`docker compose stop api`). Its read-only mount can
   still block a Windows replace. Publish through the F1 path, record the new
   baseline hashes, then `docker compose start api`.
4. Re-pin the hash-pinned tests (grep for `afb9b99da103`, `a497c85edbc0`, `20f3c54d`),
   naming the reviewed source change in each commit.
5. Rebuild the vector index if Black Library or documents changed
   (`./.venv/Scripts/python.exe ingest.py --rebuild`), and diff document identity
   against the 3,404 / 1,128 baseline.
6. Create a new benchmark expectation version only for reviewed official facts, then
   re-run R8.

**Exit:** the new baseline is recorded; the full suite, lint and benchmark are green.

## F4 — New Adeptus Custodes codex content

- **Depends on:** F3. **Parallel with:** F5. **Model:** strongest for DSL; default for
  the import.
- **Context:** 11 official units have no datasheet: Custodian Guard Sodality, Sentinel
  Guard Sodality, Gyrfalcon Jetbike Sodality, Aquilon Terminators (×2 loadouts),
  Venatari (×2), Prosecutor Squad, Vigilator Squad, Witchseeker Squad and Caladius
  Annihilator Grav-tank. Thirteen old units are retired. The new codex probably also
  brings new detachments, stratagems and enhancements.

**Tasks**

1. Check sources: the Wahapedia CSV (`python -m wiki_compile fetch-canonical`, proxy)
   for the new datasheets, and the official PDFs from F3's triage.
2. Import the new datasheets. Retire the old units by archiving, not deleting. Add the
   detachments, stratagems and enhancements; points come from MFM.
3. Write `dsl_payloads/` entries using the P7 honesty markers
   (encoded / partial / not_modeled) and its phase-gate rules.
4. Chinese names in priority order: official zh, then Black Library, then English.
5. Regenerate the wiki (`wiki_engine.from_db --faction AC`, `entities`, `crosslinks`,
   `build`, `keywords`, `lint`) and add Custodes benchmark questions in a new gold
   version.

**Exit:** `mfm --check` shows no Custodes units that exist only in the official
source; tests and lint are green.

## F5 — Official field ledgers → promotion

- **Depends on:** R9 for preparation; F3 for promotion. **Model:** strongest.

**Context**

- The shared report is `docs/superpowers/reports/2026-10-01-official-field-preflight-acceptance.md`.
- Daemons/Necrons is already integrated (`6552314b5`, `b30ad297d`).
- Sororitas/Death Guard: branch `gnhf/objective-finish-eve-d1d51d` covers 33 + 19
  decisions; the root semantic reconciliation is pending.
- Thousand Sons/Agents: branch `gnhf/objective-finish-onl-ce6398` has 7 Thousand Sons
  decisions; the remaining Thousand Sons and Imperial Agents preparation is unfinished.
- The goal is all 13 overlays.

**Tasks**

1. Reconcile Sororitas/Death Guard.
2. Finish Thousand Sons/Agents.
3. Combine all of them into the shared report.
4. Re-verify against the current official PDFs. The sources were frozen on Sept 30;
   use F3's triage.
5. Do a guarded copied rehearsal (A/B/C row-state chains, rollback and idempotency
   controls), then promote the data, DSL, Chinese and wiki changes.

**Exit:** promoted with evidence; tests and lint green.

## F6 — Long-tail data gaps and test quality (small independent PRs)

- **Depends on:** R9. **Model:** default.

Tasks:
- Find public official rules for Gunwagon, Runtherd and the 28 Ork enhancement keys.
  Keep the preview labels.
- Add Chinese names for Captain on Bike `000002702_w4` and `_w9` only with source
  evidence.
- Search for provenance for the 47 unsupported historical canonical names; otherwise
  they stay unproven.
- Periodically recheck the 4 quarantined Black Library wrong-identity responses and
  the remaining source gaps upstream (`scripts/fetch_blacklibrary_details.py`).
- Fix benchmark #41 (Ork Boyz, partial).
- In the keyword index, link "规则页 NN.NN" to the core-rules section pages.
- Review finding 8: move roster and price arithmetic tests to synthetic fixtures. Keep
  a few real-data canaries that compare against the official ledger rather than
  literal prices.

## F7 — Docker restart durability

- **Depends on:** R7. **Model:** default.
- **Context:** the containers use `restart: unless-stopped`, but after the Oct 29
  reboot Docker Desktop itself didn't start.

Tasks:
1. Enable Docker Desktop's start-on-login.
2. Document the stale-socket recovery.
3. Verify after the next **natural** reboot; don't reboot just to manufacture a pass.

## F8 — Repo hygiene and the CLAUDE.md trim

- **Depends on:** R9; F1, F2 and F5 before removing their worktrees. **Model:** default.

Tasks:
1. Delete superseded branches after confirming with `git cherry` /
   `git branch --merged main`:
   - `codex/release-coverage-unicode`;
   - `gnhf/objective-correct-th-2d20ee`;
   - `codex/release-field-daemons-necrons`;
   - `gnhf/objective-finish-eve-e81d02`;
   - `codex/release-official-field-audit`;
   - every branch merged into `main`.
2. Remove a worktree only after its work is integrated and the ignored evidence it
   owns has been copied (`git worktree remove <path>`).
3. Inspect `stash@{0}` (July PR25 debug residue); drop it or save it as a patch in
   `archive/`.
4. Trim CLAUDE.md: replace the 25 dated checkpoint sections (59 KB, loaded into every
   session) with a current status of at most one page plus links. Move the history
   verbatim to `docs/superpowers/history/claude-md-checkpoints.md`.
5. Change the GNHF convention so commit subjects describe the change. 101 of PR #75's
   139 commits read "knowledge handoff… no additional edits were needed", including
   ones that change code. Record this as a learn-notes decision.
6. After F3, archive `archive/drift-20261101/` per the archive conventions.

---

## Plan mutation protocol

- **Split or insert:** add a step with a suffix (e.g. `R2a`, `F3b`), give it the same
  fields as the others, and update the Status table and graph.
- **Skip or abandon:** set the status to `skipped` or `abandoned` with a reason.
  Never delete a step.
- **Reorder:** allowed only if no dependency edge is broken; update the table.
- **Log every change** under the log below as `date — change — reason — who`.

### Log

- 2026-10-29 — plan created from the Oct 29 review — Claude (Opus 5.5).
- 2026-11-03 — R0 archive renamed `drift-20261025` → `drift-20261101` and Data facts
  extended — the Nov 1 job ran before R0 and overwrote the Oct 25 DB; R1 also moves
  `fetch-6t362dci` (already copied into the archive) — Claude (Opus 5.5).

## Review log

The adversarial review was done inline, without a sub-agent, against completeness,
dependency order, cold-start fitness, verification, rollback and the anti-patterns
above. Findings and fixes:

1. **Coverage.** Every Oct 29 review item maps to a step:
   - review findings 1–2 → R2; 3 → F2; 4–5 → F1; 6 → R4; 7 → F2; 8 → F6; 9 → R9/F8;
   - drift → R0, R1, F3; Custodes → F3, F4;
   - branches → R3, R4, F1, F2, F5, F8;
   - final gates → R6–R9;
   - post-release list → F1–F8.
2. **Dependency.** R2's chapter-unit test needs context-points' stricter identity. It
   was moved to R3.
3. **Dependency.** R4's ability-count expectation reads the active DB, so it passes
   only after R5. The exit criteria now say so.
4. **Cold start.** R5 originally said "regenerate wiki" without the command. It now
   names `python -m wiki_engine.from_db` (there is no `from-db` subcommand).
5. **Safety.** Restoring the frozen DB would hide GW's October data. R0 now archives
   the drifted DB, caches and snapshots, and F3 uses them.
6. **Decision.** The merge-style default changed from squash to a merge commit, because
   evidence SHAs and three follow-up branches depend on PR #75's history. Both paths
   are written out.
7. **Rollback.** Every step that changes data takes a backup before the change. The
   verification-only steps, R6 and R8, need no rollback.
8. **Open risk.** R7 depends on Docker Desktop recovering on this host. If it doesn't,
   insert R7a (diagnose WSL/socket) rather than skipping R7.
9. **Cold start.** R3 and R4 pointed at "the worker's selection" without naming files.
   Both now list the exact test files, taken from the worker XML: 314 and 193 cases.
10. **Verification.** R5 described the per-column check on `units`/`weapons` without
    giving a query. It now includes a script with the explicit allowed-ID sets.
11. **Safety.** F3 publishes while Docker may be running. On Windows the bind mount
    can block the replace (compare the still-unexplained PermissionError), so F3 now
    stops the API container first.
12. **Cost.** The v3.6 benchmark run in R8 is now optional, since it is a second paid
    run.
