import json
from html import escape
from pathlib import Path, PurePosixPath
import re

from PIL import Image, ImageOps


CHAPTERS = ("people", "places", "gatherings")
# How many sequence frames show before "Continue the sequence". The rest of
# the edit and the full archive sit behind buttons so the chapter stays short.
SEQUENCE_PREVIEW = 9

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


def _photo_figure(photo: dict[str, object], *, sequence: bool) -> str:
    number = int(photo["sequence"]) if sequence else None
    classes = ["photo-item"]
    if sequence:
        classes.extend(["sequence-frame", f"sequence-frame--{photo['layout']}"])
    else:
        classes.append("archive-frame")
    label = f"Open photograph {number:02d}: {photo['alt']}" if number else f"Open photograph: {photo['alt']}"
    loading = "eager" if number == 1 else "lazy"
    caption = (
        f'<figcaption><span>{number:02d}</span><span>{escape(str(photo["chapter"]))}</span></figcaption>'
        if sequence
        else ""
    )
    return (
        f'<figure class="{" ".join(classes)}" data-cat="{escape(str(photo["chapter"]))}" '
        f'data-chapter="{escape(str(photo["chapter"]))}" '
        f'tabindex="0" role="button" aria-label="{escape(label)}">'
        f'<img loading="{loading}" src="{escape(str(photo["src"]))}" alt="{escape(str(photo["alt"]))}">'
        f"{caption}</figure>"
    )


def render_darkroom(photos: list[dict[str, object]]) -> str:
    selected = sorted(
        (photo for photo in photos if photo.get("sequence") is not None),
        key=lambda photo: int(photo["sequence"]),
    )
    sequence_parts: list[str] = []
    more_parts: list[str] = []
    index = 0
    while index < len(selected):
        photo = selected[index]
        if (
            photo["layout"] == "pair-left"
            and index + 1 < len(selected)
            and selected[index + 1]["layout"] == "pair-right"
        ):
            target = sequence_parts if index < SEQUENCE_PREVIEW else more_parts
            target.append(
                '<div class="sequence-pair">\n                    '
                + _photo_figure(photo, sequence=True)
                + "\n                    "
                + _photo_figure(selected[index + 1], sequence=True)
                + "\n                </div>"
            )
            index += 2
            continue
        (sequence_parts if index < SEQUENCE_PREVIEW else more_parts).append(
            _photo_figure(photo, sequence=True)
        )
        index += 1

    sequence_markup = "\n                ".join(sequence_parts)
    more_count = len(selected) - min(len(selected), SEQUENCE_PREVIEW)
    if more_parts:
        sequence_markup += (
            '\n                <div class="sequence-more" id="sequenceMore">\n                '
            + "\n                ".join(more_parts)
            + "\n                </div>"
        )
    archive = "\n                ".join(
        _photo_figure(photo, sequence=False) for photo in photos
    )
    more_button = (
        f'''<button type="button" class="darkroom-more" data-reveal="sequenceMore" aria-controls="sequenceMore" aria-expanded="false" data-open-label="Show the short edit" data-closed-label="Continue the sequence"><span class="darkroom-more__label">Continue the sequence</span><span class="darkroom-more__count">{more_count} more frames</span></button>'''
        if more_parts
        else ""
    )
    count = len(photos)
    return f'''<section id="photography" class="chapter chapter-dark">
        <div class="wrap">
            <div class="ch-head rv">
                <div class="ch-head-left">
                    <span class="ch-num">CH. 03</span>
                    <h2 class="ch-title">The <span class="it">Darkroom</span></h2>
                </div>
                <div class="ch-meta">Selected Sequence<br>{len(selected):02d} Frames</div>
            </div>
            <p class="ch-intro rv" style="color: var(--paper-on-dark-soft);">I photograph the instant a person drops the pose, a crowd becomes one body, or a landscape makes time feel larger. This is an edit about presence—not a catalogue of everything I have shot.</p>
            {_darkroom_cta()}

            <div class="darkroom-note rv">
                <span class="darkroom-note__label">The edit</span>
                <p>People lead. Places let the story breathe. Gatherings return the noise. The sequence moves between all three the way memory does.</p>
                <span class="darkroom-note__count">{count:02d} photographs in the archive</span>
            </div>

            <div class="sequence-heading rv">
                <span>Selected sequence</span>
                <span>Tap any frame to view full size</span>
            </div>
            <div class="photo-sequence rv">
                {sequence_markup}
            </div>
            {more_button}

            <div class="archive-heading rv">
                <div>
                    <span class="archive-kicker">The archive</span>
                    <h3>People, places, gatherings.</h3>
                </div>
                <p>Every photograph, browsable by subject.</p>
            </div>
            <button type="button" class="darkroom-more" data-reveal="archiveBody" aria-controls="archiveBody" aria-expanded="false" data-open-label="Close the archive" data-closed-label="Open the full archive"><span class="darkroom-more__label">Open the full archive</span><span class="darkroom-more__count">{count} photographs</span></button>
            <div class="archive-body" id="archiveBody">
            <div class="photo-chapters rv" aria-label="Filter photography archive">
                <button class="photo-chapter active" data-filter="all" aria-pressed="true">All work</button>
                <button class="photo-chapter" data-filter="people" aria-pressed="false">People</button>
                <button class="photo-chapter" data-filter="places" aria-pressed="false">Places</button>
                <button class="photo-chapter" data-filter="gatherings" aria-pressed="false">Gatherings</button>
            </div>
            <div class="photo-archive rv" id="photoGallery">
                {archive}
            </div>
            </div>
            <p class="darkroom-site-link rv" style="margin-top: clamp(40px, 5vw, 64px); padding-top: var(--s3); border-top: 1px solid var(--dark-rule); font-family: var(--mono); font-size: 0.66rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--paper-on-dark-mid);">Full sets, services and booking live on the photography site: <a href="photography/" style="color: var(--paper-on-dark); border-bottom: 1px solid var(--vermilion); padding-bottom: 2px;">joshuamgerman.com/photography &rarr;</a></p>
        </div>
    </section>'''


def _darkroom_cta() -> str:
    """Booking links inside the homepage Darkroom.

    The homepage stylesheet belongs to another file, so the few rules these
    links need ride along as inline styles built on the page's own tokens.
    """
    shared = (
        "display: inline-flex; align-items: center; gap: 10px; min-height: 48px; "
        "padding: 14px 26px; border-radius: 999px; font-family: var(--mono); "
        "font-size: 0.66rem; font-weight: 700; letter-spacing: 0.16em; "
        "text-transform: uppercase; text-decoration: none;"
    )
    return (
        '<div class="darkroom-cta rv" style="display: flex; flex-wrap: wrap; align-items: center; '
        'gap: 12px; margin: calc(-1 * var(--s4)) 0 var(--s6);">'
        f'<a class="darkroom-cta__book" href="photography/#book" style="{shared} '
        'background: var(--vermilion); color: var(--dark); border: 1.5px solid var(--vermilion);">'
        "Book a shoot &rarr;</a>"
        f'<a class="darkroom-cta__site" href="photography/" style="{shared} '
        'color: var(--paper-on-dark); border: 1.5px solid var(--dark-rule);">'
        "Visit the photography site</a>"
        "</div>"
    )
