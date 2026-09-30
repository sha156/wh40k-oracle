# Versioned benchmark preparation acceptance — October 1, 2026

## Source-cited v3.7 and narrow dated coverage candidate

This continuation starts from clean `codex/release-benchmark-versioning`, full
HEAD `0268450dc3a279bae64da315456793387702ea36`. The previous run reached its
iteration limit; it did not finish the objective. This bounded unit completes
the separate profile and its narrow offline answer-coverage ceiling. GNHF owns
the commit. **No fresh paid/real LLM benchmark has been run.** Root review,
integration, deployment, fresh-answer execution and release approval remain
outstanding. No clean committed candidate is claimed before GNHF commits.

Candidate: `benchmarks/v3_edition11/qa_gold_v3.7_source_cited.json`, version
**v3.7**, edition **11**, exactly **115** unique ordered rows. Byte SHA-256:
`aeed2af4f6e225a5761f8e62f541cd3472f67ac43ebffe7865747a96b31126b0`.
All questions, IDs/order, factions, types, canonical identities and unit targets
match frozen v3.6. Seven gold rows change; the other 108 gold values are exact.
All 16 rows #11–20/#75–80 retain their original mechanics apart from #14's
explicitly scoped core-rule correction. No denominator exclusions exist.

Root `qa_gold.json` and frozen `qa_gold_v3.6.json` retain byte SHA-256
`a402aed889eff64f3419d7a6768ff9b168a5912d0bc9c3e92cf225913a7fe3cc`.
Before/after checks cover **all 62 tracked gold/historical-result JSON files**;
every digest is unchanged. The frozen parent is also checked by the profile
loader before limits. Existing loader/CLI/provenance/comparator interfaces are
reused; the evaluator framework and historical results were not rebuilt.

### Changed clauses and primary evidence

The confirmed host `benchmark-freshness/REPORT.md` and `audit.json` were reused;
no web/catalogue research was repeated. All cited primary bytes are already
saved locally. Each revision embeds exact prior/new text, its rationale and
page/section or exact-card locators, linked to the profile catalogue's official
URL, SHA-256, source version and snapshot date.

| ID | Clause and scope | Source locator |
| --- | --- | --- |
| 14 | Failed hit rolls replaced by separate Hazardous rolls after all attacks, per selected Hazardous weapon; D6 1–2 fails for 1 mortal wound. Original S7/AP-2/D1 and S8/AP-3/D2 profiles retained as historical. Unasked roll detail is explanatory rather than a required expansion; false missed-hit causation remains wrong. | Unchanged Core Rules saved 2026-09-14, PDF p81 §24.15 and p24 §06.03. The source's all-Monster/Vehicle 3MW exception was verified, but is not imposed on this Hellblaster firing-mode question. |
| 34 | Khorne Berzerkers T4→T5 only; M8 retained without new full-profile certification. | World Eaters v1.3, saved/legal-from 2026-09-30, PDF p7 named unit-characteristic table. |
| 93 | Cover benefit worsens incoming ranged BS by 1, rather than improving armour saves; Ignores Cover denial, including Stealth, retained. | Same unchanged Core PDF p82 §24.18 and p50 §13.08. |
| 113 | Published Guilliman 355→415, one model; cite September 30 MFM. Published price does not verify full Codex rules or a captured universal legal-start date. | Official space-marines MFM 2026-09-30 HTML, ULTRAMARINES / exact ROBOUTE GUILLIMAN / YOUR UNIT COSTS / 1 model / (+60) 415 pts. |
| 114 | Exact Armour of Antilochus identity, historical 155, one model, September 14; exact current heading absent on all 30 September 30 pages. Both facts required. Current published price/full-body identity resolution unavailable in these sources. | Previous space-marines MFM ULTRAMARINES exact heading; all 30 current heading inventories. Ordinary MARNEUS CALGAR 180 and archived ordinary Calgar 200 are not replacements. |
| 115 | Exact Pedro Kantor identity, historical 80, one model, September 14; exact current heading absent on all 30 current pages. Both facts required; no deletion/Legends inference. | Previous space-marines MFM IMPERIAL FISTS exact heading; all 30 current heading inventories. |
| 118 | CSM130→125, DG110→105; TS110/WE120 retained. All four faction-specific one-model expectations and disambiguation retained for this question. | Four official September 30 MFM UNITS / exact HELBRUTE cards, canonical faction IDs 000000954/000001046/000001021/000002632. |

