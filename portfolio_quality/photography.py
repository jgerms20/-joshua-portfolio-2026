import json
from functools import lru_cache
from html import escape
from pathlib import Path, PurePosixPath
import re

from PIL import Image, ImageOps


CHAPTERS = ("people", "places", "gatherings")
LAYOUTS = {"hero", "wide", "inset", "pair-left", "pair-right", "archive"}
REQUIRED_FIELDS = {"id", "src", "alt", "chapter", "published", "sequence", "layout"}


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
        if entry.get("service") is not None and entry["service"] not in SERVICE_KEYS:
            raise ValueError(f"invalid photography service: {entry['service']}")
        if entry.get("project") is not None and not str(entry["project"]).strip():
            raise ValueError("photography project must be a non-empty name when set")

        seen_ids.add(identifier)
        seen_sources.add(source)
        if entry["published"]:
            published.append(entry)
    return published


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "photograph"


def import_photography_inbox(root: Path) -> list[dict[str, object]]:
    root = Path(root)
    inbox = root / "photos/inbox"
    manifest_path = root / "data/photography.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if payload.get("version") != 1 or not isinstance(entries, list):
        raise ValueError("photography manifest must contain version 1 and an entries list")

    supported = {".jpg", ".jpeg", ".png", ".webp"}
    existing_inbox_sources = {str(entry.get("inbox_source", "")) for entry in entries}
    existing_ids = {str(entry.get("id", "")) for entry in entries}
    imported: list[dict[str, object]] = []
    output_directory = root / "photos/library"

    for source in sorted(inbox.iterdir() if inbox.is_dir() else []):
        if not source.is_file() or source.suffix.lower() not in supported:
            continue
        inbox_source = source.relative_to(root).as_posix()
        if inbox_source in existing_inbox_sources:
            continue

        base = _slugify(source.stem)
        identifier = base
        counter = 2
        while identifier in existing_ids:
            identifier = f"{base}-{counter}"
            counter += 1

        output_directory.mkdir(parents=True, exist_ok=True)
        output = output_directory / f"{identifier}.webp"
        with Image.open(source) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.save(output, format="WEBP", quality=86, method=6)

        entry: dict[str, object] = {
            "id": identifier,
            "src": output.relative_to(root).as_posix(),
            "alt": "",
            "chapter": "unassigned",
            "published": False,
            "sequence": None,
            "layout": "archive",
            "inbox_source": inbox_source,
        }
        entries.append(entry)
        imported.append(entry)
        existing_ids.add(identifier)
        existing_inbox_sources.add(inbox_source)

    if imported:
        manifest_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
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


def render_darkroom(photos: list[dict[str, object]]) -> str:
    """Homepage photography chapter: straight to the pictures.

    One justified grid (every frame keeps its own ratio), curated sequence
    first, then the rest of the archive behind "See more".
    """
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
    return f'''<section id="photography" class="chapter chapter-dark">
        <div class="wrap">
            <div class="ch-head rv">
                <div class="ch-head-left">
                    <span class="ch-num">CH. 03</span>
                    <h2 class="ch-title"><span class="it">Photography</span></h2>
                </div>
                <div class="ch-meta">People · Places<br>Gatherings</div>
            </div>
            <div class="gallery-bar rv">
                <div class="photo-chapters" aria-label="Filter photographs">
                    <button class="photo-chapter active" data-filter="all" aria-pressed="true">All</button>
                    <button class="photo-chapter" data-filter="people" aria-pressed="false">People</button>
                    <button class="photo-chapter" data-filter="places" aria-pressed="false">Places</button>
                    <button class="photo-chapter" data-filter="gatherings" aria-pressed="false">Gatherings</button>
                </div>
                {_darkroom_cta()}
            </div>
            <div class="photo-grid rv" id="photoGallery">
                {tiles}
                <span class="gallery-filler" aria-hidden="true"></span>
            </div>
            {more_button}
        </div>
    </section>'''


def _darkroom_cta() -> str:
    """Two quiet links beside the filters: book, or open the full photo site."""
    return (
        '<div class="gallery-links">'
        '<a class="gallery-link gallery-link--book" href="photography/#book">Book a shoot&nbsp;&rarr;</a>'
        '<a class="gallery-link" href="photography/">Full photography site&nbsp;&rarr;</a>'
        "</div>"
    )


# =====================================================================
# The photography site: /photography/
#
# A standalone page inside the main site, built for a business-card QR
# code. photography/index.html is a hand-authored shell (head, styles,
# nav, lightbox, footer, script). Everything between the PHOTO-SITE
# markers is rendered here from data/photography.json, so a newly
# published photograph flows into the right set on the next render.
#
# Optional keys the renderer understands on a manifest entry:
#   project       a set slug or title; overrides the folder mapping
#   service       product | food | hospitality | real-estate
#   commissioned  true shows a "Commissioned" tag in the lightbox
#   recent        true adds the frame to a "Recent" strip under the hero
# Optional top-level manifest keys:
#   site.clients  list of client names for a "Select clients" line
#   site.shoots   list of {"project", "type", "year"} for a "Selected shoots"
#                 rundown under the Work sets. Real shoots only; empty hides it.
# =====================================================================

