"""Independent ordinary-account checks; never uses production credentials or DB."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import check_admin_access as audit
import manage_host_fee_campaign as operator
import test_fee_campaign as fixtures


class AdminAccessTests(unittest.TestCase):
    request = fixtures.FeeCampaignTests.request

    @classmethod
    def setUpClass(cls):
        fixtures.FeeCampaignTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        fixtures.FeeCampaignTests.tearDownClass.__func__(cls)

    def test_two_valid_ordinary_accounts_and_anonymous_cannot_read_admin_views(self):
        profiles = [('anonymous',{})]
        for account in [self.host,self.other]:
            headers = {'Cookie':'cm_session='+self.sessions[account['user_id']]}
            status,body = self.request('/api/me',headers=headers)
            self.assertEqual(status,200)
            self.assertTrue(body['authenticated'])
            self.assertEqual(body['user_id'],account['user_id'])
            profiles.append((account['user_id'],headers))
        for profile,headers in profiles:
            for path in audit.PROTECTED_PATHS:
                with self.subTest(profile=profile,path=path):
                    self.assertEqual(self.request(path,headers=headers)[0],401)

    def test_general_accounts_cannot_write_existing_admin_apis(self):
        with self.app.connect() as conn:
            before = conn.execute('select count(*) from audit_logs').fetchone()[0]
        for options in [{},{'member':True}]:
            for path in ['/api/universities','/api/circles','/api/admin/contact-research/import',
                         '/api/payments/admin/connection-status']:
                self.assertEqual(self.request(path,b'',**options)[0],401)
        with self.app.connect() as conn:
            self.assertEqual(before,conn.execute('select count(*) from audit_logs').fetchone()[0])

    def test_retired_campaign_ui_and_api_return_404_even_with_admin_credentials(self):
        with self.app.connect() as conn:
            before = self.app.fee_campaign.status(conn)
        for options in [{},{'member':True},{'admin':True}]:
            for path in audit.RETIRED_PATHS:
                for suffix in ['', '/', '?probe=1']:
                    for data in [None,dict(enabled=True,revision=before['revision'],accepted=True)]:
                        with self.subTest(options=options,path=path+suffix,method='GET' if data is None else 'POST'):
                            self.assertEqual(self.request(path+suffix,data,**options)[0],404)
        with self.app.connect() as conn:
            self.assertEqual(before,self.app.fee_campaign.status(conn))
        status,body = self.request('/admin/payments',admin=True)
        self.assertEqual(status,200)
        self.assertNotIn('/admin/payments/host-fees',body)
        self.assertNotIn('campaignEnabled',body)

    def test_basic_auth_is_still_required_regardless_of_member_session(self):
        bad = {'Authorization':'Basic bm9uYWRtaW46d3Jvbmc='}
        self.assertEqual(self.request('/admin/payments',member=True,headers=bad)[0],401)
        self.assertEqual(self.request('/admin/payments',admin=True,
            headers={'Cookie':'cm_session='+self.sessions[self.other['user_id']]})[0],200)
        self.assertEqual(self.request('/api/payments/admin/connection-status',{},admin=True,csrf=False)[0],403)

    def test_live_probe_uses_no_cached_auth_and_matches_the_deployed_revision(self):
        with patch.dict(os.environ,{'RENDER_GIT_COMMIT':'synthetic-commit'}):
            self.assertEqual(audit.wait_for_revision(self.base,'synthetic-commit',0),'synthetic-commit')
            with self.assertRaises(TimeoutError):
                audit.wait_for_revision(self.base,'different-commit',0)
            result = audit.probe(self.base)
        self.assertEqual(len(result),16)
        self.assertTrue(all(row['ok'] for row in result),result)
        self.assertTrue(all(row['profile'] == 'anonymous' for row in result))

    def test_cli_status_is_read_only_and_missing_db_is_not_created(self):
        path = self.app.DB_PATH.resolve()
        with self.app.connect() as conn:
            before = list(conn.execute('select name,sql from sqlite_master order by name'))
            state = list(conn.execute('select * from app_state'))
        connect = operator.existing_database(path,readonly=True)
        result = operator.run('status',connect)
        self.assertTrue(result['valid'])
        with connect() as conn:
            self.assertEqual(before,list(conn.execute('select name,sql from sqlite_master order by name')))
            self.assertEqual(state,list(conn.execute('select * from app_state')))
        missing = path.with_name('must-not-be-created.sqlite')
        with self.assertRaises(ValueError):
            operator.existing_database(missing,readonly=False)
        self.assertFalse(missing.exists())
        command = [os.sys.executable,'-B',str(Path(operator.__file__)),'status']
        result = subprocess.run(command,capture_output=True,text=True,encoding='utf-8',
            env=dict(os.environ,CIRCLEMATCH_DB_PATH=str(path)))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertNotIn(self.app.ADMIN_PASSWORD,result.stdout)
        self.assertIn('campaign',json.loads(result.stdout))

    def test_cli_failures_do_not_print_secret_error_details(self):
        captured = io.StringIO()
        with patch.object(operator,'existing_database',side_effect=RuntimeError('SECRET_MUST_NOT_APPEAR')):
            with redirect_stdout(captured):
                result = operator.main(['status'])
        self.assertEqual(result,2)
        self.assertNotIn('SECRET_MUST_NOT_APPEAR',captured.getvalue())


if __name__ == '__main__':
    unittest.main()
