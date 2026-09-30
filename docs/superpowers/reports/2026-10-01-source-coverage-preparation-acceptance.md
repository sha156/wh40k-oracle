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

## Iteration 2 — separate strict coverage contract

This iteration implements outcome 1's isolated validation/application/resolution boundary in `db_compile/source_coverage.py`. No real coverage declarations are published, and no application consumer is wired to the registry yet. The preceding historical-price fix is preserved. The initial working tree was clean at `ebc011b45`; the original frozen objective base remains `1cdb85f7605a5f36b833e1423f7136b4e2c449bf`. No manual commit or other Git mutation was made.

### Contract and exact identity

The manifest has exactly `schema_version: 1` and a nonempty `records` list. Every record contains exactly `identity`, `reviewed_on`, `body` and `points`:

| Object | Required fields and meaning |
| --- | --- |
| identity | `unit_id` (canonical ID or null), full `name_en`, canonical `faction_id`, exact price-source `faction_slug`, ordered `faction_keywords` |
| body | `status`, `scope`, `effective_date`, `sources`, `retained_snapshot` |
| points | Separate `status`, nullable `effective_date`, `sources`; numerical prices and all tiers remain in the existing ledger/projection |
| source | HTTPS `url`, lowercase 64-character `sha256`, `kind`, one-based `page` for PDF/preview images or null for web, nullable `source_date`, timezone-qualified `captured_at` |

Sources cite the artifact and its explicit source date; capture timestamps remain capture timestamps. They do not establish an effective/legal date. An unknown effective date is null, including current published MFM prices whose legal-start date is unproven. The validator checks provenance structure, not remote bytes or the truth of a manually reviewed declaration. Later source review and exact source-to-field patch guards remain essential.

| Body status | Allowed scope and qualification |
| --- | --- |
| current_full_verified | Exactly `full_body`, known effective date and full source evidence; preview-image evidence is rejected |
| fields_only | A nonempty subset of models/weapons/abilities/equipment/composition/keywords; full-body effective date remains null |
| historical_snapshot | Exactly `full_body`, dated historical evidence; no automatic current conversion |
| newer_full_unavailable | Empty current-body scope and null current-body effective date; may separately retain a dated full historical snapshot |
| source_only_price | Empty body scope, null canonical ID and full-body effective date; exact published-price evidence is also the evidence for its body limitation |

Points status is independently `current_published`, `historical` or `unavailable`. A current canonical declaration requires explicit `mfm.current=true` plus an exact name/faction ledger row and matching URL/hash/capture provenance. Historical canonical points require explicit `mfm.current=false`. A current-price declaration cannot certify a new full body; the paired fixture resolves `current_published` alongside `newer_full_unavailable` and a separately dated retained body.

Canonical application/resolution checks the exact ID, full English variant, canonical faction and the complete ordered `faction_keywords` array against the staged DB. A chapter-specific source slug must match its chapter keyword; the generic Space Marines source preserves all declared chapter identities. Eleven representative chapter controls cover the known five chapter price slugs plus Ultramarines, Salamanders, Imperial Fists, Iron Hands, Raven Guard and White Scars; validation itself has no chapter-keyword whitelist. A full or retained body declaration requires an existing stored model row. This is an existence guard, not numerical profile validation or a simulation acceptance result.

Source-only resolution requires the exact full English name plus source faction slug. It verifies the staged ledger's name, faction, URL, hash and capture timestamp and refuses an identity that already has a same-name canonical body in that faction. Case-insensitive English comparison retains all punctuation and full variant text; there is no alias, substring, fuzzy-sibling or equal-price identity fallback. The synthetic ordinary Calgar ledger retains both 180/300 tiers, distinct from the existing Armour 155 projection and ordinary historical 200 archive. These are registry/identity controls; actual `official_points.exact_unit` and agent lookup precedence still await outcome 3.

Malformed/unknown status, extra fields, invalid dates, preview-to-full claims, duplicate identities/pages, inconsistent per-document provenance, invalid URLs/hashes/pages, identity/chapter drift and stale prior declarations abort. Updates preserve previous declaration JSON in `source_coverage_history`, preserve unmentioned registry rows and require exact prior-state matching. Repeated identical declarations are idempotent. A direct transition from unavailable newer rules cannot recertify the same retained source bytes as a full current body, and verified effective dates cannot decrease across that transition. There is no automatic history fallback. These are explicit delta guards, not an audit of arbitrary externally edited historical registry tables.

### Later promotion interface

The exact new internal APIs are:

```python
validated = validate_manifest({"schema_version": 1, "records": reviewed_records})
prior = resolve_coverage(conn, unit_id="exact canonical ID")
price_prior = resolve_coverage(
    conn, name_en="Exact Full Source Variant", faction_slug="exact-source-slug"
)
apply_coverage(conn, validated, expected_records=[prior, price_prior])
```

The example's two records and their aligned prior records are illustrative, not a real promotion manifest. `resolve_coverage` returns the explicit declaration or None when the registry/identity is absent. It validates stored JSON and its current staged identity/provenance on each hit. It does not compute a price, load a body, infer coverage from `legend` or MFM membership, or add public tool arguments.

