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

## Iteration 3 — exact ledger identity and price lookup precedence

This iteration implements the bounded price-resolution portion of outcome 3. The starting tree was clean at `754ba4b53`; the original objective base remains `1cdb85f7605a5f36b833e1423f7136b4e2c449bf`. The earlier historical-card and separate coverage-contract implementations are retained. No manual staging, commit, publication or deployment was performed.

### Exact lookup and preserved identity

`web_api.official_points.exact_unit(db_path, name, *, faction_slug=None)` is an internal helper, not a new public model-tool argument. Existing name-only calls remain supported. An exact full English ledger name is matched first, including parenthesized variant text. When no full-name match exists, `Full Variant (source-slug)` or full-width parentheses can select an exact source faction. Internal callers may instead supply the full name and `faction_slug` separately. Canonical faction codes such as `SM` are not substitutes for full source slugs; chapter slugs remain distinct. Wrong faction or variant lookups return None without borrowing another ledger identity.

All matching unit rows are read without a pagination limit. Every model-size, repeat-unit and equipment tier remains in `official_prices`, with its original section, full name, faction slug, URL, source SHA-256 and capture timestamp. The scalar uses the existing base-tier/model-count semantics, so a weapon surcharge or later repeat-unit tier cannot become the base unit price. Enhancements cannot masquerade as unit matches.

Multiple source factions always produce `ambiguous=true`, `points=null`, `faction_slug=null`, and per-faction `candidates` containing exact re-query strings, minima and all source rows. Equal minima never collapse identity. The paired same-name fixture also has one exact canonical body in only one faction; that partial canonical index cannot hide another exact ledger faction. Space Marines, Blood Angels and Dark Angels remain separate price-source identities even when all prices equal 80.

The price payload has `unit_id=null`, `points_only=true`, `price_status=current_published`, `effective_date=null`, `source_scope`, a capture-qualified `note`, `price_sources` and lossless `official_prices`. It contains no model, weapon or invented datasheet fields. `points_only` describes the returned evidence, not proof that no body exists anywhere. It explicitly does not certify full-body coverage, equipment/composition legality or simulation rules. `price_sources` uses `captured_at` for ledger `fetched_at`; publication/source dates remain null because the existing ledger has no such date. A legacy fixture without a source hash reports a null hash rather than inventing one. Reviewed coverage-registry dates/provenance are not consumed by this helper yet; that integration remains part of the central coverage propagation slice.

`agent.tools.calc_points` now selects exact ledger identities before fuzzy canonical siblings and before ambiguous candidate expansion. A valid exact canonical path is retained only when its stored full English variant, canonical faction and, for a chapter-specific source, `faction_keywords` match the ledger identity. This prevents even an exact community alias to a different variant or a same-name body from another faction/chapter from replacing the source-only result. These checks establish identity only; they do not certify current rules bodies. Direct canonical-ID behavior and valid current canonical tier selection remain unchanged.

The ordinary Calgar archive bridge remains intact: current ordinary Calgar 180 and its two-model 300 tier remain distinct from historical ordinary Calgar 200 and historical Armour of Antilochus 155. No scalar unknown becomes zero. The fixture's Kaius 100 wins over the real resolver's fuzzy `Kaius Alpha` 999; no Chinese alias for Kaius is guessed. Internal copied-DB calls without an injected resolver now construct their resolver from that copied DB rather than reading the default runtime DB. The public `calc_points` callable signature, schemas and dispatch are unchanged.

Scope and capture qualifiers are serialized before bulk tiers. A regression through the actual formatter's 600-character evidence slice retains Kaius's full identity, source slug, price, capture timestamp and rules/effective-date limits. This checks the single source-only price result; it does not claim complete multi-subject coverage-note preservation or emergency-loop integration. Existing `calc_points` evidence remains usable under the unchanged loop's price/official-row branch. No `get_entity`, `get_datasheet`, resolver or simulation body path is made price-only aware in this iteration.

### Integration interface and remaining loop seam

Later promotion continues to stage the lossless MFM ledger in its reviewed transaction using the previously documented connection-aware APIs. This slice performs only read-only resolution after that staging; it publishes no real coverage or prices. Call `exact_unit(copied_db, full_name, faction_slug=exact_slug)` or the existing `calc_points([qualified_name], db_path=copied_db, resolver=copied_resolver)` internal seam. Do not expose `db_path`, `resolver` or the new helper keyword through public tool schemas.

The exact source-only tool evidence is `calc_points -> units[i]` with `unit_id: null`, exact `name_en`/`faction_slug`, `points_only: true`, nullable `points`, `ambiguous`, `candidates`, `price_status`, `effective_date`, `price_sources`, `official_prices`, `source_scope` and `note`. Historical Calgar additionally carries the unchanged `historical_points` and `historical_record` with its variant/composition boundary. `official_sources` retains the existing URL/capture citation shape. Source-only results do not yield an EntityCard or a loadable Datasheet. If later adapters expose this evidence as a `get_datasheet`/`get_entity` result with `datasheet/page: null`, root/security must add the narrowly tested usable-price branch there; `found=true` alone does not preserve such evidence after a later empty lookup. `agent/loop.py` remains untouched.

