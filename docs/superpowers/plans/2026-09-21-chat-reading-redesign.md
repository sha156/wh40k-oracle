# Readable chat and evidence-based rule comparisons

The user asked to replace the verdict/dashboard presentation with a simpler conversational interface, and to answer broad questions fully in one response. They explicitly clarified that the original Warhammer visual style must remain: simplify the dialogue, not the site's branding, colors or header. DeepSeek Flash is an explicit cost constraint; do not switch to Pro.

## Acceptance

1. Keep the existing dark teal/black, bone text, red accents and Aquila header. Keep all turns visible in a readable conversation, with a multiline composer, keyboard/IME handling, loading/error states and a new-conversation action.
2. Show the opening, every explanation paragraph and relevant limits together. Sources, diagnostic trace and full datasheets are secondary expandable details. Preserve per-answer Markdown export and copying.
3. Keep simple factual questions concise. Broad rule explanations and comparisons must include the applicable baseline, verified changes and unchanged parts, practical consequences, and relevant conditions without requiring another user prompt to obtain the main answer.
   Completeness means retaining independent facts, not repeating an audit checklist. Lead with the practical answer, group related content, explain unfamiliar shorthand and state each qualification once. The user rejected the initial twelve-paragraph repetitive Oath response; preserve it as failed evidence.
4. A current replacement paragraph alone cannot establish its previous wording or the date every clause changed. Retrieve prior evidence or explicitly disclose that it is missing. Check whether faction-specific army rules replace an ability before inferring eligibility from an exclusion list.
5. Verify the exact Guilliman short-name question, a two-unit citation comparison, the supplied Oath of Moment comparison, a follow-up in the same session, new-session isolation, desktop/mobile layout, and existing roster/simulator/codex routes.

## Implementation boundaries

- Preserve the existing Answer and SSE contracts. The frontend presents all content as one assistant message instead of hiding the explanation beneath a calculation label.
- Use `deepseek-flash` with thinking disabled in agent, formatter and classic fallback. Classification stays at eight output tokens; complete answers/layout have a 3,200-token ceiling. This is a maximum, not a requested minimum answer length.
- Keep numeric source identity and refusal of uncertain fuzzy matches. Reproject the one verified Guilliman alias through the existing community-alias stage; no point values change.
- Correct the manually curated Oath reference through the wiki's query/edit/build/lint/log workflow. Generated indexes are changed only by their commands.
- Cloud, the remaining public-source Ork rules, and Docker host restart durability remain outside this release's completion claims.

## Evidence and rollout

The September 21 review report will record actual tests and deployed behavior. PR #75 contains this continuation. Rebuild and check the local images before marking the PR ready. Preserve failed live responses when a later iteration corrects them. The earlier separately blocked external handoff publication remains pending; project-local notes remain the current handoff.

User requested save and stop after adding the ordinary-Calgar source-retention issue. The restored desktop style and readable copy are running; final dark mobile verification and the Calgar integration remain open. See `../reports/2026-09-21-paused-chat-calgar-checkpoint.md` for passing checks, failing draft tests, uncommitted files and resume order. Do not treat the first light-theme commit as the accepted final design.
