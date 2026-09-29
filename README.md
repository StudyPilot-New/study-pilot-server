# Study Pilot C · 2026.09.28.11

Servicio: https://study-pilot-server.onrender.com

## Actualización 2026.09.28.11

Corrige tres causas de pausa: Canvas conserva preguntas visibles repetidas sin ID y reconoce más contenedores de opciones, incluidos los que anidan la pregunta y las respuestas; Reading vuelve a la actividad aunque el libro abra en un dominio externo, en una ventana nueva o en un marco que mantenga la URL. Cuando Canvas no expone controles tras varios segundos, la app libera una posible interacción retenida y muestra un estado claro mientras continúa revisando la página.

El instalador conserva la cuenta y los ajustes existentes. La verificación utiliza páginas locales de prueba; no sustituye una prueba de toda la sesión en Canvas o McGraw Hill.

## Actualización 2026.09.27.10

Canvas utiliza un flujo específico para aplicar respuestas en etiquetas visibles y controles personalizados. Evita contar dos veces la misma opción y conserva la identidad de la pregunta cuando Canvas reconstruye sus controles. Comprueba que la selección se mantiene antes de pulsar Next; los reintentos conservan el análisis y no quedan detenidos indefinidamente tras agotar los primeros intentos. El envío final del cuestionario sigue siendo manual.

Los reintentos atienden por turnos las preguntas pendientes. Una respuesta vacía o de confianza insuficiente solicita revisión automática. El panel permite que los clics alcancen los controles durante la aplicación sin ocultarse ni provocar parpadeos.

Las pruebas incluyen varias preguntas consecutivas, controles ocultos con etiquetas visibles, opciones personalizadas, reemplazo del formulario y Next retrasado. No certifican todas las variantes de Canvas ni una sesión real completa.

## Actualización 2026.09.27.9

Corrige casos de arrastre con respuesta lenta, piezas flotantes y listas dentro de marcos con desplazamiento. Las copias visuales del arrastre no cuentan como opciones nuevas. Reading conserva la referencia a la actividad cuando abre una ventana o cambia un marco; el regreso espera a que termine la transición.

La recuperación comienza soltando el arrastre y detectando de nuevo los controles, antes de recurrir a recargas limitadas. Las operaciones bloqueadas se cancelan antes del siguiente intento. Se conserva el análisis y la memoria de errores de la sesión. El diagnóstico local se guarda en la carpeta de datos del usuario. Estos casos se verifican con pruebas aisladas del navegador; aún no se ha reproducido la pantalla negra del equipo del usuario ni validado una sesión universitaria completa.

Para actualizar cualquier instalación anterior, cierra Study Pilot C, descarga de nuevo `/download` y ejecuta el instalador. El acceso directo apunta a la nueva versión; la cuenta, los ajustes y el perfil se conservan. Las versiones ya abiertas no se actualizan desde el servidor.

## Empezar

1. Crea una cuenta en `/cuenta`. El registro por sí solo no activa el consumo de IA.
2. El administrador aprueba tu acceso o verifica el pago manual.
3. Descarga el instalador para Windows en `/download`. Incluye Python y crea un acceso directo; requiere Google Chrome.
4. Abre **Mi cuenta** en la app e inicia sesión con el mismo correo y contraseña.
5. Pega tu enlace de Canvas o plataforma en Inicio rápido, pulsa **Abrir actividad** e inicia sesión con tu universidad en el nuevo Chrome.

Elige segundos por pregunta o duración estimada. El ritmo se actualiza en vivo y conserva el progreso. El análisis y los reintentos pueden alargar la sesión.

## Administración

Los códigos anteriores siguen funcionando. Para crear el primer administrador, configura `ADMIN_BOOTSTRAP_USER=Jorge` en Render. Jorge registra su cuenta y completa **Owner setup** con su código privado anterior. Este proceso solo permite crear el primer administrador. No publiques el código.

Los pagos Cash App están desactivados inicialmente. El propietario debe comprobar que puede recibir pagos comerciales, revisar destinatario y habilitarlos desde Administración. Un reporte de pago nunca activa acceso sin verificación manual. Plan mensual: US$10 por mes calendario, renovación manual. US$40: acceso mientras exista el servicio, con límite de uso.

Mantén el disco persistente `/var/data`, una instancia y un worker. La API key permanece únicamente en Render. Las cuentas tienen límites individuales; se conservan los límites globales del servicio. No se han implementado recuperación de contraseña por email ni verificación de correo.

## Compatibilidad

McGraw Hill tiene un adaptador específico. Canvas, Moodle, Blackboard, Pearson y Cengage disponen de detección experimental de controles estándar. Las pruebas usan páginas representativas, no certifican todas las variantes reales. El avance automático y los arrastres personalizados fuera de McGraw pueden requerir intervención.

## Publicación

`assemble_client.py` une `client.partNN`, verifica SHA256 y crea el instalador indicado en `client-manifest.json`. Sube todas las partes antes de ejecutar Manual Deploy. El despliegue automático está desactivado. No subas `.env`, bases de datos, perfiles de Chrome ni archivos de acceso personales.

Una compilación y las pruebas automatizadas no garantizan una sesión real completa sin errores. El instalador no tiene firma digital de editor y Windows puede mostrar una advertencia de reputación.

Corrección 2026.09.20.4: el estado del inicio de sesión se muestra encima de los campos. Una cuenta activa abre la pestaña Actividad; errores y accesos pendientes permanecen visibles.
