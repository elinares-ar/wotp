import unittest

from publicar_cloudflare import DOMINIO, DNSError, ORIGEN, nueva_configuracion, politica_segura


class PublicacionProtegidaTests(unittest.TestCase):
    def test_conserva_rutas_y_opciones_del_tunel(self):
        original = {"ingress": [{"hostname": "otro.example.invalid", "service": "http://localhost:9000"}, {"service": "http_status:404"}], "originRequest": {"connectTimeout": 20}}
        nueva = nueva_configuracion(original)
        self.assertEqual(len(original["ingress"]), 2)
        self.assertEqual(nueva["ingress"][0], original["ingress"][0])
        self.assertEqual(nueva["ingress"][-1], original["ingress"][-1])
        self.assertEqual(nueva["originRequest"], original["originRequest"])
        self.assertEqual(nueva["ingress"][1]["hostname"], DOMINIO)
        self.assertEqual(nueva["ingress"][1]["service"], ORIGEN)

    def test_ruta_correcta_no_se_duplica_y_ruta_distinta_no_se_reemplaza(self):
        original = {"ingress": [{"hostname": DOMINIO, "service": ORIGEN}, {"service": "http_status:404"}]}
        self.assertEqual(nueva_configuracion(original), original)
        original["ingress"][0]["service"] = "http://localhost:9999"
        with self.assertRaises(DNSError):
            nueva_configuracion(original)

    def test_rechaza_acceso_publico_y_excepciones(self):
        for politica in [[], [{"decision": "allow", "include": [{"everyone": {}}]}], [{"decision": "allow", "include": [{"any": [{"everyone": {}}]}]}], [{"decision": "bypass", "include": [{"email": {"email": "owner@example.invalid"}}]}]]:
            with self.assertRaises(DNSError):
                politica_segura(politica)

    def test_acepta_lista_privada_sin_ampliarla(self):
        politica = [{"decision": "allow", "include": [{"email": {"email": "owner@example.invalid"}}]}]
        self.assertEqual(politica_segura(politica), politica)

    def test_conserva_tambien_las_politicas_de_denegacion(self):
        politicas = [
            {"decision": "deny", "precedence": 1, "include": [{"email": {"email": "blocked@example.invalid"}}]},
            {"decision": "allow", "precedence": 2, "include": [{"email": {"email": "owner@example.invalid"}}]},
        ]
        self.assertEqual(politica_segura(politicas), politicas)
