# Formatter short-name fallback fix saved at source freeze

Date: 2026-09-26. Status: **implemented, independently reviewed, not yet deployed**.

The three live comparison answers on the identity-projection API preserved correct upstream prose and evidence but returned `degraded=true` with the visible warning `回答排版失败，以下保留原始回复与已查证来源。` A diagnostic replay using the retained comparison prose, faithful current tool evidence and the configured DeepSeek Flash structurer produced valid structured JSON. Layout and grounding validation passed. The exact rejection was `_missing_table_labels`: it required the complete first-column strings `马涅乌斯·卡尔加（含 2 名护卫，非安提洛库斯之铠版）` and `罗伯特·基里曼`, while the structure pass retained them naturally as `卡尔加…` and `基里曼…`.

`web_api/formatter.py` now accepts the final component of a dotted Chinese personal name only when it is at least three CJK characters and occurs in exactly one complete table-row label. The original loss guard still rejects missing rows when two dotted names share a suffix, when a suffix overlaps another full row label, or when an ordinary and equipment-specific variant could be confused. Three regressions cover the accepted comparison and both collision forms.

Verification at source freeze:

- Exact live-model diagnostic replay: layout valid, missing labels `[]`, grounding problems `[]`, four structured body paragraphs retained.
- Focused identity/formatter suite: **113 passed**, five existing SWIG warnings, 4.87 seconds.
- Scoped diff check passed.
- Independent review first reproduced a mixed dotted/non-dotted collision, which was fixed. Final review: **APPROVE**, 26 independent formatter tests, zero findings.

No credential, canonical database, wiki output or source cache changed. No application commit was created, so no commit explanation is warranted. The current source remains part of the shared dirty branch `codex/review-answer-provenance`.

Remaining acceptance: rebuild the API from this source, verify hashes/health/warmup, repeat fresh ordinary-Calgar, armour-Calgar, Guilliman and comparison questions, and confirm the comparison responses are structured without losing the historical/current and ordinary/armour boundaries. The full suite evidence from before this final formatter edit was 2,673 passing; a final-tree full run remains necessary. Browser-level Markdown download/clipboard delivery and the optional official Dreadherder preview projection were not started because the user requested save and stop.
