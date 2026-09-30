# Source coverage consumer acceptance

Iteration 1 completes the central note, card and formatter digest slice. The
whole consumer objective remains open: simulation and roster coverage boundaries
are the next bounded iteration. This report does not authorize source promotion
or claim deployment, actual-asset acceptance or latest full-Codex parity.

The isolated checkout is
`C:/Users/Administrator/.codex/worktrees/release-native-build-recovery/RAG`, on
`codex/release-source-coverage-consumers`, with frozen base
`2acd1e4be7549e3f7553742cf8833f896b56b096`. Initial Git status was clean. The
completed `source-coverage-paths/ee8df0bc0/REPORT.md` architecture and actual
`source_coverage.resolve_coverage` contract were read. No catalogue, source or
Black Library audit was repeated. GNHF owns staging and commits; this iteration
performed neither. Concurrent owner regions remain unchanged.

## Material outcomes

- `db_compile/coverage_notes.py` resolves the existing strict registry and emits
  a complete source-qualified note. It includes exact English name, canonical ID
  or explicit absence, faction ID, exact source faction slug, faction keywords,
  review date, body status, exact verified scope, verified effective or retained
  date, and full URL/hash/kind/page/source-date/capture provenance. Independent
  points status, provenance and optional effective date follow separately.
  Missing effective dates remain unverified. Captures and source dates are never
  substituted for effective dates or body/list guarantees.
- Central `lookup_datasheet` appends this whole note to existing preview and
  historical-price notes. `EntityCard.src` already retains the exact resulting
  string; no card or frontend contract change is needed. Canonical formatter
  reloads use the same note. Price-only identities have no canonical body, models
  or weapons, and still yield no datasheet or card.
- Explicit declarations resolve before any legacy body query, parsing or
  missing-unit return. Invalid identity/JSON, deleted canonical identity and
  missing required model tables raise `CoverageError`. The formatter rethrows
  that error rather than substituting a stale recorded card. An ordinary missing
  unit without a declaration still returns `None`.
- Formatter digests retain each distinct whole reviewed note from all recorded
  subject lookups, including earlier successful calls before a later miss.
  Large body JSON cannot push the scope/date/price limitation out. The existing
  2,000-character budget applies to bulk evidence after mandatory qualifiers; it
  is deliberately soft if the complete qualifiers alone exceed it. Only notes
  carrying the central `Source coverage:` qualifier enter this path. Legacy
  preview/history digests without a declaration remain byte-equivalent.

No numerical computation, public tool signature/schema, modeled DSL, source
registry implementation or price-identity resolver was changed.

## Paired verification

All SQLite declarations and body/price data below are synthetic fixtures in
temporary databases, with `example.invalid` provenance. No production database,
models, downloads, paid calls or dependency installation was used. The unchanged
full-stack interpreter is:

```text
D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe
Python 3.11.9
```

| Evidence | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Initial 12-case matrix against untouched frozen base | 1 | 11 | 0 | 0 |
| Final 17-case matrix against exact frozen base modules | 3 | 14 | 0 | 0 |
| Final candidate, same 17-case matrix | 17 | 0 | 0 | 0 |
| Scoped regression, six test modules | 143 | 0 | 0 | 9 |

The final paired base run loads the exact Git blobs for the two modified existing
modules and blocks the new helper, which is absent from the base. Remaining
modules are unchanged. The loader and frozen blobs are saved as evidence; no
checkout, Git index or working source was swapped. Three paired controls pass on
both base and candidate: missing/empty registry legacy datasheet/card behavior,
preview-only legacy digest and historical-price-only legacy digest.

The 17 candidate cases cover current-full, exact fields-only, historical-full,
unavailable-newer with retained full body, unavailable-newer without retained
body, independent current price versus body limitations, preservation of preview
and historical-price notes, absent-registry payloads, source-only exact faction
notes with no card, actual canonical card reload, five invalid-declaration/body
mutations at lookup and reload, and complete multi-subject digest qualifiers
after large bodies and a later miss. Assertions check actual consumer strings,
whole dates/scopes and full provenance; body/price algorithms remain unchanged.

The regression command was:

```powershell
& '<full-stack interpreter above>' -m pytest `
  tests/test_source_coverage_consumers.py tests/test_source_coverage.py `
  tests/test_db_compile_datasheet.py tests/test_historical_card_points.py `
  tests/test_web_card_provenance.py tests/test_web_api_stage3.py `
  -q -rs --junitxml=db_sources/source-coverage-consumers/iteration-01/regression.xml
```

