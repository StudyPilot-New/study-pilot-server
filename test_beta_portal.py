"""Offline browser regressions: no live service, credentials, or payments."""
import asyncio
import json
from pathlib import Path
import unittest
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
TOKEN = 'spc_' + 'x' * 43


class PortalBetaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(channel='chrome', headless=True)
        self.page = await self.browser.new_page(viewport={'width':1280, 'height':900})
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.calls = []
        self.fail = None
        self.delay = False
        self.active = False
        self.payments = False
        await self.page.route('**/*', self.route)
        await self.page.goto('https://study.test/cuenta')

    async def asyncTearDown(self):
        await self.browser.close()
        await self.pw.stop()
        self.assertEqual(self.errors, [])

    async def route(self, route):
        path = route.request.url.split('study.test', 1)[-1]
        self.calls.append(path)
        assets = {'/cuenta':'account.html', '/account.js':'account.js', '/account.css':'account.css'}
        if path in assets:
            mime = 'text/html' if path=='/cuenta' else 'text/javascript' if path.endswith('.js') else 'text/css'
            return await route.fulfill(body=(ROOT/assets[path]).read_bytes(), content_type=mime)
        if self.fail == path:
            return await route.fulfill(status=502, body='<html>Gateway unavailable</html>', content_type='text/html')
        if self.fail == 'offline':
            return await route.abort('internetdisconnected')
        if self.fail == 'expired' and path=='/v1/account/me':
            return await route.fulfill(status=401, json={'error':{'message':'Expired'}})
        if self.delay and path=='/v1/account/trial':
            await asyncio.sleep(.25)
        if path=='/v1/account/trial': self.active=True
        account = {'display_name':'Beta friend','active':self.active,'role':'member','access_reason':'trial' if self.active else None, 'trial':None}
        data = {
            '/v1/account/login':{'access_token':TOKEN,'account':account},
            '/v1/account/me':{'account':account},
            '/v1/payments/config':{'enabled':self.payments,'cashtag':'$test','plans':[]},
            '/v1/payments/orders':{'orders':[]},
            '/v1/account/trial':{'account':account},
            '/v1/account/logout':{'ok':True},
        }.get(path)
        await route.fulfill(status=200 if data is not None else 404, json=data or {})

    async def login(self):
        await self.page.locator('#login input[name=email]').fill('beta@example.com')
        await self.page.locator('#login input[name=password]').fill('temporary-password')
        await self.page.locator('#login button').click()
        await self.page.wait_for_function("document.querySelector('#welcome').textContent==='Hello, Beta friend' && !document.querySelector('#refresh').disabled")

    async def test_expired_session_returns_to_login_and_removes_private_code(self):
        await self.login()
        self.fail='expired'
        await self.page.locator('#refresh').click()
        await self.page.wait_for_function("!document.querySelector('#auth').hidden")
        self.assertTrue(await self.page.locator('#member').is_hidden())
        self.assertEqual(await self.page.evaluate('session'), '')
        self.assertIn('Sign in again', await self.page.locator('#message').inner_text())

    async def test_html_response_has_recovery_and_session_can_refresh(self):
        self.fail='/v1/payments/config'
        await self.page.locator('#login input[name=email]').fill('beta@example.com')
        await self.page.locator('#login input[name=password]').fill('temporary-password')
        await self.page.locator('#login button').click()
        await self.page.wait_for_function("document.querySelector('#message').textContent.includes('unreadable')")
        self.fail=None
        await self.page.locator('#refresh').click()
        await self.page.wait_for_function("document.querySelector('#message').textContent===''")
        self.assertFalse(await self.page.locator('#monthly').is_enabled())

    async def test_repeated_trial_click_only_sends_one_request(self):
        await self.login()
        self.delay=True
        await self.page.evaluate("for(let i=0;i<5;i++)document.querySelector('#startTrial').dispatchEvent(new MouseEvent('click'))")
        await self.page.wait_for_function("document.querySelector('#message').textContent.includes('Trial activated')")
        self.assertEqual(self.calls.count('/v1/account/trial'), 1)
        self.assertFalse(await self.page.locator('#monthly').is_enabled())

    async def test_offline_logout_clears_local_session_and_explains_limit(self):
        await self.login()
        self.fail='offline'
        await self.page.locator('#logout').click()
        await self.page.wait_for_function("!document.querySelector('#auth').hidden")
        self.assertEqual(await self.page.evaluate('session'), '')
        self.assertIn('could not be confirmed', await self.page.locator('#message').inner_text())
        self.assertEqual(await self.page.evaluate('localStorage.length'), 0)

    async def test_keyboard_mobile_layout_and_screenshot(self):
        await self.page.set_viewport_size({'width':390, 'height':844})
        await self.page.keyboard.press('Tab')
        self.assertEqual(await self.page.evaluate('document.activeElement.tagName'), 'A')
        self.assertTrue(await self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        await self.page.screenshot(path=str(ROOT/'beta-portal-mobile.png'), full_page=True)
        await self.page.set_viewport_size({'width':1280, 'height':900})
        await self.login()
        await self.page.screenshot(path=str(ROOT/'beta-portal-desktop.png'), full_page=True)

    async def test_timeout_restores_controls_and_does_not_retry_mutation(self):
        await self.login()
        await self.page.evaluate("AbortSignal.timeout = () => AbortSignal.abort(new DOMException('Timed out', 'TimeoutError'))")
        await self.page.locator('#startTrial').click()
        await self.page.wait_for_function("document.querySelector('#message').textContent.includes('timed out')")
        self.assertTrue(await self.page.locator('#startTrial').is_enabled())
        self.assertEqual(self.calls.count('/v1/account/trial'), 0)
        self.assertEqual(await self.page.evaluate('session'), TOKEN)

    async def test_offline_refresh_can_recover_without_losing_session(self):
        await self.login()
        self.fail='offline'
        await self.page.locator('#refresh').click()
        await self.page.wait_for_function("document.querySelector('#message').textContent.includes('Connection lost')")
        self.fail=None
        await self.page.locator('#refresh').click()
        await self.page.wait_for_function("document.querySelector('#message').textContent===''")
        self.assertEqual(await self.page.evaluate('session'), TOKEN)


if __name__ == '__main__':
    unittest.main()
