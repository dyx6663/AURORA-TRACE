import json
import tempfile
import unittest
from pathlib import Path

from aurora import ToolExecutor, contract_for, profile_project, safe_path, safe_zip_member


class CoreSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        (self.workspace / "demo.py").write_text("value = 1\n", encoding="utf-8")
        self.tools = ToolExecutor(self.workspace)

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


if __name__ == "__main__":
    unittest.main()
