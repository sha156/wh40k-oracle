# Readable chat and local review acceptance

The user requested continued local Docker testing, a working Guilliman points lookup, affordable DeepSeek Flash, and a conversational interface that displays a complete answer to broad questions. Cloud remains deferred. PR #75 carries this continuation.

## Implemented behavior

- The Chinese short name `基里曼` resolves exactly to Roboute Guilliman. The existing community-alias projection added one alias to the runtime database; no points changed. The prior failure was an ambiguous name match with Ahriman, not a missing LLM connection. Ambiguous datasheet results now retain candidates and a recovery instruction. Uncertain fuzzy numeric matches remain refused.
- Multiple successful tool calls retain their individual sources even if the last lookup fails. The formatting evidence digest preserves identity and source scope before bulk content. Invalid/nested layout fields preserve the original answer through an explicit fallback. Nonfinite simulator inputs produce a disclosed validation warning instead of HTTP 500.
- The agent, answer formatter and classic fallback explicitly use `deepseek-flash` with thinking disabled. A small live API call confirmed the model and nonempty text; the account model list included Flash and Pro, but no Pro request was made. Classification remains at eight output tokens. Answer/layout ceilings increase to 3,200 tokens to accommodate complete explanations; this is a ceiling, not a minimum response length.
- Broad questions request the applicable scope, full explanation, practical effects and limits in one response. Version comparisons must identify an actual older baseline; a replacement instruction alone does not prove every clause is new. Simple points questions remain concise.
- The chat redesign presents all explanation paragraphs with the opening answer, retains conversation turns, and puts sources, tool trace and full datasheets in expandable details. It adds a multiline composer, Enter/Shift+Enter and IME handling, stop/retry, new conversations, and bounded local reading history. A reload explicitly starts a fresh server conversation; restored visible records are not represented as retained model memory.

## Oath of Moment source audit

The submitted answer cited only current English Faction Pack page 60. That alone could not support its historical claims.

| Local evidence | Verified implication |
| --- | --- |
| Official English Faction Pack Space Marines v1.2, effective August 26, 2026, p.60 | Current target/hit-reroll rule, Codex detachment condition, four excluded chapter keywords and their MFM sections. |
| Official Chinese v1.1, effective July 22, 2026, p.56 | Those same conditions already appear. The inspected Oath text shows no substantive July-to-August difference. |
| Older translated `6月4日平衡版中午.pdf`, p.9 | Includes Black Templars in the exclusion list, has no MFM-section clause, but already requires a Codex: Space Marines detachment. It is a specifically named older snapshot, not an inferred immediately preceding official release. |
| Black Templars translated codex p.1 and current faction-pack context | Ability replacement requires a separate check. Absence from an exclusion list cannot establish that an army possesses Oath or automatically receives its benefit. |

The manually curated `wiki/core-rules/oath-of-moment.md` now records these boundaries. It was updated through query/edit/build/lint/log; generated indexes were changed only by the normal command. The old wiki text was not shown in the submitted `rag_search` trace, so it is not claimed as the proven cause of that response. The PDF index has no wiki pages; the curated comparison is available through keyword/wiki tools.

The first exact Oath question returned an 11-paragraph explanation in **10.281 seconds**, with no fallback, distinguishing the two baselines and preserving the Black Templars limit. See `2026-09-21-live-oath-v1.json`. Although these factual checks passed, the user rejected the follow-up candidate's twelve-paragraph answer as confusing and repetitive, and rejected the light visual redesign. Their actual rejected response is preserved in `2026-09-21-oath-rejected-long.json`. This candidate is not treated as final product acceptance. The revised pass restores the Warhammer visual language, groups related facts, removes duplicate caveats and makes Copy Answer return readable prose and sources without the internal JSON archive.

## Checks completed before final frontend rollout

- Full native pytest after the lookup/provenance/simulator fixes: **2,545 passed**, 19 warnings, 135.51 seconds. This preceded three additional Flash guard tests and the final answer-strategy/UI changes.
- Flash-focused suite: **64 passed**. Final strategy-focused suite: **124 passed**. Independent backend review ran **126 targeted tests**, with no actionable findings.
- New regression cases were observed failing before the corresponding fixes: citation/layout retention, nonfinite simulator inputs, and exact alias/ambiguity recovery.
- Wiki lint: **0 errors, 1 known aggregated warning**.
- Hosted push and pull-request checks passed for `74a1bbf40` before the redesign; the final PR head must be checked separately.
- Live short-name question: **355 points**, correct single model, L3 and MFM citations, **6.703 seconds**, no fallback. A two-unit comparison retained distinct Guilliman and Shadowsun citations and returned 355/100 points in **7.219 seconds**, no fallback.
- Local HTTP checks exercised health/assets, Titan inventory, 50 keywords with 37 chapter links, changelog, official points browsing, explicit-loadout simulation, wrong-phase rejection, roster parsing/validation/critique, unresolved import text, nonfinite input, empty chat and unknown-unit handling. Raw results are in `2026-09-21-local-functionality.json`.
- Browser checks before the redesign confirmed a legal two-unit 150-point roster and visible critique, and a Broadside simulation with an explicit Heavy rail rifle loadout. The UI rejected the missing loadout before the equipped run succeeded.

## Data and reproducibility

Implementation commits already published: `793b7128b` (lookup/provenance/input fixes) and `74a1bbf40` (Flash selection). Runtime assets remain under `D:/Project/py/RAG`. The alias change was first tested on a copied database; the pre-change backup is `db/backups/20260921-before-guilliman-alias.sqlite` (ignored). The normal authority restoration includes community aliases, so the fix is reproducible after a database rebuild.

No official points source was refreshed in this pass. The cache is still dated September 14; the displayed points are verified against that existing official snapshot, not a newly fetched September 21 price. The full 115-question AI benchmark was not rerun; September 18's result remains historical.

## Retained limits

Complete public official rules for Gunwagon, Runtherd and 28 Ork enhancement keys remain unavailable in the verified corpus. Docker Desktop starting successfully today does not demonstrate durable recovery from the Windows stale-socket failure. Cloud and automatic AI insertion into the authoritative wiki remain deferred. Separately blocked external devlog/learning/error-note publication remains pending in the prepared project-local handoff.

## Paused final revision

The user requested save and stop. The final Warhammer style revision is running locally; 10 frontend unit tests, TypeScript, ESLint and the Docker production build passed. Desktop visual checks and readable copying passed. The final dark mobile layout still needs verification, and automatic download completion remains unconfirmed. The later concise points response was 355 with no extra body, 4.906 seconds and no fallback. The revised Oath response grouped the answer into five body paragraphs; the final browser copy contained three sources and no internal JSON archive. This is selected-response evidence, not a general guarantee of factual or stylistic accuracy.

The newly reported ordinary-Calgar gap is diagnosed but not fixed end to end: Black Library's deleted historical source record was skipped because canonical units contains only the armour variant. A separate archive projector and restore hook are saved with 37 focused tests passing; the agent/formatter integration draft remains incomplete and its first test run had 9 failures and 1 pass, including fixture problems. No runtime archive projection or deployment occurred. Full paused state, image IDs, tests and resume order are in `2026-09-21-paused-chat-calgar-checkpoint.md`. PR #75 remains draft and unmerged; final changes are saved locally but not yet published.
