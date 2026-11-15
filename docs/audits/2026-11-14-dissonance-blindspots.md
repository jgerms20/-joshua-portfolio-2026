# Portfolio audit: dissonance and blind spots (2026-11-14)

Status: read-only audit. No site files were touched and nothing was committed.

Scope read: index.html (re-read after the reorder), work/index.html, all 12 work/work-*.html plus work-template.html, builds/ (4 pages), photography/, network/, podcasts/ (4), media-diet/, shop.html. Line numbers are source lines at time of reading; index.html is being edited concurrently, so re-grep the quoted string before editing. Not flagged, per brief: About/Builds reorder, the "Creative, Cultural & Content Strategist" title.

Not verified: no external link was opened, no award or metric was checked against a source. Items marked VERIFY are suspicions from reading, not confirmed errors.

---

## A. Dissonance

### A1. Risky: fix or pull before the audience sees it

1. **Gen Alpha Intelligence Lab has an unresolved rights question, and the question itself ships in public HTML.**
   builds/gen-alpha-intelligence-lab.html:68 (hidden by CSS, visible in view-source): "Confirm you have the right to show this publicly. It began as an agency assignment... the public AgencyThings README on GitHub describes the Lab as an 'internal agency research site'. If you cannot confirm the rights, unlink this page before Nov 16."
   Same page :97: "The Curious & Creative Company presents the Lab as its Consultancy's research product." The live URL is `agencythings-gen-alpha.vercel.app`.
   That is agency-origin work presented as C&C product, which the house rules forbid, and it is the first card in Builds (index.html:2026). Hiring teams at AI companies do read source.
   Fix: Joshua decides by Nov 16. If rights are unconfirmed, unlink the card and page and promote a lab build (Kindling or The Man and the Machine) to the third slot. Either way, strip the TODO text from shipped HTML. FACT-DEPENDENT for the decision, DOABLE NOW for stripping notes.

2. **The three "case studies" in Builds are not case studies in public view.**
   Problem, insight, limits and "what changed" sections are `is-pending` and hidden: gen-alpha :104, :112, :160; life-gamified :97, :152, :160; meme-library :106, :163. What a visitor gets is a feature list, with section numbers that skip (01, 03, 04).
   Yet index.html:2023 says "Three case studies first" and each card says "Read the case study →" (:2037, :2053, :2069).
   Fix now: relabel "Case study" to "Build notes" or "How it works" and renumber visible sections. Fix properly: Joshua answers the five TODO prompts per page (about 10 sentences each). For an AI-company reader these missing sections (why, what he decided vs. what the model wrote, limits) are the whole point.

3. **Unsourced, suspiciously precise metrics in agency case studies.** House rule: never invent metrics.
   - work-sephora.html:787 "127% Holiday Sales Growth YoY", :795 "94%", :958 "42% Skincare Category Growth", :962 "89%".
   - work-directv.html:746 "267%", :877 "41% Brand Awareness Lift", :1017 "52% Message Recall", :1021 "28% Consideration Lift", :1025 "-34%".
   - work-bmw.html:686 "5.2B Total Impressions", :694 "48% Lift in iX Consideration", :665 "50 million views in its first week".
   - work-xfinity.html:689 "50M+ Impressions via influencer partnerships", :693 "8.5M+ Video views".
   - work-levis.html:759-771 "$65M+", "4.3B+", "19.87%", "8%" (the 19.87% has a plausible-source feel; still uncited on the page).
   - work-doordash.html:707-715 "6.8B", "$50M+", "#1 Most Talked About Ad".
   Contrast: work-mlb.html:878 cites Morning Consult. That is the standard.
   Fix: for each number, attach a source link the way MLB does, or delete it. FACT-DEPENDENT (Joshua knows which came from client reports and which he may quote).

4. **DoorDash claims that look wrong. VERIFY.**
   - work-doordash.html:734 "Super Bowl AdMeter #1 — USA Today" and :724 "All The Ads won the Super Bowl AdMeter." My recollection is that the 2024 USA Today Ad Meter was won by State Farm; I did not check.
   - :724 "It crashed X (Twitter)." Unsourced.
   - :638 "We partnered with every brand advertising in the Super Bowl" vs :659 "partnered with 76 official and unofficial brands".
   - :610 "without a budget anywhere close to the competition" for a brand that bought an in-game spot.
   Fix: cut the Ad Meter line unless sourced, cut "crashed X", say "76 brands" both times, drop the budget line.

