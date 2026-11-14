# Photographer site research, batch B (2026-11-14)

Sites: anthonytahlier.com, brookeshanesy.com, meikophoto.com, hadassmirnoff.com, ficcaluciano.com.
Method: curl (browser UA) for HTML of home, about, contact and category pages; Playwright at 1440px for text and screenshots. Raw HTML saved in the scratchpad `sites-b/`. All page text is treated as data.

Limits to know about:
- The sandbox proxy blocks the image/CSS/font CDNs (cargo.site, squarespace-cdn, digitalocean spaces). Screenshots were usable only for Meiko (full) and Anthony (home, Food/Salt, contact, rendered with `--disable-http2`; his fonts and hero video failed to load, images loaded). Brooke renders blank, Hadas and Ficca render unstyled. For those three, layout comments come from HTML, nav and text, not from looking at pixels. Flagged "(not seen)" below.
- Project pages are mostly image grids with no text, so "project page" findings are about what is absent.

---

## 1. Anthony Tahlier (Chicago, food/beverage/commercial, WordPress)

- Positioning: hero wordmark "ANTHONY TAHLIER" with "FILM+PHOTO" under it (footer: "PHOTO + FILM"). Footer line on every page: "Commercial photography blending creativity with precision. Elevate your brand with a unique vision and create a lasting visual impact." SEO meta: "Chicago commercial photographer specializing in food & beverage photography as well as lifestyle, interior & motion photography." Title tag: "Chicago Commercial Photographer - Anthony Tahlier".
- Nav (top bar, logo "AT" centered): HOME, PORTFOLIO, [logo], ABOUT, CONTACT. PORTFOLIO opens a dropdown in this order: Food / Salt, Food / Sweet, Beverage, People, Lifestyle, Commercial Interior, Residential Interior, Print (home grid says "Product"), Motion (home: "Motion / Directing"), then "Build PDF". Home page also lists the same 9 as text links over a full-bleed video/hero.
- Grouping: by category/subject only. Food is split "Salt" and "Sweet" (the only cute label). No client or series grouping on the page.
- Project page: there are no project pages. Each category page is a title bar ("FOOD / SALT") over a 3-column masonry of images on a light gray gutter. No captions, no client names, no credits, no alt text (only "AT-Logo"). Roughly 70 to 170 uploaded images per category (HTML upload count: Salt ~171, People ~155, Sweet ~68, includes resized duplicates).
- About (/about-anthony/): first person, about 200 words, very short. Leads with origin and tone: "Green Bay Wisconsin roots with a Chicagoland area code." Then a comma list of identities ("Dad, husband, brother, son, dog dad, movie nut, music lover, fan of cocktails, pizza crusher ... generally smiley fellow."). Then "a work life that has continued to bring me joy for almost 20 years", then a one-sentence scope of work ("shooting a new dish or a 12 year old bottle of brown, highlighting a thoughtful lobby design at your favorite new hotel, capturing the happiness of a group of friends having a most wonderful time on vacation ... spending time with the world's movers and shakers"). Close: "I'm always excited to hear what you are excited about ... whether it's here in Chicago or wherever the wind takes us. Let's talk."
- Clients/press: about page ends with a lowercase, pipe-separated list of 127 names mixing brands, agencies, hotels and magazines: "acn design | advanstar communications | affinia hotels | airtran airways | aldi | ... | american express | architectural digest | ... | esquire magazine | food&wine magazine | forbes | gq magazine | hilton hotels | hyatt hotels | intel | jim beam | kraft foods | marriott hotels | porsche | ritz carlton hotels | travel leisure magazine | walmart | westin hotels | zagat".
- Contact (/contact/): H1 "CONTACT", meta title "Contact Anthony or Request Quote". Block: "PHONE: 312-927-8669 / EMAIL: INFO@ANTHONYTAHLIER.COM / STUDIO: 2414 W CULLERTON ST, CHICAGO, IL 60608 / STOPOVERSTUDIO.COM / REPRESENTED BY: JODIE ZEITLER / WONDERFUL MACHINE / FOUND ARTISTS / THE WORKBOOK". Form headed "TELL US ABOUT YOUR PROJECT" with fields FIRST NAME, LAST NAME, EMAIL ADDRESS, PHONE NUMBER, SUBJECT, PROJECT INFO, button SUBMIT. No rates. Footer link "Book Anthony".
- Offer packaging: none stated. The packaging is the category list itself, plus "Build PDF" (a visitor builds a custom PDF portfolio of selected categories) and a "Create PDF Porfolio" footer link (typo is theirs).
- Text-to-image: about 3% text. Home is a hero plus link list. Category pages carry zero prose.
- Type/layout: big uppercase tracked sans nav; wordmark with outline "ANTHONY" and solid "TAHLIER"; custom face "Dallas Bold". Dark, saturated food hero; light-gray gutter masonry on category pages. Footer repeated on every page with phone, address, email, socials.
- Distinctive: "Build PDF" tool; salt/sweet split; studio address printed with the studio's own name and link (a shared studio, stopoverstudio.com); three reps and directories listed by name.

