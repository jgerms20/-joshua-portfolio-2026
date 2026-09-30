from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from portfolio_quality.html_checks import check_page
from portfolio_quality.photography import (
    COMMERCIAL_CATEGORIES,
    INQUIRY_EMAIL,
    PHOTO_SITE_END,
    PHOTO_SITE_CARD_URL,
    PHOTO_SITE_START,
    PHOTO_SITE_URL,
    SIZED_DIR,
    UNLOCK_THRESHOLD,
    apply_photo_site,
    group_photo_site,
    import_photography_inbox,
    load_photo_site_settings,
    load_photography_manifest,
    missing_sized_images,
    render_darkroom,
    render_photo_site,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/photography.json"
PHOTO_SITE = ROOT / "photography/index.html"


class PhotographyManifestTests(unittest.TestCase):
    def test_manifest_has_valid_unique_published_photos(self):
        photos = load_photography_manifest(MANIFEST)
        ids = [photo["id"] for photo in photos]
        sources = [photo["src"] for photo in photos]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(sources), len(set(sources)))
        self.assertTrue(all(photo["chapter"] in {"people", "places", "gatherings"} for photo in photos))
        self.assertTrue(all(photo["alt"].strip() for photo in photos))
        self.assertTrue(all((ROOT / photo["src"]).is_file() for photo in photos))

    def test_selected_sequence_is_contiguous_and_curated(self):
        photos = load_photography_manifest(MANIFEST)
        selected = sorted(
            (photo for photo in photos if photo.get("sequence") is not None),
            key=lambda photo: photo["sequence"],
        )

        self.assertGreaterEqual(len(selected), 18)
        self.assertLessEqual(len(selected), 24)
        self.assertEqual(
            [photo["sequence"] for photo in selected],
            list(range(1, len(selected) + 1)),
        )
        self.assertEqual(selected[0]["layout"], "hero")

    def test_darkroom_is_chapter_three_and_sends_people_to_the_photo_site(self):
        markup = render_darkroom(load_photography_manifest(MANIFEST))

        # the sequence toggle carries the right count for each state
        self.assertRegex(markup, r'data-open-count="\d+ frames" data-closed-count="\d+ more frames"')
        # the site link never breaks before its arrow
        self.assertIn("joshuamgerman.com/photography&nbsp;&rarr;", markup)

        self.assertIn('<span class="ch-num">CH. 03</span>', markup)
        self.assertNotIn("CH. 06", markup)
        self.assertIn('href="photography/#book"', markup)
        self.assertIn('href="photography/"', markup)
        self.assertIn("Visit the photography site", markup)

    def test_renderer_outputs_story_and_three_accessible_chapters(self):
        markup = render_darkroom(load_photography_manifest(MANIFEST))

        self.assertIn('class="photo-sequence rv"', markup)
        self.assertIn('data-chapter="people"', markup)
        self.assertIn('data-chapter="places"', markup)
        self.assertIn('data-chapter="gatherings"', markup)
        self.assertIn('aria-pressed="true"', markup)
        self.assertIn("Selected sequence", markup)
        self.assertNotIn("photo-masonry", markup)

    def test_homepage_contains_rendered_darkroom_markers(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("<!-- PHOTOGRAPHY:START -->", page)
        self.assertIn("<!-- PHOTOGRAPHY:END -->", page)
        self.assertIn('class="photo-sequence rv"', page)

    def test_inbox_import_creates_an_unpublished_metadata_stripped_webp_once(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / "photos/inbox"
            inbox.mkdir(parents=True)
            manifest_path = root / "data/photography.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text('{"version": 1, "entries": []}', encoding="utf-8")
            source = inbox / "New Portrait.JPG"
            image = Image.new("RGB", (32, 48), "red")
            image.save(source, exif=b"Exif\x00\x00test-metadata")

            first = import_photography_inbox(root)
            second = import_photography_inbox(root)

            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            generated = root / first[0]["src"]
            self.assertTrue(generated.is_file())
            with Image.open(generated) as imported:
                self.assertEqual(imported.format, "WEBP")
                self.assertEqual(dict(imported.getexif()), {})
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["entries"]), 1)
            self.assertFalse(payload["entries"][0]["published"])
            self.assertEqual(payload["entries"][0]["chapter"], "unassigned")
            self.assertEqual(payload["entries"][0]["alt"], "")


