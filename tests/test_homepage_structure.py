from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "index.html").read_text(encoding="utf-8")


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.body_sections = []
        self.nav_links = []
        self.mobile_links = []
        self.ep_cover = None
        self._depth = 0
        self._in_nav_links = False
        self._in_mobile = False
        self._link = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "section" and attrs.get("id"):
            self.body_sections.append(attrs["id"])
        if tag == "div" and "nav-links" in classes:
            self._in_nav_links = True
        if tag == "div" and attrs.get("id") == "mobileMenu":
            self._in_mobile = True
        if tag == "a" and (self._in_nav_links or self._in_mobile):
            self._link = attrs.get("href")
            self._text = []
        if tag == "img" and attrs.get("id") == "ep-show-cover":
            self.ep_cover = attrs

    def handle_endtag(self, tag):
        if tag == "a" and self._link is not None:
            label = " ".join("".join(self._text).split())
            target = self.nav_links if self._in_nav_links else self.mobile_links
            target.append((self._link, label))
            self._link = None
        if tag == "div" and (self._in_nav_links or self._in_mobile) and self._link is None:
            self._in_nav_links = False
            self._in_mobile = False

    def handle_data(self, data):
        if self._link is not None:
            self._text.append(data)


class HomepageStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = _Collector()
        cls.page.feed(PAGE)

    def test_chapters_run_brand_work_podcasts_network_photography_ai(self):
        self.assertEqual(
            self.page.body_sections,
            [
                "hero",
                "about",
                "work",
                "podcasts",
                "network",
                "photography",
                "ai",
                "media-diet",
                "in-the-works",
                "contact",
            ],
        )

    def test_desktop_nav_follows_the_new_order(self):
        self.assertEqual(
            self.page.nav_links,
            [
                ("#about", "About"),
                ("#work", "Brand Work"),
                ("#podcasts", "Podcasts"),
                ("#network", "Curious & Creative"),
                ("#photography", "Photography"),
                ("#ai", "AI"),
                ("#art", "Art"),
                ("shop.html", "Shop"),
            ],
        )

    def test_mobile_menu_matches_nav_and_ends_with_contact(self):
        self.assertEqual(
            [href for href, _ in self.page.mobile_links],
            [
                "#about", "#work", "#podcasts", "#network", "#photography", "#ai", "#art",
                "shop.html", "#contact", "photography/#book",
            ],
        )
        # Chapter links carry the same numbers as the chapter heads (CH. 01-05);
        # Shop and Contact are not chapters, so they must not borrow CH. 07/08.
        numbered = [label for _, label in self.page.mobile_links if label[:2].isdigit()]
        self.assertEqual(numbered, ["01 About", "02 Brand Work", "03 Podcasts", "04 Photography", "05 AI"])
        for number, section in (("02", "work"), ("03", "podcasts"), ("04", "photography"), ("05", "ai")):
            head = PAGE[PAGE.index(f'<section id="{section}"'):]
            self.assertIn(f'<span class="ch-num">CH. {number}</span>', head[:600], section)
        # the Network band is a feature, not a numbered chapter
        network = dict(self.page.mobile_links)["#network"]
        self.assertFalse(network[:2].isdigit(), network)
        self.assertTrue(self.page.mobile_links[-1][1].startswith("Book a shoot"))

    def test_collection_and_interviews_are_one_compact_band_after_media_diet(self):
        band = PAGE[PAGE.index('<section id="in-the-works"'):]
        band = band[: band.index("</section>")]
        self.assertIn('id="collection"', band)
        self.assertIn('id="interviews"', band)
        self.assertIn('href="shop.html"', band)
        self.assertIn('href="mailto:', band)
        self.assertNotIn("veil", PAGE)

    def test_network_band_follows_podcasts_and_links_to_the_hub(self):
        band = PAGE[PAGE.index('<section id="network"'):]
        band = band[: band.index("</section>")]
        self.assertIn('href="network/"', band)
        self.assertIn("Janel Moore", band)
        self.assertIn("jgerms20.github.io/curious-and-creative", band)

    def test_no_culture_chapter_and_advisory_work_is_public_in_brand_work(self):
        self.assertNotIn('id="projects"', PAGE)
        self.assertNotIn("openStartupGate", PAGE)
        self.assertNotIn("startup-locked", PAGE)
        work = PAGE[PAGE.index('<section id="work"'):]
        work = work[: work.index("</section>")]
        self.assertEqual(work.count('data-agency="independent"'), 3)  # filter + HIIKE + U&AI
        self.assertEqual(work.count("plate-startup"), 2)  # their own cards, flagged as startups
        self.assertEqual(work.count("Startup &middot; Independent"), 2)
        self.assertNotIn("plate-group", work)
        self.assertIn("Fractional Chief Marketing Officer", work)
        self.assertIn("HIIKE", work)
        self.assertIn("U&amp;AI", work)

    def test_about_keeps_it_personal_and_accurate(self):
        about = PAGE[PAGE.index('<section id="about"'):]
        about = about[: about.index("</section>")]
        self.assertIn("South Carolina", about)
        self.assertNotIn("Pepsi", PAGE)
        self.assertNotIn("Signal Trace", PAGE)
        for tool in ("Claude", "Codex", "Gemini"):
            self.assertNotIn(tool, about)
        self.assertIn('id="selfRotator"', about)
        self.assertNotIn("data-count", PAGE)  # no quantified hero stats

    def test_art_section_shows_every_collage(self):
        works = PAGE[PAGE.index('<section id="in-the-works"'):]
        works = works[: works.index("</section>")]
        art = works[works.index('id="art"'):]
        import re
        pieces = re.findall(r'data-full="(photos/art/[^"]+)"', art)
        self.assertEqual(len(pieces), 6)
        for full in pieces:
            self.assertTrue((ROOT / full).is_file(), full)
            self.assertTrue((ROOT / full.replace(".jpg", "-sm.jpg")).is_file(), full)

    def test_eclectic_polymath_cover_can_load(self):
        cover = self.page.ep_cover
        self.assertIsNotNone(cover)
        # Chrome never fetches a lazy image that is display:none, which hid the cover.
        self.assertNotEqual(cover.get("loading"), "lazy")
        self.assertNotIn("display:none", (cover.get("style") or "").replace(" ", ""))
        self.assertIn('class="ep-fallback"', PAGE)
        # the real cover ships with the site; no dependency on Spotify
        self.assertEqual(cover.get("src"), "photos/podcasts/eclectic-polymath-cover.jpg")

    def test_public_copy_has_no_internal_or_solo_notes(self):
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", PAGE, flags=re.S | re.I)
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text).lower()
        for phrase in ("solo", "no guests", "live catalog", "twice weekly", "newest first"):
            self.assertNotIn(phrase, text)

    def test_hero_cta_block_is_booking_first(self):
        hero = PAGE[PAGE.index('<section id="hero"'):]
        hero = hero[: hero.index("</section>")]
        self.assertIn("Now booking independent work", hero)
        self.assertIn('href="photography/#book"', hero)

    def test_contact_pitches_independent_work_only(self):
        contact = PAGE[PAGE.index('<section id="contact"'):]
        contact = contact[: contact.index("</section>")]
        self.assertNotIn("Full-time", contact)
        self.assertIn('href="photography/#book"', contact)
        self.assertIn("subject=Project%20inquiry", contact)

    def test_metadata_leads_with_the_new_positioning(self):
        head = PAGE[: PAGE.index("</head>")]
        self.assertNotIn("| Creative Strategist</title>", head)
        lead = "Joshua McKenzie German | Creative &amp; Cultural Strategist, Photographer, Podcaster, AI Builder"
        self.assertIn(f"<title>{lead}</title>", head)
        self.assertIn(f'property="og:title" content="{lead}"', head)
        hero = PAGE[PAGE.index('<section id="hero"'):]
        roles = re.findall(r'<span class="hero-role">(.*?)</span>', hero[: hero.index("</section>")])
        self.assertEqual(roles, ["Creative &amp; Cultural Strategist", "Photographer", "Podcaster", "AI Builder &amp; Creator"])

    def test_in_the_works_does_not_overclaim(self):
        self.assertNotIn("In production", PAGE)
        self.assertNotIn("in production", PAGE.lower().replace("post-production", ""))

    def test_sites_chapter_is_off_for_now(self):
        self.assertNotIn("sites-rail", PAGE)
        self.assertNotIn("data-gate", PAGE)

    def test_brand_work_leads_with_the_best_campaigns(self):
        work = PAGE[PAGE.index('<section id="work"'):]
        work = work[: work.index("</section>")]
        hrefs = re.findall(r'<a href="([^"]+)" class="plate\b', work)
        self.assertEqual(hrefs[:7], [
            "work/work-levis.html", "work/work-gatorade.html#stranger-things", "work/work-doordash.html",
            "work/work-dwb.html", "work/work-gatorade.html#body-of-science", "work/work-gatorade.html#lower-sugar",
            "work/work-directv.html#like-never-seen",
        ])
        self.assertLess(hrefs.index("work/work-sephora.html#skincare"), hrefs.index("work/work-gatorade.html#nfl"))
        # every campaign card shows a picture (or a brand tile), never an empty box
        for card in re.findall(r'<a href="[^"]+" class="plate\b.*?</a>', work, re.S):
            self.assertTrue("<img" in card or "plate-media-brand" in card, card[:120])

    def test_ai_lab_leads_with_gen_alpha_then_life_gamified(self):
        ai = PAGE[PAGE.index('<section id="ai"'):]
        ai = ai[: ai.index("</section>")]
        titles = re.findall(r'class="lab-title">(.*?) <svg', ai)
        self.assertEqual(titles[:6], ["Gen Alpha Intelligence Lab", "Life Gamified", "Archive", "Veritas",
                                      "The Man and the Machine", "Creator Search"])
        self.assertIn('class="lab-card lab-hero', ai)
        self.assertLess(titles.index("Creator Search"), titles.index("Dreamcatcher"))

    def test_network_band_names_the_network_and_drops_god_is_brazilian(self):
        band = PAGE[PAGE.index('<section id="network"'):]
        band = band[: band.index("</section>")]
        self.assertIn("The Curious &amp; Creative Network", band)
        self.assertNotIn("brazil", band)
        self.assertIn("network/art/dominate.jpg", band)

    def test_contact_invites_collaboration(self):
        contact = PAGE[PAGE.index('<section id="contact"'):]
        contact = contact[: contact.index("</section>")]
        self.assertIn("Let&rsquo;s create<br><span class=\"it\">together.</span>", contact)
        self.assertIn("From Columbia to Los Angeles, same instinct the whole way", contact)
        self.assertNotIn("by way of", contact)

    def test_every_public_page_has_the_tab_icon(self):
        for rel in ("index.html", "shop.html", "network/index.html", "photography/index.html",
                    "podcasts/podcast-eclectic-polymath.html", "work/work-levis.html"):
            page = (ROOT / rel).read_text(encoding="utf-8")
            up = "../" * rel.count("/")
            self.assertIn(f'<link rel="icon" href="{up}favicon.svg" type="image/svg+xml">', page, rel)
            self.assertIn(f'<link rel="apple-touch-icon" href="{up}apple-touch-icon.png">', page, rel)
        for asset in ("favicon.svg", "favicon.ico", "apple-touch-icon.png", "site.webmanifest"):
            self.assertTrue((ROOT / asset).is_file(), asset)


if __name__ == "__main__":
    unittest.main()