Relevant exact source hashes (all 37 entries and URLs are in the profile):

- Core Rules: `f6a2443a44627ac5f0ef08407d29aa5ec7e97339998f05bc35f3ae37bf276833`.
- World Eaters v1.3: `93e29f1b166d2a06fafa37a543890e56ae59c712b73b5a1e26f0a1c1ecf6a8e9`.
- September 30 space-marines MFM: `ea31748246aa16270052c994e47edfbbd5dbd5b5f14521414f6c99a708e6f816`.
- September 14 space-marines MFM: `99f45a5032c4862df89529f02a66122897429ccea7280b0fb318335cf23ad884`.
- CSM/DG/TS/WE MFM respectively: `52ca2e41a872469e5efea39aae211db5fbee38839e95693badd4fd3568a04e29`, `90b4a7d2f68b6305905920acf0dca799d0e74d9f1e36c607809155e52c24a0c7`, `23fc92f48bd5e49494fb06cfc36b93e94d6f997b9dc5ae6a4f2dc1b553d08e3b`, `846bad84cc224df9cae3f5c3be40befe989e3d87b88bc9a3e26255bd82ad1666`.

### Dated coverage semantics and validation

The profile has **21** per-item `coverage_contract` entries: #11–20, #34,
#75–80, #113–115 and #118. Sixteen historical-body entries cite the unchanged
Space Marine supplement scope or the three new Legends-only packs. They
require dated historical/cached/base mechanics and explicit lack of complete
current target-body verification as of September 30. `2026-09-16` identifies
the frozen v3.6 expectation date, not a newly certified primary-body date.
An answer may instead cite its actual dated base-source snapshot. #76 explicitly
rejects replacing the original M8/T10 target with the Magna-grapple M8/T9 variant.

The original factual judge and mechanical extraction remain unchanged. After
that judgment, a separate narrow API check returns strict booleans for every
named requirement/prohibition and literal answer quotations supporting positive
claims. Supplied metadata is not answer evidence. Missing claims and API/JSON/
quote errors cannot certify coverage. A qualified check leaves the factual
verdict unchanged; missing/unverified coverage caps it at partial; an affirmative
prohibited identity/current-price/parity claim caps it at wrong. The minimum of
the factual verdict and this ceiling is final, so no wrong/partial answer can
upgrade. This is a semantic model check with fail-closed response validation,
not an independently proven semantic classifier.

Results echo the contract, named checks, status, `factual_verdict` and
`factual_reason`. Ordinary and layered generation apply the ceiling; retrieval
remains unchanged. The summary reports checked/status counts, as-of date and
`full_current_body_verified: false`. The source-aware loader validates full
ordered targets, before/after clauses, official URLs, byte hashes, source
versions/dates, meaningful locators, all required claim IDs, exact coverage
scope and all-30-page historical-price references before any limit. Legacy gold
keeps the original five fields, judge behavior and API call count.

Focused command:

```powershell
& 'D:/Project/py/RAG/.venv/Scripts/python.exe' -m pytest tests/test_qa_bench_source_coverage.py tests/test_qa_bench.py tests/test_qa_bench_gold_selection.py tests/test_qa_bench_provenance.py tests/test_compare_bench_runs.py -q --tb=short
```

