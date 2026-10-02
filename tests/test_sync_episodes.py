import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_episodes", ROOT / "scripts/sync-episodes.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <title>Sample Show</title>
  <itunes:image href="https://example.com/show.jpg"/>
  <item>
    <title>Older episode</title>
    <pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate>
    <link>https://example.com/ep1</link>
    <description>&lt;p&gt;First &lt;b&gt;one&lt;/b&gt;.&lt;/p&gt;</description>
    <itunes:duration>1:05:00</itunes:duration>
  </item>
  <item>
    <title>Newest episode</title>
    <pubDate>Tue, 15 Sep 2026 10:00:00 GMT</pubDate>
    <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg"/>
    <itunes:summary>Second.</itunes:summary>
    <itunes:image href="https://example.com/ep2.jpg"/>
    <itunes:duration>2400</itunes:duration>
  </item>
  <item><title></title></item>
</channel>
</rss>"""


class SyncEpisodesTests(unittest.TestCase):
    def test_parses_newest_first_with_clean_fields(self):
        episodes = sync.parse_feed(FEED)

        self.assertEqual([e["title"] for e in episodes], ["Newest episode", "Older episode"])
        newest, older = episodes
        self.assertEqual(newest["date"], "2026-09-15")
        self.assertEqual(newest["url"], "https://example.com/ep2.mp3")
        self.assertEqual(newest["image"], "https://example.com/ep2.jpg")
        self.assertEqual(newest["duration"], "40 min")
        self.assertEqual(older["description"], "First one .")
        self.assertEqual(older["image"], "https://example.com/show.jpg")
        self.assertEqual(older["duration"], "1 hr 5 min")

    def test_writes_only_when_episodes_change(self):
        episodes = sync.parse_feed(FEED)
        with mock.patch.object(sync, "OUT_DIR", Path(self.tmp.name)):
            self.assertTrue(sync.write_show("sample", "https://example.com/feed", episodes))
            self.assertFalse(sync.write_show("sample", "https://example.com/feed", episodes))
            data = json.loads((Path(self.tmp.name) / "sample.json").read_text())
        self.assertEqual(data["show"], "sample")
        self.assertEqual(len(data["episodes"]), 2)

    def test_parses_spotify_api_episodes(self):
        payload = {"items": [
            None,
            {"name": "Pilot", "release_date": "2026-09-20", "duration_ms": 2_700_000,
             "description": "First <b>one</b>", "external_urls": {"spotify": "https://open.spotify.com/episode/abc"},
             "images": [{"url": "https://i.scdn.co/small", "width": 64}, {"url": "https://i.scdn.co/big", "width": 640}]},
        ]}
        [episode] = sync.parse_spotify(payload)
        self.assertEqual(episode["title"], "Pilot")
        self.assertEqual(episode["url"], "https://open.spotify.com/episode/abc")
        self.assertEqual(episode["image"], "https://i.scdn.co/big")
        self.assertEqual(episode["duration"], "45 min")
        self.assertEqual(episode["description"], "First one")

    def test_spotify_needs_credentials_from_the_environment(self):
        with mock.patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "", "SPOTIFY_CLIENT_SECRET": ""}):
            with self.assertRaises(RuntimeError):
                sync.spotify_episodes("anything")

    def test_one_spotify_episode_is_enough_to_find_the_show(self):
        with mock.patch.object(sync, "spotify_token", return_value="t"), \
             mock.patch.object(sync, "spotify_get", return_value={"show": {"id": "SHOW123"}}) as get:
            self.assertEqual(sync.spotify_show_for_episode("EP1"), "SHOW123")
        self.assertIn("episodes/EP1", get.call_args[0][0])

    def test_every_show_in_config_has_a_slug_matching_a_podcast_page(self):
        shows = json.loads((ROOT / "data/podcast-feeds.json").read_text())["shows"]
        for show in shows:
            self.assertTrue((ROOT / f"podcasts/podcast-{show['slug']}.html").is_file(), show["slug"])

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
