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
    INQUIRY_EMAIL,
    PHOTO_SITE_END,
    PHOTO_SITE_CARD_URL,
    PHOTO_SITE_START,
    PHOTO_SITE_URL,
    SIZED_DIR,
    apply_photo_site,
    build_photo_sets,
    group_photo_site,
    import_photography_inbox,
    load_photo_sets,
    load_photo_site_settings,
    load_photography_manifest,
    missing_sized_images,
    render_darkroom,
    GALLERY_PREVIEW,
    render_photo_site,
    set_folder,
    set_title_from_slug,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/photography.json"
SETS = ROOT / "data/photo-sets.json"
PHOTO_SITE = ROOT / "photography/index.html"
RIO_IDS = {"rio-brahma-corner", "rio-fog-islands-moon", "rio-two-brothers", "rio-santa-teresa-trams"}


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

    def test_homepage_photography_goes_straight_to_the_photos(self):
        photos = load_photography_manifest(MANIFEST)
        markup = render_darkroom(photos)

        self.assertIn('<span class="ch-num">CH. 03</span>', markup)
        self.assertIn("Photography", markup)
        # no Darkroom preamble: header, filters, then pictures
        for gone in ("Darkroom", "darkroom-note", "Selected sequence", "Continue the sequence", "The archive"):
            self.assertNotIn(gone, markup)
        self.assertIn('href="photography/#book"', markup)
        self.assertIn('href="photography/"', markup)
        self.assertIn("Full photography site&nbsp;&rarr;", markup)

    def test_gallery_shows_a_preview_and_a_see_more_toggle(self):
        photos = load_photography_manifest(MANIFEST)
        markup = render_darkroom(photos)

        self.assertIn('class="photo-grid rv" id="photoGallery"', markup)
        self.assertEqual(markup.count('class="photo-item gallery-tile'), len(photos))
        self.assertEqual(markup.count(" is-extra"), max(0, len(photos) - GALLERY_PREVIEW))
        self.assertIn('data-closed-label="See more"', markup)
        self.assertRegex(markup, r'<span class="darkroom-more__count">\d+ more photos</span>')
        for chapter in ("people", "places", "gatherings"):
            self.assertIn(f'data-chapter="{chapter}"', markup)
        self.assertIn('aria-pressed="true"', markup)
        # every tile carries its real ratio and dimensions (no layout shift)
        self.assertEqual(markup.count("--r:"), len(photos))
        self.assertNotRegex(markup, r"<img(?![^>]*width=)[^>]*>")

    def test_homepage_gallery_links_to_sets_that_have_photos(self):
        photos = load_photography_manifest(MANIFEST)
        sets = load_photo_sets(SETS)
        markup = render_darkroom(photos, sets)
        self.assertIn('aria-label="Photo sets"', markup)
        self.assertIn('href="photography/#set-rio-de-janeiro">Rio de Janeiro&nbsp;&rarr;</a>', markup)
        # an empty set gets no link, and no sets means no row at all
        with_empty = sets + [{"slug": "oregon", "title": "Oregon"}]
        self.assertNotIn("#set-oregon", render_darkroom(photos, with_empty))
        loose = [{key: value for key, value in photo.items() if key != "set"} for photo in photos]
        self.assertNotIn("Photo sets", render_darkroom(loose, []))

    def test_homepage_contains_rendered_gallery_markers(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("<!-- PHOTOGRAPHY:START -->", page)
        self.assertIn("<!-- PHOTOGRAPHY:END -->", page)
        self.assertIn('class="photo-grid rv" id="photoGallery"', page)

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
            self.assertNotIn("set", payload["entries"][0])
            # loose photos never create a sets file
            self.assertFalse((root / "data/photo-sets.json").exists())

    def test_inbox_subfolder_imports_into_a_set_and_registers_it(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "photos/inbox/north-carolina"
            folder.mkdir(parents=True)
            (root / "photos/inbox/README.md").write_text("notes", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data/photography.json").write_text('{"version": 1, "entries": []}', encoding="utf-8")
            (root / "data/photo-sets.json").write_text(
                json.dumps({"version": 1, "sets": [{"slug": "rio-de-janeiro", "title": "Rio de Janeiro"}]}),
                encoding="utf-8",
            )
            Image.new("RGB", (40, 30), "blue").save(folder / "IMG_0001.jpg")
            Image.new("RGB", (40, 30), "green").save(folder / "IMG_0002.png")

            imported = import_photography_inbox(root)
            self.assertEqual(len(imported), 2)
            for entry in imported:
                self.assertEqual(entry["set"], "north-carolina")
                self.assertFalse(entry["published"])
                self.assertEqual(entry["chapter"], "places")
                # letters-only folder keeps the mirror's ([a-z]+)-(.+)-480.webp pattern intact
                self.assertTrue(entry["src"].startswith("photos/northcarolina/north-carolina-"), entry["src"])
                self.assertTrue((root / entry["src"]).is_file())
            sets = load_photo_sets(root / "data/photo-sets.json")
            self.assertEqual(
                [(item["slug"], item["title"]) for item in sets],
                [("rio-de-janeiro", "Rio de Janeiro"), ("north-carolina", "North Carolina")],
            )
            # a second run adds nothing, and the set is not duplicated
            self.assertEqual(import_photography_inbox(root), [])
            self.assertEqual(len(load_photo_sets(root / "data/photo-sets.json")), 2)

    def test_set_titles_and_folders_from_slugs(self):
        self.assertEqual(set_title_from_slug("north-carolina"), "North Carolina")
        self.assertEqual(set_title_from_slug("rio-de-janeiro"), "Rio de Janeiro")
        self.assertEqual(set_title_from_slug("oregon"), "Oregon")
        self.assertEqual(set_folder("north-carolina"), "northcarolina")
        self.assertRegex(set_folder("tokyo-2025"), r"^[a-z]+$")


class PhotoSetTests(unittest.TestCase):
    def test_rio_is_the_only_seeded_set_and_holds_exactly_the_rio_photos(self):
        photos = load_photography_manifest(MANIFEST)
        sets = load_photo_sets(SETS)
        self.assertEqual([item["slug"] for item in sets], ["rio-de-janeiro"])
        built = build_photo_sets(photos, sets)
        self.assertEqual(len(built), 1)
        self.assertEqual({frame["id"] for frame in built[0]["frames"]}, RIO_IDS)
        self.assertTrue(all(frame["src"].startswith("photos/shop/rio-") for frame in built[0]["frames"]))
        self.assertEqual(built[0]["frames"][0]["id"], sets[0]["cover"])
        # nothing outside photos/shop/rio-* claims a set yet
        self.assertEqual({photo["id"] for photo in photos if photo.get("set")}, RIO_IDS)

    def test_sets_without_published_photos_do_not_render(self):
        photos = load_photography_manifest(MANIFEST)
        sets = load_photo_sets(SETS) + [{"slug": "oregon", "title": "Oregon", "place": "USA"}]
        self.assertEqual([item["slug"] for item in build_photo_sets(photos, sets)], ["rio-de-janeiro"])
        page = render_photo_site(photos, root=ROOT, sets=sets)
        self.assertNotIn("set-oregon", page)
        self.assertNotIn("Oregon", page)

    def test_a_new_set_renders_as_a_card_with_a_deep_link(self):
        photos = [dict(photo) for photo in load_photography_manifest(MANIFEST)]
        for photo in photos:
            if photo["src"].startswith("photos/landscape/"):
                photo["set"] = "oregon"
        sets = load_photo_sets(SETS) + [{"slug": "oregon", "title": "Oregon", "year": "2024", "blurb": "Fog and pines."}]
        page = render_photo_site(photos, root=ROOT, sets=sets)
        self.assertIn('<article class="set-card rv" data-set="set-oregon">', page)
        self.assertIn('href="#set-oregon" data-open="set-oregon" data-index="0"', page)
        self.assertIn('<section class="gallery" id="set-oregon"', page)
        self.assertIn("2024 &middot; 09 frames", page)
        self.assertIn("Fog and pines.", page)
        # set order follows the file: Rio first
        self.assertLess(page.index('data-set="set-rio-de-janeiro"'), page.index('data-set="set-oregon"'))
        # a set frame from a folder group still shows in that group too
        self.assertIn('<section class="gallery" id="landscapes"', page)

    def test_unknown_set_reference_fails_loudly(self):
        photos = [dict(photo) for photo in load_photography_manifest(MANIFEST)]
        photos[5]["set"] = "atlantis"
        with self.assertRaises(ValueError):
            render_photo_site(photos, root=ROOT)

    def test_sets_file_is_validated(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "photo-sets.json"
            for bad in (
                {"version": 1, "sets": [{"slug": "North Carolina", "title": "x"}]},
                {"version": 1, "sets": [{"slug": "a", "title": "A"}, {"slug": "a", "title": "B"}]},
                {"version": 1, "sets": [{"slug": "a"}]},
                {"version": 1, "sets": [{"slug": "a", "title": "A", "price": "10"}]},
                {"version": 2, "sets": []},
            ):
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaises(ValueError, msg=bad):
                    load_photo_sets(path)
            self.assertEqual(load_photo_sets(Path(directory) / "missing.json"), [])

    def test_manifest_rejects_a_malformed_set_slug(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "photography.json"
            entry = dict(load_photography_manifest(MANIFEST)[0], set="Rio De Janeiro")
            path.write_text(json.dumps({"version": 1, "entries": [entry]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_photography_manifest(path)


class _Tags(HTMLParser):
    """Collects start tags with their attributes."""

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


class _MirrorGrab(HTMLParser):
    """What curious-and-creative's scripts/refresh_content.py sees: for each <img>
    outside script/style/noscript, the last srcset candidate, else src."""

    def __init__(self):
        super().__init__()
        self.imgs: list[dict[str, str]] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "template"):
            self._skip += 1
        if tag == "img" and not self._skip:
            src = a.get("src") or a.get("data-src") or ""
            srcset = a.get("srcset") or a.get("data-srcset") or ""
            if srcset:
                candidates = [c.strip().split(" ")[0] for c in srcset.split(",") if c.strip()]
                src = candidates[-1] if candidates else src
            if src:
                self.imgs.append({"src": src, "alt": a.get("alt", "")})

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self._skip:
            self._skip -= 1


def _visible_text(page: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S | re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return re.sub(r"<[^>]+>", " ", text)


def _view(page: str, view_id: str) -> str:
    start = page.index(f'id="{view_id}" data-view="{view_id}"')
    following = [page.find('data-view="', start + 40)]
    end = min([index for index in following if index > 0] or [page.index(PHOTO_SITE_END)])
    return page[start:end]


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
            render_photo_site(self.photos, root=ROOT, sets=load_photo_sets(SETS), shoots=settings["shoots"]),
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

    def test_four_views_in_nav_order(self):
        views = re.findall(r'<(?:div|section) class="view view--(\w+)[^"]*" id="(\w+)" data-view="(\w+)"', self.page)
        self.assertEqual([v[0] for v in views], ["work", "about", "services", "book"])
        self.assertTrue(all(a == b == c for a, b, c in views))
        nav = self.page[self.page.index('<nav class="nav-links"'):]
        nav = nav[: nav.index("</nav>")]
        self.assertEqual(re.findall(r'href="([^"]+)"', nav), ["#work", "#about", "#services"])
        self.assertIn('class="nav-book" href="#book" data-nav="book"', self.page)
        header = self.page[: self.page.index("</header>")]
        self.assertIn("Joshua McKenzie German", header)
        self.assertIn(">Photography<", header)
        self.assertIn('class="nav-home" href="../"', self.page)
        # each view has one heading the router focuses
        for view in ("work", "about", "services", "book"):
            self.assertEqual(_view(self.page, view).count("data-view-heading"), 1, view)

    def test_views_are_plain_sections_without_js(self):
        """Hidden only under :root[data-page], which only the scripts set."""
        self.assertIn(":root[data-page] .view { display: none; }", self.page)
        self.assertNotRegex(self.page, r'class="view[^"]*"[^>]*\shidden\b')
        head_script = self.page[self.page.index("<script>"): self.page.index("</script>")]
        self.assertIn("data-page", head_script)
        # router: hash routing with back/forward, focus and aria-current
        self.assertIn("window.addEventListener('hashchange', route)", self.page)
        self.assertIn("aria-current", self.page)
        self.assertIn("heading.focus({ preventScroll: true })", self.page)

    def test_work_view_leads_with_sets_then_more_work(self):
        work = _view(self.page, "work")
        self.assertIn('id="hero"', work)
        self.assertLess(work.index('id="sets"'), work.index('id="more"'))
        self.assertLess(work.index('id="more"'), work.index('id="galleries"'))
        card = work[work.index('<article class="set-card'): ]
        card = card[: card.index("</article>")]
        self.assertIn("Rio de Janeiro", card)
        self.assertIn("Brazil &middot; 04 frames", card)
        self.assertIn('href="#set-rio-de-janeiro" data-open="set-rio-de-janeiro"', card)
        self.assertIn('href="../shop.html"', card)
        for slug in ("portraits", "fashion", "events", "landscapes", "travel"):
            self.assertIn(f'<article class="card rv" data-set="{slug}">', work)
            self.assertIn(f'<section class="gallery" id="{slug}"', work)
        self.assertIn('<section class="gallery" id="set-rio-de-janeiro"', work)
        # Rio frames live in the set, not in a leftover group
        self.assertNotIn('id="archive"', work)

    def test_hero_is_short_and_leads_with_booking(self):
        hero = self.page[self.page.index('<section class="hero"'):]
        hero = hero[: hero.index("</section>")]
        self.assertIn("Joshua McKenzie <em>German</em>", hero)
        self.assertIn('href="#book">Book a shoot', hero)
        self.assertIn('fetchpriority="high"', hero)
        self.assertEqual(self.page.count('fetchpriority="high"'), 1)
        self.assertEqual(self.page.count('loading="eager"'), 1)
        self.assertNotIn("hospitality", hero.lower())

    def test_every_published_photo_appears_in_a_gallery(self):
        for photo in self.photos:
            self.assertIn(f'data-full="../{photo["src"]}"', self.page, photo["id"])
        placed = [frame["id"] for project in group_photo_site(self.photos) for frame in project["frames"]]
        placed += [frame["id"] for item in build_photo_sets(self.photos, load_photo_sets(SETS)) for frame in item["frames"]]
        self.assertEqual(set(placed), {photo["id"] for photo in self.photos})

    def test_network_mirror_contract(self):
        """curious-and-creative mirrors this page: every published photo needs an
        <img> whose src (or last srcset candidate) matches /_sized/([a-z]+)-(.+)-480.webp,
        server-rendered (so in every view), with its real alt, and the file must exist."""
        grab = _MirrorGrab()
        grab.feed(self.page)
        mirrored: dict[tuple[str, str], str] = {}
        for img in grab.imgs:
            match = re.search(r"/_sized/([a-z]+)-(.+)-480\.webp$", img["src"])
            if match:
                mirrored.setdefault((match.group(1), match.group(2)), img["alt"])
                self.assertTrue((PHOTO_SITE.parent / img["src"]).resolve().is_file(), img["src"])
        for photo in self.photos:
            source = Path(photo["src"])
            key = (source.parent.name, source.stem)
            self.assertRegex(source.parent.name, r"^[a-z]+$", photo["src"])
            self.assertIn(key, mirrored, photo["id"])
            # the first match carries the alt the mirror keeps
            self.assertEqual(mirrored[key], photo["alt"], photo["id"])
            # larger copies the mirror tries first stay available where they were made
            self.assertTrue((ROOT / SIZED_DIR / f"{key[0]}-{key[1]}-480.webp").is_file())
        # the folders the mirror's registry knows today
        self.assertTrue({"portraits", "fashion", "events", "shop", "landscape", "travel"} <= {k[0] for k in mirrored})

    def test_commercial_is_one_line_not_locked_cards(self):
        text = _visible_text(self.page).lower()
        for gone in ("locked", "now booking", "in development", "good fits", "real estate & spaces",
                     "hospitality & locations", "not client work", "shot list"):
            self.assertNotIn(gone, text)
        services = _view(self.page, "services")
        self.assertIn("Also booking: product, food and spaces.", services)
        self.assertNotIn("card--locked", self.page)

    def test_services_is_a_short_list_and_one_button(self):
        services = _view(self.page, "services")
        self.assertEqual(services.count('class="svc-row"'), 3)
        self.assertEqual(services.count('class="btn btn-safelight"'), 1)
        self.assertIn("Rates quoted per project", services)
        text = _visible_text(services).lower()
        for gone in ("strategy", "strategist", "brief", "add-on", "cut-downs", "how it works"):
            self.assertNotIn(gone, text)
        self.assertLess(len(text.split()), 70)

    def test_about_is_short_and_names_no_agencies(self):
        about = _view(self.page, "about")
        copy = about[about.index('class="about-copy'):]
        text = _visible_text(copy)
        self.assertLessEqual(len(re.findall(r"[.!?](?:\s|$)", text.replace("joshuamgerman.com", ""))), 3)
        page_text = _visible_text(self.page).lower()
        for name in ("goodby", "wieden", "tbwa", "chiat", "strategist", "brand strategy"):
            self.assertNotIn(name, page_text)
        self.assertIn('href="../"', about)
        self.assertEqual(about.count("<img"), 1)

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
        for value in ("portrait", "fashion", "event", "product", "food", "space", "other"):
            self.assertIn(f'<option value="{value}">', form)
        self.assertIn("<option>Business card</option>", form)
        self.assertIn("Photo inquiry: ", self.page)
        self.assertIn(f'href="mailto:{INQUIRY_EMAIL}"', self.page)
        self.assertIn('href="https://instagram.com/jgerms20"', self.page)
        # old ?shoot= links still land on a real option
        self.assertIn("'real-estate': 'space'", self.page)

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
                       "two podcasts", "extend", "open call", "first set", "select clients"):
            self.assertNotIn(phrase, text)
        self.assertNotRegex(text, r"\bmuse\b")
        self.assertIn("rates quoted per project", text)

    def test_links_back_to_the_main_site_and_prints(self):
        self.assertIn('href="../shop.html"', self.page)
        self.assertIn('href="../"', self.page)
        self.assertIn('href="../index.html"', self.page)

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
        # Everything a phone can fetch in the Work view above the galleries (hero,
        # set cards, group covers, at their largest candidate) stays well under ~2 MB.
        work = _view(self.page, "work")
        first_screen = work[: work.index('id="galleries"')]
        total = 0
        for attrs in (a for t, a in _parse(first_screen) if t == "img"):
            largest = attrs["srcset"].split(",")[-1].split()[0] if attrs.get("srcset") else attrs["src"]
            total += (PHOTO_SITE.parent / largest).resolve().stat().st_size
        self.assertLess(total, 1_400_000, total)

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


class MoreWorkTests(unittest.TestCase):
    def test_project_key_overrides_the_folder(self):
        photos = [dict(photo) for photo in load_photography_manifest(MANIFEST)]
        photos[0]["project"] = "Fashion"
        photos[1]["project"] = "Night Market Series"
        grouped = {project["slug"]: project for project in group_photo_site(photos)}
        self.assertIn(photos[0]["id"], [frame["id"] for frame in grouped["fashion"]["frames"]])
        self.assertEqual(grouped["night-market-series"]["title"], "Night Market Series")

    def test_a_group_slug_never_takes_a_view_or_set_id(self):
        photos = [dict(photo) for photo in load_photography_manifest(MANIFEST)]
        photos[6]["project"] = "About"
        photos[7]["project"] = "Set Piece"
        slugs = {project["slug"] for project in group_photo_site(photos)}
        self.assertIn("work-about", slugs)
        self.assertIn("work-set-piece", slugs)

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


if __name__ == "__main__":
    unittest.main()