Result: **256 passed**, five existing SWIG warnings, including **all 197 prior
gates** and **59 new controls**. The initial profile-specific pre-wiring run
produced 37 failures/3 passes, establishing missing validation/coverage behavior
rather than a production regression. Direct paired worker calls against actual
base `0268450dc3a279bae64da315456793387702ea36` confirm: right stats/missing
qualifier ✅→partial; wrong stats/correct qualifier wrong→wrong; correct both
✅→✅. This changes acceptance, not facts or historical scores.

Tests include actual fake API extraction/judge workers and CLI ordinary/agent/
layered outputs, malformed/unknown/unsupported-evidence responses, right/wrong
stats and missing/correct qualifiers, exact historical Calgar/Pedro facts plus
absence, ordinary 180/archived 200 identity substitution, unqualified historical
current prices, invented Legends status, generic ignorance, #76 variant mixing,
old Guilliman/Helbrute prices with correct qualifiers, duplicates, version/
identity/claim-scope mismatches and same/cross-gold comparator behavior. A
six-worker fake-client CLI run retains all **115** rows and checks all **21**
contracts; a deliberately wrong #11 remains wrong despite all coverage flags
being satisfied. Synthetic responses/extraction fixtures establish plumbing
and monotonic acceptance only; they are neither primary evidence nor a real
benchmark score, and do not establish the real judge's semantic accuracy.

Finite primary checks independently matched **37/37** actual saved byte hashes
and lengths, then **73** PDF clause/exact MFM card/absence probes. These verify
source citations against original saved files, including all 30 pages for each
missing identity. A table-order assumption in the first local probe was
corrected against the actual T5 row listing Khorne Berzerkers; no source or
profile fact was fabricated. No source promotion/application database mutation
occurred. All 62 protected tracked JSON files retain their original hashes.

`py_compile` and `git -c core.whitespace=cr-at-eol diff --check` pass. Tests use
the existing project environment, Python **3.9.1**. The verified Python **3.11.9**
interpreter has no pytest installed; Ruff is absent from the project environment.
Neither packages nor environments were changed. Python 3.11 full-suite and
hosted CI remain root gates, rather than inferred from these focused checks.
The actual implementation/profile/test diff was inspected locally. Independent
code/source acceptance remains root-owned; no delegated review is claimed.

Ignored finite evidence is under this worktree's
`db_sources/release-check-20260930/benchmark-versioning/`: `v37-before.json`,
`v37-red.txt`, `v37-paired.json`, `verify_v37_sources.py` and
`v37-source-verification.json`; final test/diff verification is recorded alongside
them. This report and README provide the project checkpoint and verified
learning/error handoff for root's later deduplicated knowledge publication.
No external repository or unrelated index was edited. No service/background
process, real model/API call, manual stage/commit/push/merge or deployment started.

### Remaining root/GNHF gates

1. GNHF commits the exact candidate; verify the committed bytes/clean status.
2. Root independently reviews the source-backed clause scope and semantic
   coverage prompts, and integrates independently reviewed official-source
   changes. Prices remain staged and do not prove full current Codex bodies.
3. Root executes fresh all-115 `--gold benchmarks/v3_edition11/qa_gold_v3.7_source_cited.json --path agent --workers 6`
   against that integrated runtime, with a judge distinct from production Flash.
   Retain the new result and failures separately; default comparator must refuse
   v3.6→v3.7 expectation equivalence. An explicit cross-gold comparison does not
   establish application improvement/regression.
4. Root completes Python 3.11 full-suite/CI, Docker/live acceptance, deployment,
   release/merge review and applicable knowledge publication. The historical
   source-body limits remain visible until supported by real current evidence.

The owned profile and offline ceiling are reviewable. The whole loop stop
condition is not claimed in this iteration because GNHF has not yet committed
this candidate and root acceptance has not yet reviewed the changed clauses.

## Historical previous-run preparation

