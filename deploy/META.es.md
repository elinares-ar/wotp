# Conectar Meta con esta instalación

Estado: WOTP publicado en https://wotp.ar y protegido por Google Access. El proveedor de WhatsApp sigue sin configurar y las altas de Mascotas permanecen pausadas.

## Datos necesarios

En la aplicación de Meta asociada al negocio, habilitar WhatsApp Cloud API y obtener:

- Identificador del número emisor (Phone Number ID), distinto del número telefónico.
- Identificador de la cuenta de WhatsApp Business (WABA ID).
- Token de acceso del usuario del sistema con acceso a los activos del negocio. Revisar los permisos `whatsapp_business_messaging` para mensajería y `whatsapp_business_management` para consultar y administrar los activos y plantillas. Revisar la caducidad elegida en Meta.
- Secreto de la aplicación (App Secret).
- Nombre técnico e idioma exactos de una plantilla aprobada de categoría autenticación, con botón para copiar el código. La implementación envía el mismo código en el cuerpo y en el botón.
- Versión Graph API disponible en la aplicación. El configurador no elige una versión automáticamente.

Si todavía no existen la aplicación y el número, comenzar en https://developers.facebook.com/apps/ y seguir la configuración de WhatsApp del negocio. Los nombres de los menús pueden cambiar. Antes de modificar un número que ya se usa, comprobar en Meta su modalidad de incorporación; no eliminar cuentas existentes como paso automático. Un número de prueba y sus destinatarios autorizados sirven para preparación, pero no demuestran que el servicio admita registros del público.

Referencias oficiales:

- https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started/
- https://developers.facebook.com/documentation/business-messaging/whatsapp/access-tokens
- https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api

Las páginas de Meta devolvieron HTTP 429 durante la consulta del 11 de noviembre de 2026. No se verificaron sus pantallas actuales ni se eligió una versión nueva de Graph API por suposición. La lista anterior corresponde a los campos que requiere el código de esta instalación.

## Cargar los datos

```bash
sudo python3 /srv/webs/wotp/deploy/configurar_meta.py
```

Todos los campos se solicitan con entrada oculta. Se conserva el resto del `.env`, se reemplazan las variables correspondientes y se genera un token aleatorio para el webhook si no existe. El entorno permanece con permisos 600. Este script no contacta a Meta, no reinicia servicios, no abre rutas públicas y no envía mensajes. La sintaxis válida no demuestra que Meta haya autorizado las credenciales o la plantilla.

## Siguientes pasos al terminar la carga

1. Comprobar el acceso al número, la cuenta y la plantilla con consultas de lectura a Meta, sin imprimir credenciales.
2. Aplicar la configuración del servicio y comprobar que el webhook rechaza firmas inválidas y que el token de verificación coincide.
3. Configurar una excepción específica de Access para `https://wotp.ar/gateway/webhooks/whatsapp`, manteniendo el panel y el resto de la API detrás de Google. Meta no puede completar un inicio de sesión interactivo; sus notificaciones POST deben seguir autenticadas por la firma HMAC de la aplicación. Esta excepción todavía no está creada.
4. Dar de alta esa URL en Meta y suscribir el campo `messages`. Copiar el token de verificación desde el entorno privado, sin publicarlo en chat, registros ni capturas.
5. Comprobar todo el recorrido antes de habilitar altas públicas. Los envíos reales de prueba se hacen desde el navegador por el propietario; los tests automáticos no envían mensajes.

Solo después corresponde activar la verificación en Mascotas con el procedimiento existente de `scripts/activate_whatsapp.py`. Un estado de salud que indica credenciales presentes no prueba que Meta entregue el mensaje.
