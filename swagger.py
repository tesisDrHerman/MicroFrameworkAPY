import json
from typing import List, Dict, Any, Optional


class Swagger:
    """Generador dinámico de documentación OpenAPI 3.0.3 para APY Micro-Framework."""

    def generate_swagger(
        self,
        api_details: List[Dict[str, Any]],
        host: str,
        port: int,
        title: str = "APY Generated API",
        version: str = "1.0.0",
        description: str = "Documentación interactiva autogenerada por APY Micro-Framework."
    ) -> str:
        """
        Genera la especificación JSON conforme al estándar OpenAPI 3.0.3.

        Args:
            api_details: Metadatos de los endpoints registrados en el enrutador.
            host: Dirección IP o nombre de host donde escucha el servidor.
            port: Puerto de red del servidor.
            title: Título descriptivo de la API.
            version: Versión de la API.
            description: Resumen descriptivo general de los servicios.

        Returns:
            Cadena de texto con el documento JSON estructurado según OpenAPI 3.0.3.
        """
        openapi_template: Dict[str, Any] = {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "description": description,
                "version": version
            },
            "servers": [
                {
                    "url": f"http://{host}:{port}",
                    "description": "Servidor de desarrollo local"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {}
            }
        }

        for api in api_details:
            table_name = str(api.get('table', 'General')).replace("_", " ").capitalize()
            path = api.get('path', '/')
            method = api.get('method', 'get').lower()

            if path not in openapi_template['paths']:
                openapi_template['paths'][path] = {}

            parameters: List[Dict[str, Any]] = []
            request_body: Optional[Dict[str, Any]] = None

            for param in api.get('parameters', []):
                param_in = param.get('in', 'query')
                param_type = param.get('type', 'string')

                # Normalizar tipos para esquema OpenAPI 3
                if param_type in ("int", "integer"):
                    schema_type = "integer"
                elif param_type in ("float", "number"):
                    schema_type = "number"
                elif param_type in ("bool", "boolean"):
                    schema_type = "boolean"
                else:
                    schema_type = "string"

                if param_in == "body" or (method in ("post", "put", "patch") and param.get("name") == "body"):
                    request_body = {
                        "required": param.get('required', True),
                        "content": {
                            "application/json": {
                                "schema": param.get('schema', {
                                    "type": "object",
                                    "additionalProperties": True
                                })
                            }
                        }
                    }
                else:
                    parameters.append({
                        "name": param.get('name', 'param'),
                        "in": param_in,
                        "required": param.get('required', False),
                        "schema": {
                            "type": schema_type
                        }
                    })

            operation: Dict[str, Any] = {
                "summary": api.get('summary', f"Operación {method.upper()} para {table_name}"),
                "tags": [table_name],
                "parameters": parameters,
                "responses": {
                    "200": {
                        "description": "Operación exitosa",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": True
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Petición incorrecta o parámetros inválidos"
                    },
                    "404": {
                        "description": "Recurso no encontrado"
                    }
                }
            }

            if request_body:
                operation["requestBody"] = request_body

            if 'response_model' in api and api['response_model'] and 'model_fields' in api and api['model_fields']:
                model_name = api['response_model']
                operation['responses']['200']['content']['application/json']['schema'] = {
                    "$ref": f"#/components/schemas/{model_name}"
                }
                if model_name not in openapi_template['components']['schemas']:
                    properties = {}
                    for field in api['model_fields']:
                        f_type = field.get('type', 'string')
                        if f_type in ("int", "integer"):
                            prop_type = "integer"
                        elif f_type in ("float", "number"):
                            prop_type = "number"
                        elif f_type in ("bool", "boolean"):
                            prop_type = "boolean"
                        else:
                            prop_type = "string"
                        properties[field['name']] = {"type": prop_type}
                    openapi_template['components']['schemas'][model_name] = {
                        "type": "object",
                        "properties": properties
                    }

            openapi_template['paths'][path][method] = operation

        return json.dumps(openapi_template, indent=2)
