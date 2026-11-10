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

La cuenta operadora se autentica en `/login`. `/pb/_/` es la administración de PocketBase; usa la cuenta de superusuario del `.env`, distinta del operador. El acceso de Google será una primera barrera para todo el host, sin excepciones para webhooks mientras no se configure un proveedor.

## Publicación protegida pendiente de desbloquear la credencial

Destino propuesto: **https://wotp.pruebas-ia.org**. Se utiliza el túnel `webs` existente y las convenciones documentadas en `/srv/webs/README.md`. Para publicar, ejecutar en una terminal normal:

```bash
cd /srv/webs/wotp
python3 deploy/publicar_cloudflare.py
```

Solicita de forma oculta la frase del almacén cifrado existente en `/root/proyectos/codex/.local/cloudflare.credentials.enc`. Reutiliza el lector y cliente API de ese proyecto; no copia el secreto descifrado. Verifica Google y copia los usuarios permitidos de la política privada existente antes de publicar la ruta del túnel y el CNAME. Conserva las otras rutas y se detiene ante conflictos. Finalmente comprueba que una petición HTTPS sin sesión termine en el inicio de sesión de Access. Si falla una operación, puede haber recursos parciales; no se borran aplicaciones ajenas. La política de acceso y HTTPS públicos todavía no se afirman comprobados hasta ejecutar este paso.

## Verificación

Construcción de producción completada. **159 pruebas del backend aprobadas sin red**, con el directorio de pruebas original montado en una imagen temporal. Comprobaciones del frontend: tipos, análisis estático y formato aprobados; se montó su `.gitignore` original porque el Dockerfile de producción lo excluye y los verificadores no deben recorrer dependencias ni resultados generados. Comprobados el panel, los endpoints de salud del proxy y el inicio de sesión de la cuenta operadora sin imprimir el token. Las pruebas de `deploy/test_publicar_cloudflare.py` verifican conservación de rutas y rechazo de políticas públicas sin llamar a Cloudflare.

Respaldar `data/pocketbase` con un procedimiento consistente para SQLite y guardar `.env` y `.private/` como secretos separados. El sistema de respaldo existente del VPS incluye `/srv/webs`; no se presupone una restauración probada de esta instalación nueva. Las futuras credenciales de proveedores cifradas dependen de conservar `WOTP_FERNET_KEY`.
