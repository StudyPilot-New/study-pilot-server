# Study Pilot C · 2026.09.25.8

Servicio: https://study-pilot-server.onrender.com

## Actualización 2026.09.25.8

Corrige la recuperación de arrastrar y soltar: comprueba la identidad actual de cada pieza, verifica que se soltó y limita los intentos por gesto. Conserva el análisis entre reintentos y evita capturas y recargas repetidas. El diagnóstico local se guarda en la carpeta de datos del usuario.

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
