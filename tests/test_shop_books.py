import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHOP = (ROOT / "shop.html").read_text(encoding="utf-8")
STATUSES = {"in-the-works", "pre-order", "available", "sold-out"}


class ShopBooksAndSetsTests(unittest.TestCase):
    def test_shop_has_prints_books_and_sets_sections(self):
        for anchor in ("prints", "photobooks", "photosets"):
            self.assertIn(f'id="{anchor}"', SHOP)
            self.assertIn(f'href="#{anchor}"', SHOP)

    def test_photobooks_data_is_valid(self):
        data = json.loads((ROOT / "data/photobooks.json").read_text(encoding="utf-8"))
        self.assertIsInstance(data["books"], list)
        for book in data["books"]:
            self.assertTrue(book.get("title"), book)
            self.assertIn(book.get("status", "in-the-works"), STATUSES, book)
            if "price" in book:
                self.assertIsInstance(book["price"], (int, float))
            if book.get("cover") and not book["cover"].startswith("http"):
                self.assertTrue((ROOT / book["cover"]).is_file(), book["cover"])

    def test_empty_shelf_shows_an_honest_placeholder(self):
        self.assertIn("status: 'in-the-works'", SHOP)
        self.assertIn("Get notified", SHOP)
        self.assertIn("mailto:", SHOP)

    def test_book_and_set_data_is_never_written_as_html(self):
        script = SHOP[SHOP.index("// Photo books + photo sets."):]
        script = script[: script.index("</script>")]
        for sink in ("innerHTML", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(sink, script)

    def test_sets_link_to_the_photography_site(self):
        self.assertIn("'photography/#set-'", SHOP)
        sets = json.loads((ROOT / "data/photo-sets.json").read_text(encoding="utf-8"))["sets"]
        self.assertTrue(any(s["slug"] == "rio-de-janeiro" for s in sets))

    def test_photography_site_links_to_books(self):
        page = (ROOT / "photography/index.html").read_text(encoding="utf-8")
        self.assertIn('href="../shop.html#photobooks"', page)
        self.assertIsNotNone(re.search(r'href="\.\./shop\.html#photosets"', page))


if __name__ == "__main__":
    unittest.main()
