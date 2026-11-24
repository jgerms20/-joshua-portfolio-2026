"""The six fix-now items from the grill audit (Nov 2026). Each one stays fixed."""
import json
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def jsonld(html):
    return json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))


class DoorDashClaimsTests(unittest.TestCase):
    """Only what the agency results board (brand/doordash/supporting/Results.avif) supports."""

    def setUp(self):
        self.html = read("work/work-doordash.html")

    def test_unsourced_claims_are_gone(self):
        for claim in ("AdMeter", "Ad Meter", "$50M", "crashed X", "Most Talked", "most talked"):
            self.assertNotIn(claim, self.html, claim)

    def test_stat_row_uses_the_board(self):
        nums = re.findall(r'<div class="stat-num">([^<]+)</div>', self.html)
        self.assertIn("8M", nums)
        self.assertIn("76", nums)

    def test_recognition_chips_have_no_admeter_chip(self):
        chips = re.findall(r'<span class="award-chip[^"]*">([^<]+)</span>', self.html)
        self.assertFalse(any("USA Today" in c for c in chips), chips)


class StudioRenameTests(unittest.TestCase):
    def test_booking_lines_name_curious_and_creative(self):
        html = read("index.html")
        self.assertNotIn("through the Studio", html)
        self.assertIn('?topic=photo" class="hero-book" target="_blank" rel="noopener">Book a shoot through Curious &amp; Creative&nbsp;&#8599;</a>', html)
        self.assertIn('?leg=studio" target="_blank" rel="noopener" class="rule-link">through Curious &amp; Creative&nbsp;&#8599;</a>', html)


class FounderTitleTests(unittest.TestCase):
    def test_no_co_founder_for_joshua(self):
        for rel in ("index.html", "resume/index.html", "network/index.html"):
            text = BeautifulSoup(read(rel), "lxml").get_text(" ")
            self.assertNotRegex(text.lower(), r"co-?founder", rel)
        meta = BeautifulSoup(read("resume/index.html"), "lxml").find("meta", attrs={"name": "description"})["content"]
        self.assertIn("Founder and CEO", meta)

    def test_network_roles(self):
        soup = BeautifulSoup(read("network/index.html"), "lxml")
        people = {p.h3.get_text(strip=True): p for p in soup.select(".person")}
        self.assertEqual(people["Joshua McKenzie German"].select_one(".role").get_text(" ", strip=True), "Founder & CEO · Network principal")
        self.assertIsNone(people["Janel Moore"].select_one(".role"))
        self.assertIn("Truist", people["Janel Moore"].get_text())  # her other credits stay

    def test_network_jsonld_founder_is_joshua(self):
        founders = [f["name"] for f in jsonld(read("network/index.html"))["founder"]]
        self.assertEqual(founders, ["Joshua McKenzie German"])


class ScailTests(unittest.TestCase):
    SPELLED = "South Carolina AI Literacy (SCAiL)"

    def test_about_spells_it_out(self):
        about = BeautifulSoup(read("index.html"), "lxml").select_one("#about").get_text(" ")
        self.assertIn(self.SPELLED, about)
        self.assertLess(about.index("South Carolina AI Literacy"), about.index("SCAiL"))

    def test_homepage_jsonld(self):
        graph = jsonld(read("index.html"))
        people = [n for n in graph.get("@graph", [graph]) if n.get("@type") == "Person"]
        orgs = [o["name"] for o in people[0]["worksFor"]]
        self.assertIn("The Curious & Creative Company", orgs)
        self.assertIn(self.SPELLED, orgs)

    def test_resume_has_scail_and_education(self):
        soup = BeautifulSoup(read("resume/index.html"), "lxml")
        scail = soup.select_one('.job[data-org="scail"]')
        self.assertEqual(scail.select_one(".org").get_text(strip=True), self.SPELLED)
        self.assertEqual(scail.select_one(".title").get_text(strip=True), "Founder & President")
        self.assertEqual(scail.select_one(".when").get_text(strip=True), "Now")
        edu = soup.select_one("#education").get_text(" ", strip=True)
        for part in ("University of South Carolina", "Journalism & Mass Communications", "Information Science", "The Daily Gamecock"):
            self.assertIn(part, edu)

    def test_resume_pdf_embeds_the_site_fonts(self):
        data = (ROOT / "resume/joshua-mckenzie-german-resume.pdf").read_bytes()
        for font in (b"Fraunces", b"SpaceGrotesk", b"SpaceMono"):
            self.assertTrue(font in data, font)
        self.assertFalse(b"Liberation" in data)


class NetworkPlaceholderTests(unittest.TestCase):
    def test_brazil_card_uses_its_tagline(self):
        html = read("network/index.html")
        self.assertNotIn("A podcast by Joshua German.", html)
        tagline = next(s for s in json.loads(read("data/network.json"))["shows"] if s["key"] == "brazil")["tagline"]
        self.assertIn(tagline.replace("'", "&rsquo;"), html)


class MediaDietHiddenShelvesTests(unittest.TestCase):
    def setUp(self):
        self.js = read("assets/media-diet.js")

    def test_reading_waits_for_goodreads_books(self):
        self.assertIn("live: function (list) { return list.some(function (i) { return i.kind === 'book'; }); }", self.js)
        self.assertIn("shown = liveShelves(items, true);", self.js)

    def test_keyboard_and_hash_skip_hidden_shelves(self):
        self.assertIn("var i = shown.indexOf(current)", self.js)
        self.assertIn("shown.indexOf(h) >= 0", self.js)

    def test_empty_chips_never_render(self):
        # an Albums chip with no albums behind it is left out
        self.assertIn("if (d[0] !== 'all' && (!count || (d[2] && count === list.length))) return;", self.js)


if __name__ == "__main__":
    unittest.main()