5. **Role titles disagree across the site.**
   - TBWA: index.html:1561 "Senior Connections Strategist and later AI Strategy and Systems Lead"; network/index.html:1003 "most recently as a Senior Connections Strategist"; work/index.html:453 "Connections Strategist; Senior Connections Strategist" (no AI lead anywhere on the work side).
   - Cards say "Connections Strategist" for every Gatorade and DIRECTV piece (index.html:1703, :1730, :1740; work/index.html:502, :529, :539, :625, :635, :701, :721, :731) while the case-study pages say "Senior Connections Strategist" for the same work (work-gatorade.html:806, :1086; work-directv.html:591, :729). The cards also read as a demotion over time: Senior on Sephora 2024, not senior on Gatorade 2026.
   - W+K DoorDash: card "Media & Comms Supervisor" (index.html:1713, work/index.html:512) vs page "Media & Communications Strategist" (work-doordash.html:552, :572, :700).
   - GS&P: "Communication Strategist" (index.html:1750; work/index.html:549, :688, :741, :751; work-dwb.html:626) vs "Communications Strategist" (work/index.html:665; bmw :573; califia :573; samadams :575; xfinity :580) vs "Junior Communications Strategist & Co-Creator" (work-preach.html:572).
   - work-levis.html:600 "Senior Connection Strategist" (typo) vs :725 "Senior Connections Strategist".
   - network/index.html:1037 "Co-founder · Network principal" vs "Co-founder & CEO" everywhere else.
   Fix: Joshua gives one title per agency per period (and the date the AI Strategy and Systems Lead title started); apply it to every card and page. FACT-DEPENDENT, then mechanical.

6. **Dates disagree.**
   - GS&P: index.html:1613 "2021 – 23" vs work/index.html:455 "2020 – 2023", and Xfinity is dated 2020 (work-xfinity.html:584).
   - Califia: page says Year 2023 (work-califia.html:577) but its own sources are The Drum 2021/08/24 (:643) and 2022 (:664). The campaign launched in 2021.
   - Gatorade page header says "2025-2026" for the whole page (work-gatorade.html:810) while cards split 2025–2026 and 2026.
   - Approachable AI is "2026 – Present" (index.html:1987; podcast page :585) but Episode 004 is "Kicking off 2026" (podcast-approachable-ai.html:634), so episodes 001 to 003 predate 2026.
   - The Eclectic Polymath is "2026 – Present" (index.html:1975) with episodes numbered 240 to 243 (podcast-eclectic-polymath.html:790-793). See item 8.

7. **Tense: the agency job still reads as current in one place.**
   index.html:1623-1625: "2024 – Now / Los Angeles, California / TBWA\Chiat\Day: Levi's × Beyoncé, Sephora, DIRECTV. Home base."
   Everything else says previously (index.html:1463, :1561 "where I was"; work/index.html:453 "2024 – 2026").
   Fix: "2024 – 26" for TBWA, then a separate "Now" entry for The Curious & Creative Company in Los Angeles.

8. **"Host, produce, and edit myself" vs "Hybrid: host + AI".**
   index.html:1956 "Shows I host, produce, and edit myself." and podcast-eclectic-polymath.html:798 "I do the research, follow the thread as deep as it goes".
   network/index.html:830 labels the same show "Podcast · Hybrid: host + AI", and Approachable AI Episode 005 is "How I Built 'The Eclectic Polymath Podcast'" (podcast-approachable-ai.html:623). 240+ episodes inside a year also tells the reader AI is involved.
   This is a strength told as a secret. For an AI-company audience, "I built a pipeline that researches and produces a daily show, here is what I do and what the model does" beats "I edit it myself".
   Fix: state the method on the show page and soften the homepage line to what is true for all three shows. FACT-DEPENDENT (how the show is actually made).

9. **The network page admits AI-generated shows; the homepage implies three hand-made ones.**
   network/index.html:798 "some are AI-generated; one is a hybrid", with The Jazz Riff, The Morning Read, God Is Brazilian (:890-923). Honest labelling, good. But :923 "A podcast by Joshua German." and :908 "A morning read, made with AI." are placeholder descriptions.
   Fix: one real sentence each, or drop the three from this page and leave them on the C&C site.

### A2. Names and labels

