#!/usr/bin/env python3
"""
Agentica P24: Guardian Rule DSL Engine
======================================
Loads custom pre-commit rules from .Agentica/guardian_rules.yaml
and evaluates them against staged git files.

Rule types:
  forbid_pattern    — regex must NOT appear in staged files
  require_pattern   — regex MUST appear in specific file types
  require_tests     — each changed .py/.ts file must have a paired test_ file
  min_files_for_pow — if changed files >= N, a PoW attestation must exist
  max_file_size_kb  — no staged file may exceed this size

Severity:
  warn   → prints warning, allows commit
  block  → exits 1, blocks commit

Secretary Bird: rules before stomping. 🦅
"""
import re
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# ── optional yaml import ──────────────────────────────────────────────────────
try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

RULES_FILE   = Path(".Agentica/guardian_rules.yaml")
ATTEST_DIR   = Path(".Agentica/attestations")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_staged_files() -> list[str]:
    r = subprocess.run(
        "git diff --cached --name-only --diff-filter=ACM",
        capture_output=True, text=True, shell=True
    )
    return [f for f in r.stdout.strip().splitlines() if f]


def _read_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _matches_glob(filename: str, patterns: list[str]) -> bool:
    """Simple glob: *.py, *.ts, etc."""
    from fnmatch import fnmatch
    return any(fnmatch(Path(filename).name, p) for p in patterns)


def _pow_exists() -> bool:
    latest = ATTEST_DIR / "latest.json"
    if not latest.exists():
        return False
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        ts_str = data.get("timestamp", "")
        if ts_str:
            ts = datetime.fromisoformat(ts_str)
            age_hours = (datetime.now() - ts).total_seconds() / 3600
            return age_hours < 24   # attestation must be < 24h old
    except Exception:
        pass
    return False


# ── Rule evaluators ───────────────────────────────────────────────────────────

def _eval_forbid_pattern(rule: dict, staged: list[str]) -> tuple[bool, str]:
    pattern    = rule.get("pattern", "")
    applies_to = rule.get("applies_to", ["*"])
    try:
        rx = re.compile(pattern, re.MULTILINE)
    except re.error as e:
        return True, f"Invalid regex '{pattern}': {e}"

    for f in staged:
        if not _matches_glob(f, applies_to):
            continue
        content = _read_file(f)
        m = rx.search(content)
        if m:
            line_no = content[: m.start()].count("\n") + 1
            return False, f"Pattern '{pattern}' found in {f}:{line_no}"
    return True, "Clean"


def _eval_require_pattern(rule: dict, staged: list[str]) -> tuple[bool, str]:
    pattern    = rule.get("pattern", "")
    applies_to = rule.get("applies_to", ["*"])
    try:
        rx = re.compile(pattern, re.MULTILINE)
    except re.error as e:
        return True, f"Invalid regex '{pattern}': {e}"

    for f in staged:
        if not _matches_glob(f, applies_to):
            continue
        content = _read_file(f)
        if not rx.search(content):
            return False, f"Required pattern '{pattern}' missing in {f}"
    return True, "Found"


def _eval_require_tests(rule: dict, staged: list[str]) -> tuple[bool, str]:
    applies_to = rule.get("applies_to", ["*.py", "*.ts"])
    missing = []
    for f in staged:
        if not _matches_glob(f, applies_to):
            continue
        name = Path(f).stem
        if name.startswith("test_") or name.endswith("_test"):
            continue  # is itself a test file
        # Check if a paired test file exists anywhere in the repo
        pairs = list(Path(".").rglob(f"test_{name}.py")) + \
                list(Path(".").rglob(f"{name}.test.ts")) + \
                list(Path(".").rglob(f"{name}.spec.ts"))
        if not pairs:
            missing.append(f)
    if missing:
        return False, f"No test file found for: {', '.join(missing)}"
    return True, "Tests found"


def _eval_min_files_for_pow(rule: dict, staged: list[str]) -> tuple[bool, str]:
    threshold = int(rule.get("threshold", 5))
    if len(staged) >= threshold:
        if not _pow_exists():
            return False, (
                f"{len(staged)} files changed (≥{threshold}). "
                "Run: python scripts/pow_commit.py sign"
            )
    return True, f"{len(staged)} files (threshold: {threshold})"


def _eval_max_file_size(rule: dict, staged: list[str]) -> tuple[bool, str]:
    limit_kb = float(rule.get("threshold_kb", 500))
    for f in staged:
        try:
            size_kb = Path(f).stat().st_size / 1024
            if size_kb > limit_kb:
                return False, f"{f} is {size_kb:.1f}KB (limit: {limit_kb}KB)"
        except Exception:
            pass
    return True, "All files within size limit"


EVALUATORS = {
    "forbid_pattern":    _eval_forbid_pattern,
    "require_pattern":   _eval_require_pattern,
    "require_tests":     _eval_require_tests,
    "min_files_for_pow": _eval_min_files_for_pow,
    "max_file_size_kb":  _eval_max_file_size,
}


# ── Main API ──────────────────────────────────────────────────────────────────

