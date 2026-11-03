from pathlib import Path
import re
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "media-diet/index.html"


class MediaDietPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.soup = BeautifulSoup(cls.html, "html.parser")
        cls.script = "\n".join(s.get_text() for s in cls.soup.find_all("script") if not s.get("type"))

    def test_three_tabs_watching_reading_listening(self):
        tabs = self.soup.select('[role="tablist"] [role="tab"]')
        self.assertEqual([t["data-tab"] for t in tabs], ["watching", "reading", "listening"])
        self.assertEqual(tabs[0]["aria-selected"], "true")
        self.assertIsNotNone(self.soup.find(attrs={"role": "tabpanel"}))
        self.assertNotIn("substack", self.html.lower())

    def test_hash_routed_with_watching_as_default(self):
        self.assertIn("location.hash", self.script)
        self.assertIn("hashchange", self.script)
        self.assertRegex(self.script, r"SHELVES\[h\] \? h : 'watching'")

    def test_fetches_both_data_files(self):
        self.assertIn("'../data/media-diet.json'", self.script)
        self.assertIn("'../data/listening.json'", self.script)
        self.assertTrue((ROOT / "data/media-diet.json").exists())
        self.assertTrue((ROOT / "data/listening.json").exists())

    def test_sort_filter_search_and_pages(self):
        for control in ("q", "sort", "fRating", "fDecade", "chips", "pager"):
            self.assertIsNotNone(self.soup.find(id=control), control)
        self.assertIn("PER_PAGE = 24", self.script)
        for sort in ("'new'", "'old'", "'rated'", "'title'"):
            self.assertIn(sort, self.script)

    def test_data_is_rendered_as_text_never_html(self):
        self.assertNotRegex(self.script, r"\.(innerHTML|outerHTML)\s*=")
        self.assertNotIn("insertAdjacentHTML", self.script)
        self.assertNotIn("document.write", self.script)
        self.assertIn("textContent", self.script)
        # links and images are https-only
        self.assertIn("function https(u)", self.script)
        self.assertIn("/^https:\\/\\/", self.script)

    def test_broken_images_fall_back_to_a_tile(self):
        self.assertRegex(self.script, r"addEventListener\('error', function \(\) \{ img\.replaceWith")

    def test_empty_states_link_out(self):
        reading = self.soup.find("template", id="empty-reading")
        self.assertIn("https://www.goodreads.com/user/show/95365432-joshua-german", str(reading))
        watching = self.soup.find("template", id="empty-watching")
        self.assertIn("https://letterboxd.com/jgerms/", str(watching))
        listening = self.soup.find("template", id="empty-listening")
        self.assertIn("coming soon", listening.get_text().lower())

    def test_meta_canonical_and_back_link(self):
        canonical = self.soup.find("link", rel="canonical")
        self.assertEqual(canonical["href"], "https://joshuamgerman.com/media-diet/")
        self.assertEqual(self.soup.find("meta", property="og:url")["content"], "https://joshuamgerman.com/media-diet/")
        for prop in ("og:title", "og:description", "og:image"):
            self.assertTrue(self.soup.find("meta", property=prop)["content"], prop)
        self.assertIsNotNone(self.soup.find("a", href="../index.html#media-diet"))
        self.assertEqual(self.soup.title.get_text(strip=True), "Media Diet | Joshua McKenzie German")

    def test_shares_the_site_theme(self):
        self.assertIn("localStorage.getItem('jmg-theme')", self.html)
        self.assertIn(':root[data-theme="dark"]', self.html)
        self.assertIsNotNone(self.soup.find(id="themeToggle"))

    def test_external_links_open_safely(self):
        for a in self.soup.find_all("a", target="_blank"):
            self.assertIn("noopener", a.get("rel", []), a.get("href"))
        self.assertIn("a.rel = 'noopener'", self.script)

    def test_listed_in_the_ref_checker_and_smoke_test(self):
        self.assertIn("'media-diet/index.html'", (ROOT / "scripts/check-refs.py").read_text())
        self.assertRegex((ROOT / "tests/browser/smoke.js").read_text(), r"PAGES = \[[^\]]*'media-diet/'")


if __name__ == "__main__":
    unittest.main()
