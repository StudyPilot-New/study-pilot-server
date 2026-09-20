"""Study Pilot C private Responses gateway; one worker, behind HTTPS proxy."""
import asyncio
import base64
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from portal import home_html
from openai import AsyncOpenAI
from access_store import AccessStore, AccessError
from account_routes import install_account_routes


@dataclass
class Config:
    database: str = 'data/access.sqlite3'
    model: str = 'gpt-5.6-luna'
    daily_limit: int = 3000
    concurrency: int = 4
    body_limit: int = 12 * 1024 * 1024
    output_limit: int = 4096


def clean_payload(data, config):
    allowed = {'model','input','instructions','max_output_tokens','reasoning','store','prompt_cache_key'}
    if not isinstance(data,dict) or set(data)-allowed:
        raise ValueError('Formato de solicitud no permitido.')
    instructions = data.get('instructions','')
    if not isinstance(instructions,str) or len(instructions)>16000: raise ValueError('Instrucciones demasiado largas.')
    messages = data.get('input')
    if not isinstance(messages,list) or not 1<=len(messages)<=4: raise ValueError('Contenido no válido.')
    chars, images = 0, 0
    sanitized = []
    for message in messages:
        if not isinstance(message,dict) or set(message)-{'role','content'} or message.get('role')!='user': raise ValueError('Mensaje no permitido.')
        content = message.get('content')
        if not isinstance(content,list) or not 1<=len(content)<=12: raise ValueError('Contenido no permitido.')
        parts = []
        for part in content:
            if not isinstance(part,dict): raise ValueError('Contenido no permitido.')
            if part.get('type')=='input_text':
                if set(part)-{'type','text'} or not isinstance(part.get('text'),str): raise ValueError('Texto no válido.')
                chars += len(part['text'])
                if chars>48000: raise ValueError('Texto demasiado largo.')
                parts.append({'type':'input_text','text':part['text']})
            elif part.get('type')=='input_image':
                if set(part)-{'type','image_url','detail'}: raise ValueError('Imagen no válida.')
                image = part.get('image_url','')
                if not isinstance(image,str) or not image.startswith(('data:image/png;base64,','data:image/jpeg;base64,')): raise ValueError('Se requieren imágenes PNG/JPEG incluidas, no URLs externas.')
                try: raw = base64.b64decode(image.split(',',1)[1],validate=True)
                except (ValueError,TypeError): raise ValueError('Imagen no válida.') from None
                if not raw.startswith((b'\x89PNG\r\n\x1a\n',b'\xff\xd8\xff')): raise ValueError('Imagen no válida.')
                images += 1
                if images>8 or len(raw)>8*1024*1024: raise ValueError('Demasiadas imágenes o imagen demasiado grande.')
                parts.append({'type':'input_image','image_url':image,'detail':'high'})
            else: raise ValueError('Tipo de contenido no permitido.')
        sanitized.append({'role':'user','content':parts})
    count = data.get('max_output_tokens',180)
    if type(count) is not int or count<16: raise ValueError('Límite de salida no válido.')
    reasoning = data.get('reasoning',{})
    if not isinstance(reasoning,dict) or set(reasoning)-{'effort'}: raise ValueError('Razonamiento no válido.')
    effort = reasoning.get('effort','none')
    if effort not in ('none','minimal','low','medium','high'): raise ValueError('Razonamiento no válido.')
    return dict(model=config.model,input=sanitized,instructions=instructions,
                max_output_tokens=min(count,config.output_limit),reasoning={'effort':effort},
                store=False,prompt_cache_key='study-pilot-shared-v1')


def error(status, message):
    return JSONResponse({'error':{'message':message,'type':'study_pilot_access_error','code':str(status)}},status_code=status,
                        headers={'Cache-Control':'no-store'})


