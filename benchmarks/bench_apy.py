"""Servidor de benchmark para MicroFrameworkAPY v1.0.0.
Debe ejecutarse desde la raiz del repositorio MicroFrameworkAPY.

Variables de entorno opcionales:
  APY_HOST=0.0.0.0
  APY_PORT=4201
  DB_TYPE=sqlite          (sqlite | mysql | postgresql)
  DB_NAME=benchmarks_crud.db
  DB_HOST=127.0.0.1
  DB_PORT=3306
  DB_USER=root
  DB_PASS=password
"""

import os
import sys

# Asegurar que la raiz del repositorio este en sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from server import Server, Http_status
from generator import Database, Generator

status = Http_status()
HOST = os.getenv("APY_HOST", "0.0.0.0")
PORT = int(os.getenv("APY_PORT", "4201"))
THREADS = int(os.getenv("APY_THREADS", "4"))

api = Server(HOST=HOST, PORT=PORT, SHOW_URLS=False, threads=THREADS)

# --- Escenario E1: Endpoints Echo (5 verbos HTTP) ---
def echo_get(value: str = "hello"):
    return {"value": value}, status.http_200()


def echo_post(payload: dict = None):
    return (payload if payload is not None else {"status": "ok"}), status.http_200()


def echo_put(value: str = "updated"):
    return {"value": value}, status.http_200()


def echo_delete(value: str = "deleted"):
    return {"value": value}, status.http_200()


def echo_patch(value: str = "patched"):
    return {"value": value}, status.http_200()


api.router.add_get(function=echo_get, url="echo/get")
api.router.add_post(function=echo_post, url="echo/post")
api.router.add_put(function=echo_put, url="echo/put")
api.router.add_delete(function=echo_delete, url="echo/delete")
api.router.add_patch(function=echo_patch, url="echo/patch")

# --- Escenario E2: Generacion automatica CRUD con reflexion SQLAlchemy ---
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_NAME = os.getenv("DB_NAME", "benchmarks_crud.db")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")

if DB_TYPE == "sqlite":
    db = Database(host="", port=0, database=DB_NAME, username="", password="", db_type="sqlite", threads=THREADS)
else:
    db = Database(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        username=DB_USER,
        password=DB_PASS,
        db_type=DB_TYPE,
        threads=THREADS,
    )

gen = Generator(threads=THREADS)
api.router.add_router(
    gen.build_all(
        database=db,
        prefix="api",
        ask_for_tables=False,
        ask_for_methods=False,
        threads=THREADS,
    )
)

# Alias de compatibilidad con las rutas esperadas por k6_crud.js (paridad con FastAPI y Flask)
if 'api/orders/create' in api.router.post_methods:
    api.router.post_methods['api/orders/post'] = api.router.post_methods['api/orders/create']
if 'api/orders/update' in api.router.put_methods:
    api.router.put_methods['api/orders/put'] = api.router.put_methods['api/orders/update']

if __name__ == "__main__":
    print(f"[APY v1.0.0] PID={os.getpid()} escuchando en http://{HOST}:{PORT} (threads={THREADS})")
    api.run(threads=THREADS)