Iterations 1–3 completed the immutable baseline, validated Python-loader/CLI
selection, exact-byte output provenance and version-aware comparison. The complete objective remains unfinished. No real benchmark,
source promotion, production mutation, API work, service startup or publication
was performed. GNHF owns commits; none were made manually.

## Iteration 3 — validated, version-aware result comparison

The bounded unit is `scripts/compare_bench_runs.py` and its offline contract
tests. No gold clauses changed. Source-cited v3.7 preparation remains the next
unit; the complete stop condition is not met. Only the comparator, new
`tests/test_compare_bench_runs.py`, this report and benchmark README changed.
The runner and all earlier judge/scoring fixtures remain byte-identical.

Both full result documents validate before counts or verdict transitions print.
Validation rejects duplicate, nonpositive, boolean, string or fractional IDs;
malformed roots/details/summary/rows; missing or blank question/faction/gold;
unsupported gold types; invalid or conflicting verdict axes; malformed declared
provenance; conflicting canonical identities; and declared executed totals
inconsistent with the actual rows. Gold-source total may exceed executed rows
for a limited run. Only the original #63 question/faction/type contract allows
null gold; a supplied conflicting canonical identity still fails. Historical
results may omit that identity field because the old runner did not emit it.
No missing expectation is inferred from an ID, hash or current application.

Default comparison refuses differing ID sets, questions, factions, gold, types,
known canonical identities, available row metadata or declared gold source
version/edition/hash/total/coverage. Every difference prints before exit **2**,
without verdict transitions. `--allow-different-gold` enumerates these same
differences and compares common rows with an explicit statement that the
transitions are **not an application regression claim**. Missing versus null
metadata is visible. Gold paths print but locations alone do not determine
expectation equivalence. Equal claimed hashes cannot override different actual
gold. Invalid inputs and mismatched verdict axes fail even with the override.
Ordinary verdicts and the two layered axes are inspected separately; this adds
no rejudging, scoring changes or benchmark execution.

Historical results without summary provenance remain usable by comparing
actual detailed fields. Absent provenance/metadata/canonical identity is
disclosed as unverified rather than inferred. A modern-to-historical comparison
can establish equal detailed expectations while leaving source equivalence
unverified. Even complete reported provenance is not independent primary-source
verification. Exit **0** means a comparison completed, not all answers passed.

Validation command (existing Python 3.9.1 environment, read-only):

```powershell
& 'D:/Project/py/RAG/.venv/Scripts/python.exe' -m pytest tests/test_compare_bench_runs.py tests/test_qa_bench.py tests/test_qa_bench_gold_selection.py tests/test_qa_bench_provenance.py -q --tb=short
```

Result: **197 passed**, five existing SWIG deprecation warnings. All 131 earlier
loader/CLI/judge/scoring cases remain green; **66 new comparator cases** cover
same expectations, all core-field and source differences, explicit override,
missing IDs, malformed tail rows, both input sides, null #63, known identity
changes/conflicts, metadata absence, malformed provenance, full executed counts,
layered axes and actual historical compatibility. All **58 tracked historical
result documents** pass the strict reader. This is compatibility verification,
not a new benchmark run or fresh-answer assessment.

The initial 50 comparator tests failed against the original implementation.
Some failures concern missing interface/output. Separate direct paired calls
to the actual `HEAD` comparator establish two existing defects without relying
on a new interface: duplicate IDs silently collapse with exit **0**, and changed
gold is accepted with exit **0**. Both inputs now return **2**. The actual
historical same-gold pair `qa_agent_results_same_name_disambig.json` and its
`_run2` result passes with zero verdict differences and explicit unknown
provenance. No historical result was modified.

