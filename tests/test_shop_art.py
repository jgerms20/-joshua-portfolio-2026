import json
from pathlib import Path
import re
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOP = (ROOT / "shop.html").read_text(encoding="utf-8")
ART = json.loads((ROOT / "data/art.json").read_text(encoding="utf-8"))


def art_script():
    start = SHOP.index("// Art: collages from data/art.json.")
    return SHOP[start: SHOP.index("</script>", start)]


class ArtDataTests(unittest.TestCase):
    def test_six_pieces_with_the_fields_the_pages_read(self):
        pieces = ART["pieces"]
        self.assertEqual(len(pieces), 6)
        slugs = [p["slug"] for p in pieces]
        self.assertEqual(len(set(slugs)), 6, slugs)
        for p in pieces:
            for key in ("title", "blurb", "medium", "image", "thumb"):
                self.assertIsInstance(p.get(key), str, (p["slug"], key))
                self.assertTrue(p[key].strip(), (p["slug"], key))
            self.assertIsInstance(p.get("for_sale"), bool, p["slug"])
            if p["for_sale"] and "price" in p:
                self.assertIsInstance(p["price"], (int, float))

    def test_image_files_exist_and_thumb_size_matches(self):
        for p in ART["pieces"]:
            self.assertEqual(p["image"], f"photos/art/{p['slug']}.jpg")
            self.assertEqual(p["thumb"], f"photos/art/{p['slug']}-sm.jpg")
            full, thumb = ROOT / p["image"], ROOT / p["thumb"]
            self.assertTrue(full.is_file(), p["image"])
            self.assertTrue(thumb.is_file(), p["thumb"])
            with Image.open(thumb) as im:
                self.assertEqual(list(im.size), list(p["thumb_size"]), p["thumb"])
                self.assertEqual(im.width, 720, p["thumb"])
            with Image.open(full) as im:
                self.assertLessEqual(max(im.size), 2000, p["image"])


class ShopArtSectionTests(unittest.TestCase):
    def test_art_section_and_nav_link(self):
        self.assertIn('id="art"', SHOP)
        self.assertIn('id="artGrid"', SHOP)
        nav = SHOP[SHOP.index('class="shop-sections'):]
        nav = nav[: nav.index("</nav>")]
        self.assertEqual(re.findall(r'href="#(\w+)"', nav), ["prints", "photobooks", "photosets", "art"])

    def test_art_is_rendered_from_data_with_text_content_only(self):
        script = art_script()
        self.assertIn("fetch('data/art.json'", script)
        self.assertIn("textContent", script)
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(sink, script)

    def test_urls_are_restricted_to_relative_or_https(self):
        script = art_script()
        self.assertIn("u.protocol === 'https:'", script)
        self.assertNotIn("'http:'", script)

    def test_inquiry_and_order_mailtos(self):
        script = art_script()
        self.assertIn("mailto:", script)
        self.assertIn("jgerms20@gmail.com", script)
        self.assertIn("'Art inquiry: ' + title", script)
        self.assertIn("Inquire about this piece", script)
        self.assertIn("Request it", script)

    def test_full_size_view_and_noscript_fallback(self):
        self.assertIn('<dialog class="art-lightbox" id="artLightbox"', SHOP)
        self.assertIn("showModal", art_script())
        section = SHOP[SHOP.index('id="art"'):]
        section = section[: section.index("</section>")]
        self.assertIn("<noscript>", section)
        self.assertIn("mailto:jgerms20@gmail.com?subject=Art%20inquiry", section)


if __name__ == "__main__":
    unittest.main()
