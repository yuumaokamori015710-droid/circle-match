"""SEO checks against an isolated SQLite DB; no production writes or mail."""
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
import circlematch_seo as seo


class MetadataTests(unittest.TestCase):
    body = '<!doctype html><html lang="ja"><head><title>Old</title><meta name="description" content="old"><meta name="robots" content="index"><link rel="canonical" href="https://old.invalid/"></head><body><h1>募集</h1><div>30件を表示</div><script>const msg="0件を表示";</script></body></html>'

    def render(self, path='/', body=None, status=200, event=None):
        return seo.apply_metadata(body or self.body, path, 'https://circle-match.jp', {'サッカー・フットサル':'soccer.png'}, {'kanto':{'label':'関東'}}, status, event).decode()

    def test_unique_metadata_and_unchanged_body(self):
        result = self.render('/events?sport=サッカー・フットサル&region=kanto')
        for value in ['<title>', 'name="description"', 'name="robots"', 'rel="canonical"']:
            self.assertEqual(result.count(value), 1)
        self.assertIn('関東のサッカー・フットサルの大会・イベント', result)
        self.assertIn('content="index, follow', result)
        self.assertEqual(result.split('</head>')[1], self.body.split('</head>')[1])

    def test_db_and_event_tabs_have_different_canonicals(self):
        result = self.render('/?tab=db&audience=social')
        self.assertIn('社会人サークルDB', result)
        self.assertIn('/?tab=db&amp;audience=social', result)
        self.assertIn('content="index, follow', result)

    def test_tracking_removed_and_pagination_preserved(self):
        result = self.render('/?tab=db&audience=university&page=2&utm_source=x')
        self.assertIn('audience=university&amp;page=2', result)
        self.assertNotIn('utm_source', result)

    def test_private_search_and_legacy_routes_noindex(self):
        for path in ['/signin', '/mypage', '/notifications', '/representative', '/events/new', '/events/x/apply', '/events/x/contact', '/payments', '/admin', '/events?q=private', '/events?date_from=2030-01-01', '/sports?sport=野球']:
            with self.subTest(path=path):
                self.assertIn('content="noindex, follow"', self.render(path))

    def test_empty_failed_unknown_and_error_pages_noindex(self):
        for body in [self.body.replace('30件を表示','0件を表示'), self.body.replace('30件を表示','データを取得できませんでした')]:
            self.assertIn('content="noindex, follow"', self.render('/events?region=kanto', body))
        self.assertIn('content="noindex, follow"',self.render('/events?sport=unknown'))
        self.assertIn('content="noindex, follow"',self.render('/events/missing',status=404))

    def test_schema_uses_only_public_facts_and_jst(self):
        event = {'event_id':'abc','status':'published','title':'テスト </script><script>alert(1)</script>', 'starts_at':'2030-10-01T10:00', 'location':'会場', 'prefecture':'東京都', 'description':'内容', 'organizer_name':'主催者','organizer_contact_email':'secret@example.test','target_total_amount':999,'bank_account':'secret'}
        result = self.render('/events/abc',event=event)
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',result).group(1))
        self.assertEqual(data['startDate'],'2030-10-01T10:00:00+09:00')
        self.assertNotIn('endDate',data)
        self.assertNotIn('offers',data)
        self.assertNotIn('secret',result)
        self.assertIn('\\u003c/script',result)
        event['status']='cancelled'
        self.assertIn('EventCancelled',seo.event_schema(event,''))
        event['visibility']='unlisted'
        self.assertEqual(seo.event_schema(event,''),'')
        self.assertIn('content="noindex, follow"',self.render('/events/abc',event=event))


class SitemapTests(unittest.TestCase):
    def test_real_rendering_and_sitemap(self):
        scratch = ROOT / 'work'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            os.environ['CIRCLEMATCH_DB_PATH'] = str(Path(directory)/'test.sqlite')
            spec=importlib.util.spec_from_file_location('seo_app_test',ROOT/'outputs/circlematch_db_app.py')
            app=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app)
            app.init_db()
            app.SITE_BASE_URL='https://circle-match.jp'
            body=app.render_public_html({'tab':['db'],'audience':['university']})
            self.assertIn('circle-row',body.decode())
            xml=app.sitemap_xml()
            root=ElementTree.fromstring(xml)
            urls=[node.text for node in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
            self.assertIn('https://circle-match.jp/?tab=db&audience=social',urls)
            self.assertEqual(len(urls),len(set(urls)))
            self.assertFalse(any('/representative' in u or '/signin' in u or '/sports?' in u for u in urls))
            self.assertIn(b'Sitemap: https://circle-match.jp/sitemap.xml',app.robots_txt())


if __name__=='__main__':
    unittest.main()
