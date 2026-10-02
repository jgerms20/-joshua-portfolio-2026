from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "podcasts/podcast-curious-creative.html"
SHOW_SITE = "https://jgerms20.github.io/curious-and-creative/"


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link":
            self.links.append(attrs)
        if tag == "a":
            self.anchors.append(attrs)


class CuriousCreativePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.parsed = _Collector()
        cls.parsed.feed(cls.html)

    def test_canonical_url(self):
        canon = [l.get("href") for l in self.parsed.links if l.get("rel") == "canonical"]
        self.assertEqual(
            canon, ["https://joshuamgerman.com/podcasts/podcast-curious-creative.html"]
        )

    def test_spotify_only_appears_once_a_real_show_id_is_known(self):
        self.assertNotIn("your-show-id", self.html)
        # no hardcoded show link in the markup; the button is hidden until enabled
        self.assertNotRegex(self.html, r'href="https://open\.spotify\.com')
        self.assertRegex(self.html, r'data-spotify-link hidden')
        # the id comes from the page constant or the synced data (spotify_show)
        self.assertIn("enableSpotify(data.spotify_show)", self.html)
        self.assertIn("/^[A-Za-z0-9]{10,40}$/", self.html)

    def test_names_both_hosts(self):
        self.assertIn("Joshua McKenzie German &amp; Janelle", self.html)

    def test_no_internal_or_operational_copy(self):
        for pattern in (r"\bTODO\b", r"\bFIXME\b", r"\bTBD\b", r"placeholder", r"lorem ipsum"):
            self.assertIsNone(
                re.search(pattern, self.html, re.IGNORECASE), f"found {pattern!r}"
            )
        for comment in re.findall(r"<!--(.*?)-->", self.html, re.S):
            self.assertNotRegex(comment, r"(?i)todo|fixme|replace|once available")

    def test_fetches_generated_episodes_json(self):
        self.assertIn("'../data/episodes/curious-creative.json'", self.html)
        self.assertIn("MAX_EPISODES = 6", self.html)

    def test_feed_data_never_written_as_html(self):
        script = self.html.split("<script>")[-1]
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("insertAdjacentHTML", script)
        self.assertNotIn("document.write", script)

    def test_empty_state_copy_and_actions(self):
        self.assertIn('id="epEmpty"', self.html)
        self.assertIn("New conversations, <em>every drop.</em>", self.html)
        self.assertNotIn("dropping soon", self.html)
        self.assertIn("Visit the show site", self.html)
        self.assertIn("Suggest a guest", self.html)
        self.assertIn('href="mailto:jgerms20@gmail.com', self.html)
        self.assertIn(f'href="{SHOW_SITE}"', self.html)

    def test_external_links_open_safely(self):
        for a in self.parsed.anchors:
            if a.get("href", "").startswith("http"):
                self.assertEqual(a.get("target"), "_blank", a)
                self.assertIn("noopener", a.get("rel", ""), a)

    def test_shared_theme_and_site_links(self):
        self.assertIn("'jmg-theme'", self.html)
        hrefs = {a.get("href") for a in self.parsed.anchors}
        for href in (
            "../index.html#contact",
            "../photography/",
            "podcast-eclectic-polymath.html",
            "podcast-approachable-ai.html",
            "podcast-dominate.html",
        ):
            self.assertIn(href, hrefs)


if __name__ == "__main__":
    unittest.main()
