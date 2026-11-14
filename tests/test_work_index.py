"""Brand Work index (work/index.html): every brand campaign on one page, featured six first."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "work" / "index.html"

FEATURED = [
    "work-levis.html",
    "work-gatorade.html#stranger-things",
    "work-doordash.html",
    "work-directv.html#nothing-on-roof",
    "work-gatorade.html#body-of-science",
    "work-dwb.html",
]
STARTUPS = ["https://hiike.com/", "https://www.uandai.co/"]
AGENCIES = {"all", "tbwa", "wk", "gsp", "independent"}


def _local(page_dir: Path, url: str) -> Path | None:
    parts = urlsplit(url)
    if parts.scheme or url.startswith(("//", "#", "yt:", "data:")):
        return None
    path = unquote(parts.path)
    return (page_dir / path) if path else None


class WorkIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.soup = BeautifulSoup(cls.html, "lxml")
        cls.cards = cls.soup.select("#work a.plate")

    def test_page_head(self):
        head = self.soup.head
        self.assertEqual(self.soup.title.get_text(), "Brand Work | Joshua McKenzie German")
        self.assertTrue(head.find("meta", attrs={"name": "description"})["content"].strip())
        self.assertEqual(head.find("link", rel="canonical")["href"], "https://joshuamgerman.com/work/")
        self.assertEqual(head.find("meta", property="og:url")["content"], "https://joshuamgerman.com/work/")
        self.assertIsNotNone(head.find("link", rel="manifest", href="../site.webmanifest"))
        self.assertIn("jmg-theme", " ".join(s.get_text() for s in head.find_all("script")))
        self.assertIn('href="../assets/media.css"', self.html)
        self.assertIn('src="../assets/media.js"', self.html)

    def test_nav_and_footer(self):
        back = self.soup.select_one(".nav-links a")
        self.assertEqual(back["href"], "../index.html")
        self.assertIn("Home", back.get_text())
        self.assertIsNotNone(self.soup.find(id="themeToggle"))
        self.assertEqual(self.soup.select_one(".nav-cta")["href"], "../index.html#contact")
        self.assertIsNotNone(self.soup.select_one("footer .footer-links"))

    def test_has_all_21_cards(self):
        self.assertEqual(len(self.cards), 21)
        hrefs = [a["href"] for a in self.cards]
        self.assertEqual(len(set(hrefs)), 21, "a campaign appears twice")

    def test_featured_six_then_startups_first(self):
        hrefs = [a["href"] for a in self.cards]
        self.assertEqual(hrefs[:6], FEATURED)
        self.assertEqual(hrefs[6:8], STARTUPS)
        for card in self.cards[6:8]:
            self.assertIn("plate-startup", card["class"])
            self.assertEqual(card["data-agency"], "independent")

    def test_filters_present_and_cover_every_card(self):
        buttons = self.soup.select("#campFilters .camp-filter")
        self.assertEqual({b["data-agency"] for b in buttons}, AGENCIES)
        for card in self.cards:
            self.assertIn(card.get("data-agency"), AGENCIES - {"all"}, card["href"])

    def test_every_card_has_an_image_or_brand_tile(self):
        for card in self.cards:
            media = card.select_one(".plate-media")
            self.assertIsNotNone(media, card["href"])
            img = media.find("img")
            tile = media.select_one(".plate-media-brand")
            self.assertTrue(img is not None or tile is not None, card["href"])
            if img is not None and tile is None:
                self.assertTrue(img.get("alt", "").strip(), card["href"])
                src = img["src"]
                self.assertTrue(not src.startswith("http") or img.get("data-fallbacks"),
                                f"{card['href']} has one remote image and no fallback")

    def test_agency_cards_show_a_year(self):
        for card in self.cards[:6] + self.cards[8:]:
            year = card.select_one(".plate-year")
            self.assertIsNotNone(year, card["href"])
            self.assertRegex(year.get_text(), r"^20\d\d(–20\d\d)?$")

    def test_links_and_images_resolve(self):
        page_dir = PAGE.parent
        for tag in self.soup.find_all(["a", "img", "link", "script"]):
            for attr in ("href", "src"):
                if not tag.get(attr):
                    continue
                path = _local(page_dir, tag[attr])
                if path is not None:
                    self.assertTrue(path.exists(), f"{attr}={tag[attr]}")
            for token in tag.get("data-fallbacks", "").split():
                path = _local(page_dir, token)
                if path is not None:
                    self.assertTrue(path.exists(), f"data-fallbacks {token}")

    def test_case_page_anchors_exist(self):
        for card in self.cards:
            href = card["href"]
            if "#" not in href or href.startswith("http"):
                continue
            name, frag = href.split("#", 1)
            self.assertIn(f'id="{frag}"', (PAGE.parent / name).read_text(encoding="utf-8"), href)

    def test_case_pages_link_back_here(self):
        for page in sorted(PAGE.parent.glob("work-*.html")):
            if page.name == "work-template.html":
                continue
            html = page.read_text(encoding="utf-8")
            self.assertNotIn("../index.html#work", html, page.name)
            soup = BeautifulSoup(html, "lxml")
            self.assertEqual(soup.select_one(".nav-links a")["href"], "./", page.name)

    def test_is_a_production_page(self):
        from portfolio_quality.pages import discover_production_pages

        found = {p.relative_to(ROOT).as_posix() for p in discover_production_pages(ROOT)}
        self.assertIn("work/index.html", found)


if __name__ == "__main__":
    unittest.main()
