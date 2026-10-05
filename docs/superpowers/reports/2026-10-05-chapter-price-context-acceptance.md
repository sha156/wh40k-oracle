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
