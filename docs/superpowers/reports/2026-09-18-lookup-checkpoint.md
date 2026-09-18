# Lookup completeness checkpoint

Status: saved at the user's request to stop. Work remains on `codex/benchmark-lookup-completeness` in `D:/Project/py/RAG`; it is not merged or deployed. The app checkout at `C:/Users/Administrator/Documents/ChatGPT/RAG` and the running containers still represent the previous accepted main revision, `74544de81`.

## Changes and purpose

- `get_entity` carries the resolver's canonical ID through to the indexed wiki page. Re-querying by English display name could miss a translated title or select a same-named unit from another faction. Numeric ID lookup, duplicate-ID refusal and faction-qualified ambiguous candidates preserve identity. Unique older slug-ID pages retain their compatibility path.
- A read-only, paginated `list_faction_units` tool reports current database datasheet counts separately from deduplicated official MFM unit counts. It uses the existing active-unit policy, keeps missing data distinct from zero, and preserves complete bounded JSON on the model wire.
- The existing Chaos Titan alias mapping now exposes its source: Faction Pack Adeptus Titanicus, page 2, TITANICUS TRAITORIS. Separate Imperial and Chaos points pages do not establish separate datasheets. The local official PDF text was checked.
- No database, official price cache, generated wiki or gold-answer changes were made in this continuation.

## Saved evidence

| Artifact | What it establishes |
| --- | --- |
| `2026-09-18-lookup-baseline.json` | Four baseline live trials: two each for questions 63 and 116, including the lookup/fallback limitations. |
| `2026-09-18-lookup-initial-candidate.json` | Four initial candidate trials. Retained as rejected evidence: a Titan answer incorrectly inferred independent Chaos datasheets from separate points pages. |
| `2026-09-18-lookup-final-probe.json` | Ten final-code trials: two each for 63, 109, 116, 118 and 119. Raw answers, metadata and tool traces; these are not ten formally judged passes. |

The full native suite collected the first three new regression tests and passed **2,521 tests, 19 warnings** in 175.75 seconds. The final lookup test file, including six subsequently added cases, separately passed **9 tests**. The earlier focused agent/tool/loop set passed **115 tests**. Do not add these overlapping counts or label the completed full run as 2,527 tests. The original fixture failed before implementation by selecting ID `101` rather than resolved ID `202`; the corrected identity fixture passes. `git diff --check` passed.

Both final question 116 answers report four datasheets and the sourced shared Chaos rules. Question 118 trial 1 instead leads with the World Eaters price after `get_datasheet`, then discloses other factions in a note; trial 0 lists all four faction prices through `calc_points`. This needs formal assessment and a base comparison before declaring ambiguity behavior unchanged. Question 63 answers still need complete source/freshness review. No full 115-question benchmark or hosted CI was run for this branch, and no final Docker/API/browser acceptance was performed for these changes.

## Public official source constraint

The user selected **public official sources only for now**. The [official downloads page](https://www.warhammer-community.com/en-gb/downloads/warhammer-40000/) and public Ork articles were inspected, including the [September points announcement](https://www.warhammer-community.com/en-gb/articles/x82yzzth/codex-orks-points-are-live-on-the-munitorum-field-manual/), [army examples](https://www.warhammer-community.com/en-gb/articles/fvsvtvtu/build-a-better-waaagh-warhammer-community-cooks-up-their-ideal-ork-armies/), and [army dispositions](https://www.warhammer-community.com/en-gb/articles/lyqxdhrh/building-your-ork-waaagh-around-army-dispositions-with-adrian-from-tabletop-titans/). No additional complete authoritative rules were acquired for Gunwagon, Runtherd or the 28 remaining enhancement keys. This is an acquisition limit, not proof that no public source exists. Labeled previews remain previews. No new points synchronization is claimed for September 18.

## Resume order

1. Review all final live traces and formally assess questions 63 and 118, including a real base comparison where regression is suspected. Preserve rejected evidence and existing ambiguity safeguards.
2. Finish code review and any corrections; run relevant final tests. Run the complete 115-question benchmark with unchanged gold and retain actual results.
3. Rebuild the API image and verify the new tools through the live API/browser. Existing containers have the previous accepted code, not this branch.
4. Publish a reviewable PR and require green CI and acceptance before merge. Synchronize the two checkouts only after acceptance.
5. Continue Ork source reconciliation only when suitable public official rules become available. Docker startup durability remains an independent open host issue.

No further implementation, model calls, rebuild or merge should run until the user resumes the task. Existing application services are left running; stopping this work does not shut down the user's app.
