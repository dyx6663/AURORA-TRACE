import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import aurora
from aurora import (ToolExecutor, ToolRegistry, complete_run, contract_for,
                    emit, execute_agent_tool, persist_run, profile_project,
                    phase_for_tool, safe_path, safe_zip_member)


class CoreSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        (self.workspace / "demo.py").write_text("value = 1\n", encoding="utf-8")
        self.tools = ToolExecutor(self.workspace)

    def make_run(self):
        run_dir = self.workspace / "run"
        run_dir.mkdir()
        return {
            "id": "test-run",
            "task": "test task",
            "mode": "mock",
            "workspace": run_dir,
            "events": [],
            "ledger": [],
            "diffs": [],
            "state": "QUEUED",
            "summary": "",
            "finished": False,
            "lock": threading.Lock(),
            "ledger_path": run_dir / "evidence.ndjson",
            "state_path": run_dir / "run.json",
            "contract": contract_for("test task"),
            "project": {"id": "test", "name": "Test"},
            "evidence": {},
            "evidence_details": {},
            "trust_score": 0,
            "boundary_violations": 0,
            "last_event_id": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_replace_produces_small_diff(self):
        result = self.tools.replace_text("demo.py", "value = 1", "value = 2")
        self.assertTrue(result["changed"])
        self.assertEqual(result["added_lines"], 1)
        self.assertEqual(result["removed_lines"], 1)
        self.assertEqual((self.workspace / "demo.py").read_text(encoding="utf-8"), "value = 2\n")

    def test_exact_replace_rejects_ambiguous_match(self):
        with self.assertRaises(ValueError):
            self.tools.replace_text("demo.py", "missing", "new")

    def test_path_cannot_escape_workspace(self):
        with self.assertRaises(ValueError):
            safe_path(self.workspace, "../outside.txt")

    def test_command_guard_rejects_shell_features(self):
        with self.assertRaises(ValueError):
            self.tools.run_command("python -c print(1)")
        with self.assertRaises(ValueError):
            self.tools.run_command("python demo.py && echo unsafe")

    def test_contract_has_four_evidence_gates(self):
        contract = contract_for("fix a bug")
        self.assertEqual(len(contract["checks"]), 4)
        self.assertIn("regression_tests_passed", contract["checks"])

    def test_zip_member_cannot_escape_import_root(self):
        with self.assertRaises(ValueError):
            safe_zip_member("../../secret.txt")
        self.assertEqual(str(safe_zip_member("src/main.py")), str(Path("src/main.py")))

    def test_project_profile_ignores_generated_cache(self):
        cache = self.workspace / "__pycache__"
        cache.mkdir()
        (cache / "demo.pyc").write_bytes(b"cache")
        profile = profile_project(self.workspace)
        self.assertEqual(profile["files"], 1)
        self.assertEqual(profile["languages"], ["Python"])

    def test_tool_registry_returns_structured_errors(self):
        registry = ToolRegistry(self.tools)
        result = registry.execute("read_file", {})
        self.assertFalse(result["ok"])
        self.assertIn("missing required arguments", result["error"])

    def test_boundary_violation_is_recorded_as_failed_evidence(self):
        run = self.make_run()
        result = execute_agent_tool(
            run, ToolRegistry(self.tools), "read_file", {"path": "../outside.txt"},
            reason="attempted out-of-scope read"
        )
        self.assertFalse(result["ok"])
        self.assertEqual(run["boundary_violations"], 1)
        self.assertFalse(run["evidence"]["workspace_boundary_respected"])

    def test_tool_registry_attaches_contract_metadata(self):
        registry = ToolRegistry(self.tools)
        spec = registry.get("replace_text")
        self.assertTrue(spec.mutates_workspace)
        self.assertFalse(spec.parallel_safe)
        schema = registry.schemas()
        self.assertEqual(schema[0]["type"], "function")
        self.assertIn("additionalProperties", schema[0]["function"]["parameters"])

    def test_event_has_causal_parent_and_is_persisted(self):
        run = self.make_run()
        first = emit(run, "system", "start", phase="understand")
        second = emit(run, "decision", "inspect", tool="list_files",
                      phase="context", parent_event_id=first)
        self.assertEqual(run["events"][1]["parent_event_id"], first)
        self.assertEqual(run["events"][1]["run_id"], "test-run")
        ledger = [json.loads(line) for line in run["ledger_path"].read_text(encoding="utf-8").splitlines()]
        self.assertEqual(ledger[1]["parent_event_id"], first)
        snapshot = json.loads(run["state_path"].read_text(encoding="utf-8"))
        self.assertEqual(snapshot["last_event_id"], None)
        self.assertEqual(second, 2)

    def test_execute_agent_tool_links_decision_to_result(self):
        run = self.make_run()
        result = execute_agent_tool(
            run, ToolRegistry(self.tools), "list_files", {"path": "."},
            reason="build repository context"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(run["events"]), 2)
        self.assertEqual(run["events"][1]["parent_event_id"], run["events"][0]["id"])
        self.assertEqual(run["events"][1]["phase"], "context")

    def test_command_phase_requires_evidence_of_a_patch(self):
        run = self.make_run()
        self.assertEqual(phase_for_tool(run, "run_command"), "baseline")
        run["diffs"].append("one precise diff")
        self.assertEqual(phase_for_tool(run, "run_command"), "regression")

    def test_baseline_command_creates_explicit_hypothesis_edge(self):
        run = self.make_run()
        execute_agent_tool(
            run, ToolRegistry(self.tools), "run_command",
            {"command": "python -m unittest discover -v"},
            reason="observe the pre-patch behavior", requested_phase="baseline"
        )
        self.assertEqual(run["events"][0]["kind"], "hypothesis")
        self.assertEqual(run["events"][0]["evidence_type"], "baseline_hypothesis")
        self.assertEqual(run["events"][1]["parent_event_id"], run["events"][0]["id"])
        self.assertEqual(run["events"][2]["parent_event_id"], run["events"][1]["id"])

    def test_completion_is_blocked_without_all_gates(self):
        run = self.make_run()
        self.assertFalse(complete_run(run, "should not complete"))
        self.assertEqual(run["state"], "VERIFY")
        self.assertFalse(run["finished"])
        self.assertEqual(run["events"][-1]["title"], "Completion blocked")

    def test_completion_requires_and_accepts_real_gate_evidence(self):
        run = self.make_run()
        emit(run, "error", "baseline", tool="run_command",
             phase="baseline", payload={"ok": False, "phase": "baseline"})
        run["diffs"].append("--- a/demo.py\n+++ b/demo.py\n@@\n-value = 1\n+value = 2\n")
        emit(run, "tool_result", "regression", tool="run_command",
             phase="regression", payload={"ok": True, "phase": "regression"})
        self.assertTrue(complete_run(run, "verified"))
        self.assertEqual(run["state"], "COMPLETED")
        self.assertEqual(run["trust_score"], 100)

    def test_persisted_run_contains_serializable_state(self):
        run = self.make_run()
        run["summary"] = "persisted"
        persist_run(run)
        saved = json.loads(run["state_path"].read_text(encoding="utf-8"))
        self.assertEqual(saved["run_id"], "test-run")
        self.assertEqual(saved["summary"], "persisted")
        self.assertNotIn("workspace", saved)

    def test_loaded_history_restores_finished_run(self):
        run = self.make_run()
        history_dir = self.workspace / ".runs" / "test-run"
        run["state_path"] = history_dir / "run.json"
        run["ledger_path"] = history_dir / "evidence.ndjson"
        run["state"] = "COMPLETED"
        run["finished"] = True
        persist_run(run)
        original_root = aurora.ROOT
        original_runs = dict(aurora.RUNS)
        try:
            aurora.ROOT = self.workspace
            aurora.RUNS.clear()
            aurora.load_run_history()
            self.assertIn("test-run", aurora.RUNS)
            self.assertEqual(aurora.RUNS["test-run"]["state"], "COMPLETED")
        finally:
            aurora.ROOT = original_root
            aurora.RUNS.clear()
            aurora.RUNS.update(original_runs)

    def test_live_mode_requires_api_key_before_copying_project(self):
        previous = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(ValueError):
                aurora.start_run("live test", "live")
        finally:
            if previous is not None:
                os.environ["OPENAI_API_KEY"] = previous

    def test_live_finish_proposal_cannot_bypass_acceptance_gate(self):
        run = self.make_run()

        class FinishOnlyModel:
            def __init__(self, _mode):
                pass

            def decide(self, _messages):
                return {"type": "finish", "summary": "unsupported claim"}

        with patch.object(aurora, "ModelAdapter", FinishOnlyModel):
            aurora.run_agent(run, "live")
        self.assertEqual(run["state"], "FAILED")
        self.assertFalse(any(event["title"] == "Task completed" for event in run["events"]))
        self.assertTrue(any(event["title"] == "Completion blocked" for event in run["events"]))


if __name__ == "__main__":
    unittest.main()
