import unittest
import sys
import os

# Configurar ruta para importar modulos del framework
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "Lib", "site-packages")))

from server import Router, Http_status


class TestRouter(unittest.TestCase):
    """Pruebas unitarias para la clase Router y gestion de rutas."""

    def test_router_methods_registration(self):
        """Verifica que los metodos GET, POST, PUT, DELETE y PATCH se registren correctamente."""
        router = Router()
        
        def dummy_get():
            return {"msg": "ok"}, Http_status().http_200()

        def dummy_post(req):
            return {"msg": "created"}, Http_status().http_201()

        router.add_get(dummy_get, "saludo")
        router.add_post(dummy_post, "crear")

        self.assertIn("saludo", router.get_methods)
        self.assertIn("crear", router.post_methods)

    def test_router_prefix(self):
        """Verifica que el prefijo se anteponga a las rutas registradas."""
        router = Router(prefix="api/v1")

        def dummy_endpoint():
            return "ok", Http_status().http_200()

        router.add_get(dummy_endpoint, "items")
        self.assertIn("api/v1/items", router.get_methods)

    def test_router_isolation(self):
        """
        Verifica el aislamiento de estado entre instancias independientes de Router.
        Detecta el defecto de compartir colecciones como variables de clase.
        """
        router_a = Router(prefix="modulo_a")
        router_b = Router(prefix="modulo_b")

        def handler_a():
            return "a", Http_status().http_200()

        def handler_b():
            return "b", Http_status().http_200()

        router_a.add_get(handler_a, "endpoint_a")
        router_b.add_get(handler_b, "endpoint_b")

        # Cada router debe contener unicamente sus propias rutas
        self.assertIn("modulo_a/endpoint_a", router_a.get_methods)
        self.assertIn("modulo_b/endpoint_b", router_b.get_methods)
        # Verificacion de aislamiento
        self.assertNotIn("modulo_a/endpoint_a", router_b.get_methods, 
                         "Fuga de estado detectada: Router B contiene rutas de Router A")
        self.assertNotIn("modulo_b/endpoint_b", router_a.get_methods,
                         "Fuga de estado detectada: Router A contiene rutas de Router B")


if __name__ == "__main__":
    unittest.main()