Ignored finite evidence is under this worktree's
`db_sources/release-check-20260930/benchmark-versioning/`:
`iteration-3-before.json`, `iteration-3-red.txt`, `iteration-3-paired.json`,
`iteration-3-tests.txt`, `iteration-3-historical-validation.json` and
`iteration-3-verification.json`. Before/after hashes cover 67 tracked benchmark
gold/results and owned inputs. Root/frozen v3.6 retain SHA-256
`a402aed889eff64f3419d7a6768ff9b168a5912d0bc9c3e92cf225913a7fe3cc`,
with all 115 ordered IDs/questions/factions/types/canonical identities unchanged.
Only the comparator and deliberately updated documentation differ among the
inventoried inputs. Python compilation and
`git -c core.whitespace=cr-at-eol diff --check` pass. Ruff is unavailable in the
selected environment; no dependencies were installed or changed.
The implementation/test diff was inspected locally. Independent acceptance is
host-owned and remains outstanding. No service/background process, model call,
network access, production mutation, manual commit/push or publication occurred.

This section supplies verified implementation, error reproduction and learning
evidence for the host's later deduplicated knowledge/hook handoff. External
records remain root-owned and outside this iteration's file ownership.
The source-cited v3.7 document, current-source/answer coverage inspection, real
latest 115-question execution, active database alignment, clean Python 3.11 full
suite, Docker/live checks, independent review, integration and publication remain
outstanding. Full current Space Marine bodies remain unavailable as described
below; comparator acceptance does not resolve that source-coverage limitation.

### Iteration 3 local knowledge handoff

The explicit stop-hook request authorized this additional local handoff. Existing
records were searched first. New iteration-3 sections in
`D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` record the actual
comparison behavior, paired failures, 197 passing tests, 58 historical input
checks, preserved gold/scoring and remaining v3.7/host gates. Prior sections and
concurrent source-retirement/official/API owners' content remain intact. The
comparator remains uncommitted/unreviewed; preceding real `2e2e3a9fd` is identified
only as CLI/provenance work. No commit explanation was invented.

The existing learning decision
`C:/Users/Administrator/learn-notes/decisions/20261001-freeze-gold-before-validating-selection.md`
was extended with contract-first comparison and historical-provenance limits;
its README index was updated. The separate underlying comparator error is
recorded once at
`C:/Users/Administrator/error-notes/rag/20261001-error-14-comparator-ignores-gold-contract.md`,
with full paired outputs, actual predecessor revision, reproduction, environment,
repair and validation evidence. Its README index was updated. The earlier loader
error record remains unchanged. No harness promotion is warranted by this
bounded project evidence; no manual staging, commit, push or publication occurred.

Before/after preservation checks in ignored
`benchmark-versioning/knowledge-handoff-iteration-3/` verify retained prior
content, unique entries, unchanged staged diffs in all three knowledge
repositories and unchanged implementation/test/baseline hashes. This handoff
added no application/test changes or new test run.

## Iteration 2 — CLI selection and snapshot provenance

`--gold PATH` selects an absolute or caller-relative file without fallback.
Omitting it resolves the current `QA_SOURCE`. CLI execution reads and validates
the complete selected document before credentials or application resources and
projects the unchanged five-field worker input from that same snapshot. No gold
row or clause changed; v3.7 preparation remains outstanding.

Both ordinary (classic/agent) and layered summaries add `gold_source`, containing
the resolved absolute path, SHA-256 of the exact bytes parsed, version, edition,
full-document total and source-qualified limitations. All old summary keys and
counts remain. `--limit` limits execution only; provenance still describes the
fully validated document. File replacement after loading cannot change the
judged expectations or their recorded hash.

Declared `meta.source_limitations` must be a nonempty list of nonempty strings.
Absent historical declarations produce the explicit limitation: “Selected gold
does not declare source-coverage limitations; numerical agreement alone does
not certify current source coverage.” This does not assert current body parity.
Detailed output in both modes includes the actual `gold`/`gold_type`, plus
`gold_metadata` preserving all other original row fields, including canonical
identity, source notes and any coverage/provenance fields. Extra metadata stays
outside worker/judge input. Layered output previously omitted gold and type;
retaining these fields enables the later comparator to inspect real expectations.