XML accounting confirms 152 collected cases: 143 passed and nine existing
stage3 tests skipped because `wh40k.sqlite` is absent in the isolated checkout.
The complete skipped node IDs and original reasons are in
`preservation-and-tests.json`. No new test skips or exclusions were introduced.
Actual-asset tests remain a later host gate. `git diff --check` passes. No Python
lint/format tool is installed in the fixed environment; no environment was
changed to add one.

Evidence is ignored under
`C:/Users/Administrator/.codex/worktrees/release-native-build-recovery/RAG/db_sources/source-coverage-consumers/iteration-01/`:

- `base.*`, `paired-base.*`, `final-focused.*`, `regression.*`: logs and XML.
- `run_frozen_base.py`, `frozen-base/`: reproducible final-matrix paired base.
- `protected-before.json`, `verify_preservation.py`,
  `preservation-and-tests.json`: hashes, AST preservation and exact XML counts.
- `fixture-import-error.*` and `invalid-test-path.*`: retained setup errors,
  corrected before any passing-result claim. The first used an incorrect test
  package import; the second named a nonexistent test module. Neither is counted
  as paired behavioral evidence.

## Independent review and preservation

Read-only generic and Python reviewers independently approved the final central
slice after reproducing and verifying corrections for the validation-order gap.
Both independently passed the 17-case matrix. Their approval explicitly excludes
simulation, roster, tool-loop integration, source promotion and deployment.

Ten existing protected files have identical SHA-256 digests, including the whole
`source_coverage.py`, `official_points.py`, `agent/tools.py`, `agent/loop.py`,
`web_api/main.py`, `web_api/ratelimit.py`, `web_api/simulate.py` and roster
points/validate/critique modules. Thus concurrent calc_points/name-resolver,
get_entity/get_datasheet and registry-owner regions are intact. AST checks also
confirm all existing function signatures in datasheet/formatter and every
function outside the three authorized integration functions are unchanged.

Two verified lessons are retained here to avoid duplicate cross-checkout notes:

1. Validation after body assembly is too late. A malformed legacy value or an
   early missing-row return can bypass an explicit invalid declaration and make
   an optional-card fallback display stale verified-looking evidence. Validate
   the declaration before assembly and preserve a distinct fail-closed error.
2. Whole provenance cannot always fit a fixed character budget. Preserve atomic
   per-subject qualifiers first, and budget bulk around them; applying this to
   legacy-only notes would itself change absent-registry behavior.

## Remaining authorized work and root integration seams

Iteration 2 must add strict body support decisions and notes to both simulation
sides and reverse direction, and roster validation/critique. Current prices
cannot certify a combat body, composition or equipment. Missing verified bodies
must deny simulation and remain unassessed in critique; retained historical
bodies require clear dates/status on both sides and surfaced roster limitations.
Fields-only supports only its exact verified fields. Existing algorithms,
chapter-price constraints, unknown/model-absent errors, default validity
semantics and absent-registry controls must remain intact. These boundaries have
not been changed or claimed passing in iteration 1.

Root still owns get_entity/get_datasheet source-only adapters and AgentLoop
usable-evidence integration after the security merge. The required source-only
payload should keep `datasheet=None`, no canonical unit/body/page, exact full
source name and faction slug, `points_only=True`, separate official price rows
and their provenance, and the complete `coverage_note` value in the existing
qualifier surfaces (`source_note` for digest retention, `source_scope`/`note` for
root-owned evidence seams). Do not label it a current full rules body or inherit
a sibling's models/weapons. Canonical get_datasheet already gets its reviewed
note through `Datasheet.source_note`; central card reloads use the same source.
Root must ensure a `CoverageError` is visible and never converted to current
coverage or a usable stale body by tool/loop exception handling.

The full stop condition is not met. No declarations, database, manifests, PDFs,
MFM, index or wiki were published. No manual staging/commit/push/merge/deploy or
other checkout change occurred. No background process was started. GNHF should
retain this bounded central candidate for its commit, then continue simulation
and roster acceptance before independent whole-consumer integration review.


## Explicit stop-hook knowledge handoff

The hook-authorized handoff checked existing notes before writing. Project checkpoint and roadmap now record the verified central slice and simulation/roster/root gates under `D:/Project/devlog/wh40k-oracle/`. The existing `learn-notes/decisions/20261001-separate-transactional-source-coverage.md` is extended rather than duplicated; one resolved validation-order record is saved at `C:/Users/Administrator/error-notes/rag/20261001-error-31-coverage-validation-order-bypasses-card-guard.md`, with both repository indexes updated. Original content and staged indexes are preserved. No commit explanation is invented for this uncommitted slice, and no additional harness promotion is warranted. No manual staging, commit or publication occurred; root retains intended knowledge publication.
