# Desplegar Study Pilot C en Render

Estado: configuración preparada; todavía no hay una web pública desplegada. No se incluye ninguna clave. El navegador de cada usuario permanece en su laptop; el servidor centraliza la API y muestra la guía de acceso.

## Coste previsto

Configuración inicial: servicio `0.5c-512mb` de US$7/mes y disco persistente de 1 GB a US$0,25/mes. Aproximadamente US$7,25/mes, más OpenAI, impuestos y cualquier excedente. Usa un workspace Hobby si sus límites te bastan. Confirma el total que muestra Render antes de crear el servicio. El disco es necesario para conservar códigos, revocaciones y contadores; no sustituyas el servicio por el gratuito con almacenamiento efímero.

Fuentes consultadas el 20-09-2026: [precios](https://render.com/pricing), [discos](https://render.com/docs/disks), [Blueprints](https://render.com/docs/blueprint-spec).

## 1. GitHub

1. Crea un repositorio **privado** vacío llamado `study-pilot-server`.
2. Sube el **contenido de la carpeta preparada para despliegue**, de forma que `render.yaml`, `gateway.py`, `.python-version` y `requirements.txt` estén en la raíz del repositorio.
3. No subas tu instalación personal, `.env`, claves, códigos, bases de datos ni perfiles de Chrome.

El ZIP de despliegue contiene solo los archivos del servidor y guías; el ZIP no se sube como archivo único a GitHub: primero hay que extraerlo y subir su contenido.

## 2. Render

1. Entra en [Render](https://dashboard.render.com/) y crea la cuenta con GitHub si todavía no tienes una.
2. Selecciona **New → Blueprint** y conecta únicamente el repositorio `study-pilot-server`.
3. Selecciona `render.yaml` en la raíz. El formulario debe proponer un servicio web pequeño y un disco de 1 GB, una instancia y región Virginia.
4. En el campo secreto **OPENAI_API_KEY**, pega tu clave **directamente en Render**. No la pegues en este chat ni en GitHub. Comprueba que el modelo configurado esté disponible para tu proyecto.
5. Revisa el precio y pulsa Deploy cuando estés de acuerdo. Si Render solicita tarjeta, introdúcela tú en su formulario.
6. Espera a que el servicio muestre **Live**. Abre su dirección `https://…onrender.com`; debe aparecer la página de Study Pilot C.
7. Abre también `https://…onrender.com/health`. Debe mostrar `service: study-pilot-c` y `status: ok`. Esto confirma el servidor, no todavía una respuesta real de OpenAI.

No necesitas comprar un dominio ni instalar Caddy en Render. La plantilla usa el runtime Python y HTTPS del proveedor. `.python-version` fija Python 3.13 con el parche disponible; [documentación oficial](https://render.com/docs/python-version).

## 3. Crear el primer acceso

En el servicio de Render, abre **Shell** y ejecuta:

```sh
python manage_access.py add Prueba --limit 30
```

Guarda en privado el código `spc_` mostrado una sola vez. No compartas una captura que lo incluya. No se usa una API key diferente para cada persona: todos usan tu servidor mediante códigos distintos.

En tu app **de escritorio compartida**, abre Guía de inicio, introduce la URL pública y ese código y pulsa Activar acceso. Prueba una pregunta. La activación no llama a OpenAI; el análisis sí consume API.

En Shell, comprueba:

```sh
python manage_access.py list
```

Debe subir el uso de Prueba. Reinicia el servicio una vez y confirma que ese código continúa activo; esto verifica el disco persistente.

## 4. Dar acceso a amigos

```sh
python manage_access.py add Ana --limit 600
python manage_access.py add Bea --limit 600
```

Cada persona recibe el ZIP **Escritorio-Compartido**, la URL y su propio código. En su laptop solo debe extraer el ZIP, abrir el ejecutable y seguir la guía. Necesita Chrome y su cuenta universitaria.

Para retirar un acceso:

```sh
python manage_access.py revoke Ana
```

## 5. Descargar desde la web

La carpeta preparada para GitHub incluye el cliente compartido dividido en `client.part01`, `client.part02` y `client.part03`, con `client-manifest.json`. Sube también estos cuatro archivos. Durante el build, `assemble_client.py` reconstruye el ZIP y comprueba su SHA256. El portal muestra el botón Descargar para Windows automáticamente cuando existe el paquete verificado. Ninguno de estos archivos contiene tu clave o códigos personales.

El portal admite la variable opcional `DOWNLOAD_URL`. Cuando alojes el ZIP compartido en una dirección HTTPS accesible para tus amigos, añade esa URL en **Environment** y vuelve a desplegar. Aparecerá el botón Descargar para Windows.

Si despliegas sin las partes del cliente ni un enlace de descarga, el portal indica que el administrador entrega el ZIP. Un enlace a un repositorio privado de GitHub no permite descargar a personas sin acceso. Cuando incluyas las partes verificadas, el servidor publicará ese ZIP; el repositorio puede seguir siendo privado.

## 6. Actualizaciones y límites

Las actualizaciones automáticas están desactivadas para que una subida de código no interrumpa una actividad. Después de probar los cambios, usa **Manual Deploy → Deploy latest commit** fuera de las sesiones. Mantén **una instancia y un worker**: el control de concurrencia de esta versión es local al proceso.

El límite predeterminado es 3000 solicitudes al día entre todos los usuarios y cuatro análisis concurrentes. Cada código tiene su propio límite. Son límites de solicitudes, no un presupuesto exacto. Mayor precisión puede consumir más tokens por consulta.

No borres el disco al actualizar. Si aparece un error, comparte solo el mensaje sin claves ni códigos. Falta verificar el despliegue público y una sesión real en otra laptop antes de ampliar la distribución.
