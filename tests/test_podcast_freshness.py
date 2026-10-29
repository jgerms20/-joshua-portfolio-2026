from dataclasses import dataclass
from datetime import date
from pathlib import Path
import unittest

from portfolio_quality.podcast_checks import parse_spotify_latest, probe_podcast_entries


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class FakeResponse:
    status_code: int
    text: str


def spotify_html(number=106, date_label="Today"):
    return f'''<div data-testid="episode-0">
        <div data-testid="episode-block-image"><img alt="#{number:03d} A current episode"></div>
        <a href="/episode/episode-id">Listen</a>
        <div><p>{date_label}</p><p data-testid="episode-progress-not-played"><span>38 min</span></p></div>
    </div>'''


def entry(**overrides):
    value = {
        "id": "eclectic-polymath-spotify",
        "page": "podcasts/podcast-eclectic-polymath.html",
        "kind": "spotify-show",
        "url": "https://open.spotify.com/show/example",
        "minimum_episode": 106,
        "max_age_days": 14,
    }
    value.update(overrides)
    return value


class PodcastFreshnessTests(unittest.TestCase):
    def test_parser_reads_latest_episode_number_title_link_and_date_label(self):
        latest = parse_spotify_latest(spotify_html())

        self.assertEqual(latest.number, 106)
        self.assertEqual(latest.title, "#106 A current episode")
        self.assertEqual(latest.episode_path, "/episode/episode-id")
        self.assertEqual(latest.date_label, "Today")

    def test_current_feed_returns_no_findings(self):
        findings = probe_podcast_entries(
            [entry()],
            fetch=lambda *_args, **_kwargs: FakeResponse(200, spotify_html()),
            today=date(2026, 8, 4),
        )

        self.assertEqual(findings, [])

    def test_regressed_episode_marker_is_broken(self):
        findings = probe_podcast_entries(
            [entry()],
            fetch=lambda *_args, **_kwargs: FakeResponse(200, spotify_html(number=105)),
            today=date(2026, 8, 4),
        )

        self.assertEqual(findings[0].severity, "broken")
        self.assertEqual(findings[0].code, "podcast-feed-regressed")

    def test_feed_older_than_threshold_is_broken(self):
        findings = probe_podcast_entries(
            [entry()],
            fetch=lambda *_args, **_kwargs: FakeResponse(200, spotify_html(date_label="Jul 1, 2026")),
            today=date(2026, 8, 4),
        )

        self.assertEqual(findings[0].severity, "broken")
        self.assertEqual(findings[0].code, "podcast-feed-stale")

    def test_eclectic_page_is_visitor_facing_with_live_player_and_no_fixed_counts(self):
        page = (ROOT / "podcasts/podcast-eclectic-polymath.html").read_text(encoding="utf-8")
        lowered = page.lower()

        # Joshua asked for the operational notes to come off the public page,
        # and for the show not to be framed as solo / no-guest.
        for internal_phrase in (
            "live catalog",
            "newest first",
            "twice weekly",
            "no guest",
            "no-guest",
            "live spotify feed",
            "appears here the moment it drops",
        ):
            self.assertNotIn(internal_phrase, lowered)
        self.assertNotRegex(lowered, r"\bsolo\b")

        # No hardcoded episode total anywhere on the page: Spotify's player is the catalog.
        self.assertNotIn('id="ep-count"', page)
        self.assertNotRegex(lowered, r"\b\d+\s+episodes\b")
        self.assertNotIn("open.spotify.com/embed/episode/", page)

        # The live show player and a plain Listen on Spotify link are both there,
        # so the page still works when the embed is blocked.
        self.assertIn('src="https://open.spotify.com/embed/show/3dlagzJ0jiWLTB9mF3y069', page)
        self.assertRegex(
            page,
            r'(?s)<a[^>]+href="https://open\.spotify\.com/show/3dlagzJ0jiWLTB9mF3y069"[^>]*>'
            r'(?:(?!</a>).)*Listen on Spotify(?:(?!</a>).)*</a>',
        )

        # Listeners can reach the rest of the site and the booking contact.
        self.assertIn('href="../index.html#contact"', page)
        self.assertIn('href="../photography/"', page)

        # The player is only revealed once Spotify has answered; an iframe
        # onload alone (which also fires for the browser's error page) must
        # never flip it to ready, including after "Try the player again".
        self.assertIn("reach === 'ok' && window.__epFrameLoaded", page)
        self.assertNotIn("forced", page)

    def test_eclectic_page_uses_local_cover_and_rotates_real_episode_titles(self):
        import html as html_lib
        import json
        import re

        page = (ROOT / "podcasts/podcast-eclectic-polymath.html").read_text(encoding="utf-8")
        cover = "photos/podcasts/eclectic-polymath-cover.jpg"
        self.assertTrue((ROOT / cover).is_file())

        # The real show cover is the hero img src (paints immediately), with the
        # designed sleeve kept underneath as the onerror fallback.
        hero = re.search(r'(?s)<div class="cover">(.*?)<div class="art"', page)
        self.assertIsNotNone(hero)
        self.assertRegex(hero.group(1), r'<img[^>]+src="\.\./' + re.escape(cover) + r'"[^>]*onerror=')
        self.assertIn(f'<meta property="og:image" content="https://joshuamgerman.com/{cover}">', page)
        self.assertIn(f'<meta name="twitter:image" content="https://joshuamgerman.com/{cover}">', page)
        # The Spotify oEmbed thumbnail is no longer used for the cover art.
        self.assertNotIn("thumbnail_url", page)
        self.assertNotIn("data-cover", page)

        # The rotator reads the episodes data client-side and never parses it as HTML.
        self.assertIn('data-src="../data/episodes/eclectic-polymath.json"', page)
        self.assertIn('aria-live="off"', page)
        self.assertIn("prefers-reduced-motion: reduce", page)
        self.assertNotIn("innerHTML", page)
        self.assertNotIn("insertAdjacentHTML", page)
        self.assertNotIn("document.write", page)

        # The static fallback titles are real: each one (and its link) exists in the data file.
        data = json.loads((ROOT / "data/episodes/eclectic-polymath.json").read_text(encoding="utf-8"))
        known = {}
        for ep in data["episodes"]:
            known.setdefault(re.sub(r"^#\d+\s*", "", ep["title"]).strip(), set()).add(ep["url"])
        block = re.search(r'(?s)<ul class="lately-list"[^>]*>(.*?)</ul>', page)
        self.assertIsNotNone(block)
        links = re.findall(r'(?s)<a class="lately-link" href="([^"]+)"[^>]*>(.*?)</a>', block.group(1))
        self.assertGreaterEqual(len(links), 4)
        self.assertLessEqual(len(links), 6)
        for href, inner in links:
            text = re.sub(r'<span class="sr-only">.*?</span>', "", inner)
            title = html_lib.unescape(re.sub(r"<[^>]+>", "", text)).strip()
            self.assertIn(title, known, title)
            self.assertIn(html_lib.unescape(href), known[title])
            self.assertNotRegex(title, r"^#\d+")
        self.assertEqual(block.group(1).count('target="_blank" rel="noopener"'), len(links))


if __name__ == "__main__":
    unittest.main()
