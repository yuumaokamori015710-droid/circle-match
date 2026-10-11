"""Public venue directory embedded in the native Circle Match page shell.

``render_venue_body(params)`` returns only the directory section, without navigation.
Pass the same parse_qs parameters to ``render_venue_head(params)`` so unlisted
sports or regions receive only the stylesheet, without a catalog request.
Serve the exact ``ASSET_PATHS`` entries as their (Path, Content-Type) tuple, and
return ``get_catalog()`` as JSON at GET /api/tennis-courts. No database is used.
"""
from html import escape
from hashlib import sha256
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
ASSET_VERSIONS = {url: sha256(path.read_bytes()).hexdigest()[:12] for url, (path, _) in ASSET_PATHS.items()}


def _selected(params, key: str) -> str:
    value = (params or {}).get(key, "")
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return value.strip() if isinstance(value, str) else ""


def supports_catalog(params=None) -> bool:
    """Whether the selected sport/geography includes the published Tokyo catalog."""
    return (_selected(params, "sport") in {"", "テニス"}
            and _selected(params, "prefecture") in {"", "東京都"}
            and _selected(params, "region") in {"", "kanto"})


def render_venue_body(params=None) -> str:
    """Return native content; the caller owns the shared heading, selectors and tabs."""
    if supports_catalog(params):
        return (VENUE_DIR / "static" / "tennis.html").read_text(encoding="utf-8")
    sport = _selected(params, "sport")
    message = (f"{sport}の会場は掲載準備中" if sport not in {"", "テニス"}
               else "この地域のテニス会場は掲載準備中")
    return ('<section class="venue-directory" aria-labelledby="venue-page-title">'
            '<section class="venue-intro"><p class="venue-eyebrow">公式情報から探す</p>'
            '<h2 id="venue-page-title">会場を探す</h2></section>'
            '<div class="venue-message-panel venue-unavailable">'
            f'<h3>{escape(message)}</h3>'
            '<p>現在は東京都のテニスコートを掲載しています。'
            '上の競技・地域の条件を変更してお探しください。</p>'
            '</div></section>')


def render_venue_head(params=None) -> str:
    """Return scoped CSS and, only for supported selections, the catalog script."""
    head = f'<link rel="stylesheet" href="{VENUE_CSS_URL}?v={ASSET_VERSIONS[VENUE_CSS_URL]}">'
    if supports_catalog(params):
        head += f'\n<script src="{VENUE_JS_URL}?v={ASSET_VERSIONS[VENUE_JS_URL]}" defer></script>'
    return head


__all__ = ["render_venue_body", "render_venue_head", "supports_catalog", "get_catalog", "ASSET_PATHS",
           "VENUE_CSS_URL", "VENUE_JS_URL"]
