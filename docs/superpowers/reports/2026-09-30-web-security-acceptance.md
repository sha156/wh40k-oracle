# Frontend security candidate evidence — September 30, 2026

Status: **incremental implementation; dependency remediation pending**. Iteration 1 completes the native development binding change and reproduces the vulnerable dependency baseline. This report does not establish complete frontend security acceptance, deployment, integration, merge or publication.

Workspace: `C:/Users/Administrator/.codex/worktrees/release-web-security/RAG`, branch `codex/release-web-security`, starting revision `b90e8610d64450def12ca078388b877efea7793d`. The initial tracked worktree was clean. Work stayed in this isolated checkout; no other checkout, Docker service, backend, source/data policy, benchmark, generated wiki or knowledge repository was changed. No Git commit was made by this iteration.

## Native development binding

`web/package.json` now runs `next dev --hostname 127.0.0.1`. Production `scripts/start.mjs` and Docker configuration are unchanged. No frontend compatibility or UI changes were needed for this script change.

Before editing, the installed maintainer documentation was read at `web/node_modules/next/dist/docs/01-app/03-api-reference/06-cli/next.md`. Its `next dev` options document `--hostname` and the default `0.0.0.0` address. It also documents forwarding CLI options through `npm run` using `--`. Primary published reference: <https://nextjs.org/docs/app/api-reference/cli/next#next-dev-options>. Static export guidance was read at `web/node_modules/next/dist/docs/01-app/02-guides/static-exports.md`.

Direct Windows verification used the actual npm script, `npm run dev -- --port 34204`, via a hidden, short-lived process in this checkout. `Get-NetTCPConnection -LocalPort 34204 -State Listen` returned exactly one listener: **127.0.0.1:34204**, owned by PID 14068 under the temporary npm process PID 31928. An HTTP request to `/` returned **200**, 18,733 bytes and a Next payload. The dev log confirmed the patched command and Next 16.2.10. The check and cleanup took 7.054 seconds; the recorded UTC time was `2026-09-30T14:38:53.6890549Z`.

Only the temporary npm process tree was terminated, using its specific PID. The same port had **zero listeners after cleanup**. This verifies the native dev listener and an app response; it does not exercise browser interactions, HMR, API workflows or deployed images. A caller can explicitly supply different CLI arguments; this change secures the default project script.

## Installed baseline and full audit

Node **24.14.0**, npm **11.9.0**, Next **16.2.10**, eslint-config-next **16.2.10**, React/react-dom **19.2.4**, TypeScript **5.9.3** and ESLint **9.39.5** were directly read from the installed executables/packages. This checkout had no `node_modules` before `npm ci`; the separate install added 365 packages and audited 366. There is no junction to another checkout's dependencies.

Registry commands used `HTTP_PROXY` and `HTTPS_PROXY=http://127.0.0.1:7897` with localhost bypass. `npm audit --json` included development dependencies and returned exit 1: **8 vulnerable packages: 1 critical, 6 high, 1 moderate, 0 low**. This independently reproduces the supplied baseline. Dependency versions and the lockfile remain unchanged in this iteration, so no patched-tree or after-remediation audit result is claimed.

| Vulnerable package | Installed version(s) | Audit severity |
| --- | --- | --- |
| next | 16.2.10 | critical |
| sharp | 0.34.5 | high |
| postcss | 8.4.31, 8.5.17 | high |
| nanoid | 3.3.16 | high |
| js-yaml | 4.3.0 | high |
| browserslist | 4.28.6 | high |
| brace-expansion | 5.0.7, 1.1.16 | high |
| baseline-browser-mapping | 2.10.43 | moderate |

The registry audit suggests Next 16.3.7 and reports both GHSA-p293-qw3h-jr36 and GHSA-2xp9-vwfh-vxw4 as affecting Next `>=16.0.0 <16.3.3`. The suggested version has **not yet been independently checked for stability or compatibility**. Installed-package findings alone do not demonstrate reachable exploitation in this application; no exploit path was tested. The exact audit-provided advisory URLs and affected ranges appear below and in the full local JSON.

## Validation of this iteration

| Command | Result | Wall time |
| --- | --- | --- |
| `npm ci` with the existing lockfile and no prior node_modules | exit 0; separate baseline install | 22.183 s |
| `npm audit --json` including the development tree | exit 1; eight vulnerable packages | 3.166 s |
| `npm run test:unit` | exit 0; 22 passed, zero failures/skips | 0.895 s |
| `node node_modules/typescript/bin/tsc --noEmit` | exit 0 | 4.219 s |
| `npm run lint` | exit 0; no diagnostics | 12.796 s |
| `NEXT_OUTPUT=export NEXT_PUBLIC_API_BASE=/api npm run build` | exit 0; static export succeeded | 9.527 s |
| `git -c core.whitespace=cr-at-eol diff --check` | exit 0 | not timed |

The build used the default Turbopack compiler and exported `/`, `/codex`, `/design`, `/roster`, `/simulator` and the not-found route; output files were inspected in the ignored `web/out` directory. The unit runner emitted existing module-type warnings for imported TypeScript modules; all tests passed. No tests were weakened or added to mirror the one-line configuration change. These checks used the **unpatched baseline dependency versions**, and must run again after dependency remediation.

## Evidence and remaining work

Local raw evidence is under the ignored absolute directory `C:/Users/Administrator/.codex/worktrees/release-web-security/RAG/db_sources/release-check-20260930/web-security/`:

