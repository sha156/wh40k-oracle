# Live recall fix and Docker recovery — September 18

Tasks 3–4 application acceptance is complete. Canonical runtime: `D:/Project/py/RAG`, branch `codex/live-ai-docker-acceptance`. This report supersedes the unresolved recall hypothesis in the [September 16 checkpoint](2026-09-16-live-ai-docker-checkpoint.md), while preserving its actual failed response and benchmark results.

## Failure and change

Same-session history reached `next_step`, and the live classifier correctly chose idle chat. Capturing the provider boundary showed whitespace responses in JSON mode; the bounded parsing retry could also be blank, causing fallback to retrieval without conversation history. The earlier classifier/verification-gate hypothesis was not the observed cause.

`SessionContext` stores assistant display prose. `_render_loop_message` previously sent that prose directly as assistant messages although the protocol requires JSON tool/final steps. It now serializes prior assistant text as `{"type":"final","content":text,"sources":[]}` only at the provider boundary. Session storage and user text remain unchanged. No prior citations become fresh evidence. The classifier, source-verification gate, strict parser and retry limits are unchanged.

The [DeepSeek JSON mode documentation](https://api-docs.deepseek.com/guides/json_mode/) acknowledges occasional empty responses. This change restores protocol consistency and passed the observed acceptance cases; it does not establish that every possible provider empty response is eliminated.

## Evidence and limits

- A regression using a fake provider that returns whitespace for plain assistant history failed against the old implementation and passed after the fix. It checks the two-turn loop, no fallback/tool use, quoted/multiline/Chinese content and unchanged stored history.
- Focused client/session/loop tests: **59 passed**.
- Full native `pytest -q`: **2,518 passed, 19 warnings**, 189.52 seconds. No generated data/wiki changes appeared in Git status.
- Isolated direct-call controls passed for both formats (3/3 each with a short acknowledgment, then 5/5 each using captured history). These controls were inconclusive, not evidence that plain history always fails: [provider controls](2026-09-18-recall-provider-ab.json).
- Removing JSON mode only for an empty-response retry passed 2/6 full conversations; failures included plain prose rejected by the strict parser. This probe was rejected: [retry probe](2026-09-18-recall-empty-json-probe.json).
- Alternating full multi-turn trials: plain history 3/4 passed; JSON history 4/4 passed. This is a small stochastic sample: [A/B evidence](2026-09-18-recall-multiturn-ab.json).
- Production fix with six fresh sessions: **6/6 recalls passed without degradation**: [live trials](2026-09-18-recall-fixed-live.json).
- Rebuilt Docker API: five `/chat/sync` calls returned 200. Same-session recall correctly returned the synthetic army/nickname; another session did not know them. A deliberately stale draft claimed Guilliman cost 123; the follow-up called `calc_points`, returned the database value **355**, and provided official MFM citations: [HTTP requests and responses](2026-09-18-live-session-acceptance.json). This verifies a fresh database lookup, not a new September 18 source scrape.
- September 16 full benchmark remains **113 correct / 2 partial / 0 wrong**, 115 questions. No new full benchmark was run; the changed path is prior assistant history. Partial #63 and #116 remain disclosed.

## Docker recovery

Desktop 4.53.0.211793 again failed on inaccessible `Docker/run/dockerInference` at startup. `EnableDockerAI` was already false, so disabling it previously did not establish a durable fix. The Desktop CLI said it was not running while crashed Desktop/backend processes remained.

After stopping those Docker processes, the exact two parent paths were validated, renamed to sibling backups and recreated empty:

- `%LOCALAPPDATA%/Docker/run.stale-20260918-180429`
- `%LOCALAPPDATA%/docker-secrets-engine.stale-20260918-180429`

Desktop then started and engine 29.0.1 responded. The API image rebuilt successfully using the existing build proxy. `docker compose up -d --no-build` started API and web; the API is healthy. Images, volumes, WSL distributions and project assets were preserved. No factory reset or recursive deletion was used. The underlying trigger and persistence across a later restart/reboot remain unverified.

## Browser and remaining work

The container-served codex loaded the four Titan entries. Warlord Titan displayed 3,500 points, model/weapon data and FRAME membership; the responsive page was visually inspected. The browser streaming chat also passed a real two-turn preference/recall exchange: Tau Empire / Copper Lantern 742 was recalled with zero tool steps and zero citations. The rendered answer was visually inspected. Containers are left running and the app is available on `http://127.0.0.1:3000/`.

Remaining: obtain authoritative released Ork rules for Gunwagon, Runtherd and 28 enhancement keys; supersede explicitly labeled previews when verified; improve benchmark partials #63/#116; diagnose a durable Docker host startup fix if the socket problem recurs. Current prices do not certify all structured rules as current.
