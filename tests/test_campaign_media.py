"""Campaign films and stills: every case-study film must point at a real upload."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MEDIA_JS = (ROOT / "assets/media.js").read_text(encoding="utf-8")
PAGES = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "work").glob("work-*.html")}
HOME = (ROOT / "index.html").read_text(encoding="utf-8")

# IDs that never existed on YouTube (they showed "Video unavailable"). Never again.
DEAD_IDS = ("dMD94-fjyAQ", "l8RRLQiTEks", "9PhxP53igb4")


class CampaignMediaTests(unittest.TestCase):
    def test_dead_video_ids_are_gone(self):
        for name, html in list(PAGES.items()) + [("index.html", HOME)]:
            for dead in DEAD_IDS:
                self.assertNotIn(dead, html, f"{name} still uses {dead}")

    def test_shared_media_layer_plays_vimeo(self):
        self.assertIn(".mv-frame[data-vimeo]", MEDIA_JS)
        self.assertIn("https://player.vimeo.com/video/", MEDIA_JS)
        for name, html in PAGES.items():
            self.assertNotIn("function mvVimeo", html, f"{name} duplicates the Vimeo facade")

    def test_skin_obsessed_films_play_from_vimeo(self):
        sephora = PAGES["work-sephora.html"]
        self.assertIn('data-vimeo="1075746491"', sephora)  # Security
        self.assertIn('data-vimeo="1088246390"', sephora)  # The Hunt

    def test_mlb_page_shows_the_whole_campaign(self):
        mlb = PAGES["work-mlb.html"]
        films = set(re.findall(r'data-yt="([\w-]{11})"', mlb))
        self.assertTrue({"RuezgkQvkuQ", "ff0JRU0cFtM", "VRHr8IwbSMI"} <= films, films)

    def test_every_homepage_campaign_card_has_a_fallback_or_local_image(self):
        work = HOME[HOME.index('<section id="work"'):]
        work = work[: work.index("</section>")]
        for card in re.findall(r'<a href="(work/[^"]+)" class="plate\b(.*?)</a>', work, re.S):
            href, body = card
            img = re.search(r"<img [^>]*>", body)
            self.assertIsNotNone(img, href)
            tag = img.group(0)
            src = re.search(r' src="([^"]+)"', tag).group(1)
            self.assertTrue(not src.startswith("http") or "data-fallbacks=" in tag, f"{href} has one remote image and no fallback")


class CampaignChannelTests(unittest.TestCase):
    def test_every_case_page_maps_its_channels_and_culture(self):
        for name, html in PAGES.items():
            if name == "work-template.html":
                continue
            self.assertIn('href="../assets/channels.css"', html, name)
            self.assertIn('class="chm"', html, name)
            self.assertIn('class="culture-note', html, name)

    def test_channel_rows_cite_sources(self):
        for name, html in PAGES.items():
            self.assertGreater(html.count('class="chm-src"'), 0, name) if 'class="chm"' in html else None

    def test_homepage_cards_show_channels_and_culture(self):
        work = HOME[HOME.index('<section id="work"'):]
        work = work[: work.index("</section>")]
        for href, body in re.findall(r'<a href="(work/[^"]+)" class="plate\b(.*?)</a>', work, re.S):
            self.assertIn('class="plate-channels"', body, href)
            self.assertIn('class="plate-culture"', body, href)


if __name__ == "__main__":
    unittest.main()
