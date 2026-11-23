#!/usr/bin/env python3
"""Pull what Joshua is watching and reading into data/media-diet.json.

Runs every hour in GitHub Actions (.github/workflows/sync-media-diet.yml), where
these hosts are reachable:
  - Letterboxd ratings https://letterboxd.com/jgerms/films/by/rated-date/  (every page)
  - Letterboxd diary   https://letterboxd.com/jgerms/rss/          (latest ~50 entries)
  - Goodreads shelves  currently-reading + read (list_rss for user 95365432, paged)

Films are ordered by WHEN JOSHUA RATED THEM, newest first. He rates most films
without a diary entry, and the RSS only carries diary entries, so the RSS alone
looks stale. The rated-date pages are the order; each film keeps its place as
"rated_rank" (0 = rated most recently). Letterboxd shows no rating date, so the
order is all there is: no date is invented. The diary only adds a watched date and
the rewatch flag to films it knows. Films missing a poster or year are looked up on
their film page, ENRICH_PER_RUN at a time, and the result is kept for later runs.
If the rated-date pages can't be read, the last good order is kept.

Goodreads only serves these feeds for a public profile. If the sync logs HTTP 404 for
user 95365432, set the profile to public: Goodreads > Account settings > Settings >
Privacy > "Who can view my profile: anyone". Until then the Reading shelf has no books.

The feeds only expose a recent window, so every run MERGES what it finds into the
entries already in data/media-diet.json (deduped by url, newest first, capped at
MAX_ENTRIES). The archive grows past the feed window over time.

Each source is optional: a failed fetch keeps that source's previous entries.

Listening (podcasts, articles, records) is hand-edited in data/listening.json, TV in
data/watching.json, and Spotify saves are synced by scripts/sync-spotify.py. This
script never touches any of them.

Output shape:
  {"letterboxd": [film...], "reading": [book...], "read": [book...], "updated": "..."}
  film: title, year, rating, watched, rewatch, poster, url, rated_rank (int, or null
        for a diary film that isn't in the rated list)
  book: title, author, cover, rating, url, date, shelf

Usage:
    python3 scripts/sync-media-diet.py
    python3 scripts/sync-media-diet.py --from-file letterboxd=lb.xml   # offline/testing
    python3 scripts/sync-media-diet.py --from-file read=read.xml --from-file reading=now.xml
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/media-diet.json"
KEYS = ("letterboxd", "reading", "read")
MAX_ENTRIES = 1000

# Letterboxd answers a plain, honest UA. Goodreads serves bots an HTML page (or
# nothing), so ask like a browser would.
SYNC_UA = "joshuamgerman.com media diet sync (+https://joshuamgerman.com)"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
LETTERBOXD_URL = "https://letterboxd.com/jgerms/rss/"
LETTERBOXD_USER = "jgerms"
LETTERBOXD_RATED = f"https://letterboxd.com/{LETTERBOXD_USER}/films/by/rated-date/"
LETTERBOXD_MAX_PAGES = 60
ENRICH_PER_RUN = 40
GOODREADS_USER = "95365432"
GOODREADS_RSS = f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER}"
GOODREADS_SHELVES = {"reading": "currently-reading", "read": "read"}
GOODREADS_PER_PAGE = 100
GOODREADS_MAX_PAGES = 20
LB = "{https://letterboxd.com}"


def log(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    print(f"[warn] {message}", file=sys.stderr, flush=True)


def fetch(url: str, browser: bool = False) -> bytes:
    headers = {"User-Agent": BROWSER_UA if browser else SYNC_UA}
    if browser:
        headers.update({
            "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
        })
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _rss_channel(xml_bytes: bytes):
    head = xml_bytes.lstrip()[:200].lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        raise ValueError("got an HTML page instead of RSS (blocked, private profile or bad URL?)")
    channel = ET.fromstring(xml_bytes).find("channel")
    if channel is None:
        raise ValueError("RSS has no <channel>")
    return channel


def _text(node, tag: str) -> str:
    found = node.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def _plain(value: str, limit: int = 200) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 1].rsplit(" ", 1)[0] + "…"


def _https(url: str) -> str:
    url = (url or "").strip()
    return url if url.startswith("https://") else ""


def _rfc822_date(raw: str) -> str:
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).date().isoformat() if raw else ""
    except (TypeError, ValueError, IndexError):
        return ""


def _date(item) -> str:
    return _rfc822_date(_text(item, "pubDate"))


def parse_letterboxd(xml_bytes: bytes) -> list[dict]:
    films = []
    for item in _rss_channel(xml_bytes).findall("item"):
        title = _text(item, f"{LB}filmTitle")
        if not title:  # lists and other non-diary entries
            continue
        poster = re.search(r'<img[^>]+src="([^"]+)"', _text(item, "description") or "")
        rating = _text(item, f"{LB}memberRating")
        films.append({
            "title": _plain(title, 120),
            "year": _text(item, f"{LB}filmYear"),
            "rating": float(rating) if re.fullmatch(r"\d+(\.\d+)?", rating) else None,
            "watched": _text(item, f"{LB}watchedDate") or _date(item),
            "rewatch": _text(item, f"{LB}rewatch") == "Yes",
            "poster": _https(poster.group(1)) if poster else "",
            "url": _https(_text(item, "link")),
        })
    films.sort(key=lambda f: f["watched"], reverse=True)
    return films


# ---- Letterboxd: films in the order they were rated ----
_SLUG_ATTR = re.compile(r'data-(?:item|film)-slug="([^"]+)"')
_FILM_SLUG = re.compile(r"/film/([^/?#]+)/")


def film_slug(url: str) -> str:
    found = _FILM_SLUG.search(url or "")
    return found.group(1) if found else ""


def _attr(chunk: str, *names: str) -> str:
    for name in names:
        found = re.search(rf'\b{name}="([^"]*)"', chunk)
        if found and found.group(1).strip():
            return html.unescape(found.group(1)).strip()
    return ""


def parse_rated_page(page: str) -> list[dict]:
    """One /films/by/rated-date/ page -> films in page order: slug, title, year, rating.

    Reads both grid markups Letterboxd has served: the poster <div data-film-slug ...>
    and the react LazyPoster <div data-item-slug data-item-name="Title (Year)" ...>.
    The rating is the "rated-N" class (N half-stars) inside the same grid item.
    """
    # each item starts at the tag that carries its slug, so attributes before the slug count too
    found = [(page.rfind("<", 0, m.start()), m.group(1)) for m in _SLUG_ATTR.finditer(page)]
    films, seen = [], set()
    for i, (start, slug) in enumerate(found):
        chunk = page[start: found[i + 1][0] if i + 1 < len(found) else len(page)]
        rated = re.search(r"\brated-(\d{1,2})\b", chunk)
        rating = int(rated.group(1)) / 2 if rated and 0 < int(rated.group(1)) <= 10 else None
        if slug in seen:  # one item can carry the slug on more than one element
            if films and films[-1]["slug"] == slug and films[-1]["rating"] is None:
                films[-1]["rating"] = rating
            continue
        seen.add(slug)
        tag_end = chunk.find(">")
        head = chunk[:tag_end if tag_end > 0 else len(chunk)]
        name = _attr(head, "data-item-full-display-name", "data-item-name", "data-film-name")
        if not name:
            alt = re.search(r'<img[^>]+alt="([^"]+)"', chunk)
            name = html.unescape(alt.group(1)).strip() if alt else ""
        name = re.sub(r"^Poster for\s+", "", name)
        year = ""
        titled = re.fullmatch(r"(.+?)\s+\((\d{4})\)", name)
        if titled:
            name, year = titled.group(1), titled.group(2)
        year = year or _attr(head, "data-film-release-year", "data-item-release-year")
        films.append({"slug": slug, "title": _plain(name or slug.replace("-", " "), 120),
                      "year": year if re.fullmatch(r"\d{4}", year) else "", "rating": rating})
    return films


def fetch_rated_films() -> tuple[list[dict], bool]:
    """Every rated-date page until one comes back empty. Returns (films, complete)."""
    films, seen = [], set()
    for page in range(1, LETTERBOXD_MAX_PAGES + 1):
        url = LETTERBOXD_RATED if page == 1 else f"{LETTERBOXD_RATED}page/{page}/"
        try:
            raw = fetch(url, browser=True).decode("utf-8", "replace")
        except Exception as error:
            if page == 1:
                raise
            warn(f"letterboxd rated: page {page} failed ({error}); keeping the {len(films)} films read so far")
            return films, False
        page_films = [f for f in parse_rated_page(raw) if f["slug"] not in seen]
        if not page_films:
            if page == 1:
                snippet = re.sub(r"\s+", " ", raw[:300])
                raise ValueError(f"no films found on the rated-date page (blocked or new markup?) starts: {snippet!r}")
            break
        seen.update(f["slug"] for f in page_films)
        films.extend(page_films)
        log(f"[ok] letterboxd rated: page {page} -> {len(page_films)} films")
    return films, True


def parse_film_page(page: str) -> dict:
    """A film page's JSON-LD -> {"poster", "year"} (either may be "")."""
    out = {"poster": "", "year": ""}
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    if not block:
        return out
    text = re.sub(r"/\*.*?\*/", "", block.group(1), flags=re.S).strip()
    try:
        data = json.loads(text)
    except ValueError:
        return out
    out["poster"] = _https(str(data.get("image") or ""))
    released = data.get("releasedEvent") or []
    if isinstance(released, list) and released and isinstance(released[0], dict):
        year = str(released[0].get("startDate") or "")[:4]
        out["year"] = year if re.fullmatch(r"\d{4}", year) else ""
    return out


