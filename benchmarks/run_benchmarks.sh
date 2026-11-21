#!/usr/bin/env bash
# Orquestador automatizado para Linux / Ubuntu (Local y Oracle Cloud)
# Ejecutar desde la raiz del repositorio MicroFrameworkAPY:
#   bash benchmarks/run_benchmarks.sh
set -euo pipefail

RESULTS_DIR="results"
mkdir -p "$RESULTS_DIR"

export DB_URL="${DB_URL:-sqlite:///benchmarks_crud.db}"
export DB_TYPE="${DB_TYPE:-sqlite}"
export DB_NAME="${DB_NAME:-benchmarks_crud.db}"

VUS_LIST="${VUS_LIST:-50 100 200}"
RUNS="${RUNS:-3}"
ECHO_DURATION="${ECHO_DURATION:-150s}"
CRUD_DURATION="${CRUD_DURATION:-180s}"
MON_ECHO_SEC=185
MON_CRUD_SEC=215

echo "=== 1. Registrando versiones exactas de software y hardware ==="
{
  date -u
  uname -a
  lscpu | grep -E "Model name|CPU\(s\):" || true
  free -h || true
  python3 --version
  k6 version
  echo "--- pip freeze ---"
  pip freeze
} > "$RESULTS_DIR/benchmark_versions.txt"

echo "=== 2. Ejecutando suite de 33 pruebas internas de APY ==="
python3 tests/run_tests.py > "$RESULTS_DIR/apy_unit_tests.txt" 2>&1 || true

echo "=== 3. Metricas estaticas de mantenibilidad (E4: SLOC, CC, MI) ==="
{
  echo "=== RADON RAW (SLOC) ==="
  radon raw -s benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
  echo "=== RADON CYCLOMATIC COMPLEXITY ==="
  radon cc -a benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
  echo "=== RADON MAINTAINABILITY INDEX ==="
  radon mi benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
} > "$RESULTS_DIR/radon_maintainability.txt"

echo "=== 4. Poblando base de datos relacional (E2) ==="
python3 benchmarks/schema_seed.py --db-url "$DB_URL"

run_suite_for_framework() {
  local FW="$1"
  local PORT="$2"
  local START_CMD="$3"

  echo "============================================================"
  echo "Iniciando servidor: $FW en puerto $PORT"
  echo "============================================================"
  eval "$START_CMD" > "$RESULTS_DIR/${FW}_server.log" 2>&1 &
  local SRV_PID=$!
  sleep 4

  # Smoke test rapido
  if ! curl -sf "http://127.0.0.1:${PORT}/echo/get?value=ok" > /dev/null; then
    echo "[ERROR] El servidor $FW no respondio en /echo/get. Revisa $RESULTS_DIR/${FW}_server.log"
    kill "$SRV_PID" 2>/dev/null || true
    exit 1
  fi

  # --- E1: Echo (5 metodos HTTP a 100 VUs, 3 repeticiones) ---
  for METHOD in GET POST PUT DELETE PATCH; do
    for RUN in $(seq 1 "$RUNS"); do
      local TAG="${FW}_echo-${METHOD,,}_100vu_run${RUN}"
      echo "[E1] $TAG"
      python3 benchmarks/monitor_resources.py "$SRV_PID" "$RESULTS_DIR/${TAG}_res.csv" "$MON_ECHO_SEC" &
      local MON_PID=$!
      k6 run         -e BASE_URL="http://127.0.0.1:${PORT}"         -e METHOD="$METHOD"         -e VUS=100         -e DURATION="$ECHO_DURATION"         --summary-export="$RESULTS_DIR/${TAG}_summary.json"         benchmarks/k6_echo.js
      wait "$MON_PID" || true
      sleep 5
    done
  done

  # --- E2 + E3: CRUD real con SQL + JOINs (50, 100, 200 VUs) ---
  for VUS in $VUS_LIST; do
    for RUN in $(seq 1 "$RUNS"); do
      local TAG="${FW}_crud_${VUS}vu_run${RUN}"
      echo "[E2+E3] $TAG"
      python3 benchmarks/monitor_resources.py "$SRV_PID" "$RESULTS_DIR/${TAG}_res.csv" "$MON_CRUD_SEC" &
      local MON_PID=$!
      k6 run         -e BASE_URL="http://127.0.0.1:${PORT}"         -e VUS="$VUS"         -e DURATION="$CRUD_DURATION"         --summary-export="$RESULTS_DIR/${TAG}_summary.json"         benchmarks/k6_crud.js
      wait "$MON_PID" || true
      sleep 5
    done
  done

  kill "$SRV_PID" 2>/dev/null || true
  wait "$SRV_PID" 2>/dev/null || true
  sleep 3
}

run_suite_for_framework "apy" 4201 "APY_PORT=4201 python3 benchmarks/bench_apy.py"
run_suite_for_framework "fastapi" 4202 "uvicorn benchmarks.bench_fastapi:app --host 0.0.0.0 --port 4202 --workers 1 --no-access-log"
run_suite_for_framework "flask" 4203 "gunicorn -w 1 --threads 4 -b 0.0.0.0:4203 benchmarks.bench_flask:app"

echo "=== 5. Consolidando resultados estadisticos ==="
python3 benchmarks/analyze_results.py --results-dir "$RESULTS_DIR"

echo "=== 6. Empaquetando resultados en results_export.zip ==="
zip -r results_export.zip "$RESULTS_DIR"
echo "[LISTO] Sube results_export.zip al chat para actualizar el manuscrito Word v2."
