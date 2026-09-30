from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "index.html").read_text(encoding="utf-8")


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.body_sections = []
        self.nav_links = []
        self.mobile_links = []
        self.ep_cover = None
        self._depth = 0
        self._in_nav_links = False
        self._in_mobile = False
        self._link = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "section" and attrs.get("id"):
            self.body_sections.append(attrs["id"])
        if tag == "div" and "nav-links" in classes:
            self._in_nav_links = True
        if tag == "div" and attrs.get("id") == "mobileMenu":
            self._in_mobile = True
        if tag == "a" and (self._in_nav_links or self._in_mobile):
            self._link = attrs.get("href")
            self._text = []
        if tag == "img" and attrs.get("id") == "ep-show-cover":
            self.ep_cover = attrs

    def handle_endtag(self, tag):
        if tag == "a" and self._link is not None:
            label = " ".join("".join(self._text).split())
            target = self.nav_links if self._in_nav_links else self.mobile_links
            target.append((self._link, label))
            self._link = None
        if tag == "div" and (self._in_nav_links or self._in_mobile) and self._link is None:
            self._in_nav_links = False
            self._in_mobile = False

    def handle_data(self, data):
        if self._link is not None:
            self._text.append(data)


class HomepageStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = _Collector()
        cls.page.feed(PAGE)

    def test_chapters_run_podcasts_photography_ai_then_brand_work(self):
        self.assertEqual(
            self.page.body_sections,
            [
                "hero",
                "about",
                "podcasts",
                "photography",
                "ai",
                "work",
                "projects",
                "media-diet",
                "in-the-works",
                "contact",
            ],
        )

    def test_desktop_nav_follows_the_new_order(self):
        self.assertEqual(
            self.page.nav_links,
            [
                ("#about", "About"),
                ("#podcasts", "Podcasts"),
                ("#photography", "Photography"),
                ("#ai", "AI"),
                ("#work", "Brand Work"),
                ("#projects", "Culture"),
                ("shop.html", "Shop"),
            ],
        )

    def test_mobile_menu_matches_nav_and_ends_with_contact(self):
        self.assertEqual(
            [href for href, _ in self.page.mobile_links],
            ["#about", "#podcasts", "#photography", "#ai", "#work", "#projects", "shop.html", "#contact"],
        )
        self.assertEqual(
            [label.split(" ", 1)[0] for _, label in self.page.mobile_links],
            ["01", "02", "03", "04", "05", "06", "07", "08"],
        )

    def test_collection_and_interviews_are_one_compact_band_after_media_diet(self):
        band = PAGE[PAGE.index('<section id="in-the-works"'):]
        band = band[: band.index("</section>")]
        self.assertIn('id="collection"', band)
        self.assertIn('id="interviews"', band)
        self.assertIn('href="shop.html"', band)
        self.assertIn('href="mailto:', band)
        self.assertNotIn("veil", PAGE)

    def test_eclectic_polymath_cover_can_load(self):
        cover = self.page.ep_cover
        self.assertIsNotNone(cover)
        # Chrome never fetches a lazy image that is display:none, which hid the cover.
        self.assertNotEqual(cover.get("loading"), "lazy")
        self.assertNotIn("display:none", (cover.get("style") or "").replace(" ", ""))
        self.assertIn('class="ep-fallback"', PAGE)

    def test_public_copy_has_no_internal_or_solo_notes(self):
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", PAGE, flags=re.S | re.I)
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text).lower()
        for phrase in ("solo", "no guests", "live catalog", "twice weekly", "newest first"):
            self.assertNotIn(phrase, text)

    def test_sites_chapter_is_past_tense(self):
        self.assertIn("Sites I've <span class=\"it\">Built</span>", PAGE)
        self.assertNotIn("Sites I <span", PAGE)


if __name__ == "__main__":
    unittest.main()
