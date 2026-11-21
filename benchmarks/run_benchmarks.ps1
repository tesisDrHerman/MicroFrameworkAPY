# Orquestador automatizado para Windows 11 (PowerShell)
# Ejecutar desde la raiz del repositorio MicroFrameworkAPY:
#   powershell -ExecutionPolicy Bypass -File benchmarks\run_benchmarks.ps1

$ErrorActionPreference = "Stop"
$ResultsDir = "results"
New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

$env:DB_URL = if ($env:DB_URL) { $env:DB_URL } else { "sqlite:///benchmarks_crud.db" }
$env:DB_TYPE = if ($env:DB_TYPE) { $env:DB_TYPE } else { "sqlite" }
$env:DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "benchmarks_crud.db" }

$VusList = @(50, 100, 200)
$Runs = 3
$EchoDuration = "150s"
$CrudDuration = "180s"

Write-Host "=== 1. Registrando versiones exactas ==="
@(
  (Get-Date).ToUniversalTime().ToString("u"),
  (python --version),
  (k6 version),
  "--- pip freeze ---",
  (pip freeze)
) | Out-File -Encoding utf8 "$ResultsDir\benchmark_versions.txt"

Write-Host "=== 2. Ejecutando 33 pruebas internas de APY ==="
python tests\run_tests.py *> "$ResultsDir\apy_unit_tests.txt"

Write-Host "=== 3. Metricas estaticas de mantenibilidad (E4) ==="
@(
  "=== RADON RAW ===",
  (radon raw -s benchmarks\bench_apy.py benchmarks\bench_fastapi.py benchmarks\bench_flask.py),
  "=== RADON CC ===",
  (radon cc -a benchmarks\bench_apy.py benchmarks\bench_fastapi.py benchmarks\bench_flask.py),
  "=== RADON MI ===",
  (radon mi benchmarks\bench_apy.py benchmarks\bench_fastapi.py benchmarks\bench_flask.py)
) | Out-File -Encoding utf8 "$ResultsDir\radon_maintainability.txt"

Write-Host "=== 4. Poblando base de datos relacional (E2) ==="
python benchmarks\schema_seed.py --db-url $env:DB_URL

function Run-FrameworkSuite($Fw, $Port, $Exe, $ArgList) {
  Write-Host "========================================"
  Write-Host "Iniciando $Fw en puerto $Port"
  Write-Host "========================================"
  $srv = Start-Process -FilePath $Exe -ArgumentList $ArgList -PassThru -NoNewWindow
  Start-Sleep -Seconds 4

  foreach ($Method in @("GET","POST","PUT","DELETE","PATCH")) {
    for ($Run = 1; $Run -le $Runs; $Run++) {
      $Tag = "${Fw}_echo-$($Method.ToLower())_100vu_run${Run}"
      Write-Host "[E1] $Tag"
      $mon = Start-Process -FilePath "python" -ArgumentList "benchmarks\monitor_resources.py $($srv.Id) $ResultsDir\${Tag}_res.csv 185" -PassThru -NoNewWindow
      k6 run -e "BASE_URL=http://127.0.0.1:${Port}" -e "METHOD=$Method" -e "VUS=100" -e "DURATION=$EchoDuration" --summary-export="$ResultsDir\${Tag}_summary.json" benchmarks\k6_echo.js
      Wait-Process -Id $mon.Id -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 5
    }
  }

  foreach ($Vus in $VusList) {
    for ($Run = 1; $Run -le $Runs; $Run++) {
      $Tag = "${Fw}_crud_${Vus}vu_run${Run}"
      Write-Host "[E2+E3] $Tag"
      $mon = Start-Process -FilePath "python" -ArgumentList "benchmarks\monitor_resources.py $($srv.Id) $ResultsDir\${Tag}_res.csv 215" -PassThru -NoNewWindow
      k6 run -e "BASE_URL=http://127.0.0.1:${Port}" -e "VUS=$Vus" -e "DURATION=$CrudDuration" --summary-export="$ResultsDir\${Tag}_summary.json" benchmarks\k6_crud.js
      Wait-Process -Id $mon.Id -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 5
    }
  }

  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

$env:APY_PORT = "4201"
Run-FrameworkSuite "apy" 4201 "python" "benchmarks\bench_apy.py"
Run-FrameworkSuite "fastapi" 4202 "uvicorn" "benchmarks.bench_fastapi:app --host 0.0.0.0 --port 4202 --workers 1 --no-access-log"
Run-FrameworkSuite "flask" 4203 "waitress-serve" "--host=0.0.0.0 --port=4203 --threads=4 benchmarks.bench_flask:app"

Write-Host "=== 5. Consolidando resultados ==="
python benchmarks\analyze_results.py --results-dir $ResultsDir
Compress-Archive -Path "$ResultsDir\*" -DestinationPath "results_export.zip" -Force
Write-Host "[LISTO] Sube results_export.zip al chat para actualizar el manuscrito Word v2."