10. **Show names drift.** "Curious & Creative" (index.html:2000) vs "The Curious & Creative Podcast" (network/index.html:809, :765). "Dominate the Decade" (index.html:2006, network :936) vs "Dominate The Decade" (podcast-dominate.html:655, title). Approachable AI is "A podcast" (podcast-approachable-ai.html:566) and a "Video series" (network/index.html:845). The company is "The Curious & Creative Company" on the homepage and plain "Curious & Creative" on network/, which is also the podcast's name.
11. **Campaign names drift.** "DIRECTV: Like Never Seen" (work/index.html:636) vs "Like You've Never Seen It" (same card, :633 and :637). "Next Project: Sephora: We Belong" (work-levis.html:836, work-template.html:575), a campaign that appears nowhere else; the Sephora page is "Don't Overthink It" and "Skin Obsessed". "Samuel Adams: Brighter Boston" (card) vs "Your Cousin's Brighter Boston" (work-samadams.html:598, :633).
12. **Card says one thing, strapline another.** Gatorade Body of Science: "Gatorade's sports-science story, told through the athletes who live it" (index.html:1742) directly above "The women's sports research gap, worn at the Met Gala" (:1744). The second is the interesting one. Lead with it.
13. **DWB agency credit.** Page credits "Goodby, Silverstein & Partners / Critical Mass / The Mill" (work-dwb.html:622); cards credit GS&P only. Fine, but keep the card honest with "with Critical Mass and The Mill" if they were co-leads. VERIFY.
14. **Awards counts.** DoorDash card "8× Cannes Lions" and "D&AD Yellow Pencil" (index.html:1720-1721) do not appear on the DoorDash page recognition list (work-doordash.html:733-738), which lists only the Titanium Grand Prix and One Show. Card "7× One Show Silver/Bronze/Merit" matches the page (2+3+2). Add the missing awards to the page with sources or trim the card. Levi's awards are dated 2026 for a 2024–2025 campaign (index.html:1695); plausible, VERIFY.
15. **"Kenny Mitchell" quoted twice with two titles.** work-levis.html:649 "Global Chief Marketing Officer, Levi's" and :656 "CMO, Levi Strauss & Co." Use one quote, one title, and link the source.
16. **Photography taxonomy.** Homepage filters "People / Places / Gatherings" and "What I shoot: Portraits, Fashion & Editorial, Events" (index.html:1860); photography site series "Portraits / Fashion & Editorial / Events / Places"; shop filters "Places / Street Life" (shop.html:430-431); shop meta says "landscapes, travel, and city work" (shop.html:10). Pick one set of names.
17. **Two Instagram accounts, unexplained.** index.html:2349 instagram.com/jgerms20; :1868 and photography/ use @viewsbygerm. Label them "Instagram (personal)" and "Instagram (photography)", or link one.
18. **Meme Library lives at meme-atlas.vercel.app** (builds/meme-library.html:89). Old name in the URL. Minor; mention or rename the deployment.
19. **Section numbering.** network/index.html jumps from "03 The Consultancy" (:991) to "05 Who we are" (:1025). work-directv.html runs 06, 07, then 01 (:617, :631, :649). media-diet/index.html:251 says "CH. 06".
20. **Company site is on github.io.** Every C&C link goes to `jgerms20.github.io/curious-and-creative/` (index.html:1461 and about 30 others). A "Co-founder & CEO" link landing on a personal GitHub Pages URL undercuts the title. Needs a domain. FACT-DEPENDENT.
21. **Typos.** photography/index.html:11 "los Angeles photographer". Email is "Jgerms20@gmail.com" on the homepage and "jgerms20@gmail.com" elsewhere.

### A3. Em dashes in Joshua's voice (house rule)

Counts are prose lines containing an em dash:
- work-gatorade.html 56, work-mlb.html 26, work-dwb.html 22, work-directv.html 15, work-preach.html 13, work-sephora.html 11, work-doordash.html 10, shop.html 9, work-levis.html 8, work-samadams.html 7, work-califia.html 6, work-bmw.html 4, work-xfinity.html 4, podcast-curious-creative.html 1 (:638).
- index.html: :2034 "Gen Alpha culture — insights", :2050 "GIFs — each with provenance" (builds/index.html already has the colon/comma versions of both sentences, so the two pages disagree), :2314, :2317, :2322 (`&mdash;` in the Available For and Focused On lists; :2313 was already fixed, so the list is half-converted), :2352 "Email — Primary".
- Decorative kickers ("01 — The Brief", "Portfolio — 2026 Edition") are typographic and can stay per the rule.

