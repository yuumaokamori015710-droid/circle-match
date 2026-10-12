"""Column controls, honest fee ordering and the official Komazawa additions."""
import json
from urllib.parse import parse_qs, urlsplit, urlencode

from bs4 import BeautifulSoup
from test_venues import IsolatedAppHttpCase


class VenueColumnTests(IsolatedAppHttpCase):
    def page(self, params=None):
        return BeautifulSoup(self.request('/venues?' + urlencode(params or {}, doseq=True))[1].decode(), 'html.parser')

    def test_default_is_any_published_fee_not_only_hourly(self):
        from venues.sports_catalog import filter_catalog, has_price
        rows = json.loads(self.request('/api/venues')[1])['courts']
        ordered = filter_catalog(rows, {})
        flags = [has_price(row) for row in ordered]
        self.assertEqual(flags, sorted(flags, reverse=True))
        self.assertTrue(any(row.get('fee_options') and row['price_per_hour'] is None for row in ordered if has_price(row)))
        page = self.page()
        self.assertEqual(page.select_one('#venue-sort option[selected]')['value'], 'available')
        self.assertEqual([h.get_text() for h in page.select('.venue-court-card h3')], [r['name'] for r in ordered[:50]])

    def test_zero_cost_is_known_and_unknown_fees_stay_last(self):
        from venues.sports_catalog import sort_catalog
        rows = [{'id':'a','name':'A','price_from':None}, {'id':'b','name':'B','price_from':0},
                {'id':'c','name':'C','price_from':None,'fee_options':[{'amount':100}]}]
        self.assertEqual([r['id'] for r in sort_catalog(rows)], ['b','c','a'])

    def test_all_sorts_are_server_rendered_and_unknown_facts_last(self):
        from venues.sports_catalog import filter_catalog, SORTS
        rows = json.loads(self.request('/api/venues')[1])['courts']
        for order, _ in SORTS:
            with self.subTest(order=order):
                expected = filter_catalog(rows, {'v_sort':order})
                page = self.page({'v_sort':order})
                self.assertEqual([h.get_text() for h in page.select('.venue-court-card h3')], [r['name'] for r in expected[:50]])
                self.assertEqual(page.select_one('#venue-sort option[selected]')['value'], order)
        for order in ('price','price_desc'):
            prices = [row['price_per_hour'] for row in filter_catalog(rows, {'v_sort':order})]
            known = [price for price in prices if price is not None]
            self.assertEqual(known, sorted(known, reverse=order=='price_desc'))
            self.assertTrue(all(price is None for price in prices[len(known):]))

    def test_each_column_has_native_filters_and_two_sort_links(self):
        page = self.page({'sport':'サッカー・フットサル','v_q':'公園','v_places':'世田谷区'})
        columns = page.select('.venue-table>thead th')
        self.assertEqual(len(columns),6)
        for column in columns:
            self.assertEqual(len(column.select('.venue-column-sorts a')),2)
            self.assertIsNotNone(column.select_one('.venue-column-menu summary[title]'))
            for link in column.select('[data-venue-control]'):
                query = parse_qs(urlsplit(link['href']).query)
                self.assertEqual(query['sport'],['サッカー・フットサル'])
                self.assertEqual(query['v_q'],['公園'])
                self.assertNotIn('v_page', query)
        self.assertEqual(page.select_one('[name="name"]')['form'], 'venue-court-filters')

    def test_column_filters_combine_and_do_not_confuse_missing_with_free(self):
        from venues.sports_catalog import filter_catalog, has_price
        rows = json.loads(self.request('/api/venues')[1])['courts']
        for status in ('available','missing','hourly'):
            matches = filter_catalog(rows, {'price_status':status})
            self.assertGreater(len(matches),0)
            self.assertTrue(all((has_price(r) if status=='available' else not has_price(r) if status=='missing' else r['price_per_hour'] is not None) for r in matches))
        params = {'v_name':'駒沢','v_places':'世田谷区','v_price_status':'available','v_registration':'required'}
        matches = filter_catalog(rows, params)
        self.assertGreaterEqual(len(matches),3)
        self.assertTrue(all('駒沢' in r['name'] and r['municipality']=='世田谷区' for r in matches))
        page = self.page(params)
        self.assertEqual(len(page.select('.venue-court-card')), len(matches))
        self.assertEqual(page.select_one('[name="name"]')['value'], '駒沢')
        self.assertEqual(page.select_one('[name="price_status"]')['value'], 'available')

    def test_clear_location_link_removes_legacy_geography(self):
        page = self.page({'area':'23区','municipality':'世田谷区','v_places':'世田谷区','v_q':'駒沢'})
        clear = page.select_one('[data-venue-control="places"]')
        params = parse_qs(urlsplit(clear['href']).query)
        self.assertEqual(params['v_q'],['駒沢'])
        self.assertTrue(all(key not in params for key in ('v_places','places','municipality','v_municipality','area','v_area')))

    def test_komazawa_has_separate_fields_and_official_prices(self):
        from venues.sports_catalog import filter_catalog
        rows = json.loads(self.request('/api/venues?' + urlencode({'sport':'サッカー・フットサル'}))[1])['courts']
        venues = {r['id']:r for r in rows if r['id'].startswith('tokyo-komazawa-')}
        self.assertEqual(len(venues),4)
        self.assertEqual(venues['tokyo-komazawa-ballgame2']['fee_options'][0]['amount'],19800)
        self.assertEqual(venues['tokyo-komazawa-substadium']['fee_options'][0]['amount'],18000)
        self.assertEqual(venues['tokyo-komazawa-stadium']['fee_options'][0]['amount'],48400)
        for row in venues.values():
            self.assertIsNone(row['price_per_hour'])
            self.assertTrue(row['registration_required'])
            self.assertTrue(all(p['source_url'].startswith('https://www.tef.or.jp/kopgp/') for p in row['fee_options']))
        self.assertEqual(venues['tokyo-komazawa-stadium']['booking_channels'],['counter'])
        first = venues['tokyo-komazawa-ballgame1']
        self.assertEqual(first['availability_status'],'SUSPENDED')
        self.assertIn('2027年3月31日',first['availability_note'])
        self.assertNotIn(first,filter_catalog(rows,{}))
        self.assertIn(first,filter_catalog(rows,{'show_suspended':'1'}))

    def test_column_input_is_escaped_in_initial_html(self):
        page = self.page({'v_name':'"><script>alert(1)</script>'})
        self.assertEqual(page.select_one('[name="name"]')['value'],'"><script>alert(1)</script>')
        self.assertFalse(any(s.get_text()=='alert(1)' for s in page.select('script')))
