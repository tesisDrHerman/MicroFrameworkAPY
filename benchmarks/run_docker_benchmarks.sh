#!/usr/bin/env bash
# Orquestador 100% contenerizado (MySQL 8 o PostgreSQL 16 + APY/FastAPI/Flask + Grafana k6)
# Ejecutar desde la raiz del repositorio MicroFrameworkAPY:
#   DB_ENGINE=mysql bash benchmarks/run_docker_benchmarks.sh
#   DB_ENGINE=postgres bash benchmarks/run_docker_benchmarks.sh
set -euo pipefail

DB_ENGINE="${DB_ENGINE:-mysql}"
RESULTS_DIR="results_${DB_ENGINE}"
mkdir -p "$RESULTS_DIR"

COMPOSE="docker compose -f benchmarks/docker-compose.yml"
if [ -f benchmarks/.env ]; then
  COMPOSE="$COMPOSE --env-file benchmarks/.env"
fi

if [ "$DB_ENGINE" = "mysql" ]; then
  export DB_TYPE="mysql"
  export DB_HOST="mysql"
  export DB_PORT="3306"
  export DB_NAME="${MYSQL_DATABASE:-bench_apy}"
  export DB_USER="${MYSQL_USER:-bench_user}"
  export DB_PASS="${MYSQL_PASSWORD:-bench_pass_2026}"
  export DB_URL="mysql+pymysql://${DB_USER}:${DB_PASS}@mysql:3306/${DB_NAME}"
  DB_SERVICE="mysql"
elif [ "$DB_ENGINE" = "postgres" ]; then
  export DB_TYPE="postgresql"
  export DB_HOST="postgres"
  export DB_PORT="5432"
  export DB_NAME="${POSTGRES_DB:-bench_apy}"
  export DB_USER="${POSTGRES_USER:-bench_user}"
  export DB_PASS="${POSTGRES_PASSWORD:-bench_pass_2026}"
  export DB_URL="postgresql+psycopg2://${DB_USER}:${DB_PASS}@postgres:5432/${DB_NAME}"
  DB_SERVICE="postgres"
else
  echo "[ERROR] DB_ENGINE debe ser 'mysql' o 'postgres'"
  exit 1
fi

VUS_LIST="${VUS_LIST:-50 100 200}"
RUNS="${RUNS:-3}"
ECHO_DURATION="${ECHO_DURATION:-150s}"
CRUD_DURATION="${CRUD_DURATION:-180s}"

echo "=== 1. Verificando/Construyendo imagen unificada Python 3.11 ==="
if ! docker image inspect benchmarks-apy-server:latest >/dev/null 2>&1; then
  $COMPOSE --profile apy build apy-server
else
  echo "[OK] Imagen benchmarks-apy-server:latest ya existe. Omitiendo build para proteger disco en t3.micro."
fi

echo "=== 2. Levantando base de datos ($DB_SERVICE) y esperando healthcheck ==="
$COMPOSE --profile "$DB_SERVICE" up -d "$DB_SERVICE"
for i in $(seq 1 30); do
  STATUS=$(docker inspect -f '{{.State.Health.Status}}' "bench_${DB_SERVICE}" 2>/dev/null || echo "starting")
  if [ "$STATUS" = "healthy" ]; then
    echo "[OK] bench_${DB_SERVICE} healthy."
    break
  fi
  sleep 2
done

echo "=== 3. Registrando versiones, 33 pruebas APY, radon (E4) y poblando BD ($DB_ENGINE) ==="
$COMPOSE --profile apy run --rm -e DB_URL="$DB_URL" apy-server bash -c "
  python3 --version > /app/${RESULTS_DIR}/benchmark_versions.txt
  pip freeze >> /app/${RESULTS_DIR}/benchmark_versions.txt
  python3 tests/run_tests.py > /app/${RESULTS_DIR}/apy_unit_tests.txt 2>&1 || true
  {
    echo '=== RADON RAW ==='
    radon raw -s benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
    echo '=== RADON CC ==='
    radon cc -a benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
    echo '=== RADON MI ==='
    radon mi benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
  } > /app/${RESULTS_DIR}/radon_maintainability.txt
  python3 benchmarks/schema_seed.py --db-url "\$DB_URL"
"

PROGRESS_LOG="benchmark_progress.txt"
TOTAL_TESTS=72
CURRENT_TEST=0

