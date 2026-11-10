import os
from pathlib import Path
import tempfile
import unittest

from cryptography.fernet import Fernet
from credencial_cloudflare import CloudflareCredentials, VaultError, cargar, guardar


class CredencialLocalTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        base = Path(self.temporal.name)
        self.archivo = base / 'datos' / 'credencial.enc'
        self.clave = base / 'clave' / 'local.key'
        self.credencial = CloudflareCredentials('prueba@example.invalid', 'credencial-ficticia-sin-acceso-externo')

    def guardar(self, reemplazar=False):
        guardar(self.credencial, reemplazar, self.archivo, self.clave)

    def test_cifra_y_recupera_con_permisos_privados(self):
        self.guardar()
        self.assertEqual(cargar(self.archivo, self.clave), self.credencial)
        self.assertNotIn(self.credencial.api_key.encode(), self.archivo.read_bytes())
        for path in [self.archivo, self.clave]:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_reemplazo_explicito_conserva_clave(self):
        self.guardar()
        clave = self.clave.read_bytes()
        with self.assertRaises(VaultError):
            self.guardar()
        self.guardar(True)
        self.assertEqual(self.clave.read_bytes(), clave)
        self.assertEqual(cargar(self.archivo, self.clave), self.credencial)

    def test_no_regenera_clave_perdida(self):
        self.guardar()
        self.clave.unlink()
        with self.assertRaises(VaultError):
            self.guardar(True)
        self.assertFalse(self.clave.exists())

    def test_rechaza_archivos_publicos_alterados_y_clave_distinta(self):
        self.guardar()
        self.archivo.chmod(0o644)
        with self.assertRaises(VaultError):
            cargar(self.archivo, self.clave)
        self.archivo.chmod(0o600)
        self.clave.write_bytes(Fernet.generate_key())
        with self.assertRaises(VaultError):
            cargar(self.archivo, self.clave)

    def test_rechaza_enlaces_simbolicos(self):
        self.guardar()
        enlace = self.archivo.parent / 'enlace'
        enlace.symlink_to(self.archivo)
        with self.assertRaises(OSError):
            cargar(enlace, self.clave)

    def test_rechaza_directorio_publico(self):
        self.clave.parent.mkdir(mode=0o755)
        with self.assertRaises(VaultError):
            self.guardar()
