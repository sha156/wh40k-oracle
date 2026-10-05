# Nested calculation qualification acceptance — October 5, 2026

The independently reproduced nested `calc_points` omission is corrected in this
bounded local candidate. Whole source and identity qualifications now survive
successful, max-step and emergency answers, bounded assistant history, the soft
formatter budget and visible formatted output. Independent generic and Python
source/test reviews approve the exact final diff. The intended automatic GNHF
commit and subsequent clean-tree/root handoff remain pending; this report does
not claim whole-project acceptance, publication or deployment.

Work started clean on `codex/release-final-integration` at
`534eba49b6c65c1593d8ddceb852850483a73718`, after root merged the approved
`5fd12da5b150a018602b39431cc6a6d30a8f8bef` family. Orchestrator notes were read
first and remain untouched. Ownership is limited to `agent/loop.py`,
`web_api/formatter.py`, the existing `tests/test_runtime_whole_qualification.py`
and this report. No manual staging or commit occurred.

## Reproduced boundary and correction

The exact recovered independent review was read before implementation:

```text
D:/Project/py/RAG/db_sources/release-check-20260930/host-runtime-code-review-e1a7/review-20261005-recovery/REVIEW.md
```

Its frozen candidate is `e1a7d8aa70796a4f47a37b1a8f92da01a77cebc5`; the true
family parent is `aeba602909db2ec3fde6feae466f1844971725bf`. Both have the nested
omission. The saved default-digest identity membership mismatch is Python
dictionary representation versus JSON, not semantic identity loss. This work
addresses the actual missing mandatory set at `limit=1` and the successful
answer/history/formatter omission.

The actual public call remains `calc_points(unit_list=['普通卡尔加', 'Kaius'])`.
The existing disposable `price_db` fixture yields current ordinary Calgar 180,
separately attributed archived 200, and source-only Kaius 100. Those are synthetic
integration controls, not authenticated live official prices. The tool already
returns the correct payload and is unchanged.

- The shared qualification extractor follows only the result, its supported
  datasheet, their historical records, `units[]` rows and each row's historical
  record. It preserves complete `source_note`, `source_scope`, `note` and
  `identity_scope` values. It does not recursively search arbitrary dictionaries.
- Nested qualifiers carry the unit name and faction. Archive qualifiers carry
  a separate historical-record label. The fixture has five distinct qualification
  values and six subject-associated qualifications: its identical current-price
  scope must remain attached to both Calgar and Kaius.
- A shared safe units-list adapter ignores malformed containers and nondictionary
  rows across qualification, usable-evidence, recovery-fact, archive-source and
  formatter archive paths. The existing calculation empty-result predicate uses
  those safe rows; behavior for valid public payloads remains unchanged.
- Successful and max-step completion retain whole missing qualifications.
  Emergency recovery also retains them after the existing twelve-fact readability
  bound, using `dataclasses.replace` for the frozen `AgentResult`. Prices, trace
  metadata and collected sources remain intact. The existing twelve-message
  session-history bound retains the complete answer and supplies it to the next
  turn.
- Formatter mandatory selection now includes the supported nested subject/archive
  qualifiers through that same extractor. All whole mandatory qualifications
  precede optional bulk text, including at `limit=1`. Existing root/datasheet
  representation and absent-registry legacy digest byte equivalence are preserved.
- The existing visible-body gate consumes the expanded shared set. Omitting
  layouts, including layouts that hide qualifications only in follow-ups, fall
  back to the complete original answer and verified citations. Complete layouts
  continue to pass. Debug, raw-body, error, trace and arbitrary argument mappings
  do not become mandatory public evidence.

No public signature/argument contract, tool calculation, selector, source policy,
price, source provenance, citation derivation, gold file or skip condition changed.
The complete actual-tool payload is equal before/after and equal to the original
recovered probe. Both fresh disposable probe databases remain byte-identical.

## Frozen paired evidence and validation

Interpreter: unchanged stable CPython 3.11.9 at:

```text
D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe
```

Evidence root:

```text
D:/Project/py/RAG/db_sources/runtime-integration-owned/20261005/nested-calc-qualification/
```

`iteration-01/baseline-e1a7/` is a separate copy of the saved frozen candidate,
with the exact final test file supplied to both runs. Original frozen source/proof
files were not overwritten. `verification.json` rehashes all **818 original frozen
files / 19,354,600 bytes**, checks copied module identities, protected current files,
test-file equality and ordered paired node identities. Pytest prepends the external
copy's location to baseline XML class names; reconciliation normalizes only that
location prefix and compares the exact module suffix and parametrized node order.