def order_films(films: list[dict]) -> list[dict]:
    """Ranked films in rated order, then unranked diary films newest watched first."""
    ranked = sorted((f for f in films if isinstance(f.get("rated_rank"), int)), key=lambda f: f["rated_rank"])
    rest = sorted((f for f in films if not isinstance(f.get("rated_rank"), int)),
                  key=lambda f: f.get("watched") or "", reverse=True)
    return ranked + rest


def build_films(rated: list[dict], complete: bool, diary: list[dict], previous: list[dict]) -> list[dict]:
    """The rated order, filled in from the diary and the last sync. Nothing is dropped
    on a partial read: films past the pages read keep their old order after them."""
    known: dict[str, dict] = {}
    for entry in list(diary) + list(previous):  # diary first: its copy wins
        slug = film_slug(entry.get("url", ""))
        if not slug:
            continue
        mine = known.setdefault(slug, {})
        for field in ("year", "poster", "title"):
            if entry.get(field) and not mine.get(field):
                mine[field] = entry[field]
        # watched date and rewatch flag come from the same (newest) diary entry
        if (entry.get("watched") or "") > (mine.get("watched") or ""):
            mine["watched"], mine["rewatch"] = entry["watched"], entry.get("rewatch") is True

    out, placed = [], set()
    for film in rated:
        old = known.get(film["slug"], {})
        out.append({
            "title": film["title"] or old.get("title", ""),
            "year": film["year"] or old.get("year", ""),
            "rating": film["rating"],
            "watched": old.get("watched", ""),
            "rewatch": old.get("rewatch") is True,
            "poster": old.get("poster", ""),
            "url": f"https://letterboxd.com/{LETTERBOXD_USER}/film/{film['slug']}/",
            "rated_rank": len(out),
        })
        placed.add(film["slug"])
    if not complete:  # the pages we couldn't read: keep their films, in their old order
        for entry in order_films([e for e in previous if isinstance(e.get("rated_rank"), int)]):
            slug = film_slug(entry.get("url", ""))
            if slug and slug not in placed:
                out.append(dict(entry, rated_rank=len(out)))
                placed.add(slug)
    for entry in list(diary) + list(previous):  # diary films never rated stay, after the rated ones
        slug = film_slug(entry.get("url", ""))
        if isinstance(entry, dict) and entry.get("title") and slug not in placed:
            placed.add(slug)
            out.append(dict(entry, rated_rank=None))
    return order_films(out)[:MAX_ENTRIES]


