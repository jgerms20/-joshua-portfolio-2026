import json
from functools import lru_cache
from html import escape
from pathlib import Path, PurePosixPath
import re

from PIL import Image, ImageOps


CHAPTERS = ("people", "places", "gatherings")
LAYOUTS = {"hero", "wide", "inset", "pair-left", "pair-right", "archive"}
REQUIRED_FIELDS = {"id", "src", "alt", "chapter", "published", "sequence", "layout"}

# A set slug: lowercase words joined by single hyphens ("north-carolina").
SET_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SETS_FILE = "data/photo-sets.json"


def load_photography_manifest(path: Path) -> list[dict[str, object]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("entries"), list):
        raise ValueError("photography manifest must contain version 1 and an entries list")

    published: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    for entry in payload["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("photography entry must be an object")
        missing = REQUIRED_FIELDS.difference(entry)
        if missing:
            raise ValueError(f"photography entry missing fields: {', '.join(sorted(missing))}")

        identifier = str(entry["id"]).strip()
        source = str(entry["src"]).strip()
        source_path = PurePosixPath(source)
        if not identifier or identifier in seen_ids:
            raise ValueError(f"duplicate or blank photography id: {identifier}")
        if not source or source in seen_sources:
            raise ValueError(f"duplicate or blank photography source: {source}")
        if source_path.is_absolute() or ".." in source_path.parts:
            raise ValueError(f"photography source must be repository-relative: {source}")
        if entry["chapter"] not in CHAPTERS and not (
            entry["chapter"] == "unassigned" and entry["published"] is False
        ):
            raise ValueError(f"invalid photography chapter: {entry['chapter']}")
        if entry["layout"] not in LAYOUTS:
            raise ValueError(f"invalid photography layout: {entry['layout']}")
        if not isinstance(entry["published"], bool):
            raise ValueError("photography published must be true or false")
        sequence = entry["sequence"]
        if sequence is not None and (not isinstance(sequence, int) or sequence < 1):
            raise ValueError("photography sequence must be null or a positive integer")
        if entry.get("set") is not None and not SET_SLUG.match(str(entry["set"])):
            raise ValueError(f"photography set must be a set slug like north-carolina: {entry['set']}")
        if entry.get("project") is not None and not str(entry["project"]).strip():
            raise ValueError("photography project must be a non-empty name when set")
        for flag in ("commissioned", "spec"):
            if flag in entry and not isinstance(entry[flag], bool):
                raise ValueError(f"photography {flag} must be true or false")
        if entry.get("commissioned") is True and entry.get("spec") is True:
            raise ValueError(f"photography entry {identifier} cannot be both commissioned and spec")

        seen_ids.add(identifier)
        seen_sources.add(source)
        if entry["published"]:
            published.append(entry)
    return published


# ---- Sets -------------------------------------------------------------
# A set is a place or theme ("Rio de Janeiro", "North Carolina"), listed in
# display order in data/photo-sets.json. A photograph joins one with a
# "set": "<slug>" field in data/photography.json. A set with no published
# photographs is not shown anywhere.
SET_TEXT_FIELDS = ("place", "year", "blurb", "cover")
SET_FIELDS = {"slug", "title", "prints", *SET_TEXT_FIELDS}
# Small words that stay lowercase in a title made from a folder name.
_TITLE_SMALL_WORDS = {"de", "da", "do", "dos", "das", "del", "la", "le", "of", "the", "and", "y", "e"}


def load_photo_sets(path: Path) -> list[dict[str, object]]:
    path = Path(path)
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("sets"), list):
        raise ValueError("photo sets file must contain version 1 and a sets list")
    sets: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in payload["sets"]:
        if not isinstance(item, dict):
            raise ValueError("each photo set must be an object")
        unknown = set(item).difference(SET_FIELDS)
        if unknown:
            raise ValueError(f"photo set has unknown fields: {', '.join(sorted(unknown))}")
        slug = str(item.get("slug") or "").strip()
        if not SET_SLUG.match(slug) or slug in seen:
            raise ValueError(f"duplicate or invalid photo set slug: {slug!r}")
        title = str(item.get("title") or "").strip()
        if not title:
            raise ValueError(f"photo set {slug} needs a title")
        clean: dict[str, object] = {"slug": slug, "title": title}
        for key in SET_TEXT_FIELDS:
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, (bool, dict, list)):
                raise ValueError(f"photo set {slug}: {key} must be text")
            if str(value).strip():
                clean[key] = str(value).strip()
        if "prints" in item:
            if not isinstance(item["prints"], bool):
                raise ValueError(f"photo set {slug}: prints must be true or false")
            clean["prints"] = item["prints"]
        seen.add(slug)
        sets.append(clean)
    return sets


def set_title_from_slug(slug: str) -> str:
    """north-carolina -> North Carolina; rio-de-janeiro -> Rio de Janeiro."""
    words = [word for word in slug.split("-") if word]
    return " ".join(
        word if index and word in _TITLE_SMALL_WORDS else word.capitalize()
        for index, word in enumerate(words)
    )


def set_folder(slug: str) -> str:
    """Folder an imported set photo lands in: letters only (north-carolina -> northcarolina).

    Resized copies are named <folder>-<name>-<width>.webp and the network site
    mirrors them with the pattern ([a-z]+)-(.+)-480.webp, so the folder part
    must be plain letters.
    """
    return re.sub(r"[^a-z]", "", slug.lower()) or "library"


def build_photo_sets(
    photos: list[dict[str, object]], sets: list[dict[str, object]]
) -> list[dict[str, object]]:
    """The sets that have published photographs, in display order, with their frames."""
    known = {str(definition["slug"]) for definition in sets}
    unknown = sorted({str(photo["set"]) for photo in photos if photo.get("set") and photo["set"] not in known})
    if unknown:
        raise ValueError(f"photographs name sets missing from {SETS_FILE}: {', '.join(unknown)}")
    built = []
    for definition in sets:
        frames = [photo for photo in photos if photo.get("set") == definition["slug"]]
        if frames:
            built.append(
                {**definition, "id": f"set-{definition['slug']}", "frames": _order_frames(frames, definition.get("cover"))}
            )
    return built


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "photograph"


SUPPORTED_IMPORTS = {".jpg", ".jpeg", ".png", ".webp"}