def load_rules() -> list[dict]:
    """Load rules from YAML file. Returns empty list if file missing or yaml not installed."""
    if not RULES_FILE.exists():
        return []
    if not _HAS_YAML:
        print(f"{YELLOW}[P24] PyYAML not installed — skipping custom rules. "
              f"Run: pip install pyyaml{RESET}")
        return []
    try:
        data = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
        return data.get("rules", []) if isinstance(data, dict) else []
    except Exception as e:
        print(f"{YELLOW}[P24] Could not parse guardian_rules.yaml: {e}{RESET}")
        return []


def evaluate_rules(rules: list[dict] | None = None) -> tuple[bool, list[dict]]:
    """
    Evaluate all rules against staged files.
    Returns (all_passed, results_list).
    """
    if rules is None:
        rules = load_rules()
    if not rules:
        return True, []

    staged   = _get_staged_files()
    results  = []
    any_block_failed = False

    for rule in rules:
        rule_id   = rule.get("id", "unnamed")
        rule_type = rule.get("type", "")
        severity  = rule.get("severity", "warn")
        message   = rule.get("message", "")

        evaluator = EVALUATORS.get(rule_type)
        if evaluator is None:
            results.append({
                "id": rule_id, "type": rule_type,
                "passed": True, "severity": severity,
                "output": f"Unknown rule type '{rule_type}' — skipped"
            })
            continue

        passed, detail = evaluator(rule, staged)
        output = message if (not passed and message) else detail

        if not passed and severity == "block":
            any_block_failed = True

        results.append({
            "id":       rule_id,
            "type":     rule_type,
            "passed":   passed,
            "severity": severity,
            "output":   output,
        })

    return (not any_block_failed), results


def print_results(results: list[dict]):
    """Pretty-print evaluation results."""
    for r in results:
        if r["passed"]:
            icon  = f"{GREEN}[PASS]{RESET}"
        elif r["severity"] == "block":
            icon  = f"{RED}[BLOCK]{RESET}"
        else:
            icon  = f"{YELLOW}[WARN]{RESET}"
        print(f"      {icon} {r['id']}: {r['output'][:80]}")


# ── CLI ───────────────────────────────────────────────────────────────────────

STARTER_YAML = """\
# Agenticana P24: Guardian Rule DSL
# ----------------------------------
# Define custom pre-commit rules for your project.
# Each rule has: id, type, severity (warn|block), message, and type-specific options.
# Docs: https://github.com/ashrafmusa/AGENTICANA#p24-guardian-rule-dsl
version: "1.0"

rules:
  - id: no-debug-print
    type: forbid_pattern
    pattern: "^\\\\s*print\\\\(\\\"DEBUG"
    applies_to: ["*.py"]
    severity: warn
    message: "Remove debug print statements before committing."

  - id: pow-on-big-change
    type: min_files_for_pow
    threshold: 5
    severity: block
    message: "5+ files changed — run: python scripts/pow_commit.py sign"

  - id: max-size
    type: max_file_size_kb
    threshold_kb: 500
    severity: block
    message: "File exceeds 500KB. Use Git LFS or split the file."

  # - id: require-tests
  #   type: require_tests
  #   applies_to: ["*.py"]
  #   severity: warn
  #   message: "No paired test file found for changed module."
"""


if __name__ == "__main__":
    import argparse

    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="P24: Guardian Rule DSL Engine")
    parser.add_argument("action", nargs="?",
                        choices=["validate", "init", "list"],
                        default="validate",
                        help="Action: validate (default), init, list")
    args = parser.parse_args()

    if args.action == "init":
        if RULES_FILE.exists():
            print(f"{YELLOW}[P24] {RULES_FILE} already exists. Delete it first to reinit.{RESET}")
        else:
            RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
            RULES_FILE.write_text(STARTER_YAML, encoding="utf-8")
            print(f"{GREEN}[P24] Created {RULES_FILE} with starter rules. Edit to customize.{RESET}")

    elif args.action == "list":
        rules = load_rules()
        if not rules:
            print(f"{YELLOW}[P24] No rules loaded. Run 'init' to create starter rules.{RESET}")
        else:
            print(f"\n{BOLD}Active Guardian Rules ({len(rules)}):{RESET}")
            for r in rules:
                sev_color = RED if r.get("severity") == "block" else YELLOW
                print(f"  {sev_color}[{r.get('severity','warn').upper()}]{RESET} "
                      f"{r.get('id','?')} ({r.get('type','?')})")

    else:  # validate
        print(f"\n{BOLD}[P24] Evaluating custom Guardian rules...{RESET}")
        rules = load_rules()
        if not rules:
            print(f"{YELLOW}  No rules file found at {RULES_FILE}. Skipping.{RESET}")
            sys.exit(0)
        passed, results = evaluate_rules(rules)
        print_results(results)
        if passed:
            print(f"\n{GREEN}[P24] All custom rules passed.{RESET}")
        else:
            blocked = [r["id"] for r in results if not r["passed"] and r["severity"] == "block"]
            print(f"\n{RED}[P24] Blocked by rules: {', '.join(blocked)}{RESET}")
            sys.exit(1)
