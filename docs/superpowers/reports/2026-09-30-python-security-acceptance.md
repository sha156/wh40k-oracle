# Python dependency security acceptance — September 30, 2026

Status: **incremental candidate, not release acceptance**. Iteration 1 patches the
shared FastAPI/Starlette dependency boundary. The complete CPU application stack,
full native suite, Docker/Linux installation and final audit remain outstanding.
No integration, deployment, source retirement or main-environment changes occurred.

## Scope and installed versions

Workspace: `C:/Users/Administrator/.codex/worktrees/release-python-security/RAG`,
branch `codex/release-python-security`. New interpreter:
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/.venv/Scripts/python.exe`,
created with the existing **CPython 3.11.9** executable. Main's legacy environment
and running Docker services were untouched. This iteration installed the lightweight
server set, then separate test dependencies; the full model stack is not installed.

| Distribution | Deployed audit baseline | Installed candidate | Reason |
| --- | --- | --- | --- |
| FastAPI | 0.128.8 | 0.133.0 | First upstream release supporting Starlette 1.x |
| Starlette | 0.52.1 | 1.3.1 | Includes all five distinct deployed Starlette advisory fixes |
| Pydantic | 2.12.5 | 2.12.5 | Existing server pin remains compatible |
| Uvicorn | 0.39.0 | 0.39.0 | Existing server pin remains compatible |
| Requests | 2.32.5 | 2.32.5 | Unresolved finding retained for the next bounded patch |
| setuptools | 79.0.1 | 65.5.0 | Candidate version is Python 3.11 venv bootstrap tooling; unresolved |

FastAPI and Starlette are pinned identically in `requirements.txt`,
`requirements-docker.txt` and `requirements-server.txt`. `requirements-ci.txt`
inherits the server pins. No application imports or API behavior were edited.
Other requirements remain at their previous declarations; this is **not yet a
fully pinned or fully audited reproducible application dependency set**.

The [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/#01330-2026-02-24)
identify 0.133.0 as the first release supporting Starlette 1.0.0+; registry metadata
confirms `starlette>=0.40.0` with no `<1.0.0` ceiling. This smaller upgrade avoids
unrelated changes in the newer 0.142.2 candidate. Both patched packages require
Python >=3.10; Python 3.9 is unsupported. Their published wheels are platform-neutral,
but the Linux application install has not been run here.

## Advisory evidence and reachable behavior

The deployed audit has ten Starlette records representing **five underlying
advisories**, after grouping duplicate GHSA/CVE alias records. Maintainer advisory
JSON was fetched using the existing authenticated GitHub CLI. Tagged
[Starlette release notes](https://github.com/Kludex/starlette/blob/1.3.1/docs/release-notes.md)
independently confirm the fixes.

| Underlying advisory | Fix release | Application evidence |
| --- | --- | --- |
| [GHSA-86qp-5c8j-p5mr](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr), CVE-2026-48710 | 1.0.1 | `web_api/ratelimit.py` reads `request.url.path`; forged Host bypass reproduced before and prevented after |
| [GHSA-jp82-jpqv-5vv3](https://github.com/Kludex/starlette/security/advisories/GHSA-jp82-jpqv-5vv3), CVE-2026-54282 | 1.3.0 | Direct ASGI Request probe confirms malformed path cannot replace URL hostname after upgrade |
| [GHSA-wqp7-x3pw-xc5r](https://github.com/Kludex/starlette/security/advisories/GHSA-wqp7-x3pw-xc5r), CVE-2026-48818 | 1.1.0 | No `StaticFiles` use found in `web_api`; package is patched without relying on that scope limitation |
| [GHSA-x746-7m8f-x49c](https://github.com/Kludex/starlette/security/advisories/GHSA-x746-7m8f-x49c), CVE-2026-48817 | 1.1.0 | No `HTTPEndpoint` use found in `web_api`; package is patched |
| [GHSA-82w8-qh3p-5jfq](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq), CVE-2026-54283 | 1.3.1 | No `request.form()` use found in `web_api`; package is patched |

Two isolated environments ran the same offline Host probe against the unchanged
application rate limiter. With FastAPI 0.128.8 / Starlette 0.52.1, normal requests
returned **200, 429**, while Host `testserver/healthz?ignored=` returned **200, 200**
and reported URL path `/healthz` for actual path `/protected`. With FastAPI 0.133.0 /
Starlette 1.3.1, both sequences returned **200, 429**, and the forged request reported
`/protected`. The direct malformed ASGI path `@attacker.invalid` changed hostname
to `attacker.invalid` before; after, hostname stays `localhost` and the URL path is
`/@attacker.invalid`. This direct ASGI probe does not establish what a particular
HTTP server accepts as a malformed request target.

Starlette 1.0 removed several registration APIs. The application already uses a
lifespan context manager; FastAPI's `@app.middleware("http")` compatibility wrapper
still works in the installed candidate. No compatibility shim was needed.

## Validation actually completed

- Clean server install into the new Python 3.11.9 `.venv` succeeded; installed
  inventory and pip installation report are retained. `pip check` passed both
  before and after installing test dependencies.
- Existing focused suite: **69 passed, 28 skipped, 3 warnings in 2.94 seconds**:
  `test_web_api_stage3.py`, `test_web_api_stage4_sim.py`,
  `test_web_api_stage5_deploy.py`, `test_web_api_round3_audit_fixes.py`.
  All skips are missing `db/wh40k.sqlite` assets; no copied database or asset
  junction was introduced. Tests and expectations were unchanged.
- Test-only additions to the candidate environment: pytest **9.0.3**, HTTPX
  **0.28.1**, PyMuPDF **1.26.7**, plus their resolved dependencies. These installs
  do not constitute production requirement updates. Starlette emits a deprecation
  warning for HTTPX TestClient usage; functionality passed, so no HTTPX2 migration
  was introduced solely to remove the warning.
- A fresh-process lightweight smoke entered the actual application lifespan,
  returned `/healthz` **200**, `/openapi.json` **200**, invalid `/chat` input **422**,
  and loaded none of torch, sentence-transformers, FAISS, LangChain or Streamlit.
  `WEB_API_RETRIEVAL=off`, `WEB_API_WARMUP=0`; no inference or LLM calls ran.
  Preflight correctly reported the absent canonical database.
- Initial Windows stdout encoding was GBK and preflight printing raised
  `UnicodeEncodeError` for U+21B3. Repeating with `PYTHONIOENCODING=utf-8` passed.
  No reliability-owned file was changed; this is a terminal environment limitation,
  not evidence of a dependency regression.
- Actual requirement diff inspected; `git -c core.whitespace=cr-at-eol diff --check`
  passed. No background services were started; in-process TestClients closed.

No full native suite, complete CPU installation, asset-backed retrieval test,
Docker build, Linux install, benchmark or browser acceptance is claimed.

## Fresh audit and remaining scope

Audit tool **pip-audit 2.10.1** lives in a separate ignored environment,
`db_sources/python-security/audit-venv`. It audited all **26 distributions** in the
server install inventory, including pip and bootstrap setuptools, using exact
installed pins with `--no-deps --disable-pip`. These flags prevent re-resolution
of an already enumerated tree; no runtime dependency or advisory was excluded.
The tool's own packages were not counted as application dependencies.

The audit completed with **zero skipped packages**, exit code **1**, and **ten
records in two affected packages**, grouped into **five underlying advisories**:

- Requests 2.32.5: GHSA-gc5v-m9x4-r6x2 / CVE-2026-25645 (two records), reported
  fix 2.33.0. The advisory concerns direct `extract_zipped_paths()` use; this
  iteration retains the finding rather than claiming an application exemption.
- Bootstrap setuptools 65.5.0: GHSA-r9hx-vwmv-q579 / CVE-2022-40897,
  GHSA-5rjg-fvgr-3xxf / CVE-2025-47273,
  GHSA-cx63-2mw6-8hw5 / CVE-2024-6345,
  GHSA-h35f-9h28-mq5c / CVE-2026-59890 (eight records). This package was supplied
  by venv bootstrap, not `requirements-server.txt`; a patched installation
  tooling policy still needs verification alongside jieba/other full-stack imports.

FastAPI 0.133.0 and Starlette 1.3.1 have no findings in that completed audit.
This is a scoped result, **not a clean application audit**. The post-test environment
inventory is retained separately; its added test packages have not been audited
in this iteration. CPU torch suffix mapping, LangChain migration, Transformers
and PyJWT no-fix records, Streamlit/Pillow compatibility, remaining transitives,
dev/runtime separation and full constraints are still outstanding.

## Evidence and reproduction

All raw evidence is ignored and local under the absolute directory
`C:/Users/Administrator/.codex/worktrees/release-python-security/RAG/db_sources/python-security/iteration-1/`:

- `server-install.json`, `server-install.log`, `server-installed.json`,
  `server-freeze.txt`, `server-audit-pins.txt`.
- `server-audit.json`, `server-audit-grouped.json`, `server-audit.log`,
  `server-audit.exit-code.txt`, `audit-tool-install.log`.
- All five `GHSA-*.json` maintainer advisories; FastAPI/Starlette PyPI metadata;
  downloaded release notes. Initial unauthenticated GitHub API requests hit a
  shared-proxy rate limit; authenticated CLI requests succeeded. The Starlette
  website failed TLS, so tagged upstream source supplied the release notes.
- `host_probe.py`, `host-probe-before.json`, `host-probe-after.json`,
  `baseline-install.log`; baseline environment is under `baseline-venv/`.
- `api-tests.log`, `api-tests.xml`, `test-tools-install.json`,
  `test-environment-installed.json`, `lightweight_probe.py`,
  `lightweight-smoke.json`, `lightweight-smoke.log`.

Use the full interpreter path above for `-m pip check` and `-m pytest -q` followed
by the four listed test files. Run `host_probe.py` with the new interpreter or
`db_sources/python-security/iteration-1/baseline-venv/Scripts/python.exe`, passing
a new temporary JSON output path. Use the proxy `http://127.0.0.1:7897` for external
requests and bypass localhost. Raw inventories record resolved transitive versions;
they are evidence, not a finalized portable lockfile.

## Remaining integration gates

Next iterations must finish shared runtime/build constraints and clean installs,
then validate supported ingestion, embedding, FAISS loading, optional reranking,
Streamlit and provider APIs without editing reliability-owned behavior. They must
run the available full native suite with honest asset skips and audit the final
runtime/dev trees, including upstream CPU torch version and no-fix advisory evidence.

Host independently reviews the scoped diff, resolves concurrent worker integration,
recreates the supported native environment, runs Linux/Docker and final asset/live/CI
acceptance, and maintains project/hook repositories. This worktree makes no commits,
pushes, merges or service changes. No permanent regression test was added in this
iteration; the before/after behavior evidence and existing tests support this
increment, and durable dependency regressions remain part of final-stage work.
