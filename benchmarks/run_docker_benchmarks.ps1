# Orquestador 100% contenerizado para Windows (PowerShell + Docker Desktop)
# Requiere: Docker Desktop activo y Docker Compose v2
# Ejecutar desde la raiz del repositorio MicroFrameworkAPY:
#   powershell -ExecutionPolicy Bypass -File benchmarks\run_docker_benchmarks.ps1

param(
    [string]$DbEngine = "mysql"  # "mysql" o "postgres"
)

$ErrorActionPreference = "Stop"
$ResultsDir = "results_${DbEngine}"
New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

$Compose = "docker compose -f benchmarks\docker-compose.yml"
if (Test-Path "benchmarks\.env") {
    $Compose = "$Compose --env-file benchmarks\.env"
}

if ($DbEngine -eq "mysql") {
    $env:DB_TYPE = "mysql"
    $env:DB_HOST = "mysql"
    $env:DB_PORT = "3306"
    $env:DB_NAME = "bench_apy"
    $env:DB_USER = "bench_user"
    $env:DB_PASS = "bench_pass_2026"
    $env:DB_URL  = "mysql+pymysql://${env:DB_USER}:${env:DB_PASS}@mysql:3306/${env:DB_NAME}"
    $DbService   = "mysql"
} elseif ($DbEngine -eq "postgres") {
    $env:DB_TYPE = "postgresql"
    $env:DB_HOST = "postgres"
    $env:DB_PORT = "5432"
    $env:DB_NAME = "bench_apy"
    $env:DB_USER = "bench_user"
    $env:DB_PASS = "bench_pass_2026"
    $env:DB_URL  = "postgresql+psycopg2://${env:DB_USER}:${env:DB_PASS}@postgres:5432/${env:DB_NAME}"
    $DbService   = "postgres"
} else {
    Write-Error "DbEngine debe ser 'mysql' o 'postgres'"
    exit 1
}

$VusList      = @(50, 100, 200)
$Runs         = 3
$EchoDuration = "150s"
$CrudDuration = "180s"

Write-Host "=== 1. Construyendo imagen unificada Python 3.11 ===" -ForegroundColor Cyan
Invoke-Expression "$Compose --profile apy build apy-server"

Write-Host "`n=== 2. Levantando base de datos ($DbService) y esperando healthcheck ===" -ForegroundColor Cyan
Invoke-Expression "$Compose --profile $DbService up -d $DbService"

for ($i = 1; $i -le 30; $i++) {
    $status = (docker inspect -f '{{.State.Health.Status}}' "bench_${DbService}" 2>$null)
    if ($status -eq "healthy") {
        Write-Host "[OK] bench_${DbService} healthy." -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 2
}

Write-Host "`n=== 3. Registrando versiones, radon y poblando BD ===" -ForegroundColor Cyan
Invoke-Expression "$Compose --profile apy run --rm -e DB_URL=`"$env:DB_URL`" apy-server bash -c `"
  python3 --version > /app/${ResultsDir}/benchmark_versions.txt
  pip freeze >> /app/${ResultsDir}/benchmark_versions.txt
  python3 tests/run_tests.py > /app/${ResultsDir}/apy_unit_tests.txt 2>&1 || true
  {
    echo '=== RADON RAW ==='
    radon raw -s benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
    echo '=== RADON CC ==='
    radon cc -a benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
    echo '=== RADON MI ==='
    radon mi benchmarks/bench_apy.py benchmarks/bench_fastapi.py benchmarks/bench_flask.py
  } > /app/${ResultsDir}/radon_maintainability.txt
  python3 benchmarks/schema_seed.py --db-url \`$DB_URL
`""

function Run-ContainerSuite($Fw, $Service, $Container, $Port) {
    Write-Host "`n============================================================" -ForegroundColor Yellow
    Write-Host "Levantando $Container ($DbEngine)" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow

    Invoke-Expression "$Compose --profile $Fw up -d $Service"
    Start-Sleep -Seconds 5

    $cwd = (Get-Location).Path -replace '\\', '/'

    foreach ($Method in @("GET","POST","PUT","DELETE","PATCH")) {
        for ($Run = 1; $Run -le $Runs; $Run++) {
            $tag = "${Fw}_echo-$($Method.ToLower())_100vu_run${Run}"
            Write-Host "[E1] $tag"
            $mon = Start-Process -FilePath "python" -ArgumentList "benchmarks\monitor_docker_stats.py $Container ${ResultsDir}/${tag}_res.csv 185" -PassThru -NoNewWindow
            docker run --rm --network bench_net `
                -v "${cwd}/benchmarks:/scripts:ro" `
                -v "${cwd}/${ResultsDir}:/results" `
                grafana/k6:latest run `
                -e "BASE_URL=http://${Service}:${Port}" `
                -e "METHOD=$Method" `
                -e "VUS=100" `
                -e "DURATION=$EchoDuration" `
                --summary-export="/results/${tag}_summary.json" `
                /scripts/k6_echo.js
            Wait-Process -Id $mon.Id -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 5
        }
    }

    foreach ($Vus in $VusList) {
        for ($Run = 1; $Run -le $Runs; $Run++) {
            $tag = "${Fw}_crud_${Vus}vu_run${Run}"
            Write-Host "[E2+E3] $tag"
            $mon = Start-Process -FilePath "python" -ArgumentList "benchmarks\monitor_docker_stats.py $Container ${ResultsDir}/${tag}_res.csv 215" -PassThru -NoNewWindow
            docker run --rm --network bench_net `
                -v "${cwd}/benchmarks:/scripts:ro" `
                -v "${cwd}/${ResultsDir}:/results" `
                grafana/k6:latest run `
                -e "BASE_URL=http://${Service}:${Port}" `
                -e "VUS=$Vus" `
                -e "DURATION=$CrudDuration" `
                --summary-export="/results/${tag}_summary.json" `
                /scripts/k6_crud.js
            Wait-Process -Id $mon.Id -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 5
        }
    }

    Invoke-Expression "$Compose --profile $Fw stop $Service"
    Invoke-Expression "$Compose --profile $Fw rm -f $Service"
    Start-Sleep -Seconds 3
}

Run-ContainerSuite "apy" "apy-server" "bench_apy" 4201
Run-ContainerSuite "fastapi" "fastapi-server" "bench_fastapi" 4202
Run-ContainerSuite "flask" "flask-server" "bench_flask" 4203

Write-Host "`n=== 4. Consolidando resultados ===" -ForegroundColor Cyan
Invoke-Expression "$Compose --profile apy run --rm apy-server python3 benchmarks/analyze_results.py --results-dir /app/${ResultsDir}"
Compress-Archive -Path "${ResultsDir}\*" -DestinationPath "results_${DbEngine}_docker_export.zip" -Force
Write-Host "`n[LISTO] Sube results_${DbEngine}_docker_export.zip al chat." -ForegroundColor Green
