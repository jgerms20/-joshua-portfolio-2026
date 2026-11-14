---
name: portfolio-house-rules
description: Standing rules for any work on Joshua's portfolio repo (joshuamgerman.com). Use at the start of any task here, and always when writing or editing copy in Joshua's voice, adding clients, case studies, metrics or counts, changing design, handling photos, branching or pushing, interpreting his instructions, or before declaring work done.
---

# Portfolio house rules

## Positioning and voice
- Strategist first: Joshua is a creative and cultural strategist who builds. Never lead with "AI strategist" or an AI-first label. AI is a tool he uses, not his title.
- Never use em dashes in copy written in Joshua's voice. Use a period, comma, colon or parentheses. (Existing code may use the entity for a typographic purpose; do not add em dashes to new copy.)
- Preserve the existing voice and design language. Edit in place; do not restyle or rewrite what was not asked.

## Truthfulness
- Never invent clients, metrics, results, dates or capabilities. If something is not confirmed by Joshua or a verifiable source, leave it out or label it clearly as unconfirmed.
- No hard-coded show, episode or follower counts. Derive them from data or omit.
- Brand work is agency work: label it with the agency and year. Never present it as Curious & Creative client work.

## Reading instructions
- Explicit orders: do them.
- Tentative ideas ("maybe", "what if"): propose and wait for a yes.
- "Eventually" or later-someday items: park them (note them), do not build now.
- Brainstorming is not an order.

## Design filter
- "Less, but better" (Dieter Rams). Remove before adding.
- Real photography over generated imagery.
- Follow the joshua-brand skill for tokens and components.

## Git
- One working branch: `claude/portfolio-continuous-memory-g1Fi3`. Do not create other branches.
- No pull requests (they auto-merge). Commit and push to the branch only when asked.

## Before calling anything done
Run all of these from the repo root and report real results:
1. `python3 -m unittest discover -s tests`
2. `python3 scripts/check-refs.py`
3. `python3 scripts/render-photography.py --check`
4. `python3 scripts/check-site.py --root .`
5. Browser smoke test `tests/browser/smoke.js` (Playwright). In cloud sessions launch Chromium with `executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'`. The webapp-testing skill helps.
Also: after removing or moving any page, check every link that pointed to it (internal links, nav, sitemap, redirects).
