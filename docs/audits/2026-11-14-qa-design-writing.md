# QA, design and writing audit (phone first)

Date: 2026-11-15. Snapshot: HEAD `87d2924`, served locally. Chromium via Playwright at 390x844 (touch) and 1440x900, light and dark. External images and fonts were blocked in the sandbox, so fallback tiles and system fonts are expected and not flagged.

Already fixed by Joshua's session before this run, so not re-flagged here: homepage em dashes, scroll-margin on Work/Builds/Media Diet, the 40px theme toggle on the homepage, the scrollable mobile menu, "eleven more builds", the two broken Lab-row sentences, and the timeline "2024–Now".

## What passed

- **Clean on every page:** 26 public pages x 2 sizes x 2 themes, with no page errors, no failed local requests, no sideways scroll and no broken local images. The static link crawl of every local `href` and `#anchor` found nothing broken.
- **House checks:** `check-refs.py` found 0 broken refs. `check-site.py --root .` found 0 broken, 0 degraded. `render-photography.py --check` says both pages are current. 247 unit tests pass.
- **Theme:** the toggle persists across reload and across pages on all 10 pages tested (localStorage `jmg-theme`).
- **Media Diet:**
  - Tabs, `#listening` deep link and the document title all update.
  - Search works for a match ("Matrix" returns 1 of 50), for no match (shows an empty state with a Clear button) and for Clear.
  - All five film sorts and the three Reading/Listening sorts reorder correctly.
  - Rating plus decade filters work (5 stars returns 8; 5 stars in the 1970s returns 1).
  - Paging goes through pages 1, 2 and 3 and back. Each page change scrolls the tabs back under the bar.
- **Brand Work filter:** every agency shows only its own cards (TBWA 11, W+K 2, GS&P 6, Independent 2), "All" brings back 21, and empty groups hide. `aria-pressed` is correct.
- **Photography:**
  - The Work, About and Book views route by hash and move focus to the view heading.
  - The viewer opens from all five sets. Arrow keys step through frames.
  - Esc, the Close button and browser Back all close it and restore the scroll position.
  - The sticky "Book a shoot" bar clears the footer.
- **Lightboxes:** the homepage photo lightbox (Esc, Close, arrows, body scroll lock released, focus returned to the tile), the homepage art dialog and the shop product view all close correctly. The cart count updates.
- **Mobile menu:** every hash link closes the menu, releases scroll lock and lands on its section with the heading in view. At 375x667 it scrolls (`overflow-y: auto`).

## 1. Bugs, worst first

### B1. Builds badges are invisible in dark mode on the homepage (High: visible to everyone in Night Edition)
- **Repro:** open `index.html` on a phone, switch to dark, scroll to Ch. 05 Builds. The "Invite only" and "Live" pills on the three case-study cards are blank cream lozenges.
- **Cause:** `index.html` line 925, `.lab-status`, hard-codes `background: rgba(245,241,232,0.94)` and uses `color: var(--ink)`. In dark mode `--ink` is near-white, so the text is cream on cream. `builds/builds.css` line 447 already does it right with `background: var(--paper-raised)`.
- **Fix:** use the same token on the homepage. Also raise the size from 0.52rem (8.3px) to the 0.56rem brand minimum.

### B2. Gen Alpha Lab rights deadline is tomorrow (High: a public-launch decision, not code)
- **Where:** the draft note on `builds/gen-alpha-intelligence-lab.html` says to unlink the page before Nov 16 unless the rights are confirmed.
- **Why it matters:** the page is still linked from the homepage Builds card and `builds/`. The public view also has no content yet for "The problem", "The insight" or "What changed because of it". They are TODOs, hidden unless `?draft`.
- **Same gap elsewhere:** Meme Library and Life Gamified also have no public text for their reasoning and outcome sections yet.

