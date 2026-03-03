"""
Agentica P17: Natural Language Swarm
Parses a plain English description and generates a swarm manifest.
"Add auth to Django app, audit it, and write tests"
→ Auto-selects agents, builds manifest, ready to dispatch.
Secretary Bird: understands intent before striking. 🦅
"""
import json
import sys
import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── Keyword → Agent mapping ───────────────────────────────────────

AGENT_TRIGGERS: dict[str, list[str]] = {
    "backend-specialist":  ["api", "rest", "graphql", "endpoint", "server", "backend",
                            "django", "fastapi", "flask", "express", "node", "service"],
    "security-auditor":    ["auth", "authentication", "security", "login", "password",
                            "token", "jwt", "oauth", "permission", "role", "access",
                            "encryption", "ssl", "https", "vulnerability", "audit"],
    "frontend-specialist": ["ui", "ux", "component", "react", "vue", "next", "page",
                            "form", "button", "design", "css", "style", "layout",
                            "modal", "dashboard", "interface", "frontend"],
    "database-architect":  ["database", "db", "sql", "schema", "model", "migration",
                            "postgres", "mysql", "mongo", "index", "query", "table",
                            "relation", "orm", "firestore", "redis"],
    "test-engineer":       ["test", "tests", "testing", "spec", "coverage", "unit",
                            "integration", "e2e", "mock", "fixture", "assert"],
    "devops-engineer":     ["deploy", "ci", "cd", "docker", "container", "pipeline",
                            "github actions", "workflow", "staging", "production",
                            "server", "infra", "kubernetes", "k8s", "cloud"],
    "performance-optimizer": ["performance", "speed", "slow", "fast", "optimis",
                              "cache", "memory", "bottleneck", "benchmark", "latency"],
    "documentation-writer": ["document", "docs", "readme", "changelog", "comment",
                              "explain", "write up", "api doc"]
}

# ── Intent → Task template mapping ──────────────────────────────

TASK_TEMPLATES = {
    "build": "Implement the following feature: {desc}. Follow clean code principles.",
    "audit": "Perform a thorough security audit of: {desc}. Report all risks.",
    "test":  "Write comprehensive tests for: {desc}. Cover all edge cases.",
    "deploy": "Plan and validate deployment pipeline for: {desc}.",
    "optimise": "Profile and optimise performance of: {desc}.",
    "document": "Write complete documentation for: {desc}.",
    "debug": "Identify and fix all bugs in: {desc}.",
    "review": "Conduct a code review of: {desc}. Provide actionable feedback."
}

INTENT_KEYWORDS = {
    "audit":    ["audit", "security", "check", "scan", "review", "inspect"],
    "test":     ["test", "tests", "spec", "coverage"],
    "deploy":   ["deploy", "release", "ship", "staging"],
    "optimise": ["optimis", "optimi", "speed", "performance", "fast"],
    "document": ["document", "docs", "readme", "write up"],
    "debug":    ["debug", "fix", "bug", "error", "broken"],
    "review":   ["review", "feedback", "critique"],
    "build":    []  # default
}


class SwarmTask(NamedTuple):
    id: str
    agent: str
    intent: str
    command: str
    description: str


def detect_agents(text: str) -> list[str]:
    """Select agents based on keyword matching."""
    text_lower = text.lower()
    matched = []
    for agent, keywords in AGENT_TRIGGERS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(agent)
    # Always add at least backend-specialist as fallback
    if not matched:
        matched = ["backend-specialist", "test-engineer"]
    # Deduplicate while preserving order
    return list(dict.fromkeys(matched))


def detect_intents(text: str) -> list[str]:
    """Detect what actions are requested."""
    text_lower = text.lower()
    found = []
    for intent, keywords in INTENT_KEYWORDS.items():
        if intent == "build":
            continue
        if any(kw in text_lower for kw in keywords):
            found.append(intent)
    if not found:
        found = ["build"]
    return found


def nl_to_manifest(description: str, output_path: str | None = None) -> dict:
    """Convert natural language to a swarm manifest."""
    agents  = detect_agents(description)
    intents = detect_intents(description)
    run_id  = str(uuid.uuid4())[:6]

    tasks = []
    task_num = 1
    for intent in intents:
        # Pick best agent for each intent
        agent_map = {
            "audit":    "security-auditor",
            "test":     "test-engineer",
            "deploy":   "devops-engineer",
            "optimise": "performance-optimizer",
            "document": "documentation-writer",
            "debug":    "backend-specialist",
            "review":   "backend-specialist",
            "build":    agents[0] if agents else "backend-specialist"
        }
        agent = agent_map.get(intent, agents[0])

        template = TASK_TEMPLATES.get(intent, TASK_TEMPLATES["build"])
        task_desc = template.format(desc=description[:100])
        task_id = f"{run_id}-{intent}-{task_num}"

        # Command delegates to simulacrum for debate first, then executes
        command = f"python scripts/simulacrum.py \"{task_desc[:80]}\" --agents {agent} --rounds 1"

        tasks.append({
            "id": task_id,
            "agent": agent,
            "command": command,
            "description": task_desc,
            "intent": intent
        })
        task_num += 1

    manifest = {
        "meta": {
            "generated_by": "nl_swarm.py (P17)",
            "original_description": description,
            "generated_at": datetime.now().isoformat(),
            "detected_agents": agents,
            "detected_intents": intents,
            "run_id": run_id
        },
        "tasks": tasks
    }

    # Save to file
    if output_path is None:
        out_dir = Path(".Agentica")
        out_dir.mkdir(exist_ok=True)
        output_path = str(out_dir / f"swarm_nl_{run_id}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest, output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="P17: Natural Language Swarm — converts plain English to swarm manifests"
    )
    parser.add_argument("description", help='Plain English task, e.g. "Add auth and write tests"')
    parser.add_argument("--output", "-o", help="Output manifest path (optional)")
    parser.add_argument("--run", action="store_true",
                        help="Immediately dispatch the generated swarm")
    parser.add_argument("--shadow", action="store_true",
                        help="Run in Shadow Sandbox mode (requires --run)")
    args = parser.parse_args()

    print(f"\n{YELLOW}{BOLD}Secretary Bird NL Swarm Parser (P17){RESET}")
    print(f"{BOLD}Input:{RESET} {args.description}\n")

    manifest, out_path = nl_to_manifest(args.description, args.output)

    print(f"{CYAN}{BOLD}Detected Agents:{RESET} {', '.join(manifest['meta']['detected_agents'])}")
    print(f"{CYAN}{BOLD}Detected Intents:{RESET} {', '.join(manifest['meta']['detected_intents'])}")
    print(f"\n{BOLD}Generated {len(manifest['tasks'])} tasks:{RESET}")
    for t in manifest["tasks"]:
        print(f"  [{t['agent']}] {t['intent'].upper()}: {t['description'][:70]}")

    print(f"\n{GREEN}Manifest saved >> {out_path}{RESET}")

    if args.run:
        import subprocess
        flags = ["--shadow"] if args.shadow else []
        print(f"\n{YELLOW}Dispatching swarm...{RESET}\n")
        subprocess.run(
            ["python", "scripts/swarm_dispatcher.py", out_path, "--sequential"] + flags
        )