Offline command:

```powershell
& 'D:/Project/py/RAG/.venv/Scripts/python.exe' -m pytest tests/test_qa_bench.py tests/test_qa_bench_gold_selection.py tests/test_qa_bench_provenance.py -q --tb=short
```

Result: **131 passed**, five existing SWIG deprecation warnings, using the
existing Python 3.9.1 environment read-only. All 104 earlier tests remain green;
27 additional cases cover absolute, relative and dynamic default selection,
ordinary classic/agent and layered output, exact CRLF-byte hashes, file replacement
after load, row metadata, selected-gold delivery to actual judge functions,
limited execution/full-document provenance, existing summary keys and fallback
counts, and preserved partial/wrong verdicts and zero accuracy despite normal
completion. Temporary fixture bodies and clients are test data, not source evidence.

The first 18 new cases failed against the actual pre-change CLI: explicit paths
were rejected as unsupported arguments and default output lacked provenance.
Those failures establish the missing interface/output, rather than a new scoring
defect. Paired invalid-file tests now reject missing files, broken JSON, duplicate
tail IDs and empty tail gold in both modes before credentials/resources/output,
even with `--limit 1`. Five additional cases reject malformed declared limitations.

Ignored evidence in this worktree's
`db_sources/release-check-20260930/benchmark-versioning/` includes
`iteration-2-before.json`, `iteration-2-red.txt`, `iteration-2-tests.txt` and
`iteration-2-verification.json`. Before/after hashes cover 68 tracked baseline,
result and owned-input files. Root/frozen v3.6 retain SHA-256
`a402aed889eff64f3419d7a6768ff9b168a5912d0bc9c3e92cf225913a7fe3cc`;
all 115 ordered identities/questions/types and historical results remain unchanged.
Only the runner and deliberately updated documentation differ among those inputs;
the new provenance tests are a separate added file. AST inspection verifies
judge prompts, parsing/mechanical scoring and both worker functions remain unchanged.
Compilation and `git -c core.whitespace=cr-at-eol diff --check` pass. Ruff remains
unavailable; no dependency was installed or changed. The actual implementation
and test diff was reviewed locally. Independent acceptance remains host-owned
and has not run in this iteration. No background process was started.

The next bounded units remain the source-cited v3.7 document and strict,
version-aware comparator. Real 115-question runs, honest-answer/source-coverage
inspection, database alignment, Python 3.11 full-suite acceptance, Docker/live
checks, integration and publication remain host gates. External knowledge/hook
records remain root-owned; this section supplies the verified handoff evidence.
Earlier iteration-1 statements below describe their original scope.

## Preserved historical baseline

Root `qa_gold.json` and the new
`benchmarks/v3_edition11/qa_gold_v3.6.json` are byte-identical, with SHA-256
`a402aed889eff64f3419d7a6768ff9b168a5912d0bc9c3e92cf225913a7fe3cc`.
They retain v3.6, edition 11, all 115 unique ordered IDs, every original question,
faction, gold type, canonical identity, gold clause and note. No row or clause
was revised in this iteration. Root bytes and historical results remain unchanged.
The frozen file has no Git attributes requiring newline conversion, and the
repository reports `core.autocrlf=false`.

Before/after SHA-256 inventory covers 65 tracked gold/result and owned-input
files. Of those files, only `scripts/qa_bench.py` changed in the implementation
check; README documentation was subsequently updated deliberately. All root
and historical gold/result hashes remain equal. The unchanged original test
file and comparator are included in the inventory. Detailed evidence is saved
under this worktree's ignored
`db_sources/release-check-20260930/benchmark-versioning/`:

- `iteration-1-before.json`: original input hashes.
- `iteration-1-red.txt`: failures against the actual pre-change loader.
- `iteration-1-tests.txt`: passing focused suite.
- `iteration-1-verification.json`: post-implementation hashes and AST checks.