### B3. Esc does not close the homepage mobile menu, and the burger has no `aria-expanded` (Medium)
- **Repro:** at 390 wide, tap the burger, then press Esc (hardware keyboard or a screen reader's escape gesture). The menu stays open; only the burger closes it.
- **Fix:** in `index.html` around line 2464, add a keydown handler for Escape that calls `close()`. Set `aria-expanded` and `aria-controls="mobileMenu"` on `#navBurger`.

### B4. Tap targets under 40px on phone (Medium: the theme toggle was fixed on the homepage only)

| Element | Size | Where |
|---|---|---|
| Theme toggle | 36x36 | work/, all 12 case studies, builds/, the 3 build pages, shop.html, photography/ |
| Theme toggle | 38x38 | network/, media-diet/, all 4 podcast pages |
| `a.nav-brand` (home link reduced to a dot) | 7x7 | work/ and every case study and build page |
| "Book a shoot →" nav link | 96x15, 9.3px | work/, case studies, builds |
| "← All Brand Work" / "← All Builds" | 23px tall | case studies and build pages |
| `.rule-link` "Back to …" | 17–24px tall | same pages |
| Homepage burger | 38x31 | index.html |
| Photo lightbox close | 33x41 | index.html |
| Media Diet chips | 34px | media-diet/ |
| Brand Work filter pills | 31px | work/ |
| Shop filter pills | 29px | shop.html |
| Shop cart button | 36x36 | shop.html |
| "Tell me" (bug report link) | 42x12 | index.html footer |
| "Book a shoot" footer link | 94x12 | photography/ |

**Fix:** min-height 44px (padding, not font size) on nav and back links, pills and chips, and the shared theme toggle.

### B5. Text under 12px on phone is widespread (Low as a bug, real for legibility)
The mono labels are 9–10px nearly everywhere (`.ch-meta` 9.9px, footer copyright 9.3px, award chips 9px, `.meta-label` 9px). Under 9px:

- builds/ `.lab-status` (8.3px), `.lab-tag` (8.8px), `.lab-platform` and `.lab-cta` (8.6px)
- media-diet/ `.md-when` (8.0px) and `.md-tab-count` (8.6px)
- shop.html footer line (8.0px)
- work/ "AI Visibility Venture" (8.8px)

Labels are brand-sanctioned at .56–.7rem. Proposal: floor them at 0.62rem (9.9px) on phone and never go below 0.56rem.

### B6. Em dashes remain in case-study prose and the shop (Low: house rule)
The homepage is clean. Counts below are visible text and include the "01 — Challenge" label separators. Fix the prose ones first:

- work-gatorade 134
- work-mlb 44
- work-directv 38
- work-dwb 37
- work-levis 23
- work-preach 22
- work-doordash 21
- work-samadams 18
- work-califia 14
- work-sephora 14
- work-xfinity 14
- work-bmw 12
- shop.html 8

Example: "Switching to plant-based isn't a sacrifice—it's a discovery." (Califia). In the shop: "Request the order — it drafts an email to me." becomes "Request the order. It drafts an email to me."

### B7. Small factual or consistency slips (Low)
- **Levi's role typo:** `work/work-levis.html` line 600 says "Senior Connection Strategist"; everywhere else says "Connections". `work-template.html` line 458 has the same typo, so new pages will copy it.
- **Name spelling:** "Levi's x Beyoncé" and "Levi's × Beyoncé" both appear (the homepage uses both). Pick one.
- **Two job titles:** the Levi's case study quotes Kenny Mitchell twice with two titles ("Global Chief Marketing Officer, Levi's" and "CMO, Levi Strauss & Co."). One quote with one title is enough.

### B8. Last Media Diet page leaves the tabs off screen (Low)
- **Repro:** on a phone, page to Watching page 3 (2 films). The page is too short to scroll the tabs back under the bar, so you land with the chips half under the header and no tabs in view.
- **Fix:** give the grid a `min-height` equal to one full page, or scroll the app container instead of the tabs.

## 2. Design fixes, ranked ("less, but better")

1. **One header, everywhere.** There are five header patterns:
   - Homepage: fixed nav with burger.
   - Work and Builds: a lone 7px dot plus a tiny "← Home".
   - Shop: "Photography ← Back".
   - Network, Media Diet and podcasts: "← Home · JMG" bar plus a black pill.
   - Photography: its own two-row nav.

   On a phone the Work and Builds header reads as empty. Use the homepage nav (name, theme, burger) on every Joshua page. Keep the photography site's own nav, because it is a separate product.
2. **Cut the homepage tickers from five to one.** Five marquee strips of invented percentages ("DOUBT ▼ -4.0%", "SLEEP ▼ -2.1%") break the page into slices and add about two phone screens of noise. Keep one, between the hero and About, as the signature.
3. **The homepage repeats the sub-sites instead of pointing to them.**
   - The Photography chapter carries two vermilion booking links, KOAT coverage, filters, a 37-photo grid and a sets row.
   - Brand Work shows 8 full plates.
   - On Air stacks three full-width covers.
   - Art runs six full-width collages, about six phone screens.

   Show three of each with one rule-link to the full page, and put the art in a 2-column grid on phones. The homepage is 27,400px tall on a phone.
4. **Award chips with emoji fight the type system.** DoorDash carries five chips (🏆✏️🦁✏️🎖️) and DWB four. Make them plain mono text with hairline separators ("Cannes Titanium Grand Prix · D&AD Yellow Pencil · 8 Cannes Lions"), show the top one on cards, and keep the full list on the case study.
5. **Builds cards break the plate language.** The homepage and builds/ use boxed cards with shadows and generated illustrations (alpha glyph, magnifier, shield) while every other chapter uses hairline plates over real imagery. Use real screenshots, or drop the art and go type-only plates. The brand rule is real over generated.
6. **The contact chapter is three lists deep.** "Available for", "Focused on" and "Spaces" add up to 25 rows that mostly restate each other, under a generic "Let's create together." Keep "Available for" (5 rows), cut the other two, and lead with the email.
7. **Back-to-top button sits on body copy on phones.** The 46px black disc at bottom right overlaps paragraph text through About and Art. Show it only after Contact is in view, or give it an inset with a paper ring.
8. **Hero facts row is staggered on desktop.** The Now, Independent and Previously columns start at three different heights (782, 805, 852px), and "Previously" wraps one agency per line. Top-align the columns and put the agencies on one line ("TBWA\Chiat\Day · W+K · GS&P").
9. **Dark mode misses besides B1.** The DIRECTV logo plate and the Curious & Creative logo sit on bright white boxes in Night Edition. Give logo plates `--paper-raised` in dark, or `mix-blend-mode: multiply` in light only.
10. **Sub-brand accents drift.** Network uses leaf green, podcast pages gold, photography vermilion and Joshua's pages Klein blue, each with its own button style (sans "Visit the site" pills on Network versus mono pills elsewhere). The colour choice is defensible per brand, but keep one button style (mono, pill) across all of them.
11. **Network lists many AI-generated shows at equal weight.** Fast Break, Once Upon a Time in Harlem, Gamecocks Daily, The TV Insider, The New York Read and others sit beside the flagship. Group them under one "AI-generated shows" row that expands, so the hosted shows lead.
12. **Photography has three "Book a shoot" buttons in view at once on a phone** (nav, footer line, sticky bar). Drop the footer-line link.

## 3. Copy rewrites (his voice: plain, direct, no em dashes, no new facts)

Kept as approved: "I find the idea and build the thing.", "Strategy, stories, and the things I build when nobody assigned them.", and the About paragraph beginning "My work starts with curiosity."

### Homepage and Brand Work cards (index.html, work/index.html)
| Now | Problem | Rewrite |
|---|---|---|
| Redefining an icon. A cultural reset for the denim giant that reimagined American heritage through a modern lens. | Stock hype, three clichés | Levi's and Beyoncé, built on Cowboy Carter and the Black roots of country. |
| An entertainment partnership that took Gatorade into the Upside Down for the final season of a cultural phenomenon. | "cultural phenomenon" | Gatorade went into the Upside Down for Stranger Things' final season. |
| Cannes Grand Prix winning Super Bowl phenomenon. | Not a sentence; hype | The Super Bowl ad that gave away everything in all the other ads. (check against the case study before using) |
| MLB's first brand platform in 8 years. Gen Z favorability up 10 points. The campaign that brought a new generation to the ballpark. | Third line restates the second | MLB's first brand platform in 8 years. Gen Z favorability up 10 points. |
| Arnold & Salma. The ultimate electric driving machine. | Tagline, not a description | Arnold and Salma as Zeus and Hera, for BMW's first electric Super Bowl spot. (confirm "first") |
| A joyful celebration of plant-based living. | Generic | Plant milk sold as joy, not virtue. |
| Steve Carell as Santa. Holiday campaign orchestration with strategic influencer partnerships. | "orchestration", "strategic" | Steve Carell as Santa, for a holiday most people spent apart. |
| Sephora's skincare platform, built for the skin-obsessed. | Fine; slightly ad-speak | Sephora's skincare platform, for people who read every ingredient list. |
| Holiday gifting made effortless, directed by Taika Waititi. | "effortless" is the brief, not the work | Taika Waititi directs Sephora's holiday gifting campaign: don't overthink it. |
| Gatorade's global football platform: fuel and belief, built from the inside out. | Abstract | Gatorade's global football platform, made with fans from six nations before the 2026 World Cup. |
| Brand, audience, and go-to-market strategy, built from the ground up for a film festival research and submission platform. | "built from the ground up" | Brand, audience and launch strategy for HIIKE, a platform for researching and submitting to film festivals. |
| Fractional CMO for an AI-visibility venture, leading marketing strategy, brand direction, and go-to-market. | List of nouns | Fractional CMO for U&AI: I run marketing, brand and launch. |
| Connections and cultural strategy: finding the truth a community already lives by, then carrying one idea across film, social, out-of-home, partnerships and real-world moments so every piece hands off to the next. | One 40-word sentence | I find the truth a community already lives by. Then I carry one idea across every channel so each piece hands off to the next. |
| Agency campaigns were made with the teams at each agency; my role is on every card. The two startups are independent work, not agency briefs. Years come from each case study. | Reads like a disclaimer | Agency work was made with the teams at each agency. My role is on every card. The two startups are my own independent work. |
| Have a brief that needs a cultural way in? | Good. Keep. | |

### Homepage other chapters
| Now | Problem | Rewrite |
|---|---|---|
| Creative, cultural & content strategist who builds with AI | Three adjectives stacked | Creative and cultural strategist. I build with AI. |
| I'm Joshua. Curious and creative, and happiest telling stories in whatever medium fits. | Fine; slightly soft | Keep, or: I'm Joshua. I tell stories in whatever medium fits. |
| Demystifying AI, one episode at a time. No jargon, just what's actually happening and why it matters. | Stock podcast blurb | AI without the jargon. I build things on camera and show my work. (his own words from About) |
| With co-host Janel Moore. Where creative strategy meets real conversation: the ideas, decisions, and cultural moments that shape how we see, and sell, the world. | "Where X meets Y" formula | Janel Moore and I talk about the ideas and cultural moments that shape how we see, and sell, the world. |
| Everything is interesting when you dig deep enough. Deep dives on history, geopolitics, power, culture, and human behavior. No lane. No niche. Curiosity without borders. | Four slogans; "No lane. No niche." also appears three times on the show page | Everything is interesting if you dig deep enough. History, power, culture and why people do what they do. |
| I don't stop at the recommendation. When a question about culture is worth answering, I build the tool that answers it, with AI as a collaborator and my own hands on the production. Three case studies first, then everything in the lab, labeled for what it is. | Last sentence is stage direction | I don't stop at the recommendation. When a question about culture is worth answering, I build the tool that answers it. AI helps; the decisions are mine. |
| A fully-gamified RPG quest journal for real life. … Because life should feel like an epic adventure. | Hype, cliché closer | A to-do list that plays like an RPG. Tasks are quests, finishing them earns XP, and the rewards are real ones you choose. |
| Inputs become outputs. Here's everything going in, pulled live from where I log it. Flip, sort and filter. | Slogan plus UI instructions | What I'm watching, reading and listening to, pulled from where I log it. |
| Let's create together. | Generic | Now booking independent work. (the kicker above it already says this, so promote it and cut the kicker) |
| Strategy projects, AI builds, speaking, writing, or a good conversation about culture and technology: write to me directly. | Fine | Keep. |
| "From Columbia to Los Angeles, same instinct the whole way: find the real story, then tell it better than I found it." | Sounds like him | Keep. |

### Builds (builds/index.html Lab rows)
| Now | Problem | Rewrite |
|---|---|---|
| AI-powered bias detection for news and media. Analyze content for perspective, compare sources, and see the full picture. | "AI-powered" plus "see the full picture" | Checks a news story for slant and shows how other outlets covered it. |
| AI-powered influencer and creator discovery. Find the perfect creators for your brand based on audience, style, and engagement. | "perfect" | Finds creators for a brand by audience, style and engagement. |
| AI-powered wardrobe organizer. Catalog, style, and manage your closet with intelligent outfit recommendations. | "intelligent" | Catalogs your closet and suggests outfits from what you own. |
| Letterboxd for music. Track, rate, and review albums. Share your musical journey and discover new sounds. | "musical journey" | Letterboxd for music. Track, rate and review albums. |
| AI-generated binaural beats for focus, relaxation, and meditation. Custom soundscapes tailored to your mental state. | "tailored to your mental state" | Generates binaural beats for focus, rest or meditation. |
| AI-powered productivity and goal tracking. Build momentum with intelligent task management and progress insights. | Pun plus buzzwords | Goal tracking that shows whether you're actually moving. |
| Design your ideal day with AI. Plan routines, optimize your schedule, and build habits that align with your goals. | Self-help copy | Plans a day around your routines and goals. |
| A living research lab on the forces shaping Gen Alpha culture: insights, findings, creators, and the spaces they actually occupy … | Long noun list | A research lab on Gen Alpha culture: the creators, the spaces they actually use, and the evidence behind each finding. |

### Photography (photography/index.html)
Mostly strong and plain. Two tweaks:
- "Los Angeles photographer: portraits, fashion and event coverage, on 35mm film and digital." Keep.
- "I grew up in South Carolina and started out in journalism, because I've always wanted to know what makes people tick." The homepage says "loved figuring out what makes people tick". Use one phrasing on both pages.

### Network (network/index.html)
| Now | Problem | Rewrite |
|---|---|---|
| Curious & Creative is a Los Angeles creative company built by Joshua German and Janel Moore. We run a media network, produce photography, video, editing, and podcasts through our studio, and advise founders, brands, and marketing teams on culture, audience, and AI. | One long sentence | Curious & Creative is Janel Moore's and my company in Los Angeles. We run a media network, a studio that makes photos, video and podcasts, and a consultancy on culture, audience and AI. |
| Culture, audience, and AI. / We advise founders, brands, and marketing teams on culture, audience, and AI. | Heading repeated as the sentence | Keep the heading; change the line to: We advise founders, brands and marketing teams. |
| AI workflows that actually help your team, and the know-how to use them. | "actually", "know-how" | AI workflows your team will use, and the training to run them. |
| Photography, video, editing, and podcasts, made by the same people who run the Network. We shoot it, film it, cut it, and launch it. | Second sentence is fine; first repeats the list above | We shoot it, film it, cut it and launch it. The same people who run the Network. |
| A podcast by Joshua German. (God Is Brazilian) | Placeholder | Needs a one-line premise from Joshua. |
| A morning read, made with AI. / A daily dose of jazz, made with AI. | Empty | Say what each episode is: for example, "One news story a morning, read in ten minutes." (Joshua to confirm the real format) |
| The Network is our media network, with Joshua as principal. Some shows are hosted by Joshua, Janel, or both; some are AI-generated; one is a hybrid of a host and AI. The flagship leads, then The Eclectic Polymath; the rest sort by what dropped most recently. | Explains the sort order | Our shows. Some we host, some are made with AI, and every card says which. |

## Method notes
- Scripts and screenshots are in the session scratchpad (`pw/qa/`): `audit.js` (per page, size and theme), `interact.js` (menu, theme, Media Diet, filter, photography, lightboxes, anchors), `mdpage.js`, `ph2.js`, `badge.js`, and viewport-by-viewport phone frames stitched into contact sheets (`fs/`).
- The anchor check flagged `#top` links as "under the nav". Those are false positives because the target is the page top.
