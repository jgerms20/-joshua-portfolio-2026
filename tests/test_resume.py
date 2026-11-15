"""The printable resume (resume/index.html) and its PDF."""
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "resume" / "index.html"
PDF = ROOT / "resume" / "joshua-mckenzie-german-resume.pdf"


def soup():
    return BeautifulSoup(PAGE.read_text(encoding="utf-8"), "lxml")


def job(org):
    node = soup().select_one(f'.job[data-org="{org}"]')
    if node is None:
        raise AssertionError(f"missing experience entry {org}")
    return node


class ResumeTests(unittest.TestCase):
    def test_page_exists_with_contact(self):
        self.assertTrue(PAGE.is_file())
        s = soup()
        self.assertIsNotNone(s.find("a", href="mailto:jgerms20@gmail.com"))
        self.assertIsNotNone(s.find("a", href="https://www.linkedin.com/in/joshua-german/"))
        self.assertEqual(s.find("link", rel="canonical")["href"], "https://joshuamgerman.com/resume/")
        self.assertEqual(s.find("meta", property="og:url")["content"], "https://joshuamgerman.com/resume/")
        self.assertIsNotNone(s.find("link", rel="manifest", href="../site.webmanifest"))
        self.assertIn("jmg-theme", " ".join(t.get_text() for t in s.head.find_all("script")))
        self.assertIn("Creative, Cultural & Content Strategist", s.select_one(".role").get_text())

    def test_pdf_exists_and_is_linked(self):
        self.assertTrue(PDF.is_file())
        data = PDF.read_bytes()
        self.assertGreater(len(data), 1000)
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertIsNotNone(soup().find("a", href=PDF.name))

    def test_no_em_dashes(self):
        text = PAGE.read_text(encoding="utf-8")
        for dash in ("—", "&mdash;", "&#8212;", "&#x2014;"):
            self.assertNotIn(dash, text)

    def test_titles_follow_joshuas_ruling(self):
        tbwa = job("tbwa").select_one(".title").get_text(" ", strip=True)
        self.assertIn("Senior Connections Strategist", tbwa)
        self.assertIn("AI Strategy and Systems Lead", tbwa)
        for org in ("wk", "gsp"):
            self.assertEqual(job(org).select_one(".title").get_text(strip=True), "Creative & Content Strategist", org)
        self.assertEqual(job("curious-creative").select_one(".title").get_text(strip=True), "Co-founder & CEO")
        text = soup().get_text(" ", strip=True)
        for old in ("Communication Strategist", "Communications Strategist", "Brand Strategist", "Media & Comms Supervisor"):
            self.assertNotIn(old, text)

    def test_years_match_work_index(self):
        work = (ROOT / "work" / "index.html").read_text(encoding="utf-8")
        for org, name in (("tbwa", "TBWA\\Chiat\\Day"), ("wk", "Wieden+Kennedy"), ("gsp", "Goodby, Silverstein &amp; Partners")):
            m = re.search(r'<span class="who">' + re.escape(name) + r'</span><span class="when">([^<]+)</span>', work)
            self.assertIsNotNone(m, name)
            when = m.group(1).replace("&ndash;", "–")
            self.assertEqual(job(org).select_one(".when").get_text(strip=True), when, org)

    def test_lab_count_matches_builds(self):
        rows = len(BeautifulSoup((ROOT / "builds" / "index.html").read_text(encoding="utf-8"), "lxml").select(".lab-row"))
        m = re.search(r"Plus (\d+) more in the lab", soup().get_text(" ", strip=True))
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), rows)

    def test_resume_is_registered(self):
        from portfolio_quality.pages import discover_production_pages

        found = {p.relative_to(ROOT).as_posix() for p in discover_production_pages(ROOT)}
        self.assertIn("resume/index.html", found)
        self.assertIn("https://joshuamgerman.com/resume/", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertIn("'resume/'", (ROOT / "tests" / "browser" / "smoke.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
