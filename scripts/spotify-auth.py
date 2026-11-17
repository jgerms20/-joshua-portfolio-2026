#!/usr/bin/env python3
"""One-time helper: get the Spotify refresh token that scripts/sync-spotify.py uses.

Run it on your own computer, not in CI. It never writes anything to disk and prints
no secret except the refresh token you need to copy.

Before you start, in the Spotify developer dashboard (https://developer.spotify.com/dashboard)
open the app, choose Edit settings, and add this exact Redirect URI:
    http://127.0.0.1:8888/callback

Then:
    export SPOTIFY_CLIENT_ID=...        # from the dashboard
    export SPOTIFY_CLIENT_SECRET=...    # from the dashboard
    python3 scripts/spotify-auth.py

1. It prints a Spotify link. Open it, log in as yourself and press Agree.
2. The browser lands on http://127.0.0.1:8888/callback?code=... and shows a
   "can't connect" page. That is expected: nothing is listening there. Copy the
   whole address from the address bar and paste it back here.
3. It prints the refresh token. Save it as the GitHub repository secret
   SPOTIFY_REFRESH_TOKEN (Settings > Secrets and variables > Actions).

Scopes asked for (read-only): user-library-read, user-read-playback-position.
"""
import base64
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-library-read user-read-playback-position"


def authorize_url(client_id: str, state: str) -> str:
    return AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    })


def code_from(pasted: str, state: str) -> str:
    """Accepts the whole redirected address, or just the code."""
    pasted = pasted.strip()
    if "code=" not in pasted and "error=" not in pasted:
        return pasted
    query = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
    if query.get("error"):
        raise ValueError(f"Spotify said: {query['error'][0]}")
    if query.get("state", [state])[0] != state:
        raise ValueError("that address belongs to a different run of this script; start again")
    return query.get("code", [""])[0]


def exchange(client_id: str, client_secret: str, code: str) -> dict:
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def main() -> int:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in this terminal first (see the top of this file).")
        return 1

    state = secrets.token_urlsafe(12)
    print(f"\n1. In the Spotify developer dashboard, make sure the app lists this Redirect URI:\n\n   {REDIRECT_URI}\n")
    print(f"2. Open this link, log in and press Agree:\n\n   {authorize_url(client_id, state)}\n")
    print("3. The browser will show a \"can't connect\" page. That is fine.")
    print("   Copy the whole address from the address bar and paste it here.\n")
    try:
        code = code_from(input("Paste it here: "), state)
        if not code:
            raise ValueError("no code found in what was pasted")
        tokens = exchange(client_id, client_secret, code)
    except urllib.error.HTTPError as error:
        print(f"\nSpotify refused the code (HTTP {error.code}). Codes expire in about a minute and work once: run this again.")
        return 1
    except (ValueError, EOFError, KeyboardInterrupt) as error:
        print(f"\nStopped: {error}")
        return 1

    refresh = tokens.get("refresh_token")
    if not refresh:
        print("\nSpotify answered without a refresh token. Run this again.")
        return 1
    print("\nDone. Your refresh token (treat it like a password):\n")
    print(f"   {refresh}\n")
    print("Save it on GitHub: the repository > Settings > Secrets and variables > Actions >")
    print("New repository secret, with the name SPOTIFY_REFRESH_TOKEN and the token as the value.")
    print("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET need to be saved there the same way.")
    print("Then run the \"Sync media diet\" workflow once from the Actions tab to check it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
