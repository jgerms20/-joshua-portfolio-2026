from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
STUDIO = "https://jgerms20.github.io/curious-and-creative/pages/contact.html"
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

    def test_builds_lead_then_brand_work_photography_on_air(self):
        self.assertEqual(
            self.page.body_sections,
            ["hero", "builds", "work", "photography", "podcasts", "notes",
             "about", "media-diet", "in-the-works", "contact"],
        )
        for number, section in (("01", "builds"), ("02", "work"), ("03", "photography"), ("04", "podcasts"), ("05", "about")):
            head = PAGE[PAGE.index(f'<section id="{section}"'):]
            self.assertIn(f'<span class="ch-num">CH. {number}</span>', head[:900], section)
    def test_desktop_nav_follows_the_new_order(self):
        self.assertEqual(
            self.page.nav_links,
            [
                ("#about", "About"),
                ("#builds", "Work"),
                ("#lab", "Lab"),
                ("#photography", "Photography"),
                ("#podcasts", "On Air"),
                ("#notes", "Notes"),
                ("network/", "Curious & Creative"),
            ],
        )
        # Notes only shows once a real post exists
        self.assertRegex(PAGE, r'<a href="#notes" data-notes-link hidden>Notes</a>')
    def test_mobile_menu_matches_nav_and_ends_with_contact(self):
        self.assertEqual(
            [href for href, _ in self.page.mobile_links],
            ["#builds", "#lab", "#work", "#photography", "#podcasts", "network/", "#notes", "#about",
             "#art", "shop.html", "#contact", STUDIO + "?topic=photo"],
        )
        numbered = [label for _, label in self.page.mobile_links if label[:2].isdigit()]
        self.assertEqual(numbered, ["01 Builds", "02 Brand Work", "03 Photography", "04 On Air", "05 About"])
        self.assertTrue(self.page.mobile_links[-1][1].startswith("Book a shoot"))
    def test_collection_and_interviews_are_one_compact_band_after_media_diet(self):
        band = PAGE[PAGE.index('<section id="in-the-works"'):]
        band = band[: band.index("</section>")]
        self.assertIn('id="collection"', band)
        self.assertIn('id="interviews"', band)
        self.assertIn('href="shop.html"', band)
        self.assertIn('href="mailto:', band)
        self.assertNotIn("veil", PAGE)

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

    def test_hero_leads_with_the_strategist_who_builds(self):
        hero = PAGE[PAGE.index('<section id="hero"'):]
        hero = hero[: hero.index("</section>")]
        self.assertIn("I find the idea and <em>build the thing.</em>", hero)
        self.assertIn("Strategy, stories, and the things I build when nobody assigned them.", hero)
        self.assertIn("Now booking independent work", hero)
        self.assertIn("Co-founder &amp; CEO, The Curious &amp; Creative Company", hero)
        # the agency is history, never the current job
        now = hero[hero.index('class="hero-stats hero-now"'):]
        now = now[: now.index("</dl>")]
        self.assertIn("<dt>Previously</dt>", now)
        self.assertNotRegex(now, r"<dt>(Now|Strategy)</dt><dd>TBWA")
        self.assertIn(STUDIO + "?topic=photo", hero)
    def test_contact_routes_studio_work_to_the_company(self):
        contact = PAGE[PAGE.index('<section id="contact"'):]
        contact = contact[: contact.index("</section>")]
        self.assertNotIn("Full-time", contact)
        self.assertIn(STUDIO + "?topic=photo", contact)
        self.assertIn(STUDIO + "?leg=studio", contact)
        self.assertIn("subject=Project%20inquiry", contact)  # personal projects still come to Joshua
    def test_metadata_leads_with_the_new_positioning(self):
        head = PAGE[: PAGE.index("</head>")]
        lead = "Joshua McKenzie German | Creative &amp; Cultural Strategist Who Builds"
        self.assertIn(f"<title>{lead}</title>", head)
        self.assertIn(f'property="og:title" content="{lead}"', head)
        self.assertIn("Co-founder and CEO of The Curious &amp; Creative Company", head)
        self.assertNotIn("LLC", PAGE)
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

    def test_builds_open_with_three_case_studies_then_an_honest_lab(self):
        builds = PAGE[PAGE.index('<section id="builds"'):]
        builds = builds[: builds.index("</section>")]
        cases = re.findall(r'<a href="(builds/[^"]+)" class="lab-card', builds)
        self.assertEqual(cases, ["builds/gen-alpha-intelligence-lab.html", "builds/meme-library.html", "builds/life-gamified.html"])
        self.assertIn('<span class="lab-status">Invite only</span>', builds)  # Gen Alpha is not public
        self.assertIn('href="builds/"', builds)  # the full lab lives on its own page
        self.assertIn('id="ai"', builds)  # old #ai links still land here
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


    def test_field_notes_stay_hidden_until_a_real_post_exists(self):
        import json
        self.assertRegex(PAGE, r'<section id="notes"[^>]* hidden')
        data = json.loads((ROOT / "data/notes.json").read_text(encoding="utf-8"))
        self.assertIsInstance(data["posts"], list)
        for post in data["posts"]:
            self.assertIn(post["lane"], {"build-in-public", "strategists-perspective", "behind-the-work"})
            self.assertTrue(post["url"].startswith("https://"))
        script = PAGE[PAGE.index("// ---- Field Notes"):]
        script = script[: script.index("})();")]
        self.assertNotIn("innerHTML", script)

    def test_on_air_is_the_three_hosted_shows(self):
        pods = PAGE[PAGE.index('<section id="podcasts"'):]
        pods = pods[: pods.index("</section>")]
        self.assertEqual(len(re.findall(r'class="pod-card', pods)), 3)
        self.assertIn("podcasts/podcast-dominate.html", pods)  # the archive, as a line
        self.assertNotRegex(pods, r"\b(Four|Three|Eight) [Ss]hows\b")


    def test_curious_creative_is_the_founder_story_not_a_band(self):
        self.assertNotIn('<section id="network"', PAGE)
        about = PAGE[PAGE.index('<section id="about"'):]
        about = about[: about.index("</section>")]
        self.assertIn("co-founder and CEO of The Curious &amp; Creative Company", about)
        self.assertIn("My work starts with curiosity.", about)
        self.assertIn("a journalist&rsquo;s instinct to ask questions", about)
        self.assertIn('<a href="network/">Curious &amp; Creative</a>', PAGE)


if __name__ == "__main__":
    unittest.main()
