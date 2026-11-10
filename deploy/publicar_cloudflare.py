#!/usr/bin/env python3
"""Publica únicamente WOTP después de verificar Cloudflare Access con Google."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener

# Reutiliza el lector del almacén cifrado que el propietario ya configuró.
# No copia, imprime ni persiste el texto descifrado.
sys.path.insert(0, "/root/proyectos/codex")
from scripts.cloudflare_dns import CloudflareAPI, DNSError, NoRedirect
from scripts.cloudflare_vault import DEFAULT_PATH, VaultError, _secret, load_credentials

DOMINIO = "wotp.pruebas-ia.org"
ZONA = "pruebas-ia.org"
TUNEL = "671cae54-9c0f-4f88-a9c8-5d227760214e"
ORIGEN = "http://localhost:8113"
NOMBRE = "WOTP - Solo Emilio (Google)"


def todos(valor):
    if isinstance(valor, dict):
        return "everyone" in valor or any(todos(v) for v in valor.values())
    return isinstance(valor, list) and any(todos(v) for v in valor)


def politica_segura(politicas):
    if any(p.get("decision") not in {"allow", "deny"} for p in politicas):
        raise DNSError("La aplicación tiene una excepción incompatible con el acceso exclusivo por Google.")
    permitidas = [p for p in politicas if p.get("decision") == "allow"]
    if not permitidas or any(not p.get("include") or todos(p["include"]) for p in permitidas):
        raise DNSError("No se encontró una política con una lista de acceso restringida.")
    return sorted(politicas, key=lambda p: p.get("precedence") or 1)


def nueva_configuracion(configuracion):
    copia = deepcopy(configuracion)
    reglas = copia.get("ingress")
    if not isinstance(reglas, list) or not reglas or reglas[-1].get("hostname"):
        raise DNSError("El túnel no tiene una regla final reconocible; no se modificó.")
    existentes = [r for r in reglas if r.get("hostname") == DOMINIO]
    if existentes:
        if len(existentes) != 1 or existentes[0].get("service") != ORIGEN or existentes[0].get("path"):
            raise DNSError("El subdominio ya tiene una ruta diferente; no se reemplazó.")
    else:
        reglas.insert(len(reglas) - 1, {"hostname": DOMINIO, "service": ORIGEN, "originRequest": {}})
    return copia


def publicar(api):
    zonas = api.listing("/zones", name=ZONA)
    if len(zonas) != 1 or zonas[0].get("status") != "active":
        raise DNSError("No se encontró una única zona activa para el subdominio propuesto.")
    zona = zonas[0]["id"]
    cuenta = zonas[0]["account"]["id"]
    base = f"/accounts/{cuenta}"
    apps = api.listing(base + "/access/apps")
    proveedores = api.listing(base + "/access/identity_providers")
    google = [p["id"] for p in proveedores if p.get("type") in {"google", "google-apps"}]
    if len(google) != 1:
        raise DNSError("Se necesita identificar un único proveedor Google de Access; no se publicó la ruta.")
    idp = google[0]
    concretas = [a for a in apps if a.get("domain", "").split("/")[0] == DOMINIO]
    if concretas and (len(concretas) != 1 or concretas[0].get("domain") != DOMINIO or concretas[0].get("name") != NOMBRE):
        raise DNSError("Existe una aplicación específica distinta para WOTP; no se modificó.")
    if concretas:
        app = concretas[0]
    else:
        plantillas = [a for a in apps if a.get("domain") == "war.petshopnoa.net.ar"]
        if len(plantillas) != 1:
            plantillas = [a for a in apps if a.get("domain") == "*." + ZONA]
        if len(plantillas) != 1:
            raise DNSError("No se pudo identificar la política privada existente para copiar sus usuarios autorizados.")
        originales = api.listing(base + f"/access/apps/{plantillas[0]['id']}/policies")
        restringidas = politica_segura(originales)
        # Crear Access primero: hasta completar las políticas no se publica DNS.
        app = api.request("POST", base + "/access/apps", {
            "name": NOMBRE, "domain": DOMINIO, "type": "self_hosted",
            "session_duration": "24h", "allowed_idps": [idp],
            "auto_redirect_to_identity": True, "app_launcher_visible": False,
        })["result"]
        for numero, original in enumerate(restringidas, 1):
            politica = {k: deepcopy(original[k]) for k in ("decision", "include", "exclude", "require") if k in original}
            politica.update(name="Acceso privado WOTP " + str(numero), precedence=numero)
            api.request("POST", base + f"/access/apps/{app['id']}/policies", politica)
    app = api.request("GET", base + f"/access/apps/{app['id']}")["result"]
    if app.get("allowed_idps") != [idp] or app.get("type") != "self_hosted":
        raise DNSError("La aplicación no limita el inicio de sesión a Google; no se publicó la ruta.")
    politica_segura(api.listing(base + f"/access/apps/{app['id']}/policies"))
    print("Access verificado: Google y política privada, sin excepciones públicas.", flush=True)

    dns = f"/zones/{zona}/dns_records"
    registros = api.listing(dns, name=DOMINIO)
    destino = TUNEL + ".cfargotunnel.com"
    if registros and (len(registros) != 1 or registros[0].get("type") != "CNAME" or registros[0].get("content", "").rstrip(".") != destino or not registros[0].get("proxied")):
        raise DNSError("El nombre ya tiene DNS diferente; no se reemplazó.")
    ruta = base + f"/cfd_tunnel/{TUNEL}/configurations"
    anterior = api.request("GET", ruta)["result"]["config"]
    nueva = nueva_configuracion(anterior)
    if nueva != anterior:
        if api.request("GET", ruta)["result"]["config"] != anterior:
            raise DNSError("El túnel cambió durante la operación; repetí para conservar las rutas nuevas.")
        api.request("PUT", ruta, {"config": nueva})
    if not registros:
        api.request("POST", dns, {"type": "CNAME", "name": DOMINIO, "content": destino, "proxied": True, "ttl": 1})
    if api.request("GET", ruta)["result"]["config"] != nueva:
        raise DNSError("El túnel no coincide con la configuración enviada; revisá su estado.")
    print("Ruta del túnel y DNS publicados sin reemplazar los otros sitios.", flush=True)


def verificar_puerta():
    try:
        with build_opener(NoRedirect()).open(Request("https://" + DOMINIO), timeout=20) as respuesta:
            estado, destino = respuesta.status, respuesta.headers.get("Location", "")
    except HTTPError as error:
        estado, destino = error.code, error.headers.get("Location", "")
    except (URLError, OSError):
        raise DNSError("La API confirmó la publicación, pero HTTPS aún no se pudo comprobar. Puede faltar propagación; no se afirma acceso verificado.") from None
    url = urlparse(destino)
    if estado not in {302, 303, 307} or not ((url.hostname or "").endswith(".cloudflareaccess.com") or "/cdn-cgi/access/login" in url.path):
        raise DNSError("No se recibió el inicio de sesión esperado de Access. Revisá la protección antes de usar la instalación.")
    print("HTTPS verificado: sin sesión se exige iniciar sesión en Cloudflare Access.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser._optionals.title = "Opciones"
    parser.add_argument("--ayuda", "-h", "--help", action="help", help="Mostrar esta ayuda y salir.")
    parser.add_argument("--archivo", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    try:
        credenciales = load_credentials(args.archivo, _secret("Frase de paso del almacén de Cloudflare (entrada oculta): "))
        publicar(CloudflareAPI(credenciales))
        verificar_puerta()
        print("Publicado: https://" + DOMINIO)
        return 0
    except (DNSError, VaultError) as error:
        print("Error: " + str(error), file=sys.stderr)
        print("La operación puede haber creado recursos parciales. Revisá el estado antes de reintentar; no se borran otras aplicaciones ni rutas.", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, KeyboardInterrupt, EOFError):
        print("No se pudo completar la publicación. No se muestran credenciales; revisá instalación y conectividad.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
