"""Malformed input and repeated operations against isolated temporary databases."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
import httpx
from gateway import Config, create_app


class BetaInputTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.upstream=AsyncMock()
        self.app=create_app(Config(database=str(Path(self.temp.name)/'db')), self.upstream)
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='https://test')

    async def asyncTearDown(self):
        await self.client.aclose()
        self.temp.cleanup()

    async def test_bad_unicode_in_credentials_is_400_not_server_error(self):
        for field in ('name','password','email'):
            data=dict(email='test@example.com',name='Test',password='temporary-password')
            data[field]='\ud800'*15
            import json
            result=await self.client.post('/v1/account/register', content=json.dumps(data), headers={'content-type':'application/json'})
            self.assertEqual(result.status_code,400)
        self.upstream.assert_not_awaited()

    async def test_deep_json_and_bad_unicode_never_reach_upstream(self):
        token=self.app.state.store.add('Fixture')
        headers={'authorization':'Bearer '+token,'content-type':'application/json'}
        for body in ('['*2000+'0'+']'*2000, '{"input":[{"role":"user","content":[{"type":"input_text","text":"\\ud800"}]}]}'):
            result=await self.client.post('/v1/responses',content=body,headers=headers)
            self.assertEqual(result.status_code,400)
        self.upstream.assert_not_awaited()

    async def test_logout_is_repeatable_and_session_stays_revoked(self):
        data=self.app.state.accounts.register('test@example.com','temporary-password','Test')
        headers={'authorization':'Bearer '+data['access_token']}
        for _ in range(2):
            self.assertEqual((await self.client.post('/v1/account/logout',headers=headers)).status_code,200)
        self.assertEqual((await self.client.get('/v1/account/me',headers=headers)).status_code,401)
        self.assertEqual((await self.client.post('/v1/account/logout')).status_code,401)


if __name__ == '__main__':
    unittest.main()
