"""Candidate rechecks do not imply publication or permission to send email."""
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import research_circle_contacts as crawler
import review_circle_contact_candidates as review


class CandidateReviewTests(unittest.TestCase):
    def test_shared_email_is_not_selected_for_unrelated_clubs(self):
        rows = [{'circle_id': ident, 'verified': [{'circle_id': ident, 'email':'same@club.example'}]}
                for ident in ['a','b']]
        self.assertEqual(review.publishable(rows), [])
        rows[0]['verified'].append({'circle_id':'a','email':'unique@club.example'})
        self.assertEqual(review.publishable(rows), [{'circle_id':'a','email':'unique@club.example'}])

    def test_reused_page_keeps_original_acquisition_date_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root/'old.sqlite'
            old_fetcher = crawler.Fetcher(old)
            with old_fetcher.db() as conn:
                conn.execute('insert into pages values(?,?,?,?,?,?)',
                             ('https://club.example/','https://club.example/','ok',b'<p>club</p>',
                              'text/html','2026-10-01T00:00:00Z'))
            original = old.read_bytes()
            fetcher = crawler.Fetcher(root/'new.sqlite',reuse_caches=[old])
            with patch.object(fetcher.opener,'open',side_effect=AssertionError('Network not expected')):
                page = fetcher.fetch('https://club.example/')
            self.assertEqual(page['checked_at'],'2026-10-01T00:00:00Z')
            self.assertEqual(old.read_bytes(),original)

    @unittest.skipIf(crawler.dom is None,'lxml required')
    def test_recheck_does_not_accept_email_in_another_clubs_card(self):
        circle = {'circle_id':'a','circle_name':'Blue Club','source_url':'https://club.example/list'}
        page = {'url':'https://club.example/list','status':'ok','kind':'text/html',
                'checked_at':'2026-10-13T00:00:00Z',
                'body':b'<main><article><h2>Blue Club</h2></article><article><h2>Red Club</h2><p>red@club.example</p></article></main>'}
        class Source:
            def fetch(self,url): return page
            def parsed(self,url): return crawler.parse_page(page)
        result = review.review(circle,[{'email':'red@club.example','source_url':page['url']}],Source(),['Blue Club','Red Club'])
        self.assertEqual(result['verified'],[])
        self.assertEqual(result['rejected'][0]['reason'],'club_contact_not_confirmed')


if __name__ == '__main__':
    unittest.main()