- `baseline-audit.json`, `baseline-audit-result.json`, `baseline-audit.stderr.log` contain the full baseline audit and command result.
- `baseline-npm-ci.log` and `baseline-npm-ci-result.json` contain the clean install result.
- `binding-{unit,typecheck,lint,export-build}.log` and corresponding `-result.json` files preserve validation output, exit codes and timings.
- `binding-dev-result.json`, `binding-dev.stdout.log`, `binding-dev.stderr.log` and `binding-dev-cleanup.log` preserve direct listener/HTTP/cleanup evidence.

The tracked diff is limited to the single `dev` script line in `web/package.json` and this report; `web/package-lock.json` is unchanged. The actual package diff was inspected. Build products, dependency files and evidence stay ignored.

Next iteration should verify a stable patched Next/eslint-config-next pair, update supported transitive dependencies and regenerate the lockfile. Then run a genuinely clean install, full before/after audit, unit/type/lint/export checks and repeat direct dev binding verification against the patched tree. The eight current advisory findings remain blockers to completing this objective. Host-owned independent review/integration, complete browser tests on final Docker images, CI, deployment and publication remain outstanding. No result from the main checkout's existing frontend or browser suite is used as acceptance for this checkout.

## Exact baseline advisories

The following table is derived from the saved full baseline npm audit response. Multiple affected ranges for the same package/advisory are combined; audit package counts are not advisory counts.

| Package | Advisory | Audit affected range(s) |
| --- | --- | --- |
| baseline-browser-mapping | [GHSA-w5vr-8v7q-w6rv](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv) | `>=2.0.0 <2.11.0` |
| brace-expansion | [GHSA-6j4f-fj2g-mc7p](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p) | `<1.1.19; >=4.0.0 <5.0.10` |
| brace-expansion | [GHSA-mh99-v99m-4gvg](https://github.com/advisories/GHSA-mh99-v99m-4gvg) | `<1.1.17; >=4.0.0 <5.0.8` |
| brace-expansion | [GHSA-q2hr-2g5m-vwhr](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr) | `<1.1.21; >=4.0.0 <5.0.12` |
| brace-expansion | [GHSA-qhr7-859c-m2p7](https://github.com/advisories/GHSA-qhr7-859c-m2p7) | `<1.1.20; >=4.0.0 <5.0.11` |
| brace-expansion | [GHSA-rgw5-rvv9-x895](https://github.com/advisories/GHSA-rgw5-rvv9-x895) | `<1.1.18; >=4.0.0 <5.0.9` |
| browserslist | [GHSA-73wf-gq98-2v4g](https://github.com/advisories/GHSA-73wf-gq98-2v4g) | `<=4.28.6` |
| browserslist | [GHSA-c83g-rgw3-j3cx](https://github.com/advisories/GHSA-c83g-rgw3-j3cx) | `<=4.28.6` |
| js-yaml | [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh) | `>=4.0.0 <4.3.2` |
| js-yaml | [GHSA-5p4m-2wfm-xmqj](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj) | `>=4.0.0 <4.3.1` |
| nanoid | [GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8) | `<3.3.18` |
| next | [GHSA-2xp9-vwfh-vxw4](https://github.com/advisories/GHSA-2xp9-vwfh-vxw4) | `>=16.0.0 <16.3.3` |
| next | [GHSA-4633-3j49-mh5q](https://github.com/advisories/GHSA-4633-3j49-mh5q) | `>=16.0.0 <16.2.11` |
| next | [GHSA-4c39-4ccg-62r3](https://github.com/advisories/GHSA-4c39-4ccg-62r3) | `>=16.0.0 <16.2.11` |
| next | [GHSA-68g3-v927-f742](https://github.com/advisories/GHSA-68g3-v927-f742) | `>=16.0.0 <16.2.11` |
| next | [GHSA-6gpp-xcg3-4w24](https://github.com/advisories/GHSA-6gpp-xcg3-4w24) | `>=16.0.0 <16.2.11` |
| next | [GHSA-89xv-2m56-2m9x](https://github.com/advisories/GHSA-89xv-2m56-2m9x) | `>=16.0.0 <16.2.11` |
| next | [GHSA-955p-x3mx-jcvp](https://github.com/advisories/GHSA-955p-x3mx-jcvp) | `>=16.0.0 <16.2.11` |
| next | [GHSA-m99w-x7hq-7vfj](https://github.com/advisories/GHSA-m99w-x7hq-7vfj) | `>=16.0.0 <16.2.11` |
| next | [GHSA-p293-qw3h-jr36](https://github.com/advisories/GHSA-p293-qw3h-jr36) | `>=16.0.0 <16.3.3` |
| next | [GHSA-p9j2-gv94-2wf4](https://github.com/advisories/GHSA-p9j2-gv94-2wf4) | `>=16.0.0 <16.2.11` |
| next | [GHSA-q8wf-6r8g-63ch](https://github.com/advisories/GHSA-q8wf-6r8g-63ch) | `>=16.0.0 <16.2.11` |
| postcss | [GHSA-6g55-p6wh-862q](https://github.com/advisories/GHSA-6g55-p6wh-862q) | `<=8.5.11` |
| postcss | [GHSA-fxqj-rqcc-2cmp](https://github.com/advisories/GHSA-fxqj-rqcc-2cmp) | `<=8.5.22` |
| postcss | [GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93) | `<8.5.10` |
| postcss | [GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849) | `<=8.5.17` |
| sharp | [GHSA-f88m-g3jw-g9cj](https://github.com/advisories/GHSA-f88m-g3jw-g9cj) | `<0.35.0` |
| sharp | [GHSA-rgj7-g3m4-5g8c](https://github.com/advisories/GHSA-rgj7-g3m4-5g8c) | `<0.35.4` |