### Final validation and exact evidence

All checks used the unchanged `D:/Project/py/RAG/.venv/Scripts/python.exe`, Python 3.9.1. No environment upgrade, install, network/model call or background service was required.

| Check | Result |
| --- | --- |
| Identical final 36-test matrix against exact frozen base boundary modules | 22 failed / 14 passed / zero skipped |
| Final candidate matrix | 36 passed / zero skipped / five existing SWIG warnings, 9.62 s |
| Price identities, agent/archive, coverage, MFM sync, historical cards, datasheet and canonical price suites | 251 passed / two skipped / eight existing warnings, 26.19 s |
| Exact base/candidate direct stored-DB probes | Passed; each probe DB byte-identical before/after lookup |
| Syntax compilation, actual diff inspection and `git diff --check` | Passed |
| Ruff / Black / Flake8 | Absent in permitted interpreter; no install attempted |

The base run loads exact Git bytes of `agent/tools.py` and `web_api/official_points.py` from the original objective base in isolated processes. Unchanged dependencies and the preceding candidate slices remain in place; this comparison measures this iteration's price-resolution boundary, not a full checkout or full-native acceptance. Base failures include both actual scalar/fuzzy/qualification defects and assertions for the new metadata/interface. The 14 passing controls preserve current canonical lookups, ordinary Calgar archive precedence, a full parenthesized name, unknown-name handling, old databases and read-only behavior. No synthetic assertion is counted as real-source promotion evidence.

The two skips are existing `test_agent_tools.py` real-DB checks for the four Titan prices and four Helbrute faction prices; both require the absent `db/wh40k.sqlite`. Exact node IDs/reasons are saved in JUnit XML and `final-verification.json`. The initial broader command selected nonexistent shortened test filenames and collected no tests; its log/XML remain as `focused-collection-failure.*`. Corrected final runs use the actual `test_db_compile_datasheet.py` and `test_db_compile_calc_points.py`. Initial and intermediate paired/review runs are retained and superseded by the final counts above.

Ignored evidence root: `C:/Users/Administrator/.codex/worktrees/release-web-security/RAG/db_sources/source-coverage-preparation/iteration-03/`. It contains exact frozen base bytes/hash manifest, exact final candidate bytes/hashes, the reusable `verify_pair.py`, final base/candidate/focused JUnit XML and text, preserved intermediate logs, `base-final-probe.json` / `candidate-final-probe.json` with stored disposable databases and before/after hashes, and `final-verification.json`. Probe outputs show base Kaius selecting the sibling 999 and base Shared Hero returning 120 without identity disambiguation; the final candidate returns Kaius price-only 100 and unqualified Shared Hero as ambiguous/null with exact source candidates.

### Scope and verified handoff

Tracked changes are confined to `web_api/official_points.py`, the price-only additions within `agent/tools.py`, the new synthetic regression file and this appended report. Production PDFs/manifests/database/index/wiki, historical assets, DSL/Chinese guards, benchmark gold/results, dependencies, Codex/GNHF settings and live services remain untouched. Public schemas/dispatch, `agent/loop.py`, main/rate-limit/provider security boundaries and other owners' work are not edited. All test/probe processes completed; no background process was started.

Project CHECKPOINT/ROADMAP and learning/error notes were searched for duplicates before this distinct price-identity handoff. The verified result is appended to `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`. The decision note is `C:/Users/Administrator/learn-notes/decisions/20261001-exact-price-source-identities.md`; the combined underlying identity-resolution defect is recorded at `C:/Users/Administrator/error-notes/rag/20261001-error-22-price-ledger-identity-collapse.md` with its README index. Earlier handoffs and concurrent entries are preserved. No knowledge-repository staging/commit/push is performed, and no new commit is claimed.

Outcomes 1 and 2 remain implemented; outcome 3's exact price lookup/precedence boundary now has meaningful paired regressions. The optional safe price-only body lookup adapters and their root/security-owned loop branch, reviewed coverage-date propagation, outcome 4's normal/reverse simulation and roster scope gates, and outcome 5's pre-ranking historical eligibility remain. Independent host review, supported Python 3.11/Linux/full-asset, browser, benchmark and CI acceptance, real registry/rebuild publication and actual September 30 promotion remain root gates. This is an isolated incremental candidate; the overall stop condition is not met.

## Iteration 4 — dated historical scope before candidate selection

This iteration implements outcome 5's retrieval preparation boundary in `corpus_manifest.py` and `app.py`, with genuine synthetic flat FAISS/BM25 regressions. The initial tree was clean at `1ca6b129f` on `codex/release-source-coverage`; paired boundary modules are frozen from the original objective base `1cdb85f7605a5f36b833e1423f7136b4e2c449bf`. Prior slices are preserved. No real book declaration, active index, PDF, wiki, database, service, dependency, benchmark or security-owned file was changed.

