import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "Lib", "site-packages")))

from server import Server, Http_status, Router


class TestServerProtocol(unittest.TestCase):
    """Pruebas para el manejo de protocolo HTTP, parseo y codigos de estado."""

    def setUp(self):
        self.server = Server(HOST="127.0.0.1", PORT=9999)
        self.status = Http_status()

    def test_http_status_codes(self):
        """Verifica la respuesta de codigos HTTP basicos."""
        self.assertEqual(self.status.http_200(), [b"200", b"OK"])
        self.assertEqual(self.status.http_201(), [b"201", b"Created"])
        self.assertEqual(self.status.http_404(), [b"404", b"Not-Found"])
        self.assertEqual(self.status.http_400(), [b"400", b"Bad-Request"])

    def test_get_url_standard(self):
        """Verifica la extraccion de ruta y query string en peticiones bien formadas."""
        raw_request = ["GET /api/v1/usuarios?rol=admin&activo=true HTTP/1.1\r\nHost: localhost\r\n\r\n"]
        suburl = self.server.get_url(raw_request)
        self.assertEqual(suburl[0], "api/v1/usuarios")
        self.assertEqual(suburl[1], "rol=admin&activo=true")

    def test_get_url_without_query_params(self):
        """Verifica la extraccion de ruta sin query params."""
        raw_request = ["GET /api/v1/saludo HTTP/1.1\r\nHost: localhost\r\n\r\n"]
        suburl = self.server.get_url(raw_request)
        self.assertEqual(suburl[0], "api/v1/saludo")
        self.assertEqual(suburl[1], "")

    def test_request_constructor_methods(self):
        """Verifica que el constructor de peticion identifique el metodo HTTP correcto."""
        post_raw = ["POST /api/v1/crear HTTP/1.1\r\n", '{"nombre": "test"}']
        rtype, data = self.server.request_constructor(8080, post_raw)
        self.assertEqual(rtype, "POST")
        self.assertEqual(data[1], '{"nombre": "test"}')

        get_raw = ["GET /api/v1/items HTTP/1.1\r\nHost: localhost"]
        rtype, data = self.server.request_constructor(8080, get_raw)
        self.assertEqual(rtype, "GET")

    def test_malformed_request_resilience(self):
        """
        Verifica que una peticion malformada o vacia no cause una excepcion no controlada.
        """
        empty_raw = [""]
        try:
            suburl = self.server.get_url(empty_raw)
            # Debe retornar cadena vacia o lista segura sin lanzar excepcion no capturada
            self.assertTrue(isinstance(suburl, (list, str)))
        except Exception as e:
            self.fail(f"get_url fallo con excepcion no controlada ante request vacia: {e}")

    def test_guess_type(self):
        """Verifica la deduccion automatica de tipos escalares."""
        self.assertEqual(self.server.guess_type("123"), 123)
        self.assertEqual(self.server.guess_type("45.67"), 45.67)
        self.assertEqual(self.server.guess_type("True"), True)
        self.assertEqual(self.server.guess_type("False"), False)
        self.assertEqual(self.server.guess_type("texto_plano"), "texto_plano")


if __name__ == "__main__":
    unittest.main()

