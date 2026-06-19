import argparse
import subprocess
import sys
import io
import os
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ────────────────────────────────────────────────────────────────
# Agentica CLI v2 — The Sovereign Command Interface
# Version: v5.0.0 (A.I.R. Edition)
# ────────────────────────────────────────────────────────────────

VERSION = "v5.0.0"
SCRIPTS = Path(__file__).parent

HEADER = f"""
  ___                    _   _
 / _ \\  __ _  ___ _ __ | |_(_) ___ __ _
| | | |/ _` |/ _ \\ '_ \\| __| |/ __/ _` |
| |_| | (_| |  __/ | | | |_| | (_| (_| |
 \\__\\_\\\\__, |\\___|_| |_|\\__|_|\\___\\__,_|
        |___/  {VERSION} A.I.R. Edition
"""

GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def _run(cmd: list[str], cwd: str = ".") -> int:
    """Delegate to a subprocess and return exit code."""
    return subprocess.run(cmd, cwd=cwd).returncode


# ── Sub-command handlers ──────────────────────────────────────────

def cmd_swarm(args):
    """Dispatch a Swarm Manifest."""
    flags = []
    if args.shadow:
        flags.append("--shadow")
    if args.sequential:
        flags.append("--sequential")
    if args.dry_run:
        flags.append("--dry-run")
    return _run(["python", str(SCRIPTS / "swarm_dispatcher.py"), args.manifest] + flags)


def cmd_sentinel(args):
    """Run the Self-Healing Sentinel."""
    return _run(["python", str(SCRIPTS / "sentinel.py")])


def cmd_dashboard(args):
    """Start the Control Center Dashboard API."""
    print(f"{CYAN}[*] Starting Agentica Control Center on http://127.0.0.1:{args.port}...{RESET}")
    env = os.environ.copy()
    env["AGENTICA_PORT"] = str(args.port)
    return subprocess.run(
        ["python", str(SCRIPTS / "dashboard_api.py")], env=env
    ).returncode


def cmd_bridge(args):
    """Sync Soul Memory across all bridge projects."""
    return _run(["python", str(SCRIPTS / "soul_bridge.py"), "sync"])


def cmd_simulacrum(args):
    """Run a Logic Simulacrum debate session."""
    flags = ["--agents"] + args.agents + ["--rounds", str(args.rounds)]
    return _run(["python", str(SCRIPTS / "simulacrum.py"), args.topic] + flags)


def cmd_pulse(args):
    """Run the Performance Pulse benchmark suite."""
    return _run(["python", str(SCRIPTS / "performance_pulse.py")])


def cmd_sandbox(args):
    """Manage the Shadow Sandbox."""
    return _run(["python", str(SCRIPTS / "sandbox_manager.py"), args.action])


def cmd_heartbeat(args):
    """Control the Heartbeat Daemon."""
    flags = ["--once"] if args.once else []
    return _run(["python", str(SCRIPTS / "heartbeat_daemon.py")] + flags)


def cmd_exchange(args):
    """Manage the Agent Exchange marketplace."""
    flags = [args.action]
    if hasattr(args, "agent") and args.agent:
        flags.append(args.agent)
    if hasattr(args, "force") and args.force:
        flags.append("--force")
    return _run(["python", str(SCRIPTS / "exchange.py")] + flags)


def cmd_guardian_rules(args):
    """Manage P24 custom Guardian YAML rules."""
    return _run(["python", str(SCRIPTS / "guardian_rules_engine.py"), args.action])


def cmd_sovereign(args):
    """Run P25 Sovereign Loop operations."""
    if args.action == "scan":
        cmd = ["python", str(SCRIPTS / "sovereign_intel.py")]
        if args.token:
            cmd += ["--token", args.token]
        return _run(cmd)
    elif args.action == "evolve":
        cmd = ["python", str(SCRIPTS / "sovereign_loop.py")]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.no_push:
            cmd.append("--no-push")
        if args.token:
            cmd += ["--token", args.token]
        return _run(cmd)
    elif args.action == "status":
        return _run(["python", str(SCRIPTS / "sovereign_loop.py"), "--status"])
    return 0


# ── Parser Setup ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agentica",
        description="Agentica CLI v2 — Sovereign AI Orchestration System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Commands:
  swarm           Dispatch a swarm manifest (parallel agents)
  sentinel        Run the self-healing sentinel
  dashboard       Start the Control Center dashboard
  bridge          Sync Soul Memory across projects
  simulacrum      Run an Agent-to-Agent debate
  pulse           Run performance benchmarks
  sandbox         Manage the shadow sandbox
  heartbeat       Control the background heartbeat daemon
  exchange        Manage the agent exchange marketplace
  guardian-rules  Manage P24 custom pre-commit YAML rules      [P24]
  sovereign       Run the P25 Sovereign Loop (intel/evolve)    [P25]

