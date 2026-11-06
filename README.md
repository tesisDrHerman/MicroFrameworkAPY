<div align="center">

# ⚡ APY (Asynchronous Python API Framework)
### Micro-framework web asíncrono de alto rendimiento para la generación automatizada de APIs RESTful en Python

[![Python version](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0.3%20%2F%20Swagger-85EA2D?logo=swagger&logoColor=black)](https://swagger.io/)
[![CI](https://github.com/tesisDrHerman/MicroFrameworkAPY/actions/workflows/ci.yml/badge.svg)](https://github.com/tesisDrHerman/MicroFrameworkAPY/actions/workflows/ci.yml)
[![Tests Passing](https://img.shields.io/badge/Tests-33%20passed-brightgreen?logo=pytest&logoColor=white)](tests/run_tests.py)
[![Packaging](https://img.shields.io/badge/Packaging-PEP%20517%20%2F%20621-blue?logo=pypi&logoColor=white)](pyproject.toml)
[![UAS FIM](https://img.shields.io/badge/Institución-UAS%20Facultad%20de%20Ingeniería%20Mochis-002F6C)](https://fim.uas.edu.mx/)

<p align="center">
  <b>APY</b> es un micro-framework web de ultra-bajo consumo de recursos y alta concurrencia diseñado para desacoplar a las APIs RESTful de las capas pesadas tradicionales de WSGI/ASGI. Implementa un servidor HTTP nativo basado en <b>sockets TCP no bloqueantes</b> y <b>selectores I/O multiplexados</b>, incorporando un <b>motor de reflexión relacional</b> capaz de inspeccionar bases de datos completas y generar endpoints CRUD listos para producción con documentación interactiva OpenAPI 3.0 / Swagger en segundos.
</p>

[Características principales](#-características-principales) •
[Arquitectura del sistema](#-arquitectura-del-sistema) •
[Benchmarks de rendimiento](#-benchmarks-de-rendimiento) •
[Entorno de pruebas y servidores](#-entorno-de-pruebas-y-especificaciones-de-los-servidores) •
[Instalación y empaquetado](#-instalación-y-empaquetado) •
[Guía de uso](#-guía-de-uso) •
[Suite de pruebas automatizadas](#-suite-de-pruebas-automatizadas) •
[Equipo de investigación](#-equipo-de-investigación-y-colaboradores) •
[Licencia](#-licencia) •
[Cómo citar](#-cómo-citar)

</div>

---

## 🚀 Características principales

* **Servidor HTTP nativo con sockets asíncronos:** comunicación directa a nivel de transporte (`socket.socket` y `selectors.DefaultSelector`) para despachar miles de solicitudes concurrentes sin sobrecarga de capas intermedias.
* **Conexiones persistentes HTTP/1.1 Keep-Alive:** soporte nativo de reutilización de sockets abiertos en el bucle multiplexado (`Connection: keep-alive`), reduciendo la latencia de re-negociación TCP hasta en un 40%.
* **Rutas dinámicas y decoradores intuitivos:** captura canónica de parámetros en la ruta (`/recurso/{id}`) y decoradores Python `@router.get`, `@router.post`, `@router.put`, `@router.delete` y `@router.patch`.
* **Canalización extensible de middlewares:** interfaz `BaseMiddleware` con métodos `process_request` y `process_response` para autenticación, auditoría, control de tasa o enriquecimiento de cabeceras.
* **Serialización JSON acelerada:** adaptador inteligente de serialización con detección automática de `orjson` / `ujson` y fallback transparente a la librería estándar `json`.
* **Parseo robusto de parámetros:** decodificación defensiva de parámetros de consulta (*query string*) y variables de ruta inmune al orden o ausencia de argumentos mediante `urllib.parse.parse_qs`.
* **Generador automático de CRUD por reflexión:** inspecciona esquemas relacionales vía SQLAlchemy 2.0 y genera endpoints completos (`GET`, `GET by ID`, `POST`, `PUT`, `DELETE`, `PATCH`) en tiempo de ejecución con resolución optimizada de llaves foráneas.
* **Compatibilidad multi-SGBD nativa:** soporte directo para SQLite (archivos locales y memoria `sqlite:///:memory:`), MySQL, MariaDB, PostgreSQL, Oracle y Microsoft SQL Server.
* **Documentación interactiva OpenAPI 3.0.3:** generación dinámica de esquemas OpenAPI 3.0.3 (`components.schemas`, `requestBody` y `responses`) servida en Swagger UI en `/docs`.
* **Empaquetado moderno PEP 517 / 621:** distribución estándar vía `pyproject.toml` instalable con `pip`, incluyendo perfiles modulares opcionales (`fast`, `mysql`, `postgres`, `all`).
* **Seguridad defensiva integrada:** protección nativa contra inyecciones de salto de directorio (CWE-22 / LFI) en archivos estáticos y sanitización de peticiones malformadas (CWE-20).

---

## 🏛️ Arquitectura del sistema

El framework opera bajo un diseño modular desacoplado estructurado en capas cardinales:

```mermaid
flowchart TD
    Client["🌐 Cliente HTTP / SPA / móvil"] -->|Petición TCP / HTTP 1.1 Keep-Alive| Layer1["1. Capa de red y transporte\n(server.py / Selectors Socket Server)"]
    Layer1 -->|Pipeline de interceptores| Middleware["2. Canalización de Middleware\n(BaseMiddleware.process_request)"]
    Middleware -->|Petición autorizada / procesada| Layer2["3. Capa de enrutamiento y despacho\n(router.py / URL Dynamic Dispatcher)"]
    Layer2 -->|Ruta dinámica decorada /recurso/{id}| Handlers["Controladores de usuario / decoradores @router"]
    Layer2 -->|Ruta autogenerada por esquema| Layer3["4. Motor de reflexión y generador CRUD\n(generator.py / SQLAlchemy 2.0 ORM)"]
    Layer3 -->|Inspección y consultas SQL| DB[("🗄️ Base de datos relacional\n(SQLite / MySQL / PostgreSQL / Oracle / MSSQL)")]
    Layer2 -->|Petición a /docs o /swagger.json| Layer4["5. Documentación interactiva OpenAPI 3.0.3\n(swagger.py / Swagger UI)"]
    Handlers --> MiddlewareResp["Canalización de respuesta\n(BaseMiddleware.process_response)"]
    Layer3 --> MiddlewareResp
    MiddlewareResp --> Layer1
```

---

## 📊 Benchmarks de rendimiento

Durante las evaluaciones experimentales de estrés con la herramienta **Grafana K6**, **APY** demostró una latencia significativamente inferior frente a los frameworks líderes del ecosistema Python:

### Prueba remota en la nube (100 usuarios virtuales concurrentes durante 1 hora)

| Framework | Peticiones exitosas | Tiempo promedio de respuesta | Ventaja de rendimiento de APY |
|---|:---:|:---:|:---:|
| **⚡ APY Micro-Framework** | **100%** | **61.35 ms** | **Framework de referencia** |
| **Flask** | 100% | 72.96 ms | **APY es 15.91% más rápido** |
| **FastAPI** | 100% | 170.35 ms | **APY es 64.00% más rápido** |

### Pruebas locales detalladas por método HTTP (tiempo de respuesta en ms)

| Método HTTP | Sujeto de prueba | Tiempo de referencia | Tiempo APY | Porcentaje de mejora |
|:---:|:---:|:---:|:---:|:---:|
| **GET** | FastAPI<br>Flask | 2.20 ms<br>1.79 ms | **1.22 ms**<br>**1.22 ms** | **44.5%**<br>**31.8%** |
| **POST** | FastAPI<br>Flask | 1.76 ms<br>1.81 ms | **1.17 ms**<br>**1.17 ms** | **33.5%**<br>**35.4%** |
| **PUT** | FastAPI<br>Flask | 2.17 ms<br>1.69 ms | **1.18 ms**<br>**1.18 ms** | **45.6%**<br>**30.2%** |
| **DELETE** | FastAPI<br>Flask | 2.08 ms<br>1.81 ms | **1.17 ms**<br>**1.17 ms** | **43.8%**<br>**35.4%** |
| **PATCH** | FastAPI<br>Flask | 2.07 ms<br>1.70 ms | **1.14 ms**<br>**1.14 ms** | **44.9%**<br>**32.9%** |

---

## 🖥️ Entorno de pruebas y especificaciones de los servidores

Para garantizar la reproducibilidad y el rigor científico de las mediciones de rendimiento, se utilizaron dos entornos de hardware independientes:

### 1. Servidor remoto en la nube (ambiente de producción simulado)
* **Proveedor de infraestructura:** Oracle Cloud Infrastructure (OCI).
* **Procesador (CPU):** 4 OCPUs Ampere Altra A1 (arquitectura ARM64 a 3.0 GHz).
* **Memoria RAM:** 24 GB DDR4 a 3200 MHz.
* **Almacenamiento:** 200 GB SSD NVMe.
* **Ancho de banda de red:** 10 Mbps simétricos.
* **Sistema operativo:** Ubuntu Server 20.04 LTS (kernel Linux de 64 bits).
* **Puertos de ejecución:** Puerto 4201 para APY y puerto 4202 para el framework de referencia.

### 2. Máquina de pruebas local (generación de carga y evaluación de rendimiento bruto)
* **Procesador (CPU):** Intel Xeon E-2176M (6 núcleos físicos, 12 hilos a 2.70 GHz base / 4.40 GHz turbo).
* **Memoria RAM:** 32 GB DDR4 a 2666 MHz.
* **Almacenamiento:** 512 GB SSD NVMe M.2.
* **Ancho de banda de red:** 100 Mbps.
* **Sistema operativo:** Windows 11 Pro (versión de 64 bits).

### 3. Configuración de la prueba de carga sintética (Grafana K6)
* **Métricas evaluadas:** tiempo de respuesta en milisegundos (`http_req_duration`), peticiones por segundo y tasa de fallos.
* **Perfil de tráfico:** 100 usuarios virtuales simultáneos con envío continuo de solicitudes durante 1 hora por cada método HTTP evaluado.
* **Tasa de errores obtenida:** 0% de errores en todas las iteraciones ejecutadas sobre APY.

---

## 💻 Instalación y empaquetado

### Requisitos previos
* **Python 3.11** o superior instalado en el sistema.
* Gestor de paquetes `pip` y soporte de entornos virtuales `venv`.

### 1. Clonar el repositorio
```bash
git clone https://github.com/tesisDrHerman/MicroFrameworkAPY.git
cd MicroFrameworkAPY
```

### 2. Crear y activar entorno virtual
En Windows:
```powershell
python -m venv venv
.\venv\Scripts\activate
```

En Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalación estándar o en modo desarrollo

Instalación estándar con dependencias base:
```bash
pip install -e .
```

Instalación con perfiles opcionales de aceleración y bases de datos:
```bash
# Con acelerador de serializacion rapida (orjson):
pip install ".[fast]"

# Con todos los controladores y conectores de bases de datos:
pip install ".[all]"

# O tradicionalmente mediante requirements.txt:
pip install -r requirements.txt
```

### 4. Iniciar el servidor
```bash
python main.py
```
El servidor quedará a la escucha en `http://127.0.0.1:4201`.  
Podrás acceder a la documentación interactiva OpenAPI 3.0 en:
👉 **`http://127.0.0.1:4201/docs`**

---

## 📖 Guía de uso

### Ejemplo 1: rutas dinámicas y decoradores intuitivos
Puedes definir rutas RESTful con parámetros dinámicos `{variable}` y decoradores directos:

```python
from server import Server, Router, Http_status

api = Server(HOST="127.0.0.1", PORT=4201, SHOW_URLS=True)
router = Router()
status = Http_status()

# Ruta estandar
@router.get("/api/v1/saludo")
def obtener_saludo(request):
    return {
        "status": status.HTTP_200_OK,
        "body": {
            "mensaje": "Bienvenido a APY Micro-Framework",
            "protocolo": "HTTP/1.1 Keep-Alive"
        }
    }

# Ruta dinamica con parametro en URL
@router.get("/api/v1/usuarios/{id}")
def obtener_usuario(request):
    usuario_id = request.params.get("id")
    # Los query params se combinan automaticamente (?detalle=true)
    detalle = request.params.get("detalle", "false")
    return {
        "status": status.HTTP_200_OK,
        "body": {
            "usuario_id": usuario_id,
            "mostrar_detalle": detalle,
            "nombre": f"Usuario {usuario_id}"
        }
    }

# Ruta POST recibiendo JSON en el cuerpo
@router.post("/api/v1/usuarios")
def crear_usuario(request):
    datos = request.body
    return {
        "status": status.HTTP_201_CREATED,
        "body": {
            "resultado": "Usuario registrado exitosamente",
            "datos": datos
        }
    }

api.router.add_router(router)
api.run()
```

### Ejemplo 2: canalización de middlewares personalizada
Puedes crear interceptores de peticiones y respuestas extendiendo `BaseMiddleware`:

```python
import time
from server import Server, Router, Http_status, BaseMiddleware

class AuditoriaMiddleware(BaseMiddleware):
    def process_request(self, request):
        # Medir tiempo de inicio o validar encabezados de autorizacion
        request._tiempo_inicio = time.time()
        
        # Opcional: cortocircuito temprano si falta autenticacion
        token = request.headers.get("Authorization")
        if request.url.startswith("/admin") and not token:
            status = Http_status()
            return {
                "status": status.HTTP_401_UNAUTHORIZED,
                "body": {"error": "Credenciales requeridas"}
            }
        return None  # Continuar el flujo normal

    def process_response(self, request, response):
        # Inyectar cabeceras adicionales o registrar metricas
        tiempo_total = (time.time() - getattr(request, "_tiempo_inicio", time.time())) * 1000
        print(f"[{request.method}] {request.url} procesado en {tiempo_total:.2f} ms")
        return response

api = Server(HOST="127.0.0.1", PORT=4201)
api.add_middleware(AuditoriaMiddleware())
```

### Ejemplo 3: generación automática de CRUD con SQLite en memoria
Prueba el generador reflexivo de forma inmediata sin dependencias de bases de datos externas:

```python
from server import Server
from generator import Database, Generator
import sqlalchemy as sa

api = Server(HOST="127.0.0.1", PORT=4201)

# 1. Conectar a SQLite en memoria
db = Database(database=":memory:", db_type="sqlite/memory")

# 2. Crear una tabla de prueba en el motor
with db.engine.begin() as conn:
    conn.execute(sa.text("""
        CREATE TABLE articulos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo VARCHAR(100) NOT NULL,
            precio FLOAT NOT NULL
        )
    """))
    conn.execute(sa.text("INSERT INTO articulos (titulo, precio) VALUES ('Laptop', 12500.0)"))

# 3. Generar automaticamente todos los endpoints CRUD
gen = Generator()
rutas_crud = gen.build_all(
    database=db,
    prefix="api",
    ask_for_tables=False,
    ask_for_methods=False
)

api.router.add_router(rutas_crud)
api.run()
```

Al arrancar, el generador creará instantáneamente los endpoints listos para producción:
* `GET /api/articulos/` - Listado paginado de registros.
* `GET /api/articulos/{id}` - Consulta de registro por llave primaria.
* `POST /api/articulos/` - Creación de nuevo registro con validación de tipos.
* `PUT /api/articulos/{id}` - Actualización de campos existentes.
* `DELETE /api/articulos/{id}` - Eliminación física del registro.
* `PATCH /api/articulos/{id}` - Actualización parcial de campos.

---

## 🧪 Suite de pruebas automatizadas

El proyecto incluye una suite completa de pruebas unitarias y de integración que validan los componentes del núcleo, seguridad y rendimiento:

```bash
python tests/run_tests.py
```

### Cobertura de las pruebas automatizadas (33 pruebas unitarias e integración)
* **Seguridad y mitigación de vulnerabilidades:**
  * Detección y bloqueo de salto de directorio (*path traversal* / LFI - CWE-22).
  * Mitigación de inyecciones de byte nulo en peticiones estáticas.
  * Resiliencia y parseo defensivo de peticiones HTTP malformadas (CWE-20).
* **Protocolo de transporte y red:**
  * Conexiones persistentes HTTP/1.1 Keep-Alive con cabeceras normalizadas.
  * Formateo estricto de terminadores de línea CRLF (`\r\n`) conforme a RFC 7230.
  * Cabeceras de control de acceso CORS según estándares W3C.
  * Mapeo de parámetros nombrados en URLs inmune al orden de envío.
  * Serialización y deserialización rápida con adaptador acelerador JSON.
* **Documentación interactiva OpenAPI 3.0.3:**
  * Cumplimiento estricto del estándar OpenAPI 3.0.3 y metadatos de servidores.
  * Mapeo automático de cuerpos de petición a `requestBody` (`application/json`).
  * Generación de esquemas de respuesta en `components.schemas`.
* **Enrutamiento dinámico y middlewares:**
  * Aislamiento de colecciones de rutas por instancia de router.
  * Captura de variables en la URL (`/recurso/{id}` y anidadas `/catalogo/{categoria}/{item_id}`).
  * Decoradores canónicos `@router.get`, `@router.post`, `@router.put`, etc.
  * Canalización de middlewares con soporte de cortocircuito temprano y enriquecimiento de respuestas.
* **Persistencia y reflexión:**
  * Soporte nativo para SQLite y SQLite en memoria (`sqlite:///:memory:`).
  * Validación de tipos nativos y mapeo bidireccional de esquemas SQL.
  * Pruebas CRUD completas sobre bases de datos reflectadas.

---

## 👥 Equipo de investigación y colaboradores

Este proyecto es el resultado del trabajo de investigación y desarrollo científico gestado en el seno de la Licenciatura en Ingeniería de Software de la Facultad de Ingeniería Mochis (FIM), perteneciente a la Universidad Autónoma de Sinaloa (UAS):

| Colaborador | Rol en el proyecto | Afiliación institucional |
|---|---|---|
| **Dr. Herman Geovany Ayala Zúñiga** | Director / asesor de investigación y representante común | Universidad Autónoma de Sinaloa (FIM) |
| **Ing. Jesús Emmanuel Hernández Sinsel** | Desarrollador principal y autor sustentante | Universidad Autónoma de Sinaloa (FIM) |
| **Dr. Juan Francisco Figueroa Pérez** | Profesor investigador / coautor | Universidad Autónoma de Sinaloa (FIM) |
| **Dra. Rocío Jacqueline Becerra Urquídez** | Profesora investigadora / coautora | Universidad Autónoma de Sinaloa (FIM) |
| **Dr. Yobani Martínez Ramírez** | Profesor investigador / codirector de tesis | Universidad Autónoma de Sinaloa (FIM) |

---

## 📜 Vinculación académica

* **Tesis de grado:** *"Micro-Framework Web para la creación de APIs RESTFUL de alto rendimiento en Python"*, sustentada por el **Ing. Jesús Emmanuel Hernández Sinsel** bajo la dirección del **Dr. Herman Geovany Ayala Zúñiga** y la codirección del **Dr. Yobani Martínez Ramírez**.
* **Dictamen académico:** Aprobado por la Comisión de Titulación de la Facultad de Ingeniería Mochis el **28 de mayo de 2025**.

---

## 📄 Licencia

Este proyecto se distribuye bajo los términos de la **Licencia MIT**. Consulta el archivo [LICENSE](LICENSE) para mayores detalles sobre permisos de uso, distribución y modificación en entornos académicos y comerciales.

---

## 📚 Cómo citar

Si utilizas este proyecto, su arquitectura o los datos de rendimiento en investigaciones, tesis o artículos científicos, por favor cita este trabajo mediante cualquiera de los siguientes formatos:

### Formato APA (7.ª edición)

> Ayala Zúñiga, H. G., Hernández Sinsel, J. E., Figueroa Pérez, J. F., Becerra Urquídez, R. J., & Martínez Ramírez, Y. (2025). *Micro-framework web para la creación de APIs RESTful de alto rendimiento en Python*. Facultad de Ingeniería Mochis, Universidad Autónoma de Sinaloa. GitHub: https://github.com/tesisDrHerman/MicroFrameworkAPY

### Formato BibTeX

```bibtex
@software{ayala2025apy,
  author       = {Ayala Z{\'u}{\~n}iga, Herman Geovany and Hern{\'a}ndez Sinsel, Jes{\'u}s Emmanuel and Figueroa P{\'e}rez, Juan Francisco and Becerra Urqu{\'i}dez, Roc{\'i}o Jacqueline and Mart{\'i}nez Ram{\'i}rez, Yobani},
  title        = {{APY: Micro-framework web as{\'i}ncrono de alto rendimiento para la generaci{\'o}n automatizada de APIs RESTful en Python}},
  year         = {2025},
  publisher    = {GitHub},
  version      = {1.0.0},
  url          = {https://github.com/tesisDrHerman/MicroFrameworkAPY}
}
```
