import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock
from concurrent.futures import ThreadPoolExecutor

import httpx
from openai import AsyncOpenAI
from gateway import Config,create_app,clean_payload
from access_store import AccessStore,AccessError

PAYLOAD={'model':'untrusted-model','instructions':'Respond in JSON.','input':[{'role':'user','content':[{'type':'input_text','text':'Which option?'}]}],
         'max_output_tokens':4000,'reasoning':{'effort':'medium'},'store':False}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'db.sqlite3';self.store=AccessStore(self.path)

    def test_only_hash_stored_and_revocation_persists(self):
        token=self.store.add('Ana',3)
        self.assertNotIn(token.encode(),self.path.read_bytes())
        self.assertEqual(self.store.authenticate(token)['name'],'Ana')
        self.store.revoke('Ana')
        with self.assertRaises(AccessError):AccessStore(self.path).authenticate(token)

    def test_atomic_limits_survive_restarts_and_reset_on_utc_day(self):
        token=self.store.add('Ana',2)
        def reserve(_):
            try:self.store.reserve(token,10,now=1700000000);return True
            except AccessError:return False
        with ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(sum(pool.map(reserve,range(8))),2)
        with self.assertRaises(AccessError):AccessStore(self.path).reserve(token,10,now=1700000000)
        self.store.reserve(token,10,now=1700086400)

    def test_global_limit_applies_across_people(self):
        a=self.store.add('Ana');b=self.store.add('Bea')
        self.store.reserve(a,1)
        with self.assertRaises(AccessError):self.store.reserve(b,1)

    def test_minute_limit_and_invalid_names(self):
        token=self.store.add('Ana')
        self.store.reserve(token,100,minute_limit=1,now=1700000000)
        with self.assertRaises(AccessError):self.store.reserve(token,100,minute_limit=1,now=1700000001)
        self.store.reserve(token,100,minute_limit=1,now=1700000060)
        for name in ('*','','bad\nname'):
            with self.assertRaises(ValueError):self.store.add(name)


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_portal_exposes_setup_without_secrets_or_api_calls(self):
        response=await self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn('Canvas',response.text)
        self.assertNotIn(self.code,response.text)
        self.assertIn("frame-ancestors 'none'",response.headers['content-security-policy'])
        self.upstream.assert_not_awaited()
    async def test_high_reasoning_is_preserved_with_server_budget(self):
        payload=clean_payload({**PAYLOAD,'reasoning':{'effort':'high'},'max_output_tokens':10000},Config())
        self.assertEqual(payload['reasoning']['effort'],'high')
        self.assertEqual(payload['max_output_tokens'],4096)
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.config=Config(database=str(Path(self.tmp.name)/'db.sqlite3'),model='owner-model')
        self.upstream=AsyncMock(return_value=NS(status='completed',output_text='{"answers":["Correct"],"confidence":1}',usage=NS(input_tokens=40,output_tokens=20)))
        self.app=create_app(self.config,self.upstream)
        self.code=self.app.state.store.add('Ana',3)
        self.headers={'Authorization':'Bearer '+self.code}
        self.lifespan=self.app.router.lifespan_context(self.app)
        await self.lifespan.__aenter__()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='https://gateway.test')
    async def asyncTearDown(self):
        await self.client.aclose();await self.lifespan.__aexit__(None,None,None);self.tmp.cleanup()

    async def test_auth_and_revoke_prevent_api_calls(self):
        self.assertEqual((await self.client.post('/v1/responses',json=PAYLOAD)).status_code,401)
        self.assertEqual((await self.client.get('/v1/access',headers=self.headers)).status_code,200)
        self.app.state.store.revoke('Ana')
        self.assertEqual((await self.client.post('/v1/responses',json=PAYLOAD,headers=self.headers)).status_code,401)
        self.upstream.assert_not_awaited()

    async def test_sdk_compatible_response_and_server_policy(self):
        sdk=AsyncOpenAI(api_key=self.code,base_url='https://gateway.test/v1',max_retries=0,
                        http_client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app)))
        try:
            result=await sdk.responses.create(**{**PAYLOAD,'max_output_tokens':999999,'store':True})
            self.assertIn('Correct',result.output_text)
            self.assertEqual(result.status,'completed')
        finally:await sdk.close()
        sent=self.upstream.call_args.kwargs
        self.assertEqual(sent['model'],'owner-model');self.assertFalse(sent['store'])
        self.assertEqual(sent['max_output_tokens'],4096)
        report=self.app.state.store.report()[0]
        self.assertEqual((report['requests'],report['input_tokens'],report['output_tokens']),(1,40,20))

    async def test_quotas_block_more_upstream_calls(self):
        for _ in range(3):self.assertEqual((await self.client.post('/v1/responses',headers=self.headers,json=PAYLOAD)).status_code,200)
        self.assertEqual((await self.client.post('/v1/responses',headers=self.headers,json=PAYLOAD)).status_code,429)
        self.assertEqual(self.upstream.await_count,3)

    async def test_no_tools_remote_images_or_oversized_payload(self):
        for bad in ({**PAYLOAD,'tools':[{'type':'web_search'}]},
                    {**PAYLOAD,'input':[{'role':'user','content':[{'type':'input_image','image_url':'https://example.com/x.png'}]}]},
                    {**PAYLOAD,'input':[{'role':'user','content':[{'type':'input_text','text':'x'*48001}]}]}):
            self.assertEqual((await self.client.post('/v1/responses',headers=self.headers,json=bad)).status_code,400)
        self.config.body_limit=20
        self.assertEqual((await self.client.post('/v1/responses',headers=self.headers,json=PAYLOAD)).status_code,413)
        self.upstream.assert_not_awaited()

    async def test_upstream_errors_never_expose_secrets_and_reservation_counts(self):
        self.upstream.side_effect=RuntimeError('PRIVATE_API_KEY PRIVATE_QUESTION')
        response=await self.client.post('/v1/responses',headers=self.headers,json=PAYLOAD)
        self.assertEqual(response.status_code,503)
        self.assertNotIn('PRIVATE',response.text)
        self.assertEqual(self.app.state.store.report()[0]['requests'],1)

    async def test_concurrent_same_code_is_rejected_and_released(self):
        started=asyncio.Event();finish=asyncio.Event()
        async def delayed(**kwargs):
            started.set();await finish.wait()
            return NS(status='completed',output_text='{}',usage=None)
        self.upstream.side_effect=delayed
        first=asyncio.create_task(self.client.post('/v1/responses',headers=self.headers,json=PAYLOAD))
        await asyncio.wait_for(started.wait(),2)
        second=await self.client.post('/v1/responses',headers=self.headers,json=PAYLOAD)
        self.assertEqual(second.status_code,429)
        finish.set();self.assertEqual((await first).status_code,200)
        self.assertEqual((await self.client.post('/v1/responses',headers=self.headers,json=PAYLOAD)).status_code,200)

    async def test_incomplete_status_is_preserved(self):
        self.upstream.return_value.status='incomplete'
        response=await self.client.post('/v1/responses',headers=self.headers,json=PAYLOAD)
        self.assertEqual(response.json()['status'],'incomplete')


if __name__=='__main__':unittest.main()
