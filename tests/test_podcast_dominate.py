from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "podcasts/podcast-dominate.html"

SPOTIFY_SHOW = "https://open.spotify.com/show/3IiC15tFfb1rHoDm9R6Zxp"
APPLE_SHOW = "https://podcasts.apple.com/us/podcast/dominate-the-decade/id1517223875"


class DominatePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.lowered = cls.page.lower()

    def test_canonical_url(self):
        self.assertIn(
            '<link rel="canonical" href="https://joshuamgerman.com/podcasts/podcast-dominate.html">',
            self.page,
        )

    def test_no_internal_or_operational_copy(self):
        for phrase in (
            "checked weekly",
            "live catalog",
            "live spotify feed",
            "newest first",
            "appears here the moment it drops",
            "auto-updated",
            "updated automatically",
        ):
            self.assertNotIn(phrase, self.lowered)
        # No hardcoded episode totals or counts.
        self.assertNotRegex(self.lowered, r"\b\d+\s+(?:total\s+)?episodes\b")
        self.assertNotRegex(self.lowered, r"episodes\s*\(\d+")
        self.assertNotRegex(self.lowered, r"\d+\s+seasons?\b")

    def test_spotify_and_apple_links_present(self):
        self.assertRegex(
            self.page,
            r'(?s)<a[^>]+href="' + re.escape(SPOTIFY_SHOW) + r'"[^>]*>'
            r'(?:(?!</a>).)*Listen on Spotify(?:(?!</a>).)*</a>',
        )
        self.assertIn(f'href="{APPLE_SHOW}"', self.page)
        self.assertIn(
            'src="https://open.spotify.com/embed/show/3IiC15tFfb1rHoDm9R6Zxp', self.page
        )

    def test_external_links_open_safely(self):
        for tag in re.findall(r'<a\b[^>]*target="_blank"[^>]*>', self.page):
            self.assertIn('rel="noopener', tag)

    def test_episode_json_hook_present_and_safe(self):
        self.assertIn('data-episodes="../data/episodes/dominate.json"', self.page)
        # Latest list starts hidden and is only revealed once episodes render.
        self.assertRegex(self.page, r'<div class="latest" id="latest"[^>]*\bhidden\b')
        self.assertIn("box.hidden = false", self.page)
        self.assertIn("MAX = 6", self.page)
        # Feed data is written with textContent, never innerHTML.
        self.assertNotIn("innerHTML", self.page)
        self.assertIn(".textContent = text", self.page)

    def test_player_reachability_guard(self):
        self.assertIn("reach === 'ok' && window.__epFrameLoaded", self.page)
        self.assertIn('id="playerRetry"', self.page)

    def test_site_navigation_and_theme(self):
        self.assertIn('href="../index.html#contact"', self.page)
        self.assertIn('href="../photography/"', self.page)
        self.assertIn('href="podcast-eclectic-polymath.html"', self.page)
        self.assertIn('href="podcast-approachable-ai.html"', self.page)
        self.assertIn('href="podcast-curious-creative.html"', self.page)
        self.assertIn("'jmg-theme'", self.page)


if __name__ == "__main__":
    unittest.main()
