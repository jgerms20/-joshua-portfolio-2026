from pathlib import Path
import json
import re
import shutil
import subprocess
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "media-diet/index.html"
JS = ROOT / "assets/media-diet.js"
CSS = ROOT / "assets/media-diet.css"
HOME = ROOT / "index.html"

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

    def test_articles_are_read_and_episodes_are_listened_to(self):
        for t in ("podcast", "episode", "article"):
            self.assertRegex(self.js, rf"\b{t}: \['")
        # articles sit on the Reading shelf with the books; Listening is audio only
        self.assertIn("Books on the nightstand and articles worth passing on.", self.js)
        self.assertIn("Podcasts and episodes I keep bringing up", self.js)
        self.assertIn("i.type === 'article'", self.js)
        self.assertIn("i.type !== 'article'", self.js)
        self.assertIn("function articleCard", self.js)

    def test_fetches_both_data_files_relative_to_the_root(self):
        self.assertIn("root + 'data/media-diet.json'", self.js)
        self.assertIn("root + 'data/listening.json'", self.js)
        # data-root can only be a plain relative/root path, never another origin
        self.assertIn("function safeRoot(v)", self.js)
        self.assertIn("root + 'data/watching.json'", self.js)
        self.assertIn("root + 'data/spotify.json'", self.js)
        # every file the shelf asks for is committed, so the page never 404s
        for name in ("media-diet", "listening", "watching", "spotify"):
            self.assertTrue((ROOT / f"data/{name}.json").exists(), name)

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


class MediaDietHomepageTests(unittest.TestCase):
    """index.html#media-diet: the homepage chapter embeds the full shelf, not a teaser."""

    @classmethod
    def setUpClass(cls):
        page = HOME.read_text(encoding="utf-8")
        cls.page = page
        start = page.index('<section id="media-diet"')
        cls.html = page[start: page.index("</section>", start) + len("</section>")]
        cls.soup = BeautifulSoup(cls.html, "html.parser")

    def test_homepage_loads_the_component(self):
        self.assertIn('<link rel="stylesheet" href="assets/media-diet.css">', self.page)
        self.assertIn('<script src="assets/media-diet.js" defer></script>', self.page)
        self.assertNotIn('id="intake"', self.page)  # the old three-column teaser is gone

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
            # a publish date, or just the month when the day isn't known; never a made-up day
            self.assertRegex(a["date"], r"^\d{4}-\d{2}(-\d{2})?$")
        graeber = next(a for a in articles if "bullshit-jobs" in a["url"])
        self.assertEqual(graeber["date"], "2013-08")

    def test_month_only_dates_are_supported(self):
        js = (ROOT / "assets/media-diet.js").read_text(encoding="utf-8")
        self.assertIn("/^\\d{4}-\\d{2}$/", js)


NODE = shutil.which("node")


def run_shelf(script: str):
    """Run a snippet against the component's data-only helpers (no DOM) and return its JSON."""
    code = "const md = require(process.argv[1]);\nconst out = (() => {" + script + "})();\nconsole.log(JSON.stringify(out));"
    done = subprocess.run([NODE, "-e", code, str(JS)], capture_output=True, text=True, timeout=60, cwd=ROOT)
    if done.returncode:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout)


