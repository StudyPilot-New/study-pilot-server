# Pagos manuales de Study Pilot C

## Estado de esta entrega

Incluido en la versión 2026.09.20.2. Consulta README.md para instalación y administración.
Los cobros se encuentran desactivados por defecto. Destinatario propuesto: **$Carluchad**.
No se inició ninguna transferencia, ni se comprobó que ese perfil sea elegible para recibir ventas.

## Cliente

1. Abrir `/cuenta` en el servidor y crear una cuenta con nombre, correo y contraseña.
2. Elegir **US$10 por un mes** o **US$40 por acceso permanente mientras exista el servicio**.
   Ambos conservan el límite inicial de 600 solicitudes de IA por día y los límites globales del servidor.
3. Escanear el QR o usar el enlace de Cash App. También se muestra el $Cashtag para buscarlo manualmente.
4. Verificar destinatario e importe en Cash App. El QR abre el perfil, no preautoriza ni confirma pagos.
5. Incluir la referencia de compra en la nota de la transferencia.
6. En el portal, indicar remitente y referencia de transferencia; pulsar **I paid · Send for review**.
7. El estado queda **Pending review**. Pulsar **Refresh status** después de la aprobación.
8. Con acceso activo, abrir **Mi cuenta** en la app de escritorio e iniciar sesión con el mismo correo y contraseña.

La mensualidad es de renovación manual: no hay cargos automáticos. Una renovación aprobada añade un mes
calendario a la fecha vigente, o a la fecha de aprobación si ya venció. El fin de mes se ajusta al último día
del mes siguiente. El código de sesión caduca a los 30 días: iniciar sesión de nuevo genera otro.
El portal todavía no incluye recuperación de contraseñas por correo. No se envían correos desde esta función.

## Administrador

Para la primera configuración, establecer `ADMIN_BOOTSTRAP_USER=Jorge` en el servidor, crear tu cuenta
en `/cuenta`, abrir **Owner setup** y proporcionar tu código privado existente de Jorge. La conversión
en administrador solo puede realizarse una vez. Después, retirar la variable de bootstrap.
No incluir ese código en el repositorio, enlaces ni capturas.

En **Administration → Cash App payment details**, confirmar el nombre visible y el $Cashtag.
Solo habilitar los cobros cuando la cuenta esté autorizada para recibir ventas.

En **Payments to verify**:

1. Abrir Cash App por separado y buscar la transferencia real.
2. Comprobar destinatario, remitente, estado completado e importe bruto antes de comisiones.
3. Introducir el identificador real de la transferencia y el importe recibido en USD.
4. Marcar la comprobación y pulsar **Approve verified payment**; o rechazar con una explicación.

El sistema impide reutilizar un identificador de transferencia, aprobar cuentas bloqueadas y aprobar un
importe distinto al plan. Repetir una aprobación no duplica el tiempo. El aviso del cliente no concede acceso.
La verificación es responsabilidad del administrador: no hay API de Cash App ni análisis de capturas.
Para devoluciones o disputas, resolverlas en el proveedor y bloquear el acceso si corresponde; no hay
automatización de reembolsos. **Approve free access** otorga acceso gratuito; no registra un pago.

## Despliegue

Publicar los archivos de servidor y los nuevos assets `account.html`, `account.js`, `account.css`, además de
`accounts.py`, `account_routes.py`, `plans.py`, `manual_payments.py` y `payment_routes.py`.
Instalar `requirements.txt` (incluye `qrcode==8.2`). Mantener la base SQLite en el disco persistente existente.
La migración añade tablas; mantiene los códigos y cuotas existentes. Respaldar la base antes de actualizar.
No publicar `build/preview_manual_payments.py`: usa cuentas ficticias y una base temporal.

## Pruebas

Desde la raíz: `python -m unittest discover -s servidor -p "test_*.py"`.
Demostración local: `python build/preview_manual_payments.py`, luego `http://127.0.0.1:8766/cuenta`.
Las cuentas de demostración son `student@example.com` y `owner@example.com`, contraseña `demo-password-only`.
No son cuentas reales, no llaman OpenAI y desaparecen al cerrar la demostración.
No enviar dinero durante las pruebas; las referencias usadas son ficticias.
