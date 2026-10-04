# Runtime integration acceptance — October 4, 2026

## Iteration 1 source-only price adapters

The bounded runtime slice is implemented and independently approved. Exact
source-only prices now reach `get_entity` and `get_datasheet`, survive evidence
recovery and history, and supply whole formatter qualifications and actual MFM
citations. This is incremental acceptance of the private candidate, not completion
of the owner objective or a production/data promotion claim.

Work started clean on `codex/release-final-integration` at exact
`aeba602909db2ec3fde6feae466f1844971725bf`, in
`C:/Users/Administrator/.codex/worktrees/release-final-integration/RAG`.
The orchestrator notes were read first and never modified. The actual source
preparation/price-selector, source consumer, benchmark and security acceptance
reports and the host `FINAL-ACCEPTANCE-PLAN.md` were read. Existing approved price
grammar, coverage rendering, consumer boundaries and categorical errors are reused.
No source-coverage guard, data, provider, dependency or numerical algorithm is changed.

### Verified behavior

- The adapters consult reviewed `official_points.exact_unit` before fuzzy or
  wiki/body lookup. Exact full names, source factions and reserved selectors
  retain all source price rows. Equal cross-faction prices remain ambiguous and
  their emitted candidates round-trip without a canonical body. Malformed or
  unknown reserved selectors cannot borrow a fuzzy sibling or archived body.
- Price-only results retain `unit_id=None`, `page=None`, `datasheet=None` and
  no fabricated canonical ID, models, weapons or composition. Exact canonical
  identity/faction matches keep their existing body path. A copied database's
  direct-Python datasheet call constructs its resolver against that copy instead
  of the production default. All existing Python tool signatures and thirteen
  immutable public argument contracts are unchanged.
- Synthetic current ordinary Calgar 180 remains independent from explicitly
  archived 200. Verified Chinese archive aliases can bridge to that exact current
  price identity; the archive remains separately attributed. Armour's retained
  historical 155 remains non-current, and Kaius 100 never inherits Kaius Alpha's
  999 or its body. These fixture values test integration; they do not authenticate
  source publications or recertify the separately owned historical-data restore.
- Strict source-only coverage is resolved through the existing central helper
  and preserved whole on `source_note`, `note` and `source_scope`. Its exact body
  status, scope, independent effective-date or unverified-date statement, source
  faction and full provenance survive. Invalid declarations still raise
  `CoverageError`; the adapters do not silently replace them with a stale body.
- Unambiguous source price rows are useful PRICE evidence. An identity without
  usable fields remains insufficient. Later empty lookups, malformed final
  actions, forbidden internal arguments and step-limit recovery preserve both
  subjects, historical boundaries and citations rather than using automatic RAG.
  Emergency prices retain both tier and model labels, including second-unit and
  wargear conditions. This does not authorize rules or list legality.
- Assistant history stores the complete answer rather than cutting it at 4,000
  characters; the existing twelve-message bound remains. The paired two-subject
  checks exposed a real cut through the second subject's limitation before this
  correction. User input and standalone `SessionContext` behavior are unchanged.
- Independent review established two necessary formatter adapters. The existing
  official-source citation loop now includes `get_entity`. Mandatory source-only
  notes survive the digest budget even without registry metadata, and deduplication
  uses subject plus note so two identical generic warnings do not erase one
  subject. The existing central formatter and card paths are otherwise retained.

### Paired evidence and checks

Every test uses the unchanged supported interpreter:

```text
D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe
Python 3.11.9
```

All disposable SQLite, basetemp, caches, snapshots, logs and XML are under:

```text
D:/Project/py/RAG/db_sources/release-check-20260930/runtime-integration-owned/20261004/iteration-01/
```

No paid model, network, provider call, installation, model loading, Docker,
GitHub operation, production/cache/index/wiki/PDF generation or data publication
was performed. Fake LLM actions dispatch the actual tool adapters through the
actual `AgentLoop` and `TraceRecorder`, then exercise the actual formatter.

| Final evidence | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Identical final 37-node matrix on exact starting tools/loop/formatter | 4 | 33 | 0 | 0 |
| Final candidate new matrix, included in the regression below | 37 | 0 | 0 | 0 |
| Fifteen-module runtime/recovery/coverage/security/benchmark regression | 1,301 | 0 | 0 | 0 |
| Seven-module tools/selector/datasheet/calc/provider preservation | 214 | 0 | 0 | 2 |
| Independent generic review, final runtime + identity files | 73 | 0 | 0 | 0 |
| Independent Python review, final runtime + identity files | 73 | 0 | 0 | 0 |

The four parent controls are identity-only insufficient evidence and archive-only
historical behavior, each through both tools. `run_parent.py` extracts exact
starting Git blobs for only tools, loop and formatter, loads them under their
actual module names and asserts their imported paths. Support modules are the
unchanged candidate modules. `parent-imports.json` records bindings and hashes.
The final matrix test file and all 37 node identities are identical across the
paired runs; no absent new API is invoked to manufacture a baseline failure.

