from pathlib import Path
import tempfile
import unittest

from configurar_meta import VaultError, guardar, preparar


class ConfiguracionMetaTests(unittest.TestCase):
    def setUp(self):
        self.valores={
            'META_PHONE_NUMBER_ID':'100000', 'META_WABA_ID':'200000',
            'META_ACCESS_TOKEN':'token-ficticio-para-prueba-sin-acceso',
            'META_APP_SECRET':'0'*32, 'META_TEMPLATE':'codigo_prueba',
            'META_TEMPLATE_LANG':'es', 'META_GRAPH_VERSION':'v21.0',
        }

    def test_conserva_otros_secretos_y_elimina_duplicados(self):
        anterior='SECRET_KEY=valor-local\nMETA_TEMPLATE=vieja\nexport META_TEMPLATE=otra\n'
        nuevo=preparar(anterior,self.valores)
        self.assertIn('SECRET_KEY=valor-local\n',nuevo)
        self.assertEqual(nuevo.count('META_TEMPLATE='),1)
        self.assertIn('WOTP_MOCK_DELIVERY=0\n',nuevo)

    def test_conserva_token_de_webhook(self):
        token='valor-ficticio-de-verificacion'
        nuevo=preparar('META_VERIFY_TOKEN='+token+'\n',self.valores)
        self.assertIn('META_VERIFY_TOKEN='+token+'\n',nuevo)

    def test_rechaza_inyecciones_y_campos_incompletos(self):
        for valor in ['plantilla\nOTRA=1','plantilla$VARIABLE','plantilla#comentario']:
            with self.assertRaises(VaultError):
                preparar('',dict(self.valores,META_TEMPLATE=valor))
        with self.assertRaises(VaultError): preparar('',{})

    def test_no_cambia_token_ambiguo(self):
        with self.assertRaises(VaultError):
            preparar('META_VERIFY_TOKEN=uno\nMETA_VERIFY_TOKEN=dos\n',self.valores)

    def test_guardado_privado_y_no_sigue_enlaces(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo=Path(directorio)/'.env'
            archivo.write_text('APP_ENV=production\n')
            archivo.chmod(0o600)
            guardar(self.valores,archivo)
            self.assertEqual(archivo.stat().st_mode & 0o777,0o600)
            self.assertIn('APP_ENV=production',archivo.read_text())
            enlace=Path(directorio)/'enlace'
            enlace.symlink_to(archivo)
            with self.assertRaises(OSError): guardar(self.valores,enlace)
            archivo.chmod(0o644)
            with self.assertRaises(VaultError): guardar(self.valores,archivo)
