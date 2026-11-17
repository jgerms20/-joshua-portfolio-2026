#!/usr/bin/env python3
"""Pull what Joshua has saved on Spotify into data/spotify.json.

Reads his own library with the Spotify Web API (authorization-code flow, kept alive
with a refresh token):
  - saved albums    GET /v1/me/albums
  - saved shows     GET /v1/me/shows
  - saved episodes  GET /v1/me/episodes

Credentials come from the environment only (GitHub repository secrets; never commit
them, never print them):
  SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
If any is missing the script says so and exits 0 without touching the file.
Run scripts/spotify-auth.py once on your own computer to get the refresh token.

Every run MERGES what it finds into the entries already in data/spotify.json (deduped
by url, newest first, capped at MAX_ENTRIES), so the history keeps growing even after
something is un-saved. Each source is optional: a failed fetch keeps that source's
previous entries. The file is rewritten only when something changed.

The Listening shelf (assets/media-diet.js) merges this file with the hand picks in
data/listening.json, which this script never touches.

Output shape:
  {"albums": [album...], "shows": [show...], "episodes": [episode...], "updated": "..."}
  album:   title, artist, image, url, added
  show:    title, publisher, image, url, added
  episode: title, show, image, url, added

Usage:
    python3 scripts/sync-spotify.py
"""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/spotify.json"
KEYS = ("albums", "shows", "episodes")
ENV = ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN")
TOKEN_URL = "https://accounts.spotify.com/api/token"
API = "https://api.spotify.com/v1/"
PAGE_SIZE = 50
MAX_PAGES = 40
MAX_ENTRIES = 1000
UA = {"User-Agent": "joshuamgerman.com media diet sync (+https://joshuamgerman.com)"}