def import_photography_inbox(root: Path) -> list[dict[str, object]]:
    """Turn new files in photos/inbox/ into unpublished manifest drafts.

    Files directly in photos/inbox/ become loose drafts in photos/library/.
    Files in photos/inbox/<set-slug>/ join that set: they land in
    photos/<setslug>/, get "set": "<set-slug>", and the set is added to
    data/photo-sets.json if it is not there yet.
    """
    root = Path(root)
    inbox = root / "photos/inbox"
    manifest_path = root / "data/photography.json"
    sets_path = root / SETS_FILE
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if payload.get("version") != 1 or not isinstance(entries, list):
        raise ValueError("photography manifest must contain version 1 and an entries list")

    existing_inbox_sources = {str(entry.get("inbox_source", "")) for entry in entries}
    existing_ids = {str(entry.get("id", "")) for entry in entries}
    imported: list[dict[str, object]] = []
    new_sets: list[dict[str, object]] = []
    known_sets = {str(item["slug"]) for item in load_photo_sets(sets_path)}

    candidates: list[tuple[Path, str | None]] = []
    for item in sorted(inbox.iterdir() if inbox.is_dir() else []):
        if item.is_dir() and not item.name.startswith((".", "_")):
            set_slug = _slugify(item.name)
            candidates += [(source, set_slug) for source in sorted(item.iterdir())]
        else:
            candidates.append((item, None))

    for source, set_slug in candidates:
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_IMPORTS:
            continue
        inbox_source = source.relative_to(root).as_posix()
        if inbox_source in existing_inbox_sources:
            continue

        base = _slugify(source.stem)
        if set_slug and not base.startswith(set_slug):
            base = f"{set_slug}-{base}"
        identifier = base
        counter = 2
        while identifier in existing_ids:
            identifier = f"{base}-{counter}"
            counter += 1

        output_directory = root / "photos" / (set_folder(set_slug) if set_slug else "library")
        output_directory.mkdir(parents=True, exist_ok=True)
        output = output_directory / f"{identifier}.webp"
        with Image.open(source) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.save(output, format="WEBP", quality=86, method=6)

        entry: dict[str, object] = {
            "id": identifier,
            "src": output.relative_to(root).as_posix(),
            "alt": "",
            # Set photos are usually places; change it if the frame is people or a gathering.
            "chapter": "places" if set_slug else "unassigned",
            "published": False,
            "sequence": None,
            "layout": "archive",
        }
        if set_slug:
            entry["set"] = set_slug
            if set_slug not in known_sets:
                known_sets.add(set_slug)
                new_sets.append({"slug": set_slug, "title": set_title_from_slug(set_slug)})
        entry["inbox_source"] = inbox_source
        entries.append(entry)
        imported.append(entry)
        existing_ids.add(identifier)
        existing_inbox_sources.add(inbox_source)

    if imported:
        manifest_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if new_sets:
        sets_payload = (
            json.loads(sets_path.read_text(encoding="utf-8")) if sets_path.is_file() else {"version": 1, "sets": []}
        )
        sets_payload["sets"].extend(new_sets)
        sets_path.parent.mkdir(parents=True, exist_ok=True)
        sets_path.write_text(json.dumps(sets_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return imported


# How many photos the homepage gallery shows before "See more".
GALLERY_PREVIEW = 14


def _gallery_tile(photo: dict[str, object], index: int, *, extra: bool) -> str:
    width, height = _image_size(str(Path(__file__).resolve().parents[1]), str(photo["src"]))
    chapter = escape(str(photo["chapter"]))
    classes = "photo-item gallery-tile" + (" is-extra" if extra else "")
    loading = "eager" if index < 3 else "lazy"
    return (
        f'<figure class="{classes}" data-cat="{chapter}" data-chapter="{chapter}" '
        f'style="--r:{width / height:.4f}" tabindex="0" role="button" '
        f'aria-label="{escape("Open photograph: " + str(photo["alt"]))}">'
        f'<img loading="{loading}" decoding="async" src="{escape(str(photo["src"]))}" '
        f'alt="{escape(str(photo["alt"]))}" width="{width}" height="{height}"></figure>'
    )


def render_darkroom(
    photos: list[dict[str, object]],
    sets: list[dict[str, object]] | None = None,
    coverage: list[dict[str, object]] | None = None,
) -> str:
    """Homepage photography chapter.

    A short offer band first (what Joshua shoots, booking through the
    Studio, the latest event coverage), then one justified grid (every frame
    keeps its own ratio), curated sequence first, then the rest of the
    archive behind "See more". A row of set links (Rio de Janeiro, ...) sits
    under the filters when sets exist.
    """
    if sets is None:
        sets = load_photo_sets(REPO_ROOT / SETS_FILE)
    curated = sorted(
        (photo for photo in photos if photo.get("sequence") is not None),
        key=lambda photo: int(photo["sequence"]),
    )
    ordered = curated + [photo for photo in photos if photo.get("sequence") is None]
    tiles = "\n                ".join(
        _gallery_tile(photo, i, extra=i >= GALLERY_PREVIEW) for i, photo in enumerate(ordered)
    )
    hidden = max(0, len(ordered) - GALLERY_PREVIEW)
    more_button = (
        '<button type="button" class="darkroom-more gallery-more" data-reveal="photoGallery" '
        'aria-controls="photoGallery" aria-expanded="false" data-open-label="See less" '
        f'data-closed-label="See more" data-open-count="All {len(ordered)} photos" '
        f'data-closed-count="{hidden} more photos"><span class="darkroom-more__label">See more</span>'
        f'<span class="darkroom-more__count">{hidden} more photos</span></button>'
        if hidden
        else ""
    )
    if coverage is None:
        coverage = load_photo_site_settings(REPO_ROOT / "data/photography.json")["coverage"]
    return f'''<section id="photography" class="chapter chapter-dark">
        <div class="wrap">
            <div class="ch-head rv">
                <div class="ch-head-left">
                    <span class="ch-num">CH. 03</span>
                    <h2 class="ch-title"><span class="it">Photography</span></h2>
                </div>
                <div class="ch-meta">Portraits · Fashion<br>Event coverage</div>
            </div>
            {_darkroom_offer(photos, coverage)}
            <div class="gallery-bar rv">
                <div class="photo-chapters" aria-label="Filter photographs">
                    <button class="photo-chapter active" data-filter="all" aria-pressed="true">All</button>
                    <button class="photo-chapter" data-filter="people" aria-pressed="false">People</button>
                    <button class="photo-chapter" data-filter="places" aria-pressed="false">Places</button>
                    <button class="photo-chapter" data-filter="gatherings" aria-pressed="false">Gatherings</button>
                </div>
                {_darkroom_cta()}{_darkroom_sets(build_photo_sets(photos, sets))}
            </div>
            <div class="photo-grid rv" id="photoGallery">
                {tiles}
                <span class="gallery-filler" aria-hidden="true"></span>
            </div>
            {more_button}
        </div>
    </section>'''


def _external(url: str) -> str:
    """href plus the new-tab attributes every off-site link here carries."""
    return f'href="{_attr(url)}" target="_blank" rel="noopener"'


# Inline styles for the homepage offer band: index.html is hand-authored and
# owned elsewhere, so the band uses only its existing tokens and classes.
_HP_LABEL = (
    "font-family:var(--mono);font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;"
    "color:var(--paper-on-dark-mid);margin:0 0 14px"
)
_HP_SOFT = "color:var(--paper-on-dark-soft);font-size:0.98rem;line-height:1.55;margin:0;max-width:46ch"


def _darkroom_offer(photos: list[dict[str, object]], coverage: list[dict[str, object]]) -> str:
    """What Joshua shoots, where paid shoots are booked, and the latest coverage."""
    specialties = "".join(
        f'<li style="display:flex;justify-content:space-between;align-items:baseline;gap:16px;'
        f'padding:12px 0;border-bottom:1px solid var(--dark-rule)">'
        f'<span style="font-family:var(--serif);font-size:clamp(1.3rem,2.4vw,1.8rem);line-height:1.1">{escape(name)}</span>'
        f'<span style="font-family:var(--mono);font-size:0.56rem;letter-spacing:0.16em;text-transform:uppercase;'
        f'color:var(--paper-on-dark-mid);text-align:right">{escape(short)}</span></li>'
        for name, short, _ in SERVICES
    )
    offer = (
        '<div style="min-width:0">'
        f'<p style="{_HP_LABEL}">What I shoot</p>'
        f'<ul style="list-style:none;margin:0 0 18px;padding:0;border-top:1px solid var(--dark-rule)">{specialties}</ul>'
        f'<p style="{_HP_SOFT}">Client shoots are booked through my company, The Curious &amp; Creative Company.</p>'
        '<div class="gallery-links" style="margin-top:18px">'
        f'<a class="gallery-link gallery-link--book" {_external(STUDIO_PHOTO_URL)}>{STUDIO_BOOK_LABEL}</a>'
        f'<a class="gallery-link gallery-link--book" {_external(STUDIO_EVENTS_URL)}>{STUDIO_EVENTS_LABEL}</a>'
        "</div></div>"
    )
    latest = next((item for item in coverage if item.get("published", True)), None)
    entry = _darkroom_coverage(latest, {str(p["id"]): p for p in photos}) if latest else ""
    return (
        '<div class="rv" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));'
        'gap:clamp(32px,5vw,72px);align-items:start;padding-bottom:clamp(32px,4vw,48px);'
        f'margin-bottom:clamp(28px,4vw,44px);border-bottom:1px solid var(--dark-rule)">{offer}{entry}</div>'
    )


def _darkroom_coverage(item: dict[str, object], by_id: dict[str, dict[str, object]]) -> str:
    """The latest event coverage entry: type-led, with stills when the data has them."""
    stills = _coverage_stills(item, by_id)[:3]
    stills_markup = ""
    if stills:
        frames = "".join(
            f'<a href="photography/#{_attr(_stills_id(item))}" style="display:block;flex:1;min-width:0">'
            f'<img loading="lazy" decoding="async" src="{_attr(still["src"])}" alt="{_attr(still["alt"])}" '
            f'width="{_image_size(str(REPO_ROOT), str(still["src"]))[0]}" height="{_image_size(str(REPO_ROOT), str(still["src"]))[1]}" '
            f'style="width:100%;height:auto;aspect-ratio:4/5;object-fit:cover;display:block;background:var(--dark-raised)"></a>'
            for still in stills
        )
        stills_markup = f'<div style="display:flex;gap:8px;margin-top:20px">{frames}</div>'
    credits = "".join(f'<p style="{_HP_SOFT};margin-top:8px">{escape(line)}</p>' for line in item["credits"])
    title_id = f"hp-{_coverage_id(item)}-title"
    return (
        f'<article aria-labelledby="{title_id}" style="min-width:0;border-top:2px solid var(--vermilion);padding-top:18px">'
        f'<p style="{_HP_LABEL}"><span style="color:var(--vermilion)">{escape(str(item["specialty"]))}</span>'
        f' &middot; <time datetime="{_attr(item["date"])}">{escape(_date_label(item["date"]))}</time></p>'
        f'<h3 id="{title_id}" style="font-family:var(--serif);font-weight:400;font-size:clamp(1.8rem,3.4vw,2.8rem);'
        f'line-height:1.02;letter-spacing:-0.015em;margin:0 0 14px">{escape(str(item["title"]))}</h3>'
        f'<p style="{_HP_SOFT};color:var(--paper-on-dark)">{escape(str(item["summary"]))}</p>'
        f"{credits}{stills_markup}"
        '<div class="gallery-links" style="margin-top:20px">'
        f'<a class="gallery-link" href="photography/#{_attr(_coverage_id(item))}">On the photography site&nbsp;&rarr;</a>'
        "</div></article>"
    )


def _darkroom_cta() -> str:
    """Quiet links beside the filters: the full photo site and Instagram."""
    return (
        '<div class="gallery-links">'
        '<a class="gallery-link" href="photography/">Full photography site&nbsp;&rarr;</a>'
        f'<a class="gallery-link" {_external(INSTAGRAM_URL)}>Instagram {escape(INSTAGRAM_HANDLE)}&nbsp;&#8599;</a>'
        "</div>"
    )


def _darkroom_sets(photo_sets: list[dict[str, object]]) -> str:
    """One quiet row of set links under the filters. Styled inline with the
    homepage's own gallery-link class, so index.html needs no new CSS."""
    if not photo_sets:
        return ""
    links = "".join(
        f'<a class="gallery-link" href="photography/#{_attr(item["id"])}">{escape(str(item["title"]))}&nbsp;&rarr;</a>'
        for item in photo_sets
    )
    return (
        '\n                <nav class="gallery-links gallery-sets" aria-label="Photo sets" style="flex-basis:100%">'
        '<span class="gallery-link" style="border-bottom-color:transparent;color:var(--paper-on-dark-soft)">Sets</span>'
        f"{links}</nav>"
    )


# =====================================================================
# The photography site: /photography/
#
# A standalone page inside the main site, built for a business-card QR
# code. photography/index.html is a hand-authored shell (head, styles,
# nav, lightbox, footer, script). Everything between the PHOTO-SITE
# markers is rendered here from data/photography.json and
# data/photo-sets.json.
#
# The page is four views: Work, About, Services, Book. Each is a
# server-rendered <section data-view>. Without JavaScript they stack as one
# page; with it, the shell's router shows one view per hash (#about,
# #services, #book; empty or #work is Work; #set-<slug> opens Work and that
# set in the viewer).
#
# Optional keys the renderer understands on a manifest entry:
#   set           a set slug from data/photo-sets.json (place/theme collection)
#   project       a group name for "More work"; overrides the folder mapping
#   commissioned  true shows a "Commissioned" tag in the viewer. Only for
#                 work a client actually paid for.
#   spec          true shows a "Spec" tag in the viewer: self-initiated or
#                 speculative work that must not read as a client commission.
#                 An entry cannot be both.
#   recent        true adds the frame to a "Recent" strip under the hero
# Optional top-level manifest keys:
#   site.shoots   list of {"project", "type", "year"} for a "Selected shoots"
#                 rundown under the Work view. Real shoots only; empty hides it.
#   site.coverage list of event coverage entries (see _load_coverage), newest
#                 first. Rendered text-led on the Work view and in the
#                 homepage band; "stills" (published entry ids) add frames.
#
# Network mirror contract: github.com/jgerms20/curious-and-creative scrapes
# this page and mirrors every <img> whose src (or last srcset candidate)
# matches /_sized/([a-z]+)-(.+)-480.webp. Every published photograph keeps
# one such image, with its real alt text, in the server-rendered HTML.
# =====================================================================

PHOTO_SITE_START = "<!-- PHOTO-SITE:START -->"
PHOTO_SITE_END = "<!-- PHOTO-SITE:END -->"
PHOTO_SITE_URL = "https://joshuamgerman.com/photography/"
# What the business-card QR code encodes. ?src=card preselects "Business card"
# under "How did you find me?" so card inquiries can be told apart.
PHOTO_SITE_CARD_URL = PHOTO_SITE_URL + "?src=card"
PHOTO_SITE_PREFIX = "../"
# Personal "say hi" address. Paid shoots are not booked here (see STUDIO_*).
INQUIRY_EMAIL = "jgerms20@gmail.com"
INSTAGRAM_URL = "https://www.instagram.com/viewsbygerm/"
INSTAGRAM_HANDLE = "@viewsbygerm"

# Client photography is booked through Joshua's company, The Curious &
# Creative Company ("The Studio"), on its inquiry form. Every booking CTA on
# the photo site and in the homepage block goes to one of these.
STUDIO_PHOTO_URL = "https://jgerms20.github.io/curious-and-creative/pages/contact.html?topic=photo"
STUDIO_EVENTS_URL = "https://jgerms20.github.io/curious-and-creative/pages/contact.html?topic=events"
STUDIO_BOOK_TEXT = "Book through The Curious &amp; Creative Studio"
STUDIO_BOOK_LABEL = STUDIO_BOOK_TEXT + "&nbsp;&#8599;"
STUDIO_EVENTS_LABEL = "Book event coverage through the Studio&nbsp;&#8599;"

REPO_ROOT = Path(__file__).resolve().parents[1]

VIEWS = ("work", "about", "services", "book")

HERO_LEAD = "red-coat-studio"
HERO_LEAD_POSITION = "50% 18%"
HERO_STRIP = ("rio-santa-teresa-trams", "plates-in-progress", "concert-light")

# Joshua picks the About portrait; this one is him behind a camera.
ABOUT_PORTRAIT = {
    "src": "photos/self/IMG_1912.jpg",
    "alt": "Joshua McKenzie German raising a camera to his eye outdoors.",
}
# One frame beside the Services list, so the view stays image-led.
SERVICES_PHOTO = "artist-in-studio"
SERVICES_PHOTO_POSITION = "50% 40%"

# The named specialties: (name, short tag for the homepage band, description).
SERVICES = (
    ("Portraits", "People & headshots", "People, headshots, personal sessions."),
    ("Fashion & editorial", "Lookbooks & tests", "Lookbooks, styling tests, campaigns."),
    ("Event coverage", "Documentary & BTS", "Documentary and behind the scenes: presentations, concerts, parties, launches."),
)
ALSO_BOOKING = "Also booking: product, food and spaces."

# The "More work" groups: folder-based, kept beside the sets for the
# single frames and loose groupings Joshua wants to show too.
PHOTO_PROJECTS = (
    {"slug": "portraits", "title": "Portraits", "match": ("photos/portraits/",), "cover": "father-and-child", "position": "38% 50%"},
    {"slug": "fashion", "title": "Fashion", "match": ("photos/fashion/",), "cover": "red-accent-studio", "position": "50% 40%"},
    {"slug": "events", "title": "Events & Live", "match": ("photos/events/",), "cover": "blue-lit-performer", "position": "50% 30%"},
    {"slug": "landscapes", "title": "Landscapes", "match": ("photos/landscape/",), "cover": "misty-valley", "position": "50% 50%"},
    {"slug": "travel", "title": "Travel", "match": ("photos/travel/",), "cover": "palms-at-dusk", "position": "72% 50%"},
)
# Published frames that are in no set and no folder group.
FALLBACK_PROJECT = {"slug": "archive", "title": "Archive", "match": (), "cover": None, "position": "50% 50%"}

# Element ids a group slug must not take over.
RESERVED_IDS = {
    "top", "main", "hero", "recent", "work", "sets", "coverage", "more", "shoots", "galleries",
    "about", "services", "book", "inquiry", "lightbox", *VIEWS,
}
# Id prefixes owned by sets and coverage entries.
RESERVED_PREFIXES = ("set-", "coverage-", "stills-")


@lru_cache(maxsize=None)
def _image_size(root: str, source: str) -> tuple[int, int]:
    path = Path(root) / source
    if not path.is_file():
        raise FileNotFoundError(f"photograph listed in the manifest is missing: {source}")
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).size


def _attr(value: object) -> str:
    return escape(str(value), quote=True)


# ---- Resized copies -------------------------------------------------
# The originals are ~2000px JPEGs of 150-450 KB. The photography site is
# opened from a business-card QR code, often over cellular, so every <img>
# on it points at WebP copies sized for how big the frame is drawn, with a
# srcset. Originals are only fetched by the full-screen viewer.
SIZED_DIR = "photos/_sized"
SIZED_QUALITY = 78
# Widths per placement. Each list is filtered to widths below the original.
WIDTHS_HERO = (640, 960, 1280)
WIDTHS_SET = (480, 960, 1280)
WIDTHS_COVER = (480, 960)
# 480 only: these are the images the network mirror reads (see above).
WIDTHS_THUMB = (480,)
SIZES_HERO = "(min-width: 700px) min(40vw, 580px), calc(100vw - 32px)"
SIZES_SET = "(min-width: 900px) min(60vw, 880px), calc(100vw - 32px)"
SIZES_COVER = "(min-width: 720px) min(30vw, 470px), calc(100vw - 32px)"
SIZES_STRIP = "(min-width: 700px) 18vw, 1px"
SIZES_ABOUT = "(min-width: 800px) 440px, calc(100vw - 32px)"
SIZES_THUMB = "(min-width: 900px) 160px, 31vw"

# Every variant the last render asked for: {repo-relative output: (source, width)}.
_requested_variants: dict[str, tuple[str, int]] = {}


def _variant_path(source: str, width: int) -> str:
    path = PurePosixPath(source)
    return f"{SIZED_DIR}/{path.parent.name}-{path.stem}-{width}.webp"


def _variants(root: Path, source: str, widths: tuple[int, ...]) -> list[tuple[int, str]]:
    original_width, _ = _image_size(str(root), source)
    chosen = []
    for width in widths:
        if width < original_width:
            output = _variant_path(source, width)
            _requested_variants[output] = (source, width)
            chosen.append((width, output))
    return chosen


def write_sized_images(root: Path | None = None) -> list[str]:
    """Write (or refresh) every resized copy the last render referenced."""
    root = Path(root or REPO_ROOT)
    written = []
    for output, (source, width) in sorted(_requested_variants.items()):
        target = root / output
        original = root / source
        if target.is_file() and target.stat().st_mtime >= original.stat().st_mtime:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(original) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            height = round(image.height * width / image.width)
            image = image.resize((width, height), Image.LANCZOS)
            image.save(target, format="WEBP", quality=SIZED_QUALITY, method=6)
        written.append(output)
    return written


def missing_sized_images(root: Path | None = None) -> list[str]:
    root = Path(root or REPO_ROOT)
    return sorted(output for output in _requested_variants if not (root / output).is_file())


def _site_img(
    photo: dict[str, object],
    *,
    root: Path,
    loading: str = "lazy",
    position: str = "",
    priority: bool = False,
    low_priority: bool = False,
    alt: str | None = None,
    widths: tuple[int, ...] = WIDTHS_COVER,
    sizes: str = SIZES_COVER,
) -> str:
    source = str(photo["src"])
    width, height = _image_size(str(root), source)
    variants = _variants(Path(root), source, widths)
    if variants:
        # The src fallback is the largest copy; srcset lets the browser go smaller.
        src = variants[-1][1]
        srcset = ", ".join(f"{PHOTO_SITE_PREFIX}{path} {w}w" for w, path in variants)
        responsive = [f'srcset="{_attr(srcset)}"', f'sizes="{_attr(sizes)}"']
    else:
        src, responsive = source, []
    parts = [
        f'<img src="{_attr(PHOTO_SITE_PREFIX + src)}"',
        *responsive,
        f'width="{width}" height="{height}"',
        f'alt="{_attr(photo["alt"] if alt is None else alt)}"',
        f'loading="{loading}" decoding="async"',
    ]
    if priority:
        parts.append('fetchpriority="high"')
    elif low_priority:
        parts.append('fetchpriority="low"')
    if position:
        parts.append(f'style="object-position: {_attr(position)};"')
    return " ".join(parts) + ">"


def _order_frames(frames: list[dict[str, object]], cover: object) -> list[dict[str, object]]:
    """Cover first, then the curated sequence, then everything else in manifest order."""
    sequenced = sorted(
        (frame for frame in frames if frame.get("sequence") is not None),
        key=lambda frame: int(frame["sequence"]),
    )
    rest = [frame for frame in frames if frame.get("sequence") is None]
    ordered = sequenced + rest
    lead = [frame for frame in ordered if frame["id"] == cover]
    return lead + [frame for frame in ordered if frame["id"] != cover]


def _safe_slug(slug: str) -> str:
    return f"work-{slug}" if slug in RESERVED_IDS or slug.startswith(RESERVED_PREFIXES) else slug


def group_photo_site(photos: list[dict[str, object]]) -> list[dict[str, object]]:
    """The "More work" groups: folder groups, then named projects, then an archive.

    A frame in a set also shows in its folder group (Portraits, Landscapes...),
    but never falls through to the archive just because no folder matched.
    """
    known = {project["slug"]: project for project in PHOTO_PROJECTS}
    titles = {_slugify(project["title"]): project["slug"] for project in PHOTO_PROJECTS}
    buckets: dict[str, list[dict[str, object]]] = {}
    custom: dict[str, dict[str, object]] = {}

    for photo in photos:
        explicit = str(photo.get("project") or "").strip()
        if explicit:
            slug = _slugify(explicit)
            slug = titles.get(slug, slug)
            if slug not in known and slug not in custom:
                custom[slug] = {
                    "key": slug, "slug": _safe_slug(slug), "title": explicit,
                    "match": (), "cover": None, "position": "50% 50%",
                }
            buckets.setdefault(slug, []).append(photo)
            continue
        source = str(photo["src"])
        slug = next(
            (
                project["slug"]
                for project in PHOTO_PROJECTS
                if any(source.startswith(prefix) for prefix in project["match"])
            ),
            None,
        )
        if slug is None:
            if photo.get("set"):
                continue
            slug = FALLBACK_PROJECT["slug"]
        buckets.setdefault(slug, []).append(photo)

    projects = []
    for definition in (*PHOTO_PROJECTS, *custom.values(), FALLBACK_PROJECT):
        frames = buckets.get(str(definition.get("key", definition["slug"])), [])
        if frames:
            projects.append({**definition, "frames": _order_frames(frames, definition["cover"])})
    return projects


def load_photo_site_settings(path: Path) -> dict[str, object]:
    """Optional page settings stored beside the entries in the manifest."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    site = payload.get("site") or {}
    if not isinstance(site, dict):
        raise ValueError("photography manifest 'site' must be an object")
    shoots = site.get("shoots") or []
    if not isinstance(shoots, list):
        raise ValueError("photography manifest 'site.shoots' must be a list")
    cleaned = []
    for shoot in shoots:
        if not isinstance(shoot, dict) or not str(shoot.get("project", "")).strip():
            raise ValueError("each photography 'site.shoots' entry needs a project name")
        cleaned.append({key: str(shoot.get(key) or "").strip() for key in ("project", "type", "year")})
    return {"shoots": cleaned, "coverage": _load_coverage(site.get("coverage") or [])}


COVERAGE_FIELDS = {"slug", "specialty", "title", "date", "summary", "credits", "stills", "published"}


def _load_coverage(items: object) -> list[dict[str, object]]:
    """site.coverage: event coverage entries, newest first. Text-led; stills optional.

    Each entry: slug, title, date (YYYY-MM-DD), summary, credits (list of
    lines), optional specialty (default "Event coverage"), optional stills
    (ids of published manifest entries, shown when present), optional
    published (default true; false keeps a draft out of both outputs).
    """
    if not isinstance(items, list):
        raise ValueError("photography manifest 'site.coverage' must be a list")
    cleaned: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each 'site.coverage' entry must be an object")
        unknown = set(item).difference(COVERAGE_FIELDS)
        if unknown:
            raise ValueError(f"coverage entry has unknown fields: {', '.join(sorted(unknown))}")
        slug = str(item.get("slug") or "").strip()
        if not SET_SLUG.match(slug) or slug in seen:
            raise ValueError(f"duplicate or invalid coverage slug: {slug!r}")
        for key in ("title", "date", "summary"):
            if not str(item.get(key) or "").strip():
                raise ValueError(f"coverage entry {slug} needs a {key}")
        _date_label(str(item["date"]))  # raises on a malformed date
        credits = item.get("credits") or []
        stills = item.get("stills") or []
        if not isinstance(credits, list) or not all(isinstance(line, str) and line.strip() for line in credits):
            raise ValueError(f"coverage entry {slug}: credits must be a list of lines")
        if not isinstance(stills, list) or not all(isinstance(still, str) and still.strip() for still in stills):
            raise ValueError(f"coverage entry {slug}: stills must be a list of photograph ids")
        published = item.get("published", True)
        if not isinstance(published, bool):
            raise ValueError(f"coverage entry {slug}: published must be true or false")
        seen.add(slug)
        if not published:
            continue
        cleaned.append({
            "slug": slug,
            "specialty": str(item.get("specialty") or "Event coverage").strip(),
            "title": str(item["title"]).strip(),
            "date": str(item["date"]).strip(),
            "summary": str(item["summary"]).strip(),
            "credits": [line.strip() for line in credits],
            "stills": [still.strip() for still in stills],
        })
    return cleaned


_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _date_label(value: str) -> str:
    """2026-11-07 -> November 7, 2026."""
    from datetime import date

    try:
        day = date.fromisoformat(str(value).strip())
    except ValueError as error:
        raise ValueError(f"coverage date must be YYYY-MM-DD: {value!r}") from error
    return f"{_MONTHS[day.month - 1]} {day.day}, {day.year}"


def _coverage_id(item: dict[str, object]) -> str:
    return f"coverage-{item['slug']}"


def _stills_id(item: dict[str, object]) -> str:
    return f"stills-{item['slug']}"


def _coverage_stills(item: dict[str, object], by_id: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    missing = [still for still in item["stills"] if still not in by_id]
    if missing:
        raise ValueError(
            f"coverage entry {item['slug']} names stills that are not published photographs: {', '.join(missing)}"
        )
    return [by_id[still] for still in item["stills"]]


def _arrow() -> str:
    return '<span class="arr" aria-hidden="true">&rarr;</span>'


def _ext_arrow() -> str:
    """Off-site arrow, with words for screen readers."""
    return '<span class="arr" aria-hidden="true">&#8599;</span><span class="visually-hidden"> (opens in a new tab)</span>'


def _tail_arrow() -> str:
    """Arrow glued to the last word so it never wraps onto a line of its own."""
    return "&nbsp;" + _arrow()


def _section_head(title: str, meta: str, section_id: str, *, view_heading: bool = False) -> str:
    focus = ' tabindex="-1" data-view-heading' if view_heading else ""
    meta_markup = f'<p class="sec-meta">{meta}</p>' if meta else ""
    return (
        f'<header class="sec-head rv">'
        f'<h2 class="sec-title" id="{section_id}-title"{focus}>{title}</h2>'
        f"{meta_markup}</header>"
    )


def _count(number: int, noun: str) -> str:
    return f"{number:02d} {noun}{'' if number == 1 else 's'}"


def _render_hero(
    by_id: dict[str, dict[str, object]],
    placement: dict[str, tuple[str, int]],
    titles: dict[str, str],
    root: Path,
    see_href: str,
) -> str:
    lead = by_id.get(HERO_LEAD)
    lead_markup = ""
    if lead:
        slug, index = placement.get(HERO_LEAD, ("", 0))
        image = _site_img(
            lead, root=root, loading="eager", priority=True, position=HERO_LEAD_POSITION,
            widths=WIDTHS_HERO, sizes=SIZES_HERO,
        )
        lead_markup = (
            f'<figure class="hero-lead">'
            f'<a class="hero-lead__link" href="#{_attr(slug)}" data-open="{_attr(slug)}" data-index="{index}" '
            f'aria-label="Open {_attr(titles.get(slug, "photography"))} at this frame">{image}</a>'
            f'<figcaption><span class="fig-no">Fig. 01</span><span>{escape(titles.get(slug, ""))}</span></figcaption>'
            f"</figure>"
        )

    strip_items = []
    for number, identifier in enumerate(HERO_STRIP, start=2):
        photo = by_id.get(identifier)
        if not photo:
            continue
        slug, index = placement.get(identifier, ("", 0))
        strip_items.append(
            f'<li class="strip-frame">'
            f'<a href="#{_attr(slug)}" data-open="{_attr(slug)}" data-index="{index}" '
            f'aria-label="Open {_attr(titles.get(slug, "photography"))} at this frame">'
            f'{_site_img(photo, root=root, loading="lazy", low_priority=True, sizes=SIZES_STRIP)}</a>'
            f'<span class="strip-cap"><span class="fig-no">{number:02d}</span>{escape(titles.get(slug, "photography"))}</span>'
            f"</li>"
        )
    strip = f'<ol class="hero-strip" aria-label="More frames">{"".join(strip_items)}</ol>' if strip_items else ""

    return f'''<section class="hero" id="hero" aria-labelledby="hero-title">
        <div class="hero-grid">
            <div class="hero-copy">
                <p class="kicker">Photography <span aria-hidden="true">&middot;</span> Los Angeles</p>
                <h1 class="hero-title" id="hero-title" tabindex="-1" data-view-heading>Joshua McKenzie <em>German</em></h1>
                <p class="hero-line">Portraits, fashion, event coverage and travel. On 35mm film and digital.</p>
                <div class="hero-actions">
                    <a class="btn btn-safelight" {_external(STUDIO_PHOTO_URL)}>Book a shoot {_ext_arrow()}</a>
                    <a class="btn btn-line" href="{see_href}">See the work</a>
                </div>
                {strip}
            </div>
            {lead_markup}
        </div>
    </section>'''


def _render_recent(photos: list[dict[str, object]], placement: dict[str, tuple[str, int]], root: Path) -> str:
    recent = [photo for photo in photos if photo.get("recent") is True][:8]
    if not recent:
        return ""
    items = []
    for photo in recent:
        slug, index = placement.get(str(photo["id"]), ("", 0))
        items.append(
            f'<li><a href="#{_attr(slug)}" data-open="{_attr(slug)}" data-index="{index}">'
            f'{_site_img(photo, root=root, widths=WIDTHS_THUMB, sizes=SIZES_THUMB)}</a></li>'
        )
    return f'''<section class="recent" id="recent" aria-labelledby="recent-title">
        <div class="wrap">
            <h2 class="recent-title" id="recent-title">Recent</h2>
            <ul class="recent-strip">{"".join(items)}</ul>
        </div>
    </section>'''


def _render_sets(photo_sets: list[dict[str, object]], root: Path) -> str:
    """The place/theme sets: one big image-led card each, leading the Work view."""
    if not photo_sets:
        return ""
    cards = []
    for item in photo_sets:
        frames = item["frames"]
        set_id = _attr(item["id"])
        title = escape(str(item["title"]))
        meta = [escape(str(item[key])) for key in ("place", "year") if item.get(key)]
        meta.append(_count(len(frames), "frame"))
        blurb = f'<p class="set-card__blurb">{escape(str(item["blurb"]))}</p>' if item.get("blurb") else ""
        thumbs = "".join(
            f'<li><a href="#{set_id}" data-open="{set_id}" data-index="{index}">'
            f"{_site_img(frame, root=root, widths=WIDTHS_THUMB, sizes=SIZES_THUMB)}</a></li>"
            for index, frame in enumerate(frames[1:4], start=1)
        )
        thumbs_markup = (
            f'<ul class="set-card__frames" aria-label="More from {_attr(item["title"])}">{thumbs}</ul>' if thumbs else ""
        )
        prints = (
            f'<a class="card-aside" href="../shop.html#photosets">In the shop{_tail_arrow()}</a>' if item.get("prints") else ""
        )
        cards.append(
            f'''<article class="set-card rv" data-set="{set_id}">
                    <div class="set-card__cover">{_site_img(frames[0], root=root, alt="", widths=WIDTHS_SET, sizes=SIZES_SET)}</div>
                    <div class="set-card__body">
                        <p class="set-card__meta">{" &middot; ".join(meta)}</p>
                        <h3 class="set-card__title"><a class="card-link" href="#{set_id}" data-open="{set_id}" data-index="0">{title}<span class="visually-hidden">, {len(frames)} frames</span></a></h3>
                        {blurb}
                        {thumbs_markup}
                        <p class="set-card__foot"><span class="set-card__open" aria-hidden="true">View set {_arrow()}</span>{prints}</p>
                    </div>
                </article>'''
        )
    total = sum(len(item["frames"]) for item in photo_sets)
    head = _section_head("Sets", f"{_count(len(photo_sets), 'set')} &middot; {_count(total, 'frame')}", "sets")
    body = "\n                ".join(cards)
    return f'''<section class="sec sec--sets" id="sets" aria-labelledby="sets-title">
        <div class="wrap">
            {head}
            <div class="set-cards">
                {body}
            </div>
        </div>
    </section>'''


def _render_coverage(
    coverage: list[dict[str, object]], by_id: dict[str, dict[str, object]], root: Path
) -> str:
    """Event coverage: one text-led entry per job. Reads complete without
    stills; when an entry lists stills they show as a strip that opens the viewer."""
    if not coverage:
        return ""
    entries = []
    for item in coverage:
        entry_id = _attr(_coverage_id(item))
        stills = _coverage_stills(item, by_id)
        stills_markup = ""
        if stills:
            gallery = _attr(_stills_id(item))
            thumbs = "".join(
                f'<li><a href="#{gallery}" data-open="{gallery}" data-index="{index}">'
                f"{_site_img(still, root=root, widths=WIDTHS_THUMB, sizes=SIZES_THUMB)}</a></li>"
                for index, still in enumerate(stills[:6])
            )
            stills_markup = f'<ul class="cov-stills" aria-label="Stills from {_attr(item["title"])}">{thumbs}</ul>'
        credits = "".join(f"<li>{escape(line)}</li>" for line in item["credits"])
        credits_markup = f'<ul class="cov-credits">{credits}</ul>' if credits else ""
        entries.append(
            f'''<article class="cov-entry rv" id="{entry_id}" aria-labelledby="{entry_id}-title">
                    <div class="cov-head">
                        <p class="cov-meta"><span class="cov-kind">{escape(str(item["specialty"]))}</span> <span aria-hidden="true">&middot;</span> <time datetime="{_attr(item["date"])}">{escape(_date_label(str(item["date"])))}</time></p>
                        <h3 class="cov-title" id="{entry_id}-title">{escape(str(item["title"]))}</h3>
                    </div>
                    <div class="cov-body">
                        <p class="cov-summary">{escape(str(item["summary"]))}</p>
                        {credits_markup}
                        {stills_markup}
                        <p class="cov-foot"><a class="card-aside" {_external(STUDIO_EVENTS_URL)}>Book event coverage{_tail_ext()}</a></p>
                    </div>
                </article>'''
        )
    head = _section_head("Event <em>coverage</em>", "Documentary &middot; Behind the scenes", "coverage")
    body = "\n                ".join(entries)
    return f'''<section class="sec sec--coverage" id="coverage" aria-labelledby="coverage-title">
        <div class="wrap">
            {head}
            <div class="cov-list">
                {body}
            </div>
        </div>
    </section>'''


def _tail_ext() -> str:
    return "&nbsp;" + _ext_arrow()


def _render_shoots(shoots: list[dict[str, str]]) -> str:
    if not shoots:
        return ""
    rows = "".join(
        f'<li><span class="shoot-name">{escape(shoot["project"])}</span>'
        f'<span class="shoot-type">{escape(shoot["type"])}</span>'
        f'<span class="shoot-year">{escape(shoot["year"])}</span></li>'
        for shoot in shoots
    )
    return f'''<div class="shoots rv" id="shoots">
                <h3 class="shoots-title">Selected shoots</h3>
                <ol class="shoots-list">{rows}</ol>
            </div>'''


def _render_more(projects: list[dict[str, object]], root: Path, shoots: list[dict[str, str]], has_sets: bool) -> str:
    """Folder groups (Portraits, Fashion...) as smaller cards under the sets."""
    if not projects and not shoots:
        return ""
    cards = []
    for project in projects:
        frames = project["frames"]
        slug = _attr(project["slug"])
        cover_image = _site_img(frames[0], root=root, position=str(project.get("position") or ""), alt="")
        cards.append(
            f'''<article class="card rv" data-set="{slug}">
                    <div class="card-cover">{cover_image}<span class="card-open" aria-hidden="true">View {_arrow()}</span></div>
                    <div class="card-body">
                        <h3 class="card-title"><a class="card-link" href="#{slug}" data-open="{slug}" data-index="0">{escape(str(project["title"]))}<span class="visually-hidden">, {len(frames)} frames</span></a></h3>
                        <p class="card-meta">{_count(len(frames), "frame")}</p>
                    </div>
                </article>'''
        )
    grid = "\n                ".join(cards)
    title = "More <em>work</em>" if has_sets else "Selected <em>work</em>"
    total = sum(len(project["frames"]) for project in projects)
    head = _section_head(title, f"{_count(total, 'frame')}" if projects else "", "more")
    return f'''<section class="sec sec--more" id="more" aria-labelledby="more-title">
        <div class="wrap">
            {head}
            <div class="cards cards--work">
                {grid}
            </div>
            {_render_shoots(shoots)}
        </div>
    </section>'''


def _render_galleries(galleries: list[dict[str, object]], root: Path) -> str:
    """Every set and group as a plain thumbnail block. Scripted pages hide these
    and read them to fill the viewer; without JS the card links jump here.

    These are also the images the network mirror reads: 480px only, real alt.
    """
    blocks = []
    for gallery in galleries:
        figures = []
        for frame in gallery["frames"]:
            width, height = _image_size(str(root), str(frame["src"]))
            tag = "Commissioned" if frame.get("commissioned") is True else "Spec" if frame.get("spec") is True else ""
            full = PHOTO_SITE_PREFIX + str(frame["src"])
            figures.append(
                f'<figure class="gallery-frame" data-full="{_attr(full)}" data-w="{width}" data-h="{height}" '
                f'data-alt="{_attr(frame["alt"])}" data-tag="{_attr(tag)}">'
                f'<a href="{_attr(full)}">{_site_img(frame, root=root, widths=WIDTHS_THUMB, sizes=SIZES_THUMB)}</a></figure>'
            )
        blocks.append(
            f'''<section class="gallery" id="{_attr(gallery["slug"])}" data-title="{_attr(gallery["title"])}" aria-label="{_attr(gallery["title"])}">
                <h3 class="gallery-title">{escape(str(gallery["title"]))} <span>{_count(len(gallery["frames"]), "frame")}</span></h3>
                <div class="gallery-grid">{"".join(figures)}</div>
                <p class="gallery-back"><a href="#work">Back to the work</a></p>
            </section>'''
        )
    body = "\n            ".join(blocks)
    return f'''<div class="galleries" id="galleries">
        <div class="wrap">
            {body}
        </div>
    </div>'''


def _render_about(root: Path) -> str:
    portrait = ""
    if (Path(root) / ABOUT_PORTRAIT["src"]).is_file():
        portrait = (
            f'<figure class="about-portrait rv">{_site_img(ABOUT_PORTRAIT, root=root, sizes=SIZES_ABOUT)}</figure>'
        )
    head = _section_head("About", "Los Angeles", "about", view_heading=True)
    return f'''<section class="view view--about sec" id="about" data-view="about" aria-labelledby="about-title">
        <div class="wrap">
            {head}
            <div class="about-grid">
                {portrait}
                <div class="about-copy rv">
                    <p class="about-lede">I&rsquo;m Joshua, a photographer in Los Angeles.</p>
                    <p>I shoot portraits, fashion, live events and travel, on 35mm film and digital. I also host podcasts.</p>
                    <p class="about-more"><a href="../">More at joshuamgerman.com{_tail_arrow()}</a></p>
                </div>
            </div>
        </div>
    </section>'''


def _render_services(by_id: dict[str, dict[str, object]], root: Path) -> str:
    rows = "".join(
        f'<li class="svc-row"><span class="svc-name">{escape(name)}</span><span class="svc-desc">{escape(text)}</span></li>'
        for name, _, text in SERVICES
    )
    photo = by_id.get(SERVICES_PHOTO)
    figure = (
        f'<figure class="svc-photo rv">{_site_img(photo, root=root, alt="", position=SERVICES_PHOTO_POSITION, sizes=SIZES_ABOUT)}</figure>'
        if photo
        else ""
    )
    head = _section_head("Services", "Rates quoted per project", "services", view_heading=True)
    return f'''<section class="view view--services sec" id="services" data-view="services" aria-labelledby="services-title">
        <div class="wrap">
            {head}
            <div class="svc-grid">
                {figure}
                <div class="svc rv">
                    <ul class="svc-list">{rows}</ul>
                    <p class="svc-also">{escape(ALSO_BOOKING)}</p>
                    <a class="btn btn-safelight" {_external(STUDIO_PHOTO_URL)}>{STUDIO_BOOK_TEXT} {_ext_arrow()}</a>
                    <p class="svc-how">Booking event coverage? <a {_external(STUDIO_EVENTS_URL)}>Use the events form{_tail_ext()}</a></p>
                </div>
            </div>
        </div>
    </section>'''


def _render_book() -> str:
    """#book: other pages and old links land here. Paid shoots are booked
    through the Studio's form; this view says so and links there, and keeps
    a personal line for anything that is not a booking."""
    head = _section_head("Book a <em>shoot</em>", "Through The Curious &amp; Creative Studio", "book", view_heading=True)
    email = escape(INQUIRY_EMAIL)
    options = (
        ("Portraits, fashion &amp; general shoots", STUDIO_PHOTO_URL, STUDIO_BOOK_TEXT),
        ("Event coverage", STUDIO_EVENTS_URL, "Book event coverage through the Studio"),
    )
    rows = "".join(
        f'<li class="book-route"><span class="book-route__name">{name}</span>'
        f'<a class="btn btn-safelight" {_external(url)}>{label} {_ext_arrow()}</a></li>'
        for name, url, label in options
    )
    return f'''<section class="view view--book sec sec--book" id="book" data-view="book" aria-labelledby="book-title">
        <div class="wrap">
            {head}
            <div class="book-grid">
                <div class="book-aside rv">
                    <p class="book-lede">Paid shoots are booked through my company.</p>
                    <p>Client photography runs through The Curious &amp; Creative Company. Pick the form that fits and it goes straight to the Studio.</p>
                    <p class="book-price">Rates quoted per project.</p>
                </div>
                <div class="book-main rv">
                    <ul class="book-routes">{rows}</ul>
                    <div class="direct">
                        <p class="direct-label">Not a booking? Just say hi.</p>
                        <p class="direct-row"><a class="direct-email" href="mailto:{email}">{email}</a>
                            <button type="button" class="copy-btn" data-copy="{email}">Copy</button></p>
                        <p class="direct-row"><a {_external(INSTAGRAM_URL)}>Instagram {escape(INSTAGRAM_HANDLE)}</a></p>
                    </div>
                </div>
            </div>
        </div>
    </section>'''


def render_photo_site(
    photos: list[dict[str, object]],
    *,
    root: Path | None = None,
    sets: list[dict[str, object]] | None = None,
    shoots: list[dict[str, str]] | tuple[dict[str, str], ...] = (),
    coverage: list[dict[str, object]] | tuple[dict[str, object], ...] = (),
) -> str:
    """Render everything between the PHOTO-SITE markers of photography/index.html."""
    root = Path(root or REPO_ROOT)
    _requested_variants.clear()
    if sets is None:
        sets = load_photo_sets(root / SETS_FILE)
    photo_sets = build_photo_sets(photos, sets)
    projects = group_photo_site(photos)

    galleries = [{"slug": item["id"], "title": item["title"], "frames": item["frames"]} for item in photo_sets]
    galleries += [{"slug": project["slug"], "title": project["title"], "frames": project["frames"]} for project in projects]
    by_id = {str(photo["id"]): photo for photo in photos}
    coverage = list(coverage)
    # Coverage stills get their own viewer gallery, after the groups so a
    # still's first placement (hero links, mirror alt) stays its folder group.
    galleries += [
        {"slug": _stills_id(item), "title": item["title"], "frames": _coverage_stills(item, by_id)}
        for item in coverage
        if item["stills"]
    ]

    titles: dict[str, str] = {}
    placement: dict[str, tuple[str, int]] = {}
    for gallery in galleries:
        titles.setdefault(str(gallery["slug"]), str(gallery["title"]))
        for index, frame in enumerate(gallery["frames"]):
            placement.setdefault(str(frame["id"]), (str(gallery["slug"]), index))

    work_parts = [
        _render_hero(by_id, placement, titles, root, "#sets" if photo_sets else "#more"),
        _render_recent(photos, placement, root),
        _render_sets(photo_sets, root),
        _render_coverage(coverage, by_id, root),
        _render_more(projects, root, list(shoots), bool(photo_sets)),
        _render_galleries(galleries, root),
    ]
    work = "\n    ".join(part for part in work_parts if part)
    parts = [
        f'<div class="view view--work" id="work" data-view="work">\n    {work}\n    </div>',
        _render_about(root),
        _render_services(by_id, root),
        _render_book(),
    ]
    return "\n    ".join(parts)


def apply_photo_site(shell: str, rendered: str) -> str:
    """Swap the rendered block into the page shell between the markers."""
    if PHOTO_SITE_START not in shell or PHOTO_SITE_END not in shell:
        raise ValueError("photography/index.html is missing the PHOTO-SITE markers")
    before, remainder = shell.split(PHOTO_SITE_START, 1)
    _, after = remainder.split(PHOTO_SITE_END, 1)
    return f"{before}{PHOTO_SITE_START}\n    {rendered}\n    {PHOTO_SITE_END}{after}"