## 2. Brooke Shanesy (LA and NYC, beauty, Cargo)

- Positioning: no tagline on home. About: "Making work in Los Angeles and New York City, Brooke believes in the power of a good photograph." Meta description is just "Brooke Shanesy Photography".
- Nav (spaced text, caps): BROOKE SHANESY, COMMERCIAL-ISH, EDITORIAL-ISH, ABOUT. A fourth page "Interiors & Places" exists (title "Interiors & Places") but is not in the visible nav. Underlying slugs: HOME-3, BEAUTY, EDITORIAL-ISH, Interiors-Places, ABOUT.
- Grouping: two hedged categories, "COMMERCIAL-ISH" (slug BEAUTY, ~93 unique images) and "EDITORIAL-ISH" (~83), plus an off-nav interiors/places page (~23). The "-ISH" suffix is the personality: it tells art buyers the lines are blurry. Home carries ~53 unique images.
- Project page: none. Pages are continuous scrolls of images. No titles, clients, credits or captions in the HTML.
- About: third person, 2 sentences, about 25 words, then clients, then reps. Leads with place ("Los Angeles and New York City"), then belief statement, then "Select clients include Nars Cosmetics, Ilia, Ciele, Kylie Cosmetics, IS Clinical, Goop, Credo Beauty, Nike, Avaline Wines, Briogeo, Burberry, O.P.I, e.l.f, Wal-Mart Beauty, Olay, Urban Decay, Vegamour and more."
- Contact: "Represented by I Heart Reps / Lindsay Meyers lindsay@iheartreps.com / Dara Siegel dara@iheartreps.com", direct email shanesy.brooke@gmail.com, Instagram "@brookeshanesy_studio". No form, no rates, no phone.
- Offer packaging: none; "beauty" is stated only through the client list (all beauty/skin/hair).
- Press: none. Clients: 17 named, one sentence.
- Text-to-image: about 1% text (about page is a handful of lines).
- Type/layout: Cargo template, font Standard (Book/Bold). Spaced uppercase nav, very sparse. (Not seen: render blocked.)
- Distinctive: the "-ISH" naming; page-per-category with no chrome; an unlisted page.

## 3. Meiko Takechi Arquillos (Los Angeles, playful commercial photo + motion, site by east of western)

