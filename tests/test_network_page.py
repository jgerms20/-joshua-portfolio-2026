from html.parser import HTMLParser
import html as html_lib
from pathlib import Path
import json
import re
import unittest
from urllib.parse import parse_qs, urlparse

from portfolio_quality.html_checks import check_page


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "network/index.html"
NETWORK_SITE = "https://jgerms20.github.io/curious-and-creative/"
CONTACT = NETWORK_SITE + "pages/contact.html"
# The company's current pitch, used verbatim as the page's lead.
PITCH = (
    "Curious &amp; Creative is a Los Angeles creative company built by Joshua German and Janel Moore. "
    "We run a media network, produce photography, video, editing, and podcasts through our studio, "
    "and advise founders, brands, and marketing teams on culture, audience, and AI."
)
# The three legs of the company and the company-site page each one links out to.
LEGS = {
    "The Network": NETWORK_SITE + "pages/network.html",
    "The Studio": NETWORK_SITE + "pages/studio.html",
    "The Consultancy": NETWORK_SITE + "pages/consultancy.html",
}
STUDIO_OFFERS = (
    "Photography", "Event coverage", "Video", "Editing", "Podcast production", "Websites",
)
CONSULTANCY_OFFERS = (
    "Brand and cultural strategy", "Audience systems", "Podcast strategy",
    "AI workflow design and enablement",
)
# Brand work is agency work; if the page names it, it uses exactly this line.
FOUNDERS_LINE = (
    "Our founders bring experience from work on Levi's, Gatorade, DoorDash, DIRECTV, "
    "Sephora, MLB, and BMW."
)
CONTACT_LEGS = {"network", "studio", "consultancy"}
CONTACT_TOPICS = {"photo", "events", "strategy", "ai", "project"}

# Every show in the network's static roster and where each card must link:
# Joshua's shows go to his own show pages in this repo, the others to Spotify.
SHOWS = {
    "ccpod": ("The Curious", "../podcasts/podcast-curious-creative.html"),
    "polymath": ("The Eclectic Polymath", "../podcasts/podcast-eclectic-polymath.html"),
    "brazil": ("God Is Brazilian", "https://open.spotify.com/show/4tAY78JV37aIgmJ2d1iF3w"),
    "riff": ("The Daily Riff", "https://open.spotify.com/show/79MaSzrv6uJkaHiFoZQrWk"),
    "morningread": ("The Morning Read", "https://open.spotify.com/show/1Dtk8svL8ahjAPtso2lBMp"),
    "approachable": ("Approachable AI", "../podcasts/podcast-approachable-ai.html"),
    "tmtt": ("Too Much to Tweet", "https://open.spotify.com/show/033G4KctzeuD3Pu4db1AQa"),
    "abolitionist": ("Aspiring Abolitionist", "https://open.spotify.com/show/7natfWFnBgakjLLZcEDZaw"),
    "dominate": ("Dominate the Decade", "../podcasts/podcast-dominate.html"),
}


def _text(html):
    """Visible-ish text: tags stripped, entities kept as written, whitespace collapsed."""
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S)
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


class _Collector(HTMLParser):
    """Collects links, metas, and the text of each [data-show] card."""

    def __init__(self):
        super().__init__()
        self.links, self.metas, self.anchors, self.images = [], [], [], []
        self.cards = {}  # key -> {"href": str, "text": str}
        self._stack = []  # (tag, card_key or None)
        self._card = None
        self._in_script = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link":
            self.links.append(attrs)
        elif tag == "meta":
            self.metas.append(attrs)
        elif tag == "img":
            self.images.append(attrs)
        elif tag == "script":
            self._in_script = True
            self.scripts.append({"attrs": attrs, "text": ""})
        if tag == "a":
            self.anchors.append(attrs)
        key = attrs.get("data-show")
        if key and self._card is None:
            self._card = key
            self.cards[key] = {"href": attrs.get("href", ""), "text": ""}
        elif self._card and tag == "a" and not self.cards[self._card]["href"]:
            self.cards[self._card]["href"] = attrs.get("href", "")
        if tag not in ("img", "meta", "link", "br", "input"):
            self._stack.append((tag, key))

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False
        while self._stack:
            open_tag, key = self._stack.pop()
            if key and key == self._card:
                self._card = None
            if open_tag == tag:
                break

    def handle_data(self, data):
        if self._in_script:
            self.scripts[-1]["text"] += data
        elif self._card:
            self.cards[self._card]["text"] += data


class NetworkPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.parsed = _Collector()
        cls.parsed.feed(cls.html)
        cls.script = "\n".join(
            s["text"] for s in cls.parsed.scripts if s["attrs"].get("type") != "application/ld+json"
        )

    def meta(self, key):
        for m in self.parsed.metas:
            if m.get("property") == key or m.get("name") == key:
                return m.get("content")
        return None

    def test_canonical_and_social_tags(self):
        canon = [l.get("href") for l in self.parsed.links if l.get("rel") == "canonical"]
        self.assertEqual(canon, ["https://joshuamgerman.com/network/"])
        self.assertEqual(self.meta("og:url"), "https://joshuamgerman.com/network/")
        self.assertIn("Curious", self.meta("og:title"))
        self.assertIn("Curious", self.meta("twitter:title"))
        self.assertEqual(self.meta("twitter:card"), "summary_large_image")
        self.assertIn("Curious &amp; Creative", re.search(r"<title>(.*?)</title>", self.html).group(1))
        # every description carries the current pitch
        pitch = html_lib.unescape(PITCH)
        for key in ("description", "og:description", "twitter:description"):
            self.assertEqual(self.meta(key), pitch, key)
        ld = json.loads(next(
            s["text"] for s in self.parsed.scripts if s["attrs"].get("type") == "application/ld+json"
        ))
        self.assertEqual(ld["description"], pitch)
        self.assertEqual(ld["url"], NETWORK_SITE)
        # the share image is a real file in this repo
        for key in ("og:image", "twitter:image"):
            url = self.meta(key)
            self.assertTrue(url.startswith("https://joshuamgerman.com/"), url)
            self.assertTrue((ROOT / url.removeprefix("https://joshuamgerman.com/")).is_file(), url)

    def test_pitch_is_the_lead(self):
        hero = self.html[self.html.index('<section class="hero"'):self.html.index('id="shows"')]
        lede = re.search(r'<p class="lede[^"]*"[^>]*>(.*?)</p>', hero, re.S).group(1)
        self.assertEqual(" ".join(lede.split()), PITCH)

    def test_three_legs_link_out_to_the_company_site(self):
        legs = re.search(r'<nav class="arms.*?</nav>', self.html, re.S).group(0)
        cards = re.findall(r'<a class="arm" href="([^"]+)"([^>]*)>(.*?)</a>', legs, re.S)
        self.assertEqual(len(cards), 3)
        for (href, attrs, body), (name, target) in zip(cards, LEGS.items()):
            self.assertEqual(href, target)
            self.assertIn(name, body)
            self.assertIn('target="_blank" rel="noopener"', attrs)
        hrefs = {a.get("href", "") for a in self.parsed.anchors}
        for target in LEGS.values():
            self.assertIn(target, hrefs)
        self.assertIn(NETWORK_SITE, hrefs)
        for section in ("shows", "latest", "studio", "consultancy", "photos", "duo", "pitch"):
            self.assertIn(f'id="{section}"', self.html)

    def test_contact_links_use_supported_parameters(self):
        contacts = [a.get("href", "") for a in self.parsed.anchors if a.get("href", "").startswith(CONTACT)]
        self.assertTrue(contacts)
        legs = set()
        for href in contacts:
            query = parse_qs(urlparse(href).query)
            self.assertTrue(query, href)
            self.assertLessEqual(set(query), {"leg", "topic"}, href)
            for value in query.get("leg", []):
                self.assertIn(value, CONTACT_LEGS, href)
                legs.add(value)
            for value in query.get("topic", []):
                self.assertIn(value, CONTACT_TOPICS, href)
        self.assertEqual(legs, CONTACT_LEGS)  # every leg has its own door

    def test_studio_and_consultancy_list_their_offers(self):
        studio = self.html[self.html.index('id="studio"'):self.html.index('id="consultancy"')]
        consult = self.html[self.html.index('id="consultancy"'):self.html.index('id="photos"')]
        for section, offers in ((studio, STUDIO_OFFERS), (consult, CONSULTANCY_OFFERS)):
            lists = re.findall(r'<ul class="svc[^"]*".*?</ul>', section, re.S)
            self.assertEqual(len(lists), 1)
            self.assertEqual(tuple(re.findall(r"<h3>(.*?)</h3>", lists[0])), offers)

    def test_no_counts_anywhere(self):
        text = _text(self.html)
        self.assertNotRegex(
            text, r"(?i)\d[\d,]*\+?\s*(episodes|shows|podcasts|videos|followers|listeners|subscribers)"
        )
        self.assertNotRegex(text, r"(?i)\b(eight|nine|ten|dozen)\s+(podcasts|shows)")
        self.assertNotIn("data-fact", self.html)
        # the live data never writes counts either
        self.assertNotRegex(self.script, r"\.count\b")
        self.assertNotIn("total", self.script)

    def test_no_inventions_arm(self):
        for phrase in ("Inventions", "inventions", "things we invent", "Kindling", "Gen Alpha", "kindling/"):
            self.assertNotIn(phrase, self.html, phrase)
        builds = [a for a in self.parsed.anchors if a.get("href") == "../index.html#builds"]
        self.assertTrue(builds, "no link to Joshua's builds on his portfolio")
        self.assertIn("Joshua&rsquo;s own builds and experiments live on", self.html)

    def test_company_is_not_called_an_llc(self):
        self.assertNotRegex(self.html, r"\bL\.?L\.?C\b")

    def test_brand_work_is_framed_as_agency_experience(self):
        text = html_lib.unescape(_text(self.html))
        brands = ("Levi", "Gatorade", "DoorDash", "DIRECTV", "Sephora", "MLB", "BMW")
        if any(b in text for b in brands):
            self.assertIn(FOUNDERS_LINE, text)
            stripped = text.replace(FOUNDERS_LINE, "")
            for brand in brands:
                self.assertNotIn(brand, stripped, brand)

    def test_agency_roles_are_past_tense(self):
        text = html_lib.unescape(_text(self.html))
        self.assertNotRegex(text, r"(?i)\bis an? (Senior )?(Connections )?Strategist at TBWA")
        self.assertNotRegex(text, r"(?i)Senior Connections Strategist at TBWA")
        self.assertIn(
            "Joshua spent his agency years at Goodby Silverstein & Partners, Wieden+Kennedy, "
            "and TBWA\\Chiat\\Day",
            text,
        )

    def test_fetched_data_is_never_written_as_html(self):
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            self.assertNotIn(sink, self.script)
        self.assertIn("textContent", self.script)
        # links and images from the data only ever pass through the http(s) filter
        self.assertIn("function safeUrl", self.script)
        self.assertRegex(self.script, r"url\.protocol === 'https:' \|\| url\.protocol === 'http:'")

    def test_reads_the_generated_network_snapshot(self):
        self.assertIn("'../data/network.json'", self.script)
        data = json.loads((ROOT / "data/network.json").read_text(encoding="utf-8"))
        # the fields the page reads are the ones sync-episodes.py writes
        for field in ("shows", "latest", "generated_at"):
            self.assertIn(field, data)
            self.assertIn(f"data.{field}", self.script)
        for field in ("key", "name", "hosts", "tagline", "url", "art", "latest"):
            self.assertIn(field, data["shows"][0])
        for field in ("show", "show_name", "title", "date", "url", "image"):
            self.assertIn(field, data["latest"][0])
            self.assertIn(f"item.{field}", self.script)

    def test_photo_strip_links_to_the_photography_site(self):
        photos = self.html[self.html.index('id="photos"'):self.html.index('id="duo"')]
        shots = re.findall(r'<a class="shot" href="([^"]+)"><img src="([^"]+)" alt="([^"]+)"', photos)
        self.assertGreaterEqual(len(shots), 4)
        for href, src, alt in shots:
            self.assertEqual(href, "../photography/")
            self.assertTrue((PAGE.parent / src).is_file(), src)
            self.assertTrue(alt.strip(), src)

    def test_static_markup_lists_every_show(self):
        cards = self.parsed.cards
        for key, (name, href) in SHOWS.items():
            self.assertIn(key, cards, f"no static card for {key}")
            self.assertIn(name, cards[key]["text"], key)
            self.assertEqual(cards[key]["href"], href, key)
            self.assertRegex(cards[key]["text"], r"Joshua|Janel", f"{key} card names no host")
        self.assertIn("The flagship", cards["ccpod"]["text"])
        self.assertIn("Hosted by Janel Moore", cards["tmtt"]["text"])
        self.assertIn("Hosted by Janel Moore", cards["abolitionist"]["text"])
        self.assertIn("2020", cards["dominate"]["text"])
        for key in ("brazil", "riff", "morningread"):
            self.assertIn("AI-generated", cards[key]["text"], key)
        # every card has its art in the markup, and that art exists locally
        for key in SHOWS:
            block = re.search(rf'data-art="{key}".*?<img src="([^"]+)"', self.html, re.S)
            self.assertIsNotNone(block, key)
            self.assertTrue((PAGE.parent / block.group(1)).resolve().is_file(), block.group(1))

    def test_eclectic_polymath_leads_the_roster_after_the_flagship(self):
        roster = self.html[self.html.index('id="roster"'):]
        roster = roster[: roster.index("</ul>")]
        order = re.findall(r'<li data-show="([a-z]+)"', roster)
        self.assertEqual(order[0], "polymath")
        self.assertEqual(order[-1], "dominate")  # the archive closes the list
        # the live re-sort keeps the same rule: polymath, hosted shows, AI-generated, archive
        self.assertIn("key === 'polymath' ? 0", self.script)

    def test_script_knows_every_static_show(self):
        for key in SHOWS:
            self.assertRegex(self.script, rf"\b{key}: '#[0-9A-F]{{6}}'", f"no color for {key}")
            self.assertRegex(self.script, rf"\b{key}: '[^']+\.jpg'", f"no local art for {key}")

    def test_janel_is_spelled_correctly(self):
        self.assertIn("Janel Moore", self.html)
        self.assertNotRegex(self.html, r"(?i)janelle")
        self.assertIn("Technology and finance at Truist; political fundraising veteran; artist. Hosts Too Much to Tweet.", self.html)

    def test_external_links_open_safely(self):
        for a in self.parsed.anchors:
            if a.get("target") == "_blank":
                self.assertIn("noopener", a.get("rel", ""), a.get("href"))

    def test_shares_the_site_theme_and_respects_reduced_motion(self):
        self.assertIn("localStorage.getItem('jmg-theme')", self.html)
        self.assertIn("localStorage.setItem('jmg-theme'", self.script)
        self.assertIn(':root[data-theme="dark"]', self.html)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.html)
        self.assertIn('class="skip" href="#main"', self.html)

    def test_no_internal_or_operational_copy(self):
        for pattern in (r"\bTODO\b", r"\bFIXME\b", r"\bTBD\b", r"lorem ipsum"):
            self.assertIsNone(re.search(pattern, self.html, re.IGNORECASE), pattern)

    def test_images_have_alt_text(self):
        for img in self.parsed.images:
            self.assertIn("alt", img, img.get("src"))

    def test_passes_the_production_html_checks(self):
        findings = check_page(ROOT, PAGE)
        self.assertEqual([f"{f.code}: {f.target}" for f in findings], [])


if __name__ == "__main__":
    unittest.main()
