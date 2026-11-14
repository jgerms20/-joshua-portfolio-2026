# Recruiter lens and public-mentions audit (2026-11-14)

Scope: read-only review of index.html, work/index.html, work/work-doordash.html, work/work-levis.html, builds/index.html, builds/gen-alpha-intelligence-lab.html, photography/index.html, network/index.html. Part B used WebSearch only. WebFetch could not reach external hosts (musebyclios.com, oneclub.org, adsoftheworld.com, podcasts.apple.com, audible.fr all failed DNS in this session), so every web finding below is a search-result summary, not a page I opened. Verify each link by hand before citing it.

---

## PART A. Recruiter / hiring-manager lens

### What the site does well (all three readers)
- Hero line and status are instant: "I find the idea and build the thing." plus "Now booking independent work." (index.html hero). Availability is stated in four places (hero, About "Status", contact block, ticker).
- Role is printed on every campaign card ("Senior Connections Strategist • TBWA\Chiat\Day"), and work/index.html has an honest note: "my role is on every card" and flags startups as independent. This is rare and credible.
- Case pages have a "My Role" section with verbs (levis: "built the channel strategy", "sequenced the content drops"; doordash: "helped coordinate outreach", "helped run real-time social").
- Metrics exist on both case pages (Levi's ledger: $65M EMV/48h, 4.3B impressions, 19.87% store traffic, 8% global sales; DoorDash: 6.8B impressions, $50M+ earned).
- Builds page labels Live vs Prototype, which signals honesty to an AI-company reader.
- Contact paths are plain: mailto with a prefilled project-inquiry body asking timeline and budget (index.html contact block).

### Reader 1: freelance strategy recruiter at a staffing firm
First 10 seconds: title, seniority, location, availability, can I submit this person today. Wants: resume/PDF, rate, W-2/1099/corp-to-corp, start date, remote vs on-site, references.
First 2 minutes: scans agency names and brands, checks tenure dates, looks for a resume link, tries to forward the profile to a client in one click.

Answers well: Los Angeles; "Now booking independent work"; agency pedigree is above the fold ("Previously: TBWA\Chiat\Day, Wieden+Kennedy, Goodby Silverstein & Partners"); Cannes/D&AD/One Show badges on cards.

Missing or confusing:
1. No resume or PDF. Grep for "resume" in index.html and work/*.html returns nothing in the visible UI. A recruiter cannot forward a one-pager. (Fix: add "Download resume (PDF)" in the hero CTA row and footer.)
2. LinkedIn exists only as a footer icon (index.html contact block, https://www.linkedin.com/in/joshua-german/). Recruiters live in LinkedIn; it should be in the header or hero.
3. No engagement model: nothing says fractional vs project vs full-time-contract, minimum engagement, day rate or "rates on request". Photography says "Rates quoted per project" (photography/index.html), but strategy has no equivalent line. Compare the strongest signal on the site, "Budget range:" in the mailto body, which is invisible until the email opens.
4. Availability has no date or capacity ("Now booking" with no start date, hours/week, or remote/on-site). Title says independent, network page says "Joshua is now independent and full time on the company" (network/index.html), which a recruiter may read as unavailable for contract work. Two statements pull against each other.
5. Phone: "Available upon request" is fine, but there is no scheduling link. Add Calendly or equivalent.
6. Title inconsistency creates reference-check risk. Same job at W+K appears as "Media & Comms Supervisor" (index.html card, work/index.html), "Media & Communications Strategist" (work/work-doordash.html role field and My Role), and "Brand Strategist" (work/index.html MLB card, W+K Portland). Public credits (see Part B) say "Communications Supervisor". Pick one exact title per employer and use it everywhere. Same for GS&P: "Communication Strategist" vs "Communications Strategist" (work/index.html uses both spellings). TBWA: "Senior Connections Strategist" vs "Senior Connection Strategist" (work/work-levis.html role field is singular "Connection").
7. Agency tenure is in the work/index.html header (2020-2026) but there is no single employment timeline a recruiter can scan. The About page has a place-based timeline, not a role-based one.
8. Ticker items ("Sleep -2.1%", "Curiosity +inf", "Cannes Grand Prix Work +3.8%") are charming but read as noise to a skimming recruiter and the fake percentages could look like claims.

Top fixes: resume PDF + LinkedIn in hero; a one-line "How I work" (fractional / project / embedded; remote or LA; typical start); one "Rates on request" line; unify titles; add a calendar link.

### Reader 2: hiring manager, content/creative strategy role at an AI company
First 10 seconds: does this person understand AI practically, and can they write. First 2 minutes: opens Builds, picks one case study, looks for what he decided vs what the model did, tools, evidence of use.

Answers well: "Creative & cultural strategist who builds with AI"; tool names in the ticker (Claude Code, Google AI Studio, Prompt Engineering); builds/index.html lists stacks (React 19 and Claude Code, Next.js 16 and Supabase, Web Audio API); three case studies first, then eleven in the lab labeled Live/Prototype; Approachable AI show; "AI Strategy and Systems Lead" mention in the About copy (index.html About).

Missing or confusing:
1. The featured Builds case study is unfinished. builds/gen-alpha-intelligence-lab.html contains six "TODO for Joshua" blocks (problem, insight, orchestration, limits, what changed, screenshots) and a rights warning. The page says "Draft view ... Remove ?draft to see the public page", so the public view may hide these, but the underlying page is a shell: no screenshots, no outcome, "Invite only", "Built with Codex" (an AI hiring manager will notice it is not Claude). The TODO itself says to unlink before Nov 16 if rights cannot be confirmed (it began as an agency assignment). That is a live risk, not just polish. Confirm the public view and decide this week.
2. Even where complete, builds/index.html has no outcomes: no users, usage, time-to-build, or "what I decided vs what AI wrote". Meme Library claims "1,000+ clips" but there is no proof on the index.
3. No writing sample for the "content" part of "content strategy". Notes/Field Notes exists on the homepage but is a heading with no excerpts visible in the text extract. Link two or three pieces.
4. No evals/judgment signals: prompt design, failure cases, how he'd measure content quality. A short "How I work with models" section would answer the question this reader actually has.
5. Agency work is mostly consumer/CPG/entertainment. The AI-company reader needs a bridge: one case study reframed as "what this teaches about AI product storytelling" or a POV piece.
6. No LinkedIn/resume (same as Reader 1) and no stated interest in full-time vs contract at an AI company.

Top fixes: finish or pull the Gen Alpha case study; add screenshots and a "what I decided vs the model" paragraph to every featured build; link 2-3 writing samples; add a "How I use AI" paragraph above Builds.

### Reader 3: small-brand founder looking to hire him
First 10 seconds: can he help a business like mine, how do I start, what will it cost. First 2 minutes: looks for a service list, a small-business example, price signal, process, a button.

Answers well: "Available For" list (positioning, audience, go-to-market; AI builds and workflow design; photography/video/podcast through the Studio); "Start a Project" button with prefilled questions; HIIKE and U&AI startup cards (work/index.html section 02) are the closest to a small-brand proof; network/index.html explains Studio vs Consultancy with plain service lists (podcast strategy, audience systems, AI workflow enablement).

Missing or confusing:
1. Almost all featured proof is Fortune-500 scale (Levi's, DoorDash, Gatorade). A small founder asks "can he work at my size?" HIIKE and U&AI are buried as second section and have no outcomes (cards list deliverables only, no results or client quote).
2. Three doors, unclear which to knock on: joshuamgerman.com "Let's Talk", Curious & Creative Studio form, Consultancy form (network/index.html). The homepage says shoots go through the company and strategy goes by email; the network page says Joshua is full time on the company. A founder will not know whether they hire Joshua or a company. Say it once, at the top.
3. No pricing, packages, or example engagements ("2-week positioning sprint", "podcast launch package"). Even "projects start at $X" or "retainers from $X" cuts email back-and-forth.
4. No testimonials from clients. A testimonials skill exists in this repo's tooling, yet the extracted pages show none. Founders trust one sentence from a peer over a Cannes badge.
5. No process or timeline ("what happens after I email").
6. Agency credits are collaborative; the Levi's "My Role" paragraph is good but outcomes ($65M, 19.87%) are campaign-level, not attributable to him. A founder may assume he drove them. The work/index.html disclaimer helps; repeat a one-line "team result, my part was X" near the ledger on work/work-levis.html.

Top fixes: lift HIIKE/U&AI above or beside the featured six with one result each; add 2-3 packages with a price or "from" range; add one client or collaborator quote; clarify who to hire (him vs the company).

### Cross-cutting issues (specific, with files)
| Issue | Where | Fix |
|---|---|---|
| No resume | index.html (none) | PDF link in hero + footer |
| LinkedIn buried | index.html contact block only | add to nav/hero |
| Role/title drift | index.html, work/index.html, work/work-doordash.html, work/work-levis.html | one canonical title per employer |
| DoorDash role framing | work/work-doordash.html "My Role" is strong but title "Media & Communications Strategist" differs from public credit "Communications Supervisor" | align to credit, or note both |
| Award counts on DoorDash | work/index.html card: "7× One Show Gold", "8× Cannes Lions"; work/work-doordash.html: "14+ total One Show Pencils", also "Cannes Titanium Grand Prix" while case study eyebrow says "Cannes Grand Prix". Search results showed a Cannes Titanium entry and One Show page; the One Show page snippet mentions a Merit. Verify counts against the official One Club and Cannes pages (use /results-check). | verify; reduce to what can be sourced |
| Metrics sourcing | work/work-doordash.html "6.8B impressions / $50M+ / #1" and work/work-levis.html ledger have no visible source link | footnote with source or "per agency case study" |
| Draft page publicly reachable | builds/gen-alpha-intelligence-lab.html TODO banner | resolve rights before Nov 16 or unlink |
| Availability inconsistency | index.html "Now booking" vs network/index.html "full time on the company" | one sentence reconciling |
| Photography | photography/index.html is clean: clear services, "Rates quoted per project", email, IG. Only gap: no sample rates/packages, no testimonials, no event-coverage proof beyond KOAT SS27 (Nov 7, 2026). | add 1-2 client names or quotes |

---

## PART B. Public mentions finder

Method: 16+ WebSearch queries. The search backend is not a people-search; "no result" does not prove absence. Pages could not be opened (see note at top). "Names him?" is only "yes" where the search snippet or summary showed his name.

### Confirmed or probable mentions naming him

| # | URL | What it says (from snippet) | Names him? |
|---|---|---|---|
| 1 | https://www.adsoftheworld.com/campaigns/doordash-all-the-ads | W+K Portland credit list; search summary reports "Communications Supervisor: Joshua German" | Yes, per search summary. Page not opened. |
| 2 | https://www.llllitl.fr/2024/06/doordash-all-the-ads/ | Repeats the same credit list incl. "Communications Supervisor: Joshua German" | Yes, per search summary. Not opened. |
| 3 | https://musebyclios.com/?p=42364 (also https://prod.musebyclios.com/?p=42364) "This Mobile Game From GS&P Opens a Window Into Black History" | Preach, BLK ERG Instagram/Facebook stories game. Creative credit lists "Josh German, Ezana Ataklti, Karyna Luong, Shareina Chandler, Malika Reid"; German and Ataklti also described as game designers | Yes ("Josh German"), per search summary. Name lists were jumbled in extraction; confirm roles by opening. |

Note on #1: the credit title "Communications Supervisor" differs from the site's "Media & Communications Strategist" (work-doordash.html) and "Media & Comms Supervisor" (index.html). Worth matching.

### Campaign pages that exist but do NOT show his name in what I saw (cite for the work, not for him)
| Campaign | URL | Notes |
|---|---|---|
| DoorDash All The Ads, One Show | https://www.oneclub.org/awards/theoneshow/-award/52839/doordash-all-the-ads/ | Summary says credits list Hannah Gulla (Sr Brand Strategist), Rachita Vasan (Sr Strategist); German not shown. Candidate for a credit request. |
| DoorDash All The Ads, Cannes Titanium | https://lovethework.com/work-awards/entries/718171 and campaign page https://lovethework.com/work-awards/campaigns/doordash-all-the-ads-1617392 | Cannes credit tabs not read. Check Credits tab. Other DoorDash Cannes entries: lovethework.com/work-awards/entries/717104, 711326, 712923, 716488, 712365. |
| DoorDash case study video | https://vimeo.com/936503180 | Summary credits Rachita Vasan, Andy Lindblade, Hannah Gulla; not him. |
| DoorDash press | https://www.mediapost.com/publications/article/392620/wk-to-help-doordash-craft-its-super-bowl-ads-this.html ; https://lbbonline.com/work/108180 ; https://www.peterfisk.com/?p=24501 ; https://www.fastcompany.com/91236111/doordash-brands-that-matter-2024 ; https://www.adweek.com/agencies/doordash-wieden-kennedy-creative-agency-super-bowl/ | Campaign coverage; no personal mention seen. Peter Fisk already linked on the case page. |
| Levi's x Beyonce REIIMAGINE, Clio Silver 2026 | https://clios.com/winners-gallery/details?id=218310 | Clio listing confirms Silver 2026, entrant TBWA\Chiat\Day LA. Individual credits behind login. |
| REIIMAGINE, agency page | https://tbwa.com/work/levis-reiimagine/ | Agency case page; no individual credits seen. |
| REIIMAGINE press | https://www.businesswire.com/news/home/20240930181049/en ; https://investors.levistrauss.com/news/financial-news/news-details/2025/Beyonc-and-Levis-Launch-Chapter-2-with-REIIMAGINE-Pool-Hall/default.aspx ; https://lbb.lbbonline.com/news/levis-iconic-launderette-ad-is-reimagined-with-beyonce-in-global-campaign ; https://www.marketingdive.com/news/levis-beyonce-nostalgia-launderette-culture-campaign/728394/ | No personal mention seen. |
| Driving While Black | https://musebyclios.com/?p=35766 ; https://www.adsoftheworld.com/campaigns/driving-while-black ; https://lbbonline.com/news/this-car-shines-a-light-on-the-double-standard-in-policing-of-black-people-in-america ; https://themill.com/the-mill/work/driving-while-black ; https://creativepool.com/valerie-carlson/projects/driving-while-black-for-courageous-conversation-global-foundation ; https://www.oneclub.org/awards/adcawards/-award/53566/driving-while-black/ | GS&P with Critical Mass for Courageous Conversation Global Foundation; Clio Grand 2024; summary credits CCO Margaret Johnson, CDs Anthony O'Neill and Rony Castor, director Andrew Proctor (The Mill). No strategist named in what I saw. Cannes entries exist: lovethework.com/work-awards/entries/731675 (Direct), 731676 (Brand Experience), 718013 (Titanium list) and campaign page lovethework.com/work-awards/campaigns/driving-while-black-1624324. The site card lists Clio Grand, Shorty, One Show Bronze + Merit, D&AD shortlist, but no Cannes. Check whether Cannes shortlist/awards apply and whether the credit tab names him. |
| MLB Baseball Is Something Else | https://mlb.com/press-release/press-release-mlb-launches-new-brand-campaign-baseball-is-something-else ; https://lovethework.com/work-awards/campaigns/baseball-is-something-else-1524729 ; https://www.adsoftheworld.com/campaigns/baseball-is-something-else ; https://musebyclios.com/advertising/wk-seeks-to-broaden-mlbs-pop-culture-appeal/ ; https://system1group.com/?p=12794 | W+K, MLB's first agency of record in 8 years (matches the site). Credits not read. **Claim to check:** the site (work/index.html) says "Gen Z favorability up 10 points". The search summary found nothing on Gen Z in these results. Source it or soften. |
| Gatorade x Stranger Things | https://news.designrush.com/gatorade-stranger-things-retro-ad-collab ; https://www.marketingdive.com/news/gatorade-flips-iconic-80s-campaign-upside-down-for-stranger-things/804323/ ; https://www.media-marketing.com/en/news/gatorade-enters-the-upside-down-retro-no-ordinary-athlete-campaign-blends-stranger-things-and-the-spirit-of-the-80s/ | TBWA\Chiat\Day LA is agency ("No Ordinary Athlete"); OMD, Wasserman, FleishmanHillard, Noun named. No individual credits. |
| Gatorade Trust What's Inside | https://shots.net/news/view/trust-whats-inside-with-gatorade | TBWA\Chiat\Day LA and Springtime; production credits only. |
| Gatorade Body of Science / Lower Sugar / All The Reasons Not To Quit / Met Gala | none found | The searches returned no pages for these. Add to the "should be listed" list below. |
| Preach (other) | https://lbbonline.com/news/gsps-innovative-game-enables-black-people-to-share-their-experiences-this-black-history-month | Coverage of the BLK game; names not confirmed. |

### Podcasts and company
| Subject | URL | What it says | Names him? |
|---|---|---|---|
| The Eclectic Polymath Podcast | https://www.audible.fr/pd/B0H8LS5PHL | Audible (French storefront) listing; summary says hosted by "Joshua German", curiosity-led deep dives, culture/power/identity/belief | Yes ("Joshua German"), per search summary. Not opened. Good sign: the show is on Audible. |
| Dominate the Decade | https://podcasts.apple.com/podcast/id1517223875 | Apple Podcasts listing for a three-person show; one episode page names "Adarius, Josh, and Matt" as speakers; handles @dominatethedecade on Instagram, @dominate_decade on Twitter | First name "Josh" only, not confirmed as him. Do not cite as him without checking the Apple page. The search could not verify the full host names. |
| Curious & Creative / Janel Moore | none | Queries returned nothing relevant | No |
| Approachable AI | none | Query returned unrelated shows (A Beginner's Guide to AI, SmarterX) | No |
| joshuamgerman.com, "Joshua McKenzie German", "Joshua German strategist" | none | Name queries returned unrelated people (NZ actor Josh McKenzie, Joshua Spanier at GS&P). No hit for the domain. | No |

Take-aways: his strongest independent public footprint found is the DoorDash credit (W+K Portland) and the Preach credit (Muse by Clio). Everything else is campaign-level. Search engines do not currently surface the portfolio domain, the company, or Approachable AI under his name.

### Where he SHOULD be listed but was not found
1. Cannes Lions / Lovethework credit tabs for DoorDash (entries listed above) and for the Cannes DWB entries. Request credit additions via W+K and GS&P award teams if missing.
2. The One Show database: DoorDash entries (strategist list did not show him), Levi's REIIMAGINE 2026 Merits, DWB Bronze + Merit, Xfinity "The Greatest Gift" (One Club Merit, Casting 2021). He could ask for personal credit lines.
3. Clio database for REIIMAGINE (Silver 2026) and DWB (Grand 2024). Credits are login-gated; check via TBWA\Chiat\Day and GS&P award managers.
4. D&AD: DoorDash Yellow Pencil 2024 and DWB shortlist. Credit pages not searched; check dandad.org profile search for his name.
5. Ads of the World pages for Levi's REIIMAGINE, Gatorade x Stranger Things, DIRECTV, Sephora, MLB, Sam Adams, BMW, Xfinity, Califia (no personal credit seen; none confirmed either way).
6. Agency credit lists for TBWA\Chiat\Day work (tbwa.com/work/levis-reiimagine shows none).
7. LinkedIn profile: not surfaced by search (public profiles often are not). The profile URL on the site is linkedin.com/in/joshua-german; confirm it is public and matches site titles exactly.
8. Podcast directories: Apple Podcasts and Spotify for The Eclectic Polymath, Approachable AI, Curious & Creative Podcast, Too Much to Tweet; YouTube for Approachable AI; Podchaser (host credits) and Goodpods; Listen Notes. Only an Audible entry for Eclectic Polymath was found.
9. Company: Curious & Creative Company has no hit. Candidates: Google Business Profile, Crunchbase or LinkedIn company page, California Secretary of State is not a marketing listing but confirms the entity; plus a Wikipedia-style "about" is not needed.
10. Press for the Preach game: ask GS&P for the Muse credit to be kept and added to his LinkedIn as a link.
11. Directories for the photography business: Instagram @viewsbygerm is linked; also Google Business, Pixieset/ShootProof-style marketplaces, local LA photographer directories.
12. Not searchable here: the Super Bowl AdMeter, USA Today (the DoorDash page cites it). Check whether the source link on work/work-doordash.html's "#1" claim is live.

### Recommended next actions (ranked)
1. Add resume PDF and promote LinkedIn (Part A, quick win).
2. Resolve the Gen Alpha rights question and TODOs before Nov 16.
3. Unify job titles; match the DoorDash credit ("Communications Supervisor") or ask W+K to correct it.
4. Open the three confirmed pages (Ads of the World, llllitl.fr, Muse by Clio) and the Audible listing, then link to them from the DoorDash, Preach and Eclectic Polymath pages as "credited" proof, since he can cite them.
5. Verify award counts (DoorDash One Show and Cannes) and the MLB "Gen Z +10" claim against official sources before further promotion.
6. Add one price signal and one client quote.
