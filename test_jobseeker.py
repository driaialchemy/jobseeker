import json
import unittest
from dataclasses import asdict

from jobseeker import build_plan, main


class JobseekerTests(unittest.TestCase):
    def test_build_plan_identifies_data_skill_gaps(self):
        plan = build_plan("Data Analyst", ["Python", "SQL"])

        self.assertEqual(plan.target_role, "Data Analyst")
        self.assertEqual(plan.strengths, ["python", "sql"])
        self.assertIn("excel", plan.gaps)
        self.assertTrue(plan.next_steps)

    def test_blank_role_is_rejected(self):
        with self.assertRaises(ValueError):
            build_plan("   ")

    def test_json_output_is_serializable(self):
        plan = build_plan("AI Analyst", ["python"])
        payload = json.loads(json.dumps(asdict(plan)))

        self.assertEqual(payload["target_role"], "AI Analyst")
        self.assertIsInstance(payload["next_steps"], list)

    def test_cli_smoke_path_returns_success(self):
        self.assertEqual(main(["Data Analyst", "--skills", "python", "sql"]), 0)


if __name__ == "__main__":
    unittest.main()
