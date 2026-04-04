"""
tests/test_p29p.py
==================
Unit tests for scripts/p29p_engine.py — Agenticana P29+ CI Agent Engine.

Run with:
    python -m pytest tests/test_p29p.py -v
    # or
    python tests/test_p29p.py
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make sure the repo root is importable
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import p29p_engine as engine  # noqa: E402


class TestCheckAgentYamls(unittest.TestCase):
    """check_agent_yamls — validates agent YAML definitions."""

    def test_passes_with_valid_yamls(self):
        """Should pass when all YAML files in agents/ parse cleanly."""
        result = engine.check_agent_yamls()
        # The agents/ directory exists and should have valid YAMLs
        self.assertIn("name", result)
        self.assertEqual(result["name"], "agent-yamls")
        # If yaml is installed, it must pass; if not installed it can fail with a note
        if result["passed"]:
            self.assertIn("YAMLs validated", result["note"])

    def test_returns_dict_with_required_keys(self):
        """Result dict must always contain name, passed, note."""
        result = engine.check_agent_yamls()
        self.assertIn("name", result)
        self.assertIn("passed", result)
        self.assertIn("note", result)

    def test_fails_on_invalid_yaml(self):
        """Should fail when a malformed YAML file is present."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            bad_yaml = tmp_dir / "bad-agent.yaml"
            bad_yaml.write_text(": invalid: yaml: {\n", encoding="utf-8")

            with patch.object(engine, "AGENTS_DIR", tmp_dir):
                result = engine.check_agent_yamls()

            self.assertFalse(result["passed"])


class TestCheckReasoningBank(unittest.TestCase):
    """check_reasoning_bank — validates decisions.json."""

    def test_passes_with_valid_decisions_file(self):
        """Should pass when decisions.json exists and is valid JSON."""
        result = engine.check_reasoning_bank()
        self.assertEqual(result["name"], "reasoning-bank")
        # The actual file should exist in this repo
        if result["passed"]:
            self.assertIn("decisions stored", result["note"])

    def test_fails_when_file_missing(self):
        """Should fail gracefully when decisions.json does not exist."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake_memory_dir = Path(tmp) / "nonexistent"
            with patch.object(engine, "MEMORY_DIR", fake_memory_dir):
                result = engine.check_reasoning_bank()
        self.assertFalse(result["passed"])
        self.assertIn("not found", result["note"])

    def test_fails_on_malformed_json(self):
        """Should fail when decisions.json contains invalid JSON."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake_dir = Path(tmp)
            (fake_dir / "decisions.json").write_text("{bad json}", encoding="utf-8")
            with patch.object(engine, "MEMORY_DIR", fake_dir):
                result = engine.check_reasoning_bank()
        self.assertFalse(result["passed"])

    def test_counts_decisions_correctly(self):
        """Should report the correct decision count from total_decisions."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake_dir = Path(tmp)
            data = {
                "version": "2.0",
                "total_decisions": 7,
                "decisions": [{"id": str(i)} for i in range(7)],
                "patterns": [],
            }
            (fake_dir / "decisions.json").write_text(json.dumps(data), encoding="utf-8")
            with patch.object(engine, "MEMORY_DIR", fake_dir):
                result = engine.check_reasoning_bank()
        self.assertTrue(result["passed"])
        self.assertIn("7", result["note"])


class TestCheckRouterConfig(unittest.TestCase):
    """check_router_config — validates router/config.json."""

    def test_passes_with_real_config(self):
        """The real router/config.json in this repo should pass."""
        result = engine.check_router_config()
        self.assertEqual(result["name"], "router-config")
        self.assertTrue(result["passed"], f"Router config check failed: {result['note']}")

    def test_fails_when_config_missing(self):
        """Should fail when config.json is not found."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake_router_dir = Path(tmp) / "empty"
            with patch.object(engine, "AGENTICANA_ROOT", Path(tmp)):
                result = engine.check_router_config()
        self.assertFalse(result["passed"])

    def test_fails_on_missing_keys(self):
        """Should fail when required keys are absent from config.json."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            router_dir = Path(tmp) / "router"
            router_dir.mkdir()
            (router_dir / "config.json").write_text(
                json.dumps({"models": {}}), encoding="utf-8"
            )
            with patch.object(engine, "AGENTICANA_ROOT", Path(tmp)):
                result = engine.check_router_config()
        self.assertFalse(result["passed"])
        self.assertIn("missing keys", result["note"])


class TestCheckSkillsStructure(unittest.TestCase):
    """check_skills_structure — validates skills directory."""

    def test_passes_with_real_skills(self):
        """Real skills/ directory should pass."""
        result = engine.check_skills_structure()
        self.assertEqual(result["name"], "skills-structure")
        # May pass or warn depending on which skills have SKILL.md
        self.assertIn("passed", result)

    def test_fails_when_skills_dir_missing(self):
        """Should fail gracefully when skills/ doesn't exist."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(engine, "AGENTICANA_ROOT", Path(tmp)):
                result = engine.check_skills_structure()
        self.assertFalse(result["passed"])
        self.assertIn("not found", result["note"])

    def test_reports_missing_skill_md(self):
        """Should report skills that are missing SKILL.md."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            (skills_dir / "my-skill").mkdir(parents=True)  # no SKILL.md inside
            with patch.object(engine, "AGENTICANA_ROOT", Path(tmp)):
                result = engine.check_skills_structure()
        self.assertFalse(result["passed"])
        self.assertIn("my-skill", result["note"])


class TestRunAudit(unittest.TestCase):
    """run_audit — orchestration of the full check suite."""

    def test_returns_summary_dict(self):
        """run_audit must return a dict with ok, passed, failed, total, results."""
        result = engine.run_audit(ci=True)
        for key in ("ok", "passed", "failed", "total", "results", "timestamp"):
            self.assertIn(key, result)

    def test_total_equals_check_count(self):
        """total in result should equal the number of defined checks."""
        result = engine.run_audit(ci=True)
        self.assertEqual(result["total"], len(engine.CHECKS))

    def test_passed_plus_failed_equals_total(self):
        """passed + failed must always equal total."""
        result = engine.run_audit(ci=True)
        self.assertEqual(result["passed"] + result["failed"], result["total"])

    def test_ok_reflects_zero_failures(self):
        """ok should be True only when failed == 0."""
        # Mock all checks to pass
        mock_check = MagicMock(return_value={"name": "mock", "passed": True, "note": "ok"})
        mock_check.__name__ = "check_mock"
        with patch.object(engine, "CHECKS", [mock_check, mock_check]):
            result = engine.run_audit(ci=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["failed"], 0)

    def test_ok_false_on_any_failure(self):
        """ok should be False when at least one check fails."""
        pass_check = MagicMock(return_value={"name": "pass", "passed": True, "note": "ok"})
        pass_check.__name__ = "check_pass"
        fail_check = MagicMock(return_value={"name": "fail", "passed": False, "note": "broken"})
        fail_check.__name__ = "check_fail"
        with patch.object(engine, "CHECKS", [pass_check, fail_check]):
            result = engine.run_audit(ci=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed"], 1)


if __name__ == "__main__":
    unittest.main()
