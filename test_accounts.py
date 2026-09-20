import tempfile
import unittest
from pathlib import Path
from accounts import AccountStore
from access_store import AccessError
from plans import public_plans


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'access.sqlite3'
        self.store = AccountStore(self.path)

    def member(self, email='friend@example.com'):
        return self.store.register(email, 'test-password-not-real', 'Friend')

    def admin(self):
        code = self.store.add('Jorge')
        account = self.member('owner@example.com')
        self.store.bootstrap_owner(account['access_token'], code, 'Jorge')
        return account['access_token']

    def test_pending_cannot_use_api_and_secrets_not_stored(self):
        result = self.member()
        self.assertFalse(result['account']['active'])
        with self.assertRaises(AccessError): self.store.authenticate(result['access_token'])
        raw = self.path.read_bytes()
        self.assertNotIn(b'test-password-not-real', raw)
        self.assertNotIn(result['access_token'].encode(), raw)

    def test_approval_and_block_persist_and_revoke_sessions(self):
        admin = self.admin()
        friend = self.member()
        self.store.set_access(admin, friend['account']['id'], 'approve', 2)
        reopened = AccountStore(self.path)
        self.assertTrue(reopened.session(friend['access_token'])['active'])
        self.assertEqual(reopened.authenticate(friend['access_token'])['daily_limit'], 2)
        reopened.set_access(admin, friend['account']['id'], 'block')
        with self.assertRaises(AccessError): reopened.session(friend['access_token'])
        with self.assertRaises(AccessError): reopened.authenticate(friend['access_token'])

    def test_member_cannot_approve_self_or_list_accounts(self):
        friend = self.member()
        with self.assertRaises(AccessError): self.store.list_accounts(friend['access_token'])
        with self.assertRaises(AccessError):
            self.store.set_access(friend['access_token'], friend['account']['id'], 'approve')

    def test_bootstrap_requires_owner_and_is_single_use(self):
        friend = self.member()
        wrong = self.store.add('Someone else')
        with self.assertRaises(AccessError):
            self.store.bootstrap_owner(friend['access_token'], wrong, 'Jorge')
        self.admin()
        code = self.store.add('Other owner')
        with self.assertRaises(AccessError):
            self.store.bootstrap_owner(friend['access_token'], code, 'Other owner')

    def test_email_normalization_wrong_password_logout_and_legacy(self):
        friend = self.member('Friend@Example.com')
        self.assertEqual(friend['account']['email'], 'friend@example.com')
        with self.assertRaises(AccessError): self.member('friend@example.com')
        with self.assertRaises(AccessError): self.store.login('friend@example.com', 'wrong')
        self.store.logout(friend['access_token'])
        with self.assertRaises(AccessError): self.store.session(friend['access_token'])
        code = self.store.add('Existing friend')
        self.assertEqual(self.store.authenticate(code)['name'], 'Existing friend')

    def test_rate_limits_persist_and_reset(self):
        self.store.rate_limit('test', 1, 60, now=120)
        with self.assertRaises(AccessError): AccountStore(self.path).rate_limit('test', 1, 60, now=121)
        self.store.rate_limit('test', 1, 60, now=180)

    def test_prices_are_fixed_and_payment_is_not_enabled(self):
        catalog = public_plans()
        self.assertFalse(catalog['payments_enabled'])
        self.assertEqual([p['amount_cents'] for p in catalog['plans']], [1000, 4000])
        self.assertTrue(catalog['plans'][1]['permanent'])


if __name__ == '__main__': unittest.main()
