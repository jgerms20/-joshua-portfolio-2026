from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "podcasts/podcast-approachable-ai.html"

VIDEO_IDS = ("WTV1Wh3ltCI", "dQuwJuegV5A", "fodaQYQTrpg", "rD52xDVvjNQ", "z6j0RwKSllQ")


class ApproachableAiPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.lowered = cls.page.lower()

    def test_no_internal_or_operational_copy(self):
        for phrase in (
            "todo",
            "placeholder",
            "unreachable",
            "live catalog",
            "newest first",
            "twice weekly",
            "no guest",
            "no-guest",
            "appears here the moment it drops",
        ):
            self.assertNotIn(phrase, self.lowered, phrase)
        self.assertNotRegex(self.lowered, r"\bsolo\b")
        # No hardcoded episode total.
        self.assertNotRegex(self.lowered, r"\b\d+\s+episodes\b")

    def test_every_episode_is_a_click_to_play_facade(self):
        self.assertIn('href="../assets/media.css"', self.page)
        self.assertIn('src="../assets/media.js"', self.page)
        for vid in VIDEO_IDS:
            self.assertRegex(
                self.page,
                r'<div class="mv-frame" data-yt="%s" data-title="[^"]+"></div>' % re.escape(vid),
            )
        # No eager YouTube iframes: the player only loads on click.
        self.assertNotIn("youtube.com/embed/", self.page)
        self.assertNotRegex(self.lowered, r"<iframe")

    def test_canonical_and_shared_chrome(self):
        self.assertIn(
            '<link rel="canonical" href="https://joshuamgerman.com/podcasts/podcast-approachable-ai.html">',
            self.page,
        )
        self.assertIn("localStorage.getItem('jmg-theme')", self.page)
        self.assertIn('href="../index.html#contact"', self.page)
        self.assertIn('href="../photography/"', self.page)
        for show in ("podcast-eclectic-polymath.html", "podcast-curious-creative.html", "podcast-dominate.html"):
            self.assertIn('href="%s"' % show, self.page)
        self.assertIn("../photos/podcasts/approachable-ai-logo.jpg", self.page)

    def test_no_invented_listening_links(self):
        self.assertNotIn("open.spotify.com", self.page)
        self.assertNotIn("podcasts.apple.com", self.page)

    def test_latest_episodes_hook_reads_feed_safely(self):
        self.assertIn("fetch('../data/episodes/approachable-ai.json'", self.page)
        self.assertIn('id="fresh" hidden', self.page)
        self.assertIn(".slice(0, 6)", self.page)
        script = self.page.split('src="../assets/media.js"></script>', 1)[1]
        # Feed data is only ever written with textContent.
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("insertAdjacentHTML", script)
        self.assertNotIn("document.write", script)


if __name__ == "__main__":
    unittest.main()
