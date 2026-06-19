#!/usr/bin/env python3
"""
Agentica P25: Sovereign Intel Swarm 🦅 (Real Implementation)
=============================================================
Monitors competitor GitHub repositories using the real GitHub Issues API
to identify trending feature requests and market gaps.

Uses GITHUB_TOKEN env var if set (5000 req/hr).
Falls back to unauthenticated (60 req/hr) with a warning.

Usage:
    python scripts/sovereign_intel.py
    python scripts/sovereign_intel.py --repos "owner/repo,owner/repo2"
    python scripts/sovereign_intel.py --top 5   # print top 5 gaps

Secretary Bird: always watching. 🦅
"""
import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from collections import Counter

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

DEFAULT_COMPETITORS = [
    "openclaw/openclaw",
    "continuedev/continue",
    "cline/cline",
    "Significant-Gravitas/AutoGPT",
    "reworkd/AgentGPT",
    "Pythagora-io/gpt-pilot",
    "e2b-dev/code-interpreter",
    "TabbyML/tabby",
    "OpenInterpreter/open-interpreter",
    "microsoft/autogen",
    "crewAIInc/crewAI",
]

# Labels considered "feature request"
FEATURE_LABELS = {"enhancement", "feature", "feature-request", "feat", "new feature", "proposal"}

COMPETITORS_PATH = Path(".Agentica/competitors.json")
INTEL_PATH       = Path(".Agentica/competitor_intel.json")


# ── GitHub API ────────────────────────────────────────────────────────────────

def _github_request(url: str, token: str | None) -> dict | list | None:
    """Make a GitHub API GET request. Returns parsed JSON or None on error."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "Agenticana-P25-SovereignIntel/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"{YELLOW}  [!] Rate limited by GitHub API. Set GITHUB_TOKEN env var for higher limits.{RESET}")
        elif e.code == 404:
            pass  # Repo not found — skip silently
        else:
            print(f"{YELLOW}  [!] GitHub API error {e.code} for {url}{RESET}")
    except Exception as e:
        print(f"{YELLOW}  [!] Network error: {e}{RESET}")
    return None


def _get_top_issues(repo: str, token: str | None, per_page: int = 30) -> list[dict]:
    """Fetch top open feature-request issues from a repo."""
    url = (
        f"https://api.github.com/repos/{repo}/issues"
        f"?state=open&per_page={per_page}&sort=comments&direction=desc"
    )
    data = _github_request(url, token)
    if not data or not isinstance(data, list):
        return []
    return [i for i in data if i.get("pull_request") is None]  # exclude PRs


def _extract_gaps(issues: list[dict]) -> list[str]:
    """Extract feature gap keywords from issue titles."""
    gaps = []
    for issue in issues:
        title = issue.get("title", "")
        labels = [lbl.get("name", "").lower() for lbl in issue.get("labels", [])]
        # Include if it has a feature label OR high comment count (community interest)
        is_feature = any(lbl in FEATURE_LABELS for lbl in labels)
        high_interest = issue.get("comments", 0) >= 3
        if is_feature or high_interest:
            # Clean the title to extract the core concept
            clean = title.strip()[:80]
            if clean:
                gaps.append(clean)
    return gaps[:10]  # top 10 per repo


# ── Competitor loading ────────────────────────────────────────────────────────

def load_competitors() -> list[str]:
    if COMPETITORS_PATH.exists():
        try:
            data = json.loads(COMPETITORS_PATH.read_text(encoding="utf-8"))
            repos = data.get("repos", []) if isinstance(data, dict) else []
            cleaned = [str(r).strip() for r in repos if str(r).strip()]
            if cleaned:
                return cleaned
        except Exception as exc:
            print(f"{YELLOW}[!] Could not parse {COMPETITORS_PATH}: {exc}{RESET}")

    COMPETITORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPETITORS_PATH.write_text(
        json.dumps({"updated_at": datetime.now().isoformat(), "repos": DEFAULT_COMPETITORS}, indent=2),
        encoding="utf-8",
    )
    return DEFAULT_COMPETITORS


# ── Main scan ─────────────────────────────────────────────────────────────────

def scan(repos: list[str], token: str | None = None) -> list[dict]:
    """Scan all repos and return structured intel."""
    if token:
        print(f"{GREEN}[P25] Authenticated GitHub API (5000 req/hr){RESET}")
    else:
        print(f"{YELLOW}[P25] Unauthenticated GitHub API (60 req/hr). "
              f"Set GITHUB_TOKEN for higher limits.{RESET}")

    findings = []
    for repo in repos:
        repo = repo.strip()
        print(f"  [*] Scanning {repo}...", end=" ", flush=True)
        issues = _get_top_issues(repo, token)
        gaps   = _extract_gaps(issues)
        if not gaps:
            # Fallback: use issue titles directly (no label filter)
            gaps = [i.get("title", "")[:60] for i in issues[:5] if i.get("title")]
        print(f"{len(gaps)} gaps found")
        findings.append({
            "repo":             repo,
            "scanned_at":       datetime.now().isoformat(),
            "issues_sampled":   len(issues),
            "trending_requests": gaps,
        })

    # Save
    INTEL_PATH.parent.mkdir(exist_ok=True)
    INTEL_PATH.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\n{GREEN}[P25] Intel saved → {INTEL_PATH}{RESET}")
    return findings


def top_gaps(findings: list[dict], n: int = 5) -> list[tuple[str, int]]:
    """Return the N most common gap themes across all repos."""
    counter: Counter = Counter()
    for repo in findings:
        for gap in repo.get("trending_requests", []):
            # Normalize: lowercase, first 6 words
            key = " ".join(gap.lower().split()[:6])
            counter[key] += 1
    return counter.most_common(n)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="P25: Sovereign Intel Swarm — real GitHub competitor monitoring"
    )
    parser.add_argument("--repos", help="Comma-separated list of owner/repo to scan")
    parser.add_argument("--top",   type=int, default=5, help="Show top N gaps (default: 5)")
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN env var)")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")
    repos = args.repos.split(",") if args.repos else load_competitors()

    print(f"\n{BOLD}{CYAN}🦅 Agenticana Sovereign Intel Swarm (P25){RESET}")
    print(f"{CYAN}Scanning {len(repos)} competitor repositories...{RESET}\n")

    findings = scan(repos, token)

    gaps = top_gaps(findings, args.top)
    if gaps:
        print(f"\n{BOLD}Top {len(gaps)} Feature Gaps Detected:{RESET}")
        for i, (gap, count) in enumerate(gaps, 1):
            print(f"  {i}. [{count} repos] {gap}")

    print(f"\n{GREEN}[+] Run 'python scripts/sovereign_loop.py' to auto-implement the top gap.{RESET}")


if __name__ == "__main__":
    main()
