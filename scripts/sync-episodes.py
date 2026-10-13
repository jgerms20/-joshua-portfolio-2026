#!/usr/bin/env python3
"""Pull the newest episodes for each show into data/episodes/<slug>.json.

Runs on a schedule in GitHub Actions (.github/workflows/sync-episodes.yml),
where the podcast hosts are reachable.

Primary source: the Curious & Creative network site
(github.com/jgerms20/curious-and-creative), which already aggregates every
show (RSS, Spotify and YouTube, with its own Spotify credentials) into
site/data/content.json every 6 hours. Each show's "network_key" maps it
there. Its own rss / apple_id / youtube_channel / spotify ids below are the
fallback when the network data is unavailable. The run also writes
data/network.json, a trimmed snapshot that powers /network/. Each show in data/podcast-feeds.json
needs an "rss" URL, an Apple Podcasts "apple_id" (the feed URL is looked
up from Apple), a "spotify_show" id, or just one "spotify_episode" id (its
show is looked up). Spotify needs SPOTIFY_CLIENT_ID and
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
NETWORK_SITE = "https://jgerms20.github.io/curious-and-creative/"
NETWORK_SOURCES = (
    "https://raw.githubusercontent.com/jgerms20/curious-and-creative/main/site/data/content.json",
    NETWORK_SITE + "data/content.json",
)
NETWORK_OUT = ROOT / "data/network.json"
ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"
MEDIA = "{http://search.yahoo.com/mrss/}"
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
UA = {"User-Agent": "joshuamgerman.com episode sync (+https://joshuamgerman.com)"}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def spotify_token() -> str:
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
        return json.loads(response.read())["access_token"]


def spotify_get(path: str, token: str) -> dict:
    request = urllib.request.Request(f"https://api.spotify.com/v1/{path}", headers={**UA, "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def spotify_show_for_episode(episode_id: str) -> str:
    """One episode link is enough: the API says which show it belongs to."""
    return spotify_get(f"episodes/{episode_id}?market=US", spotify_token())["show"]["id"]


def spotify_episodes(show_id: str) -> list[dict]:
    """Newest episodes from the Spotify Web API (client-credentials flow)."""
    token = spotify_token()
    return parse_spotify(spotify_get(f"shows/{show_id}/episodes?market=US&limit={MAX_EPISODES}", token))


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


def load_network(path: str | None = None) -> dict | None:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    for url in NETWORK_SOURCES:
        try:
            return json.loads(fetch(url))
        except Exception as error:  # try the next mirror
            print(f"[warn] network data unavailable from {url}: {error}")
    return None


def _abs(url: str | None) -> str:
    if not url:
        return ""
    return url if url.startswith("https://") else NETWORK_SITE + url.lstrip("./")


def network_episodes(content: dict, key: str) -> list[dict]:
    show = next((s for s in content.get("shows", []) if s.get("key") == key), {})
    art = _abs(show.get("art_remote") or show.get("art"))
    episodes = []
    for e in content.get("episodes", []):
        if e.get("show") != key or not e.get("title"):
            continue
        seconds = e.get("duration") or 0
        episodes.append({
            "title": _plain(e["title"], 160),
            "date": (e.get("date") or "")[:10],
            "url": e.get("url") if str(e.get("url", "")).startswith("https://") else "",
            "description": _plain(e.get("description") or ""),
            "image": _abs(e.get("image")) or art,
            "duration": _duration(str(seconds)) if seconds else "",
        })
    episodes.sort(key=lambda x: x["date"], reverse=True)
    return episodes[:MAX_EPISODES]


def write_network(content: dict) -> bool:
    """Trimmed snapshot of the network for /network/: shows plus newest episodes."""
    shows = []
    ordered = sorted(content.get("shows", []), key=lambda s: s.get("latest") or "", reverse=True)
    ordered.sort(key=lambda s: not s.get("flagship"))  # flagship first, then most recent
    for s in ordered:
        shows.append({
            "key": s.get("key"), "name": s.get("name"), "short": s.get("short") or s.get("name"),
            "kind": s.get("kind"), "flagship": bool(s.get("flagship")), "hosts": s.get("hosts") or [],
            "tagline": s.get("tagline") or "", "about": s.get("about") or "",
            "url": s.get("spotify_url") or s.get("youtube_url") or s.get("channel_url") or "",
            "art": _abs(s.get("art_remote") or s.get("art")), "latest": (s.get("latest") or "")[:10],
            "count": s.get("count") or 0,
        })
    latest = sorted((e for e in content.get("episodes", []) if e.get("title")), key=lambda e: e.get("date") or "", reverse=True)[:12]
    names = {s["key"]: s["short"] for s in shows}
    payload = {
        "source": NETWORK_SITE,
        "generated_at": content.get("generated_at"),
        "shows": shows,
        "latest": [{
            "show": e.get("show"), "show_name": names.get(e.get("show"), ""), "kind": e.get("kind"),
            "title": _plain(e["title"], 160), "date": (e.get("date") or "")[:10],
            "url": e.get("url") if str(e.get("url", "")).startswith("https://") else "",
            "image": _abs(e.get("image")),
        } for e in latest],
    }
    previous = json.loads(NETWORK_OUT.read_text(encoding="utf-8")) if NETWORK_OUT.exists() else None
    if previous and {k: v for k, v in previous.items() if k != "generated_at"} == {k: v for k, v in payload.items() if k != "generated_at"}:
        return False
    NETWORK_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def youtube_episodes(channel_id: str) -> list[dict]:
    return parse_youtube(fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"))


def parse_youtube(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    episodes = []
    for entry in root.findall(f"{ATOM}entry"):
        video = entry.findtext(f"{YT}videoId") or ""
        group = entry.find(f"{MEDIA}group")
        description = group.findtext(f"{MEDIA}description") if group is not None else ""
        episodes.append({
            "title": _plain(entry.findtext(f"{ATOM}title") or "", 160),
            "date": (entry.findtext(f"{ATOM}published") or "")[:10],
            "url": f"https://www.youtube.com/watch?v={video}" if video else "",
            "description": _plain(description or ""),
            "image": f"https://i.ytimg.com/vi/{video}/hqdefault.jpg" if video else "",
            "duration": "",
        })
    episodes = [e for e in episodes if e["title"]]
    episodes.sort(key=lambda e: e["date"], reverse=True)
    return episodes[:MAX_EPISODES]


def merge_with_existing(slug: str, fresh: list[dict]) -> list[dict]:
    """Keep earlier episodes a source no longer lists (Spotify-only shows expose just the newest)."""
    path = OUT_DIR / f"{slug}.json"
    if not path.exists():
        return fresh
    old = json.loads(path.read_text(encoding="utf-8")).get("episodes", [])
    seen = {e["url"] or e["title"] for e in fresh}
    merged = fresh + [e for e in old if (e.get("url") or e.get("title")) not in seen]
    merged.sort(key=lambda e: e.get("date", ""), reverse=True)
    return merged[:MAX_EPISODES]


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


def own_source(show: dict, local: dict):
    """Fallback when the network has nothing for a show. Returns (feed, episodes) or None."""
    slug = show["slug"]
    if slug in local:
        return local[slug], parse_feed(Path(local[slug]).read_bytes())
    if show.get("rss") or show.get("apple_id"):
        feed = feed_url_for(show)
        if feed:
            return feed, parse_feed(fetch(feed))
    if show.get("youtube_channel"):
        return f"https://www.youtube.com/channel/{show['youtube_channel']}", youtube_episodes(show["youtube_channel"])
    if show.get("spotify_show") or show.get("spotify_episode"):
        if not show.get("spotify_show"):
            show["spotify_show"] = spotify_show_for_episode(show["spotify_episode"])
        return f"https://open.spotify.com/show/{show['spotify_show']}", spotify_episodes(show["spotify_show"])
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-file", action="append", default=[], metavar="SLUG=PATH",
                        help="parse a local feed file instead of fetching (testing)")
    parser.add_argument("--network-file", help="read the network content.json from a local path")
    args = parser.parse_args(argv)
    local = dict(item.split("=", 1) for item in args.from_file)

    shows = json.loads(CONFIG.read_text(encoding="utf-8"))["shows"]
    network = load_network(args.network_file)
    if network:
        print(f"[{'updated' if write_network(network) else 'same'}] network snapshot ({len(network.get('shows', []))} shows)")

    failures = 0
    for show in shows:
        slug = show["slug"]
        try:
            source, episodes = None, []
            if network and show.get("network_key") and slug not in local:
                episodes = network_episodes(network, show["network_key"])
                source = NETWORK_SITE
            if not episodes:
                found = own_source(show, local)
                if not found:
                    print(f"[skip] {slug}: nothing in the network data and no feed of its own")
                    continue
                source, episodes = found
            if not episodes:
                print(f"[warn] {slug}: no episodes found; leaving existing data alone")
                continue
            episodes = merge_with_existing(slug, episodes)
            changed = write_show(slug, source, episodes, show.get("spotify_show"))
            print(f"[{'updated' if changed else 'same'}] {slug}: {len(episodes)} episodes, newest {episodes[0]['date']}")
        except Exception as error:  # one bad source shouldn't stop the others
            failures += 1
            print(f"[error] {slug}: {error}", file=sys.stderr)
    return 1 if failures == len(shows) else 0

if __name__ == "__main__":
    sys.exit(main())