def enrich_films(films: list[dict], limit: int = ENRICH_PER_RUN) -> None:
    """Fill a missing poster or year from the film page, top of the order first."""
    done = 0
    for film in films:
        if done >= limit:
            break
        if film.get("poster") and film.get("year"):
            continue
        slug = film_slug(film.get("url", ""))
        if not slug:
            continue
        done += 1
        try:
            found = parse_film_page(fetch(f"https://letterboxd.com/film/{slug}/", browser=True).decode("utf-8", "replace"))
        except Exception as error:
            warn(f"letterboxd film page {slug}: {error}")
            continue
        film["poster"] = film.get("poster") or found["poster"]
        film["year"] = film.get("year") or found["year"]
    if done:
        log(f"[ok] letterboxd: looked up {done} film pages for posters/years")


def _goodreads_cover(item) -> str:
    for tag in ("book_large_image_url", "book_medium_image_url", "book_image_url"):
        url = _https(_text(item, tag))
        if url and "nophoto" not in url:  # Goodreads' grey "no cover" placeholder
            return url
    return ""


def parse_goodreads(xml_bytes: bytes, shelf: str = "read") -> list[dict]:
    books = []
    for item in _rss_channel(xml_bytes).findall("item"):
        title = _text(item, "title")
        if not title:
            continue
        rating = _text(item, "user_rating")
        book_id = _text(item, "book_id")
        url = f"https://www.goodreads.com/book/show/{book_id}" if book_id.isdigit() else _https(_text(item, "link"))
        date = (
            _rfc822_date(_text(item, "user_read_at"))
            or _rfc822_date(_text(item, "user_date_added"))
            or _date(item)
        )
        books.append({
            "title": _plain(title, 120),
            "author": _plain(_text(item, "author_name"), 80),
            "cover": _goodreads_cover(item),
            "rating": int(rating) if rating.isdigit() and rating != "0" else None,
            "url": url.split("?", 1)[0],
            "date": date,
            "shelf": shelf,
        })
    return books


