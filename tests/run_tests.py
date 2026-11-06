#!/usr/bin/env python3
"""
Ejecutor de pruebas automatizadas para APY Micro-Framework.
Permite validar la seguridad, el protocolo y la integridad del framework
antes de realizar commits o sincronizaciones en el repositorio.
"""

import unittest
import sys
import os
import time

# Asegurar inclusion del directorio raiz y librerias
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENV_PACKAGES = os.path.join(BASE_DIR, "venv", "Lib", "site-packages")

sys.path.insert(0, BASE_DIR)
if os.path.exists(VENV_PACKAGES):
    sys.path.insert(0, VENV_PACKAGES)


def main():
    print("=" * 70)
    print("  EJECUTOR DE PRUEBAS AUTOMATIZADAS - APY MICRO-FRAMEWORK")
    print(f"  Directorio del proyecto: {BASE_DIR}")
    print(f"  Version de Python: {sys.version.split()[0]}")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.dirname(__file__), pattern="test_*.py")

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    duration = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"  RESUMEN DE PRUEBAS:")
    print(f"  - Total ejecutadas : {result.testsRun}")
    print(f"  - Exitosas         : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  - Fallidas         : {len(result.failures)}")
    print(f"  - Errores          : {len(result.errors)}")
    print(f"  - Tiempo total     : {duration:.3f} segundos")
    print("=" * 70)

    if not result.wasSuccessful():
        print("\n[!] ALERTA: Se detectaron fallos o vulnerabilidades en las pruebas.")
        sys.exit(1)
    else:
        print("\n[+] EXITO: Todas las pruebas de validacion pasaron satisfactoriamente.")
        sys.exit(0)


if __name__ == "__main__":
    main()

