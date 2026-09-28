from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class VerifiedContentTests(unittest.TestCase):
    def test_xfinity_uses_verified_campaign_embed_and_fallback(self):
        page = (ROOT / "work/work-xfinity.html").read_text(encoding="utf-8")

        # Click-to-play YouTube film (reliable poster + playback), with the
        # verified iSpot listing kept as the source link.
        self.assertIn('data-yt="63o9tgPK9r8"', page)
        self.assertIn('href="https://www.ispot.tv/ad/tBI3/', page)
        self.assertNotIn("R4MkK-9fJ9M", page)

    def test_gatorade_clio_bronze_links_official_evidence(self):
        page = (ROOT / "work/work-gatorade.html").read_text(encoding="utf-8")

        self.assertIn("2026 Clio Awards", page)
        self.assertIn("Bronze", page)
        self.assertIn(
            'href="https://clios.com/winners-gallery/details/220718"', page
        )
        self.assertIn('rel="noopener noreferrer"', page)


if __name__ == "__main__":
    unittest.main()
