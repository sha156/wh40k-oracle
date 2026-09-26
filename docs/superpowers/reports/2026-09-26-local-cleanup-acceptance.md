# Local Docker tests and Votann source retirement

Date: 2026-09-26. Status: **named source retired and local checks passed; broader source scope awaiting the user's answer**.

The user resumed Docker testing and asked to finish remaining local project work. The latest steering explicitly removes `data/沃坦联盟CODEX-双子星版 V1.30.pdf` and prefers Black Library for Chinese replacement data. A scope question remains pending about removing all other fan-translated Chinese PDFs. This report supersedes the earlier paused September 26 checkpoints; historical failed outputs remain available.

## Named source removal

The PDF and its complete refined-page directory were moved to `archive/source-retirement-20260926/`, outside active source directories. Before mutation, the existing FAISS store and SQLite database were copied into that excluded archive. The original PDF SHA-256 is `bca401f19514354e91d2dd3cc44fdbf2b4effdc705c52776e67ef941f850283d`.

Exactly **73 source-attributed chunks** were removed: 5,754 to **5,681**. Every retained document, metadata value and vector was compared with the backup and is unchanged. Its incremental-processing key was removed. The database is byte-identical to its backup. A copied-database alias rebuild produces the same 705 refined aliases: the Votann file's harvested headings had not supplied valid unit aliases. No Votann term-pair or faction name patch in the audited pipelines points to this PDF. Current Votann wiki cards are rendered from the structured database/Black Library, so canonical units were preserved rather than deleting the faction.

`corpus_policy.json` records the retired stem. PDF ingestion, refinement, cached Markdown loading, entity extraction, alias harvesting, database term-name restoration and cached wiki synthesis all consult the policy. The comparison handles Windows and Unix paths and `.PDF` case variants. Missing or malformed policy fails rather than silently restoring blocked inputs. The PDF/refined archive and runtime assets are ignored by Git and Docker.

Evidence: [retirement audit](2026-09-26-votann-source-retirement.json). Scope is the named PDF, not all other translators. The remaining inventory includes 27 Chinese PDF candidates, including the June translated points/balance files and the community keyword quick reference. The latter also feeds keyword classification, and other codices feed aliases/names, so broader retirement needs those derived consumers reconciled as well. Official GW Chinese PDFs remain eligible. A fresh Votann fallback still retrieved the separate June points PDF, confirming why a broader removal must not be claimed yet.

## Application fixes and checks

The coordinated source task completed independently reviewed fixes for historical/current Calgar identity, preservation of earlier verified evidence after later misses or step limits, malformed source handling, roster constraints/pricing, simulator composition counts and stale frontend responses. The final formatter change permits a unique short dotted Chinese name while keeping ambiguous row identities fail-closed. This task added source-retirement guards and three delivery E2E tests, then inspected their diff and ran the relevant suites.

| Check | Result |
| --- | --- |
| Retirement/ingestion/refinement/alias/wiki focused suite | 100 passed |
| Full native suite | **2,687 passed**, 19 existing warnings, 188.80 seconds |
| Frontend unit tests | **22 passed** |
| TypeScript and ESLint | Passed |
| Real Chrome E2E | **12 passed**, 43.3 seconds |
| Download delivery | Actual downloaded Markdown bytes retain prose, citations, AI/unreviewed label and exact JSON answer snapshot |
| Clipboard | Actual clipboard text verified; simulated denial exposes selectable text |
| Deployed source verification | **117 files match** the workspace exactly |
| Required assets and model warmup | Ready; warmup done; no warmup error |

Logs: `pytest-retirement-final-20260926.log`, `e2e-retirement-final-20260926.log`, `docker-build-retirement-final-20260926.log` (ignored runtime files). The E2E run used the same source semantics immediately before a line-ending-only API rebuild. Web source and its deployed image were unchanged. API image: `sha256:40652df2a692db43d7ffd26195999457066ce2529bf088134d240014af3523b2`; web image: `sha256:5156e1f53e6792b1f3de10da01106b885c5ba36e790c2a50cdaa48b2997cedda`. [Source/health verification](2026-09-26-retirement-source-verification.json).

## Live response limits

Three fresh ordinary-Calgar/Guilliman comparisons retain historical ordinary Calgar 200 and official-snapshot Guilliman 355, with the two-guard identity distinct from the Armour variant. Two format normally; one safely falls back to complete upstream prose. All three individual point queries format normally, including Armour Calgar 155. Correct numbers do not establish arbitrary factual correctness; this is a scoped acceptance, not a new full 115-question model benchmark. The official points snapshot is still September 14.

The first Votann probe used an unsupported Chinese name and fell back to retrieval. It did not retrieve the retired PDF, but did retrieve a different translated points document. These results are preserved under `2026-09-26-accepted-live-*.json`; the filename denotes this acceptance run and does not claim every response passed every quality gate. [Batch summary](2026-09-26-accepted-live-summary.json).

The canonical-name Votann follow-up (Hearthkyn Warriors / 炉心战士) returned HTTP 200 with `degraded=false`, 10 models at 90 points from the September 14 MFM snapshot, and a populated structured card. Its prose still broadly describes the merged card as the structured database instead of tracing each translated line to Black Library; field-level Chinese provenance is not established by that answer. [Response](2026-09-26-accepted-live-votann-canonical.json).

Application changes are committed as `fc84793b5` (Fix answer provenance, roster validation and retired-source ingestion). Publication/CI status is recorded separately after push.

## Remaining source work

- Black Library resumed from the copied September 22 snapshot: 1,171 accounted-for records, 1,071 full details, two explicit empty details, 98 unresolved. All 1,180 raw and seven output hashes match. The observed full-unit request uses English names; 94 missing names and four identity mismatches remain unresolved. No canonical promotion was performed. See [capture audit](2026-09-26-blacklibrary-capture-audit.md).
- A public [Dreadherder preview](https://www.warhammer-community.com/en-gb/articles/fvsvtvtu/build-a-better-waaagh-warhammer-community-cooks-up-their-ideal-ork-armies/) was located. Integration was superseded by the user's source-cleanup request and remains pending; it must be labelled preview, not verified released-codex coverage. No new Ork rules were imported. The existing public Ork Faction Pack matches the local PDF and does not close Gunwagon/Runtherd full-card gaps or the outstanding enhancement set.
- Broader fan-PDF removal awaits scope clarification. Do not describe the whole corpus as cleaned while other fan sources remain active.
- Docker Desktop host-restart durability, cloud deployment and automatic promotion of AI answers into the official wiki remain unverified/deferred. Container recreation and current readiness do not establish host-reboot durability.
- PR #75 remains the publication target; no merge is authorized or claimed by this report.
