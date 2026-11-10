"""Case-study pages for Joshua's AI builds (builds/*.html)."""
import json
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_JSON = Path("/home/user/jgerms20/curious-and-creative/site/data/projects.json")

PAGES = {
    "gen-alpha-intelligence-lab.html": "genalpha",
    "meme-library.html": "memelibrary",
    "life-gamified.html": "lifegamified",
}
# Mirrors projects.json (the company site's Inventions data) so the test also runs without it.
EXPECTED_STATUS = {
    "genalpha": "Invite only",
    "memelibrary": "Live · updating",
    "lifegamified": "Live",
}
SECTIONS = ["problem", "insight", "build", "what", "limits", "changed"]
DRAFT_SCRIPT = "if(/[?&]draft\\b/.test(location.search))document.documentElement.classList.add('draft')"


def soup_for(name):
    return BeautifulSoup((ROOT / "builds" / name).read_text(encoding="utf-8"), "lxml")


class BuildPagesTests(unittest.TestCase):
    def test_pages_exist(self):
        for name in PAGES:
            self.assertTrue((ROOT / "builds" / name).is_file(), name)

    def test_six_sections_in_order(self):
        for name in PAGES:
            soup = soup_for(name)
            found = [s["data-section"] for s in soup.select("main section[data-section]")]
            self.assertEqual(found, SECTIONS, name)
            labels = [s.select_one(".cs-label").get_text() for s in soup.select("main section[data-section]")]
            self.assertEqual([l[:2] for l in labels], ["01", "02", "03", "04", "05", "06"], name)

    def test_draft_mode_mechanism(self):
        css = (ROOT / "builds" / "builds.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.todo\s*\{\s*display:\s*none")
        self.assertRegex(css, r"\.draft \.todo\s*\{[^}]*display:\s*block")
        self.assertRegex(css, r"\.is-pending\s*\{\s*display:\s*none")
        self.assertRegex(css, r"\.draft \.cs-sec\.is-pending\s*\{\s*display:\s*grid")
        for name in PAGES:
            soup = soup_for(name)
            self.assertIsNotNone(soup.find("link", href="builds.css"), name)
            head_scripts = [s.get_text() for s in soup.head.find_all("script")]
            self.assertIn(DRAFT_SCRIPT, head_scripts[0], f"{name}: draft script must come first in <head>")
            self.assertTrue(soup.select(".todo[data-todo]"), name)

    def test_todo_slots_are_well_formed_and_unique(self):
        ids = []
        for name in PAGES:
            for todo in soup_for(name).select(".todo"):
                self.assertTrue(todo.get("data-todo"), name)
                self.assertTrue(todo.get_text().startswith("TODO for Joshua:"), todo.get("data-todo"))
                ids.append(todo["data-todo"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_pending_sections_hold_only_todos(self):
        for name in PAGES:
            soup = soup_for(name)
            for section in soup.select("main section[data-section]"):
                body = section.select_one(".cs-body")
                content = [c for c in body.find_all(recursive=False) if c.name != "h2"]
                only_todos = all("todo" in (c.get("class") or []) for c in content)
                pending = "is-pending" in section.get("class", [])
                self.assertEqual(
                    pending, only_todos,
                    f"{name} #{section.get('id')}: is-pending must be set exactly when the body is only TODOs",
                )

    def test_no_todo_text_outside_todo_slots(self):
        for name in PAGES:
            soup = soup_for(name)
            for todo in soup.select(".todo"):
                todo.decompose()
            for tag in soup(["script", "style"]):
                tag.decompose()
            self.assertNotRegex(soup.get_text(" "), r"(?i)\bTODO\b|\bTBD\b|lorem ipsum", name)

    def test_gen_alpha_rights_flag(self):
        soup = soup_for("gen-alpha-intelligence-lab.html")
        rights = soup.select_one('.todo[data-todo="genalpha-rights"]')
        self.assertIsNotNone(rights)
        self.assertIn("Confirm you have the right to show this publicly", rights.get_text())
        self.assertIn("agency assignment", rights.get_text())
        # It sits near the top, before the first case section.
        html = str(soup)
        self.assertLess(html.index('data-todo="genalpha-rights"'), html.index('data-section="problem"'))
        # Public, truthful note linking the invite-only lab rather than duplicating it.
        note = soup.select_one(".note")
        self.assertIn("Curious & Creative Company", note.get_text())
        self.assertIn("research product", note.get_text())
        self.assertIn("invite only", note.get_text().lower())
        self.assertIsNotNone(note.find("a", href="https://agencythings-gen-alpha.vercel.app"))

    def test_status_chips_match_projects_json(self):
        expected = dict(EXPECTED_STATUS)
        if PROJECTS_JSON.exists():
            data = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
            expected = {p["id"]: p["status"] for p in data["projects"] if p["id"] in EXPECTED_STATUS}
            self.assertEqual(expected, EXPECTED_STATUS)
        for name, pid in PAGES.items():
            chips = soup_for(name).select(".status-chip")
            self.assertEqual(len(chips), 1, name)
            self.assertEqual(chips[0].get_text(strip=True), expected[pid], name)
            self.assertEqual(chips[0]["data-status"], expected[pid], name)

    def test_head_and_navigation(self):
        for name in PAGES:
            soup = soup_for(name)
            url = f"https://joshuamgerman.com/builds/{name}"
            self.assertEqual(soup.find("link", rel="canonical")["href"], url)
            self.assertEqual(soup.find("meta", property="og:url")["content"], url)
            self.assertIsNotNone(soup.find("link", rel="manifest", href="../site.webmanifest"))
            self.assertIn("jmg-theme", " ".join(s.get_text() for s in soup.head.find_all("script")))
            back = soup.select_one(".nav-links a")
            self.assertEqual(back["href"], "../index.html#builds")
            self.assertIn("All Builds", back.get_text())
            self.assertIsNotNone(soup.find(id="themeToggle"))
            footer = [(a.get_text(strip=True), a["href"]) for a in soup.select(".footer-links a")]
            self.assertEqual(
                [h for _, h in footer],
                ["../index.html#builds", "../index.html#work", "../photography/", "../shop.html", "../photography/#book"],
            )
            for img in soup.find_all("img"):
                self.assertTrue(img.get("alt", "").strip(), f"{name}: {img.get('src')}")

    def test_builds_are_production_pages(self):
        from portfolio_quality.pages import discover_production_pages

        found = {p.relative_to(ROOT).as_posix() for p in discover_production_pages(ROOT)}
        for name in PAGES:
            self.assertIn(f"builds/{name}", found)


if __name__ == "__main__":
    unittest.main()
