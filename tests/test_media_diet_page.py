from pathlib import Path
import json
import re
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "media-diet/index.html"
JS = ROOT / "assets/media-diet.js"
CSS = ROOT / "assets/media-diet.css"
PARTIAL = ROOT / "partials/media-diet-section.html"

LETTERBOXD = "https://letterboxd.com/jgerms/"
GOODREADS = "https://www.goodreads.com/user/show/95365432-joshua-german"


class MediaDietComponentTests(unittest.TestCase):
    """assets/media-diet.js + .css: the shelf, mountable anywhere."""

    @classmethod
    def setUpClass(cls):
        cls.js = JS.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")

    def test_assets_exist(self):
        self.assertTrue(JS.is_file())
        self.assertTrue(CSS.is_file())

    def test_mounts_every_md_app(self):
        self.assertIn("document.querySelectorAll('.md-app')", self.js)
        for attr in ("data-root", "data-hash-prefix", "data-per-page", "data-pager", "data-heading-level"):
            self.assertIn(attr, self.js, attr)

    def test_three_shelves_watching_reading_listening(self):
        self.assertIn("var ORDER = ['watching', 'reading', 'listening'];", self.js)
        self.assertIn("setAttribute('role', 'tablist')", self.js)
        self.assertIn("setAttribute('role', 'tabpanel')", self.js)
        self.assertNotIn("substack", self.js.lower())

    def test_listening_covers_podcasts_episodes_and_articles(self):
        for t in ("podcast", "episode", "article"):
            self.assertRegex(self.js, rf"\b{t}: \['")
        self.assertIn("Podcasts, episodes and articles", self.js)

    def test_fetches_both_data_files_relative_to_the_root(self):
        self.assertIn("root + 'data/media-diet.json'", self.js)
        self.assertIn("root + 'data/listening.json'", self.js)
        # data-root can only be a plain relative/root path, never another origin
        self.assertIn("function safeRoot(v)", self.js)
        self.assertTrue((ROOT / "data/media-diet.json").exists())
        self.assertTrue((ROOT / "data/listening.json").exists())

    def test_hash_routing_is_opt_in_and_prefixed(self):
        self.assertIn("location.hash", self.js)
        self.assertIn("hashchange", self.js)
        self.assertIn("if (opt.prefix === null) return null;", self.js)
        # an embedded shelf rewrites the URL in place instead of stacking history entries
        self.assertIn("'replaceState' : 'pushState'", self.js)

    def test_sort_filter_search_and_pages(self):
        for sort in ("'new'", "'old'", "'rated'", "'title'", "'release'"):
            self.assertIn(sort, self.js)
        for piece in ("q.type = 'search'", "md-chips", "selBox('Rating'", "selBox('Decade'", "selBox('Sort'", "md-pager"):
            self.assertIn(piece, self.js, piece)
        self.assertIn("parseInt(app.getAttribute('data-per-page'), 10) || 24", self.js)

    def test_data_is_rendered_as_text_never_html(self):
        self.assertNotRegex(self.js, r"\.(innerHTML|outerHTML)\s*=")
        self.assertNotIn("insertAdjacentHTML", self.js)
        self.assertNotIn("document.write", self.js)
        self.assertNotIn("eval(", self.js)
        self.assertIn("textContent", self.js)
        # links and images are https-only
        self.assertIn("function https(u)", self.js)
        self.assertIn("/^https:\\/\\/", self.js)

    def test_broken_images_fall_back_to_a_tile(self):
        self.assertRegex(self.js, r"addEventListener\('error', function \(\) \{ img\.replaceWith")

    def test_empty_states_link_out(self):
        self.assertIn(f"var LETTERBOXD = '{LETTERBOXD}';", self.js)
        self.assertIn(f"var GOODREADS = '{GOODREADS}';", self.js)
        self.assertIn("cta: ['See my Letterboxd diary', LETTERBOXD]", self.js)
        self.assertIn("cta: ['See my Goodreads shelves', GOODREADS]", self.js)
        self.assertIn("coming soon.", self.js)

    def test_external_links_open_safely(self):
        self.assertIn("a.rel = 'noopener'", self.js)

    def test_styles_are_scoped_and_themed(self):
        selectors = re.findall(r"(?m)^([^@\s/{}][^{]*)\{", self.css)
        for sel in selectors:
            for part in re.split(r",(?![^(]*\))", sel):  # commas outside :where(...)
                part = part.strip()
                if part.startswith(("from", "to")):
                    continue
                self.assertRegex(part, r"(\.md-|:root\[data-theme=\"dark\"\] \.md-)", part)
        self.assertIn(':root[data-theme="dark"] .md-app', self.css)
        self.assertIn(".md-app [hidden] { display: none !important; }", self.css)


