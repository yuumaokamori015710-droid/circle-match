"""Theme color-pair and public asset contracts; browser audit checks the cascade."""
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

from test_venues import IsolatedAppHttpCase

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / 'outputs/club_static/contrast.css'


def luminance(color):
    values = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(foreground, background):
    a, b = luminance(foreground), luminance(background)
    return (max(a, b) + .05) / (min(a, b) + .05)


class ThemeContrastPaletteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS.read_text(encoding='utf-8')
        cls.colors = dict(re.findall(r'(--cm-[a-z-]+):\s*(#[0-9a-fA-F]{6});', cls.css))

    def test_readable_text_on_every_supported_dark_surface(self):
        for foreground in ['text', 'muted', 'link']:
            for background in ['bg', 'surface', 'raised', 'selected']:
                with self.subTest(foreground=foreground, background=background):
                    self.assertGreaterEqual(contrast(self.colors['--cm-' + foreground], self.colors['--cm-' + background]), 4.5)

    def test_action_and_semantic_messages_have_full_body_text_contrast(self):
        for foreground, background in [('action-text', 'action'), ('success', 'success-bg'),
                                       ('warning', 'warning-bg'), ('danger', 'danger-bg'),
                                       ('text', 'success-bg'), ('text', 'danger-bg')]:
            with self.subTest(foreground=foreground):
                self.assertGreaterEqual(contrast(self.colors['--cm-' + foreground], self.colors['--cm-' + background]), 4.5)

    def test_focus_and_control_edges_are_distinguishable(self):
        for background in ['bg', 'surface', 'raised', 'selected']:
            with self.subTest(background=background):
                self.assertGreaterEqual(contrast(self.colors['--cm-border'], self.colors['--cm-' + background]), 3)
                self.assertGreaterEqual(contrast(self.colors['--cm-link'], self.colors['--cm-' + background]), 3)

    def test_legacy_light_surfaces_keep_readable_text_and_actions(self):
        for background in ['#ffffff', '#eef3f7', '#f4f7fa', '#f7fafc']:
            for foreground in ['light-text', 'light-muted', 'light-action']:
                self.assertGreaterEqual(contrast(self.colors['--cm-' + foreground], background), 4.5)
        self.assertGreaterEqual(contrast('#ffffff', self.colors['--cm-light-action']), 4.5)
        self.assertGreaterEqual(contrast(self.colors['--cm-light-border'], '#ffffff'), 3)

    def test_covers_legacy_components_without_hiding_or_rebranding_them(self):
        for selector in ['.cm-view-options label:has(input:checked)', '.cm-settings-actions button[type=submit]',
                         '.invite-ui .invite-primary', '.invite-ui .invite-manage .invite-primary',
                         '.host-fee-note', '.payment-details dt', '.venue-skip-link', '.venue-message-panel']:
            self.assertIn(selector, self.css)
        for forbidden in ['display:none', 'visibility:hidden', '!important', '.brand{', '.mobile-apply']:
            self.assertNotIn(forbidden, self.css)
        self.assertIn('fieldset:disabled', self.css)
        self.assertIn('cursor: not-allowed', self.css)


class StylesheetLinks(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.styles = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.styles.append(attrs.get('href', ''))


class ThemeContrastHttpTests(IsolatedAppHttpCase):
    def test_hash_versioned_theme_is_after_legacy_styles_and_present_once(self):
        expected = '/assets/club/contrast.css?v=' + sha256(CSS.read_bytes()).hexdigest()[:12]
        for path in ['/', '/events', '/settings', '/signin', '/venues', '/guides', '/terms']:
            with self.subTest(path=path):
                status, body, _ = self.request(path)
                self.assertEqual(status, 200)
                links = StylesheetLinks(body.decode()).styles
                self.assertEqual(links.count(expected), 1)
                if '<body class="cm-club">' in body.decode():
                    self.assertGreater(links.index(expected), next(i for i, url in enumerate(links) if url.startswith('/assets/club/styles.css?')))

    def test_asset_is_public_read_only_and_retains_mime_and_cache_contract(self):
        status, body, headers = self.request('/assets/club/contrast.css')
        self.assertEqual(status, 200)
        self.assertEqual(body, CSS.read_bytes())
        self.assertIn('text/css', headers['Content-Type'])
        self.assertIn('max-age', headers['Cache-Control'])
        self.assertEqual(self.request('/assets/club/contrast.css', method='POST')[0], 405)


if __name__ == '__main__':
    unittest.main()