class _Tags(HTMLParser):
    """Collects start tags with their attributes and the text inside chosen elements."""

    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        attributes = {name: value or "" for name, value in attrs}
        self.tags.append((tag, attributes))
        if attributes.get("id"):
            self.ids.add(attributes["id"])


def _parse(markup: str) -> list[tuple[str, dict[str, str]]]:
    tags = _Tags()
    tags.feed(markup)
    return tags.tags


def _visible_text(page: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S | re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return re.sub(r"<[^>]+>", " ", text)


def _locked_cards(page: str) -> list[str]:
    return re.findall(r'<article class="[^"]*card--locked.*?</article>', page, flags=re.S)


class PhotoSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.photos = load_photography_manifest(MANIFEST)
        cls.page = PHOTO_SITE.read_text(encoding="utf-8")
        cls.tags = _Tags()
        cls.tags.feed(cls.page)

    def test_page_is_current_with_the_manifest(self):
        settings = load_photo_site_settings(MANIFEST)
        rendered = apply_photo_site(
            self.page,
            render_photo_site(self.photos, root=ROOT, clients=settings["clients"], shoots=settings["shoots"]),
        )
        self.assertEqual(rendered, self.page, "run python3 scripts/render-photography.py --page-only")
        self.assertIn(PHOTO_SITE_START, self.page)
        self.assertIn(PHOTO_SITE_END, self.page)

    def test_render_script_check_mode_reports_current_page(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/render-photography.py"), "--page-only", "--check"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_required_sections_and_nav_exist(self):
        for section in ("hero", "work", "commercial", "services", "process", "prints", "about", "book"):
            self.assertIn(section, self.tags.ids, section)
        order = [self.page.index(f'id="{section}"') for section in ("hero", "work", "commercial", "services", "prints", "about", "book")]
        self.assertEqual(order, sorted(order))
        nav = self.page[self.page.index('<nav class="nav-links"'):]
        nav = nav[: nav.index("</nav>")]
        self.assertEqual(re.findall(r'href="([^"]+)"', nav), ["#work", "#services", "#about"])
        self.assertIn('class="nav-book" href="#book"', self.page)
        self.assertIn("Joshua McKenzie German", self.page[: self.page.index("</header>")])
        self.assertIn(">Photography<", self.page[: self.page.index("</header>")])
        self.assertIn('class="nav-home" href="../"', self.page)

    def test_hero_leads_with_booking(self):
        hero = self.page[self.page.index('<section class="hero"'):]
        hero = hero[: hero.index("</section>")]
        self.assertIn("Joshua McKenzie <em>German</em>", hero)
        self.assertIn("Now booking product, food, hospitality and real-estate shoots too.", hero)
        self.assertIn('href="#book">Book a shoot', hero)
        self.assertIn('fetchpriority="high"', hero)
        self.assertEqual(self.page.count('fetchpriority="high"'), 1)
        self.assertEqual(self.page.count('loading="eager"'), 1)

    def test_every_published_photo_appears_in_a_set(self):
        for photo in self.photos:
            self.assertIn(f'data-full="../{photo["src"]}"', self.page, photo["id"])

    def test_projects_are_derived_from_folders_and_cover_every_frame(self):
        grouped = group_photo_site(self.photos)
        projects = {project["slug"]: project for project in grouped["projects"]}
        built_in = ["portraits", "fashion", "events", "rio-de-janeiro", "landscapes", "travel"]
        self.assertEqual([slug for slug in projects if slug in built_in], built_in)
        placed = [frame["id"] for project in projects.values() for frame in project["frames"]]
        self.assertEqual(sorted(placed), sorted(photo["id"] for photo in self.photos))
        self.assertEqual(projects["portraits"]["frames"][0]["id"], "father-and-child")
        self.assertTrue(all(frame["src"].startswith("photos/shop/rio-") for frame in projects["rio-de-janeiro"]["frames"]))
        for slug in projects:
            self.assertIn(f'<section class="set" id="{slug}"', self.page)
            self.assertIn(f'href="#{slug}" data-open="{slug}"', self.page)

    def test_locked_categories_render_without_images(self):
        cards = _locked_cards(self.page)
        self.assertEqual(len(cards), 4)
        titles = [re.search(r'<h3 class="lock-title">(.*?)</h3>', card).group(1) for card in cards]
        self.assertEqual(titles, ["Product", "Food &amp; Restaurants", "Hospitality &amp; Locations", "Real Estate &amp; Spaces"])
        for card in cards:
            self.assertNotIn("<img", card)
            self.assertIn("<span>Locked</span>", card)
            # "in development" is said once, in the section header, not per card
            self.assertNotIn("development", card.lower())
            self.assertRegex(card, r'href="#book" data-shoot="(product|food|hospitality|real-estate)"')
        commercial = self.page[self.page.index('id="commercial"'):self.page.index('id="services"')]
        self.assertEqual(_visible_text(commercial).lower().count("in development"), 1)

    def test_booking_links_preselect_the_matching_shoot(self):
        commercial = self.page[self.page.index('id="commercial"'):self.page.index('id="services"')]
        # the Now booking button covers four kinds of shoot, so it preselects none
        self.assertRegex(commercial, r'<a class="btn btn-safelight" href="#book">Plan your shoot')
        services = self.page[self.page.index('id="services"'):self.page.index('id="process"')]
        self.assertIn('data-shoot="real-estate"', services)
        self.assertIn('data-shoot="hospitality"', services)
        landscapes = self.page[self.page.index('data-set="landscapes"'):]
        landscapes = landscapes[: landscapes.index("</article>")]
        self.assertNotIn('data-shoot="hospitality"', landscapes)

    def test_nearby_archive_frames_are_labelled_as_not_client_work(self):
        for slug in ("food-archive", "hospitality-archive"):
            block = self.page[self.page.index(f'<section class="set" id="{slug}"'):]
            block = block[: block.index("</section>")]
            self.assertIn("not client work", block)
        self.assertNotIn('id="product-archive"', self.page)
        self.assertNotIn('id="real-estate-archive"', self.page)

    def test_service_unlocks_into_a_volume_after_the_threshold(self):
        base = [dict(photo) for photo in self.photos]
        tagged = [dict(photo, service="product") for photo in base[: UNLOCK_THRESHOLD - 1]]
        almost = group_photo_site(tagged + base[UNLOCK_THRESHOLD - 1 :])
        self.assertIn("product", [category["slug"] for category in almost["locked"]])
        self.assertEqual(len(almost["locked"][0]["frames"]), UNLOCK_THRESHOLD - 1)
        almost_page = render_photo_site(tagged + base[UNLOCK_THRESHOLD - 1 :], root=ROOT)
        self.assertIn('<section class="set" id="product"', almost_page)
        self.assertNotIn("Product 1.0", almost_page)

        tagged = [dict(photo, service="product") for photo in base[:UNLOCK_THRESHOLD]]
        unlocked = group_photo_site(tagged + base[UNLOCK_THRESHOLD:])
        self.assertNotIn("product", [category["slug"] for category in unlocked["locked"]])
        self.assertEqual(unlocked["projects"][0]["title"], "Product 1.0")
        page = render_photo_site(tagged + base[UNLOCK_THRESHOLD:], root=ROOT)
        self.assertEqual(len(_locked_cards(page)), 3)
        self.assertIn("Product 1.0", page)

    def test_project_key_overrides_the_folder(self):
        photos = [dict(photo) for photo in self.photos]
        photos[0]["project"] = "Fashion"
        photos[1]["project"] = "Night Market Series"
        grouped = {project["slug"]: project for project in group_photo_site(photos)["projects"]}
        self.assertIn(photos[0]["id"], [frame["id"] for frame in grouped["fashion"]["frames"]])
        self.assertEqual(grouped["night-market-series"]["title"], "Night Market Series")

    def test_manifest_rejects_unknown_service(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "photography.json"
            entry = dict(self.photos[0], service="cars")
            path.write_text(json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_photography_manifest(path)

    def test_inquiry_form_builds_an_email_to_joshua(self):
        form = self.page[self.page.index('<form class="inquiry'):]
        form = form[: form.index("</form>")]
        self.assertIn(f'action="mailto:{INQUIRY_EMAIL}"', form)
        self.assertIn(f'data-email="{INQUIRY_EMAIL}"', form)
        for name in ("name", "email", "shoot", "company", "date", "location", "budget", "source", "details"):
            self.assertIn(f'name="{name}"', form)
        # budget is the client's own words: no preset bands that read as a rate card
        self.assertRegex(form, r'<input id="f-budget" name="budget" type="text"')
        self.assertNotRegex(form, r"\d,\d{3}")
        self.assertNotIn("USD", self.page)
        for field in ("name", "email", "shoot", "details"):
            self.assertRegex(form, rf'name="{field}"[^>]*required')
        for category in COMMERCIAL_CATEGORIES:
            self.assertIn(f'<option value="{category["service"]}">', form)
        self.assertIn("<option>Business card</option>", form)
        self.assertIn("Photo inquiry: ", self.page)
        self.assertIn(f'href="mailto:{INQUIRY_EMAIL}"', self.page)
        self.assertIn('href="https://instagram.com/jgerms20"', self.page)

    def test_seo_tags_use_the_canonical_url_and_a_real_photo(self):
        self.assertIn(f'<link rel="canonical" href="{PHOTO_SITE_URL}">', self.page)
        self.assertRegex(self.page, r"<title>[^<]*Photography[^<]*Joshua McKenzie German[^<]*</title>")
        self.assertIn('<meta name="description"', self.page)
        sources = {photo["src"] for photo in self.photos}
        for key in ('property="og:image"', 'name="twitter:image"'):
            url = re.search(rf'<meta {key} content="([^"]+)">', self.page).group(1)
            self.assertTrue(url.startswith("https://joshuamgerman.com/"), url)
            self.assertIn(url.removeprefix("https://joshuamgerman.com/"), sources)
        self.assertIn(f'<meta property="og:url" content="{PHOTO_SITE_URL}">', self.page)
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', self.page, re.S).group(1))
        types = {node["@type"] for node in data["@graph"]}
        self.assertEqual(types, {"Person", "ProfessionalService"})
        self.assertNotIn("priceRange", json.dumps(data))
        self.assertNotIn("aggregateRating", json.dumps(data))

    def test_no_invented_rates_or_internal_notes(self):
        self.assertNotIn("$", self.page)
        text = _visible_text(self.page).lower()
        for phrase in ("starting at", "per hour", "/hr", "turnaround", "48 hours", "testimonial",
                       "live catalog", "twice weekly", "newest first", "no guests", "threshold",
                       "two podcasts", "extend", "open call", "first set"):
            self.assertNotIn(phrase, text)
        self.assertNotRegex(text, r"\bmuse\b")
        self.assertIn("rates quoted per project", text)

    def test_links_back_to_the_main_site_and_prints(self):
        self.assertIn('href="../shop.html"', self.page)
        self.assertIn('href="../"', self.page)
        self.assertIn('href="../index.html"', self.page)
        self.assertIn("The Rio set is available as prints", self.page)

    def test_images_are_served_as_resized_copies(self):
        """A QR scan over cellular should not pull 2000px originals for thumbnails."""
        images = [attrs for tag, attrs in self.tags.tags if tag == "img" and attrs.get("src")]
        for attrs in images:
            if "srcset" not in attrs:
                continue
            for candidate in attrs["srcset"].split(","):
                url, descriptor = candidate.split()
                self.assertTrue(url.startswith(f"../{SIZED_DIR}/"), url)
                self.assertTrue(descriptor.endswith("w"), candidate)
                self.assertTrue((PHOTO_SITE.parent / url).resolve().is_file(), url)
            self.assertTrue(attrs.get("sizes"), attrs["src"])
        self.assertEqual(missing_sized_images(ROOT), [])
        page_images = [attrs for attrs in images if "lb-img" not in attrs.get("class", "")]
        self.assertTrue(all("srcset" in attrs for attrs in page_images))
        # Everything a phone can fetch on first load (hero + Work covers + prints
        # thumbs, at their largest candidate) stays well under the old ~2 MB.
        first_screen = self.page[: self.page.index('id="services"')] + self.page[self.page.index('id="prints"'): self.page.index('id="about"')]
        total = 0
        for attrs in (a for t, a in _parse(first_screen) if t == "img"):
            largest = attrs["srcset"].split(",")[-1].split()[0] if attrs.get("srcset") else attrs["src"]
            total += (PHOTO_SITE.parent / largest).resolve().stat().st_size
        self.assertLess(total, 900_000, total)

    def test_every_image_has_dimensions_and_alt_text(self):
        images = [attrs for tag, attrs in self.tags.tags if tag == "img"]
        self.assertGreater(len(images), 37)
        for attrs in images:
            self.assertTrue(attrs.get("width", "").isdigit() and attrs.get("height", "").isdigit(), attrs)
            self.assertIn("alt", attrs)
            if attrs.get("src"):
                self.assertTrue(attrs["src"].startswith("../"), attrs["src"])
                self.assertTrue((PHOTO_SITE.parent / attrs["src"]).resolve().is_file(), attrs["src"])

    def test_page_has_no_static_media_findings(self):
        self.assertEqual(check_page(ROOT, PHOTO_SITE), [])

    def test_business_card_qr_codes_point_at_the_photo_site(self):
        svg = ROOT / "assets/qr/photography-qr.svg"
        png = ROOT / "assets/qr/photography-qr.png"
        self.assertTrue(svg.is_file())
        self.assertIn("<svg", svg.read_text(encoding="utf-8"))
        try:
            import qrcode
        except ImportError:  # pragma: no cover
            self.skipTest("qrcode is not installed")
        self.assertEqual(PHOTO_SITE_CARD_URL, PHOTO_SITE_URL + "?src=card")
        # the card URL is what preselects "Business card" in the form
        self.assertIn("params.get('src') === 'card'", self.page)
        code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=40, border=4)
        code.add_data(PHOTO_SITE_CARD_URL)
        code.make(fit=True)
        matrix = code.get_matrix()
        with Image.open(png) as image:
            image = image.convert("L")
            self.assertEqual(image.size, (len(matrix) * 40, len(matrix) * 40))
            for row, cells in enumerate(matrix):
                for column, dark in enumerate(cells):
                    pixel = image.getpixel((column * 40 + 20, row * 40 + 20))
                    self.assertEqual(pixel < 128, dark, (row, column))


if __name__ == "__main__":
    unittest.main()


class SelectedShootsTests(unittest.TestCase):
    def test_shoots_render_only_when_the_manifest_lists_them(self):
        photos = load_photography_manifest(MANIFEST)
        self.assertNotIn("Selected shoots", render_photo_site(photos, root=ROOT))
        page = render_photo_site(photos, root=ROOT, shoots=[{"project": "Test shoot", "type": "Event", "year": "2025"}])
        self.assertIn("Selected shoots", page)
        self.assertIn("Test shoot", page)

    def test_manifest_shoots_need_a_project_name(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "photography.json"
            path.write_text(json.dumps({"version": 1, "entries": [], "site": {"shoots": [{"type": "Event"}]}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_photo_site_settings(path)
