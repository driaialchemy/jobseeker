import json
import unittest
from dataclasses import asdict
from datetime import datetime, timezone

from jobseeker import build_plan, main
from job_search import (
    JobListing,
    find_english_evidence,
    is_global_remote,
    keep_listing,
)


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

    def test_global_remote_filter_requires_explicit_global_signal(self):
        self.assertTrue(is_global_remote("Worldwide", ""))
        self.assertTrue(is_global_remote("Remote", "Work from anywhere."))
        self.assertFalse(is_global_remote("United States", "Remote role for US candidates."))
        self.assertFalse(is_global_remote("Canada", "Work from anywhere after onboarding."))

    def test_english_evidence_rejects_non_english_language_roles(self):
        self.assertTrue(find_english_evidence("Analyst", "Fluent English communication required."))
        self.assertFalse(find_english_evidence("Online Data Analyst French Language", "French speakers required."))

    def test_keep_listing_enforces_recent_global_english_filters(self):
        listing = JobListing(
            source="test",
            title="Data Analyst",
            company="Example",
            url="https://example.com/job",
            location="Worldwide",
            published_at="2026-06-07T12:00:00+00:00",
            description="Remote global role requiring fluent English communication.",
            tags=["data"],
            match_score=3,
            keyword_matches=["data"],
            english_evidence=["fluent English communication"],
        )

        now = datetime(2026, 6, 8, tzinfo=timezone.utc)
        self.assertTrue(keep_listing(listing, days=3, now=now))


if __name__ == "__main__":
    unittest.main()