**The fix was applied badly in builds/index.html.** Em dashes were swapped for colons mechanically and the sentences broke:
- :127 "Play bass or connect MIDI: and the AI plays back." and "10 AI musician personalities: from Supportive to Adversary, Listen to Free."
- :134 "four lenses: Jungian, Freudian, cognitive, and cultural: and correlates it against your sleep data."
- :141 "Think ESPN Tournament Challenge: but for your friend group."
Fix: rewrite as sentences ("Play bass or connect MIDI and the AI plays back."). When doing the case-study pass, rewrite, do not find-and-replace.

### A4. Copy that reads as filler or AI-written

22. **work-xfinity.html is the weakest page on the site.** :596 "connectivity and staying in touch with loved ones becomes paramount... capture the hearts of families everywhere"; :604 "orchestrated the rollout strategy... resonated with audiences authentically"; :669-670; :683; :705 "set a new benchmark for holiday campaign effectiveness in the connected home category"; :713 "authenticity compounds reach". Every paragraph could describe any campaign. The "Across Channels" section on the same page (:626-657) is specific and sourced. Cut the page down to that plus two honest sentences on his role, or drop it to a card.
23. **podcast-curious-creative.html** :638 "A deep dive into the minds of artists, creators, and innovators"; :733-743 "The messy, beautiful journey of turning curiosity into creative breakthroughs"; :762-763. It also contradicts the homepage description of the same show ("creative strategy and culture with Janel Moore", index.html:1956). And the page says "Now streaming / New conversations, every drop" (:700-701) inside the empty state, with a "Listen on Spotify" button whose href is "#" (:644, hidden until populated). If no episodes are out, the homepage "Now Airing" (index.html:2002) is false. VERIFY whether episodes exist; if not, label "Coming soon" or remove the card.
24. **podcast-approachable-ai.html "What we explore"** (:677-712): "Humans, meet machines", "position yourself on the right side of the shift", "at the edge of what's possible" (twice). None of the six topics matches the six real episodes, which are all "I built X on camera". Replace with three lines describing what actually happens.
25. **Prototype cards in builds/index.html** :148 to :190: "AI-powered bias detection", "AI-powered influencer and creator discovery. Find the perfect creators for your brand", "AI-powered productivity and goal tracking", "Share your musical journey and discover new sounds". Seven near-identical blurbs. Also "AI-powered" seven times on a site whose rule is strategist first.
26. **Case-study tics**: "not just X, but Y" appears in most My Role and Impact paragraphs (levis :623, :633, :782; bmw :593; califia :675-676; samadams :618, :719; mlb :867). "REIIMAGINE did what great campaigns rarely do" (levis :781), "The numbers backed that up" (bmw :703), "You can't script that kind of credibility" (samadams :718), "Campaign Manifesto" quotes with no source (califia :629, samadams :692). The Impact sections on Califia (:684) and Sam Adams (:718-719) contain no outcome at all.
27. **Tickers.** Fake stock percentages ("Claude Code ▲ +4.8%", "Sleep ▼ -2.1%") run between every homepage section, six or seven strips in all. One is a joke; seven is noise, and "Cannes Grand Prix Work ▲ +3.8%" puts an invented number next to a real award. Keep one.
28. **Hero stacks four identity lines.** index.html:1451 "I find the idea and build the thing." :1453 "Creative, cultural & content strategist who builds with AI" :1454-1455 "Photographer / Podcaster" :1459 "Strategy, stories, and the things I build..." :1461 "Co-founder & CEO" :1462 "Independent Strategist & AI builder". CEO of a company and "Independent Strategist" on adjacent lines reads as two different answers to "what do you do".
29. **"Let's create together."** (index.html:2297). Generic. The mailto template two lines below (:2306, asks for timeline and budget) is much more like him.
30. **Contact lists.** "Focused On" (7 items) and "Spaces" (8 items, :2330-2338: entertainment, tech, music, fashion, food, hospitality, real estate, consumer, sports, startups) say "anything". "Food, hospitality & real estate" has no supporting work on the site.

### A5. Dead ends and stale items

