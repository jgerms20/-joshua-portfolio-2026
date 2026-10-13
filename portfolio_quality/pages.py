from pathlib import Path


PRODUCTION_GLOBS = (
    "index.html",
    "network/index.html",
    "media/media-*.html",
    "podcasts/podcast-*.html",
    "work/work-*.html",
)

EXCLUDED_NAMES = {"work-template.html"}


def discover_production_pages(root: Path) -> list[Path]:
    root = Path(root)
    pages = {
        page
        for pattern in PRODUCTION_GLOBS
        for page in root.glob(pattern)
        if page.is_file() and page.name not in EXCLUDED_NAMES
    }
    return sorted(pages, key=lambda page: page.relative_to(root).as_posix())
