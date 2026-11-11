# WOTP en el VPS

Origen: https://github.com/Luckyyaduvanshiofficial/wotp, commit `94c086a`. Copia propia: https://github.com/elinares-ar/wotp. Licencia AGPL-3.0-or-later conservada. Los cambios de esta instalación se limitan al despliegue y no reemplazan la aplicación original.

Instalación en `/srv/webs/wotp`. El único puerto publicado es **127.0.0.1:8113**. El proxy enruta `/` al panel, `/gateway/` a FastAPI y `/pb/` a PocketBase. Los servicios internos no publican puertos. La red `wotp_clients` permite a la aplicación Django acceder al proxy con una clave propia sin atravesar el inicio de sesión interactivo de Google. PocketBase permanece en la red interna, con sus datos persistentes en `data/pocketbase`, propiedad del UID 10001.

## Estado de la instalación

El panel, la API, PocketBase y el proxy arrancan; los servicios con comprobación de salud están saludables. Se creó una cuenta operadora con credenciales aleatorias en `.private/operator.json` (permisos 600). El usuario está indicado en ese archivo; la contraseña nunca se imprimió ni se versionó. No hay registro público. Las credenciales del sistema y de proveedores se configuran desde `.env`, fuera de Git.

Se configuró el país por defecto en 54, código de seis dígitos y entrega simulada desactivada. **Todavía no se configuraron las credenciales de Meta o Telegram ni se enviaron códigos reales.** El panel disponible y la salud de la API no demuestran que un proveedor pueda entregar mensajes.

Arranque y actualización:

```bash
cd /srv/webs/wotp
docker compose --env-file .env -f deploy/compose.vps.yml up -d --build
```

La cuenta operadora se autentica en `/login`. `/pb/_/` es la administración de PocketBase; usa la cuenta de superusuario del `.env`, distinta del operador. El acceso de Google es una primera barrera para todo el host, sin excepciones para webhooks mientras no se configure un proveedor.

## Publicación protegida activa

Dominio solicitado: **https://wotp.ar**. Se utiliza el túnel `webs` existente y las convenciones documentadas en `/srv/webs/README.md`. Para volver a comprobar o publicar la configuración:

```bash
cd /srv/webs/wotp
python3 deploy/publicar_cloudflare.py
```

Utiliza la credencial local cifrada cuando está configurada. Como alternativa, solicita de forma oculta la frase del almacén anterior en `/root/proyectos/codex/.local/cloudflare.credentials.enc`. Reutiliza el cliente API del proyecto; no imprime credenciales. Verifica Google y copia los usuarios permitidos de la política privada existente antes de publicar la ruta del túnel y el CNAME. Conserva las otras rutas y se detiene ante conflictos. Finalmente comprueba que una petición HTTPS sin sesión termine en el inicio de sesión de Access. Si falla una operación, puede haber recursos parciales; no se borran aplicaciones ajenas. El 11 de noviembre de 2026 se publicaron y verificaron mediante API el CNAME con proxy, la ruta del túnel y la aplicación de Access con Google y política privada. Una consulta DNS pública devolvió direcciones de Cloudflare. HTTPS, con certificado validado y resolución explícita a una de esas direcciones, respondió 302 al inicio de sesión de Cloudflare Access. El resolvedor local del VPS todavía conservaba una respuesta negativa; la prueba HTTPS no dependió de esa caché. No se realizó un inicio de sesión interactivo de Google.

## Verificación

Construcción de producción completada. **159 pruebas del backend aprobadas sin red**, con el directorio de pruebas original montado en una imagen temporal. Comprobaciones del frontend: tipos, análisis estático y formato aprobados; se montó su `.gitignore` original porque el Dockerfile de producción lo excluye y los verificadores no deben recorrer dependencias ni resultados generados. Comprobados el panel, los endpoints de salud del proxy y el inicio de sesión de la cuenta operadora sin imprimir el token. Las pruebas de `deploy/test_publicar_cloudflare.py` verifican conservación de rutas y rechazo de políticas públicas sin llamar a Cloudflare.

Respaldar `data/pocketbase` con un procedimiento consistente para SQLite y guardar `.env` y `.private/` como secretos separados. El sistema de respaldo existente del VPS incluye `/srv/webs`; no se presupone una restauración probada de esta instalación nueva. Las futuras credenciales de proveedores cifradas dependen de conservar `WOTP_FERNET_KEY`.

## Cambio a wotp.ar

Las cinco URL del entorno y del ejemplo usan `https://wotp.ar`. El panel debe reconstruirse porque Next.js incorpora estas URL durante la compilación. El publicador exige la zona activa `wotp.ar` en la cuenta del túnel; mantiene la política privada existente como plantilla. La conexión interna de Mascotas continúa por `http://wotp-gateway:8080/gateway`. DNS, Access y HTTPS publicados y comprobados el 11 de noviembre de 2026 según el procedimiento descrito arriba.

## Credencial local para automatización

Para permitir la administración solicitada sin introducir la frase del almacén anterior en cada ejecución:

```bash
sudo python3 /srv/webs/wotp/deploy/credencial_cloudflare.py
```

Solicita el correo y la Global API Key con entrada oculta. Cifra los datos en `.private/cloudflare.credentials.enc` (600) y guarda la clave de cifrado en `/etc/wotp/cloudflare-local.key` (600), dentro de carpetas 700. Ambos archivos quedan fuera de Git y de los contenedores. Root puede descifrarlos: esto habilita la automatización, no protege frente a una intrusión con privilegios root. Los permisos efectivos son los de la credencial y la cuenta de Cloudflare.

El publicador utiliza esta credencial automáticamente cuando existe, sin mostrarla. Para comprobar solamente la lectura local, usar `--comprobar`; para cambiarla, `--reemplazar`. El almacén anterior permanece intacto y se puede seleccionar explícitamente con `publicar_cloudflare.py --archivo RUTA`. Eliminar la credencial local impide su uso posterior en esta instalación; revocar la Global API Key en Cloudflare también invalida sus demás copias. Respaldar la credencial cifrada y la clave por separado.

## Configuración de WhatsApp

La guía local en [META.es.md](META.es.md) detalla los campos necesarios y el configurador con entrada oculta `deploy/configurar_meta.py`. Las credenciales de Meta y la plantilla aún deben cargarse y comprobarse antes de abrir el webhook específico o activar registros.
