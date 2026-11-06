import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "Lib", "site-packages")))

from server import Router, Server, Http_status, BaseMiddleware
import router as router_module


class TestRouterDynamicAndMiddleware(unittest.TestCase):
    """Pruebas unitarias para rutas dinamicas, decoradores, middlewares e importacion de router.py."""

    def setUp(self):
        self.router = Router()
        self.status = Http_status()

    def test_router_decorators_syntax(self):
        """Verifica que los decoradores @router.get, @router.post registren rutas correctamente."""
        @self.router.get("ping")
        def ping():
            return {"msg": "pong"}, self.status.http_200()

        @self.router.post("enviar")
        def enviar(req):
            return {"recibido": True}, self.status.http_201()

        self.assertIn("ping", self.router.get_methods)
        self.assertIn("enviar", self.router.post_methods)

    def test_dynamic_path_parameter_matching(self):
        """Verifica que las rutas con parametros /recurso/{id} se capturen con sus valores."""
        @self.router.get("usuarios/{id}")
        def get_usuario(id):
            return {"id": id}, self.status.http_200()

        matched = self.router.match_dynamic_route("GET", "usuarios/105")
        self.assertIsNotNone(matched, "Fallo al emparejar ruta dinamica usuarios/{id}")
        fn, meta, path_params = matched
        self.assertEqual(path_params.get("id"), "105")

    def test_multi_parameter_dynamic_path(self):
        """Verifica rutas dinamicas con multiples parametros /catalogo/{categoria}/{item_id}."""
        @self.router.get("catalogo/{categoria}/{item_id}")
        def get_item(categoria, item_id):
            return {"categoria": categoria, "item_id": item_id}, self.status.http_200()

        matched = self.router.match_dynamic_route("GET", "catalogo/software/42")
        self.assertIsNotNone(matched)
        fn, meta, path_params = matched
        self.assertEqual(path_params.get("categoria"), "software")
        self.assertEqual(path_params.get("item_id"), "42")

    def test_middleware_process_request_short_circuit(self):
        """Verifica que un middleware pueda interceptar la peticion y responder anticipadamente."""
        class AuthMiddleware(BaseMiddleware):
            def process_request(self, rtype, suburl, params):
                if suburl[0] == "admin/secreto":
                    return {"error": "No autorizado"}, [b"401", b"Unauthorized"]
                return None

        server = Server(HOST="127.0.0.1", PORT=9998)
        server.add_middleware(AuthMiddleware())

        # Probar intercepcion en handle_request
        run, status = server.handle_request("GET", ["admin/secreto", ""], ["GET /admin/secreto HTTP/1.1\r\n\r\n"])
        self.assertEqual(status[0], b"401")
        self.assertEqual(run, {"error": "No autorizado"})

    def test_middleware_process_response_modification(self):
        """Verifica que un middleware pueda enriquecer o modificar la respuesta del controlador."""
        class HeaderEnricherMiddleware(BaseMiddleware):
            def process_response(self, rtype, suburl, run, status):
                if isinstance(run, dict):
                    run["procesado_por_middleware"] = True
                return run, status

        server = Server(HOST="127.0.0.1", PORT=9997)
        router = Router()

        @router.get("api/info")
        def info():
            return {"version": "1.0.0"}, Http_status().http_200()

        server.router.add_router(router)
        server.add_middleware(HeaderEnricherMiddleware())
        server._Server__METHODS = server.router

        run, status = server.handle_request("GET", ["api/info", ""], ["GET /api/info HTTP/1.1\r\n\r\n"])
        self.assertIn("procesado_por_middleware", run)
        self.assertTrue(run["procesado_por_middleware"])

    def test_router_module_exports(self):
        """Verifica que router.py exporte Router, Http_status y Request limpiamente sin imports ciclicos."""
        self.assertTrue(hasattr(router_module, "Router"))
        self.assertTrue(hasattr(router_module, "Http_status"))
        self.assertTrue(hasattr(router_module, "Request"))


if __name__ == "__main__":
    unittest.main()

