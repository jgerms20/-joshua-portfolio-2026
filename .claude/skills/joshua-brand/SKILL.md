---
name: joshua-brand
description: Joshua McKenzie German's own visual brand and design system ("The Paper Edition") as implemented in index.html. Use when building or restyling any new page or component on joshuamgerman.com, choosing colors, fonts, spacing, chapter heads, breakers, plate cards, kickers or links, or touching the favicon. Not for Anthropic's brand (that is brand-guidelines).
---

# Joshua brand: The Paper Edition

Source of truth is the `:root` block and component CSS in `index.html` (about lines 30-135 for tokens). Reuse the CSS variables; never hard-code hex values that already have a token. Editorial catalogue feel: warm paper, near-black ink, one electric blue accent, mono labels, serif headlines. Design filter: less, but better.

Note: `design-system.json` at repo root describes an older dark/lime dashboard system. It is NOT the site brand. Ignore it for site work.

## Color tokens (light)
- Paper: `--paper #F5F1E8`, `--paper-warm #EFEADF`, `--paper-raised #FBF8F1`, `--paper-dim #E9E3D5`
- Ink `--ink #171512`; alpha ramp `--ink-soft` .72, `--ink-mid` .52, `--ink-faint` .34, `--ink-ghost` .14
- Rules: `--rule` ink at .16, `--rule-soft` ink at .09 (hairlines, borders, dividers)
- Accent, International Klein Blue: `--blue #1F1DDB`, `--blue-deep #14129E`, `--blue-wash` (7%), `--blue-glow` (22%). The single dominant accent: links on hover, chapter numbers, selection, progress hairline.
- Supporting marks (use sparingly): `--vermilion #E8380D` (cultural-insight label, "down", the favicon dot), `--leaf #2F6B33` ("up", live/network), `--gold #9A7B23`
- Darkroom (dark chapters, `.chapter-dark`): `--dark #12100C`, `--dark-raised #1B1813`, `--dark-rule` / `--dark-rule-soft` (paper at .14 / .08), `--paper-on-dark #F5F1E8` with `-soft` .68, `-mid` .46, `-faint` .30

## Dark mode (Night Edition)
Toggled by `data-theme="dark"` on `<html>`, persisted in localStorage key `jmg-theme` (an inline head script sets it before paint; keep try/catch). Overrides: paper `#14110D`, warm `#191511`, raised `#1C1813`, dim `#0E0C09`; ink `#F0EAE0` with alpha ramp from that; rules at .17 / .09; blue lifts to `#7B79FF` (deep `#9D9BFF`); vermilion `#FF5C33`; gold `#C9A84C`; leaf `#7DC982`. `.chapter-dark` deepens to `#070605` / `#100D0B` with safelight vermilion borders (`rgba(255,92,51,.25)`). Always use tokens so dark mode works for free; check both themes. Art frames use `--art-frame/--art-mat/--art-shadow`.

## Fonts (Google Fonts, already linked in index.html)
- Fraunces (`--serif`), optical size 9..144, weights 300-600 plus italics: all headlines, ledes, plate titles. Display sizes weight 400, tight leading (.86-.95) and letter-spacing -0.015em; titles 500. Italic weight 300 for emphasis words (`.it`) and ledes (`.t-lede`). Pull-quote style: Fraunces italic.
- Space Grotesk (`--sans`), 300-700: body copy (1rem, line-height 1.6; descriptions .92rem / 1.65, color `--ink-soft`), UI text.
- Space Mono (`--mono`), 400/700: kickers, labels, nav-ish text, buttons, tags, counters. Always uppercase, small (.56-.7rem), wide tracking (.1-.22em).
Type scale classes: `.t-mega`, `.t-display`, `.t-title`, `.t-lede`, `.t-mono`, `.t-mono-sm`, `.accent` (blue), `.it`.

## Spacing, layout, motion
- Space: `--s-1 4px, --s0 8, --s1 12, --s2 16, --s3 24, --s4 32, --s5 48, --s6 64, --s7 96, --s8 144`
- `--edge: clamp(20px, 5vw, 72px)` side gutter, `--max: 1560px`; wrap with `.wrap`. Sections are `.chapter` (padding `--s8` top and bottom); dark ones `.chapter-dark`.
- Motion: `--exp cubic-bezier(.16,1,.3,1)`, `--quint`, `--spring`. Respect `prefers-reduced-motion` (breakers stop animating). Reveal class `.rv`.
- Texture: fixed paper `.grain` overlay (opacity .30, .22 in dark), 2px blue `.progress-rail` at top. Selection is blue on paper.
- Breakpoints seen: 820px (plates go single column), 640px (ch-meta left-aligns).

## Recurring components
- Chapter head `.ch-head` (flex, bottom `--rule` hairline, margin-bottom `--s6`): `.ch-head-left` holds `.ch-num` (mono, blue, e.g. "CH. 01") and `.ch-title` (Fraunces, clamp 2.8-6.4rem, italic word in `<span class="it">`); right side `.ch-meta` (mono .62rem uppercase, `--ink-mid`, right-aligned, left on phones). Optional `.ch-intro` (max 620px, 1.02rem, `--ink-soft`).
- Breakers `.brk`: marquee ticker strip between chapters, `--paper-raised` with top/bottom rules, `.brk-track` scrolls 54s linear, pauses on hover, `aria-hidden`. Items `.brk-item` are mono .66rem uppercase, separated by a `|`; `.hi` emphasis, `.up` leaf, `.down` vermilion. Variants `.brk-blue` (Klein blue fill, cream text) and `.brk-ink` (darkroom fill).
- Plate cards `.plates` (12-col grid) / `.plate` (span 6; `.plate-wide` span 12, 21:9 image): `.plate-media` bordered image on `--paper-dim` (16:10, saturate .94, slow zoom on hover), `.plate-index` numbered chip top-left, `.plate-body` with `.plate-tag` (mono kicker), `.plate-title` (Fraunces 500 with an `.arr` arrow that nudges up-right and turns blue), `.plate-desc`, `.plate-channels` (blue mono list with hairline separators), `.plate-culture` (italic Fraunces, with a vermilion mono "Cultural insight" prefix). `.plate-startup` gets a blue edge plus `.plate-flag` pill.
- Mono kickers: small uppercase Space Mono labels above headings (`.plate-tag`, `.archive-kicker`, `.ep-kicker`, `.net-kicker` in green). Pattern: dot or rule + tracking .14-.2em.
- Rule-link `.rule-link`: mono .68rem bold uppercase, tracking .2em, ink text with a 1.5px ink underline; on hover text and underline go blue and the gap to the arrow widens 10px to 16px. Preferred text-link style over underlined body links.
- Buttons `.btn`: pill (radius 999px), mono uppercase, padding 18px 34px.

## Favicon
`favicon.svg` (also `favicon.ico`, `apple-touch-icon.png`): 64x64 rounded square (rx 14) filled Klein blue `#1F1DDB`, a cream `#F5F1E8` italic serif "J", and a vermilion `#E8380D` dot (circle r5.5 at 48.5,48) at the baseline right. Do not redraw; copy the existing SVG. The vermilion dot is the brand's signature small mark.

## When making something new
1. Copy the head (fonts, theme script) and `:root` tokens from index.html; do not fork new palettes.
2. Compose from the components above; add new ones only if none fit, named in the same style.
3. Ink on paper by default, blue as the one accent, vermilion/leaf/gold as rare punctuation.
4. Real photography over generated imagery; hairline rules rather than boxes and shadows.
5. Check light and dark and a phone width.