DIET = {
    "letterboxd": [
        {"title": "Film A", "year": "2025", "watched": "2026-11-12", "url": "https://letterboxd.com/x/film/a/"},
        {"title": "Film B", "year": "1999", "watched": "2026-10-30", "rewatch": True, "url": "https://letterboxd.com/x/film/b/"},
        {"title": "Film C", "year": "1999", "watched": "2026-06-01", "url": "https://letterboxd.com/x/film/c/"},
    ],
    "reading": [{"title": "Book Now", "author": "A", "date": "2026-11-01", "url": "https://www.goodreads.com/book/show/1"}],
    "read": [{"title": "Book Done", "author": "B", "date": "2026-09-20", "url": "https://www.goodreads.com/book/show/2"}],
    "updated": "2026-11-17T00:00:00Z",
}
LISTEN = {"items": [
    {"type": "article", "title": "Essay", "creator": "W · Mag", "url": "https://example.org/essay", "date": "2026-11-10"},
    {"type": "article", "title": "Old essay", "creator": "W · Mag", "url": "https://example.org/old", "date": "2013-08"},
    {"type": "episode", "title": "Picked episode", "creator": "A Show", "url": "https://open.spotify.com/episode/e1?si=abc", "date": "2026-11-05", "note": "Mine."},
    {"type": "podcast", "title": "No link show", "creator": "Host", "date": "2026-01-02"},
]}
WATCH = {"items": [
    {"type": "tv", "title": "Show A", "season": 2, "date": "2026-11-15", "url": "https://example.org/show-a"},
    {"type": "tv", "title": "Show B", "season": "Limited series", "date": "2026-05", "url": "http://insecure.example/show-b"},
    {"type": "film", "title": "Not TV", "date": "2026-11-16"},
    {"type": "tv", "title": "", "date": "2026-11-16"},
]}
SPOTIFY = {
    "albums": [{"title": "Album A", "artist": "Artist", "image": "https://i.scdn.co/a", "url": "https://open.spotify.com/album/a1", "added": "2026-11-14"}],
    "shows": [{"title": "Saved show", "publisher": "Pub", "image": "", "url": "https://open.spotify.com/show/s1", "added": "2026-08-01"}],
    "episodes": [
        {"title": "Picked episode (Spotify copy)", "show": "A Show", "image": "", "url": "https://open.spotify.com/episode/e1", "added": "2026-11-06"},
        {"title": "Saved episode", "show": "B Show", "image": "", "url": "https://open.spotify.com/episode/e2", "added": "2026-11-16"},
        {"title": "Bad link", "show": "B Show", "image": "", "url": "javascript:alert(1)", "added": "2026-11-16"},
    ],
    "updated": "2026-11-17T00:00:00Z",
}
FIXTURES = "const [diet, listen, watch, spot] = " + json.dumps([DIET, LISTEN, WATCH, SPOTIFY]) + ";\n"


