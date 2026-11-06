import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "Lib", "site-packages")))


from server import Server


def is_safe_static_path(base_dir: str, requested_path: str) -> bool:
    """
    Funcion de referencia de seguridad recomendada para validar rutas estaticas.
    Previene ataques de Path Traversal (CWE-22).
    """
    if not requested_path or "\x00" in requested_path:
        return False
    # Normalizar ruta base canonica
    base_canonical = os.path.realpath(base_dir)
    # Resolver ruta absoluta objetivo
    target_path = os.path.realpath(os.path.join(base_canonical, requested_path))
    # Comprobar si la ruta objetivo reside estrictamente dentro de la ruta base
    try:
        common = os.path.commonpath([base_canonical, target_path])
        return common == base_canonical and os.path.isfile(target_path)
    except ValueError:
        return False


class TestSecurityLFI(unittest.TestCase):
    """Pruebas de seguridad defensiva contra Path Traversal y LFI (Local File Inclusion)."""

    def setUp(self):
        self.htdocs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "htdocs"))

    def test_safe_path_valid_file(self):
        """Verifica que los archivos legítimos dentro de htdocs sean permitidos."""
        self.assertTrue(is_safe_static_path(self.htdocs_dir, "swagger.html"))

    def test_path_traversal_detection(self):
        """
        Verifica que intentos de escape con ../ sean detectados y bloqueados.
        """
        malicious_paths = [
            "../../main.py",
            "../server.py",
            "../../../../etc/passwd",
            "..\\..\\README.md",
            "./../../requirements.txt"
        ]
        for path in malicious_paths:
            is_safe = is_safe_static_path(self.htdocs_dir, path)
            self.assertFalse(is_safe, f"Fallo de seguridad: {path} no fue bloqueado.")

    def test_null_byte_injection(self):
        """Verifica que inyecciones de byte nulo sean bloqueadas."""
        malicious = "swagger.html\x00.php"
        self.assertFalse(is_safe_static_path(self.htdocs_dir, malicious))

    def test_server_safe_static_path_integration(self):
        """Verifica que el metodo implementado en Server bloquee traversal y acepte legitimos."""
        self.assertIsNotNone(Server.safe_static_path("htdocs", "swagger.html"))
        self.assertIsNone(Server.safe_static_path("htdocs", "../../main.py"))
        self.assertIsNone(Server.safe_static_path("htdocs", "../server.py"))
        self.assertIsNone(Server.safe_static_path("htdocs", "..\\..\\README.md"))
        self.assertIsNone(Server.safe_static_path("htdocs", "archivo_inexistente_123.txt"))


if __name__ == "__main__":
    unittest.main()
