"""Monitor de recursos (CPU %, RAM RSS en MB, sockets TCP abiertos, hilos) a 1 Hz.
Uso:
  python benchmarks/monitor_resources.py <PID> results/apy_crud_100vu_run1_res.csv 215
"""

import csv
import sys
import time
import psutil


def monitor(pid: int, out_csv: str, duration_sec: int):
    proc = psutil.Process(pid)
    proc.cpu_percent(interval=None)
    start = time.time()

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["elapsed_s", "cpu_percent", "rss_mb", "open_sockets", "num_threads"])
        while time.time() - start < duration_sec:
            try:
                cpu = proc.cpu_percent(interval=1.0)
                rss_mb = proc.memory_info().rss / (1024 * 1024)
                try:
                    sockets = len(proc.net_connections(kind="inet"))
                except Exception:
                    sockets = -1
                threads = proc.num_threads()
                writer.writerow([round(time.time() - start, 1), round(cpu, 2), round(rss_mb, 2), sockets, threads])
                f.flush()
            except psutil.NoSuchProcess:
                break


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python monitor_resources.py <PID> <OUT_CSV> <DURATION_SEC>")
        sys.exit(1)
    monitor(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]))
