from html.parser import HTMLParser
from pathlib import Path
import json
import re
import unittest

from portfolio_quality.html_checks import check_page


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "network/index.html"
NETWORK_SITE = "https://jgerms20.github.io/curious-and-creative/"
CONTACT = NETWORK_SITE + "pages/contact.html"
GEN_ALPHA_LAB = "https://agencythings-gen-alpha.vercel.app"
COMPANY = "Curious Creative Company"
# The studio's six offers, as the Curious Creative Company site names them.
STUDIO_OFFERS = (
    "Photography", "Videography", "Podcasts from zero",
    "Brand assets", "Strategy &amp; consulting", "Events",
)

# Every show in the Curious & Creative Network and where each card must link:
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
        self.assertTrue(self.meta("description"))
        self.assertIn(COMPANY, re.search(r"<title>(.*?)</title>", self.html).group(1))
        self.assertIn(COMPANY, self.meta("description"))
        # the share image is a real file in this repo
        for key in ("og:image", "twitter:image"):
            url = self.meta(key)
            self.assertTrue(url.startswith("https://joshuamgerman.com/"), url)
            self.assertTrue((ROOT / url.removeprefix("https://joshuamgerman.com/")).is_file(), url)

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
        for field in ("key", "name", "hosts", "tagline", "url", "art", "latest", "count"):
            self.assertIn(field, data["shows"][0])
        for field in ("show", "show_name", "title", "date", "url", "image"):
            self.assertIn(field, data["latest"][0])
            self.assertIn(f"item.{field}", self.script)

    def test_page_is_framed_as_the_company_with_three_arms(self):
        h1 = re.search(r"<h1\b.*?</h1>", self.html, re.S).group(0)
        h1_text = " ".join(re.sub(r"<[^>]+>", " ", h1).split())
        self.assertEqual(h1_text, COMPANY)
        self.assertIn("Curious first. Then creative.", self.html)
        arms = re.search(r'<nav class="arms.*?</nav>', self.html, re.S).group(0)
        for target, name in (("#shows", "The Network"), ("#studio", "The Studio"), ("#inventions", "Inventions")):
            self.assertIn(f'href="{target}"', arms)
            self.assertIn(name, arms)
        for section in ("shows", "latest", "studio", "inventions", "photos", "duo", "pitch"):
            self.assertIn(f'id="{section}"', self.html)

    def test_studio_lists_the_six_offers(self):
        studio = self.html[self.html.index('id="studio"'):self.html.index('id="inventions"')]
        offers = re.findall(r'<ul class="svc".*?</ul>', studio, re.S)
        self.assertEqual(len(offers), 1)
        names = re.findall(r"<h3>(.*?)</h3>", offers[0])
        self.assertEqual(tuple(names), STUDIO_OFFERS)

    def test_gen_alpha_lab_is_the_featured_invention(self):
        inventions = self.html[self.html.index('id="inventions"'):self.html.index('id="photos"')]
        lab = re.search(r'<a class="lab".*?</a>', inventions, re.S).group(0)
        self.assertIn(f'href="{GEN_ALPHA_LAB}"', lab)
        self.assertIn('target="_blank" rel="noopener"', lab)
        self.assertIn("Gen Alpha <em>Intelligence Lab</em>", lab)
        self.assertIn(">Live<", lab)
        self.assertIn("Built with", lab)
        self.assertIn('src="../assets/genalpha.svg"', lab)
        self.assertTrue((ROOT / "assets/genalpha.svg").is_file())
        # Kindling and the other inventions carry their own art, copied locally
        self.assertIn(NETWORK_SITE + "kindling/", inventions)
        arts = re.findall(r'<img src="(art/[^"]+\.svg)"', inventions)
        self.assertGreaterEqual(len(arts), 3)
        for src in arts:
            self.assertTrue((PAGE.parent / src).is_file(), src)

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
        self.assertIn("Joshua McKenzie German &", self.html)
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

    def test_script_knows_every_static_show(self):
        for key in SHOWS:
            self.assertRegex(self.script, rf"\b{key}: '#[0-9A-F]{{6}}'", f"no color for {key}")
            self.assertRegex(self.script, rf"\b{key}: '[^']+\.jpg'", f"no local art for {key}")

    def test_janel_is_spelled_correctly(self):
        self.assertIn("Janel Moore", self.html)
        self.assertNotRegex(self.html, r"(?i)janelle")
        # her bio uses the Curious Creative Company site's current wording
        self.assertIn("Technology and finance at Truist; political fundraising veteran; artist. Hosts Too Much to Tweet.", self.html)

    def test_links_to_the_network_site_and_its_doors(self):
        hrefs = [a.get("href", "") for a in self.parsed.anchors]
        self.assertIn(NETWORK_SITE, hrefs)
        self.assertIn(CONTACT + "?topic=project", hrefs)
        self.assertIn(CONTACT + "?topic=guest", hrefs)
        self.assertIn(NETWORK_SITE + "kindling/", hrefs)
        for label in ("Visit the site", "Work with the studio", "Pitch a guest"):
            self.assertIn(label, self.html)

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
