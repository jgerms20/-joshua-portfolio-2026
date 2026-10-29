#!/usr/bin/env python3
"""Pull what Joshua is watching, reading and writing into data/media-diet.json.

Runs on the same schedule as the podcast sync (.github/workflows/sync-episodes.yml),
where these hosts are reachable:
  - Letterboxd diary   https://letterboxd.com/jgerms/rss/
  - Goodreads shelves  currently-reading + read (list_rss for user 95365432)
  - Substack           https://jgerms20.substack.com/feed
Each source is optional: a failed fetch keeps that source's previous entries.

Usage:
    python3 scripts/sync-media-diet.py
    python3 scripts/sync-media-diet.py --from-file letterboxd=lb.xml   # offline/testing
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import json
from pathlib import Path
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/media-diet.json"
UA = {"User-Agent": "joshuamgerman.com media diet sync (+https://joshuamgerman.com)"}
SOURCES = {
    "letterboxd": "https://letterboxd.com/jgerms/rss/",
    "reading": "https://www.goodreads.com/review/list_rss/95365432?shelf=currently-reading",
    "read": "https://www.goodreads.com/review/list_rss/95365432?shelf=read",
    "substack": "https://jgerms20.substack.com/feed",
}
LB = "{https://letterboxd.com}"
LIMITS = {"letterboxd": 8, "reading": 4, "read": 6, "substack": 4}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


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


def _date(item) -> str:
    raw = _text(item, "pubDate")
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).date().isoformat() if raw else ""
    except (TypeError, ValueError):
        return ""


def parse_letterboxd(xml_bytes: bytes) -> list[dict]:
    channel = ET.fromstring(xml_bytes).find("channel")
    films = []
    for item in channel.findall("item") if channel is not None else []:
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
    return films[: LIMITS["letterboxd"]]


def parse_goodreads(xml_bytes: bytes, limit: int) -> list[dict]:
    channel = ET.fromstring(xml_bytes).find("channel")
    books = []
    for item in channel.findall("item") if channel is not None else []:
        title = _text(item, "title")
        if not title:
            continue
        rating = _text(item, "user_rating")
        books.append({
            "title": _plain(title, 120),
            "author": _plain(_text(item, "author_name"), 80),
            "cover": _https(_text(item, "book_large_image_url") or _text(item, "book_medium_image_url") or _text(item, "book_image_url")),
            "rating": int(rating) if rating.isdigit() and rating != "0" else None,
            "url": _https(_text(item, "link")),
            "date": _date(item),
        })
    return books[:limit]


def parse_substack(xml_bytes: bytes) -> list[dict]:
    channel = ET.fromstring(xml_bytes).find("channel")
    posts = []
    for item in channel.findall("item") if channel is not None else []:
        title = _text(item, "title")
        if not title:
            continue
        posts.append({
            "title": _plain(title, 140),
            "dek": _plain(_text(item, "description"), 160),
            "date": _date(item),
            "url": _https(_text(item, "link")),
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts[: LIMITS["substack"]]


PARSERS = {
    "letterboxd": parse_letterboxd,
    "reading": lambda b: parse_goodreads(b, LIMITS["reading"]),
    "read": lambda b: parse_goodreads(b, LIMITS["read"]),
    "substack": parse_substack,
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-file", action="append", default=[], metavar="SOURCE=PATH")
    args = parser.parse_args(argv)
    local = dict(item.split("=", 1) for item in args.from_file)

    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    data = {key: previous.get(key, []) for key in SOURCES}
    ok = 0
    for key, url in SOURCES.items():
        try:
            raw = Path(local[key]).read_bytes() if key in local else fetch(url)
            entries = PARSERS[key](raw)
            if entries or key in local:
                data[key] = entries
            ok += 1
            print(f"[ok] {key}: {len(entries)} entries")
        except Exception as error:  # keep last good data for this source
            print(f"[warn] {key}: {error}", file=sys.stderr)
    if {k: v for k, v in previous.items() if k != "updated"} == data:
        print("[same] media diet unchanged")
        return 0
    data["updated"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("[updated] data/media-diet.json")
    return 0  # media diet is a nice-to-have; never fail the shared sync job


if __name__ == "__main__":
    sys.exit(main())