### Classification and later publication interface

`classify_book_with_origin(book_name, manifest)` now preserves validated optional `status`, `scope` and `effective_date`, alongside edition/layer and the existing origin. Status, when supplied, is exactly `current`, `carry_forward` or `historical`; unknown/null statuses are rejected. Scope is a nonempty reviewed text label of at most 500 characters. Effective dates are canonical calendar-valid YYYY-MM-DD strings or null. Historical status requires a date and can only be declared under an exact book key, never a prefix or default. Scope is a retrieval label, not per-unit full-body certification, and source capture dates must not be substituted for effective dates.

The later promotion worker can publish an exact entry using the existing manifest interface:

```json
{
  "books": {
    "Exact archived chunk book key": {
      "edition": "11",
      "layer": "overlay",
      "status": "historical",
      "scope": "withdrawn full chapter pack",
      "effective_date": "2026-06-20"
    }
  }
}
```

This is a synthetic declaration, not an assertion about any actual source. Use the captured source/legal-date evidence and the actual `ingest.get_book_name()`/indexed book key when preparing real entries. Keep retained carry-forward codex sources eligible and distinguish current Legends-only publications from their withdrawn full predecessors. The official recommendation and saved hashes remain the later promotion authority; this iteration does not infer withdrawal from age, edition, prefix, points membership or catalogue absence.

`resolve_book_metadata(metadata, manifest)` is the new small read-only resolver. Valid exact declarations override old indexed tags even when edition/layer already exist; indexed source tags survive when there is no exact override. Prefix/default tags only fill absent fields. Absent optional declarations retain legacy fields and eligibility. No indexed Document is mutated. The real existing Universal Rules Updates effective date is preserved by classification without editing its declaration.

The later worker still owns real manifest/index publication, exact archived sources and restart/rebuild verification. The runtime resolver lets exact declarations govern already-tagged copied indexes without re-embedding; it does not atomically publish a manifest and SQLite coverage registry or acquire a missing rules body. Outcome 1's separately validated transaction contract remains the body authority.

### Retrieval and historical access

Default BM25 construction excludes confirmed historical documents before corpus statistics, scoring and top-K. Its resource cache includes serialized manifest content, so a new exact declaration cannot reuse the pre-exclusion retriever. If a caller supplies an older complete BM25 retriever, hybrid retrieval rebuilds its eligible candidate set before ranking. Explicit book selections rebuild from the full stored docstore, allowing historical access even when the default BM25 index omitted those sources. An uninspectable adapter can use the full docstore; if neither corpus is inspectable under declared historical scope, it reports a retrieval-side error instead of silently filtering a starved top-K list. Absent-declaration legacy adapters remain supported.

FAISS uses the same metadata eligibility predicate for ordinary recall and the independent rules-floor search. LangChain applies metadata filtering after vector search, so scoped requests fetch at least the complete stored `index.ntotal`/docstore candidate pool before selecting eligible top-K. The existing flat-index guarantee is demonstrated with real synthetic FAISS. This is **not** a pre-ANN filter or a completeness claim for arbitrary approximate indexes. Rules-floor fetch size also grows beyond the historical fixed 8,000 limit. Exact layer overrides govern rules-floor selection before injection; only eligible documents reach RRF/FlashRank. No vectors are copied/re-embedded by retrieval.

The existing `hybrid_retrieve(..., filter_books=[exact_book_keys])` interface is the explicit historical-access boundary. It disables unrelated rules-floor injection and retains historical status/date/scope in returned passages. A dated `source_note` is also prepended to historical passage text so bounded tool excerpts retain the limitation. `format_context` displays supplied status, effective date and scope. Public model-tool schemas/arguments are unchanged; the default web/agent `rag_search(query)` remains current-scoped. Automatic historical question routing or new model-controlled archive access is not added. Root/security owns any later explicit binding.

### Final validation and evidence

All execution used the unchanged `D:/Project/py/RAG/.venv/Scripts/python.exe` (Python 3.9.1). Tests use deterministic query vectors with `embed_documents` forbidden, real FAISS/BM25 and temporary synthetic document stores; no provider, network, real model or production asset call occurred.

| Check | Result |
| --- | --- |
| Identical final 31-test matrix against frozen boundary modules | 27 failed / four passed / zero skipped |
| Final candidate matrix | 31 passed / zero skipped / nine warnings, 17.53 s |
| Retrieval/classification/audit/coverage/price-identity/historical-card focused suite | 205 passed / nine skipped / eight warnings, 26.01 s |
| Exact base/candidate saved synthetic index probes | Base returns only archived hits by default; candidate returns current rules and carry-forward codex; both index/docstore hashes unchanged |
| AST syntax checks of runtime modules/tests, actual diff review and `git diff --check` | Passed |
| Ruff / Black / Flake8 | Not installed in permitted interpreter; no install attempted |