- Positioning: no tagline. Info page: "Meiko is a creative with a love for playful storytelling, colorful worlds, and unexpected visual ideas. Originally from Tokyo ..." and "character-driven comedy, practical effects, miniatures, or a little movie magic".
- Nav (top right, plain sans, white on gradient): Overview, Live Action, People, Still Life, Kids, GIFs, Commissions, Info. Logo is a hand-drawn outline wordmark "Meiko Takechi Arquillos". Three small red/yellow/green dots sit above the nav (a status/slideshow control).
- Grouping: by subject/format (Live Action, People, Still Life, Kids, GIFs), with "Commissions" as the client-work page. Overview is a 49-image mixed grid.
- Project page: image-level, not project-level. Each image opens a slideshow (/slideshow/commissions#N). On Commissions every image carries a client caption, repeated per image: "Firefox", "Olipop", "DoorDash / McDonald's", "Verizon", "Walmart Plus", "Scholastic", "Adidas x The Simpsons", "Hello Bello", "Popcorn for the People", "Amazon Prime", "Vans", "Reebok Cardi B/Venables Bell & Partners", "Lowe's / Deutsch LA", "Microsoft/VMLY&R", "Hello Bello Training Pants / Awesomely Bad Portraits", "Zappos Halloween", "Zappos Kids Winter", "The New York Times". Format: Client or "Client / Agency". About 113 images on Commissions. A video entry links to /single/16064/zappos-video.
- About/Info: third person, ~120 words, warm and jokey. Leads with temperament and origin (Tokyo). Ends with a request: "She does her best work with thoughtful creatives who bring both expertise and great taste. Please email and say hello!!"
- Contact (same page): "Photography & Motion: Meiko Takechi Arquillos meiko@meikophoto.com 323-963-4561 Los Angeles", instagram, linkedin. Then "Commercial Directing: A FRESH FACE IN HELL (freshface.tv) Jason Botkin jason@freshface.tv 310-739-9226". No form, no rates. Location line is attached to the phone number.
- Clients: "Select Clients" slash-separated, 36 names, brands and agencies mixed: "72andSunny / Adidas / Amazon / BBDO / Bose / Chobani / Cottonelle / Crispin Porter + Bogusky / DoorDash / Deutsch LA / Disney / Dunkin / FCB / Firefox / ... / TBWA Chiat Day / Vans / VML / Walmart".
- Text-to-image: about 2% text. Images carry the content.
- Type/layout (seen): full-page pastel blue-to-pink gradient background, white sans nav, two-column staggered tile grid with unequal image heights, images edge-to-gutter on the gradient. Candy-colored images are chosen to match the gradient. The site's chrome is the brand.
- Distinctive: a dedicated GIFs page; "Kids" as a category; a split contact (photo/motion vs commercial directing rep); the gradient.

## 4. Hadas Smirnoff (NYC food stylist and art director, Squarespace)

- Positioning: title tag "Hadas Smirnoff | Food Stylist". About lead: "Hadas Smirnoff is a NYC- based Food Stylist and Art director." Meta description empty.
- Nav: WORK, ABOUT, CONTACT (cart icon "0" is a leftover Squarespace default). Header text is the full name with the role: "Hadas Smirnoff | Food Stylist".
- Grouping: home is 6 tiles, in order: FOOD 1.0, FOOD 2.0, DRINKS, DESSERT, MOTION, COMMISSIONED. "1.0 / 2.0" reads as vintage by era (version numbers). COMMISSIONED is a text-only page (no images) listing client names: "Chobani, Almond Breeze, Shake Shack, Dunkin, Athletic Greens, Shakeology". Slugs are leftovers from a template (/work/people-..., /work/interiors-..., /work/city-...).
- Project page: Food 1.0 holds 29 images, file names showing (alt text is the camera filenames such as "01_moment_0135.jpg", "03_milkbarcookiecake_0197.jpg", "040925_CG_TacoTIme_0555.jpg", and a .gif). No titles or captions; bottom has Previous/Next links labeled with the next category name (e.g. "Next: FOOD 2.0").
- About: third person, about 95 words (two paragraphs) plus client list. Leads with place of origin and food memory: "She grew up on the Mediterranean coast, eating seasonal, aromatic and local food." Then: "finds the ultimate joy in life by sharing food with her family and friends ... the vibrant inspiration she garners by seeing others discover new dishes and share memories over comforting meals act as the muse for her style today."
- Clients (about page, labeled "CLIENTS"): Bodi, Stella, Haus, Netflix, Fresh Pet, Madison Square Garden, Marc Jacobs, Athletic Greens, Chobani, Coca Cola, Kind Bar, Caraway, Shake Shack, Starbucks, Dunkin, New York Times, Magnum, Klondike, Pernod Ricard (sic "Picard"), Remy Martin, Somos, Maya Kaimal, The Good Batch, Haagen Dazs. 24 names, stacked as a one-per-line column, not a paragraph.
- Contact: "E. Hadassmirnoff@gmail.com / T. (917) 848 2208". Two lines, no form, no rep, no rates, no location line (NYC lives in the about page).
- Offer packaging: by medium (Food, Drinks, Dessert, Motion), not tiers. The role itself (Food Stylist and Art Director) is the offer.
- Text-to-image: about 2% text.
- Type/layout: Squarespace with Adobe Fonts (Typekit). Three-link nav, tile home. (Not seen: render blocked.)
- Distinctive: version-numbered categories; one text-only "COMMISSIONED" page that serves as the client list; filename alt text (a hole to avoid).

## 5. Ficca+Luciano (Brooklyn + Montreal, food & beverage studio, Squarespace)

- Positioning (contact page): "Ficca+Luciano is a commercial photography studio specializing in food and beverage. We create distinctive, highly crafted imagery that gives brands a visual identity of their own." Next: "Founded by photographer and director Davide Luciano and food stylist Claudia Ficca, the studio brings together image-making, food, and production under one creative vision." Then location line: "Brooklyn + Montréal." Social handle: "@ficca+luciano". Page title: "Contact Ficca+Luciano — Food & Beverage Studio".
- Nav: WORK, MOTION, FOOD, DRINK, PACKAGING, CONTACT (about content lives on Contact). Logo image "Ficca+Luciano". Instagram icon on home.
- Grouping: by category (Motion, Food, Drink, Packaging) and by client: home (WORK) is a grid of 28 client project pages, each named by the brand: OXO, Olipop, GoPuff's, Thomas' Bagels, Daring, Jif, Kraft, Museum of Ice Cream, Hoppy, Sola, Cutwater, Publix Ice Cream, Almond Breeze, Maestro, Publix, Kraft Sauces, Bubly, Amazon, Hidden Valley Ranch, Cann, SodaStream, HVR Videos, Culture Pop, Shake Shack, Hot Pockets, La Lechera, Pret, Made Good. Slugs are client names; /motion 404s in the link set (the real route is /work-1).
- Project page: client name as slug, images only. OXO page: 19 images, no visible text. No credits, no captions, no copy. Alt text is full descriptive sentences (e.g. "A bottle of Hoppy, a Japanese beverage, next to a glass filled with a golden, carbonated drink topped with foam, on a wooden surface ..."). Category pages are 63 to 77 images (Packaging 63, Drink 77, Food 71).
- Contact flow: email only, "FICCA + LUCIANO: e-mail us@ficcaluciano.com". Rep block by territory, with flags: "USA Rep. Art Department - Rika Noda Hope rikan@art-dept.com", "Canada Rep. Free Society (motion) - Dan Arki dan@freesociety.tv", "Italy Rep. 360FX- Gabriele Giudici gabriele@360fx.it". No form, no phone, no rates. Mailto subject prefilled "HELLO".
- Clients/press: shown only via project names (the 28 above); no separate list.
- Offer packaging: four lines by deliverable: Motion, Food, Drink, Packaging. Packaging is a named product line, which is unusual.
- Text-to-image: under 1%. The only prose is on Contact.
- Type/layout: Squarespace; page fonts include Modak and Archivo Black on parts of the site (display faces). Home meta: "Explore our diverse portfolio spanning motion, food, drink, and packaging." (Not seen: render blocked.)
- Distinctive: two-person studio framing (photographer/director + food stylist); a territory-based rep list; client-named projects as the homepage.

---

## Cross-site table

| Site | Nav count | Grouping | Project pages | About voice / length | Contact |
|---|---|---|---|---|---|
| Tahlier | 4 + 9 dropdown | subject | none | 1st / ~200 words | phone, email, studio address, 3 reps, 6-field form |
| Shanesy | 3-4 | "-ish" categories | none | 3rd / ~25 words | 2 reps, direct email, IG |
| Takechi Arquillos | 8 | subject + Commissions | image captions | 3rd / ~120 words | email, phone + city, directing rep |
| Smirnoff | 3 | medium (1.0 / 2.0) | none | 3rd / ~95 words | email + phone |
| Ficca+Luciano | 6 | category + client | client-named, images only | 3rd (studio "we") / ~55 words | email + 3 territory reps |

Neither site shows rates, tiers or a booking calendar. None shows a project title, credits or a caption beyond Meiko's per-image client label.

---

## 10 patterns for Joshua to borrow

1. Hedged category names with attitude (Shanesy's COMMERCIAL-ISH / EDITORIAL-ISH). For Joshua: "Portraits", "Fashion + Editorial", "Events", "Travel" can stay plain, but one small joke label signals the mixed practice, e.g. "Also shoots: Product / Food / Spaces". Do not label work "-ish" if he does not want to look hesitant.
2. Split a category in two with plain words (Tahlier's Food / Salt and Food / Sweet). Joshua's equivalent: Events split "Live" and "After Dark", or Spaces split "Interiors" and "Venues".
3. One caption format, client first (Meiko: "Client" or "Client / Agency", per image). Use "Client / Brief / Year" in one short line under each plate. Strongest proof signal for the lowest text cost.
4. Print the client list in one tight line, lowercase or slashed (Tahlier's pipe list, Meiko's slash list). One line, 15 to 35 names, brands, publications and venues mixed in one run. Lowest-effort credibility block.
5. Build-your-own-PDF (Tahlier "Build PDF"). Joshua version: a "Send me the deck" link that outputs a capabilities PDF per category (Fashion, Events, Product). Gives the studio form a warm follow-up and fits "booking through his company's studio form".
6. A short, first-person about page that leads with place and trade, not with a mission statement (Tahlier: "Green Bay Wisconsin roots with a Chicagoland area code"). Joshua: open with LA plus the four things he shoots, then one human sentence, then "Let's talk."
7. A territory-aware contact block (Ficca+Luciano's "USA Rep / Canada Rep / Italy Rep"). Joshua has no rep, so print the equivalent: "Booking: studio form. Direct: email. Based: Los Angeles. Travels: [list]". One labeled line per route, no tiers.
8. Footer that repeats the contact on every page (Tahlier: phone, address, email, "Book Anthony" with a button). Joshua: footer has "Book Joshua" link to the studio form on every page, plus city line.
9. Name product lines by deliverable, not by genre (Ficca+Luciano's PACKAGING; Hadas's DRINKS and DESSERT; Tahlier's Beverage). For Joshua's side lines: "Product", "Food + Drink", "Spaces" as their own short pages rather than burying them under "Other".
10. Let chrome carry the brand when the images vary (Meiko's pastel gradient and hand-drawn wordmark). Joshua's Paper Edition already has a house look; keep it constant while mixed subjects (portrait, hotel lobby, plated dish) flow through it, so the range reads as one eye.

Anti-patterns to skip: filename alt text ("040925_CG_TacoTIme_0555.jpg" on Hadas), a stray shopping cart icon, template slugs that do not match the label ("people-mpk5m" for FOOD 1.0), an unlisted page, no form and no rate hint.

---

## Selling vocabulary actually used (verbatim)

Positioning and promise:
- "Commercial photography blending creativity with precision."
- "Elevate your brand with a unique vision and create a lasting visual impact."
- "distinctive, highly crafted imagery that gives brands a visual identity of their own"
- "image-making, food, and production under one creative vision"
- "commercial photography studio specializing in food and beverage"
- "believes in the power of a good photograph"
- "playful storytelling, colorful worlds, and unexpected visual ideas"
- "whimsy and humor to the everyday", "finding the extraordinary in the ordinary"
- "from the initial concept to production and post"
- "thoughtful creatives who bring both expertise and great taste"
- "a unique vision", "a lasting visual impact", "highly crafted"

Role and offer words:
- "Food Stylist and Art director", "photographer and director", "Photography & Motion", "Commercial Directing", "Commissions", "Commissioned", "Select Clients", "Represented by", "Rep."
- Category labels: Salt, Sweet, Beverage, People, Lifestyle, Commercial Interior, Residential Interior, Product, Motion / Directing, Live Action, Still Life, Kids, GIFs, Overview, Food 1.0 / 2.0, Drinks, Dessert, Packaging, Beauty (Commercial-ish), Editorial-ish, Interiors & Places.
- Process verbs: "Collaborating with an agency or brand", "show off their next great concept", "highlighting a thoughtful lobby design", "capturing the happiness of a group of friends", "showing the detail and care", "shooting a new dish".

Calls to action:
- "Let's talk."
- "Tell Us About Your Project" (form header), "Contact Anthony or Request Quote" (page title)
- "Book Anthony"
- "Please email and say hello!!"
- "I'm always excited to hear what you are excited about"
- "e-mail us" (mailto subject "HELLO")
- "Create PDF Porfolio" / "Build PDF"
- "Select clients include ... and more."

Trust framing:
- "almost 20 years", "Represented by", "Select Clients", "Wonderful Machine / Found Artists / The Workbook", named agency pairs ("Reebok Cardi B/Venables Bell & Partners", "Lowe's / Deutsch LA", "Microsoft/VMLY&R").
- Place words: "Chicago", "Brooklyn + Montréal", "Los Angeles and New York City", "NYC- based", "Tokyo", "Mediterranean coast", "wherever the wind takes us".

Takeaway on voice: sentences are short, verbs are concrete (shoot, capture, highlight), adjectives are rare ("thoughtful", "distinctive", "highly crafted"). The only places any site uses price or tier language: none.
