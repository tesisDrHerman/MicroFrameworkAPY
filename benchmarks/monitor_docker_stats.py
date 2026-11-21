"""Monitor de recursos de contenedores Docker (CPU %, RAM en MB, % RAM) a 1 Hz.
Compatible con Linux, macOS y Windows Docker Desktop.
Uso:
  python3 benchmarks/monitor_docker_stats.py bench_apy results/apy_crud_100vu_run1_res.csv 215
"""

import csv
import re
import subprocess
import sys
import time


def parse_mem_to_mb(mem_str: str) -> float:
    # Ejemplo: "84.5MiB / 1GiB" o "1.02GiB / 2GiB"
    used = mem_str.split("/")[0].strip()
    m = re.match(r"([0-9.]+)\s*([a-zA-Z]+)", used)
    if not m:
        return 0.0
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("g"):
        return round(val * 1024.0, 2)
    if unit.startswith("k"):
        return round(val / 1024.0, 2)
    return round(val, 2)


def monitor_container(container_name: str, out_csv: str, duration_sec: int):
    start = time.time()
    fmt = "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.PIDs}}"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["elapsed_s", "cpu_percent", "rss_mb", "mem_percent", "pids"])
        while time.time() - start < duration_sec:
            t0 = time.time()
            proc = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", fmt, container_name],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                time.sleep(0.5)
                continue
            parts = proc.stdout.strip().split(",")
            if len(parts) >= 4:
                cpu = float(parts[0].replace("%", "").strip() or 0.0)
                rss_mb = parse_mem_to_mb(parts[1])
                mem_pct = float(parts[2].replace("%", "").strip() or 0.0)
                pids = int(parts[3].strip() or 0)
                writer.writerow([round(time.time() - start, 1), cpu, rss_mb, mem_pct, pids])
                f.flush()
            elapsed_step = time.time() - t0
            if elapsed_step < 1.0:
                time.sleep(1.0 - elapsed_step)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python3 monitor_docker_stats.py <CONTAINER_NAME> <OUT_CSV> <DURATION_SEC>")
        sys.exit(1)
    monitor_container(sys.argv[1], sys.argv[2], int(sys.argv[3]))
