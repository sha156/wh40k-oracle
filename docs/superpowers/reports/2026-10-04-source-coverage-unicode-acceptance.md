# Source coverage Unicode identity acceptance

Verified on October 5, 2026 against parent `e7c12cc6690effab0811588ac8b67e81f288db31`. This is a finite identity-guard correction, not a release, body certification, registry promotion or deployment. The pre-existing `codex/release-coverage-unicode` branch points at that exact base; GNHF is operating on `gnhf/objective-correct-th-2d20ee`. No branch history was rewritten and no commit was made by this iteration. Prior chronology proofs and concurrent owners' files remain preserved.

## Result and implementation boundary

SQLite's default `lower()` leaves accented capitals unchanged. Two predicates in `db_compile/source_coverage.py::_check_identity` therefore classified the same complete Unicode name differently from the existing source-only `casefold()` key. A null-ID declaration could evade an existing canonical body, while a declaration using its exact canonical ID and stored name falsely failed published-price provenance.

Both predicates now retrieve names inside their original exact SQL faction boundaries and compare complete names using Python `casefold()`. The published ledger query also retains `kind='unit'`. Any fold-equivalent canonical row excludes source-only coverage before metadata creation. Every matching ledger tier contributes to the full provenance set; no arbitrary first-row selection occurs. Duplicate canonical matches do not select an ID. Canonical declarations still require their explicit ID, literal stored name, exact faction and ordered keywords.

There is no fuzzy matching, singular/plural conversion, accent removal, punctuation/whitespace normalization, schema change, global collation or connection function. Names, parser, ledger rows, canonical IDs, price projections, statuses and dates are unchanged. AST comparison confirms the entire canonical branch, faction/chapter guards, signatures and every other function remain exact against the parent, including history validation before the body shortcut, transitions, exact prior guards, savepoints and `BaseException` cleanup.

## Actual five conflicts

Read-only frozen database SHA-256: `afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`. The retained raw MFM snapshot is `D:/Project/py/RAG/db_sources/mfm/snapshots/fetch-jtgkljt3/`; all 30 page hashes are verified and the complete parsed ledger equals all 3,635 database rows.

| ID | Literal canonical name | Literal published name | Retained price tiers |
| --- | --- | --- | ---: |
| 000004201 | Berehk Stornbröw | BEREHK STORNBRÖW | 1 |
| 000002597 | Brôkhyr Iron-master | BRÔKHYR IRON-MASTER | 1 |
| 000002603 | Brôkhyr Thunderkyn | BRÔKHYR THUNDERKYN | 4 |
| 000002594 | Kâhl | KÂHL | 1 |
| 000002622 | Khârn The Betrayer | KHÂRN THE BETRAYER | 1 |

The bounded verifier authenticates these five stored IDs, names, factions and ordered keywords against the saved conflict inventory; all eight tier rows, raw hashes and capture receipts match. For every name, actual SQLite lower values differ and complete Python casefold values agree. The exact parent rejects canonical published-price provenance and falsely admits the corresponding source-only identity. The candidate rejects each null-ID declaration with `Source-only identity already has a canonical body` while all 19 original tables and metadata absence remain unchanged.

On one owned AFB copy, five canonical declarations plus the two actual prepared source-only declarations (`KAIUS KONORIUS`, ordinary `MARNEUS CALGAR`) apply and resolve correctly. Canonical body declarations are explicitly synthetic identity controls using a `fields_only` keyword scope; citing a price receipt does not authenticate a body, keyword membership, unavailable/newer body or full consumer category. They are never published. Real source-only declaration dates remain null and no canonical body is attached. Exact replay makes zero row changes, late wrong-hash rejection preserves accepted metadata/history, and caller rollback restores all 19 tables and the entire private file byte-for-byte to AFB. No actual registry write occurs.

## Tests and independent review

The identical 47-node Unicode matrix on the exact parent yields **13 failures / 34 passes / zero errors / zero skips**. These failures include all five canonical-positive and five source-only-exclusion cases, full multi-receipt provenance, duplicate canonical handling and late-batch preservation. After correcting a synthetic fixture query that accidentally selected its just-added enhancement row, the same candidate matrix passes **47/47**. Earlier failed logs are retained without replacement.

The complete bounded candidate command passes **444 tests / zero failures / zero errors / zero skips**, XML-accounted:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe' -B -X utf8 -m pytest tests/test_source_coverage.py tests/test_source_coverage_transitions.py tests/test_source_coverage_same_date.py tests/test_source_coverage_legacy_history.py tests/test_source_coverage_unicode.py tests/test_source_coverage_consumers.py tests/test_source_coverage_calculations.py tests/test_qa_bench_source_coverage.py -q -p no:cacheprovider --basetemp='D:/Project/py/RAG/db_sources/source-coverage-unicode-owned/20261004/iteration-02-temp' --junitxml='D:/Project/py/RAG/db_sources/source-coverage-unicode-owned/20261004/iteration-02-tests.xml'
```

Adversarial controls retain rejection of different accents, decomposed accents, titles, singular/plural changes, bare variants, whitespace and punctuation changes, canonical uppercase substitutions, wrong IDs/factions/chapters/keywords and wrong hashes/captures/receipt URLs. Synthetic extra case-equivalent tiers require every receipt; enhancement rows and other factions cannot contaminate unit provenance. Existing same-date, legacy history, cancellation, transition and consumer controls also pass. The one warning is the existing unrelated invalid escape in `engines/simulator/_spike_allocation.py`.

Independent generic and Python reviewers both return **APPROVE**, with no actionable findings. Each independently runs all 47 Unicode tests with zero skips. Both modified Python files compile and `git diff --check` passes. Ruff, mypy, pylint and Black are unavailable in the specified interpreter; no packages are installed. Root host review, the GNHF commit and later publication remain pending.

## Preservation and evidence

All **82 protected inputs / 413,900,574 bytes** match the saved prior hashes before and after the verifier. All original table schemas, counts and content digests remain exact. Only the intended production module, narrow test module and this new report are changed in the checkout. Shared knowledge handoff appends verified findings to existing exact-identity and coverage-history decisions and records one underlying SQLite Unicode issue; concurrent note bodies and shared indexes are preserved for root publication.

Evidence directory: `D:/Project/py/RAG/db_sources/source-coverage-unicode-owned/20261004/`.

- `iteration-02-tests.log` and `iteration-02-tests.xml`: 444-node bounded candidate acceptance.
- `iteration-02-parent-tests.log` and `iteration-02-parent-tests.xml`: identical 47-node parent matrix.
- `iteration-02-parent-source-coverage.py`: exact parent module, SHA-256 `5c7967d33eb4ff499a235de20b54150d1d903950867fe53f82bcceeeaaf033e9`.
- `verify_iteration_02.py`, `iteration-02-actual-verification.log` and `iteration-02-actual-verification.json`: read-only receipts, private-copy identity/replay/rollback and AST/preservation results.
- `iteration-02-afb-copy.sqlite`: private trial, rolled back byte-exact to AFB.
- `iteration-02-review.txt`: both independent reviewer verdicts and validation.
- `iteration-02-final-accounting.json`: final XML/hash/diff accounting and knowledge handoff locations.

Candidate production module SHA-256: `0ee46f8504be76d29c8846ea2d2ea3af93bb83b5324c6eb4ae8757007b2e4a3e`. The inherited failed fixture run and the verifier's initial list-to-`ast.dump` diagnostic are retained; neither changed actual assets. No network, model, full native suite, Docker, browser, service, active-asset copy or installation is involved. No background processes remain. The entire stop condition is not claimed because the orchestrator commit and root host acceptance are still outstanding.
