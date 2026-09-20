"""Bounded, bearer-only account API for desktop and web clients.

Cookies are deliberately not accepted: cross-site forms cannot authorize changes.
"""
import asyncio
import json
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from accounts import AccountStore
from access_store import AccessError
from plans import public_plans
from payment_routes import install_payment_routes


def install_account_routes(app, database):
    store = AccountStore(database)
    app.state.accounts = store
    hashing_slots = asyncio.Semaphore(2)

    def token(request):
        value = request.headers.get('authorization', '')
        if not value.startswith('Bearer spc_') or len(value) > 150:
            raise AccessError(401, 'Inicia sesión para continuar.')
        return value[7:]

    def response(data, status=200):
        return JSONResponse(data, status_code=status, headers={
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})

    async def body(request):
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            raise AccessError(415, 'Se requiere JSON.')
        raw = bytearray()
        async with asyncio.timeout(10):
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > 8192: raise AccessError(413, 'Solicitud demasiado grande.')
        try: data = json.loads(raw)
        except (ValueError, UnicodeError): raise AccessError(400, 'Revisa los datos enviados.') from None
        if not isinstance(data, dict): raise AccessError(400, 'Revisa los datos enviados.')
        return data

    @app.exception_handler(AccessError)
    async def access_error(request, exc):
        return response({'error': {'message': exc.message}}, exc.status)

    install_payment_routes(app, database, token, body, response)

    @app.exception_handler(TimeoutError)
    async def timed_out(request, exc):
        return response({'error': {'message': 'La solicitud tardó demasiado. Vuelve a intentarlo.'}}, 408)

    @app.get('/v1/plans')
    async def plans():
        catalog = await run_in_threadpool(app.state.payments.catalog)
        return response({'payments_enabled': catalog['enabled'], 'automatic_renewal': False, 'plans': catalog['plans']})

    async def credentials(request, register=False):
        # Use the ASGI peer supplied by the configured proxy, never raw forwarded headers.
        peer = request.client.host if request.client else 'unknown'
        await run_in_threadpool(store.rate_limit, 'auth-ip:' + peer, 20, 300)
        data = await body(request)
        email = data.get('email', '')
        if isinstance(email, str):
            await run_in_threadpool(store.rate_limit, 'auth-email:' + email.strip().casefold(), 10, 300)
        async with asyncio.timeout(10):
            async with hashing_slots:
                if register:
                    result = await run_in_threadpool(store.register, email, data.get('password'), data.get('name'))
                else:
                    result = await run_in_threadpool(store.login, email, data.get('password'))
        return response(result, 201 if register else 200)

    @app.post('/v1/account/register')
    async def register(request: Request): return await credentials(request, True)

    @app.post('/v1/account/login')
    async def login(request: Request): return await credentials(request)

    @app.get('/v1/account/me')
    async def me(request: Request):
        return response({'account': await run_in_threadpool(store.session, token(request))})

    @app.post('/v1/account/trial')
    async def trial(request:Request):
        peer=request.client.host if request.client else 'unknown'
        return response({'account':await run_in_threadpool(store.start_trial,token(request),peer)})

    @app.post('/v1/account/logout')
    async def logout(request: Request):
        value = token(request)
        await run_in_threadpool(store.session, value)
        await run_in_threadpool(store.logout, value)
        return response({'ok': True})

    @app.post('/v1/account/owner')
    async def owner(request: Request):
        value = token(request)
        account = await run_in_threadpool(store.session, value)
        await run_in_threadpool(store.rate_limit, 'owner:' + account['id'], 5, 3600)
        data = await body(request)
        result = await run_in_threadpool(store.bootstrap_owner, value, data.get('code'),
                                        os.getenv('ADMIN_BOOTSTRAP_USER', ''))
        return response({'account': result})

    @app.get('/v1/admin/accounts')
    async def listing(request: Request):
        return response({'accounts': await run_in_threadpool(store.list_accounts, token(request))})

    @app.post('/v1/admin/accounts/{account_id}')
    async def change(account_id: str, request: Request):
        value = token(request)
        # Check permission before consuming a request body.
        account = await run_in_threadpool(store.session, value)
        if account['role'] != 'admin': raise AccessError(403, 'Solo el administrador puede cambiar accesos.')
        data = await body(request)
        await run_in_threadpool(store.set_access, value, account_id, data.get('action'), data.get('daily_limit', 600))
        return response({'ok': True})
