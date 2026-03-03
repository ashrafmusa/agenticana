import subprocess
import time
import json
import sys
from datetime import datetime
from pathlib import Path

# ────────────────────────────────────────────────────────────────
# Agentica P13: The Performance Pulse
# Benchmarks core Agentica scripts for speed and memory footprint.
# Output: .Agentica/logs/performance/pulse_<timestamp>.json
# ────────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# Thresholds
TIME_WARN_MS   = 500    # warn if avg > 500ms
MEMORY_WARN_MB = 100    # warn if peak > 100MB
RUNS = 3                # number of benchmark runs per script


BENCHMARKS = [
    {
        "name": "simulacrum.py",
        "cmd": ["python", "scripts/simulacrum.py",
                "benchmark test topic", "--agents",
                "backend-specialist", "security-auditor", "--rounds", "1"]
    },
    {
        "name": "swarm_dispatcher.py (sequential)",
        "cmd": ["python", "scripts/swarm_dispatcher.py",
                ".Agentica/swarm_manifest.json", "--sequential"]
    },
    {
        "name": "soul_inject.py",
        "cmd": ["python", "scripts/soul_inject.py", "benchmark query"]
    },
    {
        "name": "vector_memory.py",
        "cmd": ["python", "scripts/vector_memory.py"]
    }
]


def get_peak_memory_mb(pid: int) -> float:
    """Approximate peak memory usage using Windows wmic or /proc."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["wmic", "process", "where", f"processid={pid}",
                 "get", "workingsetsize"],
                capture_output=True, text=True
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip().isdigit()]
            if lines:
                return int(lines[0]) / (1024 * 1024)
        else:
            with open(f"/proc/{pid}/status") as f:
                for line in f:
                    if "VmRSS" in line:
                        return int(line.split()[1]) / 1024
    except Exception:
        pass
    return 0.0


def benchmark_script(entry: dict) -> dict:
    """Run a single benchmark multiple times and return stats."""
    name = entry["name"]
    cmd  = entry["cmd"]
    times_ms = []
    peak_mb  = 0.0

    print(f"  {CYAN}[~]{RESET} Benchmarking {BOLD}{name}{RESET}...", end=" ", flush=True)

    for _ in range(RUNS):
        t0 = time.perf_counter()
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Sample memory mid-run
            time.sleep(0.05)
            mem = get_peak_memory_mb(proc.pid)
            peak_mb = max(peak_mb, mem)
            proc.wait(timeout=60)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            times_ms.append(elapsed_ms)
        except subprocess.TimeoutExpired:
            proc.kill()
            times_ms.append(60_000)
        except FileNotFoundError:
            times_ms.append(-1)
            break

    valid_times = [t for t in times_ms if t >= 0]
    avg_ms = sum(valid_times) / len(valid_times) if valid_times else -1

    if avg_ms < 0:
        status = "ERROR"
        color = RED
    elif avg_ms > TIME_WARN_MS or peak_mb > MEMORY_WARN_MB:
        status = "WARN"
        color = YELLOW
    else:
        status = "OPTIMAL"
        color = GREEN

    print(f"{color}[{status}]{RESET}  avg={avg_ms:.0f}ms  peak={peak_mb:.1f}MB")

    return {
        "script": name,
        "avg_time_ms": round(avg_ms, 2),
        "peak_memory_mb": round(peak_mb, 2),
        "runs": RUNS,
        "status": status
    }


def run_pulse() -> list[dict]:
    """Run all benchmarks and save the pulse report."""
    log_dir = Path(".Agentica/logs/performance")
    log_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{YELLOW}{BOLD}=========================================={RESET}")
    print(f"{YELLOW}{BOLD}  PERFORMANCE PULSE -- v5.0.0 A.I.R{RESET}")
    print(f"{YELLOW}{BOLD}  Benchmarking {len(BENCHMARKS)} core scripts ({RUNS} runs each){RESET}")
    print(f"{YELLOW}{BOLD}=========================================={RESET}\n")

    results = []
    for entry in BENCHMARKS:
        result = benchmark_script(entry)
        results.append(result)

    # Summary
    optimal = sum(1 for r in results if r["status"] == "OPTIMAL")
    warns   = sum(1 for r in results if r["status"] == "WARN")
    errors  = sum(1 for r in results if r["status"] == "ERROR")

    report = {
        "timestamp": datetime.now().isoformat(),
        "version": "v5.0.0",
        "summary": {
            "total": len(results),
            "optimal": optimal,
            "warn": warns,
            "error": errors,
            "system_health": "OPTIMAL" if errors == 0 and warns == 0 else
                             "DEGRADED" if warns > 0 else "CRITICAL"
        },
        "results": results
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = log_dir / f"pulse_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n{BOLD}System Health: ", end="")
    health = report["summary"]["system_health"]
    color = GREEN if health == "OPTIMAL" else YELLOW if health == "DEGRADED" else RED
    print(f"{color}{BOLD}{health}{RESET}")
    print(f"  Optimal: {optimal}  |  Warn: {warns}  |  Error: {errors}")
    print(f"  Report >> {report_path}\n")

    return results


if __name__ == "__main__":
    run_pulse()
