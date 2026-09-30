# Versioned benchmark preparation acceptance — October 1, 2026

Iteration 1 completes only the immutable baseline and validated Python-loader
selection. The complete objective remains unfinished. No real benchmark,
source promotion, production mutation, API work, service startup or publication
was performed. GNHF owns commits; none were made manually.

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