log_progress() {
  local MSG="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
  echo "$MSG" | tee -a "$PROGRESS_LOG"
}

run_container_suite() {
  local FW="$1"
  local SERVICE="$2"
  local CONTAINER="$3"
  local PORT="$4"

  log_progress "============================================================"
  log_progress "Levantando $CONTAINER ($DB_ENGINE)"
  log_progress "============================================================"
  $COMPOSE --profile "$FW" up -d "$SERVICE"
  sleep 5

  local MON_ECHO_DUR=$(( ${ECHO_DURATION%s} + 45 ))
  local MON_CRUD_DUR=$(( ${CRUD_DURATION%s} + 45 ))

  # E1: Echo 5 metodos
  for METHOD in GET POST PUT DELETE PATCH; do
    for RUN in $(seq 1 "$RUNS"); do
      CURRENT_TEST=$((CURRENT_TEST + 1))
      local PCT=$(( CURRENT_TEST * 100 / TOTAL_TESTS ))
      local TAG="${FW}_echo-${METHOD,,}_100vu_run${RUN}"
      log_progress "[$CURRENT_TEST/$TOTAL_TESTS - ${PCT}%] Iniciar [E1 Echo] $TAG (duracion: $ECHO_DURATION)"
      python3 benchmarks/monitor_docker_stats.py "$CONTAINER" "${RESULTS_DIR}/${TAG}_res.csv" "$MON_ECHO_DUR" &
      local MON_PID=$!
      docker run --rm --network bench_net \
        -v "$(pwd)/benchmarks:/scripts:ro" \
        -v "$(pwd)/${RESULTS_DIR}:/results" \
        grafana/k6:latest run \
        -e BASE_URL="http://${SERVICE}:${PORT}" \
        -e METHOD="$METHOD" \
        -e VUS=100 \
        -e DURATION="$ECHO_DURATION" \
        --summary-export="/results/${TAG}_summary.json" \
        /scripts/k6_echo.js
      wait "$MON_PID" || true
      log_progress "[$CURRENT_TEST/$TOTAL_TESTS - ${PCT}%] Completado [E1 Echo] $TAG"
      sleep 5
    done
  done

  # E2 + E3: CRUD real con SQL + JOINs
  for VUS in $VUS_LIST; do
    for RUN in $(seq 1 "$RUNS"); do
      CURRENT_TEST=$((CURRENT_TEST + 1))
      local PCT=$(( CURRENT_TEST * 100 / TOTAL_TESTS ))
      local TAG="${FW}_crud_${VUS}vu_run${RUN}"
      log_progress "[$CURRENT_TEST/$TOTAL_TESTS - ${PCT}%] Iniciar [E2+E3 CRUD] $TAG (VUs: $VUS, duracion: $CRUD_DURATION)"
      python3 benchmarks/monitor_docker_stats.py "$CONTAINER" "${RESULTS_DIR}/${TAG}_res.csv" "$MON_CRUD_DUR" &
      local MON_PID=$!
      docker run --rm --network bench_net \
        -v "$(pwd)/benchmarks:/scripts:ro" \
        -v "$(pwd)/${RESULTS_DIR}:/results" \
        grafana/k6:latest run \
        -e BASE_URL="http://${SERVICE}:${PORT}" \
        -e VUS="$VUS" \
        -e DURATION="$CRUD_DURATION" \
        --summary-export="/results/${TAG}_summary.json" \
        /scripts/k6_crud.js
      wait "$MON_PID" || true
      log_progress "[$CURRENT_TEST/$TOTAL_TESTS - ${PCT}%] Completado [E2+E3 CRUD] $TAG"
      sleep 5
    done
  done

  $COMPOSE --profile "$FW" stop "$SERVICE"
  $COMPOSE --profile "$FW" rm -f "$SERVICE"
  sleep 3
}

run_container_suite "apy" "apy-server" "bench_apy" 4201
run_container_suite "fastapi" "fastapi-server" "bench_fastapi" 4202
run_container_suite "flask" "flask-server" "bench_flask" 4203

log_progress "=== 4. Consolidando resultados ==="
$COMPOSE --profile apy run --rm apy-server python3 benchmarks/analyze_results.py --results-dir "/app/${RESULTS_DIR}"
python3 -m zipfile -c "results_${DB_ENGINE}_docker_export.zip" "$RESULTS_DIR"
log_progress "[LISTO] Suite completada con exito. Archivo generado: results_${DB_ENGINE}_docker_export.zip"
