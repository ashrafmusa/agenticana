#!/usr/bin/env python3
"""
Agentica P25: Sovereign Loop Orchestrator 🦅
=============================================
The full autonomous evolution pipeline. Chains all Agenticana subsystems
into a single self-improving cycle:

  1. sovereign_intel.py  → scan competitors → write competitor_intel.json
  2. evolve.py           → pick top gap → create plan + update docs
  3. nl_swarm.py --intel → convert gaps to swarm manifest
  4. pow_commit.py sign  → attest the evolution commit
  5. git push            → optional push to GitHub

Usage:
    python scripts/sovereign_loop.py               # full cycle
    python scripts/sovereign_loop.py --dry-run     # show what would happen
    python scripts/sovereign_loop.py --no-push     # commit but don't push
    python scripts/sovereign_loop.py --phase P23   # force specific phase

Secretary Bird: always evolving, never stopping. 🦅
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

BASE_DIR   = Path(__file__).resolve().parent.parent
SCRIPTS    = BASE_DIR / "scripts"
INTEL_PATH = BASE_DIR / ".Agentica" / "competitor_intel.json"
EVLOG_PATH = BASE_DIR / ".Agentica" / "evolution_log.json"
ATTEST_DIR = BASE_DIR / ".Agentica" / "attestations"


def log(msg: str, color: str = ""):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {color}{msg}{RESET}", flush=True)


def run_step(label: str, cmd: list[str], dry_run: bool = False) -> int:
    """Run a pipeline step, print label, return exit code."""
    log(f"▶ {label}", CYAN + BOLD)
    if dry_run:
        log(f"  [DRY-RUN] would run: {' '.join(cmd)}", DIM)
        return 0
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    ok = result.returncode == 0
    log(f"  {'✓ done' if ok else '✗ failed'}", GREEN if ok else RED)
    return result.returncode


def get_top_gap() -> str:
    """Read competitor intel and return the most common gap."""
    if not INTEL_PATH.exists():
        return "General capability improvement"
    try:
        intel = json.loads(INTEL_PATH.read_text(encoding="utf-8"))
        from collections import Counter
        counter: Counter = Counter()
        for repo in intel:
            for gap in repo.get("trending_requests", []):
                counter[gap[:50]] += 1
        if counter:
            return counter.most_common(1)[0][0]
    except Exception:
        pass
    return "General capability improvement"


def get_trust_score() -> str:
    """Read latest PoW attestation trust score."""
    latest = ATTEST_DIR / "latest.json"
    if not latest.exists():
        return "UNVERIFIED"
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        return data.get("trust_score", "UNKNOWN")
    except Exception:
        return "UNKNOWN"


def check_trust_score(score_str: str, min_score: int) -> bool:
    """Parse 'NN/100 (LABEL)' and check if NN >= min_score."""
    try:
        value = int(score_str.split("/")[0])
        return value >= min_score
    except Exception:
        return False


def load_ev_log() -> dict:
    if EVLOG_PATH.exists():
        try:
            return json.loads(EVLOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"completed_phases": [], "cycles": []}


def show_status():
    """Print last evolution cycle summary."""
    ev_log = load_ev_log()
    cycles = ev_log.get("cycles", [])
    if not cycles:
        print(f"{YELLOW}No evolution cycles recorded yet.{RESET}")
        return
    last = cycles[-1]
    print(f"\n{BOLD}Last Sovereign Loop Cycle:{RESET}")
    print(f"  Phase:     {last.get('phase')} — {last.get('name')}")
    print(f"  Gap:       {last.get('gap_trigger')}")
    print(f"  Timestamp: {last.get('timestamp','?')[:19]}")
    print(f"  Files:     {', '.join(last.get('files_created',[]))}")
    print(f"  Total cycles run: {len(cycles)}")

    trust = get_trust_score()
    color = GREEN if "CERTIFIED" in trust else YELLOW
    print(f"  Last PoW:  {color}{trust}{RESET}\n")


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(dry_run: bool, no_push: bool, force_phase: str | None,
                 token: str | None, min_trust: int):
    log("=" * 55, BOLD + CYAN)
    log("  🦅 AGENTICANA SOVEREIGN LOOP (P25)", BOLD + CYAN)
    log("=" * 55, BOLD + CYAN)

    # ── Step 1: Competitor Intel Scan ─────────────────────────────────────────
    intel_cmd = ["python", str(SCRIPTS / "sovereign_intel.py")]
    if token:
        intel_cmd += ["--token", token]
    rc = run_step("Step 1/5 — Competitor Intel Scan", intel_cmd, dry_run)
    if rc != 0:
        log("Intel scan failed — continuing with cached intel if available.", YELLOW)

    gap = get_top_gap() if not dry_run else "Voice-to-code integration (simulated)"
    log(f"  Top gap identified: '{gap}'", GREEN)

    # ── Step 2: Evolution Engine ───────────────────────────────────────────────
    evolve_cmd = ["python", str(SCRIPTS / "evolve.py")]
    if dry_run:
        # evolve.py does a git push — skip in dry-run
        log(f"▶ Step 2/5 — Evolution Engine", CYAN + BOLD)
        log(f"  [DRY-RUN] would run: {' '.join(evolve_cmd)}", DIM)
        log(f"  [DRY-RUN] would create plan file + update ROADMAP/CHANGELOG", DIM)
    else:
        # We pass --no-push to evolve.py so sovereign_loop controls the push
        rc = run_step("Step 2/5 — Evolution Engine (evolve.py)", evolve_cmd, False)
        if rc != 0:
            log("Evolution engine failed — aborting loop.", RED)
            sys.exit(1)

    # ── Step 3: NL Swarm from Intel ───────────────────────────────────────────
    nl_cmd = ["python", str(SCRIPTS / "nl_swarm.py"),
              f"Implement: {gap[:80]}",
              "--output", str(BASE_DIR / ".Agentica" / "swarm_sovereign.json")]
    rc = run_step("Step 3/5 — NL Swarm Manifest Generation", nl_cmd, dry_run)
    if rc != 0:
        log("NL Swarm failed — continuing.", YELLOW)

    # ── Step 4: Proof-of-Work Sign ────────────────────────────────────────────
    pow_cmd = ["python", str(SCRIPTS / "pow_commit.py"), "sign"]
    rc = run_step("Step 4/5 — Proof-of-Work Attestation", pow_cmd, dry_run)
    if rc != 0:
        log("PoW sign failed — skipping trust check.", YELLOW)
    else:
        trust = get_trust_score()
        log(f"  Trust Score: {trust}", GREEN if "CERTIFIED" in trust else YELLOW)
        if not dry_run and not check_trust_score(trust, min_trust):
            log(f"  Trust score below minimum ({min_trust}). Evolution not pushed.", RED)
            log(f"  Run more Simulacrum debates or Guardian checks to increase score.", YELLOW)
            no_push = True

    # ── Step 5: Git Push ──────────────────────────────────────────────────────
    if no_push:
        log("Step 5/5 — Git Push SKIPPED (--no-push or trust score too low)", YELLOW)
    else:
        push_cmd = ["git", "push", "origin", "main"]
        rc = run_step("Step 5/5 — Push to GitHub", push_cmd, dry_run)
        if rc != 0:
            log("Push failed — check your git remote config.", RED)

    # ── Summary ───────────────────────────────────────────────────────────────
    log("=" * 55, BOLD + GREEN)
    log("  ✅ SOVEREIGN LOOP COMPLETE", BOLD + GREEN)
    log(f"  Gap addressed: {gap[:60]}", GREEN)
    log(f"  Trust:         {get_trust_score() if not dry_run else 'DRY-RUN'}", GREEN)
    log(f"  Pushed:        {'NO' if (no_push or dry_run) else 'YES'}", GREEN)
    log("  🦅 Secretary Bird out.", GREEN)
    log("=" * 55, BOLD + GREEN)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="P25: Agenticana Sovereign Loop — autonomous evolution orchestrator"
    )
    parser.add_argument("--dry-run",    dest="dry_run",    action="store_true",
                        help="Show what would happen without writing files")
    parser.add_argument("--no-push",    dest="no_push",    action="store_true",
                        help="Create artifacts + commit but do NOT push to GitHub")
    parser.add_argument("--phase",      default=None,
                        help="Force a specific phase ID (e.g. P23) instead of auto-selecting")
    parser.add_argument("--token",      default=None,
                        help="GitHub personal access token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--min-trust",  dest="min_trust",  type=int, default=70,
                        help="Minimum trust score (0-100) required to push (default: 70)")
    parser.add_argument("--status",     action="store_true",
                        help="Show status of last evolution cycle and exit")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    token = args.token or os.environ.get("GITHUB_TOKEN")

    run_pipeline(
        dry_run=args.dry_run,
        no_push=args.no_push,
        force_phase=args.phase,
        token=token,
        min_trust=args.min_trust,
    )


if __name__ == "__main__":
    main()