@unittest.skipUnless(NODE, "node is not installed")
class ShelfDataTests(unittest.TestCase):
    """The data-only half of assets/media-diet.js, run in node with fixture data."""

    @classmethod
    def setUpClass(cls):
        cls.shelves = run_shelf(FIXTURES + "return md.buildShelves(diet, listen, watch, spot);")

    def chips(self, diet=DIET, listen=LISTEN, watch=WATCH, spot=SPOTIFY):
        return run_shelf(
            "const [diet, listen, watch, spot] = " + json.dumps([diet, listen, watch, spot]) + ";"
            "const s = md.buildShelves(diet, listen, watch, spot);"
            "return Object.fromEntries(['watching', 'reading', 'listening'].map(k => [k, md.chipList(k, s[k])]));"
        )

    def summary(self, key, today="2026-11-17", **files):
        data = {"diet": DIET, "listen": LISTEN, "watch": WATCH, "spot": SPOTIFY, **files}
        return run_shelf(
            "const d = " + json.dumps(data) + ";"
            "const s = md.buildShelves(d.diet, d.listen, d.watch, d.spot);"
            f"return md.summaryLine({json.dumps(key)}, s[{json.dumps(key)}], {json.dumps(today)});"
        )

    # ---- films in the order Joshua rated them ----
    def test_rated_order_beats_the_watched_date(self):
        diet = {"letterboxd": [
            {"title": "Diary film", "watched": "2026-08-31", "rated_rank": 2, "url": "https://letterboxd.com/x/film/d/"},
            {"title": "Rated last", "rated_rank": 0, "url": "https://letterboxd.com/x/film/r0/"},
            {"title": "Rated before", "rated_rank": 1, "url": "https://letterboxd.com/x/film/r1/"},
            {"title": "Never rated", "watched": "2026-09-01", "url": "https://letterboxd.com/x/film/n/"},
        ]}
        shelves = run_shelf("const d = " + json.dumps(diet) + "; return md.buildShelves(d, {}, {}, {});")
        self.assertEqual([i["rank"] for i in shelves["watching"]], [2, 0, 1, None])
        # no rating date exists, so the latest line names the film without a date
        self.assertEqual(self.summary("watching", diet=diet, watch={"items": []}), "Latest: Rated last")
        js = JS.read_text(encoding="utf-8")
        self.assertIn("'new': byRecent", js)
        self.assertIn("['new', newestLabel(key, list)]", js)

    def test_sort_label_matches_the_order_it_shows(self):
        def label(key, diet):
            return run_shelf("const d = " + json.dumps(diet) + "; const s = md.buildShelves(d, {}, {}, {});"
                             f"return md.newestLabel({json.dumps(key)}, s[{json.dumps(key)}]);")
        ranked = {"letterboxd": [{"title": "A", "rated_rank": 0}, {"title": "B", "watched": "2026-08-31"}]}
        diary = {"letterboxd": [{"title": "A", "watched": "2026-08-31"}, {"title": "B", "watched": "2026-07-28"}]}
        self.assertEqual(label("watching", ranked), "Recently rated")
        self.assertEqual(label("watching", diary), "Recently watched")  # diary order: never claim "rated"
        self.assertEqual(label("reading", diary), "Newest")

    # ---- TV by hand ----
    def test_tv_merges_into_watching(self):
        watching = self.shelves["watching"]
        self.assertEqual([i["title"] for i in watching if i["kind"] == "tv"], ["Show A", "Show B"])
        self.assertEqual(len([i for i in watching if i["kind"] == "film"]), 3)
        show_a, show_b = [i for i in watching if i["kind"] == "tv"]
        self.assertEqual(show_a["season"], "Season 2")
        self.assertEqual(show_b["season"], "Limited series")
        self.assertEqual(show_b["date"], "2026-05")
        self.assertEqual(show_b["url"], "")  # http links are dropped

    def test_missing_or_empty_files_are_fine(self):
        for watch, spot in (({}, {}), ({"items": []}, {"albums": [], "shows": [], "episodes": []}), (None, None), ([], "x")):
            shelves = run_shelf(f"return md.buildShelves({json.dumps(DIET)}, {json.dumps(LISTEN)}, {json.dumps(watch)}, {json.dumps(spot)});")
            self.assertEqual(len(shelves["watching"]), 3)
            self.assertEqual(len(shelves["listening"]), 2)
        empty = run_shelf("return md.buildShelves(null, null, null, null);")
        self.assertEqual([empty[k] for k in ("watching", "reading", "listening")], [[], [], []])

    # ---- Spotify merges into Listening ----
    def test_spotify_merges_into_listening_deduped_by_url(self):
        listening = self.shelves["listening"]
        titles = [i["title"] for i in listening]
        # the hand pick wins over Spotify's copy of the same link (?si= share tags ignored)
        self.assertIn("Picked episode", titles)
        self.assertNotIn("Picked episode (Spotify copy)", titles)
        self.assertEqual(len(titles), len(set(titles)))
        by_title = {i["title"]: i for i in listening}
        self.assertEqual(by_title["Album A"]["type"], "album")
        self.assertEqual(by_title["Album A"]["creator"], "Artist")
        self.assertEqual(by_title["Album A"]["date"], "2026-11-14")
        self.assertEqual(by_title["Saved show"]["type"], "podcast")
        self.assertEqual(by_title["Saved episode"]["type"], "episode")
        self.assertEqual(by_title["Saved episode"]["creator"], "B Show")
        self.assertEqual(by_title["Bad link"]["url"], "")
        self.assertFalse(any(i["type"] == "article" for i in listening))

    # ---- Type chips ----
    def test_type_chips_on_every_shelf(self):
        chips = self.chips()
        self.assertEqual(chips["watching"], [["all", "All", 5], ["films", "Films", 3], ["tv", "TV", 2], ["first", "First watch", 2], ["rewatch", "Rewatches", 1]])
        self.assertEqual(chips["reading"], [["all", "All", 4], ["books", "Books", 2], ["articles", "Articles", 2], ["now", "Now reading", 1]])
        # episodes and shows both count as Podcasts
        self.assertEqual(chips["listening"], [["all", "All", 6], ["album", "Albums", 1], ["podcast", "Podcasts", 5]])

    def test_a_chip_with_nothing_behind_it_is_hidden(self):
        chips = self.chips(watch={"items": []}, spot={})
        self.assertNotIn("TV", [c[1] for c in chips["watching"]])
        self.assertNotIn("Albums", [c[1] for c in chips["listening"]])
        # a shelf holding one type does not repeat "All" as a type chip
        self.assertEqual([c[1] for c in chips["watching"]], ["All", "First watch", "Rewatches"])
        self.assertEqual(chips["listening"], [["all", "All", 2]])
        no_books = self.chips(diet={"letterboxd": []})
        self.assertEqual(no_books["reading"], [["all", "All", 2]])
        self.assertEqual(no_books["watching"], [["all", "All", 2]])

    def test_chips_are_wired_in_the_component(self):
        js = JS.read_text(encoding="utf-8")
        for label in ("'Films'", "'TV'", "'Books'", "'Articles'", "'Now reading'", "'Albums'", "'Podcasts'"):
            self.assertIn(label, js)
        self.assertIn("var defs = chipList(key, list);", js)

    # ---- "Latest + how often" ----
    def test_summary_lines(self):
        self.assertEqual(self.summary("watching"), "Latest: Show A, Nov 15 · 2 films and 1 show in the last 30 days")
        self.assertEqual(self.summary("reading"), "Latest: Essay · 2 books and 1 article in the last 90 days")
        self.assertEqual(self.summary("listening"), "Latest: Saved episode · 1 album and 3 podcasts in the last 90 days")

    def test_summary_leaves_out_what_it_cannot_say(self):
        # nothing in the window: no count, and never a zero
        self.assertEqual(self.summary("watching", watch={}, today="2027-03-01"), "Latest: Film A, Nov 12, 2026")
        self.assertEqual(self.summary("watching", watch={}), "Latest: Film A, Nov 12 · 2 films in the last 30 days")
        one = {"letterboxd": [{"title": "Solo", "watched": "2026-11-16"}]}
        self.assertEqual(self.summary("watching", diet=one, watch={}), "Latest: Solo, Nov 16 · 1 film in the last 30 days")
        self.assertEqual(self.summary("reading", diet={}), "Latest: Essay · 1 article in the last 90 days")
        # no dates at all: no line
        undated = {"letterboxd": [{"title": "No date"}]}
        self.assertEqual(self.summary("watching", diet=undated, watch={}), "")
        self.assertEqual(self.summary("listening", listen={}, spot={}), "")
        self.assertEqual(self.summary("watching", today="not a date"), "")
        for key in ("watching", "reading", "listening"):
            for today in ("2026-11-17", "2027-06-01", "2030-01-01"):
                self.assertNotRegex(self.summary(key, today=today), r"(^|\D)0 ")

    def test_summary_handles_month_only_and_future_dates(self):
        month = {"items": [{"type": "tv", "title": "Month show", "date": "2026-11"}]}
        self.assertEqual(self.summary("watching", diet={}, watch=month), "Latest: Month show, Nov 2026 · 1 show in the last 30 days")
        future = {"items": [{"type": "tv", "title": "Not yet", "date": "2027-01-01"}]}
        self.assertEqual(self.summary("watching", diet={}, watch=future), "")

    def test_summary_is_computed_and_written_as_text(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn("latest.textContent = line;", js)
        self.assertIn("summaryLine(key, items[key], todayISO())", js)
        body = js[js.index("function summaryLine("): js.index("// ---- Shelves ----")]
        self.assertNotRegex(body, r"\b\d+ (films?|books?|articles?|albums?|podcasts?|shows?)\b")  # no hard-coded counts
        self.assertIn(".md-latest", CSS.read_text(encoding="utf-8"))


class WatchingFileTests(unittest.TestCase):
    """data/watching.json: TV, logged by hand."""

    def test_watching_file_is_valid_and_documented(self):
        data = json.loads((ROOT / "data/watching.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"_readme", "items"})
        readme = " ".join(data["_readme"])
        for word in ("type", "title", "season", "date", "url", "image", "note", "YYYY-MM-DD"):
            self.assertIn(word, readme)
        self.assertIsInstance(data["items"], list)
        allowed = {"type", "title", "season", "date", "url", "image", "note"}
        for item in data["items"]:
            self.assertLessEqual(set(item), allowed)
            self.assertEqual(item.get("type"), "tv")
            self.assertTrue(item.get("title"))
            self.assertRegex(item.get("date", ""), r"^\d{4}-\d{2}(-\d{2})?$")
            for key in ("url", "image"):
                if item.get(key):
                    self.assertTrue(item[key].startswith("https://"), item[key])

    def test_tv_cards_are_labelled(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn("function tvCard", js)
        self.assertIn("el('span', 'md-tv', 'TV')", js)
        self.assertIn(".md-tv", CSS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
