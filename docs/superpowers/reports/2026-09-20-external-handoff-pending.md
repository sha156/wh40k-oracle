# Prepared knowledge handoff — external publication pending

The project-local roadmap and acceptance report contain the complete current handoff. The earlier automatic approval review rejected a separate devlog write/publish action with only `blocked by policy`; this document prepares the concrete content without retrying that external mutation. No new cross-project harness rule is warranted.

## Project devlog entry

Intended destination: `D:/Project/devlog/wh40k-oracle/commits/20260920-b7dde5bdc-web-provenance-export.md`, with a linked current section in `wh40k-oracle/ROADMAP.md`.

Real implementation commits: `b7dde5bdc5c1451fc5d473d27e8c678d23402414` (web card citations and Markdown export), `ea84ff1bf` (named-table retention), `da57a429c` (line endings) and `d38a2fe7a` (copy panel). PR #74 carries the earlier canonical identity, faction inventory and lookup optimization work.

Why: a merged card lacked a dedicated web citation, and its scope warning was truncated; the layout model could then attach a general PDF page to card-specific counts and ranges. Add the explicit card source and retain scope first. Valid JSON also failed to guarantee that named rule-table rows survived into visible content; keep the original prose with a warning when they disappear. Provide a user-controlled, explicitly unreviewed Markdown snapshot instead of injecting AI text into the authoritative wiki.

Checks: 2,532 full native tests passed before the last two guard tests; final 40 focused tests passed. Two export tests, TypeScript, ESLint and production build passed. Rebuilt Docker services passed asset/warmup, codex, points, simulator and roster checks. Final command question returned all six effects with separate card/PDF citations, HTTP 200 in 55.215 seconds, no degradation. The browser copy panel delivered 4,551 characters with the AI label, source and full snapshot. Automatic download completion was not confirmed. The full September 18 benchmark remains 115/115; it was not rerun on September 20.

Remaining: public official rules for two units and 28 Ork enhancement keys; Docker restart durability; cloud deferred by user decision. No source refresh or database change in this pass. See the project acceptance report for final PR/merge status rather than inventing a merge commit here.

## Learning-note addition

Intended destination: append to `C:/Users/Administrator/learn-notes/decisions/20260918-inventory-counts-need-identity-semantics.md`, retaining its existing frontmatter (`date`, `project`, `status`, `promoted_to`).

### September 20 follow-through: check the final model boundary

The second LLM that formats an answer needs the same provenance boundaries as the reasoning agent. A correct source-scope warning on the first tool wire did not help when a later digest truncated it and offered only unrelated page citations. Preserve identity and scope before bulk text, and give each evidence class its own usable citation.

Also distinguish parseable JSON from complete user-visible content. In a controlled replay, the revised layout prompt put the full rule list under `verdict.calc` instead of top-level `calc`. Prompting alone was insufficient. A narrow deterministic named-table guard now preserves the full original reply with a warning when formatting loses rows. Do not describe this as general semantic validation; paraphrases and arbitrary sentence provenance still need separate evaluation. Before/after observations and failed responses remain in the project report.

## Resolved error record

Intended destination: `C:/Users/Administrator/error-notes/rag/20260920-error-01-web-card-citation-lost.md`, plus one README index link.

**Date:** 2026-09-20
**Project:** sha156/wh40k-oracle
**Status:** missing structured-card citation and scope truncation fixed; general model citation accuracy is not guaranteed.

### Error

No exception occurred in production. The initial HTTP response cited the general orders PDF page for the Leman Russ card's two-order/12-inch fields. That page supported general order effects and the ordinary 6-inch rule, not those card-specific numbers. The regression test looking for the missing L3 citation initially raised:

```text
StopIteration
next(c for c in answer.cites if c.book == "L3 结构库 · Alpha")
```

### Environment and reproduction

Windows, local Docker Desktop, Python backend/Next.js frontend; project runtime `D:/Project/py/RAG`. Return an official-db merged WikiPage from `get_entity`, including a long body and its `source_scope`, then format an answer with an independently retrieved general-rule PDF source. Before the fix, web `_derive_cites` omitted the merged card and `_evidence_digest` truncated the warning.

### Attempts and resolution

Agent-level scope disclosure alone was insufficient: the final web formatting boundary still lost it. Commit `b7dde5bdc` derives a dedicated L3 merged-card citation without inventing a page and puts scope ahead of bulk content. Regression tests confirm the card and real PDF citation coexist, unrelated patch-page references are not promoted and scope survives the digest limit. The final live HTTP answer cites the card-specific fields to L3 and the six general effects to PDF page 1. Failed lookup results do not create card citations.

```powershell
& 'D:/Project/py/RAG/.venv/Scripts/python.exe' -m pytest tests/test_web_card_provenance.py tests/test_web_api_stage3.py tests/test_agent_lookup_completeness.py -q
```

Final result: 40 passed. Do not infer that the separate named-table guard or one passing web response proves every future model citation correct.

### Lesson

Validate provenance after every transformation, especially a second formatting model. A source listed on a merged entity is not automatically provenance for every field. Keep failed evidence and distinguish deterministic source availability from probabilistic model selection.