`verification.json` reconciles XML nodes, outcomes and public signatures/contracts,
parses changed Python sources and verifies exact protected Git blobs. Source
coverage, central coverage notes, official price selector, model client and
`qa_gold.json` remain unchanged. Gold SHA-256 remains
`a402aed889eff64f3419d7a6768ff9b168a5912d0bc9c3e92cf225913a7fe3cc`.
`git diff --check` passes. Ruff, Black and Flake8 are unavailable in this fixed
environment; none was installed. No frontend change requires a frontend build
in this iteration. Existing deprecation warnings are retained in the logs.

The two additional-suite skips are the unchanged real-database cases
`tests/test_agent_tools.py::TestCalcPointsRealDbTitanRegression::test_four_titans_all_resolved_with_official_points` and
`tests/test_agent_tools.py::TestSameNameCrossFactionRealDb::test_helbrute_four_factions_points_from_real_db`, each with
the original reason `需要 db/wh40k.sqlite`. The exact XML node identities are
reconciled; the missing isolated asset is not repaired, excluded or disguised as
passing. No new skip is introduced.
The 1,301-case core acceptance and both independent matrices have zero skips.

The primary regression command uses `-B -m pytest -q -rs`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONUTF8=1`, `WEB_API_WARMUP=0`, `WEB_API_RETRIEVAL=off`, a D-drive basetemp/cache
and XML path, and these unchanged file selections:

```text
tests/test_runtime_price_adapters.py tests/test_source_only_price_identity.py
tests/test_agent_source_archive.py tests/test_agent_loop.py
tests/test_agent_loop_recovery.py tests/test_agent_tool_boundary.py
tests/test_agent_error_boundary.py tests/test_source_coverage_consumers.py
tests/test_source_coverage_calculations.py tests/test_source_coverage.py
tests/test_source_coverage_legacy_history.py tests/test_source_coverage_transitions.py
tests/test_web_card_provenance.py tests/test_qa_bench_source_coverage.py
tests/test_qa_source_contract_boundary.py
```

The additional selection is `test_agent_tools.py`, `test_price_selector_roundtrip.py`,
`test_db_compile_datasheet.py`, `test_db_compile_calc_points.py`,
`test_agent_lookup_completeness.py`, `test_llm_client.py` and
`test_llm_transport_policy.py`, with the same runtime/output controls. There are
no new deselections, weakened fixtures, benchmark changes or production-asset substitutions.
The complete actual 3,635-row source ledger and conditional Storm Shield source
binding remain the separately approved price-owner evidence; this new matrix
uses accepted-schema synthetic integration fixtures and does not claim another
real-source audit.

### Attempts, review and remaining work

Preserved unsuccessful attempts remain visible:

- `fixture-transaction-attempt.*`: 26 setup errors because the new fixture omitted
  the registry's required caller transaction. Explicit `BEGIN` corrected setup;
  these errors are not behavioral baseline evidence.
- `base.*`: the corrected initial 28-node matrix gives 26 failures/two controls.
- `candidate-01.*`: 20 passes/eight genuine history truncation failures.
- `candidate-02.*`: 20 passes/eight test attribute errors (`entityCard` instead
  of the existing Python `entity_card`). The assertion was corrected without a
  contract change. `candidate-03.*` then passes the intermediate 35-node matrix.
- `review-red.*`: eight failures exposing missing emergency tier labels.
  `citation-red.*`: after tier correction, four remaining actual formatter
  citation failures. `digest-red.*`: two no-registry qualification losses.
- `verification-annotation-attempt.log`: the evidence script initially expected
  an ordinary AST assignment for annotated `TOOL_SPECS`; corrected verification
  supports both assignment forms without changing source/tests.

Generic and Python reviewers approve only this bounded runtime slice. Their
final XML/logs are in `generic-review/` and `python-review/`. They do not certify
successful model prose/structuring as universally qualification-preserving.

Next iteration must verify the broader canonical `get_entity` whole-qualification
seam, long-body/two-date success and formatter paths, then make the tiny edition
number and two simulator scope-copy corrections against actual options/report
contracts. Those TypeScript edits still require independent TS and generic review.
The consumer report is untouched: the clean starting/current diff does not expose
the previously described four whitespace lines, and no broad cleanup is performed.
Separately owned source-coverage A metadata correction, supported setup/Origin
fixture, rebuild/history/Black Library metadata, staged updates, overlay ledgers
and fresh-listing policy remain their owners' work.

The full actual-asset native/model/Docker/browser/115-question benchmark/CI,
source promotion and release publication remain root gates. No whole-project
completion or production freshness claim is made. No manual staging or Git
commit is performed; GNHF owns the intended scoped commit and later clean-tree
check. All test processes exited; no server, watcher or browser was started.

Verified learning/error handoff is deduplicated into existing evidence-retention
notes and project checkpoint/roadmap, preserving prior content and concurrent
entries. No fictional commit explanation or new harness promotion is warranted;
root retains knowledge publication ownership. The complete owner stop condition
is not met in this iteration.
