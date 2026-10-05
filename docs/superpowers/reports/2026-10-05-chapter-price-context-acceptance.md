# Chapter price context acceptance, October 5

## Iteration 1: shared canonical projection and check

The six Black Templars canonical rows now select their exact retained chapter
tiers in the shared MFM application/check path. This is a source-code correction
verified on disposable copies, with no active database or asset promotion.
Roster context and bidirectional canonical selector binding remain the next
iteration. No complete release, deployment or full-book acceptance is claimed.

The starting branch is `codex/release-context-points`, parent
`fff4d974ceabb2d8b45126e42f346ec1f975a417`. GNHF owns the subsequent commit;
this iteration made no commit, network request, installation, model invocation,
Docker action or GitHub action. Existing services and orchestrator notes were
untouched. No background process was started.

## Correction and boundaries

`mfm._canonical_rows` selects independently for every same-name canonical row,
using the full canonical name, SM faction and the ordered faction keyword
array. Exact recognized chapter identities select that chapter page. The
original generic-page priority and non-SM matching remain in place; no name
alias, plural or diacritic override was added. Invader ATV remains explicitly
unmatched under the exact SM source identity rule, rather than acquiring a new
invented binding.

The shared helper rejects unknown, multiple, mixed, malformed and missing
chapter identities. SQL NULL in a real keyword column is unresolved. Only
legacy schemas without that column retain compatibility. Existing generic
test fixtures now supply explicit Adeptus Astartes identities; previous
assertions are retained and generic-page priority additionally requires a
nonzero comparison count.

Chapter tiers must agree with their exact source head and receipt, supplied by
the current snapshot or the complete retained ledger. Chapter provenance stores
the source slug, page URL, hash, capture and source section. Receipt reads are
cached once per source slug. Selection preserves ordered base, repeat and paid
option rows; options do not enter canonical base prices. Check still reports
base numeric comparisons, and separately reports complete chapter
tier/provenance differences and unmatched context. Snapshot sync passes its
current source metadata to both application and check; a chapter context
difference prevents convergence. An unmatched identity remains explicit and
does not regain a verified current marker through snapshot application.

| Exact BT canonical ID | Unit | Base | Repeat | First repeat occurrence |
| --- | --- | ---: | ---: | ---: |
| 000002786 | Impulsor | 70 | 80 | 4 |
| 000002787 | Gladiator Lancer | 165 | 185 | 3 |
| 000002788 | Gladiator Valiant | 145 | 165 | 3 |
| 000002789 | Gladiator Reaper | 165 | 185 | 3 |
| 000002790 | Repulsor Executioner | 265 | 285 | 3 |
| 000002791 | Repulsor | 190 | 210 | 3 |

All six preserve the repeat-tier `per Multi-melta` +10 row; Impulsor also
preserves `per Orbital Comms Array` +10. Generic Executioner retains its
different `per Heavy Laser Destroyer` option. These checks establish pricing
evidence, not body, model-composition or equipment legality.

## Paired evidence and preservation

Evidence root:
`D:/Project/py/RAG/db_sources/chapter-price-context-owned/20261005/iteration-01/`.
`checks.json` records exact file/log/XML hashes, test counts and parent-code
verification. `parent-fff4.zip` and `parent-exact-fff4/` contain the Git-exported
parent code; every archived `db_compile` source was compared byte-for-byte with
the exact parent revision. Parent and candidate run the same byte-identical
test module, same ordered 15 test nodes and independently copied AFB databases.
The frozen parent XML contains those 15 nodes. The frozen candidate XML
contains 160 nodes, with the same 15 as its first module; `checks.json`
reconciles that ordered subset. Earlier standalone candidate XML also records
15 passes, before the final extra preservation assertions.

| Validation | Result |
| --- | --- |
| Frozen exact parent, dedicated pair | 11 failed / 4 passed / 0 errors / 0 skips |
| Frozen candidate, same 15-node module subset | 15 passed / 0 failures / 0 errors / 0 skips |
| Candidate existing and new related suite | 160 passed / 0 failures / 0 errors / 0 skips |
| Python compilation and Python 3.9 grammar | Pass |
| Original-CRLF-aware Git whitespace check | Pass |

The four parent passes are the existing transaction behaviors: late direct
and snapshot failures roll back for both RuntimeError and a custom
BaseException. The eleven parent failures demonstrate numeric selection,
full tier/provenance, NULL/mixed/unknown identity, removed paid option,
keyword-order and wrong-receipt defects. They do not rely on a new function
signature. Earlier diagnostic failures are retained: `parent.log` contains
the initial eight failures; `candidate.log` contains 63 passes and the
intermediate replay-reporting failure, corrected before final acceptance.

