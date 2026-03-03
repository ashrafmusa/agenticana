import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ────────────────────────────────────────────────────────────────
# Agentica P15: Real LLM Simulacrum
# Agents call an ACTUAL LLM API with domain-specific system prompts.
# Each agent persona gets its own Gemini instance with a unique role.
# Result: Real AI debate, not hardcoded responses.
# Mascot: Secretary Bird — stomps first, asks questions never. 🦅
# ────────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

AGENT_SYSTEM_PROMPTS = {
    "backend-specialist": (
        "You are a pragmatic backend engineer on a code review council. "
        "You ONLY think about: API performance, scalability, clean service boundaries, "
        "and database efficiency. You are opinionated and concise. "
        "Max 3 sentences. No fluff. Challenge bad ideas directly."
    ),
    "security-auditor": (
        "You are a paranoid security engineer on a code review council. "
        "You ONLY think about: threat vectors, injection risks, token leakage, "
        "insecure defaults, and zero-trust architecture. "
        "Every proposal has a flaw. Find it. Max 3 sentences."
    ),
    "frontend-specialist": (
        "You are a UX-obsessed frontend engineer on a code review council. "
        "You ONLY think about: developer experience, component reusability, "
        "state complexity, bundle size, and accessibility. "
        "You push back on backend-heavy solutions. Max 3 sentences."
    ),
    "database-architect": (
        "You are a meticulous database architect on a code review council. "
        "You ONLY think about: schema integrity, indexing strategy, migration safety, "
        "N+1 query prevention, and data normalisation. "
        "You distrust ORMs. Max 3 sentences."
    ),
    "devops-engineer": (
        "You are an operational devops engineer on a code review council. "
        "You ONLY think about: CI/CD reliability, deployment safety, rollback strategy, "
        "container health, and secrets management. "
        "You will block any unsafe deploy. Max 3 sentences."
    ),
    "performance-optimizer": (
        "You are a metric-obsessed performance engineer on a code review council. "
        "You ONLY think about: execution speed, memory footprint, cache efficiency, "
        "Core Web Vitals, and bottleneck identification. "
        "Everything is too slow until proven otherwise. Max 3 sentences."
    ),
    "test-engineer": (
        "You are a methodical test engineer on a code review council. "
        "You ONLY think about: test coverage, edge cases, regression safety, "
        "integration gaps, and flaky test prevention. "
        "No code ships untested. Max 3 sentences."
    )
}


