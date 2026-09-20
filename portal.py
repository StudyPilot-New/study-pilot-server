"""Public setup page. No credentials, private user data or API calls."""
from html import escape
from urllib.parse import urlsplit

def home_html(download_url='',local_download=False):
    parsed=urlsplit(download_url)
    valid=parsed.scheme=='https' and bool(parsed.hostname) and not parsed.username and not parsed.password
    link='/download' if local_download else download_url
    download=('<a class="primary" href="'+escape(link,quote=True)+'" rel="noopener">Descargar para Windows</a>' if local_download or valid
              else '<p class="note">Pide a tu administrador el ZIP de escritorio compartido y tu código individual.</p>')
    return '''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Study Pilot C · Empieza tu sesión</title><style>
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#142c3c;background:#f1f5f7}*{box-sizing:border-box}body{margin:0}
main{max-width:1060px;margin:auto;padding:32px 24px 60px}nav{display:flex;justify-content:space-between;gap:24px;align-items:center;margin-bottom:52px}
.brand{font-weight:800;letter-spacing:-.5px;font-size:22px}.tag{background:#d9f1e9;border-radius:30px;padding:8px 14px;color:#075e52;font-size:13px}
.hero{background:#142c3c;color:white;border-radius:24px;padding:46px;display:grid;grid-template-columns:1.5fr 1fr;gap:36px}
h1{font-size:clamp(32px,5vw,52px);line-height:1.12;letter-spacing:-1.5px;margin:12px 0 20px}p{line-height:1.65}h2{font-size:22px}.eyebrow{color:#a7f3d0;font-size:12px;font-weight:750;letter-spacing:2px}
.hero p{color:#d2e2eb}.primary{display:inline-block;background:#a7f3d0;color:#142c3c;padding:14px 20px;text-decoration:none;border-radius:10px;font-weight:750;margin-top:12px}
.setup{border:1px solid #547084;padding:24px;border-radius:16px;align-self:center}.setup h2{margin-top:0}code{overflow-wrap:anywhere;background:#24485d;display:block;padding:12px;border-radius:8px;color:#fff;font-size:13px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:26px 0}.card{background:white;padding:26px;border:1px solid #d8e2e8;border-radius:16px}.number{color:#087f73;font-weight:800;font-size:13px}.card h2{font-size:18px}.card p,.note{font-size:15px}.help{padding:16px 0}details{background:white;border:1px solid #d8e2e8;border-radius:12px;padding:18px;margin:12px 0}summary{font-weight:650;cursor:pointer}details p{max-width:80ch}footer{margin-top:30px;font-size:13px;color:#536579}a:focus-visible,summary:focus-visible{outline:3px solid #087f73;outline-offset:5px}
@media(max-width:740px){.hero,.steps{grid-template-columns:1fr}.hero{padding:28px}nav{margin-bottom:28px;flex-wrap:wrap}.tag{font-size:12px}}
</style></head><body><main><nav><span class="brand">Study Pilot C</span><span class="tag">Acceso con código individual</span></nav>
<section class="hero"><div><div class="eyebrow">TU ESPACIO DE ESTUDIO</div><h1>Prepara tu sesión.<br>Empieza con claridad.</h1><p>Instala la app, activa tu acceso y abre tu actividad desde Canvas. Tu administrador configura la API por ti.</p>'''+download+'''</div><aside class="setup"><h2>Para activar la app</h2><p>Abre <strong>Guía de inicio</strong> e introduce la dirección de esta web y el código que recibiste.</p><p>No necesitas una clave de OpenAI. Sí necesitas tu propia cuenta de la universidad.</p></aside></section>
<section class="steps" aria-label="Primeros pasos"><article class="card"><span class="number">01 / INSTALA</span><h2>Abre la aplicación</h2><p>Extrae todo el ZIP y abre Study Pilot C.exe. Conserva la carpeta _internal junto al ejecutable. Necesitas Windows y Chrome.</p></article>
<article class="card"><span class="number">02 / ACTIVA</span><h2>Usa tu código</h2><p>En Guía de inicio, pega la URL de esta web y tu código spc_. Pulsa Activar acceso y después Iniciar sesión.</p></article>
<article class="card"><span class="number">03 / CONECTA</span><h2>Entra desde Canvas</h2><p>Pega el enlace de la actividad de Canvas en el nuevo Chrome de la app. Inicia sesión con la universidad y abre McGraw desde allí.</p></article></section>
<section class="help"><h2>Todo listo para empezar</h2><details><summary>¿Puedo elegir una IA con más razonamiento?</summary><p>Sí. En Ajustes de sesión, elige Mayor precisión en Potencia de la IA. Puede tardar más y consumir más API. Se aplica al iniciar la siguiente sesión; no garantiza acertar todas las preguntas.</p></details>
<details><summary>¿Qué hago si Reading o un arrastre se bloquean?</summary><p>La app intenta recuperarse automáticamente. También puedes pulsar Recuperar para liberar el arrastre y revisar la página conservando la memoria de la sesión. Si persiste, guarda el error del registro y avisa al administrador.</p></details>
<details><summary>¿La actividad se ejecuta en esta web?</summary><p>Chrome y Canvas se ejecutan en tu laptop. Este servidor proporciona el acceso compartido a la IA. Las preguntas, imágenes y descripciones usadas para el análisis pasan por este servidor y por OpenAI.</p></details></section>
<footer>Study Pilot C · Aplicación independiente. Conserva tu código en privado y revisa el registro de tu sesión.</footer></main></body></html>'''
