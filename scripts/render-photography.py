#!/usr/bin/env python3
"""Render the photography manifest into the site.

    python3 scripts/render-photography.py              # homepage Darkroom + photography/index.html
    python3 scripts/render-photography.py --page-only  # only photography/index.html
    python3 scripts/render-photography.py --check      # exit 1 if either output is stale
    python3 scripts/render-photography.py --qr         # also rebuild the business-card QR codes

data/photography.json is the single source of truth for both outputs.
"""
import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio_quality.photography import (  # noqa: E402
    PHOTO_SITE_URL,
    apply_photo_site,
    load_photo_site_settings,
    load_photography_manifest,
    render_darkroom,
    render_photo_site,
)


START = "<!-- PHOTOGRAPHY:START -->"
END = "<!-- PHOTOGRAPHY:END -->"
LEGACY_END = "    <!-- =====================================================\n         07 — THE COLLECTION (dark)"

MANIFEST = ROOT / "data/photography.json"
HOMEPAGE = ROOT / "index.html"
PHOTO_SITE = ROOT / "photography/index.html"
QR_DIR = ROOT / "assets/qr"


def replace_darkroom(page: str, rendered: str) -> str:
    block = f"{START}\n    {rendered}\n    {END}\n\n"
    if START in page and END in page:
        before, remainder = page.split(START, 1)
        _, after = remainder.split(END, 1)
        return before + block + after.lstrip("\n")

    legacy_start = page.index('    <section id="photography" class="chapter chapter-dark">')
    legacy_end = page.index(LEGACY_END, legacy_start)
    return page[:legacy_start] + "    " + block + page[legacy_end:]


def _write_if_changed(path: Path, original: str, updated: str, label: str, check: bool) -> bool:
    """Returns True when the file is (or was) stale."""
    if updated == original:
        print(f"{label} is already current")
        return False
    if check:
        print(f"{label} is out of date; run scripts/render-photography.py")
        return True
    path.write_text(updated, encoding="utf-8")
    print(f"Rendered {label}")
    return True


def render_qr_codes() -> None:
    import qrcode
    import qrcode.image.svg

    QR_DIR.mkdir(parents=True, exist_ok=True)
    common = {"error_correction": qrcode.constants.ERROR_CORRECT_Q, "border": 4}

    svg = qrcode.QRCode(image_factory=qrcode.image.svg.SvgPathImage, box_size=10, **common)
    svg.add_data(PHOTO_SITE_URL)
    svg.make(fit=True)
    svg.make_image().save(str(QR_DIR / "photography-qr.svg"))

    png = qrcode.QRCode(box_size=40, **common)
    png.add_data(PHOTO_SITE_URL)
    png.make(fit=True)
    png.make_image(fill_color="black", back_color="white").save(str(QR_DIR / "photography-qr.png"))
    print(f"Wrote QR codes for {PHOTO_SITE_URL} to {QR_DIR.relative_to(ROOT)}/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--page-only", action="store_true", help="only render photography/index.html")
    parser.add_argument("--check", action="store_true", help="report stale output without writing")
    parser.add_argument("--qr", action="store_true", help="also regenerate assets/qr/ for business cards")
    args = parser.parse_args(argv)

    manifest = load_photography_manifest(MANIFEST)
    settings = load_photo_site_settings(MANIFEST)
    stale = False

    if not args.page_only:
        original = HOMEPAGE.read_text(encoding="utf-8")
        updated = replace_darkroom(original, render_darkroom(manifest))
        stale |= _write_if_changed(HOMEPAGE, original, updated, f"index.html Darkroom ({len(manifest)} photographs)", args.check)

    shell = PHOTO_SITE.read_text(encoding="utf-8")
    page = apply_photo_site(shell, render_photo_site(manifest, root=ROOT, clients=settings["clients"]))
    stale |= _write_if_changed(PHOTO_SITE, shell, page, f"photography/index.html ({len(manifest)} photographs)", args.check)

    if args.qr and not args.check:
        render_qr_codes()

    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
