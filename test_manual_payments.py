import asyncio
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import httpx
from access_store import AccessError
from gateway import Config, create_app
from manual_payments import PaymentStore, next_month


class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'db.sqlite3';self.store=PaymentStore(self.path)
        self.admin=self.store.register('owner@example.com','test-only-password','Owner')['access_token']
        self.store.bootstrap_owner(self.admin,self.store.add('Owner'),'Owner')
        self.friend=self.store.register('friend@example.com','test-only-password','Friend')
        self.token=self.friend['access_token']
        self.store.configure(self.admin,dict(enabled=True,cashtag='$TestOnly',recipient_name='Test only'))

    def order(self,plan='monthly',token=None):
        token=token or self.token
        order=self.store.create_order(token,plan)
        self.store.report(token,order['id'],'Test payer','customer-reference')
        return order

    def approve(self,order,reference='real-test-id'):
        return self.store.review(self.admin,order['id'],'approve',reference,received_cents=order['amount_cents'])

    def test_report_does_not_grant_access_and_other_user_cannot_review(self):
        order=self.order()
        with self.assertRaises(AccessError):self.store.authenticate(self.token)
        with self.assertRaises(AccessError):self.store.review(self.token,order['id'],'approve','fake',received_cents=1000)
        self.assertEqual(self.store.orders(self.token)[0]['status'],'pending_review')

    def test_month_approval_idempotent_and_expiry_checked_on_every_api_use(self):
        order=self.order();self.approve(order)
        expiry=self.store.session(self.token)['paid_until']
        self.approve(order)
        self.assertEqual(self.store.session(self.token)['paid_until'],expiry)
        self.assertGreater(expiry,time.time()+27*86400)
        self.assertTrue(self.store.authenticate(self.token)['active'])
        with self.store.connect() as db:db.execute('UPDATE accounts SET paid_until=? WHERE id=?',(time.time()-1,self.friend['account']['id']))
        with self.assertRaises(AccessError):self.store.authenticate(self.token)

    def test_permanent_access_persists_and_cannot_buy_again(self):
        self.approve(self.order('one_time'))
        reopened=PaymentStore(self.path)
        self.assertTrue(reopened.session(self.token)['active'])
        self.assertIsNone(reopened.session(self.token)['paid_until'])
        with self.assertRaises(AccessError):reopened.create_order(self.token,'monthly')

    def test_duplicate_transaction_rolls_back_entitlement(self):
        self.approve(self.order())
        other=self.store.register('other@example.com','test-only-password','Other')['access_token']
        order=self.order(token=other)
        with self.assertRaises(AccessError):self.approve(order)
        self.assertFalse(self.store.session(other)['active'])
        self.assertEqual(self.store.orders(other)[0]['status'],'pending_review')

    def test_wrong_amount_and_blocked_user_cannot_be_approved(self):
        order=self.order()
        with self.assertRaises(AccessError):self.store.review(self.admin,order['id'],'approve','id',received_cents=1)
        self.store.set_access(self.admin,self.friend['account']['id'],'block')
        with self.assertRaises(AccessError):self.approve(order)

    def test_reject_retry_and_cancel(self):
        order=self.order();self.store.review(self.admin,order['id'],'reject',note='Payment not received')
        new=self.store.create_order(self.token,'one_time')
        self.assertNotEqual(order['id'],new['id'])
        self.store.cancel(self.token,new['id'])
        with self.assertRaises(AccessError):self.store.report(self.token,new['id'],'payer','id')

    def test_repeated_order_and_concurrent_review_do_not_extend_twice(self):
        first=self.store.create_order(self.token,'monthly')
        self.assertEqual(first['id'],self.store.create_order(self.token,'monthly')['id'])
        self.store.report(self.token,first['id'],'payer','id')
        with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda _:self.approve(first),range(3)))
        self.assertLess(self.store.session(self.token)['paid_until'],time.time()+32*86400)

    def test_renewal_adds_month_and_calendar_handles_leap_day(self):
        self.approve(self.order());before=self.store.session(self.token)['paid_until']
        self.approve(self.order(),reference='second-payment')
        self.assertEqual(self.store.session(self.token)['paid_until'],next_month(before))
        jan=datetime(2028,1,31,tzinfo=timezone.utc).timestamp()
        self.assertEqual(datetime.fromtimestamp(next_month(jan),timezone.utc).day,29)

    def test_settings_require_admin_and_disable_new_orders(self):
        with self.assertRaises(AccessError):self.store.configure(self.token,dict(enabled=True,cashtag='Test',recipient_name='Test'))
        self.store.configure(self.admin,dict(enabled=False,cashtag='Test',recipient_name='Test'))
        with self.assertRaises(AccessError):self.store.create_order(self.token,'monthly')


class PaymentHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_account_to_report_to_approval_flow_and_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            app=create_app(Config(database=str(Path(directory)/'db.sqlite3')),upstream=lambda **kw:None)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                for path in ('/cuenta','/account.js','/account.css'):
                    self.assertEqual((await client.get(path)).status_code,200)
                data=dict(email='friend@example.com',password='test-only-password',name='Friend')
                register=await client.post('/v1/account/register',json=data)
                self.assertEqual(register.status_code,201)
                token=register.json()['access_token'];headers={'Authorization':'Bearer '+token}
                self.assertEqual((await client.post('/v1/payments/orders',json={'plan':'monthly'},headers=headers)).status_code,409)
                store=app.state.payments
                owner=store.register('owner@example.com','test-only-password','Owner')['access_token']
                store.bootstrap_owner(owner,store.add('Owner'),'Owner')
                admin={'Authorization':'Bearer '+owner}
                result=await client.post('/v1/admin/payments/settings',headers=admin,json=dict(enabled=True,cashtag='$Test',recipient_name='Test'))
                self.assertEqual(result.status_code,200)
                self.assertIn('<svg',(await client.get('/v1/payments/qr.svg')).text)
                order=(await client.post('/v1/payments/orders',headers=headers,json={'plan':'monthly'})).json()
                report=await client.post('/v1/payments/orders/'+order['id']+'/report',headers=headers,json={'payer':'Friend','reference':'test-report'})
                self.assertEqual(report.status_code,200)
                self.assertEqual((await client.get('/v1/access',headers=headers)).status_code,403)
                self.assertEqual((await client.get('/v1/admin/payments',headers=headers)).status_code,403)
                approved=await client.post('/v1/admin/payments/'+order['id']+'/review',headers=admin,json={'action':'approve','reference':'test-verified','received_cents':1000})
                self.assertEqual(approved.status_code,200)
                self.assertEqual((await client.get('/v1/access',headers=headers)).status_code,200)
                self.assertEqual((await client.post('/v1/account/logout',headers=headers)).status_code,200)
                self.assertEqual((await client.get('/v1/access',headers=headers)).status_code,401)


if __name__=='__main__':unittest.main()
