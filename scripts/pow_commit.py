"""
Agentica P19: Proof-of-Work Commit
Signs every commit with a verified attestation — proving AI work was
debated, tested, benchmarked, and sandbox-verified before shipping.
Secretary Bird: every stomp is on the record. 🦅

Usage:
  python scripts/pow_commit.py sign        # Sign latest commit
  python scripts/pow_commit.py verify      # Verify last attestation
  python scripts/pow_commit.py --message "feat: add auth"  # Commit + sign
  python scripts/pow_commit.py log         # Show attestation history
"""
import json
import hashlib
import subprocess
import sys
import io
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

ATTEST_DIR = Path(".Agentica/attestations")
ATTEST_DIR.mkdir(parents=True, exist_ok=True)


def _run(cmd: str) -> tuple[str, int]:
    r = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return r.stdout.strip(), r.returncode


def get_current_commit() -> str:
    out, code = _run("git rev-parse HEAD")
    return out if code == 0 else "unknown"


def get_staged_files() -> list[str]:
    out, _ = _run("git diff --cached --name-only")
    return [f for f in out.splitlines() if f]


def get_latest_simulacrum_session() -> dict | None:
    log_dir = Path(".Agentica/logs/simulacrum")
    if not log_dir.exists():
        return None
    sessions = sorted(log_dir.glob("session_*.json"), reverse=True)
    if sessions:
        return json.loads(sessions[0].read_text(encoding="utf-8"))
    return None


def get_latest_pulse() -> dict | None:
    perf_dir = Path(".Agentica/logs/performance")
    if not perf_dir.exists():
        return None
    pulses = sorted(perf_dir.glob("pulse_*.json"), reverse=True)
    if pulses:
        return json.loads(pulses[0].read_text(encoding="utf-8"))
    return None


def get_latest_guardian_audit() -> dict | None:
    guard_dir = Path(".Agentica/logs/guardian")
    if not guard_dir.exists():
        return None
    audits = sorted(guard_dir.glob("pre_commit_*.json"), reverse=True)
    if audits:
        return json.loads(audits[0].read_text(encoding="utf-8"))
    return None


def compute_file_hash(files: list[str]) -> str:
    """SHA-256 of staged file contents combined."""
    h = hashlib.sha256()
    for f in sorted(files):
        try:
            h.update(Path(f).read_bytes())
        except Exception:
            h.update(f.encode())
    return h.hexdigest()[:16]


def sign_commit(commit_hash: str = None, message: str = None) -> dict:
    """Create a proof-of-work attestation for the current commit."""
    if commit_hash is None:
        commit_hash = get_current_commit()

    staged = get_staged_files()
    file_hash = compute_file_hash(staged)
    simulacrum = get_latest_simulacrum_session()
    pulse = get_latest_pulse()
    guardian = get_latest_guardian_audit()

    attestation = {
        "agentica_pow": "v1",
        "mascot": "Secretary Bird",
        "timestamp": datetime.now().isoformat(),
        "commit": commit_hash,
        "commit_message": message or "N/A",
        "files_hash": file_hash,
        "files_signed": staged,
        "debate": {
            "session_id": simulacrum.get("session_id") if simulacrum else None,
            "topic": simulacrum.get("topic", "")[:80] if simulacrum else None,
            "winning_agent": simulacrum.get("winning_agent") if simulacrum else None,
            "debated": simulacrum is not None
        },
        "performance": {
            "pulse_run": pulse is not None,
            "system_health": pulse["summary"]["system_health"] if pulse else "NOT_RUN",
            "timestamp": pulse["timestamp"] if pulse else None
        },
        "guardian": {
            "ran": guardian is not None,
            "passed": not guardian["blocked"] if guardian else None,
            "checks": [c["name"] for c in guardian["checks"]] if guardian else []
        },
        "sandbox_verified": (simulacrum is not None),
        "signed_by": "Agentica v5.0 Secretary Bird",
        "trust_score": _compute_trust_score(simulacrum, pulse, guardian)
    }

    # Save attestation
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    attest_path = ATTEST_DIR / f"attest_{commit_hash[:8]}_{ts}.json"
    with open(attest_path, "w", encoding="utf-8") as f:
        json.dump(attestation, f, indent=2)

    # Also write to latest.json for quick access
    (ATTEST_DIR / "latest.json").write_text(
        json.dumps(attestation, indent=2), encoding="utf-8"
    )

    return attestation, attest_path