## Loader selection and strict validation

`load_questions(limit=None, gold_path=None)` resolves the current `QA_SOURCE`
when omitted. Explicit paths can be absolute or relative to the caller's working
directory; missing/invalid selected files fail rather than using root gold.
Default callers retain precisely the original five fields and row order.
The selected document is read once as bytes, parsed and fully validated before
any limit. The private reader retains those exact parsed bytes and resolved
path for the future result-provenance integration; no provenance output is
claimed yet.

Validation rejects non-object roots/metadata, non-list or empty details,
incorrect v3/edition-11 metadata, mismatched or non-integer totals,
non-object rows, duplicate IDs, nonpositive/non-integer/boolean IDs,
missing or blank factions/questions, unsupported scoring types and missing,
blank or malformed gold. Supported types remain stat, weapon, ability, rule
and points. Only the explicit original #63 null-gold contract, including its
question, faction, type and canonical identity, may use intrinsic judging.

The existing loader previously accepted both a duplicate-ID tail and an
empty-gold tail when `limit=1`. Paired tests reproduce those failures before
the change and now reject both. This preserves scoring strength instead of
silently treating missing expectations as intrinsic.

AST comparison with `HEAD:scripts/qa_bench.py` confirms the only changed existing
function is `load_questions`, and all original module assignments are retained.
The judge prompts, `parse_verdict`, mechanical contradiction/omission logic,
worker modes and result-summary behavior are unchanged.

## Validation

Command, using the existing project interpreter read-only:

```powershell
& 'D:/Project/py/RAG/.venv/Scripts/python.exe' -m pytest tests/test_qa_bench.py tests/test_qa_bench_gold_selection.py -q --tb=short
```

Result: **104 passed**, five existing SWIG deprecation warnings, Python 3.9.1.
The 56 new selection/validation cases originally produced 55 failures and one
pass; all now pass alongside the 48 unchanged parsing/judge/scoring cases.
Tests use temporary JSON files, without model calls or application assets.
Compatibility checks compare every default row to the original loader's
five-field projection of the immutable bytes, test the frozen explicit file,
and retain the original #63 behavior. Invalid tail tests prove validation
precedes slicing. Both absolute and caller-relative selection are covered.

`git -c core.whitespace=cr-at-eol diff --check` passes. Ruff is unavailable in
the selected environment; no package was installed. No formatter configuration
was found among tracked Ruff/pytest/pyproject/setup.cfg paths. No background
process was started. The implementation diff was inspected directly.

## Remaining objective and host gates

The next units must add CLI selection and exact-byte result provenance in both
ordinary and layered modes, prepare the source-cited v3.7 document, and make
comparison reject duplicate/invalid identities and distinguish changed gold
from application regressions. They must retain old downstream summary keys
and historical-result compatibility, and add offline meaningful tests.

The comprehensive source audit at
`D:/Project/py/RAG/db_sources/release-check-20260930/host/benchmark-freshness/REPORT.md`
and `audit.json` is the confirmed basis for future v3.7 changes; this iteration
did not repeat it. Expected revisions remain #34 T, #113 price, #118 two
four-faction prices, #14 Hazardous wording, #93 Cover wording, and dated
exact-identity/source-absence qualification for #114/#115. Source metadata must
cite every changed clause; none is implemented here.

Full current Space Marine bodies for #11–20 and non-Legends chapter bodies
for #75–80 remain unavailable. Historical numbers must remain in all 115 rows,
with per-row source-coverage notes in v3.7. Mechanical stat checks establish
numerical agreement only, and cannot certify date or source qualification.
Neither latest MFM prices nor the three new Legends packs resolve those body
gaps. The frozen file alone supplies no current-source coverage certification.

Independent review, the real latest 115-question execution, active database
alignment, a clean Python 3.11 full suite, integration/deployment, final live
acceptance and GitHub publication remain host-owned gates. No benchmark score,
latest-body parity or final release acceptance is claimed.