The related suite is, in order: `test_mfm_chapter_context.py`,
`test_db_compile_mfm.py`, `test_mfm_sync.py`,
`test_source_only_price_identity.py`, `test_price_selector_roundtrip.py`,
`test_roster_surcharges.py`, and `test_db_compile_calc_points.py`.
It uses the supplied stable full-stack Python 3.11 executable:
`D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`.
All pytest temporary output and XML/logs are under the owned evidence root.
No configured Python formatter/linter is present; the supplied interpreter
does not have Ruff, mypy, pylint or Black. No dependency was installed.

Narrow copied applications filter the unchanged snapshot to the six exact
names on the generic and BT pages. Both page orders produce the correct six BT
rows. All six generic neighbors and every other canonical row retain exact
price JSON. Whole-unit-row comparisons also preserve every other column,
including ordered keywords. Every non-unit table is exact, including all
3,635 official ledger rows. Replay changes zero unit prices and preserves
the already accepted JSON. A removed Multi-melta tier is detected even when
the base value remains correct. Wrong source tiers and uncertain identities
are explicit unmatched results, with their prior price JSON untouched.

The original active DB remains SHA-256
`afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`.
The retained BT HTML remains SHA-256
`f819675c38d99f84673696604eff78d54863cc0f4a7b5f4457291e89909bae7d`.
Its capture is `2026-10-03T19:00:56.192123+00:00` (the cached equivalent
`2026-10-04T04:00:56.192123+09:00` is preserved verbatim).
The generic HTML and complete source cache are hash-checked before/after each
copied trial. The existing complete 3,635-row source audit is reused; no
30-page download or source inventory is repeated.

## Independent review and remaining work

Independent code, Python and database reviewers approved the shared
projection/check scope after the reproduced NULL-identity issue was fixed.
Python independently ran 71 related tests with no failures/skips; database
review independently confirmed direct/snapshot BaseException rollback and
indexed chapter receipt selection. Review evidence is under the sibling
`code-review/`, `python-review/` and `database-review/` directories. The
existing test file retains its original Git CRLF bytes; use
`git -c core.whitespace=cr-at-eol diff --check` for its whitespace validation.

Next iteration must bind the same exact chapter identity to roster routing and
canonical source selector matching, preserve ambiguous shared detachment
names, add the actual roster/API option-occurrence totals and direct
canonical/agent/card acceptance, and obtain final independent consumer
reviews. Required reviewed one-Multi-melta boundary totals remain 300, 525,
465, 525, 825 and 600; this iteration does not claim those consumer acceptance
cases are complete. Asset promotion, clean intended commit verification and
root publication remain pending. The loop stop condition is not met.

The append-only checkpoint/roadmap, existing learning decision and underlying
error handoff are listed in `iteration-01/knowledge-handoff.json`. Existing
bodies and staging were preserved; these local notes await root publication.

## Iteration 2: roster consumers and bidirectional selector context

The remaining consumer correction is accepted on disposable actual-asset
copies. Exact BT canonical entries establish a roster chapter context even
when the name-only detachment lookup cannot do so. Generic Adeptus Astartes
entries can follow that verified context, while generic-only rosters retain
their generic source prices. The six copied canonical, agent and English card
base prices agree with the table above. Actual `validate_roster` API calls
agree with independently checked engine occurrence totals:

| Canonical ID | Entries | One Multi-melta per entry, total |
| --- | ---: | ---: |
| 000002786 | 4 | 300 |
| 000002787 | 3 | 525 |
| 000002788 | 3 | 465 |
| 000002789 | 3 | 525 |
| 000002790 | 3 | 825 |
| 000002791 | 3 | 600 |

The source repeat thresholds remain fourth Impulsor and third of the other
five units. Options apply only in their retained repeat tiers. Both Impulsor
options, paid weapon counts, firing-profile names, known free weapons and API
duplicate loadout merging are checked. Two-model Lancer entries remain
unpriced; weapon/occurrence charges do not become model counts or base prices.
These numeric tests do not certify army, body, composition or equipment legality.

`canonical_price_identity` retains named chapter identity separately from its
price-page route; `canonical_price_slug` preserves its existing signature and
direct price routing. The independent code reviewer reproduced and prompted
a fix for a real intermediate defect: Ultramarines shares the generic price
page but cannot join BT as if its chapter were unspecified. BT/Ultramarines,
Ultramarines/White Scars, BT/Blood Angels and conflicting exact detachment
ties now fail closed. Unknown, NULL, missing or mixed faction identities
also remain unpriced. The selector guard uses the same identity helper in
both directions, rejecting a BT ID for generic source intent and a generic
ID for BT source intent. All six unqualified names remain six-source ambiguous;
explicit source selectors preserve their full ordered ledger evidence and
their price-only/effective-date qualifiers.