| Evidence | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Frozen e1a7, exact final 45-node qualification file | 24 | 21 | 0 | 0 |
| Current candidate, identical ordered 45 nodes | 45 | 0 | 0 | 0 |
| Final targeted runtime, recovery, source-only, source-consumer and formatter selection | 649 | 0 | 0 | 0 |
| Independent generic qualification/legacy-consumer checks | 62 | 0 | 0 | 0 |
| Independent Python qualification/legacy-consumer checks | 62 | 0 | 0 | 0 |

The 24 baseline passes are existing positive controls and two already-safe malformed
controls, not newly repaired behavior. The 23 new cases cover the real two-subject
tool through normal/max/emergency/history/late-failure endings, omitting/follow-up-only/
complete layouts, both digest budgets, identical warnings, unsupported sentinel
mappings, malformed containers/mixed rows and qualifications beyond twelve facts.

The final fresh selection is:

```text
tests/test_runtime_whole_qualification.py
tests/test_runtime_price_adapters.py
tests/test_agent_loop_recovery.py
tests/test_agent_source_archive.py
tests/test_source_only_price_identity.py
tests/test_source_coverage_consumers.py
tests/test_web_card_provenance.py
tests/test_llm_json_parsing.py
tests/test_web_api_stage3.py::test_formatter_derives_slots_and_richtext
tests/test_web_api_stage3.py::test_formatter_fallback_without_structurer
tests/test_web_api_stage3.py::test_formatter_degraded_flows_through
tests/test_web_api_stage3.py::test_contract_json_roundtrip_camelcase
```

Commands use the full interpreter, `-m pytest -q`, `PYTHONUTF8=1`,
`PYTHONDONTWRITEBYTECODE=1`, external `--basetemp` and `--junitxml` paths. XML confirms
zero failures/errors/skips. One existing invalid-escape deprecation warning remains
in `final.log`. Python syntax/AST and `git diff --check` pass. Ruff, Black, Flake8 and
mypy are unavailable in this environment; none was installed. No frontend code
changed or frontend build result is claimed.

The unchanged original `probe_calc_qualifications.py` ran against the frozen copy
and final candidate using separate disposable databases. `baseline-probe/result.json`
and `final-probe/result.json` show unchanged numerical/provenance payloads. For normal,
max-step and malformed-final cases, every one of the five original complete values
is now present in answers, history, ordinary and `limit=1` digests and visible fallback
output. Omitting successful layouts now degrade conservatively; an already-degraded
emergency answer retains all qualifications when formatting is attempted.

Earlier saved root 650/704/145 and separately reported 424 acceptance remain
historical evidence, not rerun broad acceptance. The verifier directly reaccounts
the original 650/704/145 XML files. No new actual-asset, model, browser, Docker,
benchmark, CI or release acceptance is inferred from this targeted correction.

## Independent review and retained attempts

Generic and Python reviewers approve the exact source/test SHA-256 set:

```text
agent/loop.py
ece4e1e8d0b33b067aba4212439b113aeaf38deb0daf14d2baf9d60ff0d6db5a
web_api/formatter.py
00ab6ec90145ef0e6cebb34446e95db555221457e0095216129cfd224c9e22b9
tests/test_runtime_whole_qualification.py
7dfbcefc0b2b855a798842a3b507056a068315840af540563ea686af535b8343
```

Reports are `review-generic.md` and `review-python.md` at the evidence root;
their independent XML/logs are under `generic-review/` and `python-review/`.
Source/test approval preceded this report's final evidence cross-check.

Unsuccessful attempts remain preserved under `iteration-01/`: the initial candidate
recovery tried assigning to frozen `AgentResult.answer`, causing
`dataclasses.FrozenInstanceError: cannot assign to field 'answer'`. The final fix uses
`replace`; the 290-failure initial log/XML is not counted as acceptance.
`candidate-r2` passed 555 before the final mixed-row/debug controls and legacy digest
preservation checks. The initial verification failed on baseline XML's location
prefix; `verification-r2.log` records the corrected ordered-node reconciliation.
No original proof or failed log was overwritten, and no failure was hidden by a
skip, weakened expectation, fixture price change or gold edit.

## Commit and knowledge handoff

No server, browser, watcher, model or service was started. All validation processes
completed. No network, installation, Docker, GitHub or source-asset operation occurred.
Concurrent owners' source and shared notes/indexes remain untouched.

GNHF owns the automatic scoped source/tests/report commit. Root must check that
real commit and clean status before closing the configured loop. Knowledge handoff
is deduplicated against the existing evidence-retention decision and underlying
later-lookup evidence-loss error record; the reviewed append text is saved externally
as `iteration-01/knowledge-handoff.md` for root to apply with the actual correction
commit ID. No fictional commit ID or duplicate underlying issue is created.
Checkpoint/roadmap/shared-note publication remains root's responsibility within
the explicit narrow ownership of this task.