The base failures include actual dominated-top-K and missing temporal-field defects, plus new validation/interface assertions; they are not 27 independently observed production failures. Four controls pass for legacy absence, unlisted codex/prefix eligibility, current availability and unknown explicit book selection. The FAISS starvation fixture has 8,010 historical vectors before the current rules vector, exceeding the old rules-floor cap; the BM25 fixture independently proves old top-K hits all belong to the archived source before candidate preparation.

The nine skips are existing real-database tests in `test_audit_leftovers_r1.py` (four) and `test_audit_r1_core_chain.py` (five); this worktree lacks `db/wh40k.sqlite`. Exact node IDs/reasons are retained in JUnit XML and `test-summary.json`. Warnings are dependency SWIG/import deprecations plus the existing module-docstring invalid escape warning; no warning suppression was added. These are focused synthetic/local-stack checks, not full-native or real-source promotion acceptance.

Ignored evidence root: `C:/Users/Administrator/.codex/worktrees/release-web-security/RAG/db_sources/source-coverage-preparation/iteration-04/`. It contains exact base/candidate module bytes and hashes, `verify_pair.py`, final base/candidate/focused XML and text, direct probe JSON, saved synthetic `index.faiss`/`index.pkl` pairs and their before/after hashes, plus verification summaries. Frozen modules use their original worktree `__file__` for equivalent local metadata reads. An initial harness import used its evidence-directory path and hit an existing GBK/emoji warning encoding error; preserving the real file-relative location and UTF-8 execution fixed the harness without altering base bytes. An initial focused command used the nonexistent `test_historical_card_prices.py`; its no-collection XML/log is preserved, and the corrected run uses `test_historical_card_points.py`. Neither initial failure is counted as validation.

### Scope, handoff and remaining gates

Tracked changes are only the two owned runtime modules, `tests/test_source_retrieval_scope.py` and this appended report. Actual production PDFs/manifests/database/index/wiki, retained history, Chinese/DSL guards, benchmark gold/results, dependencies, public security/schema/dispatch and live services are untouched. GNHF orchestrator notes/settings are untouched; no manual staging/commit/push/merge/deploy occurred. All started test/probe processes finished; no server/browser/watcher was started.

CHECKPOINT/ROADMAP and learning/error notes were searched for duplicates before the distinct retrieval handoff. Verified results are appended to `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`; the decision is `C:/Users/Administrator/learn-notes/decisions/20261001-scope-retrieval-before-topk.md`, and the resolved underlying retrieval defect is `C:/Users/Administrator/error-notes/rag/20261001-error-23-historical-retrieval-starves-current.md` with its README index. Earlier/concurrent entries remain intact; no new commit is claimed.

Outcomes 1–3 remain implemented, and outcome 5 now has meaningful paired candidate-selection regressions. Outcome 4 remains unfinished: central per-unit coverage/date propagation through datasheet/card/tool evidence, normal/reverse simulation body qualification or denial, and roster validation/critique scope. Optional price-only body adapters and the narrow usable-evidence loop integration remain root/security-owned. Independent host review and supported Python 3.11/Linux/full-asset/browser/benchmark/CI gates, real coverage/manifest/rebuild publication and actual September 30 promotion remain pending. The overall stop condition is not met.

## Correction iteration 1 — coverage history and interrupted savepoints

The two independently reproduced coverage-state defects and interrupted-savepoint defect are corrected in `db_compile/source_coverage.py`. This bounded iteration starts from clean committed preparation HEAD `2acd1e4be7549e3f7553742cf8833f896b56b096` on `codex/release-source-coverage`. It reads the completed exact `754ba4b5393aa905da0dce37eb5de639b6db4dc3` host review and retains its findings. No registry is published. Exact before Git blobs for nine boundary/report/test files and SHA-256 hashes for all 5,718 tracked working files are frozen under the ignored correction evidence root. GNHF owns the eventual commit; this section does not invent a correcting commit or certify an uncommitted tree as a clean committed candidate.

### History boundary

The actual history schema is content-addressed: its primary key is `(identity_key, record_sha256)`. It does not declare event order, insertion time or a monotonic revision counter. The correction therefore reads all prior declarations for the exact identity, verifies stored payload digests, strict declaration shape and exact identity, and includes the current registry record for older callers without a history table. It does not sort digests into an invented timeline. Historical price provenance is validated structurally rather than compared against today's ledger, which may legitimately have advanced.

Unavailable declarations remain an anti-recertification barrier across historical, limited-fields and repeated/longer status detours. A proposed current full body's hashes must include evidence outside all recorded unavailable/retained evidence for that identity. Changing a URL, page, document date, capture timestamp or effective-date label does not acquire new bytes. The barrier also covers reclassifying unchanged unavailable/preview evidence as full-body evidence. Legitimate newly reviewed full-source declarations can advance and can replay exactly; the structural contract still depends on human review of actual source truth and does not authenticate arbitrary newly supplied hashes.