Roster chapter selection reads an exact full head from the retained ledger,
in ordinal order, preferring the actual primary source section. Complete
tiers must satisfy the existing source receipt guard. Missing source heads
return no price. No fuzzy, plural, diacritic or apostrophe repair is used.
The actual Marshal's Household/Living Miracle and shared Ironstorm/Stormlance
name-only routes still return no chapter. A separately labeled synthetic-copy
control supplies the exact retained ASCII `MARSHAL'S HOUSEHOLD` name to prove
the positive unique-detachment route and its named-chapter conflict guard;
no production detachment metadata was repaired or promoted.

## Final paired acceptance and independent review

Evidence root:
`D:/Project/py/RAG/db_sources/chapter-price-context-owned/20261005/iteration-02/`.
`verify_acceptance.py` and `checks.json` bind the final source/test hashes,
log/XML hashes, preserved asset hashes and public signatures. A complete Git
export of exact `fff4d974ceabb2d8b45126e42f346ec1f975a417` is preserved in
`parent-fff4.zip` and `parent-exact-fff4/`; all exported files are exact against
the archive except the two intentionally added paired test modules. Those
modules are byte-identical to the candidate tests. Parent and candidate use
independent disposable DBs and the same ordered 59 meaningful acceptance nodes.

| Final validation | Result |
| --- | --- |
| Exact parent, frozen same 59 nodes | 50 failed / 9 passed / 0 errors / 0 skips |
| Candidate, ordered matching 59-node subset | 59 passed / 0 failures / 0 errors / 0 skips |
| Candidate complete related suite | 214 passed / 0 failures / 0 errors / 0 skips |
| Independent code review, narrow modules | 148 passed / 0 failures / 0 errors / 0 skips; approve |
| Independent Python review, final modules | 99 passed / 0 failures / 0 errors / 0 skips; approve |
| Independent database review | 70 passed / 0 failures / 0 errors / 0 skips; approve |
| Compilation, Python 3.9 grammar, public signatures, Git whitespace | Pass |

The final related suite runs, in order, `test_mfm_chapter_context.py`,
`test_chapter_price_consumers.py`, `test_db_compile_mfm.py`, `test_mfm_sync.py`,
`test_source_only_price_identity.py`, `test_price_selector_roundtrip.py`,
`test_roster_surcharges.py`, `test_db_compile_calc_points.py` and
`test_roster_faction_validation.py`, using the supplied full-stack Python 3.11.
The six direct canonical/agent/card cases and six actual roster/API cases are
separate tests, so parent provenance failures cannot short-circuit API evaluation.
The nine passing parent controls retain rollback, generic-only routing and
invalid option-count behavior.

Two existing synthetic fixtures now explicitly identify Adeptus Astartes:
the source-only canonical identity and roster faction validation fixtures.
Their original assertions remain unchanged. No old test/gold was weakened,
no new skip was added and no dependency or formatter was installed. Earlier
logs/XML remain intact, including the initial new-module import error, the
overbroad synthetic detachment update's unique-constraint error and the
missing-identity fixture failures. A first parent copy command used its own
relative paths and reported a self-copy error; it was corrected with an
absolute worktree source before the frozen byte-identical pair. Supplemental
review runs had pre-existing relative-asset skips; they are not counted in
the no-skip actual-copy acceptance above. The independent code review's first
source-only failure occurred before the concurrent fixture correction loaded;
its final narrow rerun and retained standalone rerun pass. The test-only split
after review has a final independent code-review addendum; runtime source
hashes remain the approved values.

All six generic neighbors and every unrelated canonical row/column remain
exact under narrow copied apply and replay. All non-unit tables, including
all 3,635 lossless ledger rows/receipts, remain content-exact. Both source-page
orders, complete tiers/provenance, removed-option detection, late failure and
custom BaseException rollback, and zero-change replay remain in the final
paired module. Roster and consumer reads preserve copied DB bytes. The active
DB is still SHA-256
`afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`;
the retained BT HTML is still
`f819675c38d99f84673696604eff78d54863cc0f4a7b5f4457291e89909bae7d`.
The retained generic HTML and complete MFM cache pass before/after fixture
hash checks. The existing complete 3,635-row audit is reused.

## Handoff and remaining release boundary

This iteration began at the real GNHF commit
`4587efeda330585602083bd8e91bbcbb655f2d9c`, which contains the preceding shared
apply/check correction despite its knowledge-handoff subject. The new consumer
source/tests/report are reviewable and uncommitted; GNHF owns their commit.
Root must inspect that actual resulting commit and clean intended tree, then
promote only a final accepted copy under its separate integration ownership.
No commit was made here. The full loop stop condition is not yet met because
the intended clean commit and root publication/promotion are pending.

No active DB/wiki/index, raw HTML, ledger or cache was modified. No network,
model, installation, Docker, GitHub or service action occurred; all started
test/export processes completed. Orchestrator notes and concurrent owners'
work remain untouched. Append-only existing project checkpoint/roadmap,
learning decision and underlying error handoffs are recorded in
`iteration-02/knowledge-handoff.json`; no new duplicate issue note is created.
No whole-project, deployed, full-book or effective-date claim is made.