def _get_api_key() -> str | None:
    """Load Gemini API key from environment or .Agentica config."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    cfg = Path(".Agentica/gemini.key")
    if cfg.exists():
        return cfg.read_text().strip()
    return None


def _call_gemini(system_prompt: str, user_message: str, api_key: str) -> str:
    """Call Gemini Flash API and return the text response."""
    payload = json.dumps({
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_message}]}],
        "generationConfig": {"maxOutputTokens": 200, "temperature": 0.7}
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{GEMINI_API_URL}?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        return f"[API Error {e.code}]: {e.reason}"
    except Exception as e:
        return f"[Error]: {str(e)}"


def _fallback_response(agent_name: str, topic: str, round_num: int) -> str:
    """Persona-based fallback when no API key is available."""
    persona_map = {
        "backend-specialist": f"From a scalability lens: we must address API latency and service boundaries for '{topic[:40]}'. I propose a clean REST contract with proper caching headers.",
        "security-auditor": f"Security concern on '{topic[:40]}': every input must be validated and sanitised. Assume malicious intent by default.",
        "frontend-specialist": f"UX impact of '{topic[:40]}': keep state minimal and ensure the API contract doesn't force the client into complex state management.",
        "database-architect": f"Schema impact: '{topic[:40]}' must define clear indexes upfront. Migration scripts must be reversible.",
        "devops-engineer": f"Deploy risk for '{topic[:40]}': ensure rollback strategy is defined before merging. Secrets must not be in environment strings.",
        "performance-optimizer": f"Perf concern: '{topic[:40]}' needs a benchmark baseline. No merge without profiling.",
        "test-engineer": f"Test gap: '{topic[:40]}' needs unit tests for ALL branches plus integration test for the happy path."
    }
    return persona_map.get(agent_name, f"Concern about '{topic[:40]}': apply best practices.")


class RealAgent:
    """An agent that calls a real LLM with domain-specific system prompt."""

    def __init__(self, name: str, api_key: str | None):
        self.name = name
        self.api_key = api_key
        self.system_prompt = AGENT_SYSTEM_PROMPTS.get(name, "You are a senior software engineer. Be concise.")

    def speak(self, topic: str, context: str = "", round_label: str = "opening") -> str:
        """Generate a real LLM response for this agent's role."""
        if self.api_key:
            if round_label == "opening":
                msg = f"The team is debating: {topic}\n\nGive your opening position."
            else:
                msg = f"Topic: {topic}\n\nPrevious argument: {context}\n\nRespond and add your specific concern."
            response = _call_gemini(self.system_prompt, msg, self.api_key)
        else:
            response = _fallback_response(self.name, topic, 0)
        return response

    def propose(self, topic: str) -> str:
        """Agent makes a concrete proposal."""
        if self.api_key:
            msg = f"Topic: {topic}\n\nMake a ONE concrete, specific proposal (one sentence) for how to approach this."
            return _call_gemini(self.system_prompt, msg, self.api_key)
        concern = AGENT_SYSTEM_PROMPTS.get(self.name, "").split(".")[1].strip() if self.name in AGENT_SYSTEM_PROMPTS else "best practices"
        return f"Use {concern.split(',')[0].strip()} as the primary constraint for {topic[:50]}."

    def vote(self, proposals: dict[str, str]) -> str:
        """Agent votes for the strongest proposal."""
        if self.api_key and proposals:
            opts = "\n".join([f"{i+1}. [{a}]: {p[:120]}" for i, (a, p) in enumerate(proposals.items())])
            msg = f"Topic: {topic if (topic := '') else 'the debate'}\n\nProposals:\n{opts}\n\nWhich number best aligns with your domain? Reply with just the number."
            vote_text = _call_gemini(self.system_prompt, msg, self.api_key)
            # extract first digit
            for char in vote_text:
                if char.isdigit() and 1 <= int(char) <= len(proposals):
                    return list(proposals.keys())[int(char) - 1]
        # fallback: vote for own proposal
        return self.name


