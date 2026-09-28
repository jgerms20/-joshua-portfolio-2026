#!/usr/bin/env python3
"""
Auto-syncs The Eclectic Polymath Podcast from Spotify to the portfolio.

Full auto mode:  Set SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET env vars.
                 Get free credentials at https://developer.spotify.com/dashboard
                 (Create app → Settings → copy Client ID and Client Secret)

Reminder mode:  If no credentials, reminds every 5 days to check manually.
"""

import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).parent.parent.parent))
PODCAST_HTML = PROJECT_DIR / "podcasts" / "podcast-eclectic-polymath.html"
INDEX_HTML = PROJECT_DIR / "index.html"
TRACKER_FILE = PROJECT_DIR / ".claude" / "eclectic-podcast-tracker.json"
SHOW_ID = "3dlagzJ0jiWLTB9mF3y069"
SPOTIFY_SHOW_URL = f"https://open.spotify.com/show/{SHOW_ID}"
CHECK_INTERVAL_DAYS = 5


# ── Portfolio helpers ────────────────────────────────────────────────────────

def portfolio_episode_ids() -> list:
    """Returns Spotify episode IDs already in the portfolio (newest first)."""
    if not PODCAST_HTML.exists():
        return []
    return re.findall(r'open\.spotify\.com/embed/episode/([A-Za-z0-9]+)', PODCAST_HTML.read_text())


def portfolio_count() -> int:
    """Current episode total as displayed on the site.

    The show page now says "Live Spotify feed" instead of a number (the
    embed is the live feed, so a hardcoded count there was just drift
    waiting to happen). The homepage ticker is the remaining hardcoded
    figure, so read that first and fall back to the show page badge.
    """
    if INDEX_HTML.exists():
        m = re.findall(r'<span class="hi">(\d+) EPISODES</span>', INDEX_HTML.read_text())
        if m:
            return int(m[0])
    if PODCAST_HTML.exists():
        m = re.findall(r'id="ep-count">(\d+)', PODCAST_HTML.read_text())
        if m:
            return int(m[0])
    return 0


def set_episode_count(total: int) -> None:
    """Write the episode total everywhere it is displayed.

    The show page embeds Spotify's live show feed, so new episodes appear
    there on their own — but the count is static text. It lives in two
    places (the show page badge and the homepage ticker), and only the
    show page was ever being updated, so the homepage silently drifted.
    """
    if PODCAST_HTML.exists():
        c = PODCAST_HTML.read_text()
        c, n = re.subn(r'(id="ep-count">)\d+', rf'\g<1>{total}', c)
        if n:
            PODCAST_HTML.write_text(c)
            print(f"  [sync] show page count -> {total}")

    if INDEX_HTML.exists():
        c = INDEX_HTML.read_text()
        c, n = re.subn(r'(<span class="hi">)\d+( EPISODES</span>)', rf'\g<1>{total}\g<2>', c)
        if n:
            INDEX_HTML.write_text(c)
            print(f"  [sync] homepage ticker ({n}x) -> {total}")


# ── Tracker ──────────────────────────────────────────────────────────────────

def load_tracker() -> dict:
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text())
        except Exception:
            pass
    return {"last_checked": None, "last_known_count": 0}


def save_tracker(data: dict):
    TRACKER_FILE.write_text(json.dumps(data, indent=2))


# ── Spotify API ──────────────────────────────────────────────────────────────

