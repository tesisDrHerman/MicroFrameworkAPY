"""Consolida todos los archivos *_summary.json de Grafana k6 y *_res.csv de psutil
en tablas listas para el manuscrito (Media, P50, P95, P99, IC 95%, req/s, total requests, error %, CPU y RAM).
Uso:
  python benchmarks/analyze_results.py --results-dir results
"""

import argparse
import glob
import json
import os
import numpy as np
import pandas as pd
from scipy import stats


def ci95(arr):
    arr = np.asarray(arr, dtype=float)
    if len(arr) < 2:
        return 0.0
    return float(stats.t.ppf(0.975, len(arr) - 1) * stats.sem(arr))


def main(results_dir: str):
    rows = []
    for path in sorted(glob.glob(os.path.join(results_dir, "*_summary.json"))):
        name = os.path.basename(path).replace("_summary.json", "")
        parts = name.split("_")
        # Formato esperado: <framework>_<scenario>_<vus>vu_run<N>
        fw = parts[0]
        scenario = "_".join(parts[1:-2])
        vus = parts[-2]
        run = parts[-1]

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        m = data.get("metrics", {})
        dur = m.get("http_req_duration", {})
        reqs = m.get("http_reqs", {})
        failed = m.get("http_req_failed", {})

        res_csv = path.replace("_summary.json", "_res.csv")
        cpu_mean = ram_mean = ram_max = np.nan
        if os.path.exists(res_csv):
            df_r = pd.read_csv(res_csv)
            if not df_r.empty:
                cpu_mean = df_r["cpu_percent"].mean()
                ram_mean = df_r["rss_mb"].mean()
                ram_max = df_r["rss_mb"].max()

        rows.append(
            {
                "framework": fw,
                "scenario": scenario,
                "vus": vus,
                "run": run,
                "total_reqs": reqs.get("count", 0),
                "rps": reqs.get("rate", 0.0),
                "error_rate_pct": failed.get("value", 0.0) * 100.0,
                "mean_ms": dur.get("avg", np.nan),
                "p50_ms": dur.get("med", np.nan),
                "p95_ms": dur.get("p(95)", np.nan),
                "p99_ms": dur.get("p(99)", np.nan),
                "cpu_mean_pct": cpu_mean,
                "ram_mean_mb": ram_mean,
                "ram_peak_mb": ram_max,
            }
        )

    if not rows:
        print("[WARN] No se encontraron archivos *_summary.json en", results_dir)
        return

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(results_dir, "all_runs_detailed.csv"), index=False)

    agg_rows = []
    for (fw, scenario, vus), g in df.groupby(["framework", "scenario", "vus"]):
        agg_rows.append(
            {
                "framework": fw,
                "scenario": scenario,
                "vus": vus,
                "runs": len(g),
                "total_reqs_mean": round(g["total_reqs"].mean(), 1),
                "rps_mean": round(g["rps"].mean(), 2),
                "rps_ci95": round(ci95(g["rps"]), 2),
                "error_pct_mean": round(g["error_rate_pct"].mean(), 4),
                "mean_ms": round(g["mean_ms"].mean(), 2),
                "mean_ms_ci95": round(ci95(g["mean_ms"]), 2),
                "p50_ms": round(g["p50_ms"].mean(), 2),
                "p95_ms": round(g["p95_ms"].mean(), 2),
                "p99_ms": round(g["p99_ms"].mean(), 2),
                "cpu_mean_pct": round(g["cpu_mean_pct"].mean(), 2),
                "ram_mean_mb": round(g["ram_mean_mb"].mean(), 2),
                "ram_peak_mb": round(g["ram_peak_mb"].max(), 2),
            }
        )

    df_agg = pd.DataFrame(agg_rows)
    out_csv = os.path.join(results_dir, "summary_for_manuscript.csv")
    df_agg.to_csv(out_csv, index=False)
    print(f"[OK] Resumen consolidado guardado en: {out_csv}")
    print(df_agg.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()
    main(args.results_dir)