## Local knowledge handoff

The iteration-2 stop hook explicitly authorized the local knowledge handoff.
Existing records were searched before writing. New current sections in
`D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` describe the CLI,
same-snapshot hashes/metadata, 131 passing offline tests, uncommitted/unreviewed
status and remaining v3.7/comparator/host gates, preserving earlier sections and
other owners' entries.

The existing learning decision
`C:/Users/Administrator/learn-notes/decisions/20261001-freeze-gold-before-validating-selection.md`
and validation error
`C:/Users/Administrator/error-notes/rag/20261001-error-10-gold-loader-accepts-invalid-tail.md`
were extended and their existing README entries updated. The missing pre-change
CLI/provenance interface is not recorded as a new scoring defect. No duplicate
record, invented commit explanation, manual staging/commit/push or harness
promotion was added. The hook introduced no application/test changes or new
test runs. Preservation checks and unchanged staged-diff hashes are saved under
the ignored `benchmark-versioning/knowledge-handoff-iteration-2/` directory.
The earlier iteration-1 handoff below retains its original scope.

The explicit stop-hook request authorized a local knowledge handoff after the
implementation. Existing notes were searched for duplicates before writing.
The benchmark's separate iteration-1 section was added to
`D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md`, preserving all
previous content bytes and concurrent owners' entries. No commit explanation
was added because this candidate has no real implementation commit yet.

The learning record is
`C:/Users/Administrator/learn-notes/decisions/20261001-freeze-gold-before-validating-selection.md`.
The single underlying validation error is recorded at
`C:/Users/Administrator/error-notes/rag/20261001-error-10-gold-loader-accepts-invalid-tail.md`,
including both actual failing original-API cases, reproduction and verified
resolution. Both repository README indexes link these records. No harness
promotion is warranted by this bounded project evidence.

`knowledge-handoff-integrity.json` in the ignored evidence directory verifies
the original note bytes were preserved and all three knowledge repositories'
staged diffs remained unchanged. No manual staging, commit or push occurred;
later publication and the real-commit explanation remain host/GNHF work.

## Source-cited v3.7 local knowledge handoff

The explicit stop hook authorized this additional local handoff. Existing project, learning and error records were checked for duplicates. New scoped current sections in `D:/Project/devlog/wh40k-oracle/CHECKPOINT.md` and `ROADMAP.md` record the actual115-row profile,21 coverage contracts,256 passing offline checks,37 byte hashes/73 citation probes, baseline preservation and remaining GNHF/root gates. Earlier/concurrent content is preserved. The real predecessor comparator commit `0268450dc3a279bae64da315456793387702ea36` is explained in `commits/20261001-0268450dc-version-aware-benchmark-comparison.md`; no current implementation commit is invented.

The existing learning decision `C:/Users/Administrator/learn-notes/decisions/20261001-freeze-gold-before-validating-selection.md` is extended with the non-upgrading ceiling, literal answer evidence and semantic-judge limits, and its existing index entry is updated. The distinct reproduced dated-coverage acceptance gap is recorded once at `C:/Users/Administrator/error-notes/rag/20261001-error-18-benchmark-source-coverage-not-scored.md`, with full paired outcomes, exact predecessor, reproduction and verified offline resolution. The repeated GBK primary-audit diagnostic extends the existing `common/20260921-error-41-python-stdout-gbk.md` rather than creating a duplicate. Error indexes are updated. No cross-project harness promotion is warranted before root review.

Ignored `benchmark-versioning/v37-knowledge-handoff-integrity.json` checks preserved prior note content, staged diff hashes in all four repositories, unchanged implementation/tests/profile/baselines and unique entries. Only this handoff documentation changed after the recorded256-pass run; no new application/test changes or test execution occurred. No manual staging/commit/push/publication or service occurred. Root owns final knowledge publication and GNHF owns the implementation commit.