def spotify_token() -> str:
    """Returns a Client Credentials access token. Raises if credentials missing/invalid."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise EnvironmentError("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not set")

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=data,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["access_token"]


def fetch_all_episodes(token: str) -> list:
    """Returns all show episodes, newest first."""
    episodes = []
    url = f"https://api.spotify.com/v1/shows/{SHOW_ID}/episodes?limit=50&market=US"
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        episodes.extend(data.get("items", []))
        url = data.get("next")
    return episodes


# ── HTML patching ────────────────────────────────────────────────────────────

def insert_episode(ep_id: str, ep_number: int) -> bool:
    """Inserts a new episode card at the top of the episodes list."""
    content = PODCAST_HTML.read_text()

    # Demote the previous "Latest Episode" label
    content = content.replace("Latest Episode", f"Episode {ep_number - 1:03d}", 1)

    new_card = f"""<!-- Episode {ep_number:03d} — LATEST -->
                <div class="episode-item">
                    <div class="episode-header">
                        <div class="episode-number">{ep_number:02d}</div>
                        <span class="episode-label-text">Latest Episode</span>
                    </div>
                    <div class="episode-embed">
                        <iframe data-testid="embed-iframe" style="border-radius:12px"
                            src="https://open.spotify.com/embed/episode/{ep_id}?utm_source=generator"
                            width="100%" height="352" frameBorder="0" allowfullscreen=""
                            allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                            loading="lazy"></iframe>
                    </div>
                </div>

                """

    marker = "<!-- Episode"
    pos = content.find(marker)
    if pos == -1:
        print(f"  [sync] ERROR: Could not find episode insertion point in HTML.")
        return False

    content = content[:pos] + new_card + content[pos:]
    PODCAST_HTML.write_text(content)
    # Keep every displayed count in sync (show page + homepage ticker).
    set_episode_count(ep_number)
    return True


# ── Git ──────────────────────────────────────────────────────────────────────

def commit_and_push(added: int, total: int):
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=PROJECT_DIR, capture_output=True, text=True,
    ).stdout.strip()

    subprocess.run(["git", "add", str(PODCAST_HTML), str(TRACKER_FILE)], cwd=PROJECT_DIR)
    msg = (
        f"Auto-sync: Add {added} Eclectic Polymath episode(s) (total: {total})\n\n"
        f"https://claude.ai/code/session_015odKPRMgeVo2QMjiFYnduq"
    )
    subprocess.run(["git", "commit", "-m", msg], cwd=PROJECT_DIR)

    for delay in [0, 2, 4, 8]:
        if delay:
            import time; time.sleep(delay)
        r = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=PROJECT_DIR, capture_output=True, text=True,
        )
        if r.returncode == 0:
            print(f"  [sync] Pushed to {branch}.")
            return
    print(f"  [sync] WARNING: Push failed after retries.")


# ── Main ─────────────────────────────────────────────────────────────────────

def run_reminder_fallback():
    """No credentials — remind on a cadence."""
    tracker = load_tracker()
    current = portfolio_count()
    now = datetime.now()

    if current != tracker.get("last_known_count", 0):
        print(f"\n🎙️  [Eclectic Polymath] Portfolio updated: {tracker['last_known_count']} → {current} episodes.")
        tracker["last_known_count"] = current
        tracker["last_checked"] = now.isoformat()
        save_tracker(tracker)
        return

    last = tracker.get("last_checked")
    should_remind = True
    if last:
        try:
            should_remind = (now - datetime.fromisoformat(last)).days >= CHECK_INTERVAL_DAYS
        except Exception:
            pass

    if should_remind:
        if current:
            print(f"\n🎙️  [Eclectic Polymath] {current} episode(s) in portfolio.")
        else:
            print(f"\n🎙️  [Eclectic Polymath] Site shows Spotify's live feed (no hardcoded count).")
        print(f"   Add SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET for full auto-sync.")
        print(f"   Get free credentials → https://developer.spotify.com/dashboard")
        print(f"   Or add an episode manually: /add-eclectic-episode")
        tracker["last_checked"] = now.isoformat()
        save_tracker(tracker)


def main() -> int:
    try:
        token = spotify_token()
    except EnvironmentError:
        run_reminder_fallback()
        return 0
    except Exception as e:
        print(f"\n🎙️  [Eclectic Polymath] Spotify auth error: {e}")
        return 1

    print(f"\n🎙️  [Eclectic Polymath Sync] Fetching episodes from Spotify...")

    try:
        all_episodes = fetch_all_episodes(token)
    except Exception as e:
        print(f"  [sync] ERROR fetching episodes: {e}")
        return 1

    known_ids = set(portfolio_episode_ids())
    # Spotify returns newest-first; reverse so we add oldest-new first (correct numbering)
    new_episodes = [ep for ep in reversed(all_episodes) if ep["id"] not in known_ids]

    if not new_episodes:
        count = portfolio_count()
        print(f"  [sync] Up to date. {count} episode(s) in portfolio, {len(all_episodes)} on Spotify.")
        tracker = load_tracker()
        tracker["last_checked"] = datetime.now().isoformat()
        tracker["last_known_count"] = count
        save_tracker(tracker)
        return 0

    base = portfolio_count()
    print(f"  [sync] {len(new_episodes)} new episode(s) found.")

    added = 0
    for i, ep in enumerate(new_episodes):
        ep_num = base + i + 1
        title = ep.get("name", f"Episode {ep_num:03d}")
        print(f"  [sync] Adding EP{ep_num:03d}: {title} ({ep['id']})")
        if insert_episode(ep["id"], ep_num):
            added += 1

    if added:
        new_total = base + added
        tracker = load_tracker()
        tracker["last_checked"] = datetime.now().isoformat()
        tracker["last_known_count"] = new_total
        save_tracker(tracker)
        commit_and_push(added, new_total)
        print(f"\n✅ Added {added} episode(s). Portfolio now has {new_total} episodes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
