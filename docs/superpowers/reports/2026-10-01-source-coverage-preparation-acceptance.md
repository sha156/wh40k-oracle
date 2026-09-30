# Source coverage preparation acceptance

## Iteration 1 — historical card prices

This isolated candidate fixes the confirmed historical-price card defect. It is an incremental preparation result, not official-data promotion or full release acceptance. The branch started clean at `1cdb85f7605a5f36b833e1423f7136b4e2c449bf` on `codex/release-source-coverage`. No manual staging, commit, push, merge or deployment was performed; GNHF owns scoped commits.

The existing read-only architecture report and its probes were used at `D:/Project/py/RAG/db_sources/release-check-20260930/host/source-coverage-paths/ee8df0bc0/`. The saved official recommendation and source metadata remain the authority for later promotion. No catalogue, PDF, Black Library or benchmark audit was repeated.

### Behavior and integration surface

Previously, `mfm.current=false` made `Datasheet.points_min=None` but retained old `points_options`. Both the badge and composition rendered the retained 155-point tier as an ordinary current price.

`db_compile.datasheet._parse_points` now returns `(None, [])` only for an explicit JSON boolean `mfm.current=false`. `lookup_datasheet` retains that record's original tiers and provenance under a separate optional `Datasheet.historical_points` field:

```json
{
  "status": "historical",
  "points_options": [{"line": "1", "desc": "1 model", "cost": 155}],
  "source": {
    "current": false,
    "fetched_at": "2026-09-14T12:00:00Z",
    "checked_at": "2026-09-30T12:00:00Z",
    "source_url": "https://example.invalid/synthetic-mfm",
    "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "tiers": [{"tier": "YOUR UNIT COSTS", "models": "1 model", "cost": 155}]
  }
}
```

This example is synthetic. The source object is retained verbatim when present, including all original tiers and metadata. Identity remains the owning datasheet's exact canonical ID/name/faction; no source-only unit or sibling identity is inserted. `historical_points` is `None` when the marker is absent or current. This field is price evidence, not a rules-body coverage registry.

The source note labels historical prices, their capture timestamp and the later MFM check separately. Missing capture dates say `capture date unavailable`; check timestamps are never relabelled as capture/effective dates. Unmatched pricing does not establish retirement, Legends status or rule-body freshness. A preview note on a non-current record no longer says `current MFM points`.

Both direct codex cards and `get_datasheet` payload cards show `—` for the current badge and omit historical price-bearing composition. Historical tiers remain visible in the qualified `source_note` / `EntityCard.src` and machine-readable evidence. An injected Chinese composition override cannot restore the old price. Current and legacy valid price tiers, language selection, exact identity, chapter keywords and loaded model profiles are preserved. Unknown pricing is not zero.

The catalogue/list/picker and roster consumers already use the canonical current-price guard. Their paired controls pass without changes: explicit legacy rows have no current badge, roster recomputation discards cached historical prices, and validation surfaces `unit_unpriced` instead of silently accepting a zero-cost unit. The simulator and roster UI consume the catalogue through the shared codex API; browser rendering was not run.

**Later promotion interface for this slice:** atomically stage the reviewed price snapshot using the existing `db_compile.mfm_sync.apply_snapshot(db_path, snapshot)` contract, then read through `lookup_datasheet(db_path, exact_unit_id)` / existing adapters. A matched identity regains `mfm.current=true`; an unmatched record retains its original provenance and receives the existing `checked_at` marker. This candidate performs no apply. The separate validated body-coverage application API required by outcome 1 has not yet been implemented and must not be substituted with `historical_points` or source-reconcile manifest fields.

### Validation and paired evidence

All tests used the existing full executable `D:/Project/py/RAG/.venv/Scripts/python.exe`, verified as Python 3.9.1. No environment upgrades or installs were made.

| Check | Result |
| --- | --- |
| Final 12-test matrix against actual frozen base modules | 7 failed / 5 passed; expected historical defect and missing disclosures reproduced |
| Identical final matrix against candidate | 12 passed / 0 skipped |
| Focused datasheet/composition/MFM/roster/card/provenance/archive suite | 168 passed / 23 skipped / 5 existing SWIG warnings, 9.61 s |
| Syntax compilation of both changed modules and new tests | Passed |
| Actual diff inspection and `git diff --check` | Passed |
| Ruff / Black / Flake8 | Not installed in the permitted interpreter; no install attempted |

The 23 skips are existing local-real-asset tests in the roster and web suites because this worktree lacks `db/wh40k.sqlite`. Exact node IDs and reasons are retained in the focused JUnit XML. These are not promotion/full-native acceptance results.

Ignored evidence root: `C:/Users/Administrator/.codex/worktrees/release-web-security/RAG/db_sources/source-coverage-preparation/iteration-01/`.

- `base/` contains exact Git bytes of the two changed modules from the starting commit.
- `verify_pair.py` loads those frozen modules in an isolated process for the base run, without replacing candidate files. Run with `--base --tests` or `--tests` for the paired test matrix, and with `--base` or no flags for the direct probes.
- `base-tests.xml/.txt`, `candidate-tests.xml/.txt`, `focused-tests.xml/.txt` retain the actual results.
- `base-probe.json` shows badge `155`, composition `1 model — 155 分`, and an unqualified structural source footer. `candidate-probe.json` shows badge `—`, empty current composition and qualified historical evidence. Both use stored synthetic DB fixtures and record identical before/after DB hashes.

One intermediate test used a nonnumeric synthetic ID with a resolver placeholder; the real adapter correctly attempted name resolution and the fixture failed. It was corrected to a numeric synthetic canonical ID and an actual copied-fixture `EntityResolver`. The final suite above supersedes that intermediate run. There was no application change to bypass the resolver.

### Scope and remaining gates

Only `db_compile/datasheet.py`, `web_api/entity_card.py`, the new regression file and this report change in the tracked candidate. No production data, source PDFs, manifests, indexes, wiki files, DSL, benchmark gold/results, dependencies, credentials, Codex/GNHF configuration or live services were modified. No long-running background process was started; all test processes completed.

Outcome 2's local historical badge/options boundary is implemented. Outcomes 1, 3, 4 and 5 remain: strict coverage validation/atomic resolution; full source-only price qualification and precedence including ordinary Calgar 180 versus historical 200 and Armour 155 and Kaius 100; dated simulation/roster/body limits; and consistent historical eligibility before BM25/FAISS/rules-floor ranking. The security owner still owns the narrow `agent/loop.py` evidence-retention integration and public tool schemas. Independent host review, supported Python 3.11/Linux/full-asset checks, browser/benchmark/CI, real source publication and production promotion remain root gates. The overall stop condition is not met.

### Knowledge handoff

Existing project CHECKPOINT/ROADMAP, learning notes and resolved error notes were searched before writing the handoff. The earlier community-composition note concerns a different override path; this defect is the retention of non-current canonical tiers as current options.

Verified records are maintained in `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`, `C:/Users/Administrator/learn-notes/decisions/20261001-current-options-exclude-historical-prices.md`, and `C:/Users/Administrator/error-notes/rag/20261001-error-19-historical-tiers-render-as-current.md` with its README index. Concurrent entries are preserved. No new commit is claimed for this candidate or handoff.
