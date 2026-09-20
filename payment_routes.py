from pathlib import Path
import qrcode
from qrcode.image.svg import SvgPathFillImage
from fastapi import Request
from fastapi.responses import FileResponse, Response
from starlette.concurrency import run_in_threadpool
from access_store import AccessError
from manual_payments import PaymentStore


def install_payment_routes(app, database, token, body, response):
    store = PaymentStore(database)
    app.state.payments = store
    root = Path(__file__).parent

    @app.get('/cuenta')
    async def page():
        return FileResponse(root/'account.html', headers={
            'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff'})

    @app.get('/account.js')
    async def script(): return FileResponse(root/'account.js', media_type='text/javascript')

    @app.get('/account.css')
    async def style(): return FileResponse(root/'account.css', media_type='text/css')

    @app.get('/v1/payments/config')
    async def config(): return response(await run_in_threadpool(store.catalog))

    @app.get('/v1/payments/qr.svg')
    async def qr():
        config = await run_in_threadpool(store.catalog)
        if not config['enabled']: raise AccessError(409, 'Los cobros están desactivados.')
        image = await run_in_threadpool(qrcode.make, config['payment_url'], image_factory=SvgPathFillImage)
        return Response(image.to_string(), media_type='image/svg+xml', headers={'Cache-Control':'no-store'})

    @app.get('/v1/payments/orders')
    async def orders(request: Request): return response({'orders': await run_in_threadpool(store.orders, token(request))})

    @app.post('/v1/payments/orders')
    async def create(request: Request):
        value = token(request)
        account = await run_in_threadpool(store.session, value)
        await run_in_threadpool(store.rate_limit, 'payment:' + account['id'], 10, 3600)
        data = await body(request)
        return response(await run_in_threadpool(store.create_order, value, data.get('plan')))

    @app.post('/v1/payments/orders/{identifier}/report')
    async def report(identifier: str, request: Request):
        value = token(request)
        data = await body(request)
        return response(await run_in_threadpool(store.report, value, identifier, data.get('payer'), data.get('reference')))

    @app.get('/v1/admin/payments')
    async def queue(request: Request): return response({'orders': await run_in_threadpool(store.orders, token(request), True)})

    @app.post('/v1/payments/orders/{identifier}/cancel')
    async def cancel(identifier: str, request: Request):
        return response(await run_in_threadpool(store.cancel, token(request), identifier))

    @app.post('/v1/admin/payments/settings')
    async def settings(request: Request):
        value = token(request)
        await run_in_threadpool(store.admin, value)
        return response(await run_in_threadpool(store.configure, value, await body(request)))

    @app.post('/v1/admin/payments/{identifier}/review')
    async def review(identifier: str, request: Request):
        value = token(request)
        await run_in_threadpool(store.admin, value)
        data = await body(request)
        return response(await run_in_threadpool(store.review, value, identifier, data.get('action'),
            data.get('reference',''), data.get('note',''), data.get('received_cents')))