31. **work/work-template.html is public.** A full duplicate of the Levi's page with older, more inflated copy (:505 "I architected the channel strategy... multi-platform ecosystem"), no noindex. Delete or noindex. DOABLE NOW.
32. **No sitemap.xml and no robots.txt** in the repo root.
33. **index-gemini-ultra.html** sits in the root and is presumably served. Not read in full; check and remove or noindex.
34. **"In the Works" (index.html:2166)**: "On the Record... An interview series I'm planning" (:2249-2252) is an "eventually" item on the public homepage. Park it. The chapter title "In the Works" also undersells the collages, which are finished work.
35. **Shop**: "Photo Books... listed here when they're ready" (shop.html:447) is an empty section. Precise paper and delivery promises (:499 "100% cotton rag... no color shift over time", :507, :551 "Ships in 3–5 days") sit next to "This shop is new... Real-time checkout is coming" (:415, :572) and an unnamed "print-on-demand partner". Either the lab is chosen and the specs are real, or soften them. Homepage says prints are "in the shop now" (index.html:2245). VERIFY.
36. **"eleven more builds"** (index.html:2075) is a hard-coded count. It is correct today (11 lab cards). House rule says derive or omit: "The whole lab, labeled Live or Prototype".
37. **Field Notes** correctly hides while data/notes.json is empty. No action; noting that the nav target exists with nothing behind it until the first post.
38. **"Also open-source: Digital Task Brief"** (index.html:1807) is a build sitting at the bottom of Brand Work. Move to Builds.
39. **Nav.** "Work" goes to Brand Work (now consistent after the reorder). The drawer numbers five chapters (:1409-1413) but the page has CH. 06 Media Diet and CH. 07 In the Works with no drawer number; fine, but Media Diet is missing from the drawer entirely.
40. **Preach stat tiles** (work-preach.html:704-713): "Press / Global / BLK" in the slots where other pages have numbers. Honest, but "Played by Black people across the US and internationally" is unsourced.

---

## B. Blind spots

### What a stranger cannot tell in 10 seconds

- **What to hire him for.** The hero offers strategist, AI builder, photographer, podcaster, CEO. There is no sentence of the form "I do X for Y". A recruiter at an AI company and a founder wanting a brand strategy need different sentences and get neither.
- **Whether he is looking for a job.** "Now booking independent work" (hero, About, contact) says freelance only. A hiring team at OpenAI or Anthropic will read that as "not available for a role". If he is open to full-time, nothing says so.
- **How senior he is.** No years of experience, no team size, no "led" vs "contributed" summary. The role-title inconsistencies in A5 make this worse.
- **What he personally did on the famous work.** DoorDash is the biggest name on the site and his role there was partner outreach and game-day social. The page is honest about that (work-doordash.html:700-701), which is good, but the card presents it as his headline piece with 20+ awards.
- **What is real in Builds.** See A2. Which are used by anyone, and what he decided vs. what the model wrote, is exactly what is missing.

### What this audience expects and does not find

| Missing | Why it matters | Status |
|---|---|---|
| Resume / CV (PDF link) | Recruiters need a file to forward. None anywhere on the site. | FACT-DEPENDENT (needs his current resume) |
| LinkedIn above the fold | Exists only at the very bottom (index.html:2348). | DOABLE NOW |
| GitHub in contact links | The builder claim's main proof. Only linked from builds/index.html:195. | DOABLE NOW |
| Any testimonial | Zero quotes about Joshua on the entire site. The only quotes are a Levi's CMO about Beyoncé. | FACT-DEPENDENT. Gatherable: a CD or strategy lead from each agency, HIIKE and U&AI founders, the KOAT designer, Janel. |
| Outcomes for independent work | HIIKE and U&AI cards are deliverable lists with no result, date, or duration (index.html:1769-1801). These are the only proof he can do this without an agency. | FACT-DEPENDENT |
| Services with a shape | "Available For" is a list of nouns. No engagement types, no typical length, no starting price or "from". Photography says "Rates quoted per project". | FACT-DEPENDENT for pricing; DOABLE NOW for shape |
| A written point of view | He started in journalism and the site has no writing. Substack is linked four times, Field Notes is empty. For a content strategist this is the biggest gap. | FACT-DEPENDENT (needs one real post) |
| AI work evidence beyond apps | "AI Strategy and Systems Lead" at TBWA gets half a sentence (index.html:1561). No description of what he built or rolled out there. That is the most relevant job he has had for an AI-company reader. | FACT-DEPENDENT (and confidentiality) |
| Speaking proof | "Speaking" is offered (index.html:2315); no talk, panel, or guest appearance is shown. | FACT-DEPENDENT; otherwise cut the offer |
| Contact form or calendar link | Personal contact is mailto only. C&C has a form; the portfolio does not. A Gmail address for a CEO is a small credibility cost. | FACT-DEPENDENT (domain email, scheduling link) |

