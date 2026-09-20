# Study Pilot C · tu API, acceso para tus amigos

Esta carpeta es para ti. El ZIP «Amigos» es el que compartes. La clave OpenAI permanece únicamente en el servidor; cada amigo usa un código individual que puedes revocar.

## Estado de la entrega

El programa y el servidor están preparados. **Todavía no existe un servidor público ni un dominio configurado.** No se ha copiado ni publicado tu clave. Antes de que tus amigos puedan usar el acceso incluido, completa el despliegue y prueba un código.

## 1. Lo que necesitas

- Un servidor Linux que puedas administrar por SSH, con Docker Engine y el complemento Docker Compose instalados. Sigue la [instalación oficial de Docker](https://docs.docker.com/engine/install/).
- Un dominio o subdominio, por ejemplo `study.tu-dominio.com`, cuyo registro DNS A apunte a la IP pública del servidor. Si existe AAAA, debe apuntar a un IPv6 que también funcione.
- Puertos TCP 80 y 443 accesibles en el firewall del servidor y del proveedor. El puerto interno 8000 no se publica.
- Tu clave OpenAI, saldo y acceso al modelo configurado. Puedes usar la misma clave que ya utilizas. No la envíes a tus amigos ni la pegues en el chat.

El servidor, el dominio y todas las llamadas API se pagan con tus cuentas. Esta entrega no contrata ni publica servicios externos.

## 2. Desplegar

Copia esta carpeta completa al servidor, por ejemplo `/opt/study-pilot`. Desde una terminal SSH situada en esa carpeta:

```sh
cp .env.example .env
chmod 600 .env
nano .env
```

Dentro del editor, completa `OPENAI_API_KEY`, `PUBLIC_DOMAIN` (solo nombre, sin `https://`) y `ACME_EMAIL`. Deja tu modelo actual si tienes acceso. Guarda el archivo. No pongas la clave dentro de comandos que vayan a quedar en el historial.

```sh
docker compose up -d --build
docker compose ps
```

Caddy solicita y renueva el certificado HTTPS cuando el DNS y los puertos están correctos. Abre `https://study.tu-dominio.com/health`: debe mostrar `service: study-pilot-c` y `status: ok`. Este chequeo no consume API y no demuestra todavía que la clave o el modelo funcionen.

No uses `docker compose config` para compartir diagnósticos: puede mostrar variables resueltas, incluida tu clave. Revisa personalmente los registros antes de enviarlos.

## 3. Dar acceso a cada amigo

Ejemplo: crear el acceso de Ana con hasta 600 solicitudes de análisis por día UTC:

```sh
docker compose exec gateway python manage_access.py add Ana --limit 600
```

El comando muestra una sola vez un código que empieza por `spc_`. Envía en privado a Ana su código, la URL HTTPS del servidor y el ZIP «Amigos». No necesita cuenta ni clave de OpenAI; sí necesita su propia cuenta de McGraw.

Repite el comando con un nombre distinto por persona. El servidor guarda solo una huella del código. Si lo pierdes, revoca ese acceso y crea uno nuevo con otro nombre, por ejemplo `Ana-2`.

```sh
docker compose exec gateway python manage_access.py list
docker compose exec gateway python manage_access.py revoke Ana
```

La revocación bloquea nuevas solicitudes; una que ya esté ejecutándose puede terminar. `list` muestra estado, solicitudes y tokens del día UTC, sin códigos ni enunciados. Los contadores sobreviven a reinicios gracias al volumen de datos.

## 4. Límites y gastos

Por defecto hay 600 solicitudes/día por código, 3000/día en total, 20/minuto por código, una consulta simultánea por persona y cuatro en todo el servidor. Una pregunta puede generar varias solicitudes cuando se revisa o se recupera de un error. Un límite diario alcanzado impide nuevos análisis hasta el siguiente día UTC o hasta que tú ajustes el límite.

El servidor cuenta una solicitud al reservarla, antes de enviarla a OpenAI; un fallo de red también consume esa reserva. Esto evita que los reintentos eludan los límites. El modelo lo fija el servidor, la salida se limita a 4096 tokens y no se permiten herramientas ni URLs externas para imágenes.

**Los límites son de solicitudes, no un presupuesto exacto en dólares.** Consulta también el consumo de tu proyecto en OpenAI. Para cambiar el límite total o concurrencia, edita `.env` y ejecuta `docker compose up -d`. Para cambiar el límite de una persona, revoca y crea un acceso nuevo con el límite deseado. Mantén un solo contenedor gateway y un solo worker; esta versión usa SQLite local y control de concurrencia en memoria.

## 5. Prueba antes de compartir

1. Crea un código de prueba e instala el ZIP Amigos en una carpeta nueva de Windows.
2. Ejecuta `Configurar acceso.bat`, introduce tu URL HTTPS y el código. Debe mostrar «Acceso activado» sin hacer una llamada de pago.
3. Abre la aplicación y prueba una pregunta en una actividad propia. Este paso sí usa tu API y confirma acceso al modelo, análisis y conexión de extremo a extremo.
4. Revisa `manage_access.py list` y confirma que aumenta el uso del código.
5. Revoca el código de prueba y comprueba que ya no permite activar el acceso. Emite uno definitivo.

Las pruebas automáticas locales no sustituyen esta comprobación pública. No se ha hecho una sesión real de dos horas ni un despliegue externo desde esta entrega.

## 6. Mantenimiento y privacidad

- No compartas `.env`, el volumen `access_data` ni la carpeta personal de la app.
- Cada amigo guarda su código en `access.json` en su PC. Puede copiarlo; el control disponible es revocación y límites, no un sistema anticopia por dispositivo.
- Preguntas, imágenes y descripciones pasan por tu servidor y luego por OpenAI. El servidor de esta entrega no registra esos contenidos; almacena nombres, huellas de códigos y contadores. No actives registros detallados de peticiones.
- Haz copias privadas del volumen de datos antes de actualizar. `docker compose down` conserva los volúmenes; **no uses `down -v`**, porque los borra.
- Para parar temporalmente: `docker compose stop gateway`. Para reanudar: `docker compose start gateway`.
- Si la clave falla, cambia únicamente `.env` en el servidor y ejecuta `docker compose up -d`; tus amigos conservan sus códigos.

La separación entre cliente y servidor sigue la [guía de autenticación de OpenAI](https://developers.openai.com/api/reference/overview). El despliegue usa [FastAPI](https://fastapi.tiangolo.com/advanced/events/) y [HTTPS automático de Caddy](https://caddyserver.com/docs/automatic-https).


## Prueba gratuita · versión 2026.09.20.4

Cada cuenta puede activar una prueba una sola vez desde Mi cuenta. Incluye 20 análisis durante 48 horas desde la activación, sin tarjeta ni cargos automáticos. Los reintentos y correcciones cuentan; una solicitud reservada puede consumir un análisis aunque el proveedor falle. Cerrar sesión o reiniciar el servidor no restablece el cupo.

Protección inicial: hasta 2 activaciones por red al día y 100 análisis gratuitos diarios para todo el servicio. Las cuentas de pago conservan sus límites existentes. Una red universitaria compartida puede alcanzar el límite de activaciones; el administrador puede aprobar acceso individualmente. No se verifica el correo: estos límites reducen el abuso pero no garantizan una prueba por persona.

El contador y la fecha de vencimiento aparecen en Mi cuenta. Al terminar, el usuario elige un plan y el administrador verifica el pago como antes. Las cuentas, pagos y pruebas se conservan en el disco persistente de Render. La guía ilustrada está en /guia.
