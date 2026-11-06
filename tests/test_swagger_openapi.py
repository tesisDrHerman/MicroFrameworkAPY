import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "Lib", "site-packages")))

from swagger import Swagger


class TestSwaggerOpenAPI(unittest.TestCase):
    """Pruebas para la generacion de documentacion OpenAPI 3.0 / Swagger."""

    def setUp(self):
        self.swagger = Swagger()
        self.sample_api_details = [
            {
                "path": "/api/usuarios",
                "method": "GET",
                "summary": "Obtener listado de usuarios",
                "table": "usuarios",
                "parameters": [
                    {
                        "name": "id",
                        "in": "query",
                        "required": False,
                        "type": "integer"
                    }
                ],
                "response_model": "UsuarioModel",
                "model_fields": [
                    {"name": "id", "type": "integer"},
                    {"name": "nombre", "type": "string"},
                    {"name": "email", "type": "string"}
                ]
            },
            {
                "path": "/api/usuarios",
                "method": "POST",
                "summary": "Crear nuevo usuario",
                "table": "usuarios",
                "parameters": [
                    {
                        "name": "body",
                        "in": "body",
                        "required": True,
                        "type": "object"
                    }
                ],
                "response_model": "",
                "model_fields": []
            }
        ]

    def test_openapi_version_and_info(self):
        """Verifica que la documentacion generada use el estandar OpenAPI 3.0.3."""
        raw_json = self.swagger.generate_swagger(self.sample_api_details, "127.0.0.1", 4201)
        doc = json.loads(raw_json)

        self.assertEqual(doc.get("openapi"), "3.0.3")
        self.assertIn("info", doc)
        self.assertIn("title", doc["info"])
        self.assertIn("version", doc["info"])

    def test_servers_configuration(self):
        """Verifica que la seccion servers contenga la URL correcta del host y puerto."""
        raw_json = self.swagger.generate_swagger(self.sample_api_details, "127.0.0.1", 4201)
        doc = json.loads(raw_json)

        self.assertIn("servers", doc)
        self.assertEqual(doc["servers"][0]["url"], "http://127.0.0.1:4201")

    def test_paths_and_operations(self):
        """Verifica que las rutas y metodos HTTP se mapeen correctamente con sus etiquetas."""
        raw_json = self.swagger.generate_swagger(self.sample_api_details, "127.0.0.1", 4201)
        doc = json.loads(raw_json)

        self.assertIn("/api/usuarios", doc["paths"])
        path_item = doc["paths"]["/api/usuarios"]
        self.assertIn("get", path_item)
        self.assertIn("post", path_item)
        self.assertEqual(path_item["get"]["tags"], ["Usuarios"])

    def test_openapi3_request_body_conversion(self):
        """Verifica que los parametros de tipo body se conviertan a requestBody en OpenAPI 3."""
        raw_json = self.swagger.generate_swagger(self.sample_api_details, "127.0.0.1", 4201)
        doc = json.loads(raw_json)

        post_op = doc["paths"]["/api/usuarios"]["post"]
        self.assertIn("requestBody", post_op)
        self.assertIn("application/json", post_op["requestBody"]["content"])

    def test_components_schemas_generation(self):
        """Verifica que los modelos de respuesta se generen en components.schemas."""
        raw_json = self.swagger.generate_swagger(self.sample_api_details, "127.0.0.1", 4201)
        doc = json.loads(raw_json)

        self.assertIn("components", doc)
        self.assertIn("schemas", doc["components"])
        self.assertIn("UsuarioModel", doc["components"]["schemas"])
        fields = doc["components"]["schemas"]["UsuarioModel"]["properties"]
        self.assertIn("id", fields)
        self.assertIn("nombre", fields)


if __name__ == "__main__":
    unittest.main()
