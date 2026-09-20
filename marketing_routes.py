from pathlib import Path
from fastapi.responses import FileResponse,Response
from fastapi import HTTPException
from guide_visuals import svg

def install_marketing_routes(app):
    root=Path(__file__).parent
    headers={'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
    @app.get('/guia')
    async def guide():return FileResponse(root/'guide.html',headers=headers)
    @app.get('/site.css')
    async def style():return FileResponse(root/'site.css',media_type='text/css')
    @app.get('/site.js')
    async def script():return FileResponse(root/'site.js',media_type='text/javascript')
    @app.get('/guide/{step}.svg')
    async def illustration(step:int):
        if not 0<=step<=3:raise HTTPException(404)
        return Response(svg(step),media_type='image/svg+xml',headers={'Cache-Control':'public,max-age=3600','X-Content-Type-Options':'nosniff'})
