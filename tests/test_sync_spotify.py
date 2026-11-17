import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync = load("sync_spotify", "scripts/sync-spotify.py")
auth = load("spotify_auth", "scripts/spotify-auth.py")

ENV = {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret", "SPOTIFY_REFRESH_TOKEN": "refresh"}
IMAGES = [{"url": "https://i.scdn.co/small", "width": 64}, {"url": "https://i.scdn.co/large", "width": 640}]

ALBUMS = [
    {"added_at": "2026-11-10T08:00:00Z", "album": {
        "name": "  Album   One ", "artists": [{"name": "Artist A"}, {"name": "Artist B"}], "images": IMAGES,
        "external_urls": {"spotify": "https://open.spotify.com/album/1"}}},
    {"added_at": "2026-11-12T08:00:00Z", "album": {
        "name": "Album Two", "artists": [{"name": "Artist C"}], "images": [{"url": "http://insecure/x", "width": 640}],
        "external_urls": {"spotify": "https://open.spotify.com/album/2"}}},
    {"added_at": "2026-11-13T08:00:00Z", "album": {"name": "No link", "external_urls": {"spotify": "http://open.spotify.com/album/3"}}},
    {"added_at": "2026-11-13T08:00:00Z", "album": None},
    None,
]
SHOWS = [{"added_at": "2026-10-01T00:00:00Z", "show": {
    "name": "Show One", "publisher": "Publisher", "images": IMAGES, "external_urls": {"spotify": "https://open.spotify.com/show/1"}}}]
EPISODES = [
    {"added_at": "2026-11-15T00:00:00Z", "episode": {
        "name": "Episode One", "show": {"name": "Show One"}, "images": IMAGES,
        "external_urls": {"spotify": "https://open.spotify.com/episode/1"}}},
    {"added_at": "2026-11-16T00:00:00Z", "episode": None},  # removed from Spotify
]


class SpotifyParserTests(unittest.TestCase):
    def test_albums(self):
        self.assertEqual(sync.parse_albums(ALBUMS), [
            {"title": "Album Two", "artist": "Artist C", "image": "", "url": "https://open.spotify.com/album/2", "added": "2026-11-12"},
            {"title": "Album One", "artist": "Artist A, Artist B", "image": "https://i.scdn.co/large",
             "url": "https://open.spotify.com/album/1", "added": "2026-11-10"},
        ])

    def test_shows_and_episodes(self):
        self.assertEqual(sync.parse_shows(SHOWS), [
            {"title": "Show One", "publisher": "Publisher", "image": "https://i.scdn.co/large",
             "url": "https://open.spotify.com/show/1", "added": "2026-10-01"}])
        self.assertEqual(sync.parse_episodes(EPISODES), [
            {"title": "Episode One", "show": "Show One", "image": "https://i.scdn.co/large",
             "url": "https://open.spotify.com/episode/1", "added": "2026-11-15"}])

    def test_parsers_survive_junk(self):
        for parse in (sync.parse_albums, sync.parse_shows, sync.parse_episodes):
            self.assertEqual(parse(None), [])
            self.assertEqual(parse([None, {}, {"album": "x", "show": 3, "episode": []}]), [])

    def test_every_url_is_https(self):
        for entry in sync.parse_albums(ALBUMS) + sync.parse_shows(SHOWS) + sync.parse_episodes(EPISODES):
            self.assertTrue(entry["url"].startswith("https://"))
            self.assertTrue(entry["image"] == "" or entry["image"].startswith("https://"))

    def test_merge_accumulates_history(self):
        old = [{"title": "Un-saved since", "url": "https://open.spotify.com/album/9", "added": "2025-01-01"},
               {"title": "Album One (stale title)", "url": "https://open.spotify.com/album/1", "added": "2026-11-10"},
               {"title": "Bad", "url": "http://x"}, "junk"]
        merged = sync.merge(sync.parse_albums(ALBUMS), old)
        self.assertEqual([e["title"] for e in merged], ["Album Two", "Album One", "Un-saved since"])

    def test_paging_follows_next(self):
        pages = {
            sync.API + "me/albums?limit=50&offset=0": {"items": [1, 2], "next": sync.API + "me/albums?limit=50&offset=50"},
            sync.API + "me/albums?limit=50&offset=50": {"items": [3], "next": None},
        }
        calls = []

        def get(url, token):
            calls.append((url, token))
            return pages[url]

        self.assertEqual(sync.fetch_all("me/albums", "tok", get=get), [1, 2, 3])
        self.assertEqual(len(calls), 2)

    def test_token_only_goes_to_spotify(self):
        with self.assertRaises(ValueError):
            sync.api_get("https://evil.example/v1/me/albums", "tok")


class SpotifySyncRunTests(unittest.TestCase):
    def run_sync(self, previous, items=None, env=ENV, token=None):
        items = items or {"me/albums": ALBUMS, "me/shows": SHOWS, "me/episodes": EPISODES}

        def fetch_all(path, tok):
            if isinstance(items.get(path), Exception):
                raise items[path]
            return items.get(path, [])

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "spotify.json"
            if previous is not None:
                out.write_text(json.dumps(previous), encoding="utf-8")
            before = out.read_text(encoding="utf-8") if out.exists() else None
            with mock.patch.object(sync, "OUT", out), mock.patch.object(sync, "fetch_all", fetch_all), \
                    mock.patch.object(sync, "access_token", token or (lambda creds: "tok")), \
                    mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(sync.main([]), 0)
            after = out.read_text(encoding="utf-8") if out.exists() else None
            return before, after

    def test_writes_the_documented_shape(self):
        _, after = self.run_sync({"albums": [], "shows": [], "episodes": [], "updated": ""})
        data = json.loads(after)
        self.assertEqual(list(data), ["albums", "shows", "episodes", "updated"])
        self.assertEqual(set(data["albums"][0]), {"title", "artist", "image", "url", "added"})
        self.assertEqual(set(data["shows"][0]), {"title", "publisher", "image", "url", "added"})
        self.assertEqual(set(data["episodes"][0]), {"title", "show", "image", "url", "added"})
        self.assertRegex(data["updated"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_unchanged_data_is_not_rewritten(self):
        _, first = self.run_sync(None)
        before, after = self.run_sync(json.loads(first))
        self.assertEqual(before, after)

    def test_missing_credentials_exit_quietly(self):
        for missing in ENV:
            env = {k: v for k, v in ENV.items() if k != missing}
            token = mock.Mock(side_effect=AssertionError("must not call Spotify"))
            before, after = self.run_sync({"albums": []}, env=env, token=token)
            self.assertEqual(before, after)
            token.assert_not_called()

    def test_a_failed_source_keeps_its_saved_entries(self):
        previous = {"albums": [{"title": "Kept", "url": "https://open.spotify.com/album/k", "added": "2026-01-01"}],
                    "shows": [], "episodes": [], "updated": ""}
        _, after = self.run_sync(previous, items={"me/albums": OSError("blocked"), "me/shows": SHOWS})
        data = json.loads(after)
        self.assertEqual([a["title"] for a in data["albums"]], ["Kept"])
        self.assertEqual(len(data["shows"]), 1)

    def test_a_bad_refresh_token_never_fails_the_job(self):
        before, after = self.run_sync({"albums": []}, token=mock.Mock(side_effect=OSError("401")))
        self.assertEqual(before, after)

    def test_refresh_token_flow(self):
        sent = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"access_token": "fresh"}'

        def urlopen(request, timeout=0):
            sent["url"], sent["body"], sent["auth"] = request.full_url, request.data.decode(), request.get_header("Authorization")
            return Response()

        with mock.patch.object(sync.urllib.request, "urlopen", urlopen):
            self.assertEqual(sync.access_token(ENV), "fresh")
        self.assertEqual(sent["url"], "https://accounts.spotify.com/api/token")
        self.assertEqual(sent["body"], "grant_type=refresh_token&refresh_token=refresh")
        self.assertTrue(sent["auth"].startswith("Basic "))

    def test_committed_file_is_valid(self):
        data = json.loads((ROOT / "data/spotify.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"albums", "shows", "episodes", "updated"})
        for key in ("albums", "shows", "episodes"):
            self.assertIsInstance(data[key], list)
            for entry in data[key]:
                self.assertTrue(entry.get("title"))
                self.assertTrue(entry["url"].startswith("https://"))
                self.assertTrue(not entry.get("image") or entry["image"].startswith("https://"))
                self.assertRegex(entry.get("added", ""), r"^(\d{4}-\d{2}-\d{2})?$")


class SpotifyAuthHelperTests(unittest.TestCase):
    def test_authorize_url(self):
        url = auth.authorize_url("my-client", "st")
        self.assertTrue(url.startswith("https://accounts.spotify.com/authorize?"))
        self.assertIn("client_id=my-client", url)
        self.assertIn("response_type=code", url)
        self.assertIn("redirect_uri=http%3A%2F%2F127.0.0.1%3A8888%2Fcallback", url)
        self.assertIn("scope=user-library-read+user-read-playback-position", url)

    def test_reads_the_code_from_a_pasted_address_or_code(self):
        self.assertEqual(auth.code_from(" abc123 ", "st"), "abc123")
        self.assertEqual(auth.code_from("http://127.0.0.1:8888/callback?code=abc123&state=st", "st"), "abc123")
        with self.assertRaises(ValueError):
            auth.code_from("http://127.0.0.1:8888/callback?code=abc123&state=other", "st")
        with self.assertRaises(ValueError):
            auth.code_from("http://127.0.0.1:8888/callback?error=access_denied&state=st", "st")

    def test_prints_no_secret_but_the_refresh_token(self):
        source = (ROOT / "scripts/spotify-auth.py").read_text(encoding="utf-8")
        printed = "\n".join(re.findall(r"print\((.*)\)", source))
        self.assertNotIn("client_secret", printed)
        self.assertNotIn("access_token", printed)
        self.assertIn("SPOTIFY_REFRESH_TOKEN", printed)


class MediaDietWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / ".github/workflows/sync-media-diet.yml"
        cls.text = cls.path.read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.text)
        cls.steps = cls.workflow["jobs"]["sync"]["steps"]

    def test_runs_hourly_and_by_hand(self):
        triggers = self.workflow.get("on", self.workflow.get(True))
        self.assertEqual([item["cron"] for item in triggers["schedule"]], ["17 * * * *"])
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(self.workflow["permissions"], {"contents": "write", "actions": "write"})

    def test_runs_both_syncs_and_commits_only_changes(self):
        runs = [step.get("run", "") for step in self.steps]
        self.assertIn("python3 scripts/sync-media-diet.py", runs)
        self.assertIn("python3 scripts/sync-spotify.py", runs)
        commit = runs[-1]
        self.assertIn('if [ -n "$(git status --porcelain data/media-diet.json data/spotify.json)" ]; then', commit)
        self.assertIn("git add data/media-diet.json data/spotify.json", commit)
        self.assertLess(commit.index("git pull --rebase"), commit.index("git push"))
        self.assertIn("gh workflow run deploy.yml --ref main", commit)

    def test_spotify_secrets_reach_only_the_spotify_step(self):
        for step in self.steps:
            env = step.get("env") or {}
            if step.get("run") == "python3 scripts/sync-spotify.py":
                self.assertEqual(env, {name: "${{ secrets.%s }}" % name for name in ENV})
            else:
                self.assertFalse([name for name in env if name.startswith("SPOTIFY")], step.get("name"))
        self.assertNotIn("env", self.workflow)
        self.assertNotIn("env", self.workflow["jobs"]["sync"])

    def test_no_hardcoded_secrets(self):
        files = [self.path, ROOT / "scripts/sync-spotify.py", ROOT / "scripts/spotify-auth.py", ROOT / "data/spotify.json"]
        for path in files:
            text = path.read_text(encoding="utf-8")
            # Spotify ids and secrets are 32 hex characters; refresh tokens are long opaque strings
            self.assertNotRegex(text, r"\b[0-9a-f]{32}\b", path.name)
            self.assertNotRegex(text, r"\bAQ[A-Za-z0-9_-]{40,}", path.name)
            for line in text.splitlines():
                if re.search(r"SPOTIFY_(CLIENT_ID|CLIENT_SECRET|REFRESH_TOKEN)\s*[:=]", line) and path.suffix == ".yml":
                    self.assertRegex(line, r"\$\{\{ secrets\.SPOTIFY_[A-Z_]+ \}\}\s*$", line)

    def test_podcast_sync_no_longer_runs_the_media_diet(self):
        episodes = (ROOT / ".github/workflows/sync-episodes.yml").read_text(encoding="utf-8")
        self.assertNotIn("sync-media-diet.py", episodes)
        self.assertNotIn("sync-spotify.py", episodes)
        self.assertNotIn("data/media-diet.json", episodes)
        self.assertNotIn("SPOTIFY_REFRESH_TOKEN", episodes)


if __name__ == "__main__":
    unittest.main()