def create_app(config=None, upstream=None):
    config = config or Config(database=os.getenv('ACCESS_DB','data/access.sqlite3'),
                              model=os.getenv('OPENAI_MODEL','gpt-5.6-luna'),
                              daily_limit=int(os.getenv('GLOBAL_DAILY_REQUESTS','3000')),
                              concurrency=int(os.getenv('MAX_CONCURRENT','4')))
    if config.daily_limit<1 or not 1<=config.concurrency<=32: raise ValueError('Límites del servidor no válidos.')
    store = AccessStore(config.database)

    @asynccontextmanager
    async def lifespan(app):
        client = None
        if upstream is None:
            key = os.getenv('OPENAI_API_KEY','')
            if not key: raise RuntimeError('Configura OPENAI_API_KEY únicamente en el servidor.')
            client = AsyncOpenAI(api_key=key,base_url='https://api.openai.com/v1',max_retries=0,timeout=75)
            app.state.upstream = client.responses.create
        else: app.state.upstream = upstream
        try: yield
        finally:
            if client is not None: await client.close()

    app = FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.state.store = store
    install_account_routes(app, config.database)
    active = set()

    def token_for(request):
        header = request.headers.get('authorization','')
        if not header.startswith('Bearer spc_') or len(header)>150:
            raise AccessError(401,'Se necesita un código de acceso válido.')
        return header[7:]

    @app.get('/health')
    async def health(): return {'service':'study-pilot-c','status':'ok'}

    @app.get('/',response_class=HTMLResponse)
    async def home():
        return HTMLResponse(home_html(os.getenv('DOWNLOAD_URL',''),any((Path(__file__).parent/'downloads'/name).is_file() for name in ('StudyPilotC-Setup.exe','StudyPilotC.zip'))),headers={
            'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
            'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'})

    @app.get('/download')
    async def download():
        package=Path(__file__).parent/'downloads/StudyPilotC-Setup.exe'
        if not package.is_file():package=Path(__file__).parent/'downloads/StudyPilotC.zip'
        if not package.is_file():return error(404,'El administrador todavía no publicó el paquete de escritorio.')
        return FileResponse(package,media_type='application/octet-stream' if package.suffix=='.exe' else 'application/zip',filename=package.name,
                            headers={'X-Content-Type-Options':'nosniff'})

    @app.get('/v1/access')
    async def access(request:Request):
        try:
            user = store.authenticate(token_for(request))
            return JSONResponse({'service':'study-pilot-c','active':True,'daily_limit':user['daily_limit']},headers={'Cache-Control':'no-store'})
        except AccessError as exc: return error(exc.status,exc.message)

    @app.post('/v1/responses')
    async def responses(request:Request):
        try:
            token = token_for(request)
            user = store.authenticate(token)
            if user['name'] in active or len(active)>=config.concurrency:
                return error(429,'Servidor ocupado. La aplicación volverá a intentarlo.')
            if request.headers.get('content-type','').split(';')[0]!='application/json':
                return error(415,'Se requiere JSON.')
            active.add(user['name'])
            try:
                async with asyncio.timeout(15):
                    body = bytearray()
                    async for chunk in request.stream():
                        body.extend(chunk)
                        if len(body)>config.body_limit: return error(413,'Solicitud demasiado grande.')
                try: payload = clean_payload(json.loads(body),config)
                except (ValueError,TypeError,UnicodeError): return error(400,'Contenido inválido o no compatible con esta aplicación.')
                name, day = store.reserve(token,config.daily_limit)
                try:
                    async with asyncio.timeout(80):
                        response = await app.state.upstream(**payload)
                except Exception:
                    # Never expose upstream exceptions, headers, credentials or prompts.
                    return error(503,'El servicio de análisis no está disponible. Se volverá a intentar.')
                usage = getattr(response,'usage',None)
                if usage:
                    store.record_tokens(name,day,int(getattr(usage,'input_tokens',0)),int(getattr(usage,'output_tokens',0)))
                text = getattr(response,'output_text','')
                return JSONResponse({'id':'resp_'+uuid.uuid4().hex,'object':'response','created_at':int(time.time()),
                    'status':getattr(response,'status','completed'),'model':config.model,
                    'output':[{'id':'msg_'+uuid.uuid4().hex,'type':'message','role':'assistant','status':'completed',
                               'content':[{'type':'output_text','text':text,'annotations':[]}]}]},headers={'Cache-Control':'no-store'})
            finally: active.discard(user['name'])
        except AccessError as exc: return error(exc.status,exc.message)
        except TimeoutError: return error(408,'La carga tardó demasiado. Inténtalo de nuevo.')

    return app