All previously reviewed full and retained snapshots contribute to the latest known effective-date boundary, including after a fields-only detour. Older full/historical declarations or unavailable records retaining an older snapshot are rejected. An unavailable transition cannot drop a known full snapshot altogether. Relabelling a previously known older source with the latest date cannot replace the latest known source evidence. Newly reviewed distinct sources can advance full or retained evidence; the latter keeps empty current-body scope and does not claim current full coverage. Historical declarations remain possible. Exact prior-record, identity/faction/chapter, review-date and default-absent behavior are preserved; exact replay adds no history row.

The `source_date` chronology limit remains explicit: the schema means source/document date and does not distinguish a publication date from a printed cover/version/effective date. A future printed document date can be legitimate; capture is not publication or legal activation. This correction does not infer publication dates, reject effective dates merely because they follow capture, alter audited actual provenance, or redesign the schema. The existing effective-date/capture versus review checks remain unchanged. An actual SQLite positive control preserves an effective date after capture and a future document-date label.

### Interrupted savepoint ownership

Application cleanup now catches `BaseException`, rolls back and releases the owned savepoint, and re-raises the original failure object. Real SQLite connection subclasses interrupt before and after the second registry insertion, after the first actual registry/history writes. KeyboardInterrupt, SystemExit, asyncio cancellation and a distinct BaseException subclass all leave registry/history exactly as before the attempted batch; caller-owned prior rows and the active transaction survive and remain committable. Both newly created and pre-existing registry/history tables are covered. The caller's earlier savepoint with the same name is preserved. Cleanup exceptions cannot replace the original interrupt; a controlled release wrapper performs the real release then raises and verifies original object identity. No retries, global rollback, caller commit, sleeps or GC are added. If SQLite itself rejects cleanup, cleanup is best effort and the original failure still wins; this is not a guarantee that a broken connection can be made usable.

### Exact validation and preservation

All test/probe interpreters are existing and used read-only: stable native Windows Python 3.11.9 at `D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-ci/Scripts/python.exe`, and the permitted full project interpreter `D:/Project/py/RAG/.venv/Scripts/python.exe` (Python 3.9.1). No installs, provider/model calls, external network calls or production assets are used. New cases use actual disposable SQLite databases, transactions, writes and stored JSON/history; no boolean-result mocks or body/price edits make the guards pass.

| Check | Actual result |
| --- | --- |
| Identical final 61-control matrix against exact committed parent coverage module | 52 failures / nine compatibility passes / zero skips |
| Final 61-control matrix in candidate native/full-project runs | 61 passed / zero skips in each interpreter |
| Native 3.11 coverage, historical cards, datasheets, Chinese composition, source reconciliation and MFM sync | 195 passed / zero failures/errors/skips, 8.03 s |
| Broad 19-file full-project coverage/card/price/identity/archive/transaction/source-revision/retrieval controls | 550 passed / zero failures/errors / 43 existing missing-asset skips, 45.11 s |
| Broad native 3.11 candidate attempt | 450 passed / 18 failures / 51 errors / 44 skips, 32.04 s |
| Same existing broad controls with frozen parent coverage on native 3.11 | 389 passed / the same 18 failing and 51 error node IDs / the same 44 skips, 29.32 s |
| Actual saved SQLite direct/detour/downgrade/interrupt probes | Parent accepts both state defects and persists partial interrupt writes; candidate rejects/undoes each, preserving caller rows and all body/price sentinels |
| In-memory Python compilation, inspected scoped diff and `git diff --check` | Passed; no source-tree bytecode generation |

The 52 paired failures are individual synthetic control outcomes, not 52 distinct production defects. The nine passing controls preserve the direct retained-byte rejection, direct current/historical date floors, legitimate reviewed advancement and existing exact/date semantics. Final JUnit XML records every node/status, and verification compares identical 61-node sets and unchanged existing native preservation outcomes. The 43 full-project skips are two existing agent real-price checks, one resolver real-data check, four saved community-alias checks and 36 active/original/cleaned retirement-asset checks. Native 3.11 adds one collection-level skip because Streamlit is absent; full-project retrieval controls execute with stored synthetic FAISS/BM25 and no model. Skip IDs/reasons are saved rather than counted as verified production behavior.

The broader native failures/errors reproduce on the frozen parent and originate in unchanged temporary SQLite builder/fixture lifetimes (`WinError 32` at replacement/cleanup, with downstream expected-error assertions). This iteration does not modify the separately owned builder or its fixtures, add GC/retries, weaken those tests, or claim broad native 3.11 acceptance. The broad full-project suite passes, including source-revision actual child-process tests and unchanged exact-price/name/fuzzy/full-variant controls. Two initial test-harness mistakes (fixture import path and a missing explicit fixture transaction), an intermediate over-specific error-message assertion, and a harness mode that briefly loaded candidate bytes under a before-labelled run are preserved with their original logs/XML; none is used as paired evidence. The corrected frozen-parent run explicitly uses the frozen parent module.

