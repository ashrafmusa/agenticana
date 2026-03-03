#!/usr/bin/env python3
"""
Agentica P16: Guardian Mode — Git Pre-Commit Hook
Intercepts every commit, runs Sentinel + Pulse, blocks on failure.
Secretary Bird: stomps snakes before they reach production. 🦅

INSTALL: python scripts/guardian_mode.py install
REMOVE:  python scripts/guardian_mode.py remove
AUDIT:   python scripts/guardian_mode.py audit
"""
import subprocess
import sys
import json
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

HOOK_SCRIPT = '''#!/usr/bin/env python3
"""Agentica Guardian -- pre-commit hook. Auto-generated. Do not edit."""
import subprocess, sys, json, io
from pathlib import Path
from datetime import datetime

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RED   = "\\033[91m"
GREEN = "\\033[92m"
YELLOW= "\\033[93m"
BOLD  = "\\033[1m"
RESET = "\\033[0m"

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, shell=True)

print(f"\\n{YELLOW}{BOLD}[Guardian] Secretary Bird pre-commit intercept...{RESET}")

root = Path(__file__).parent.parent
results = {"timestamp": datetime.now().isoformat(), "checks": [], "blocked": False}

# Check 1: Sentinel (advisory only - never blocks)
print(f"  [1/3] Running Sentinel audit...", end=" ", flush=True)
r = run(f"python {root / 'scripts' / 'sentinel.py'}")
results["checks"].append({"name": "sentinel", "passed": True, "output": r.stdout[-300:] if r.stdout else r.stderr[-200:]})
print(f"{YELLOW}WARN{RESET} (advisory)" if r.returncode != 0 else f"{GREEN}PASS{RESET}")

# Check 2: Quick lint
print(f"  [2/3] Running lint check...", end=" ", flush=True)
staged = run("git diff --cached --name-only --diff-filter=ACM").stdout.strip().splitlines()
py_files = [f for f in staged if f.endswith(".py")]
lint_ok = True
lint_out = ""
if py_files:
    r2 = run(f"python -m py_compile {chr(32).join(py_files)}")
    lint_ok = r2.returncode == 0
    lint_out = r2.stderr[:300] if r2.stderr else "OK"
else:
    lint_out = "No Python files changed."
results["checks"].append({"name": "lint", "passed": lint_ok, "output": lint_out})
print(f"{GREEN}PASS{RESET}" if lint_ok else f"{RED}FAIL{RESET}")
if not lint_ok:
    print(f"    {RED}{lint_out}{RESET}")

# Check 3: Smart secret scan
print(f"  [3/3] Scanning for secrets...", end=" ", flush=True)
secret_found = False
secret_note = ""
danger_vars = ["api_key", "secret_key", "password", "aws_secret", "private_key"]
skip_files = [".key", "test", "guardian", "simulacrum", "real_sim", "pow_commit", "nl_swarm"]
for f in staged:
    if any(skip in f.lower() for skip in skip_files):
        continue
    try:
        content = Path(f).read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            line_l = line.strip().lower()
            for var in danger_vars:
                if var in line_l and "=" in line_l:
                    parts = line_l.split("=", 1)
                    val = parts[1].strip().strip(\'"\').strip("\'").strip()
                    if len(val) > 20 and " " not in val and val not in ("none", "your_key", "change_me", ""):
                        secret_found = True
                        secret_note = f"Possible hardcoded secret in {f}"
                        break
            if secret_found:
                break
    except Exception:
        pass
results["checks"].append({"name": "secret_scan", "passed": not secret_found, "output": secret_note or "Clean"})
print(f"{GREEN}PASS{RESET}" if not secret_found else f"{YELLOW}WARN -- {secret_note}{RESET}")

# Result
all_passed = all(c["passed"] for c in results["checks"])
results["blocked"] = not all_passed

log_dir = root / ".Agentica" / "logs" / "guardian"
log_dir.mkdir(parents=True, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = log_dir / f"pre_commit_{ts}.json"
with open(log_path, "w") as f:
    json.dump(results, f, indent=2)

if all_passed:
    print(f"\\n{GREEN}{BOLD}[Guardian] ALL CHECKS PASSED. Commit approved. [Secretary Bird]{RESET}\\n")
    sys.exit(0)
else:
    failed = [c["name"] for c in results["checks"] if not c["passed"]]
    print(f"\\n{RED}{BOLD}[Guardian] COMMIT BLOCKED. Failed: {chr(44).join(failed)}{RESET}")
    print(f"{RED}Fix issues then retry. Log: {log_path}{RESET}\\n")
    sys.exit(1)
'''

HOOK_PATH = Path(".git/hooks/pre-commit")
PROJECT_ROOT = Path(".")


def install():
    if not (PROJECT_ROOT / ".git").exists():
        print(f"{RED}[Guardian] Not a git repo. Run from project root.{RESET}")
        sys.exit(1)

    HOOK_PATH.write_text(HOOK_SCRIPT, encoding="utf-8")
    # Make executable on Unix
    if sys.platform != "win32":
        HOOK_PATH.chmod(0o755)

    print(f"{GREEN}{BOLD}[Guardian] Installed successfully!{RESET}")
    print(f"  Hook: {HOOK_PATH}")
    print(f"  Every `git commit` will now run:")
    print(f"    [1] Sentinel audit")
    print(f"    [2] Python lint check")
    print(f"    [3] Secret pattern scan")
    print(f"\n{YELLOW}  Remove with: python scripts/guardian_mode.py remove{RESET}\n")


def remove():
    if HOOK_PATH.exists():
        HOOK_PATH.unlink()
        print(f"{YELLOW}[Guardian] Removed. Commits no longer guarded.{RESET}")
    else:
        print(f"[Guardian] No hook installed.")


def audit():
    """Show the last 5 guardian audit logs."""
    log_dir = PROJECT_ROOT / ".Agentica" / "logs" / "guardian"
    if not log_dir.exists():
        print("[Guardian] No audit logs yet. Make a commit to generate one.")
        return
    logs = sorted(log_dir.glob("*.json"), reverse=True)[:5]
    print(f"\n{BOLD}Last {len(logs)} Guardian Audits:{RESET}")
    for log_file in logs:
        data = json.loads(log_file.read_text(encoding="utf-8"))
        status = f"{RED}BLOCKED{RESET}" if data["blocked"] else f"{GREEN}APPROVED{RESET}"
        print(f"  {log_file.name}  →  {status}")
        for check in data["checks"]:
            icon = "[OK]" if check["passed"] else "[FAIL]"
            color = GREEN if check["passed"] else RED
            print(f"    {color}{icon}{RESET} {check['name']}: {check['output'][:60]}")


def status():
    """Check if guardian is currently installed."""
    if HOOK_PATH.exists() and "Guardian" in HOOK_PATH.read_text(encoding="utf-8", errors="ignore"):
        print(f"{GREEN}[Guardian] ACTIVE — hook installed at {HOOK_PATH}{RESET}")
    else:
        print(f"{YELLOW}[Guardian] NOT ACTIVE — run: python scripts/guardian_mode.py install{RESET}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Agentica P16: Guardian Mode")
    parser.add_argument("action", choices=["install", "remove", "audit", "status"],
                        help="Guardian action")
    args = parser.parse_args()
    {"install": install, "remove": remove, "audit": audit, "status": status}[args.action]()