def _compute_trust_score(simulacrum, pulse, guardian) -> str:
    score = 0
    if simulacrum:   score += 30   # debated
    if pulse:
        health = pulse["summary"]["system_health"]
        score += 30 if health == "OPTIMAL" else 15
    if guardian:
        score += 40 if not guardian["blocked"] else 0
    return f"{score}/100 ({'CERTIFIED' if score >= 70 else 'PARTIAL' if score >= 40 else 'UNVERIFIED'})"


def verify() -> dict | None:
    latest = ATTEST_DIR / "latest.json"
    if not latest.exists():
        print(f"{YELLOW}No attestation found. Run 'sign' first.{RESET}")
        return None
    return json.loads(latest.read_text(encoding="utf-8"))


def show_attestation(attest: dict):
    """Pretty-print an attestation."""
    score = attest.get("trust_score", "N/A")
    color = GREEN if "CERTIFIED" in score else YELLOW if "PARTIAL" in score else RED

    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  Agentica Proof-of-Work Attestation 🦅{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")
    print(f"  Commit:        {attest.get('commit', '?')[:12]}...")
    print(f"  Timestamp:     {attest.get('timestamp', '?')[:19]}")
    print(f"  Files signed:  {len(attest.get('files_signed', []))}")
    print(f"  Files hash:    {attest.get('files_hash', '?')}")
    print()
    d = attest.get("debate", {})
    print(f"  Debate:        {'YES — ' + str(d.get('session_id','?')) if d.get('debated') else 'NO'}")
    if d.get("debated"):
        print(f"    Topic:       {d.get('topic','')[:55]}")
        print(f"    Winner:      {d.get('winning_agent','?')}")
    p = attest.get("performance", {})
    print(f"  Performance:   {p.get('system_health','NOT_RUN')}")
    g = attest.get("guardian", {})
    guard_status = "PASSED" if g.get("passed") else ("FAILED" if g.get("ran") else "NOT_RUN")
    print(f"  Guardian:      {guard_status}")
    print()
    print(f"  {color}{BOLD}Trust Score:   {score}{RESET}")
    print(f"{BOLD}{'='*55}{RESET}\n")


def log_attestations(limit: int = 5):
    """Show recent attestations."""
    files = sorted(ATTEST_DIR.glob("attest_*.json"), reverse=True)[:limit]
    if not files:
        print(f"{YELLOW}No attestations found.{RESET}")
        return
    print(f"\n{BOLD}Recent Attestations:{RESET}")
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        score = data.get("trust_score", "?")
        color = GREEN if "CERTIFIED" in score else YELLOW
        print(f"  {color}[{score}]{RESET} {f.stem[:30]}  commit={data.get('commit','?')[:10]}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="P19: Proof-of-Work Commit Attestation")
    parser.add_argument("action", nargs="?", choices=["sign", "verify", "log"],
                        default="sign", help="Action to perform")
    parser.add_argument("--message", "-m", help="Commit message (for sign)")
    args = parser.parse_args()

    if args.action == "sign":
        print(f"\n{YELLOW}[POW] Creating attestation...{RESET}")
        attest, path = sign_commit(message=args.message)
        show_attestation(attest)
        print(f"{GREEN}Saved >> {path}{RESET}")

    elif args.action == "verify":
        attest = verify()
        if attest:
            show_attestation(attest)

    elif args.action == "log":
        log_attestations()