Evidence root: `C:/Users/Administrator/.codex/worktrees/release-web-security/RAG/db_sources/source-coverage-corrections/iteration-01/`. It contains exact before blobs/hashes, all attempted/final XML and logs, commands/interpreter versions, the reusable paired harness, direct before/candidate probe JSON, six saved synthetic proof databases with full registry/history rows and unchanged body/price hashes, exact node/skip accounting, final source hashes and preservation verification. No test server/browser/watcher is started; all test/probe processes exit.

Tracked candidate changes are limited to the coverage module, new adjacent offline transition/interruption tests and this appended acceptance report. The historical-card, exact-price, pre-ranking retrieval, public/security contracts and helper source files remain exact before bytes. Production database/index/wiki/PDF/cache/model/assets, dependencies, other worktrees, source research and GNHF notes remain untouched. Devlog CHECKPOINT/ROADMAP and the existing learning/error repositories receive a deduplicated verified handoff: one combined transition/history issue, one interrupted-savepoint issue and one reusable decision. No manual staging/commit/push/merge/publication or harness promotion occurs.

Remaining correction gates are the independently reproduced eager copied-DB resolver construction for a direct canonical ID and the emitted candidate-query/literal full-variant collision. `agent/tools.py` and `web_api/official_points.py` are unchanged in this bounded iteration; these failures are not claimed fixed by existing general preservation tests. Next iteration should implement their narrow lazy and collision-safe seams with actual minimal helper/candidate-roundtrip controls and immutable public model arguments, then root can run its unchanged approved direct-Python override security control. GNHF commit/clean verification, independent exact host review/integration and real publication remain separate. Central consumer/simulation/roster propagation, actual source parity, Linux/full-asset/browser/benchmark/CI/deployment and September 30 promotion gates remain open. The whole correction-loop stop condition is not met.

## Correction iteration 2 — lazy copied-database canonical-ID helper

This iteration corrects only the independently reproduced HIGH eager resolver regression from the completed exact `1ca6b129fb2cfa1c23da09800c7b756806fc8d32` review at `D:/Project/py/RAG/db_sources/release-check-20260930/source-coverage-preparation/host-code-review-1ca6b129f/verdict.md`. Starting HEAD is clean `4498bb68f869bda95c0ecd478bcb42fc4394234e` on `codex/release-source-coverage`. The prior history/savepoint correction is already present in that committed preparation tree. Exact before Git blobs and all 5,719 tracked working-file hashes are frozen in this iteration's evidence; GNHF owns the next commit. No real registry publication is attempted.

`agent.tools.calc_points` constructs an internal copied-DB `EntityResolver` only after a query misses the existing direct canonical-ID path. Existing IDs, including unpriced and non-current IDs, need only the original `units(id,name_en,points_json)` table. Missing prices remain null and retired prices remain non-current; they do not become reasons to invoke name resolution. Empty lists likewise need no resolver. Once actual name resolution is required, the copied-DB resolver is constructed locally and reused for the remainder of the call. Injected resolvers are retained. A failed copied-DB resolver is not replaced with the production resolver. Public signatures, schemas and dispatch are unchanged, with no new model-visible arguments.

The minimal reproduction uses the actual three-column database from the host review's contract, with no fake datasheets rows. Saved before/candidate processes see byte-identical synthetic databases. The committed before module raises `sqlite3.OperationalError: no such table: datasheets`; the candidate returns `found=true`, canonical ID `fixture`, price `123`, and leaves the database byte-identical. Actual full-schema fixtures separately verify mixed ID/name batches, exact copied-DB names, accepted fuzzy names with disclosure, unresolved names without production fallback, injected resolver preservation, exact source-ledger-before-fuzzy precedence and full parenthesized variants. The tests do not mock resolver answers or modify production/body/price data to obtain an outcome.

| Check | Actual result |
| --- | --- |
| Identical 14-control matrix on exact committed parent helper | Five failures / nine compatibility passes / zero errors/skips, 1.59 s |
| Candidate 14-control matrix, native Python 3.11 | 14 passed / zero errors/failures/skips, 1.43 s |
| Native coverage/history/savepoint/card/datasheet/composition/reconciliation/MFM preservation plus new helper controls | 209 passed / zero errors/failures/skips, 9.94 s |
| Broad full-project 20-file coverage/card/identity/price/archive/transaction/source-revision/retrieval preservation | 564 passed / zero errors/failures / 43 existing asset skips, 41.06 s |
| Exact minimal helper probe, in-memory compilation, scoped diff inspection and `git diff --check` | Passed; before/candidate database hashes match and neither lookup writes |

All execution uses the existing read-only native Python 3.11.9 CI interpreter or existing full-project Python 3.9.1 interpreter named in correction iteration 1. No installs, providers, models or network calls occur. XML reconciliation verifies identical 14 paired node IDs and exact counts, plus identical 43 pre-existing skip IDs and reasons against correction iteration 1. The missing-asset categories remain two real agent-price checks, one real resolver-data check, four saved alias checks and 36 active/original/cleaned retirement-asset checks. The broader project run's 15 warnings are existing dependency/import and invalid-escape deprecations; no suppression was added. Ruff, Black and Flake8 are absent in the permitted native interpreter; no install is attempted. Broad native Windows builder/fixture acceptance is still the separately recorded limitation; this iteration makes no new claim about that suite.

