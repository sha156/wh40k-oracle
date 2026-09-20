# Local Docker completion roadmap

Scope: finish the local Docker application first, per the user's September 20 decision. Cloud deployment is deferred. This audit supersedes the open-status claims in the July remaining-task inventory and earlier release checkpoints; those documents remain historical evidence.

## Implemented and verified

| Area | Current state and evidence |
| --- | --- |
| Edition migration, DSL and structured authority layers | Existing implementation complete; September reconciliation restores 390 reviewed patches and checks 2,901 DSL fingerprints. This continuation did not rebuild or modify the database. |
| Official points | Existing ledger has 3,893 rows; latest reconciliation matched 1,333 operational tiers and 879 enhancement rows. September 20 live price browsing confirms the ledger and both Warlord prices at 3,500. Cache is dated September 14; this is not a new source fetch. |
| Four local web sections | Chat, codex, simulator and roster laboratory implemented and exercised through Docker. |
| Roster text import, validation and critique | Already implemented. Live two-unit roster parses, validates at 150 points and critiques its equipped unit; an unknown third line remains explicitly unresolved. Corrected stale agent-tool text that claimed parsing was unavailable. |
| Conversation memory | September 18 acceptance passed six same-session recall trials, isolation and fresh-fact checks. No new full memory benchmark this pass. |
| Canonical identity and faction inventory | Preserve IDs across wiki lookup, refuse duplicate IDs, separate pagination from total counts and source prices. Live Titan answer confirms four shared Imperial/Chaos datasheets. |
| Referenced rules and citations | Retrieve army-rule text separately from card references. Web formatting now supplies a dedicated merged-card citation and retains source-scope warnings. Final live command answer lists all six effects and separates PDF effects from card-specific counts/ranges. |
| Lossy answer formatting | Preserve named Markdown table rows or fall back to the original reply with a visible warning. This is a narrow content-loss guard, not general semantic equivalence checking. |
| Keyword-to-core-rule links | Already implemented; live index has 50 entries, 37 with chapter links, and sampled detail/chapter requests succeed. Not every unit-specific keyword has an official section link. |
| Saving an answer | Added user-controlled Markdown export with citations, AI/unreviewed labeling and a lossless JSON snapshot. Download and visible copy-panel controls are provided. No AI answer is automatically promoted into authoritative wiki content. |
| Docker deployment | Both images build and run; required assets and model warmup pass. Final release evidence is in the September 20 acceptance report. |
| README artwork and font delivery | Existing README artwork and self-hosted display font are present. The documented system-font fallback for Chinese remains a deliberate performance choice. |

## Remaining work with explicit limits

1. Acquire complete suitable **public official** rules for Gunwagon, Runtherd and 28 Ork enhancement keys. Keep preview-derived records labeled. Current points do not establish current rules coverage.
2. Establish Docker Desktop restart durability. The user started it successfully this time; the earlier stale-socket recovery is a workaround, not a demonstrated permanent fix. Do not restart the host solely to manufacture a passing claim.
3. Continue rolling AI quality evaluation. The September 18 agent benchmark was 115/115; September 20 checks cover selected final web responses and deterministic regressions, not another full benchmark. Arbitrary sentence-to-source correctness remains probabilistic.
4. Revisit cloud hosting only after the local app, as requested. No cloud server/provider changes were made.
5. Automatic `archive_answer` insertion into the official wiki remains intentionally unwired. The wiki constitution reserves FAQ pages for official FAQ; any AI archive integration needs a separate non-authoritative content design. Manual Markdown export is available now.

Release tracking: [PR #74](https://github.com/sha156/wh40k-oracle/pull/74). Exact tests, browser limits and deployment evidence: [September 20 acceptance](../reports/2026-09-20-lookup-deployment-acceptance.md).