### What to cut

1. Six of the seven ticker strips.
2. work-template.html, index-gemini-ultra.html (after checking).
3. "On the Record" planned series; the empty Photo Books section.
4. The "Spaces" list and half of "Focused On".
5. The seven Prototype cards, or collapse them to a single line linking GitHub. Four Live builds plus three written-up ones is a stronger lab than fourteen.
6. The Xfinity page as a full case study. Consider the same for Califia and BMW: three thin 2021–22 pages dilute Levi's, Gatorade, DWB and Preach.
7. Every unsourced metric that cannot be sourced.
8. Media Diet from the homepage flow (keep the page, link it from About). It is charming and it sits between the proof and the contact section.
9. Awards emoji rows on cards where his role was supporting; keep the awards on the case-study page with the role stated.

### The five additions that would matter most

1. **A one-line offer plus availability, in the hero.** Who he works for, what he delivers, and whether he is open to roles as well as projects. FACT-DEPENDENT (his call on full-time), 10 minutes to implement.
2. **Resume PDF and LinkedIn/GitHub links in the hero and contact.** Links DOABLE NOW; PDF FACT-DEPENDENT. The resume-sync skill exists for this.
3. **Finish one build case study properly.** Life Gamified is the best candidate: it is his, it is live, the technical section is already strong (MCP endpoint, RLS, shared game engine). It needs the problem, his reasoning, what he decided vs. what Claude Code wrote, limits, and what changed. FACT-DEPENDENT, about 10 sentences from Joshua.
4. **Three testimonials.** One agency lead, one independent client, one collaborator. FACT-DEPENDENT; the add-testimonial skill exists.
5. **One independent case study with an outcome.** HIIKE or U&AI written up like the agency pages: the problem, what he made, what happened. Plus a paragraph on the TBWA AI Strategy and Systems Lead work. FACT-DEPENDENT.

Runner-up: one published Field Note, so the content-strategist claim has content behind it.

---

## Prioritized top 15

| # | Item | Type | Ref |
|---|---|---|---|
| 1 | Gen Alpha Lab: resolve rights by Nov 16 or unlink; strip TODO notes from shipped HTML | Fact-dependent + now | A1.1 |
| 2 | Source or delete unsourced metrics (Sephora, DIRECTV, BMW, Xfinity, DoorDash, Levi's) | Fact-dependent | A1.3 |
| 3 | DoorDash: Ad Meter #1, "crashed X", "every brand" vs 76 | Verify, then now | A1.4 |
| 4 | One title per agency, applied to every card and page; add the AI lead title to the work side | Fact-dependent | A1.5 |
| 5 | Journey map still says TBWA "2024 – Now" | Now | A1.7 |
| 6 | Relabel the three build "case studies" or fill them in | Now / fact-dependent | A1.2 |
| 7 | Eclectic Polymath: "edit myself" vs "Hybrid: host + AI"; say how it is made | Fact-dependent | A1.8 |
| 8 | Hero: one offer line, and say whether he is open to roles | Fact-dependent | B |
| 9 | Resume PDF; LinkedIn and GitHub up top | Fact-dependent / now | B |
| 10 | Testimonials: none exist | Fact-dependent | B |
| 11 | Dates: GS&P 2020 vs 2021, Califia 2023 vs 2021, Approachable AI start year | Fact-dependent | A1.6 |
| 12 | Em dashes: about 190 prose lines in work pages and shop; broken colon swaps in builds/index.html | Now (rewrite, not replace) | A3 |
| 13 | Delete or noindex work-template.html; check index-gemini-ultra.html; add sitemap and robots | Now | A5.31-33 |
| 14 | Curious & Creative podcast: "Now Airing" with an empty page and filler copy | Verify, then now | A4.23 |
| 15 | Cut: six tickers, Prototype cards, "On the Record", Photo Books, Spaces list, Xfinity page | Now (needs his yes) | B |
