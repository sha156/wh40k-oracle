# Paused chat redesign and historical Calgar checkpoint

The user requested **save and stop** on September 21. Implementation and testing stopped. All current files remain saved locally; unfinished archive work is not deployed or claimed complete.

## Repository and runtime

- Working repository/assets: `D:/Project/py/RAG`, branch `codex/review-answer-provenance`.
- Draft PR: https://github.com/sha156/wh40k-oracle/pull/75. It is not merged. Do not mark ready until the revised scope is tested and published.
- Published commits: `793b7128b` (lookup, evidence retention and input fixes), `74a1bbf40` (explicit DeepSeek Flash).
- Local commit: `641d95b67a2efdd3514399d3e7561c153bbc8f75` (first conversational UI). Subsequent uncommitted changes restore the original Warhammer appearance after the user rejected its light theme.
- The final style revision, readability/export changes, wiki refinement, archive draft and handoff documents are saved but uncommitted. No push, merge or additional deployment was performed after the stop request.
- Local Docker services were left running. Last deployed API image: `sha256:bfcec93694cdda46328c63569d94038f2f21190fbf2affb2a35d2a189ab77882`; web: `sha256:fc004700da5e76774b69ffa41e84932891aed7879ee82e776ab61c1f613feaa9`. Neither includes the new archive integration.

## Completed user-visible work

Guilliman's Chinese short name resolves to the correct 355-point record. The alias was projected through the existing stage after a copied-DB trial; no point values changed. DeepSeek Flash is explicitly selected with thinking disabled; no Pro requests were made.

The running chat retains the original Aquila header, dark teal/black, bone text, condensed fonts and red accents. Only the dialogue presentation is simplified: continuous visible answers and history, expandable sources/trace/datasheets, multiline input, stop/retry and new conversation. Copy Answer produces readable Markdown; the separate view/download archive retains its complete JSON snapshot.

Readability prompts group independent facts and remove repeated qualifications. The Oath reference distinguishes the current official English v1.2 text, official Chinese v1.1 text, and the named older translated balance document. A missing chapter name in an exclusion list does not itself establish possession of the ability.

## Calgar diagnosis and saved partial implementation

Ordinary Marneus Calgar is present in Black Library's local cache: source id `6`, `马涅乌斯.卡尔加（已删除）`, faction `极限战士`, historical score **200**, including two Victrix guards. The importer previously overlaid only existing canonical units and skipped this unmatched record. The current SQLite contains only **Marneus Calgar in Armour of Antilochus**, canonical id `000004183`, official cached price **155**. Its cached Black Library price of 140 is stale. These are different records; never point an ordinary-Calgar alias at the armour variant.

`db_compile/source_archive.py` now defines a separate `source_archived_units` table, projection of explicitly deleted cached records, and conservative exact/verified-alias lookup. `db_compile/update.py::stage_zh_details` calls the projection, so a future normal rebuild can reproduce it. `tests/test_source_archive.py` covers status/authority, raw-payload retention, variant separation, missing inputs, idempotence, transaction rollback and restore wiring. The worker reports **37 focused tests passed**. A disposable DB probe archived **2 deleted records from 1,072 cached entries**. The runtime database has **not** received this projection.

Lookup returns `historical_points`, `status=historical_source_only`, `authority=third_party_deleted_record`, `is_current=false`, original names/raw payload, source ID and provenance. It does not invent a canonical ID or current points field. `cached_at` is expressly filesystem modification time, not a publication or verification date. `source_url` is the known POST API endpoint, not a navigable public card permalink.

The first integration-test draft is saved in `tests/test_agent_source_archive.py`. Its first run was **9 failed / 1 passed**. Integration has not been implemented, and the draft fixture also needs repair: its generated DB contained only the armour row, so four tests failed first on missing Guilliman points; its Calgar faction string must be aligned with the verified `极限战士` source identity. Do not present this test draft as a valid all-red proof of the application bug or a passing suite.

## Verification boundaries

- Full native suite before later Flash/UI/prompt/archive changes: **2,545 passed**. Subsequent targeted backend suites passed, including the final readability-focused **64** and independent review's **126** tests. No new full suite has run on this paused working tree.
- Final frontend revision: **10 unit tests**, TypeScript, ESLint and Docker production build passed. Source review approved the style/export revision; it did not review the later archive draft.
- Browser: restored dark desktop style inspected; complete answers, source details, readable copy, reload notice, same-session follow-up, new-session isolation, cancellation and Shift+Enter exercised. The latest readable Oath copy was 893 characters with three sources and no internal JSON. A single follow-up misstated an English version as Chinese; source wording remains a quality limit.
- Mobile overflow was checked on the earlier candidate; the final dark header still needs a fresh mobile check.
- Automatic Markdown download completion remains unconfirmed. Visible copy/archive rendering worked.
- Wiki build/lint: **0 errors / 1 existing aggregated warning**.
- Official points cache is dated September 14. No September 21 source refresh or full 115-question AI benchmark was performed.

## Resume order

1. Inspect this checkpoint and current diff. Preserve saved frontend changes and all unrelated work.
2. Repair the Calgar integration fixture, then implement archive handling in `agent/tools.py`, the relevant empty-result gate, and `web_api/formatter.py`. Historical evidence must survive lookup without becoming current points, a roster unit, an official MFM citation or a fabricated L3 datasheet. Protect against the existing fuzzy ordinary-name match to the armour variant. Exact current identities must retain priority.
3. Review and run meaningful focused regressions. Trial projection on a copied DB, compare all current units/points unchanged, then back up and intentionally project into the runtime DB.
4. Rebuild the API and verify the exact user comparison, ordinary Calgar alone, the armour variant, and Guilliman. Require separate historical/current provenance, correct 200/155/355 values and no misleading fallback.
5. Check the final dark mobile layout, run final appropriate suites, update acceptance evidence, then commit/push the intended changes. Rewrite PR #75 for the final scope and check its actual head before any merge.
6. Update the knowledge handoff. The earlier automatic approval review rejected external devlog publication with `blocked by policy`; prepared content remains project-local. Do not claim external notes were published.

Other retained work: public official rules for Gunwagon, Runtherd and 28 Ork enhancement keys; Docker restart durability; rolling answer-quality evaluation. Cloud and automatic AI insertion into the authoritative wiki remain deferred.
