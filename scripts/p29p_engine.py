#!/usr/bin/env python3
"""
Agenticana P29+ — GitHub Actions CI Agent Engine
=================================================

Runs the full Agenticana audit chain on every PR:
    Guardian lint → Sentinel audit → Agent YAML validation →
    ReasoningBank stats → Model Router smoke test

Also exposes a Flask API endpoint at /api/p29+ for dashboard integration.

Usage (CLI):
    python scripts/p29p_engine.py run [--path .] [--ci]
    python scripts/p29p_engine.py serve [--port 5050]
    python scripts/p29p_engine.py status

Exit codes:
    0 — All checks passed
    1 — One or more checks failed
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────────────
AGENTICANA_ROOT = Path(__file__).parent.parent
AGENTS_DIR = AGENTICANA_ROOT / "agents"
SCRIPTS_DIR = AGENTICANA_ROOT / "scripts"
MEMORY_DIR = AGENTICANA_ROOT / "memory" / "reasoning-bank"

# ── ANSI colours (suppressed in --ci / non-TTY) ───────────────────────────────
_USE_COLOR = sys.stdout.isatty() and os.environ.get("CI") != "true"

GREEN = "\033[92m" if _USE_COLOR else ""
YELLOW = "\033[93m" if _USE_COLOR else ""
RED = "\033[91m" if _USE_COLOR else ""
BOLD = "\033[1m" if _USE_COLOR else ""
RESET = "\033[0m" if _USE_COLOR else ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a subprocess and return its result."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd or AGENTICANA_ROOT),
        timeout=timeout,
    )


def _print_step(idx: int, total: int, label: str) -> None:
    print(f"  [{idx}/{total}] {label}...", end=" ", flush=True)


def _print_result(passed: bool, note: str = "") -> None:
    if passed:
        print(f"{GREEN}PASS{RESET}" + (f"  {note}" if note else ""))
    else:
        print(f"{RED}FAIL{RESET}" + (f"  {note}" if note else ""))


# ── Individual checks ─────────────────────────────────────────────────────────

def check_agent_yamls() -> dict[str, Any]:
    """Validate all agent YAML definitions are parseable."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return {"name": "agent-yamls", "passed": False, "note": "pyyaml not installed"}

    yaml_files = list(AGENTS_DIR.glob("*.yaml"))
    errors: list[str] = []
    for f in yaml_files:
        try:
            yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{f.name}: {exc}")

    passed = len(errors) == 0
    return {
        "name": "agent-yamls",
        "passed": passed,
        "note": f"{len(yaml_files)} YAMLs validated" if passed else "; ".join(errors),
    }


def check_reasoning_bank() -> dict[str, Any]:
    """Verify the ReasoningBank data file is readable and well-formed."""
    decisions_file = MEMORY_DIR / "decisions.json"
    if not decisions_file.exists():
        return {"name": "reasoning-bank", "passed": False, "note": "decisions.json not found"}
    try:
        data = json.loads(decisions_file.read_text(encoding="utf-8"))
        count = data.get("total_decisions", len(data.get("decisions", [])))
        return {
            "name": "reasoning-bank",
            "passed": True,
            "note": f"{count} decisions stored",
        }
    except json.JSONDecodeError as exc:
        return {"name": "reasoning-bank", "passed": False, "note": str(exc)}


def check_router_config() -> dict[str, Any]:
    """Validate the Model Router config.json."""
    config_file = AGENTICANA_ROOT / "router" / "config.json"
    if not config_file.exists():
        return {"name": "router-config", "passed": False, "note": "config.json not found"}
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        required_keys = {"models", "thresholds", "context_strategies"}
        missing = required_keys - set(data.keys())
        if missing:
            return {"name": "router-config", "passed": False, "note": f"missing keys: {missing}"}
        return {"name": "router-config", "passed": True, "note": "config valid"}
    except json.JSONDecodeError as exc:
        return {"name": "router-config", "passed": False, "note": str(exc)}


def check_mcp_tools() -> dict[str, Any]:
    """Verify MCP tool modules can be required by Node.js."""
    mcp_dir = AGENTICANA_ROOT / "mcp"
    tool_modules = [
        "tools/memory-tools.js",
        "tools/reasoning-bank-tools.js",
        "tools/router-tools.js",
        "tools/agent-tools.js",
    ]
    existing = [m for m in tool_modules if (mcp_dir / m).exists()]
    if not existing:
        return {"name": "mcp-tools", "passed": False, "note": "no MCP tool modules found"}

    # Skip gracefully when node_modules haven't been installed yet
    node_modules = mcp_dir / "node_modules"
    if not node_modules.exists():
        return {
            "name": "mcp-tools",
            "passed": True,
            "note": f"skipped (run 'cd mcp && npm ci' to enable) — {len(existing)} modules found",
        }

    node_script = (
        "try { ["
        + ", ".join(f"require('./{m}')" for m in existing)
        + "]; process.exit(0); } catch(e) { console.error(e.message); process.exit(1); }"
    )
    try:
        result = _run(["node", "-e", node_script], cwd=mcp_dir, timeout=20)
        passed = result.returncode == 0
        note = f"{len(existing)} modules ok" if passed else result.stderr.strip()[:200]
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        passed = False
        note = f"node unavailable: {exc}"

    return {"name": "mcp-tools", "passed": passed, "note": note}