class RealSimulacrum:
    """
    P15: The Real LLM Simulacrum.
    Actual Gemini calls per agent → genuine multi-model debate.
    Falls back gracefully to persona mode if no API key.
    """

    def __init__(self, topic: str, agents: list[str], rounds: int = 2):
        self.topic = topic
        self.rounds = rounds
        self.session_id = str(uuid.uuid4())[:8]
        self.api_key = _get_api_key()
        self.agents = [RealAgent(name, self.api_key) for name in agents]
        self.log_dir = Path(".Agentica/logs/simulacrum")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.transcript: list[dict] = []
        self.mode = "LIVE_LLM" if self.api_key else "PERSONA_FALLBACK"

    def _record(self, speaker: str, content: str, phase: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase, "speaker": speaker, "content": content, "mode": self.mode
        }
        self.transcript.append(entry)
        tag = {
            "opening":   f"{CYAN}[OPEN]   {RESET}",
            "debate":    f"{YELLOW}[DEBATE] {RESET}",
            "proposal":  f"{BOLD}[PROP]   {RESET}",
            "vote":      f"{GREEN}[VOTE]   {RESET}",
            "consensus": f"{GREEN}[CONSENSUS]{RESET}"
        }.get(phase, "[LOG]")
        print(f"  {tag}{BOLD}{speaker}{RESET}")
        # Word-wrap the content at 80 chars
        words = content.split()
        line = "    "
        for word in words:
            if len(line) + len(word) > 80:
                print(line)
                line = "    " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line)
        print()

    def run(self) -> dict:
        mode_label = f"{GREEN}LIVE LLM{RESET}" if self.api_key else f"{YELLOW}PERSONA MODE{RESET}"
        print(f"\n{BOLD}{'='*50}{RESET}")
        print(f"{BOLD}  SECRETARY BIRD SIMULACRUM (P15){RESET}  {mode_label}")
        print(f"{BOLD}  Session: {self.session_id}{RESET}")
        print(f"{BOLD}  Topic: {self.topic[:70]}{RESET}")
        print(f"{BOLD}  Agents: {', '.join(a.name for a in self.agents)}{RESET}")
        print(f"{BOLD}{'='*50}{RESET}\n")

        # Phase 1: Opening
        print(f"{BOLD}[Phase 1] Opening Positions{RESET}")
        last_context = self.topic
        for agent in self.agents:
            resp = agent.speak(self.topic, round_label="opening")
            self._record(agent.name, resp, "opening")
            last_context = resp
            time.sleep(0.3 if self.api_key else 0.05)

        # Phase 2: Debate Rounds
        for rnd in range(self.rounds):
            print(f"{BOLD}[Phase 2] Debate Round {rnd + 1}{RESET}")
            for agent in self.agents:
                resp = agent.speak(self.topic, last_context, round_label=f"round_{rnd}")
                self._record(agent.name, resp, "debate")
                last_context = resp
                time.sleep(0.3 if self.api_key else 0.05)

        # Phase 3: Proposals
        print(f"{BOLD}[Phase 3] Proposals{RESET}")
        proposals: dict[str, str] = {}
        for agent in self.agents:
            prop = agent.propose(self.topic)
            proposals[agent.name] = prop
            self._record(agent.name, prop, "proposal")
            time.sleep(0.2 if self.api_key else 0.02)

        # Phase 4: Voting
        print(f"{BOLD}[Phase 4] Voting{RESET}")
        vote_tally: dict[str, int] = {a: 0 for a in proposals}
        for agent in self.agents:
            winner_name = agent.vote(proposals)
            if winner_name in vote_tally:
                vote_tally[winner_name] += 1
            self._record(agent.name, f"Votes for: {winner_name}", "vote")
            time.sleep(0.1)

        winner = max(vote_tally, key=vote_tally.get)
        winning_proposal = proposals[winner]

        # Phase 5: Consensus
        consensus_text = (
            f"CONSENSUS: [{winner}]'s approach wins with {vote_tally[winner]} vote(s). "
            f"Proposal: {winning_proposal[:100]}"
        )
        self._record("SECRETARY BIRD", consensus_text, "consensus")

        result = {
            "session_id": self.session_id,
            "topic": self.topic,
            "mode": self.mode,
            "agents": [a.name for a in self.agents],
            "winning_agent": winner,
            "winning_proposal": winning_proposal,
            "vote_tally": vote_tally,
            "all_proposals": proposals,
            "timestamp": datetime.now().isoformat(),
            "transcript": self.transcript
        }

        log_path = self.log_dir / f"session_{self.session_id}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"{GREEN}{BOLD}{'='*50}{RESET}")
        print(f"{GREEN}{BOLD}  DEBATE COMPLETE >> {log_path}{RESET}")
        print(f"{GREEN}{BOLD}{'='*50}{RESET}\n")
        return result


def run_real_simulacrum(topic: str, agents: list[str], rounds: int = 2) -> dict:
    """Public API for P15 Real LLM Simulacrum."""
    sim = RealSimulacrum(topic=topic, agents=agents, rounds=rounds)
    return sim.run()


if __name__ == "__main__":
    import argparse, io
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="P15: Real LLM Simulacrum")
    parser.add_argument("topic", help="Topic to debate")
    parser.add_argument("--agents", nargs="+",
                        default=["backend-specialist", "security-auditor", "frontend-specialist"])
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--set-key", help="Save Gemini API key to .Agentica/gemini.key")
    args = parser.parse_args()

    if args.set_key:
        Path(".Agentica/gemini.key").write_text(args.set_key)
        print(f"{GREEN}[OK] API key saved to .Agentica/gemini.key{RESET}")
        sys.exit(0)

    result = run_real_simulacrum(args.topic, args.agents, args.rounds)
    print(f"{BOLD}Winner:{RESET} {result['winning_agent']}")
    print(f"{BOLD}Proposal:{RESET} {result['winning_proposal'][:120]}")
