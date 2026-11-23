param (
    [int]$Threads = 4,
    [int]$Replicas = 3,
    [int]$WarmupSeconds = 3,
    [int]$EchoSeconds = 12,
    [int]$CrudSeconds = 12
)

# Orquestador automatizado para Windows 11 (PowerShell)
# Ejecutar desde la raiz del repositorio MicroFrameworkAPY:
#   powershell -ExecutionPolicy Bypass -File benchmarks\run_benchmarks.ps1 -Threads 4 -Replicas 3

$ErrorActionPreference = "Continue"
$ResultsDir = "results"
New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

$env:DB_URL = if ($env:DB_URL) { $env:DB_URL } else { "mysql+pymysql://root:@127.0.0.1:3306/bench_apy" }
$env:DB_TYPE = if ($env:DB_TYPE) { $env:DB_TYPE } else { "mysql" }
$env:DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "bench_apy" }
$env:DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "127.0.0.1" }
$env:DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "3306" }
$env:DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "root" }
$env:DB_PASS = if ($env:DB_PASS) { $env:DB_PASS } else { "" }

$env:APY_THREADS = "$Threads"
$env:FASTAPI_THREADS = "$Threads"

$PyExe = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }
$UvicornExe = if (Test-Path ".venv\Scripts\uvicorn.exe") { ".venv\Scripts\uvicorn.exe" } else { "uvicorn" }
$WaitressExe = if (Test-Path ".venv\Scripts\waitress-serve.exe") { ".venv\Scripts\waitress-serve.exe" } else { "waitress-serve" }

$K6Config = "benchmarks\k6_config.json"
if (-not (Test-Path $K6Config)) {
    Set-Content -Path $K6Config -Value "{}" -Encoding utf8
}

$WarmupSecs = if ($env:WARMUP_SECS) { [int]$env:WARMUP_SECS } else { $WarmupSeconds }
$EchoSecs = if ($env:ECHO_SECS) { [int]$env:ECHO_SECS } else { $EchoSeconds }
$CrudSecs = if ($env:CRUD_SECS) { [int]$env:CRUD_SECS } else { $CrudSeconds }
$EchoDuration = "${EchoSecs}s"
$CrudDuration = "${CrudSecs}s"
$WarmupDuration = "${WarmupSecs}s"
$EchoMonSecs = $EchoSecs + $WarmupSecs + 8
$CrudMonSecs = $CrudSecs + $WarmupSecs + 8

$VusList = @(50, 100, 200)
$Runs = if ($env:RUNS) { [int]$env:RUNS } else { $Replicas }

Write-Host "=== 1. Registrando versiones exactas ==="
@(
  (Get-Date).ToUniversalTime().ToString("u"),
  (& $PyExe --version),
  (k6 version),
  "--- pip freeze ---",
  (& $PyExe -m pip freeze)
) | Out-File -Encoding utf8 "$ResultsDir\benchmark_versions.txt"

Write-Host "=== 2. Ejecutando 34 pruebas internas de APY ==="
cmd /c "`"$PyExe`" tests\run_tests.py > `"$ResultsDir\apy_unit_tests.txt`" 2>&1"

Write-Host "=== 3. Metricas estaticas de mantenibilidad (E4) ==="
@(
  "=== RADON RAW ===",
  (& $PyExe -m radon raw -s benchmarks\bench_apy.py benchmarks\bench_fastapi.py benchmarks\bench_flask.py),
  "=== RADON CC ===",
  (& $PyExe -m radon cc -a benchmarks\bench_apy.py benchmarks\bench_fastapi.py benchmarks\bench_flask.py),
  "=== RADON MI ===",
  (& $PyExe -m radon mi benchmarks\bench_apy.py benchmarks\bench_fastapi.py benchmarks\bench_flask.py)
) | Out-File -Encoding utf8 "$ResultsDir\radon_maintainability.txt"

Write-Host "=== 4. Poblando base de datos relacional (E2) ==="
& $PyExe benchmarks\schema_seed.py --db-url $env:DB_URL

function Run-FrameworkSuite($Fw, $Port, $Exe, $ArgList) {
  Write-Host "========================================"
  Write-Host "Iniciando $Fw en puerto $Port (Threads=$Threads)"
  Write-Host "========================================"
  $srv = Start-Process -FilePath $Exe -ArgumentList $ArgList -PassThru -NoNewWindow
  Start-Sleep -Seconds 4

  foreach ($Method in @("GET","POST","PUT","DELETE","PATCH")) {
    for ($Run = 1; $Run -le $Runs; $Run++) {
      $Tag = "${Fw}_echo-$($Method.ToLower())_100vu_run${Run}"
      Write-Host "[E1] $Tag"
      $mon = Start-Process -FilePath $PyExe -ArgumentList "benchmarks\monitor_resources.py $($srv.Id) $ResultsDir\${Tag}_res.csv $EchoMonSecs" -PassThru -NoNewWindow
      k6 run -c $K6Config -e "BASE_URL=http://127.0.0.1:${Port}" -e "METHOD=$Method" -e "VUS=100" -e "WARMUP=$WarmupDuration" -e "DURATION=$EchoDuration" --summary-export="$ResultsDir\${Tag}_summary.json" benchmarks\k6_echo.js
      Wait-Process -Id $mon.Id -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 3
    }
  }

  foreach ($Vus in $VusList) {
    for ($Run = 1; $Run -le $Runs; $Run++) {
      $Tag = "${Fw}_crud_${Vus}vu_run${Run}"
      Write-Host "[E2+E3] $Tag"
      $mon = Start-Process -FilePath $PyExe -ArgumentList "benchmarks\monitor_resources.py $($srv.Id) $ResultsDir\${Tag}_res.csv $CrudMonSecs" -PassThru -NoNewWindow
      k6 run -c $K6Config -e "BASE_URL=http://127.0.0.1:${Port}" -e "VUS=$Vus" -e "WARMUP=$WarmupDuration" -e "DURATION=$CrudDuration" --summary-export="$ResultsDir\${Tag}_summary.json" benchmarks\k6_crud.js
      Wait-Process -Id $mon.Id -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 3
    }
  }

  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

$env:APY_PORT = "4201"
Run-FrameworkSuite "apy" 4201 $PyExe "benchmarks\bench_apy.py --threads $Threads"
Run-FrameworkSuite "fastapi" 4202 $UvicornExe "benchmarks.bench_fastapi:app --host 0.0.0.0 --port 4202 --workers 1 --no-access-log"
Run-FrameworkSuite "flask" 4203 $WaitressExe "--host=0.0.0.0 --port=4203 --threads=$Threads benchmarks.bench_flask:app"

Write-Host "=== 5. Consolidando resultados ==="
& $PyExe benchmarks\analyze_results.py --results-dir $ResultsDir

Add-Type -AssemblyName System.IO.Compression.FileSystem
$ZipPath = Join-Path (Get-Location) "results_export.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
[System.IO.Compression.ZipFile]::CreateFromDirectory((Resolve-Path $ResultsDir), $ZipPath)

Write-Host "[LISTO] Sube results_export.zip al chat para actualizar el manuscrito Word v2."