class MediaDietPageTests(unittest.TestCase):
    """media-diet/index.html: the standalone page, now a host for the component."""

    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.soup = BeautifulSoup(cls.html, "html.parser")
        cls.script = "\n".join(s.get_text() for s in cls.soup.find_all("script") if not s.get("type"))

    def test_uses_the_component(self):
        self.assertIsNotNone(self.soup.find("link", rel="stylesheet", href="../assets/media-diet.css"))
        self.assertIsNotNone(self.soup.find("script", src="../assets/media-diet.js"))
        app = self.soup.select_one(".md-app")
        self.assertIsNotNone(app)
        self.assertEqual(app["data-root"], "../")
        # the standalone page owns its hash: #watching / #reading / #listening
        self.assertEqual(app["data-hash-prefix"], "")
        self.assertEqual(app["data-per-page"], "24")
        self.assertEqual(app["data-stack"], "#stack")
        self.assertIsNotNone(self.soup.select_one(app["data-stack"]))
        self.assertIsNotNone(self.soup.select_one(app["data-synced"]))

    def test_no_leftover_inline_shelf(self):
        self.assertNotIn("function render(", self.script)
        self.assertIsNone(self.soup.find("template"))
        self.assertNotRegex(self.script, r"\.(innerHTML|outerHTML)\s*=")

    def test_noscript_links_out(self):
        fallback = self.soup.select_one(".md-app noscript")
        self.assertIsNotNone(fallback)
        self.assertIn(LETTERBOXD, str(fallback))
        self.assertIn(GOODREADS, str(fallback))

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

    def test_listed_in_the_ref_checker_and_smoke_test(self):
        self.assertIn("'media-diet/index.html'", (ROOT / "scripts/check-refs.py").read_text())
        self.assertRegex((ROOT / "tests/browser/smoke.js").read_text(), r"PAGES = \[[^\]]*'media-diet/'")


class MediaDietHomepagePartialTests(unittest.TestCase):
    """partials/media-diet-section.html: the homepage chapter that embeds the shelf."""

    @classmethod
    def setUpClass(cls):
        cls.html = PARTIAL.read_text(encoding="utf-8")
        cls.soup = BeautifulSoup(cls.html, "html.parser")

    def test_is_the_media_diet_chapter(self):
        section = self.soup.find("section")
        self.assertEqual(section["id"], "media-diet")
        self.assertIn("chapter", section["class"])
        self.assertEqual(self.soup.select_one(".ch-head .ch-num").get_text(strip=True), "CH. 06")
        self.assertEqual(self.soup.select_one(".ch-head .ch-title").get_text(" ", strip=True), "Media Diet")
        self.assertIn("What a curious, creative", self.soup.select_one(".ch-meta").get_text())
        self.assertTrue(self.soup.select_one(".ch-intro").get_text(strip=True))

    def test_mounts_the_component_without_taking_over_the_hash(self):
        app = self.soup.select_one("#media-diet .md-app")
        self.assertIsNotNone(app)
        self.assertEqual(app["data-root"], "./")
        self.assertTrue(app["data-hash-prefix"])  # e.g. #md-reading, never a bare #reading
        self.assertEqual(app["data-per-page"], "12")

    def test_also_links(self):
        also = [p for p in self.soup.find_all("p", class_="md-also") if p.parent.name != "noscript"][0]
        hrefs = [a["href"] for a in also.find_all("a")]
        self.assertEqual(hrefs, [
            LETTERBOXD,
            GOODREADS,
            "https://www.chess.com/member/jgerms",
            "https://jgerms20.substack.com",
        ])
        for a in also.find_all("a"):
            self.assertEqual(a.get("target"), "_blank")
            self.assertIn("noopener", a.get("rel", []))

    def test_no_ids_beyond_the_section(self):
        ids = [t["id"] for t in self.soup.find_all(attrs={"id": True})]
        self.assertEqual(ids, ["media-diet"])

    def test_no_inline_script(self):
        self.assertIsNone(self.soup.find("script"))


class ListeningArticlesTests(unittest.TestCase):
    def test_articles_are_on_the_listening_shelf(self):
        items = json.loads((ROOT / "data/listening.json").read_text(encoding="utf-8"))["items"]
        articles = [i for i in items if i["type"] == "article"]
        self.assertGreaterEqual(len(articles), 3)
        for a in articles:
            self.assertTrue(a["url"].startswith("https://"), a["url"])
            self.assertTrue(a["creator"])


if __name__ == "__main__":
    unittest.main()
