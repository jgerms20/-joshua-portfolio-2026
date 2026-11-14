# Photography inventory (2026-11-14)

Read-only inventory of `data/photography.json`, `data/photo-sets.json`, the `photos/` tree (top two levels, `photos/_sized` skipped) and `photography/index.html`. Facts only.

## 1. Photo entries by category

`data/photography.json` holds 37 entries, all `published: true`, all with alt text, all source files present on disk.

Site gallery categories (from `photography/index.html`, matching the JSON counts):

| Category (site gallery) | Frames | Source folder in JSON |
|---|---|---|
| Rio de Janeiro (set) | 4 | `photos/shop/` |
| Portraits | 7 | `photos/portraits/` |
| Fashion | 5 | `photos/fashion/` |
| Events & Live | 9 | `photos/events/` |
| Landscapes | 9 | `photos/landscape/` |
| Travel | 3 | `photos/travel/` |
| **Total** | **37** | |

Other groupings in the JSON:

- `chapter`: places 15, people 12, gatherings 10
- `layout`: archive 16, pair-left 7, pair-right 7, wide 4, inset 2, hero 1
- `sequence` (homepage order 1..21): 21 entries; 16 entries are `null` (archive)
- `set`: rio-de-janeiro 4; no set on 33 entries
- `commissioned` / `spec` / `recent` / `project` flags: none set on any entry

## 2. Sets (`data/photo-sets.json`)

One set:

- slug `rio-de-janeiro`, title "Rio de Janeiro", place "Brazil", cover `rio-santa-teresa-trams`, prints `true`
- count: 4 frames (all in `photos/shop/`, all `archive` layout)
- date/year: none
- location: "Brazil" only (no city-level field in the set record; alt text names Rio de Janeiro)

## 3. Event coverage (`site.coverage` in the JSON)

One entry:

- slug `koat-ss27`, title "KOAT SS27 presentation coverage", specialty "Event coverage"
- date 2026-11-07, summary "Documentary and behind-the-scenes coverage of a fashion presentation."
- credits: Joshua shot stills and video on a two-camera setup; Janel Moore covered the room on camcorder
- stills: none (renders text-only)

`site.shoots` (the "Selected shoots" list) is absent from the JSON.

## 4. Photo site views and section names (current)

Views (`data-view` / hash targets):

- **Work** (`#work`), nav label "Work"
  - Hero (`#hero`), hero line "Portraits, fashion, event coverage and travel. On 35mm film and digital."
  - **Sets** (`#sets`), meta "01 set · 04 frames"
  - **Event coverage** (`#coverage`)
  - **More work** (`#more`), meta "33 frames", cards: Portraits, Fashion, Events & Live, Landscapes, Travel
  - Galleries (`#galleries`): Rio de Janeiro, Portraits, Fashion, Events & Live, Landscapes, Travel
- **About** (`#about`), nav "About", heading "About", meta "Los Angeles"
- **Services** (`#services`), nav "Services", heading "Services", meta "Rates quoted per project"
- **Book** (`#book`), no nav link; reached by the header "Book" pill (opens external Studio form) or hash `#inquiry`. Heading "Book a shoot", meta "Through The Curious & Creative Studio"

Lightbox heading: "Photographs".

## 5. Services and offers listed

Services view rows:

1. Portraits: "People, headshots, personal sessions."
2. Fashion & editorial: "Lookbooks, styling tests, campaigns."
3. Event coverage: "Documentary and behind the scenes: presentations, concerts, parties, launches."

Also listed as text: "Also booking: product, food and spaces." (no gallery or folder for these).

Other offer text on the site:

- Book view routes: "Portraits, fashion & general shoots"; "Event coverage"
- About: "I shoot portraits, fashion, live events and travel, on 35mm film and digital. I also host podcasts."
- Travel appears in the hero and About copy but is not a Services row.
- No rates or prices are listed ("Rates quoted per project").

## 6. Booking links on the page

All paid-booking links go to The Curious & Creative Studio contact form:

- `https://jgerms20.github.io/curious-and-creative/pages/contact.html?topic=photo`: header "Book" pill, hero "Book a shoot", Services button "Book through The Curious & Creative Studio", Book view "Portraits, fashion & general shoots" (4 occurrences)
- `https://jgerms20.github.io/curious-and-creative/pages/contact.html?topic=events`: Services "Use the events form", Event coverage card "Book event coverage", Book view "Event coverage"

Direct contact (not bookings):

- `mailto:jgerms20@gmail.com` (Book view "Say hi" with copy button; footer "Say hi")
- `https://www.instagram.com/viewsbygerm/` (Book view and footer)

Links into the shop:

- `../shop.html#photosets` (Rio set card, "In the shop")
- `../shop.html` and `../shop.html#photobooks` (footer "Prints", "Photo books")

The JSON readme states paid shoots are booked through the Studio and that no personal booking form should be added.

## 7. Photo folder counts (`photos/`, top two levels, `_sized` skipped)

| Folder | Files | Notes |
|---|---|---|
| `photos/portraits/` | 31 | 7 published in JSON |
| `photos/landscape/` | 30 | 9 published |
| `photos/self/` | 26 | not in `photography.json`; mixed JPG/JPEG/HEIC/PNG |
| `photos/fashion/` | 17 | 5 published |
| `photos/events/` | 14 | 9 published |
| `photos/art/` | 12 | 6 artworks, each with a `-sm` version; not in `photography.json` |
| `photos/travel/` | 9 | 3 published |
| `photos/shop/` | 4 | the 4 Rio set frames |
| `photos/podcasts/` | 3 | logo/cover images; not photography |
| `photos/inbox/` | 1 | `README.md` only; no pending imports |

Top-level files in `photos/`: `route-map-dots.png`, `us-map.jpeg` (not photography).

Folder files exceed published frames in every photo category, so unpublished candidates exist on disk. Quality of those files was not assessed.

## 8. Thin or missing categories

Counts only. "Strong frame" quality was not judged.

Thin (under ~6 published frames):

- **Travel**: 3 frames
- **Fashion**: 5 frames
- **Rio de Janeiro** (set): 4 frames

Missing or near-missing for the freelance offers listed on the site:

- **Product**: no folder, gallery or entries. Named only in Services text.
- **Food**: no gallery. Two entries in `photos/events/` (`culinary-set`, `plates-in-progress`), both tagged `gatherings`, describe a culinary set and plated dishes. Named only in Services text.
- **Spaces** (interiors, architecture): no folder, gallery or entries. Named only in Services text.
- **Editorial**: offered as "Fashion & editorial" in Services; no separate editorial gallery, so it shares the Fashion gallery (5 frames).
- **Event coverage**: "Events & Live" has 9 frames, but the one coverage entry (`koat-ss27`) has no stills.

Present with reasonable counts: Portraits (7), Landscapes (9), Events & Live (9).

## 9. Working tree note

`git status` shows `photography/index.html` modified (`M`) and `.claude/skills/` untracked. This inventory did not change either.