def log(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    print(f"[warn] {message}", file=sys.stderr, flush=True)


def credentials() -> dict | None:
    """The three values from the environment, or None when any is missing."""
    values = {name: os.environ.get(name, "").strip() for name in ENV}
    return values if all(values.values()) else None


def access_token(creds: dict) -> str:
    """Trade the long-lived refresh token for a one-hour access token."""
    auth = base64.b64encode(f"{creds['SPOTIFY_CLIENT_ID']}:{creds['SPOTIFY_CLIENT_SECRET']}".encode()).decode()
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": creds["SPOTIFY_REFRESH_TOKEN"],
        }).encode(),
        headers={**UA, "Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())["access_token"]


def api_get(url: str, token: str) -> dict:
    if not url.startswith(API):  # the bearer token only ever goes to the Spotify API
        raise ValueError("refusing to send the token to a non-Spotify URL")
    request = urllib.request.Request(url, headers={**UA, "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def fetch_all(path: str, token: str, get=api_get) -> list[dict]:
    """Every page of one library endpoint, following "next" until it runs out."""
    items, url = [], f"{API}{path}?{urllib.parse.urlencode({'limit': PAGE_SIZE, 'offset': 0})}"
    for _ in range(MAX_PAGES):
        payload = get(url, token)
        items.extend(payload.get("items") or [])
        url = payload.get("next") or ""
        if not url:
            break
    return items


def _plain(value, limit: int = 160) -> str:
    value = re.sub(r"\s+", " ", value if isinstance(value, str) else "").strip()
    return value if len(value) <= limit else value[: limit - 1].rsplit(" ", 1)[0] + "…"


def _https(url) -> str:
    url = url.strip() if isinstance(url, str) else ""
    return url if url.startswith("https://") and not re.search(r"[\s\"'<>]", url) else ""


def _image(images) -> str:
    """The largest https image Spotify lists."""
    ranked = sorted((i for i in images or [] if isinstance(i, dict)), key=lambda i: -(i.get("width") or 0))
    return next((u for u in (_https(i.get("url")) for i in ranked) if u), "")


def _link(obj: dict) -> str:
    return _https((obj.get("external_urls") or {}).get("spotify"))


def _added(item: dict) -> str:
    raw = item.get("added_at")
    return raw[:10] if isinstance(raw, str) and re.match(r"\d{4}-\d{2}-\d{2}", raw) else ""


def _entries(items, inner: str, build) -> list[dict]:
    out = []
    for item in items or []:
        obj = item.get(inner) if isinstance(item, dict) else None
        if not isinstance(obj, dict) or not _plain(obj.get("name")) or not _link(obj):
            continue  # removed or region-locked entries come back as null or nameless
        out.append({"title": _plain(obj["name"]), **build(obj), "image": _image(obj.get("images")),
                    "url": _link(obj), "added": _added(item)})
    out.sort(key=lambda e: e["added"], reverse=True)
    return out


def parse_albums(items) -> list[dict]:
    """Items of GET /v1/me/albums -> [{title, artist, image, url, added}]."""
    def artist(album):
        names = [_plain(a.get("name"), 80) for a in album.get("artists") or [] if isinstance(a, dict)]
        return {"artist": _plain(", ".join(n for n in names if n), 120)}
    return _entries(items, "album", artist)


def parse_shows(items) -> list[dict]:
    """Items of GET /v1/me/shows -> [{title, publisher, image, url, added}]."""
    return _entries(items, "show", lambda show: {"publisher": _plain(show.get("publisher"), 120)})


def parse_episodes(items) -> list[dict]:
    """Items of GET /v1/me/episodes -> [{title, show, image, url, added}]."""
    return _entries(items, "episode", lambda ep: {"show": _plain((ep.get("show") or {}).get("name"), 120)})


SOURCES = {
    "albums": ("me/albums", parse_albums),
    "shows": ("me/shows", parse_shows),
    "episodes": ("me/episodes", parse_episodes),
}


def merge(fresh: list[dict], previous: list[dict]) -> list[dict]:
    """New entries win; ones no longer saved are kept. Newest first, capped."""
    merged, seen = [], set()
    for entry in list(fresh) + list(previous or []):
        if not isinstance(entry, dict) or not entry.get("title") or not _https(entry.get("url")):
            continue
        if entry["url"] in seen:
            continue
        seen.add(entry["url"])
        merged.append(entry)
    merged.sort(key=lambda e: e.get("added") or "", reverse=True)  # stable: ties keep fresh-first order
    return merged[:MAX_ENTRIES]


def main(argv=None) -> int:
    creds = credentials()
    if not creds:
        log("[skip] spotify: " + " / ".join(ENV) + " not all set; nothing to do")
        return 0

    try:
        previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    except ValueError:
        previous = {}
    if not isinstance(previous, dict):
        previous = {}
    data = {key: [e for e in previous.get(key) or [] if isinstance(e, dict)] for key in KEYS}

    try:
        token = access_token(creds)
    except Exception as error:  # an expired or revoked token must not fail the shared sync job
        code = f"HTTP {error.code}" if isinstance(error, urllib.error.HTTPError) else type(error).__name__
        warn(f"spotify: could not get an access token ({code}); run scripts/spotify-auth.py again "
             "and update the SPOTIFY_REFRESH_TOKEN secret")
        return 0

    for key, (path, parse) in SOURCES.items():
        try:
            entries = parse(fetch_all(path, token))
            data[key] = merge(entries, data[key])
            log(f"[ok] {key}: {len(entries)} saved on Spotify")
        except Exception as error:  # keep last good data for this source
            code = f"HTTP {error.code}" if isinstance(error, urllib.error.HTTPError) else str(error)
            warn(f"{key}: {code} (keeping {len(data[key])} saved entries)")

    log(f"[total] {len(data['albums'])} albums, {len(data['shows'])} shows, {len(data['episodes'])} episodes")
    if {key: previous.get(key) for key in KEYS} == data:
        log("[same] spotify unchanged")
        return 0
    data["updated"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log("[updated] data/spotify.json")
    return 0  # a nice-to-have; never fail the sync job


if __name__ == "__main__":
    sys.exit(main())