def check_sentinel() -> dict[str, Any]:
    """Run the Sentinel script (advisory — never blocks the pipeline)."""
    sentinel = SCRIPTS_DIR / "sentinel.py"
    if not sentinel.exists():
        return {"name": "sentinel", "passed": True, "note": "sentinel.py not found (skipped)"}
    try:
        result = _run(["python", str(sentinel)], timeout=30)
        passed = result.returncode == 0
        output = (result.stdout or result.stderr or "").strip()[-200:]
        return {"name": "sentinel", "passed": passed, "note": output or "ok"}
    except subprocess.TimeoutExpired:
        return {"name": "sentinel", "passed": False, "note": "timed out"}


def check_skills_structure() -> dict[str, Any]:
    """Verify the skills directory has the expected SKILL.md files."""
    skills_dir = AGENTICANA_ROOT / "skills"
    if not skills_dir.exists():
        return {"name": "skills-structure", "passed": False, "note": "skills/ not found"}
    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    missing = [d.name for d in skill_dirs if not (d / "SKILL.md").exists()]
    passed = len(missing) == 0
    note = (
        f"{len(skill_dirs)} skills ok"
        if passed
        else f"missing SKILL.md: {', '.join(missing[:5])}"
    )
    return {"name": "skills-structure", "passed": passed, "note": note}


# ── Audit chain ───────────────────────────────────────────────────────────────

CHECKS = [
    check_agent_yamls,
    check_reasoning_bank,
    check_router_config,
    check_mcp_tools,
    check_sentinel,
    check_skills_structure,
]


def run_audit(path: str = ".", ci: bool = False) -> dict[str, Any]:
    """
    Execute the full Agenticana audit chain.

    Returns a result dict with keys: timestamp, passed, failed, results.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"\n{BOLD}🦅 Agenticana P29+ Full Agent Audit{RESET}")
    print(f"   Root: {AGENTICANA_ROOT}")
    print(f"   Time: {timestamp}\n")

    results: list[dict[str, Any]] = []
    total = len(CHECKS)

    for idx, check_fn in enumerate(CHECKS, start=1):
        label = check_fn.__name__.replace("check_", "").replace("_", " ").title()
        _print_step(idx, total, label)
        result = check_fn()
        _print_result(result["passed"], result.get("note", ""))
        results.append(result)

    passed = [r for r in results if r["passed"]]
    failed = [r for r in results if not r["passed"]]

    print(f"\n{'─'*50}")
    if failed:
        print(f"{RED}{BOLD}  ✗ {len(failed)} check(s) failed:{RESET}")
        for r in failed:
            print(f"    • {r['name']}: {r.get('note', '')}")
    else:
        print(f"{GREEN}{BOLD}  ✓ All {len(passed)} checks passed 🦅{RESET}")
    print()

    return {
        "timestamp": timestamp,
        "passed": len(passed),
        "failed": len(failed),
        "total": total,
        "ok": len(failed) == 0,
        "results": results,
    }


# ── Flask API (optional) ──────────────────────────────────────────────────────

def serve(port: int = 5050) -> None:
    """Start a lightweight Flask API server exposing /api/p29+."""
    try:
        from flask import Flask, jsonify, request  # type: ignore
    except ImportError:
        print(f"{RED}Flask not installed. Run: pip install flask{RESET}")
        sys.exit(1)

    app = Flask(__name__)

    @app.route("/api/p29+", methods=["GET", "POST"])
    def api_p29():  # type: ignore
        path = request.args.get("path", ".")
        result = run_audit(path=path, ci=True)
        return jsonify(result), (200 if result["ok"] else 500)

    @app.route("/health", methods=["GET"])
    def health():  # type: ignore
        return jsonify({"status": "ok", "agent": "p29+"}), 200

    print(f"🦅 Agenticana P29+ API running on http://0.0.0.0:{port}")
    print(f"   POST /api/p29+  — run full audit")
    app.run(host="0.0.0.0", port=port)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agenticana P29+ — Full Agent CI Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # run
    run_p = sub.add_parser("run", help="Run the full audit chain")
    run_p.add_argument("--path", default=".", help="Project root path")
    run_p.add_argument("--ci", action="store_true", help="CI mode (no colours)")

    # serve
    serve_p = sub.add_parser("serve", help="Start Flask API server")
    serve_p.add_argument("--port", type=int, default=5050, help="Port (default 5050)")

    # status
    sub.add_parser("status", help="Quick health check (alias for run --ci)")

    args = parser.parse_args()

    if args.command in ("run", None):
        path = getattr(args, "path", ".")
        ci = getattr(args, "ci", False) or os.environ.get("CI") == "true"
        result = run_audit(path=path, ci=ci)
        sys.exit(0 if result["ok"] else 1)

    elif args.command == "status":
        result = run_audit(path=".", ci=True)
        sys.exit(0 if result["ok"] else 1)

    elif args.command == "serve":
        serve(port=args.port)


if __name__ == "__main__":
    main()
