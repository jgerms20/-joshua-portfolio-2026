from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/weekly-update.yml"


class WorkflowContractTests(unittest.TestCase):
    def test_workflow_checks_health_without_content_write_access(self):
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        triggers = workflow.get("on", workflow.get(True))
        jobs = workflow["jobs"]

        self.assertEqual(workflow.get("permissions"), {"contents": "read"})
        self.assertEqual(
            [item["cron"] for item in triggers["schedule"]],
            ["13 16 * * *"],
        )
        self.assertEqual(set(jobs), {"health"})

        steps = jobs["health"]["steps"]
        run_commands = "\n".join(step.get("run", "") for step in steps)
        actions = [step["uses"] for step in steps if "uses" in step]

        self.assertIn("python3 -m unittest discover -s tests -v", run_commands)
        self.assertIn(
            "python3 scripts/check-site.py --root . --json-out reports/site-health-static.json",
            run_commands,
        )
        self.assertIn("actions/upload-artifact@v4", actions)
        self.assertNotIn("scripts/update-portfolio.py", run_commands)
        self.assertNotIn("git commit", run_commands)
        self.assertNotIn("git push", run_commands)


if __name__ == "__main__":
    unittest.main()
