#!/usr/bin/env python3
"""Guarda credenciales cifradas de Cloudflare para la automatización local como root."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

from cryptography.fernet import Fernet, InvalidToken

sys.path.insert(0, '/root/proyectos/codex')
from scripts.cloudflare_vault import CloudflareCredentials, VaultError, _secret

ARCHIVO = Path('/srv/webs/wotp/.private/cloudflare.credentials.enc')
CLAVE = Path('/etc/wotp/cloudflare-local.key')


def leer_privado(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise VaultError('El archivo debe pertenecer al usuario ejecutor y tener permisos privados.')
        value = stream.read(32769)
        if len(value) > 32768:
            raise VaultError('El archivo privado supera el tamaño permitido.')
        return value


def carpeta_privada(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise VaultError('La carpeta de secretos debe pertenecer al usuario ejecutor y tener permisos 700.')


def escribir_privado(path, value, reemplazar=False):
    carpeta_privada(path.parent)
    fd, temporal = tempfile.mkstemp(prefix='.credencial-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        if reemplazar:
            os.replace(temporal, path)
        else:
            os.link(temporal, path)
    finally:
        Path(temporal).unlink(missing_ok=True)


def cargar(archivo=ARCHIVO, clave=CLAVE):
    try:
        valor = json.loads(Fernet(leer_privado(clave)).decrypt(leer_privado(archivo)))
        credencial = CloudflareCredentials(valor['email'], valor['api_key'])
        credencial.validate()
        return credencial
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise VaultError('No se pudo validar o descifrar la credencial local.') from None


def guardar(credencial, reemplazar=False, archivo=ARCHIVO, clave=CLAVE):
    credencial.validate()
    if os.path.lexists(archivo) and not reemplazar:
        raise VaultError('Ya existe una credencial. Usá --reemplazar para actualizarla.')
    if not os.path.lexists(clave):
        if os.path.lexists(archivo):
            raise VaultError('Falta la clave de una credencial existente; no se genera otra automáticamente.')
        escribir_privado(clave, Fernet.generate_key())
    cifrador = Fernet(leer_privado(clave))
    contenido = json.dumps({'email': credencial.email, 'api_key': credencial.api_key}).encode()
    escribir_privado(archivo, cifrador.encrypt(contenido), reemplazar)
    cargar(archivo, clave)


class ArgumentosEspanol(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage().replace('usage:', 'Uso:')

    def format_help(self):
        return super().format_help().replace('usage:', 'Uso:')

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, 'Error: argumentos no válidos; consultá --ayuda.\n')


def main():
    parser = ArgumentosEspanol(description=__doc__, add_help=False, usage='%(prog)s [--ayuda] [--reemplazar] [--comprobar]')
    parser._optionals.title = 'Opciones'
    parser.add_argument('--ayuda', '-h', action='help', help='Mostrar esta ayuda.')
    parser.add_argument('--reemplazar', action='store_true', help='Actualizar la credencial existente.')
    parser.add_argument('--comprobar', action='store_true', help='Comprobar el descifrado local sin contactar a Cloudflare.')
    args = parser.parse_args()
    try:
        if os.geteuid() != 0:
            raise VaultError('Ejecutá este script con sudo o como root.')
        if args.comprobar:
            cargar()
            print('Credencial local comprobada. No se mostraron secretos ni se contactó a Cloudflare.')
        else:
            credencial = CloudflareCredentials(_secret('Correo asociado a Cloudflare (entrada oculta): ').strip(), _secret('Global API Key (entrada oculta): ').strip())
            guardar(credencial, args.reemplazar)
            print('Credenciales cifradas guardadas con permisos privados. La clave de cifrado queda en /etc/wotp, separada del proyecto.')
            print('La automatización local como root ya puede utilizarlas sin frase de paso. No se verificaron todavía los permisos en Cloudflare.')
        return 0
    except (VaultError, OSError, ValueError):
        print('No se pudo guardar o comprobar la credencial. Revisá permisos, datos y si necesitás --reemplazar. No se muestran secretos.', file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print('Operación cancelada sin mostrar credenciales.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
