#!/usr/bin/env python3
"""Pull the newest episodes for each show into data/episodes/<slug>.json.

Runs on a schedule in GitHub Actions (.github/workflows/sync-episodes.yml),
where the podcast hosts are reachable. Each show in data/podcast-feeds.json
needs an "rss" URL, an Apple Podcasts "apple_id" (the feed URL is looked
up from Apple), or a "spotify_show" id. Spotify needs SPOTIFY_CLIENT_ID and
SPOTIFY_CLIENT_SECRET in the environment (GitHub repository secrets; never
commit them). Shows with none of these are skipped, and the podcast pages
simply don't show a "Latest episodes" list for them.

Usage:
    python3 scripts/sync-episodes.py            # fetch and write
    python3 scripts/sync-episodes.py --from-file dominate=feed.xml   # offline
"""
import argparse
import base64
import os
import urllib.parse
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
CONFIG = ROOT / "data/podcast-feeds.json"
OUT_DIR = ROOT / "data/episodes"
MAX_EPISODES = 12
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
UA = {"User-Agent": "joshuamgerman.com episode sync (+https://joshuamgerman.com)"}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def spotify_episodes(show_id: str) -> list[dict]:
    """Newest episodes from the Spotify Web API (client-credentials flow)."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not secret:
        raise RuntimeError("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not set")
    auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    token_request = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={**UA, "Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(token_request, timeout=30) as response:
        token = json.loads(response.read())["access_token"]
    request = urllib.request.Request(
        f"https://api.spotify.com/v1/shows/{show_id}/episodes?market=US&limit={MAX_EPISODES}",
        headers={**UA, "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return parse_spotify(json.loads(response.read()))


def parse_spotify(payload: dict) -> list[dict]:
    episodes = []
    for item in payload.get("items") or []:
        if not item or not item.get("name"):
            continue
        images = sorted(item.get("images") or [], key=lambda i: -(i.get("width") or 0))
        seconds = round((item.get("duration_ms") or 0) / 1000)
        episodes.append({
            "title": _plain(item["name"], 160),
            "date": (item.get("release_date") or "")[:10],
            "url": (item.get("external_urls") or {}).get("spotify", ""),
            "description": _plain(item.get("description") or ""),
            "image": images[0]["url"] if images else "",
            "duration": _duration(str(seconds)) if seconds else "",
        })
    episodes.sort(key=lambda e: e["date"], reverse=True)
    return episodes[:MAX_EPISODES]


def feed_url_for(show: dict) -> str | None:
    if show.get("rss"):
        return show["rss"]
    if show.get("apple_id"):
        data = json.loads(fetch(f"https://itunes.apple.com/lookup?id={show['apple_id']}&entity=podcast"))
        for result in data.get("results", []):
            if result.get("feedUrl"):
                return result["feedUrl"]
    return None


def _text(node, tag: str) -> str:
    found = node.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def _plain(value: str, limit: int = 240) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 1].rsplit(" ", 1)[0] + "…"


def _duration(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if raw.isdigit():
        seconds = int(raw)
    else:
        parts = [int(p) for p in raw.split(":") if p.isdigit()]
        seconds = 0
        for part in parts:
            seconds = seconds * 60 + part
    minutes = round(seconds / 60)
    return f"{minutes // 60} hr {minutes % 60} min" if minutes >= 60 else f"{minutes} min"


def parse_feed(xml_bytes: bytes) -> list[dict]:
    channel = ET.fromstring(xml_bytes).find("channel")
    if channel is None:
        return []
    show_image = ""
    image_node = channel.find(f"{ITUNES}image")
    if image_node is not None:
        show_image = image_node.get("href", "")
    episodes = []
    for item in channel.findall("item"):
        title = _text(item, "title")
        if not title:
            continue
        date = ""
        if _text(item, "pubDate"):
            try:
                date = parsedate_to_datetime(_text(item, "pubDate")).astimezone(timezone.utc).date().isoformat()
            except (TypeError, ValueError):
                date = ""
        enclosure = item.find("enclosure")
        link = _text(item, "link") or (enclosure.get("url", "") if enclosure is not None else "")
        image_node = item.find(f"{ITUNES}image")
        episodes.append({
            "title": _plain(title, 160),
            "date": date,
            "url": link if link.startswith("https://") else "",
            "description": _plain(_text(item, f"{ITUNES}summary") or _text(item, "description")),
            "image": (image_node.get("href", "") if image_node is not None else "") or show_image,
            "duration": _duration(_text(item, f"{ITUNES}duration")),
        })
    episodes.sort(key=lambda e: e["date"], reverse=True)
    return episodes[:MAX_EPISODES]


def write_show(slug: str, feed: str, episodes: list[dict], spotify_show: str | None = None) -> bool:
    """Write only when the episode list changed, so the Action commits nothing on quiet days."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{slug}.json"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if (previous.get("episodes") == episodes and previous.get("feed") == feed
                and previous.get("spotify_show") == spotify_show):
            return False
    payload = {
        "show": slug,
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "feed": feed,
        "spotify_show": spotify_show,
        "episodes": episodes,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-file", action="append", default=[], metavar="SLUG=PATH",
                        help="parse a local feed file instead of fetching (testing)")
    args = parser.parse_args(argv)
    local = dict(item.split("=", 1) for item in args.from_file)

    shows = json.loads(CONFIG.read_text(encoding="utf-8"))["shows"]
    failures = 0
    for show in shows:
        slug = show["slug"]
        try:
            if slug in local:
                feed, xml_bytes = local[slug], Path(local[slug]).read_bytes()
            elif show.get("spotify_show") and not (show.get("rss") or show.get("apple_id")):
                feed, xml_bytes = f"https://open.spotify.com/show/{show['spotify_show']}", None
            else:
                feed = feed_url_for(show)
                if not feed:
                    print(f"[skip] {slug}: no rss, apple_id or spotify_show configured")
                    continue
                xml_bytes = fetch(feed)
            episodes = parse_feed(xml_bytes) if xml_bytes is not None else spotify_episodes(show["spotify_show"])
            if not episodes:
                print(f"[warn] {slug}: feed had no episodes; leaving existing data alone")
                continue
            changed = write_show(slug, feed, episodes, show.get("spotify_show"))
            print(f"[{'updated' if changed else 'same'}] {slug}: {len(episodes)} episodes, newest {episodes[0]['date']}")
        except Exception as error:  # one bad feed shouldn't stop the others
            failures += 1
            print(f"[error] {slug}: {error}", file=sys.stderr)
    configured = [s for s in shows if s.get("rss") or s.get("apple_id") or s.get("spotify_show")]
    return 1 if failures and failures == len(configured) else 0


if __name__ == "__main__":
    sys.exit(main())