`apply_coverage` requires the caller's already active SQLite transaction. Collect prior declarations before changing their body/price projections; stage reviewed body/price changes on that same connection, apply coverage with exact aligned prior records (None for an absent entry), run the promotion's convergence/preservation gates, then let the caller commit. The function never opens a DB or commits. An internal savepoint undoes all registry/history changes on failure even if the outer caller catches the error; an outer promotion failure rolls back staged body/price/coverage changes together.

The existing `mfm_sync.apply_snapshot(db_path, snapshot)` opens and commits its own connection. Calling it next to coverage application does **not** make the two atomic. The later promotion must use the existing connection-aware `mfm.apply_points(..., connection=conn)` and `mfm_source.write_ledger(conn, snapshot)` seams inside its reviewed staging transaction, preserving the sync's current-flag, enhancement and convergence guards, or provide a reviewed caller-connection adapter. This iteration does not alter that worker's pipeline. Real registry publication/replay and rebuild preservation are later promotion responsibilities; no restore hook is added now.

Coverage continues to be rejected by `source_reconcile.apply_patches`; no coverage fields have been inserted into that restoration manifest. Its exact patch-chain/metadata/abort behavior remains unchanged. Body/price consumer propagation will reuse this resolver in subsequent preparation slices, without translating absent coverage into a verified status.

### Validation and evidence

All execution used the unchanged `D:/Project/py/RAG/.venv/Scripts/python.exe` (Python 3.9.1). No installs/upgrades, network/model calls or services were needed.

| Check | Result |
| --- | --- |
| Identical 57-test contract matrix against exact original base | 56 failed / 1 passed / 0 skipped |
| Final candidate matrix | 57 passed / 0 skipped |
| Coverage, reconciliation, MFM sync, source archive, agent archive, historical-card and datasheet suites | 171 passed / 0 skipped / five existing SWIG warnings, 10.26 s |
| Syntax compilation of new module/tests | Passed |
| Actual module/test review, whitespace checks and `git diff --check` | Passed |

The 56 base failures explicitly mean `db_compile.source_coverage` is absent at the frozen base; they do not claim that base silently accepted malformed declarations or reproduced 56 runtime defects. The one passing control is the unchanged patch-manifest rejection. The original modules used by base fixtures/control were frozen as exact Git bytes. Direct saved probes corroborate the absent API versus candidate application/resolution, preserve every original fixture row/table, and show identical patch-contract rejection.

Candidate tests also demonstrate caller-owned rollback including price/body staging; rollback of partial registry writes under an injected SQLite trigger; same-record idempotence and declaration history; rejection of retained old bytes as newer full rules; exact chapters/variants; missing-body denial; stored JSON/canonical/price provenance drift; absent-registry read-only behavior and input immutability. All fixtures are synthetic. The 171-test selection has no local-real-asset skips; it makes no claim about a full native or real-source suite. The final paired matrix was rerun after the last error-message clarification; that clarification changes no behavior in the wider suite.

Ignored evidence root: `C:/Users/Administrator/.codex/worktrees/release-web-security/RAG/db_sources/source-coverage-preparation/iteration-02/`. It contains exact base modules/hash manifest, `verify_pair.py`, base/candidate JUnit XML and text, focused JUnit XML/text, base/candidate direct JSON probes and disposable fixture DBs. The candidate direct probe retains the applied synthetic registry for independent inspection. No original fixture unit/model/DSL/archive/ledger row is modified by coverage staging, and the candidate probe's original-row preservation checks pass before and after commit.

### Scope, handoff and remaining work

This iteration's tracked scope is the new coverage module, its new tests and this appended report. All existing runtime adapters, public tool signatures/schemas, security/dependency/benchmark ownership, source-reconcile manifests, wiki, production PDFs/databases/indexes and live services remain untouched. No long-running background process was started; all test/probe processes finished. Independent review is still pending.

Outcomes 1 (strict contract) and 2 (historical current-price rendering boundary) now have isolated implementations. Outcomes 3–5 remain: actual qualified source-only price/tool precedence including Kaius and same-name faction ambiguity; central source-note/card/tool propagation and normal/reverse simulation plus roster body-scope gates; and historical eligibility before BM25/FAISS/rules-floor ranking with explicit historical access. The `agent/loop.py` usable-price evidence branch remains with the security owner/root. None of those remaining outcomes is claimed by these registry tests.

Project CHECKPOINT/ROADMAP and learning/error notes were checked for duplicates before recording this distinct contract decision. The new verified handoff is appended to `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`; the reusable decision is `C:/Users/Administrator/learn-notes/decisions/20261001-separate-transactional-source-coverage.md`. No new underlying runtime error was encountered, so no duplicate or placeholder error note is created. No knowledge-repository commit/push is performed under this iteration's no-manual-commit instruction.

Root still owns independent host review, supported Python 3.11/Linux/full-asset acceptance, browser, benchmark and CI checks, real source/registry publication and September 30 promotion. The stop condition remains unmet.
