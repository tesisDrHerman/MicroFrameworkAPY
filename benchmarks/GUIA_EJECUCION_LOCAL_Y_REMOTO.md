# Guía Detallada de Ejecución (Local y Remoto en Oracle Cloud)
## Paquete de Benchmarking Reproducible — MicroFrameworkAPY v1.0.0

Esta guía permite ejecutar en **un solo flujo automatizado** toda la batería experimental diseñada para responder a las observaciones mayores y menores del Revisor 1 (Obs. 2, 3, 4, 5, 6, 7, 10 y Menor 2–3) sobre [tesisDrHerman/MicroFrameworkAPY](https://github.com/tesisDrHerman/MicroFrameworkAPY).

---

## 1. Contenido del paquete

Al descomprimir `benchmarks_apy_v1_pack.zip`, coloca la carpeta resultante como `benchmarks/` **dentro de la raíz** de tu clon de `MicroFrameworkAPY`:

```text
MicroFrameworkAPY/
├── server.py
├── router.py
├── generator.py
├── tests/
└── benchmarks/
    ├── GUIA_EJECUCION_LOCAL_Y_REMOTO.md
    ├── requirements_bench.txt
    ├── schema_seed.py          # Crea esquema relacional (categories, users, orders) con 10,000 registros
    ├── bench_apy.py            # Servidor APY v1.0.0 (Echo + CRUD auto-generado con SQLAlchemy)
    ├── bench_fastapi.py        # Servidor equivalente FastAPI + Pydantic v2 + SQLAlchemy 2.0
    ├── bench_flask.py          # Servidor equivalente Flask + SQLAlchemy 2.0
    ├── k6_echo.js              # Escenario E1: 5 verbos HTTP Echo (warm-up 30s + medición)
    ├── k6_crud.js              # Escenario E2: CRUD real con JOINs/FK (50, 100, 200 VUs)
    ├── monitor_resources.py    # Escenario E3: Monitor 1 Hz de CPU %, RAM RSS (MB), sockets e hilos
    ├── run_benchmarks.sh       # Orquestador automático Linux / Ubuntu / macOS
    ├── run_benchmarks.ps1      # Orquestador automático Windows 11 (PowerShell)
    └── analyze_results.py      # Consolida JSON/CSV con IC 95% en summary_for_manuscript.csv
```

---

## 2. Requisitos previos

1. **Python 3.11 o 3.12** (usar exactamente la misma versión en local y en remoto).
2. **Grafana k6** ([documentación oficial](https://grafana.com/docs/k6/latest/set-up/install-k6/)):
   * **Ubuntu / Oracle Cloud:**
     ```bash
     sudo gpg -k
     sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
     echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
     sudo apt-get update && sudo apt-get install -y k6
     ```
   * **Windows 11 (PowerShell como Administrador):**
     ```powershell
     winget install k6 --source winget
     ```
3. **Base de datos para E2:** Por defecto los scripts usan **SQLite** (`benchmarks_crud.db`, cero configuración) para validar rápido. **Para la corrida definitiva de publicación (Q2)** se recomienda usar **MySQL 8 / MariaDB** o **PostgreSQL 16** pasando `DB_URL`, `DB_TYPE`, `DB_NAME`, `DB_HOST`, `DB_PORT`, `DB_USER` y `DB_PASS` como variables de entorno.

---

## 3. Ejecución en Entorno Local

### 3.1 Preparación del entorno virtual (Windows o Linux)

```bash
git clone https://github.com/tesisDrHerman/MicroFrameworkAPY.git
cd MicroFrameworkAPY
# (Copia aqui la carpeta benchmarks/ descomprimida)

python3 -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1

pip install -e ".[all]"
pip install -r benchmarks/requirements_bench.txt
```

### 3.2 Verificación rápida (prueba piloto de 15 segundos antes de la corrida larga)

Antes de lanzar la batería completa (~90 min con 3 repeticiones), valida que los 3 servidores arranquen y respondan correctamente:

```bash
# En Linux/macOS:
RUNS=1 VUS_LIST="50" ECHO_DURATION="15s" CRUD_DURATION="15s" bash benchmarks/run_benchmarks.sh
```

### 3.3 Corrida definitiva en Local (3 repeticiones + IC 95%)

* **En Linux / macOS:**
  ```bash
  bash benchmarks/run_benchmarks.sh
  ```
* **En Windows 11 (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File benchmarksun_benchmarks.ps1
  ```
* **Con MySQL local (recomendado para E2 definitivo):**
  ```bash
  export DB_TYPE="mysql"
  export DB_HOST="127.0.0.1"
  export DB_PORT="3306"
  export DB_NAME="bench_apy"
  export DB_USER="root"
  export DB_PASS="tu_password"
  export DB_URL="mysql+pymysql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
  bash benchmarks/run_benchmarks.sh
  ```

Al finalizar se generará **`results_export.zip`** con `summary_for_manuscript.csv`, `benchmark_versions.txt`, `radon_maintainability.txt`, todos los `*_summary.json` y los CSV de recursos.

---

## 4. Ejecución en Entorno Remoto (Oracle Cloud — OCI)

Para replicar el entorno de producción de la tesis (**4 OCPUs Ampere A1 ARM64, 24 GB RAM, Ubuntu**) evitando interferencia del generador de carga sobre el servidor bajo prueba, separa **Servidor (OCI)** y **Cliente generador (tu PC local o una segunda VM)**:

### 4.1 En el servidor remoto (Oracle Cloud — Ubuntu)

1. **Abrir puertos en OCI Security List y firewall local (`ufw` / `iptables`):**
   Permitir tráfico TCP entrante en los puertos `4201` (APY), `4202` (FastAPI) y `4203` (Flask) **únicamente desde la IP pública de tu máquina cliente**.
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 4201:4203 -j ACCEPT
   ```
2. **Clonar el repo, instalar dependencias y poblar la BD (paso 3.1 + `schema_seed.py`):**
   ```bash
   python3 benchmarks/schema_seed.py --db-url "$DB_URL"
   ```
3. **Levantar UN servidor a la vez dentro de `tmux`** (para que no se corte si cae SSH) y monitorear sus recursos en paralelo:
   ```bash
   tmux new -s bench
   # Ejemplo 1: APY v1.0.0
   APY_HOST=0.0.0.0 APY_PORT=4201 python3 benchmarks/bench_apy.py &
   SRV_PID=$!
   python3 benchmarks/monitor_resources.py $SRV_PID results/remote_apy_crud_100vu_run1_res.csv 215
   ```
   *(Al terminar las 3 repeticiones de APY, detenlo con `kill $SRV_PID`, espera 5 s y repite con FastAPI en `4202` y Flask en `4203`.)*

### 4.2 En la máquina cliente (generando carga hacia `<IP_OCI>`)

Ejecutar Grafana k6 apuntando a la IP pública del servidor OCI:

```bash
export OCI_IP="TU.IP.DE.OCI"

# Ejemplo: APY remoto (puerto 4201), 100 VUs, 3 repeticiones
for run in 1 2 3; do
  k6 run     -e BASE_URL="http://${OCI_IP}:4201"     -e VUS=100     -e DURATION=180s     --summary-export="results_remote/remote_apy_crud_100vu_run${run}_summary.json"     benchmarks/k6_crud.js
  sleep 10
done
```
Repetir el mismo bucle cambiando el puerto y el prefijo para **FastAPI (`4202`)** y **Flask (`4203`)**, y también para `k6_echo.js` (`METHOD=GET`) si se desea mantener la comparación directa de 1 hora (`DURATION=3600s`) o 3 repeticiones de 10 minutos (`DURATION=600s`).

### 4.3 Consolidación remota
Copia los `*_res.csv` del servidor OCI dentro de `results_remote/` y ejecuta:
```bash
python3 benchmarks/analyze_results.py --results-dir results_remote
zip -r results_remote_export.zip results_remote
```

---

## 5. Qué subir al chat al terminar

Sube **`results_export.zip`** (local) y **`results_remote_export.zip`** (remoto). Con esos archivos generaré automáticamente:
1. Las tablas completas (`Mean`, `P50`, `P95`, `P99`, `IC 95%`, `req/s`, `total requests`, `error %`, `CPU %`, `RAM MB`, `SLOC/CC/MI`).
2. Las gráficas renovadas a 300 dpi con percentiles y bandas de confianza.
3. El manuscrito **Word v2** actualizado con todas las mejoras de `MicroFrameworkAPY v1.0.0` y la **Carta de Respuesta punto por punto al Revisor 1**.