PHOTO_SITE_START = "<!-- PHOTO-SITE:START -->"
PHOTO_SITE_END = "<!-- PHOTO-SITE:END -->"
PHOTO_SITE_URL = "https://joshuamgerman.com/photography/"
# What the business-card QR code encodes. ?src=card preselects "Business card"
# under "How did you find me?" so card inquiries can be told apart.
PHOTO_SITE_CARD_URL = PHOTO_SITE_URL + "?src=card"
PHOTO_SITE_PREFIX = "../"
INQUIRY_EMAIL = "jgerms20@gmail.com"
INSTAGRAM_URL = "https://instagram.com/jgerms20"
INSTAGRAM_HANDLE = "@jgerms20"

REPO_ROOT = Path(__file__).resolve().parents[1]

# A commercial category stays a locked card until it has this many
# published frames tagged with its `service`. Then it becomes a set
# titled "<Category> 1.0".
UNLOCK_THRESHOLD = 6
FIRST_VOLUME = "1.0"

HERO_LEAD = "red-coat-studio"
HERO_LEAD_POSITION = "50% 18%"
HERO_STRIP = ("rio-santa-teresa-trams", "plates-in-progress", "concert-light")

# Joshua picks the About portrait; this one is him behind a camera.
ABOUT_PORTRAIT = {
    "src": "photos/self/IMG_1912.jpg",
    "alt": "Joshua McKenzie German raising a camera to his eye outdoors.",
}

SHOOT_TYPES = (
    ("portrait", "Portraits & headshots"),
    ("fashion", "Fashion & lookbooks"),
    ("event", "Events & live music"),
    ("product", "Product & e-commerce"),
    ("food", "Food & restaurants"),
    ("hospitality", "Hospitality & locations"),
    ("real-estate", "Real estate & spaces"),
    ("other", "Something else"),
)
SHOOT_VALUES = {value for value, _ in SHOOT_TYPES}

# Budget is the client's own free text. No preset bands: Joshua has not set
# any, and bands would read as a public rate card.
REFERRAL_SOURCES = ("Business card", "Instagram", "Referral", "Main site", "Other")

PHOTO_PROJECTS = (
    {
        "slug": "portraits",
        "title": "Portraits",
        "kind": "People",
        "match": ("photos/portraits/",),
        "cover": "father-and-child",
        "position": "38% 50%",
        "pitch": "Book a portrait session",
        "shoot": "portrait",
    },
    {
        "slug": "fashion",
        "title": "Fashion",
        "kind": "Style",
        "match": ("photos/fashion/",),
        "cover": "red-accent-studio",
        "position": "50% 40%",
        "pitch": "Book a lookbook shoot",
        "shoot": "fashion",
    },
    {
        "slug": "events",
        "title": "Events & Live",
        "kind": "Gatherings",
        "match": ("photos/events/",),
        "cover": "blue-lit-performer",
        "position": "50% 30%",
        "pitch": "Get your event covered",
        "shoot": "event",
    },
    {
        "slug": "rio-de-janeiro",
        "title": "Rio de Janeiro",
        "kind": "Travel · prints",
        "match": ("photos/shop/rio-",),
        "cover": "rio-brahma-corner",
        "position": "50% 60%",
        "pitch": "Order a Rio print",
        "href": "../shop.html",
    },
    {
        "slug": "landscapes",
        "title": "Landscapes",
        "kind": "Places",
        "match": ("photos/landscape/",),
        "cover": "misty-valley",
        "position": "50% 50%",
        "pitch": "Book an outdoor shoot",
        "shoot": "other",
    },
    {
        "slug": "travel",
        "title": "Travel",
        "kind": "Places",
        "match": ("photos/travel/",),
        "cover": "palms-at-dusk",
        "position": "72% 50%",
        "pitch": "Book a travel shoot",
        "shoot": "other",
    },
)
FALLBACK_PROJECT = {
    "slug": "more-work",
    "title": "More work",
    "kind": "Mixed",
    "match": (),
    "cover": None,
    "position": "50% 50%",
    "pitch": "Book a shoot",
    "shoot": "other",
}

