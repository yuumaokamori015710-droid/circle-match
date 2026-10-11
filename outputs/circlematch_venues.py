"""Public venue directory embedded in the native Circle Match page shell.

``render_venue_body()`` returns only the directory section, without navigation.
Insert ``render_venue_head()`` in the shared page head for the two external assets.
Serve the exact ``ASSET_PATHS`` entries as their (Path, Content-Type) tuple, and
return ``get_catalog()`` as JSON at GET /api/tennis-courts. No database is used.
"""
from pathlib import Path

if __package__:
    from .venues.tennis_catalog import get_catalog
else:
    from venues.tennis_catalog import get_catalog


VENUE_DIR = Path(__file__).resolve().parent / "venues"
VENUE_CSS_URL = "/assets/venues/tennis.css"
VENUE_JS_URL = "/assets/venues/tennis.js"
ASSET_PATHS = {
    VENUE_CSS_URL: (VENUE_DIR / "static" / "tennis.css", "text/css; charset=utf-8"),
    VENUE_JS_URL: (VENUE_DIR / "static" / "tennis.js", "application/javascript; charset=utf-8"),
}


def render_venue_body() -> str:
    """Return the native .venue-directory section; the caller owns shared tabs."""
    return (VENUE_DIR / "static" / "tennis.html").read_text(encoding="utf-8")


def render_venue_head() -> str:
    """Return a stylesheet and deferred script, with no inline code or styles."""
    return (f'<link rel="stylesheet" href="{VENUE_CSS_URL}">\n'
            f'<script src="{VENUE_JS_URL}" defer></script>')


__all__ = ["render_venue_body", "render_venue_head", "get_catalog", "ASSET_PATHS",
           "VENUE_CSS_URL", "VENUE_JS_URL"]