def fetch_goodreads_shelf(key: str) -> list[dict]:
    """Every page of one Goodreads shelf, until a page comes back empty or repeats."""
    shelf = GOODREADS_SHELVES[key]
    books, seen = [], set()
    for page in range(1, GOODREADS_MAX_PAGES + 1):
        url = f"{GOODREADS_RSS}?{urlencode({'shelf': shelf, 'per_page': GOODREADS_PER_PAGE, 'page': page})}"
        try:
            raw = fetch(url, browser=True)
        except Exception as error:
            if page == 1:  # retry once with the bare shelf URL before giving up
                warn(f"{key}: {url} failed ({error}); retrying without paging params")
                raw = fetch(f"{GOODREADS_RSS}?{urlencode({'shelf': shelf})}", browser=True)
                fresh = [b for b in parse_goodreads(raw, shelf) if b["url"] not in seen]
                log(f"[ok] {key}: page 1 (unpaged) -> {len(fresh)} books")
                return fresh
            raise
        page_books = parse_goodreads(raw, shelf)
        fresh = [b for b in page_books if b["url"] not in seen]
        log(f"[ok] {key}: page {page} -> {len(page_books)} books ({len(fresh)} new)")
        if not fresh:  # empty page, or Goodreads ignored ?page= and repeated itself
            break
        seen.update(b["url"] for b in fresh)
        books.extend(fresh)
        # No early stop on a short page: Goodreads may cap per_page lower than asked.
    return books


def _sort_key(key: str):
    if key == "letterboxd":  # rated order first (see order_films), then newest watched
        return lambda entry: (
            (1, -entry["rated_rank"], "") if isinstance(entry.get("rated_rank"), int) else (0, 0, entry.get("watched") or ""))
    return lambda entry: entry.get("date") or ""