Evidence root: `C:/Users/Administrator/.codex/worktrees/release-web-security/RAG/db_sources/source-coverage-corrections/iteration-02/`. It contains exact before/candidate helper/test blobs and hashes, paired/focused XML/logs, commands/interpreter versions, two saved minimal SQLite databases and result JSON, a reusable paired runner, exact node/skip accounting and verification. All 5,717 tracked inputs outside the owned helper/report remain byte-identical, including coverage/history, historical cards, exact-price adapters, pre-ranking retrieval and public/security contracts. Tracked candidate scope is only `agent/tools.py`, `tests/test_calc_points_lazy_resolver.py` and this appended report. No production assets, dependencies, other worktrees, orchestrator notes or other owners' source files are changed. All started checks/probes exited; no server/browser/watcher was started. No manual staging, commit, push, merge or publication occurs.

The verified handoff is appended to the existing project CHECKPOINT/ROADMAP and exact-price identity learning note. One new underlying eager-helper regression is recorded in `C:/Users/Administrator/error-notes/rag/20261001-error-30-eager-copied-db-resolver-breaks-direct-id.md` and its existing README index; the already resolved history/interrupt notes are not duplicated. Concurrent content and staging are preserved. No new commit is claimed.

The separate MEDIUM candidate-query/literal full-variant collision remains reproduced and open. `web_api/official_points.py` is untouched in this bounded iteration. Next work must make emitted selections collision-safe or fail closed while preserving literal full variants and the exact internal `full_name`/`faction_slug` seam. Root still owns the unchanged approved public-boundary `test_direct_python_database_override_remains_supported` integration control, exact GNHF commit/clean verification, independent host review/integration and real publication. Final consumer/simulation/roster propagation and broader release/promotion gates remain separate. The whole correction-loop stop condition is not met.

## History final correction iteration 1 — exact legacy registry adoption

This iteration starts from clean `1a263aa6392f81c0c704f243ace5dfb5c04e0cef` on `codex/release-source-coverage` and corrects only defect B from the independent `host-code-review-4498bb68f/VERDICT.md` and `host-transition-review-4498bb68f/REPORT.md`. The independent proof JSON, reusable legacy probe and saved proof databases were inspected; the database inspection opens read-only connections and verifies unchanged file hashes. Prior strict-history/date and BaseException savepoint work, and the separately owned price/lazy-resolver/collision correction at `1a263aa`, remain intact. Earlier report sections retain their historical status; the collision correction in the current parent is not reopened here.

### Adopted history and exact replay

Before replacing a registry declaration, `apply_coverage` now saves the exact validated original `record_json` and its SHA-256 digest under its original identity key in content-addressed history. This includes registry-only states with missing or empty history tables. The original JSON is not reconstructed from its parsed dictionary: deliberate whitespace and a trailing newline remain exact in the SQLite evidence. An existing identical history row is preserved. Adoption, replacement history and registry writes share the existing owned savepoint, after all batch declarations have passed validation. No source, rule, model, DSL, archive or price row is modified.

Exact replay is a true write no-op, including noncanonical legacy JSON: it preserves the registry bytes, history rows/schema and SQLite `total_changes`. Mixed batches replace only changed declarations. Caller transactions are never committed, and caller savepoints, including an earlier savepoint with the same name, remain usable. Full original body source sets remain in the adopted payload. Historical price provenance remains structurally validated without requiring old declarations to agree with today's ledger.

The four registry-only bypass variants now reject: current-full September 30 → fields-only → September 14 full, and unavailable retained-source → fields-only → unchanged full recertification, each with missing and empty history. Further repeated honest historical/fields-only detours retain those boundaries. Distinct independently reviewed source declarations can still advance at the same or a later effective date, retain a full snapshot through unavailable status and replay unchanged; exact reuse after an unavailable barrier remains rejected. These are synthetic structural controls, not authentication of a supplied source hash.

### Actual SQLite validation and preservation

All execution uses only the existing read-only Python 3.11.9 interpreter at `D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`. Disposable SQLite databases, pytest basetemp, caches and copied evidence are under the owned ignored D-drive evidence root. No dependency installation, old main `.venv`, production asset, provider/model/network call or service is involved.