COMMERCIAL_CATEGORIES = (
    {
        "service": "product",
        "slug": "product",
        "short": "Product",
        "title": "Product",
        "blurb": "Packshots, e-comm sets, product in use.",
        "shots": ("Hero", "Detail", "In use", "Loop"),
        "cta": "Ask about a product shoot",
        "nearby": (),
        "nearby_note": "",
    },
    {
        "service": "food",
        "slug": "food",
        "short": "Food",
        "title": "Food & Restaurants",
        "blurb": "Plated dishes, menus, kitchens, openings.",
        "shots": ("The plate", "Overhead", "The pass", "The room"),
        "cta": "Ask about a food shoot",
        "nearby": ("culinary-set", "plates-in-progress"),
        "nearby_note": "From the archive: event photos, not client work.",
    },
    {
        "service": "hospitality",
        "slug": "hospitality",
        "short": "Hospitality",
        "title": "Hospitality & Locations",
        "blurb": "Hotels, bars, venues, the room itself.",
        "shots": ("Arrival", "The room", "Details", "After dark"),
        "cta": "Ask about a location shoot",
        "nearby": ("rio-brahma-corner", "market-crowd"),
        "nearby_note": "From the archive: travel and event photos, not client work.",
    },
    {
        "service": "real-estate",
        "slug": "real-estate",
        "short": "Real estate",
        "title": "Real Estate & Spaces",
        "blurb": "Listings, interiors, architecture.",
        "shots": ("Exterior", "Main room", "Details", "Twilight"),
        "cta": "Ask about a space shoot",
        "nearby": (),
        "nearby_note": "",
    },
)
SERVICE_KEYS = {category["service"] for category in COMMERCIAL_CATEGORIES}
COMMERCIAL_FITS = (
    "A product launch that needs e-comm and social images",
    "A new menu, a pop-up or an opening night",
    "A bar, hotel or venue that just changed its look",
    "A listing or a space that deserves better than phone photos",
)

SERVICES_NOW = (
    ("portrait", "Portraits & headshots", "People, teams, personal portraits."),
    ("fashion", "Fashion & lookbooks", "Lookbooks, styling tests, campaigns."),
    ("event", "Events & live music", "Concerts, parties, launches, dinners."),
)
SERVICES_NEW = (
    ("product", "Product & e-commerce", "Packshots, e-comm sets, product in use."),
    ("food", "Food & restaurants", "Plates, menus, kitchens, openings."),
    ("hospitality", "Hospitality & locations", "Hotels, bars, venues, the room itself."),
    ("real-estate", "Real estate & spaces", "Listings, interiors, architecture."),
)
PROCESS_STEPS = (
    ("Inquire", "Send the form below. Tell me what you're making and where the photos will run."),
    ("Plan", "We talk through the brief, the shot list and the location. I send a quote."),
    ("Shoot", "We make the pictures. I shoot to the plan and leave room for the good accidents."),
    ("Deliver", "You get edited, full-resolution files, cropped for the places they'll live."),
)

# Section ids a project slug must not take over.
RESERVED_IDS = {
    "top", "hero", "jump", "recent", "work", "sets", "commercial", "services",
    "process", "prints", "about", "book", "inquiry", "lightbox", "main",
}


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
WIDTHS_COVER = (480, 960)
WIDTHS_THUMB = (480,)
WIDTHS_PRINT = (240,)
SIZES_HERO = "(min-width: 700px) min(40vw, 580px), calc(100vw - 32px)"
SIZES_COVER = "(min-width: 720px) min(30vw, 470px), calc(100vw - 32px)"
SIZES_STRIP = "(min-width: 700px) 18vw, 1px"
SIZES_ABOUT = "(min-width: 800px) 440px, calc(100vw - 32px)"
SIZES_THUMB = "(min-width: 720px) 200px, 45vw"
SIZES_PRINT = "92px"

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
    return f"set-{slug}" if slug in RESERVED_IDS else slug


def group_photo_site(photos: list[dict[str, object]]) -> dict[str, object]:
    """Sort published photographs into the sets the photography site shows.

    Returns a dict with:
      projects  ordered list of sets for the Work grid (unlocked commercial first)
      locked    commercial categories still in development, with any first frames
      nearby    archive frames shown next to a locked category
    """
    by_id = {str(photo["id"]): photo for photo in photos}
    known = {project["slug"]: project for project in PHOTO_PROJECTS}
    titles = {_slugify(project["title"]): project["slug"] for project in PHOTO_PROJECTS}
    buckets: dict[str, list[dict[str, object]]] = {}
    custom: dict[str, dict[str, object]] = {}
    service_frames: dict[str, list[dict[str, object]]] = {key: [] for key in SERVICE_KEYS}

    for photo in photos:
        explicit = str(photo.get("project") or "").strip()
        service = photo.get("service")
        if explicit:
            slug = _slugify(explicit)
            slug = titles.get(slug, slug)
            if slug not in known and slug not in custom:
                custom[slug] = {
                    "key": slug,
                    "slug": _safe_slug(slug),
                    "title": explicit,
                    "kind": "Series",
                    "match": (),
                    "cover": None,
                    "position": "50% 50%",
                    "pitch": "Book a shoot like this",
                    "shoot": "other",
                }
            buckets.setdefault(slug, []).append(photo)
            continue
        if service in SERVICE_KEYS:
            service_frames[str(service)].append(photo)
            continue
        source = str(photo["src"])
        slug = next(
            (
                project["slug"]
                for project in PHOTO_PROJECTS
                if any(source.startswith(prefix) for prefix in project["match"])
            ),
            FALLBACK_PROJECT["slug"],
        )
        buckets.setdefault(slug, []).append(photo)

    projects: list[dict[str, object]] = []
    locked: list[dict[str, object]] = []
    for category in COMMERCIAL_CATEGORIES:
        frames = service_frames[category["service"]]
        if len(frames) >= UNLOCK_THRESHOLD:
            projects.append(
                {
                    "slug": category["slug"],
                    "title": f'{category["title"]} {FIRST_VOLUME}',
                    "kind": category["blurb"].rstrip("."),
                    "cover": None,
                    "position": "50% 50%",
                    "pitch": category["cta"],
                    "shoot": category["service"],
                    "frames": _order_frames(frames, None),
                    "commercial": True,
                }
            )
        else:
            locked.append({**category, "frames": _order_frames(frames, None)})

    for definition in (*PHOTO_PROJECTS, *custom.values(), FALLBACK_PROJECT):
        frames = buckets.get(str(definition.get("key", definition["slug"])), [])
        if not frames:
            continue
        projects.append({**definition, "frames": _order_frames(frames, definition["cover"])})

    nearby = [
        {
            "slug": f'{category["slug"]}-archive',
            "title": f'{category["short"]} · from the archive',
            "note": category["nearby_note"],
            "frames": [by_id[identifier] for identifier in category["nearby"] if identifier in by_id],
            "category": category["slug"],
        }
        for category in locked
        if any(identifier in by_id for identifier in category["nearby"])
    ]
    return {"projects": projects, "locked": locked, "nearby": nearby}


