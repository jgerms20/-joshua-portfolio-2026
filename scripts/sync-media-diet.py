#!/usr/bin/env python3
"""Pull what Joshua is watching and reading into data/media-diet.json.

Runs on the same schedule as the podcast sync (.github/workflows/sync-episodes.yml),
where these hosts are reachable:
  - Letterboxd diary   https://letterboxd.com/jgerms/rss/          (latest ~50 entries)
  - Goodreads shelves  currently-reading + read (list_rss for user 95365432, paged)

The feeds only expose a recent window, so every run MERGES what it finds into the
entries already in data/media-diet.json (deduped by url, newest first, capped at
MAX_ENTRIES). The archive grows past the feed window over time.

Each source is optional: a failed fetch keeps that source's previous entries.

Listening (podcasts, articles, records) is hand-edited in data/listening.json and
this script never touches it.

Output shape:
  {"letterboxd": [film...], "reading": [book...], "read": [book...], "updated": "..."}
  film: title, year, rating, watched, rewatch, poster, url
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
    field = "watched" if key == "letterboxd" else "date"
    return lambda entry: entry.get(field) or ""


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

    if fresh["letterboxd"] is not None:
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
    return 0  # media diet is a nice-to-have; never fail the shared sync job


if __name__ == "__main__":
    sys.exit(main())
