# Photography inbox

## Add a set (a place or a theme: Rio, North Carolina, Oregon...)

1. Make a folder named for the set, lowercase with hyphens, and drop the photos in it:
   `photos/inbox/north-carolina/`
2. Run `python3 scripts/import-photography.py`.
   Each photo becomes a WebP in `photos/northcarolina/` and an unpublished draft in
   `data/photography.json` with `"set": "north-carolina"`. If the set is new, it is added to
   `data/photo-sets.json` with the title "North Carolina".
3. In `data/photography.json`, for each new draft: write the `alt` text, check `chapter`
   (`places`, `people` or `gatherings`; it starts as `places`), and set `published` to `true`.
4. Optional, in `data/photo-sets.json`: fix the `title`, add `place` ("USA"), `year`, a one-line
   `blurb`, and `cover` (a photo id). The list order is the order on the site.
5. Run `python3 scripts/render-photography.py` and the tests.

The set shows up on /photography/ (link: `/photography/#set-north-carolina`) and as a link
on the homepage gallery once it has at least one published photo. An empty set never shows.

To put an existing photo in a set, add `"set": "<slug>"` to its entry in `data/photography.json`.

## Single photos (no set)

Drop files straight into `photos/inbox/` and run the same importer. They land in
`photos/library/` as unassigned drafts: write alt text, pick a `chapter`, set `published` to
`true`, and render. Leave `sequence` as `null` unless you want the frame in the homepage edit.

Nothing is ever published automatically, and the original inbox files are kept.
