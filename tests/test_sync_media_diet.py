import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

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

SUBSTACK = b"""<?xml version="1.0"?><rss><channel>
<item><title>Why curiosity scales</title><link>https://jgerms20.substack.com/p/why</link>
<description>A short dek &amp; more.</description><pubDate>Wed, 15 Oct 2026 12:00:00 GMT</pubDate></item>
</channel></rss>"""


class MediaDietSyncTests(unittest.TestCase):
    def test_letterboxd_diary_entries_only(self):
        [film] = sync.parse_letterboxd(LETTERBOXD)
        self.assertEqual(film["title"], "Sinners")
        self.assertEqual(film["year"], "2025")
        self.assertEqual(film["rating"], 4.5)
        self.assertEqual(film["watched"], "2026-10-19")
        self.assertEqual(film["poster"], "https://a.ltrbxd.com/poster.jpg")

    def test_goodreads_books(self):
        [book] = sync.parse_goodreads(GOODREADS, 4)
        self.assertEqual(book["author"], "Octavia E. Butler")
        self.assertEqual(book["cover"], "https://i.gr-assets.com/b.jpg")
        self.assertIsNone(book["rating"])

    def test_substack_posts(self):
        [post] = sync.parse_substack(SUBSTACK)
        self.assertEqual(post["dek"], "A short dek & more.")
        self.assertEqual(post["date"], "2026-10-15")

    def test_failed_source_keeps_previous_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "media-diet.json"
            out.write_text(json.dumps({"letterboxd": [{"title": "Old"}], "reading": [], "read": [], "substack": []}))
            with mock.patch.object(sync, "OUT", out), mock.patch.object(sync, "fetch", side_effect=OSError("blocked")):
                self.assertEqual(sync.main([]), 0)
            self.assertEqual(json.loads(out.read_text())["letterboxd"], [{"title": "Old"}])


if __name__ == "__main__":
    unittest.main()
