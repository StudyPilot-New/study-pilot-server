import tempfile,unittest,time,concurrent.futures
from pathlib import Path
from accounts import AccountStore
from access_store import AccessError
class Trials(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.s=AccountStore(Path(self.temp.name)/'db');self.r=self.s.register('trial@example.com','long-test-password','Trial');self.t=self.r['access_token']
 def tearDown(self):self.temp.cleanup()
 def test_lifetime_quota_expiry_and_no_reset(self):
  self.assertFalse(self.s.session(self.t)['active']);self.s.start_trial(self.t,'peer1')
  for _ in range(20):self.s.reserve(self.t,3000,minute_limit=100)
  self.assertEqual(self.s.session(self.t)['trial']['remaining'],0)
  with self.assertRaises(AccessError):self.s.reserve(self.t,3000)
  with self.assertRaises(AccessError):self.s.start_trial(self.t,'peer2')
  again=self.s.login('trial@example.com','long-test-password')['access_token']
  self.assertFalse(self.s.session(again)['active'])
 def test_expiry_and_paid_upgrade(self):
  self.s.start_trial(self.t,'peer1')
  with self.s.connect() as db:db.execute('UPDATE account_trials SET expires_at=?',(time.time()-1,))
  with self.assertRaises(AccessError):self.s.authenticate(self.t)
  with self.s.connect() as db:db.execute("UPDATE accounts SET access_reason='paid_lifetime'")
  self.assertTrue(self.s.authenticate(self.t)['active'])
 def test_network_and_global_limits(self):
  self.s.start_trial(self.t,'same')
  r=self.s.register('two@example.com','long-test-password','Two');self.s.start_trial(r['access_token'],'same')
  r=self.s.register('three@example.com','long-test-password','Three')
  with self.assertRaises(AccessError):self.s.start_trial(r['access_token'],'same')
  with self.s.connect() as db:db.execute("INSERT INTO usage(bucket,name,requests) VALUES(?,'*trial',100)",(self.s.day(),))
  with self.assertRaises(AccessError):self.s.reserve(self.t,3000)
  self.assertEqual(self.s.session(self.t)['trial']['remaining'],20)
 def test_parallel_reservations_cannot_exceed_quota(self):
  self.s.start_trial(self.t,'peer')
  def reserve(_):
   try:self.s.reserve(self.t,3000,minute_limit=100);return 1
   except AccessError:return 0
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:self.assertEqual(sum(pool.map(reserve,range(28))),20)
class TrialHttpTests(unittest.IsolatedAsyncioTestCase):
 async def test_registration_trial_access_and_assets(self):
  import httpx
  from gateway import Config,create_app
  with tempfile.TemporaryDirectory() as directory:
   app=create_app(Config(database=str(Path(directory)/'db')),upstream=lambda **kw:None)
   async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
    self.assertEqual((await c.post('/v1/account/trial')).status_code,401)
    result=await c.post('/v1/account/register',json=dict(email='http@example.com',password='long-test-password',name='HTTP'))
    h={'Authorization':'Bearer '+result.json()['access_token']}
    self.assertEqual((await c.get('/v1/access',headers=h)).status_code,403)
    trial=await c.post('/v1/account/trial',headers=h)
    self.assertEqual(trial.status_code,200)
    self.assertEqual(trial.json()['account']['trial']['remaining'],20)
    self.assertEqual((await c.get('/v1/access',headers=h)).status_code,200)
    self.assertEqual((await c.post('/v1/account/trial',headers=h)).status_code,409)
    for route in ('/','/guia','/site.css','/site.js','/guide/0.svg','/guide/1.svg','/guide/2.svg','/guide/3.svg'):
     r=await c.get(route);self.assertEqual(r.status_code,200,route)
    self.assertEqual((await c.get('/guide/4.svg')).status_code,404)

if __name__=='__main__':unittest.main()