def merge(key: str, fresh: list[dict], previous: list[dict]) -> list[dict]:
    """New entries win; old ones outside the feed window are kept. Newest first, capped."""
    merged, seen = [], set()
    for entry in list(fresh) + list(previous or []):
        if not isinstance(entry, dict) or not entry.get("title"):
            continue
        ident = entry.get("url") or f"{entry.get('title')}|{entry.get('watched') or entry.get('date')}"
        if ident in seen:
            continue
        seen.add(ident)
        merged.append(entry)
    merged.sort(key=_sort_key(key), reverse=True)  # stable: ties keep fresh-first order
    return merged[:MAX_ENTRIES]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-file", action="append", default=[], metavar="SOURCE=PATH")
    args = parser.parse_args(argv)
    local = dict(item.split("=", 1) for item in args.from_file)

    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    data = {key: [e for e in previous.get(key, []) if isinstance(e, dict)] for key in KEYS}
    fresh: dict[str, list[dict] | None] = {}

    for key in KEYS:
        try:
            if key in local:
                raw = Path(local[key]).read_bytes()
                entries = parse_letterboxd(raw) if key == "letterboxd" else parse_goodreads(raw, GOODREADS_SHELVES[key])
            elif key == "letterboxd":
                entries = parse_letterboxd(fetch(LETTERBOXD_URL))
            else:
                entries = fetch_goodreads_shelf(key)
            fresh[key] = entries
            log(f"[ok] {key}: {len(entries)} entries from the feed")
        except Exception as error:  # keep last good data for this source
            fresh[key] = None
            warn(f"{key}: {error} (keeping {len(data[key])} saved entries)")

    rated, complete = None, False
    if "letterboxd" not in local:
        try:
            rated, complete = fetch_rated_films()
            log(f"[ok] letterboxd rated: {len(rated)} films in rated order" + ("" if complete else " (partial)"))
            for n, film in enumerate(rated[:8], 1):
                log(f"       {n}. {film['title']} ({film['year'] or '?'}) {film['rating'] or 'unrated'}")
        except Exception as error:  # keep the last good order
            warn(f"letterboxd rated: {error} (keeping the saved order)")
    if rated:
        data["letterboxd"] = build_films(rated, complete, fresh["letterboxd"] or [], data["letterboxd"])
        enrich_films(data["letterboxd"])
    elif fresh["letterboxd"] is not None:
        if any(isinstance(e.get("rated_rank"), int) for e in data["letterboxd"]):
            # no fresh order this run: keep the saved one, add any new diary-only films after it
            data["letterboxd"] = build_films([], False, fresh["letterboxd"], data["letterboxd"])
        else:
            data["letterboxd"] = merge("letterboxd", fresh["letterboxd"], data["letterboxd"])
    if fresh["read"] is not None:
        data["read"] = merge("read", fresh["read"], data["read"])
    # Currently-reading is a state, not a log: replace it, but only when Goodreads is
    # clearly answering (an empty shelf alongside an empty "read" shelf looks like a block).
    if fresh["reading"] is not None and (fresh["reading"] or fresh["read"]):
        data["reading"] = merge("reading", fresh["reading"], [])
    finished = {b.get("url") for b in data["read"]}
    data["reading"] = [b for b in data["reading"] if b.get("url") not in finished]
    if not fresh.get("read") and not fresh.get("reading") and "read" not in local:
        warn("goodreads returned no books; check the profile is public and "
             f"{GOODREADS_RSS}?shelf=read opens in a browser")

    log(f"[total] {len(data['letterboxd'])} films, {len(data['reading'])} reading, {len(data['read'])} read")
    if {k: previous.get(k) for k in KEYS} == data and set(previous) <= set(KEYS) | {"updated"}:
        log("[same] media diet unchanged")
        return 0
    data["updated"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log("[updated] data/media-diet.json")
    return 0  # media diet is a nice-to-have; never fail the sync job


if __name__ == "__main__":
    sys.exit(main())
