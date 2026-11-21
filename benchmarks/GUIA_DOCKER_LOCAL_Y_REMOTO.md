# Guía de Ejecución con Docker Compose (MySQL 8 / PostgreSQL 16)
## Entorno Local y Remoto (Oracle Cloud) — MicroFrameworkAPY v1.0.0

Este paquete incluye **Docker Compose preconfigurado** con perfiles independientes para **MySQL 8.0** y **PostgreSQL 16**, límites fijos de CPU y RAM (`2 vCPU / 1 GB RAM` por servidor de API; `2 vCPU / 2 GB RAM` para la BD), imagen unificada Python 3.11 (`Dockerfile.bench`) y contenedor oficial `grafana/k6:latest` (no requiere instalar k6 ni Python localmente).

---

## 1. Preparación rápida (2 pasos)

1. Clona el repositorio y coloca la carpeta `benchmarks/` descomprimida en la raíz:
   ```bash
   git clone https://github.com/tesisDrHerman/MicroFrameworkAPY.git
   cd MicroFrameworkAPY
   cp benchmarks/.env.example benchmarks/.env
   ```
2. Verifica que Docker y Docker Compose v2 estén activos:
   ```bash
   docker --version && docker compose version
   ```

---

## 2. Ejecución automatizada en Local (MySQL o PostgreSQL)

* **Prueba piloto rápida (15 s por escenario, 1 repetición) con MySQL 8:**
  ```bash
  DB_ENGINE=mysql RUNS=1 VUS_LIST="50" ECHO_DURATION="15s" CRUD_DURATION="15s" bash benchmarks/run_docker_benchmarks.sh
  ```
* **Corrida definitiva con MySQL 8 (3 repeticiones + IC 95%):**
  ```bash
  DB_ENGINE=mysql bash benchmarks/run_docker_benchmarks.sh
  ```
* **Corrida definitiva con PostgreSQL 16 (3 repeticiones + IC 95%):**
  ```bash
  DB_ENGINE=postgres bash benchmarks/run_docker_benchmarks.sh
  ```

Al terminar, se genera `results_mysql_docker_export.zip` (o `results_postgres_docker_export.zip`) con `summary_for_manuscript.csv`, `benchmark_versions.txt`, `radon_maintainability.txt`, todos los `*_summary.json` de k6 y los CSV de `docker stats` (CPU % y RAM MB por segundo).

---

## 3. Ejecución en Remoto (Oracle Cloud — OCI)

Para separar **Servidor bajo prueba (OCI)** y **Cliente generador de carga (tu PC)**:

### 3.1 En el servidor Oracle Cloud (Ubuntu)
1. Abrir los puertos `4201–4203` únicamente para la IP de tu máquina cliente.
2. Levantar la base de datos elegida (`mysql` o `postgres`) y poblarla:
   ```bash
   docker compose -f benchmarks/docker-compose.yml --env-file benchmarks/.env --profile mysql up -d mysql
   docker compose -f benchmarks/docker-compose.yml --env-file benchmarks/.env --profile apy run --rm \
     -e DB_URL="mysql+pymysql://bench_user:bench_pass_2026@mysql:3306/bench_apy" \
     apy-server python3 benchmarks/schema_seed.py --db-url "mysql+pymysql://bench_user:bench_pass_2026@mysql:3306/bench_apy"
   ```
3. Levantar **un solo framework a la vez** (`apy-server`, luego `fastapi-server`, luego `flask-server`) y registrar recursos con `monitor_docker_stats.py`:
   ```bash
   docker compose -f benchmarks/docker-compose.yml --env-file benchmarks/.env --profile apy up -d apy-server
   python3 benchmarks/monitor_docker_stats.py bench_apy results_remote/remote_apy_crud_100vu_run1_res.csv 215
   ```

### 3.2 En la máquina cliente (apuntando a `<IP_OCI>`)
Ejecutar el contenedor oficial de k6 contra el puerto del servidor activo en OCI:
```bash
export OCI_IP="TU.IP.DE.OCI"
mkdir -p results_remote

for run in 1 2 3; do
  docker run --rm \
    -v "$(pwd)/benchmarks:/scripts:ro" \
    -v "$(pwd)/results_remote:/results" \
    grafana/k6:latest run \
    -e BASE_URL="http://${OCI_IP}:4201" \
    -e VUS=100 \
    -e DURATION=180s \
    --summary-export="/results/remote_apy_crud_100vu_run${run}_summary.json" \
    /scripts/k6_crud.js
  sleep 10
done
```
Repite el mismo bucle para `4202` (`fastapi`) y `4203` (`flask`), junta los `*_res.csv` en `results_remote/`, ejecuta `analyze_results.py` y sube el ZIP final al chat.
