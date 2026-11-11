#!/usr/bin/env python3
"""Carga las credenciales de Meta en el entorno privado, sin enviar mensajes."""
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import tempfile

sys.path.insert(0, '/root/proyectos/codex')
from scripts.cloudflare_vault import VaultError, _secret

ENTORNO = Path('/srv/webs/wotp/.env')
PATRONES = {
    'META_PHONE_NUMBER_ID': r'[0-9]{5,40}',
    'META_WABA_ID': r'[0-9]{5,40}',
    'META_ACCESS_TOKEN': r'[A-Za-z0-9._|~+-]{20,4096}',
    'META_APP_SECRET': r'[a-fA-F0-9]{32}',
    'META_TEMPLATE': r'[a-z0-9_]{1,512}',
    'META_TEMPLATE_LANG': r'[a-z]{2,3}(?:_[A-Z]{2})?',
    'META_GRAPH_VERSION': r'v[0-9]{1,3}\.0',
}


def preparar(texto, valores):
    if set(valores) != set(PATRONES):
        raise VaultError('Faltan campos de la configuración de Meta.')
    for campo, patron in PATRONES.items():
        if not re.fullmatch(patron, valores[campo]):
            raise VaultError('Formato no válido en '+campo+'.')
    lineas = texto.splitlines()
    previos = [l.split('=', 1)[1] for l in lineas if l.startswith('META_VERIFY_TOKEN=')]
    if len(previos)>1:
        raise VaultError('Existe más de un token de verificación; revisá el entorno.')
    token = previos[0] if previos and previos[0] else secrets.token_urlsafe(32)
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,256}', token):
        raise VaultError('El token de verificación existente necesita revisión manual; no se reemplazó.')
    nuevos = dict(valores, META_VERIFY_TOKEN=token, WHATSAPP_PROVIDER='meta', WOTP_MOCK_DELIVERY='0')
    patron = re.compile(r'^\s*(?:export\s+)?('+'|'.join(nuevos)+r')\s*=')
    conservadas = [l for l in lineas if not patron.match(l)]
    return '\n'.join(conservadas)+'\n'+'\n'.join(k+'='+v for k,v in nuevos.items())+'\n'


def guardar(valores, archivo=ENTORNO):
    with os.fdopen(os.open(archivo, os.O_RDONLY | os.O_NOFOLLOW), 'r') as entrada:
        info=os.fstat(entrada.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise VaultError('El entorno debe ser privado y pertenecer al usuario ejecutor.')
        anterior=entrada.read()
    nuevo=preparar(anterior, valores)
    fd, temporal=tempfile.mkstemp(prefix='.meta-', dir=archivo.parent)
    try:
        with os.fdopen(fd,'w') as salida:
            salida.write(nuevo)
            salida.flush()
            os.fsync(salida.fileno())
        if archivo.is_symlink() or archivo.read_text()!=anterior:
            raise VaultError('El entorno cambió durante la configuración; no se reemplazó.')
        os.replace(temporal,archivo)
    finally:
        Path(temporal).unlink(missing_ok=True)


def main():
    try:
        if os.geteuid()!=0:
            raise VaultError('Ejecutá el script con sudo o como root.')
        etiquetas={
            'META_PHONE_NUMBER_ID':'Identificador del número de WhatsApp (Phone Number ID)',
            'META_WABA_ID':'Identificador de la cuenta de WhatsApp Business (WABA ID)',
            'META_ACCESS_TOKEN':'Token de acceso de usuario del sistema de Meta',
            'META_APP_SECRET':'Secreto de la aplicación de Meta (App Secret)',
            'META_TEMPLATE':'Nombre técnico de la plantilla de autenticación aprobada',
            'META_TEMPLATE_LANG':'Código de idioma exacto de la plantilla, por ejemplo es o es_AR',
            'META_GRAPH_VERSION':'Versión Graph API indicada en tu aplicación, por ejemplo v21.0',
        }
        valores={k:_secret(etiquetas[k]+' (entrada oculta): ').strip() for k in PATRONES}
        guardar(valores)
        print('Configuración de Meta guardada en el entorno privado con permisos 600. No se mostraron secretos.')
        print('Todavía no se reiniciaron servicios, no se validaron credenciales en Meta y no se enviaron mensajes.')
        print('Avisá que terminaste para comprobar la configuración y preparar el webhook antes de activar el registro.')
        return 0
    except VaultError as error:
        print('Error: '+str(error),file=sys.stderr)
        return 2
    except OSError:
        print('No se pudo guardar la configuración. Revisá la instalación y los permisos; no se muestran secretos.',file=sys.stderr)
        return 2
    except (KeyboardInterrupt,EOFError):
        print('Operación cancelada sin mostrar credenciales.',file=sys.stderr)
        return 130


if __name__=='__main__':
    raise SystemExit(main())