Examples:
  agentica swarm .Agentica/swarm_manifest.json --shadow
  agentica simulacrum "How to implement auth?" --agents backend-specialist security-auditor
  agentica pulse
  agentica dashboard --port 8080
  agentica exchange install react-expert
  agentica guardian-rules init
  agentica guardian-rules validate
  agentica sovereign scan
  agentica sovereign evolve --dry-run
        """
    )
    p.add_argument("--version", action="version", version=f"Agentica {VERSION}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    # swarm
    sp = sub.add_parser("swarm", help="Dispatch agent swarm")
    sp.add_argument("manifest", help="Path to swarm manifest JSON")
    sp.add_argument("--shadow", action="store_true", help="Run in isolated sandbox")
    sp.add_argument("--sequential", action="store_true", help="Run tasks sequentially")
    sp.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="Print tasks without executing")
    sp.set_defaults(func=cmd_swarm)

    # sentinel
    sp = sub.add_parser("sentinel", help="Run self-healing sentinel")
    sp.set_defaults(func=cmd_sentinel)

    # dashboard
    sp = sub.add_parser("dashboard", help="Start Control Center")
    sp.add_argument("--port", type=int, default=8080)
    sp.set_defaults(func=cmd_dashboard)

    # bridge
    sp = sub.add_parser("bridge", help="Sync Soul Memory")
    sp.set_defaults(func=cmd_bridge)

    # simulacrum
    sp = sub.add_parser("simulacrum", help="Run Agent-to-Agent debate")
    sp.add_argument("topic", help="Topic to debate")
    sp.add_argument("--agents", nargs="+",
                    default=["backend-specialist", "security-auditor", "frontend-specialist"])
    sp.add_argument("--rounds", type=int, default=3)
    sp.set_defaults(func=cmd_simulacrum)

    # pulse
    sp = sub.add_parser("pulse", help="Run performance benchmarks")
    sp.set_defaults(func=cmd_pulse)

    # sandbox
    sp = sub.add_parser("sandbox", help="Shadow Sandbox management")
    sp.add_argument("action", choices=["init", "audit", "merge", "rollback"],
                    help="Sandbox action to perform")
    sp.set_defaults(func=cmd_sandbox)

    # heartbeat
    sp = sub.add_parser("heartbeat", help="Heartbeat daemon control")
    sp.add_argument("--once", action="store_true", help="Run single heartbeat cycle")
    sp.set_defaults(func=cmd_heartbeat)

    # exchange
    sp = sub.add_parser("exchange", help="Agent Exchange marketplace")
    sp.add_argument("action", choices=["sync", "install", "list"],
                    help="Exchange action")
    sp.add_argument("agent", nargs="?", help="Agent name (for install)")
    sp.add_argument("--force", action="store_true", help="Force overwrite on install")
    sp.set_defaults(func=cmd_exchange)

    # guardian-rules (P24)
    sp = sub.add_parser("guardian-rules", help="Manage custom P24 Guardian YAML rules")
    sp.add_argument("action", choices=["validate", "init", "list"],
                    default="validate", nargs="?",
                    help="validate (default): check staged files | init: create starter YAML | list: show active rules")
    sp.set_defaults(func=cmd_guardian_rules)

    # sovereign (P25)
    sp = sub.add_parser("sovereign", help="P25 Sovereign Loop — competitor intel & auto-evolution")
    sp.add_argument("action", choices=["scan", "evolve", "status"],
                    help="scan: fetch competitor intel | evolve: run full loop | status: show last cycle")
    sp.add_argument("--dry-run",  dest="dry_run",  action="store_true",
                    help="(evolve) Show what would happen without writing files")
    sp.add_argument("--no-push",  dest="no_push",  action="store_true",
                    help="(evolve) Commit but do not push to GitHub")
    sp.add_argument("--token",    default=None,
                    help="GitHub personal access token (or set GITHUB_TOKEN env var)")
    sp.set_defaults(func=cmd_sovereign)

    return p


def main():
    print(f"{YELLOW}{BOLD}{HEADER}{RESET}")
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    print(f"{DIM}[agentica] Executing: {args.command}...{RESET}\n")
    code = args.func(args)
    sys.exit(code or 0)


if __name__ == "__main__":
    main()