def load_photo_site_settings(path: Path) -> dict[str, object]:
    """Optional page settings stored beside the entries in the manifest."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    site = payload.get("site") or {}
    if not isinstance(site, dict):
        raise ValueError("photography manifest 'site' must be an object")
    clients = site.get("clients") or []
    if not isinstance(clients, list) or not all(isinstance(name, str) for name in clients):
        raise ValueError("photography manifest 'site.clients' must be a list of names")
    shoots = site.get("shoots") or []
    if not isinstance(shoots, list):
        raise ValueError("photography manifest 'site.shoots' must be a list")
    cleaned = []
    for shoot in shoots:
        if not isinstance(shoot, dict) or not str(shoot.get("project", "")).strip():
            raise ValueError("each photography 'site.shoots' entry needs a project name")
        cleaned.append({key: str(shoot.get(key) or "").strip() for key in ("project", "type", "year")})
    return {"clients": [name.strip() for name in clients if name.strip()], "shoots": cleaned}


def _arrow() -> str:
    return '<span class="arr" aria-hidden="true">&rarr;</span>'


def _tail_arrow() -> str:
    """Arrow glued to the last word so it never wraps onto a line of its own."""
    return "&nbsp;" + _arrow()


def _section_head(number: str, title: str, meta: str, section_id: str) -> str:
    return (
        f'<header class="sec-head rv">'
        f'<span class="sec-num">{number}</span>'
        f'<h2 class="sec-title" id="{section_id}-title">{title}</h2>'
        f'<p class="sec-meta">{meta}</p>'
        f"</header>"
    )


def _render_hero(
    by_id: dict[str, dict[str, object]],
    placement: dict[str, tuple[str, int]],
    titles: dict[str, str],
    root: Path,
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
            f'aria-label="Open the {_attr(titles.get(slug, "photography"))} set">{image}</a>'
            f'<figcaption><span class="fig-no">Fig. 01</span><span>Studio portrait</span></figcaption>'
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
            f'aria-label="Open the {_attr(titles.get(slug, "photography"))} set at this frame">'
            f'{_site_img(photo, root=root, loading="lazy", low_priority=True, sizes=SIZES_STRIP)}</a>'
            f'<span class="strip-cap"><span class="fig-no">{number:02d}</span>{escape(titles.get(slug, "photography"))}</span>'
            f"</li>"
        )
    strip = f'<ol class="hero-strip" aria-label="More frames">{"".join(strip_items)}</ol>' if strip_items else ""

    return f'''<section class="hero" id="hero" aria-labelledby="hero-title">
        <div class="hero-grid">
            <div class="hero-copy">
                <p class="kicker">Photography <span aria-hidden="true">&middot;</span> Los Angeles</p>
                <h1 class="hero-title" id="hero-title">Joshua McKenzie <em>German</em></h1>
                <p class="hero-line">Portraits, fashion and live events in Los Angeles. Now booking product, food, hospitality and real-estate shoots too.</p>
                <div class="hero-actions">
                    <a class="btn btn-safelight" href="#book">Book a shoot {_arrow()}</a>
                    <a class="btn btn-line" href="#work">See the work</a>
                </div>
                {strip}
            </div>
            {lead_markup}
        </div>
    </section>'''


def _render_jump(has_locked: bool) -> str:
    links = [("#work", "Work")]
    if has_locked:
        links.append(("#commercial", "Commercial"))
    links += [("#services", "Services"), ("#prints", "Prints"), ("#about", "About"), ("#book", "Book")]
    items = "".join(f'<li><a href="{href}">{label}</a></li>' for href, label in links)
    return f'<nav class="jump" id="jump" aria-label="Page sections"><ul>{items}<li><a href="../">Main site</a></li></ul></nav>'


def _render_recent(photos: list[dict[str, object]], placement: dict[str, tuple[str, int]], root: Path) -> str:
    recent = [photo for photo in photos if photo.get("recent") is True][:8]
    if not recent:
        return ""
    items = []
    for photo in recent:
        slug, index = placement.get(str(photo["id"]), ("", 0))
        items.append(
            f'<li><a href="#{_attr(slug)}" data-open="{_attr(slug)}" data-index="{index}" '
            f'aria-label="Open {_attr(photo["alt"])}">{_site_img(photo, root=root, widths=WIDTHS_THUMB, sizes=SIZES_THUMB)}</a></li>'
        )
    return f'''<section class="recent" id="recent" aria-labelledby="recent-title">
        <div class="wrap">
            <h2 class="recent-title" id="recent-title">Recent</h2>
            <ul class="recent-strip">{"".join(items)}</ul>
        </div>
    </section>'''


def _pitch_link(project: dict[str, object]) -> str:
    label = escape(str(project["pitch"]))
    if project.get("href"):
        return f'<a class="card-pitch" href="{_attr(project["href"])}">{label}{_tail_arrow()}</a>'
    return f'<a class="card-pitch" href="#book" data-shoot="{_attr(project.get("shoot", "other"))}">{label}{_tail_arrow()}</a>'


def _render_shoots(shoots: list[dict[str, str]]) -> str:
    if not shoots:
        return ""
    rows = "".join(
        f'<li><span class="shoot-name">{escape(shoot["project"])}</span>'
        f'<span class="shoot-type">{escape(shoot["type"])}</span>'
        f'<span class="shoot-year">{escape(shoot["year"])}</span></li>'
        for shoot in shoots
    )
    return f'''<div class="shoots rv">
                <h3 class="shoots-title">Selected shoots</h3>
                <ol class="shoots-list">{rows}</ol>
            </div>'''


def _render_work(projects: list[dict[str, object]], root: Path, shoots: list[dict[str, str]] = ()) -> str:
    cards = []
    total = 0
    for number, project in enumerate(projects, start=1):
        frames = project["frames"]
        total += len(frames)
        cover = frames[0]
        slug = _attr(project["slug"])
        title = escape(str(project["title"]))
        cover_image = _site_img(
            cover, root=root, position=str(project.get("position") or ""),
            alt="",
        )
        badge = '<span class="card-badge">New</span>' if project.get("commercial") else ""
        cards.append(
            f'''<article class="card rv" data-set="{slug}">
                    <div class="card-cover">{cover_image}{badge}<span class="card-open" aria-hidden="true">View set {_arrow()}</span></div>
                    <div class="card-body">
                        <p class="card-meta"><span class="card-num">{number:02d}</span> {len(frames):02d} frames &middot; {escape(str(project["kind"]))}</p>
                        <h3 class="card-title"><a class="card-link" href="#{slug}" data-open="{slug}" data-index="0">{title}<span class="visually-hidden">, {len(frames)} frames</span></a></h3>
                        {_pitch_link(project)}
                    </div>
                </article>'''
        )
    grid = "\n                ".join(cards)
    head = _section_head("01", "Selected <em>work</em>", f"{total:02d} frames &middot; {len(projects):02d} sets", "work")
    return f'''<section class="sec" id="work" aria-labelledby="work-title">
        <div class="wrap">
            {head}
            <p class="sec-intro rv">People, places and nights out, grouped into sets. Open one to flip through it.</p>
            <div class="cards cards--work">
                {grid}
            </div>
            {_render_shoots(list(shoots))}
        </div>
    </section>'''


LOCK_ICON = (
    '<svg class="lock" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false">'
    '<rect x="4.5" y="10.5" width="15" height="10" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.6"/>'
    '<path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" stroke-width="1.6"/>'
    '<circle cx="12" cy="15.5" r="1.4" fill="currentColor"/></svg>'
)


def _render_commercial(
    locked: list[dict[str, object]], nearby: list[dict[str, object]], start_number: int
) -> str:
    """The commercial books that are not open yet.

    One strong moment (the Now booking panel) beside compact locked tiles:
    no empty image frames, and "in development" said once, in the header.
    """
    if not locked:
        return ""
    nearby_by_category = {item["category"]: item for item in nearby}
    tiles = []
    for offset, category in enumerate(locked):
        shot_names = " / ".join(category["shots"])
        links = [
            f'<a class="card-pitch" href="#book" data-shoot="{_attr(category["service"])}">'
            f'{escape(str(category["cta"]))}{_tail_arrow()}</a>'
        ]
        frames = category["frames"]
        if frames:
            links.append(
                f'<a class="card-aside" href="#{_attr(category["slug"])}" data-open="{_attr(category["slug"])}" data-index="0">'
                f'First frames in: {len(frames):02d}{_tail_arrow()}</a>'
            )
        near = nearby_by_category.get(category["slug"])
        if near:
            links.append(
                f'<a class="card-aside" href="#{_attr(near["slug"])}" data-open="{_attr(near["slug"])}" data-index="0">'
                f'From the archive<span class="visually-hidden"> ({len(near["frames"])} frames, not client work)</span>{_tail_arrow()}</a>'
            )
        tiles.append(
            f'''<article class="lock-tile card--locked rv" data-service="{_attr(category["service"])}">
                        <p class="lock-meta"><span class="card-num">{start_number + offset:02d}</span>{LOCK_ICON}<span>Locked</span></p>
                        <h3 class="lock-title">{escape(str(category["title"]))}</h3>
                        <p class="lock-blurb">{escape(str(category["blurb"]))}</p>
                        <p class="lock-shots"><span class="visually-hidden">Shot list: </span>{escape(shot_names)}</p>
                        <div class="lock-links">{"".join(links)}</div>
                    </article>'''
        )
    grid = "\n                    ".join(tiles)
    fits = "".join(f"<li>{escape(line)}</li>" for line in COMMERCIAL_FITS)
    head = _section_head("02", "Commercial", f"{len(locked):02d} books in development", "commercial")
    return f'''<section class="sec sec--commercial" id="commercial" aria-labelledby="commercial-title">
        <div class="wrap">
            {head}
            <div class="commercial">
                <div class="commercial-intro rv">
                    <p class="commercial-kicker"><span class="dot" aria-hidden="true"></span>Now booking</p>
                    <p class="commercial-lede">Product, food, hospitality and real estate are the newest books. Have a launch, a menu or a space that needs pictures? Let&rsquo;s plan it.</p>
                    <div class="commercial-fits">
                        <p class="commercial-fits__label">Good fits</p>
                        <ul>{fits}</ul>
                    </div>
                    <p class="commercial-note">No stock photos, no borrowed frames. Each book opens once it has real shoots in it.</p>
                    <a class="btn btn-safelight" href="#book">Plan your shoot {_arrow()}</a>
                </div>
                <div class="lock-grid">
                    {grid}
                </div>
            </div>
        </div>
    </section>'''


def _render_services(number: str) -> str:
    def rows(items: tuple[tuple[str, str, str], ...], new: bool) -> str:
        tag = '<span class="svc-tag">New</span>' if new else ""
        return "".join(
            f'<li><a class="svc-row" href="#book" data-shoot="{_attr(value)}">'
            f'<span class="svc-name">{escape(name)}{tag}</span>'
            f'<span class="svc-desc">{escape(description)}</span>'
            f'<span class="svc-go">Book {_arrow()}</span></a></li>'
            for value, name, description in items
        )

    steps = "".join(
        f'<li class="step"><span class="step-no">{index:02d}</span><h4>{escape(name)}</h4><p>{escape(text)}</p></li>'
        for index, (name, text) in enumerate(PROCESS_STEPS, start=1)
    )
    head = _section_head(number, "Services", "Now booking", "services")
    return f'''<section class="sec" id="services" aria-labelledby="services-title">
        <div class="wrap">
            {head}
            <div class="svc-grid">
                <div class="svc-lede rv">
                    <p class="svc-strategy">I came up in brand strategy, so I can help write the brief, not just shoot it.</p>
                    <p class="svc-price">Rates quoted per project.</p>
                    <a class="btn btn-safelight" href="#book">Book a shoot {_arrow()}</a>
                </div>
                <div class="svc-lists">
                    <div class="svc-group rv">
                        <h3 class="svc-label">Booking now</h3>
                        <ul class="svc-list">{rows(SERVICES_NOW, False)}</ul>
                    </div>
                    <div class="svc-group rv">
                        <h3 class="svc-label"><span class="dot" aria-hidden="true"></span>New</h3>
                        <ul class="svc-list">{rows(SERVICES_NEW, False)}</ul>
                    </div>
                    <div class="svc-group svc-extend rv">
                        <h3 class="svc-label">Add-on &middot; Social cut-downs</h3>
                        <p>One shoot, planned for more places: social crops, short loops and extra sizes, built into the shot list from day one.</p>
                    </div>
                </div>
            </div>
            <div class="process rv" id="process">
                <h3 class="process-title">How it works</h3>
                <ol class="steps">{steps}</ol>
            </div>
        </div>
    </section>'''


def _render_prints(rio: list[dict[str, object]], root: Path) -> str:
    if not rio:
        return ""
    thumbs = "".join(
        f'<li><a href="../shop.html" tabindex="-1" aria-hidden="true">{_site_img(photo, root=root, alt="", widths=WIDTHS_PRINT, sizes=SIZES_PRINT)}</a></li>'
        for photo in rio[:4]
    )
    return f'''<section class="prints" id="prints" aria-label="Prints">
        <div class="wrap prints-row">
            <ul class="prints-thumbs">{thumbs}</ul>
            <p class="prints-line"><a href="../shop.html">The Rio set is available as prints{_tail_arrow()}</a></p>
        </div>
    </section>'''


def _render_about(number: str, clients: list[str], root: Path) -> str:
    portrait = ""
    if (Path(root) / ABOUT_PORTRAIT["src"]).is_file():
        portrait = (
            f'<figure class="about-portrait rv">{_site_img(ABOUT_PORTRAIT, root=root, sizes=SIZES_ABOUT)}'
            f'<figcaption><span class="fig-no">Self</span><span>Joshua McKenzie German</span></figcaption></figure>'
        )
    client_line = (
        f'<p class="about-clients"><span>Select clients</span> {escape(" · ".join(clients))}</p>' if clients else ""
    )
    head = _section_head(number, "About", "Los Angeles, CA", "about")
    return f'''<section class="sec" id="about" aria-labelledby="about-title">
        <div class="wrap">
            {head}
            <div class="about-grid">
                {portrait}
                <div class="about-copy rv">
                    <p class="about-lede">I&rsquo;m a Los Angeles photographer with a strategist&rsquo;s habit.</p>
                    <p>I started as a reporter, then moved into brand strategy at Goodby Silverstein &amp; Partners, Wieden+Kennedy and TBWA\\Chiat\\Day. That work taught me to ask where a picture will live before I take it: the feed, the site, the menu, the listing. So I plan the shoot around the use. Then I wait for the moment someone stops posing.</p>
                    <p>Off the clock I host and produce podcasts and build tools with AI.</p>
                    {client_line}
                    <dl class="about-facts">
                        <div><dt>Based</dt><dd>Los Angeles, CA</dd></div>
                        <div><dt>Shoots</dt><dd>People, places, live events</dd></div>
                        <div><dt>Adding</dt><dd>Product, food, hospitality, real estate</dd></div>
                    </dl>
                    <p class="about-more"><span>More on the main site</span>
                        <a href="../index.html#work">Brand strategy work</a>
                        <a href="../index.html#podcasts">Podcasts</a>
                        <a href="../index.html#ai">AI builds</a>
                    </p>
                </div>
            </div>
        </div>
    </section>'''


def _render_book(number: str) -> str:
    shoot_options = '<option value="">Choose one</option>' + "".join(
        f'<option value="{_attr(value)}">{escape(label)}</option>' for value, label in SHOOT_TYPES
    )
    source_options = '<option value="">Choose one (optional)</option>' + "".join(
        f"<option>{escape(label)}</option>" for label in REFERRAL_SOURCES
    )
    head = _section_head(number, "Book a <em>shoot</em>", "Inquiries by email", "book")
    email = escape(INQUIRY_EMAIL)
    return f'''<section class="sec sec--book" id="book" aria-labelledby="book-title">
        <div class="wrap">
            {head}
            <div class="book-grid">
                <div class="book-aside rv">
                    <p class="book-lede">Tell me what you&rsquo;re making.</p>
                    <p>Fill this in and your email app opens with it written up. Nothing sends until you hit send.</p>
                    <p class="book-price">Rates quoted per project.</p>
                    <div class="direct">
                        <p class="direct-label">Rather write it yourself?</p>
                        <p class="direct-row"><a class="direct-email" href="mailto:{email}">{email}</a>
                            <button type="button" class="copy-btn" data-copy="{email}">Copy</button></p>
                        <p class="direct-row"><a href="{_attr(INSTAGRAM_URL)}" rel="noopener" target="_blank">Instagram {escape(INSTAGRAM_HANDLE)}</a></p>
                    </div>
                </div>
                <form class="inquiry rv" id="inquiry" action="mailto:{email}" method="post" enctype="text/plain" data-email="{email}" novalidate>
                    <div class="field">
                        <label for="f-name">Name <span class="req" aria-hidden="true">*</span></label>
                        <input id="f-name" name="name" type="text" autocomplete="name" required aria-describedby="f-name-err">
                        <p class="field-err" id="f-name-err"></p>
                    </div>
                    <div class="field">
                        <label for="f-email">Email <span class="req" aria-hidden="true">*</span></label>
                        <input id="f-email" name="email" type="email" autocomplete="email" inputmode="email" required aria-describedby="f-email-err">
                        <p class="field-err" id="f-email-err"></p>
                    </div>
                    <div class="field">
                        <label for="f-shoot">What do you need? <span class="req" aria-hidden="true">*</span></label>
                        <select id="f-shoot" name="shoot" required aria-describedby="f-shoot-err">{shoot_options}</select>
                        <p class="field-err" id="f-shoot-err"></p>
                    </div>
                    <div class="field">
                        <label for="f-company">Company or brand</label>
                        <input id="f-company" name="company" type="text" autocomplete="organization">
                    </div>
                    <div class="field">
                        <label for="f-date">Date</label>
                        <input id="f-date" name="date" type="text" placeholder="A date, a month, or flexible">
                    </div>
                    <div class="field">
                        <label for="f-location">Location</label>
                        <input id="f-location" name="location" type="text" placeholder="City, venue or address">
                    </div>
                    <div class="field">
                        <label for="f-budget">Your budget</label>
                        <input id="f-budget" name="budget" type="text" placeholder="A range or a number (optional)">
                    </div>
                    <div class="field">
                        <label for="f-source">How did you find me?</label>
                        <select id="f-source" name="source">{source_options}</select>
                    </div>
                    <div class="field field--wide">
                        <label for="f-details">Details <span class="req" aria-hidden="true">*</span></label>
                        <p class="field-hint" id="f-details-hint">What are we making, and where will the photos live?</p>
                        <textarea id="f-details" name="details" rows="5" required aria-describedby="f-details-hint f-details-err"></textarea>
                        <p class="field-err" id="f-details-err"></p>
                    </div>
                    <div class="form-foot field--wide">
                        <button class="btn btn-safelight" type="submit">Open my email draft {_arrow()}</button>
                        <p class="form-note"><span class="req" aria-hidden="true">*</span> Required</p>
                    </div>
                    <p class="form-status field--wide" id="form-status" role="status" aria-live="polite"></p>
                    <p class="form-fallback field--wide" id="form-fallback" hidden>Email app didn&rsquo;t open? <a id="mailto-link" href="mailto:{email}">Open the draft here</a> or copy the address above.</p>
                </form>
            </div>
        </div>
    </section>'''


def _render_sets(groups: list[dict[str, object]], root: Path) -> str:
    """Each set as a plain thumbnail block. Scripted pages hide these and read
    them to fill the lightbox; without JS the card links jump straight here."""
    blocks = []
    for group in groups:
        figures = []
        for frame in group["frames"]:
            width, height = _image_size(str(root), str(frame["src"]))
            tags = []
            if frame.get("commissioned") is True:
                tags.append("Commissioned")
            full = PHOTO_SITE_PREFIX + str(frame["src"])
            figures.append(
                f'<figure class="set-frame" data-full="{_attr(full)}" data-w="{width}" data-h="{height}" '
                f'data-alt="{_attr(frame["alt"])}" data-tag="{_attr(" · ".join(tags))}">'
                f'<a href="{_attr(full)}">{_site_img(frame, root=root, widths=WIDTHS_THUMB, sizes=SIZES_THUMB)}</a></figure>'
            )
        note = str(group.get("note") or "")
        note_markup = f'<p class="set-note">{escape(note)}</p>' if note else ""
        blocks.append(
            f'''<section class="set" id="{_attr(group["slug"])}" data-title="{_attr(group["title"])}" data-note="{_attr(note)}" aria-label="{_attr(group["title"])}">
                <h3 class="set-title">{escape(str(group["title"]))} <span>{len(group["frames"]):02d} frames</span></h3>
                {note_markup}
                <div class="set-grid">{"".join(figures)}</div>
                <p class="set-back"><a href="#work">Back to all sets</a></p>
            </section>'''
        )
    body = "\n            ".join(blocks)
    return f'''<div class="sets" id="sets">
        <div class="wrap">
            {body}
        </div>
    </div>'''


def render_photo_site(
    photos: list[dict[str, object]],
    *,
    root: Path | None = None,
    clients: list[str] | tuple[str, ...] = (),
    shoots: list[dict[str, str]] | tuple[dict[str, str], ...] = (),
) -> str:
    """Render everything between the PHOTO-SITE markers of photography/index.html."""
    root = Path(root or REPO_ROOT)
    _requested_variants.clear()
    grouped = group_photo_site(photos)
    projects = grouped["projects"]
    locked = grouped["locked"]
    nearby = grouped["nearby"]

    galleries: list[dict[str, object]] = [
        {"slug": project["slug"], "title": project["title"], "note": "", "frames": project["frames"]}
        for project in projects
    ]
    galleries += [
        {
            "slug": category["slug"],
            "title": f'{category["title"]}: first frames',
            "note": "Early frames for a book still in development.",
            "frames": category["frames"],
        }
        for category in locked
        if category["frames"]
    ]
    galleries += nearby

    titles: dict[str, str] = {}
    placement: dict[str, tuple[str, int]] = {}
    for gallery in galleries:
        titles.setdefault(str(gallery["slug"]), str(gallery["title"]))
        for index, frame in enumerate(gallery["frames"]):
            placement.setdefault(str(frame["id"]), (str(gallery["slug"]), index))

    by_id = {str(photo["id"]): photo for photo in photos}
    rio = next((project["frames"] for project in projects if project["slug"] == "rio-de-janeiro"), [])
    numbers = iter(f"{value:02d}" for value in range(3 if locked else 2, 10))
    parts = [
        _render_hero(by_id, placement, titles, root),
        _render_jump(bool(locked)),
        _render_recent(photos, placement, root),
        _render_work(projects, root, list(shoots)),
        _render_commercial(locked, nearby, start_number=len(projects) + 1),
        _render_services(next(numbers)),
        _render_prints(rio, root),
        _render_about(next(numbers), list(clients), root),
        _render_book(next(numbers)),
        _render_sets(galleries, root),
    ]
    return "\n    ".join(part for part in parts if part)


def apply_photo_site(shell: str, rendered: str) -> str:
    """Swap the rendered block into the page shell between the markers."""
    if PHOTO_SITE_START not in shell or PHOTO_SITE_END not in shell:
        raise ValueError("photography/index.html is missing the PHOTO-SITE markers")
    before, remainder = shell.split(PHOTO_SITE_START, 1)
    _, after = remainder.split(PHOTO_SITE_END, 1)
    return f"{before}{PHOTO_SITE_START}\n    {rendered}\n    {PHOTO_SITE_END}{after}"