| Check | Actual result |
| --- | --- |
| Four identical bypass controls on exact `1a263aa` coverage bytes | **Four failed / zero errors/skips**: each forbidden final declaration is accepted; failure XML/log retained |
| Saved parent SQLite proof | **Four legacy bypass acceptances / two normal-history rejections**; body/price sentinels and caller work preserved |
| Saved candidate SQLite proof | **All six forbidden final declarations rejected**; adopted exact payload/digest and unchanged sentinels/caller work recorded |
| Final original coverage/history matrix | **57 + 61 passed**, unchanged original test files |
| New adoption/replay/interrupt controls | **32 passed**, including all four missing/empty variants and repeated detours |
| Final nine-file focused coverage/card/datasheet/composition/reconciliation/MFM/lazy-resolver suite | **241 passed / zero failures/errors/skips**, 11.15 s; final XML retained |
| In-memory compilation, Python 3.9 grammar/API/helper comparison and diff whitespace | Passed; only `apply_coverage` changes; all existing helper ASTs and public signatures unchanged |
| Tracked-file preservation | **5,718 tracked files outside module/report unchanged**; new focused test is the only added tracked-scope file |

Sixteen cancellation controls use real private SQLite connection subclasses to raise the exact KeyboardInterrupt object before/after the actual first/second history or registry insertion, with missing and empty history. They demonstrate successful rollback of the adopted original record, replacement records and owned schema together; pre-existing registry JSON, caller rows, the active transaction and caller same-named savepoint survive. Caller commit/reopen verifies the preserved state. The existing 61 controls retain SystemExit, asyncio cancellation and other BaseException coverage. Mixed validation failures occur before any adoption write. A separate controlled rollback rejection leaves two partial history rows until the caller explicitly rolls back and preserves the original interrupt: this records the best-effort cleanup limit, not successful atomicity on a broken cleanup path.

An initial wider command included `test_source_only_price_identity.py` and `test_db_compile_calc_points.py`, which use the unchanged native builder fixtures and hit the already documented `WinError 32`: **241 passed / four failed / 36 errors / zero skips**, 14.36 s. Its XML/log are retained as `surrounding-attempt.*` and are not claimed as passing. No native fixture fix was duplicated and those failing suites were not rerun. Their independently resolved native583 integration remains separately owned. The final focused result does not claim full-suite or full collision-fixture acceptance. Ruff, Black and Flake8 are absent in the permitted interpreter; no install was attempted.

Evidence root: `D:/Project/py/RAG/db_sources/source-coverage-preparation/history-final-correction/iteration-01-legacy-adoption/`. It contains the exact parent module, baseline and tracked hashes, reusable paired runner, four-failure negative-control XML/log, six parent and six candidate saved SQLite proofs, intermediate/final XML/logs, full declarations, sentinel hashes, node accounting and preservation verification. Parent coverage SHA-256 is `5527c71d6128e22a22b7b403e7f49e0cd79a23012d08b0aa8ec44c2ed691d139`; candidate coverage SHA-256 is `6390dd7d448c1e34c31836233fbae9b13450182c6562e55958e8d81fdddfb9e2`; new test SHA-256 is `9e30de4e5fb43c234e0c90dd83f437c1d81d0066af2ee28352866cacaef27272`. Negative and final candidate XML contain the same four bypass node IDs. The earlier 147-pass coverage run predates the three additional zero-write replay controls; the final coverage count is 150.

### Remaining scope and handoff

Defect A remains open: the same-date `{A}` → `{A,D}` → unavailable retaining `{A}` path, directly or through fields-only, still requires a separate latest-source-footprint correction. `_check_body_transition` is unchanged in this iteration; no new candidate acceptance is claimed for that defect. The next bounded iteration must retain the independent distinct-source advancement/replay/date controls while rejecting loss of known latest-date evidence without inventing content-hash ordering.

Tracked scope is only `db_compile/source_coverage.py`, `tests/test_source_coverage_legacy_history.py` and this report append. No other owner's source, consumer, dependency, worktree, source declaration, database/index/wiki/PDF/model asset, Docker service or orchestrator notes are changed. External knowledge publication remains root-owned; verified learning/error handoff is contained here without duplicating external notes or indexes. All started test/probe processes exited; no server/browser/watcher was started. No manual staging/commit/push/merge/publication occurs: GNHF owns the scoped commit, which has not yet happened in this iteration.

Structural history checks cannot acquire or authenticate arbitrary new source hashes, identify publication dates from printed source dates/captures, or certify semantic full-body parity. Exact committed independent review, defect A, real declaration publication, consumer propagation and broader release/promotion acceptance remain pending. This is a reviewable incremental correction, not a completed release; the overall stop condition is not met.

The subsequent explicit stop hook completes the duplicate-checked local knowledge handoff: appended checkpoint/roadmap entries under `D:/Project/devlog/wh40k-oracle/`, extended `C:/Users/Administrator/learn-notes/decisions/20261001-coverage-history-and-savepoint-ownership.md` and `C:/Users/Administrator/error-notes/rag/20261001-error-25-coverage-status-detours-and-retained-downgrade.md`, and updated their existing index entries. No duplicate issue/decision, correcting `commits/` record or private harness rule was created. The evidence root's `knowledge-handoff-verification.json` verifies original devlog content and staged entries across all three note repositories are preserved. No manual staging/commit/push occurred; root retains intended publication ownership and GNHF retains the scoped correction commit.
