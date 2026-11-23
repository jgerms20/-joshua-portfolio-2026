import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_media", ROOT / "scripts/sync-media-diet.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

LETTERBOXD = """<?xml version="1.0"?><rss xmlns:letterboxd="https://letterboxd.com"><channel>
<item><title>Sinners, 2025 - ★★★★½</title><link>https://letterboxd.com/jgerms/film/sinners/</link>
<pubDate>Mon, 20 Oct 2026 03:00:00 +1300</pubDate>
<letterboxd:watchedDate>2026-10-19</letterboxd:watchedDate><letterboxd:rewatch>No</letterboxd:rewatch>
<letterboxd:filmTitle>Sinners</letterboxd:filmTitle><letterboxd:filmYear>2025</letterboxd:filmYear>
<letterboxd:memberRating>4.5</letterboxd:memberRating>
<description><![CDATA[<p><img src="https://a.ltrbxd.com/poster.jpg"/></p><p>Watched.</p>]]></description></item>
<item><title>A list</title><link>https://letterboxd.com/jgerms/list/x/</link></item>
</channel></rss>""".encode("utf-8")

GOODREADS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Parable of the Sower</title><link>https://www.goodreads.com/review/show/1</link>
<author_name>Octavia E. Butler</author_name><book_large_image_url>https://i.gr-assets.com/b.jpg</book_large_image_url>
<user_rating>0</user_rating><pubDate>Tue, 01 Oct 2026 10:00:00 -0700</pubDate></item>
</channel></rss>"""


def goodreads_item(n: int, read_at: str = "", added: str = "Mon, 05 Jan 2026 09:00:00 -0800", rating: int = 4) -> str:
    return (
        f"<item><title><![CDATA[Book {n}]]></title>"
        f"<link><![CDATA[https://www.goodreads.com/review/show/{9000 + n}?utm_medium=api&utm_source=rss]]></link>"
        f"<book_id>{n}</book_id>"
        f"<book_large_image_url><![CDATA[https://i.gr-assets.com/{n}.jpg]]></book_large_image_url>"
        f"<author_name>Author {n}</author_name><user_rating>{rating}</user_rating>"
        f"<user_read_at>{read_at}</user_read_at><user_date_added><![CDATA[{added}]]></user_date_added>"
        f"<pubDate>Wed, 01 Jan 2025 00:00:00 -0800</pubDate></item>"
    )


def goodreads_page(numbers) -> bytes:
    return ("<?xml version='1.0'?><rss><channel>" + "".join(goodreads_item(n) for n in numbers) + "</channel></rss>").encode()


# Two grid markups Letterboxd has served on /films/ pages
RATED_PAGE_REACT = """<ul class="grid">
<li class="griditem"><div class="react-component" data-component-class="LazyPoster" data-item-name="The Hunger Games: The Ballad of Songbirds &amp; Snakes (2023)" data-item-slug="the-hunger-games-the-ballad-of-songbirds-snakes" data-item-link="/film/the-hunger-games-the-ballad-of-songbirds-snakes/"><img alt="The Hunger Games: The Ballad of Songbirds &amp; Snakes" src="empty.png"/></div>
<p class="poster-viewingdata"><span class="rating -micro -darker rated-7">★★★½</span></p></li>
<li class="griditem"><div class="react-component" data-item-name="Adaptation. (2002)" data-item-slug="adaptation" data-item-link="/film/adaptation/"></div>
<p class="poster-viewingdata"><span class="rating -micro -darker rated-8">★★★★</span></p></li>
</ul>"""
RATED_PAGE_POSTER = """<ul class="poster-list">
<li class="poster-container"><div class="really-lazy-load poster film-poster" data-film-id="1" data-film-slug="rocky" data-target-link="/film/rocky/"><img alt="Rocky" src="empty.png"/></div>
<p class="poster-viewingdata"><span class="rating -micro -darker rated-8">★★★★</span></p></li>
<li class="poster-container"><div class="poster film-poster" data-film-slug="dunkirk-2017" data-target-link="/film/dunkirk-2017/"><img alt="Dunkirk" src="e.png"/></div></li>
</ul>"""
FILM_PAGE = """<html><script type="application/ld+json">
/* <![CDATA[ */
{"name":"Adaptation.","image":"https://a.ltrbxd.com/resized/adaptation-0-230-0-345-crop.jpg","releasedEvent":[{"@type":"PublicationEvent","startDate":"2002"}]}
/* ]]> */
</script></html>"""


class FakeFeeds:
    """Answers fetch(url, browser=...) like the live hosts, and records each call."""

    def __init__(self, shelves, letterboxd=LETTERBOXD):
        self.shelves = shelves  # {"read": [[1, 2], [3]], "currently-reading": [[7]]}
        self.letterboxd = letterboxd
        self.calls = []

    def __call__(self, url, browser=False):
        self.calls.append((url, browser))
        if "letterboxd.com" in url:
            return self.letterboxd
        query = parse_qs(urlparse(url).query)
        pages = self.shelves.get(query["shelf"][0], [])
        page = int(query.get("page", ["1"])[0])
        return goodreads_page(pages[page - 1] if page <= len(pages) else [])


class MediaDietSyncTests(unittest.TestCase):
    def run_sync(self, previous, feeds, argv=()):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "media-diet.json"
            if previous is not None:
                out.write_text(json.dumps(previous))
            with mock.patch.object(sync, "OUT", out), mock.patch.object(sync, "fetch", side_effect=feeds), \
                    mock.patch("sys.stdout"), mock.patch("sys.stderr"):
                self.assertEqual(sync.main(list(argv)), 0)
            return json.loads(out.read_text())

    # ---- parsers ----
    def test_letterboxd_diary_entries_only(self):
        [film] = sync.parse_letterboxd(LETTERBOXD)
        self.assertEqual(film["title"], "Sinners")
        self.assertEqual(film["year"], "2025")
        self.assertEqual(film["rating"], 4.5)
        self.assertEqual(film["watched"], "2026-10-19")
        self.assertEqual(film["poster"], "https://a.ltrbxd.com/poster.jpg")

    def test_letterboxd_keeps_the_whole_feed_window(self):
        items = "".join(
            f"<item><link>https://letterboxd.com/jgerms/film/f{n}/</link>"
            f"<letterboxd:filmTitle>Film {n}</letterboxd:filmTitle><letterboxd:watchedDate>2026-01-{n:02d}</letterboxd:watchedDate></item>"
            for n in range(1, 21)
        )
        xml = f'<rss xmlns:letterboxd="https://letterboxd.com"><channel>{items}</channel></rss>'.encode()
        films = sync.parse_letterboxd(xml)
        self.assertEqual(len(films), 20)  # no more 8-film cap
        self.assertEqual(films[0]["title"], "Film 20")

    def test_goodreads_books(self):
        [book] = sync.parse_goodreads(GOODREADS, "read")
        self.assertEqual(book["author"], "Octavia E. Butler")
        self.assertEqual(book["cover"], "https://i.gr-assets.com/b.jpg")
        self.assertIsNone(book["rating"])
        self.assertEqual(book["date"], "2026-10-01")
        self.assertEqual(book["shelf"], "read")
        self.assertEqual(book["url"], "https://www.goodreads.com/review/show/1")

    def test_goodreads_prefers_read_date_then_date_added_and_links_the_book(self):
        xml = ("<rss><channel>" + goodreads_item(5, read_at="Sat, 14 Mar 2026 00:00:00 -0700")
               + goodreads_item(6) + "</channel></rss>").encode()
        finished, added = sync.parse_goodreads(xml, "read")
        self.assertEqual(finished["date"], "2026-03-14")
        self.assertEqual(added["date"], "2026-01-05")
        self.assertEqual(finished["url"], "https://www.goodreads.com/book/show/5")
        self.assertEqual(finished["rating"], 4)
        self.assertEqual(finished["shelf"], "read")

    def test_goodreads_placeholder_cover_is_dropped(self):
        xml = b"""<rss><channel><item><title>No Cover</title><book_id>3</book_id>
        <book_large_image_url>https://s.gr-assets.com/assets/nophoto/book/111x148.png</book_large_image_url></item></channel></rss>"""
        [book] = sync.parse_goodreads(xml, "read")
        self.assertEqual(book["cover"], "")

    def test_html_instead_of_rss_is_an_error_not_an_empty_shelf(self):
        with self.assertRaises(ValueError):
            sync.parse_goodreads(b"<!DOCTYPE html><html><body>Sign in</body></html>", "read")

    # ---- Goodreads paging + user agent ----
    def test_goodreads_pages_until_empty_with_a_browser_user_agent(self):
        feeds = FakeFeeds({"read": [list(range(1, 101)), list(range(101, 131))]})
        with mock.patch.object(sync, "fetch", side_effect=feeds), mock.patch("sys.stdout"):
            books = sync.fetch_goodreads_shelf("read")
        self.assertEqual(len(books), 130)
        self.assertEqual(len(feeds.calls), 3)  # pages 1, 2 and the empty page 3
        for url, browser in feeds.calls:
            self.assertTrue(browser)
            query = parse_qs(urlparse(url).query)
            self.assertEqual(query["shelf"], ["read"])
            self.assertEqual(query["per_page"], ["100"])
        self.assertEqual([parse_qs(urlparse(u).query)["page"] for u, _ in feeds.calls], [["1"], ["2"], ["3"]])
        self.assertTrue(feeds.calls[0][0].startswith("https://www.goodreads.com/review/list_rss/95365432?"))

    def test_goodreads_stops_when_the_page_param_is_ignored(self):
        def same_page_every_time(url, browser=False):
            return goodreads_page([1, 2, 3])
        with mock.patch.object(sync, "fetch", side_effect=same_page_every_time) as fetch, mock.patch("sys.stdout"):
            books = sync.fetch_goodreads_shelf("read")
        self.assertEqual(len(books), 3)
        self.assertEqual(fetch.call_count, 2)

    def test_browser_user_agent_is_sent(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b"<rss/>"
        with mock.patch("urllib.request.urlopen", return_value=Response()) as urlopen:
            sync.fetch("https://www.goodreads.com/review/list_rss/95365432?shelf=read", browser=True)
        request = urlopen.call_args[0][0]
        self.assertIn("Mozilla/5.0", request.get_header("User-agent"))

    # ---- accumulation ----
    def test_new_entries_merge_with_the_archive_newest_first(self):
        old_film = {"title": "Dunkirk", "year": "2017", "rating": 4.0, "watched": "2026-07-28", "rewatch": True,
                    "poster": "", "url": "https://letterboxd.com/jgerms/film/dunkirk-2017/"}
        stale_sinners = {"title": "Sinners", "rating": 3.0, "watched": "2026-10-19",
                         "url": "https://letterboxd.com/jgerms/film/sinners/"}
        old_book = {"title": "Old Book", "author": "A", "cover": "", "rating": 5, "date": "2020-01-01",
                    "url": "https://www.goodreads.com/book/show/999", "shelf": "read"}
        previous = {"letterboxd": [stale_sinners, old_film], "reading": [], "read": [old_book], "updated": "x"}
        feeds = FakeFeeds({"read": [[1, 2]], "currently-reading": [[7]]})
        data = self.run_sync(previous, feeds)
        self.assertEqual([f["title"] for f in data["letterboxd"]], ["Sinners", "Dunkirk"])
        self.assertEqual(data["letterboxd"][0]["rating"], 4.5)  # the feed's copy wins
        self.assertEqual([b["title"] for b in data["read"]], ["Book 1", "Book 2", "Old Book"])
        self.assertEqual([b["title"] for b in data["reading"]], ["Book 7"])
        self.assertEqual(data["reading"][0]["shelf"], "currently-reading")

    def test_archive_is_capped(self):
        previous = {"letterboxd": [{"title": f"F{n}", "watched": f"2020-01-01", "url": f"https://letterboxd.com/x/{n}/"}
                                   for n in range(sync.MAX_ENTRIES + 50)], "reading": [], "read": []}
        data = self.run_sync(previous, FakeFeeds({}))
        self.assertEqual(len(data["letterboxd"]), sync.MAX_ENTRIES)
        self.assertEqual(data["letterboxd"][0]["title"], "Sinners")

    def test_finished_books_leave_the_nightstand(self):
        previous = {"letterboxd": [], "read": [], "reading": [
            {"title": "Book 1", "url": "https://www.goodreads.com/book/show/1", "date": "2026-01-01"}]}
        data = self.run_sync(previous, FakeFeeds({"read": [[1]], "currently-reading": []}))
        self.assertEqual(data["reading"], [])
        self.assertEqual([b["title"] for b in data["read"]], ["Book 1"])

    def test_empty_goodreads_answer_keeps_the_nightstand(self):
        now = {"title": "Still Reading", "url": "https://www.goodreads.com/book/show/77", "date": "2026-01-01"}
        data = self.run_sync({"letterboxd": [], "read": [], "reading": [now]}, FakeFeeds({}))
        self.assertEqual(data["reading"], [now])

    def test_failed_source_keeps_previous_entries(self):
        previous = {"letterboxd": [{"title": "Old"}], "reading": [], "read": [{"title": "Kept"}]}
        data = self.run_sync(previous, mock.Mock(side_effect=OSError("blocked")))
        self.assertEqual(data["letterboxd"], [{"title": "Old"}])
        self.assertEqual(data["read"], [{"title": "Kept"}])

    # ---- rated order ----
    def test_rated_page_reads_both_markups(self):
        films = sync.parse_rated_page(RATED_PAGE_REACT)
        self.assertEqual(films, [
            {"slug": "the-hunger-games-the-ballad-of-songbirds-snakes",
             "title": "The Hunger Games: The Ballad of Songbirds & Snakes", "year": "2023", "rating": 3.5},
            {"slug": "adaptation", "title": "Adaptation.", "year": "2002", "rating": 4.0},
        ])
        films = sync.parse_rated_page(RATED_PAGE_POSTER)
        self.assertEqual([(f["slug"], f["title"], f["year"], f["rating"]) for f in films],
                         [("rocky", "Rocky", "", 4.0), ("dunkirk-2017", "Dunkirk", "", None)])
        self.assertEqual(sync.parse_rated_page("<html>Just a moment...</html>"), [])

    def test_film_page_gives_poster_and_year(self):
        self.assertEqual(sync.parse_film_page(FILM_PAGE),
                         {"poster": "https://a.ltrbxd.com/resized/adaptation-0-230-0-345-crop.jpg", "year": "2002"})
        self.assertEqual(sync.parse_film_page("<html></html>"), {"poster": "", "year": ""})

    def test_films_follow_the_rated_order_not_the_diary(self):
        rated = [{"slug": "adaptation", "title": "Adaptation.", "year": "2002", "rating": 4.0},
                 {"slug": "dunkirk-2017", "title": "Dunkirk", "year": "", "rating": 4.0}]
        diary = [{"title": "Dunkirk", "year": "2017", "rating": 4.0, "watched": "2026-07-28", "rewatch": True,
                  "poster": "https://a.ltrbxd.com/d.jpg", "url": "https://letterboxd.com/jgerms/film/dunkirk-2017/"},
                 {"title": "Unrated", "year": "2001", "rating": None, "watched": "2026-08-01", "rewatch": False,
                  "poster": "", "url": "https://letterboxd.com/jgerms/film/unrated/"}]
        films = sync.build_films(rated, True, diary, [])
        self.assertEqual([f["title"] for f in films], ["Adaptation.", "Dunkirk", "Unrated"])
        self.assertEqual([f["rated_rank"] for f in films], [0, 1, None])
        self.assertEqual(films[0]["watched"], "")  # no diary entry: no invented date
        self.assertEqual(films[1]["watched"], "2026-07-28")
        self.assertTrue(films[1]["rewatch"])
        self.assertEqual(films[1]["year"], "2017")
        self.assertEqual(films[1]["poster"], "https://a.ltrbxd.com/d.jpg")
        self.assertEqual(films[0]["url"], "https://letterboxd.com/jgerms/film/adaptation/")

    def test_partial_read_keeps_the_rest_of_the_old_order(self):
        previous = [{"title": t, "url": f"https://letterboxd.com/jgerms/film/{t}/", "rated_rank": i}
                    for i, t in enumerate(["a", "b", "c"])]
        films = sync.build_films([{"slug": "new", "title": "new", "year": "", "rating": 3.0}], False, [], previous)
        self.assertEqual([f["title"] for f in films], ["new", "a", "b", "c"])
        self.assertEqual([f["rated_rank"] for f in films], [0, 1, 2, 3])

    def test_sync_uses_the_rated_pages_and_looks_up_missing_posters(self):
        def fetch(url, browser=False):
            if "/films/by/rated-date/page/2/" in url:
                return RATED_PAGE_POSTER.encode()
            if "/films/by/rated-date/" in url:
                return RATED_PAGE_REACT.encode()
            if "/film/" in url and "/jgerms/" not in url:
                return FILM_PAGE.encode()
            if "letterboxd.com" in url:
                return LETTERBOXD  # the diary RSS
            return goodreads_page([])
        data = self.run_sync({"letterboxd": [], "reading": [], "read": []}, fetch)
        self.assertEqual([f["title"] for f in data["letterboxd"]][:4],
                         ["The Hunger Games: The Ballad of Songbirds & Snakes", "Adaptation.", "Rocky", "Dunkirk"])
        self.assertEqual(data["letterboxd"][-1]["title"], "Sinners")  # diary-only, after the rated films
        self.assertIsNone(data["letterboxd"][-1]["rated_rank"])
        self.assertTrue(all(f["poster"] for f in data["letterboxd"]))

    def test_blocked_rated_pages_keep_the_saved_order(self):
        previous = {"letterboxd": [
            {"title": "Top", "url": "https://letterboxd.com/jgerms/film/top/", "rated_rank": 0},
            {"title": "Next", "url": "https://letterboxd.com/jgerms/film/next/", "rated_rank": 1}],
            "reading": [], "read": []}
        data = self.run_sync(previous, FakeFeeds({}))  # rated-date pages answer with RSS: no films
        self.assertEqual([f["title"] for f in data["letterboxd"]], ["Top", "Next", "Sinners"])

    # ---- Substack is gone; listening is hand-edited ----
    def test_substack_is_dropped(self):
        self.assertFalse(hasattr(sync, "parse_substack"))
        previous = {"letterboxd": [], "reading": [], "read": [], "substack": [{"title": "Old post"}]}
        feeds = FakeFeeds({})
        data = self.run_sync(previous, feeds)
        self.assertNotIn("substack", data)
        self.assertEqual(set(data), {"letterboxd", "reading", "read", "updated"})
        self.assertFalse(any("substack" in url for url, _ in feeds.calls))

    def test_sync_never_touches_listening(self):
        self.assertNotIn("listening", Path(ROOT / "scripts/sync-media-diet.py").read_text().split('"""', 2)[2])

    def test_listening_file_is_valid_and_documented(self):
        data = json.loads((ROOT / "data/listening.json").read_text(encoding="utf-8"))
        self.assertIn("_readme", data)
        self.assertIsInstance(data["items"], list)
        allowed = {"podcast", "episode", "article", "album", "song", "video"}
        for item in data["items"]:
            self.assertIn(item.get("type"), allowed)
            self.assertTrue(item.get("title"))
            if "url" in item:  # no link is fine; a guessed or non-https link is not
                self.assertTrue(item["url"].startswith("https://"))
            self.assertRegex(item.get("date", ""), r"^\d{4}-\d{2}(-\d{2})?$")  # a day, or just the month
            if item.get("image"):
                self.assertTrue(item["image"].startswith("https://"))

    def test_committed_media_diet_has_the_new_shape(self):
        data = json.loads((ROOT / "data/media-diet.json").read_text(encoding="utf-8"))
        self.assertNotIn("substack", data)
        for key in ("letterboxd", "reading", "read"):
            self.assertIsInstance(data[key], list)


if __name__ == "__main__":
    unittest.main()
