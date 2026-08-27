import json
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent import data_service
from gtm_agent.gtm_agent import (
    ProspectScore,
    build_prospect_profile,
    score_prospect,
    update_prospect_info,
)


class RescoreAfterUpdateTest(unittest.TestCase):
    def setUp(self):
        data_service._PROFILES.clear()
        data_service.PROSPECTS["LEAD-39002"]["tech_stack"] = [
            "Databricks", "Kubernetes", "Redis", "Segment", "AWS"
        ]

    def tearDown(self):
        data_service._PROFILES.clear()
        data_service.PROSPECTS["LEAD-39002"]["tech_stack"] = [
            "Databricks", "Kubernetes", "Redis", "Segment", "AWS"
        ]

    def test_rescore_uses_confirmed_technology(self):
        profile = build_prospect_profile.invoke({"prospect_id": "LEAD-39002"})[
            "prospect_profile"
        ]
        offering = {
            "required_tech_stack": ["Terraform", "AWS", "Kubernetes", "Segment"],
            "min_annual_revenue": 50_000_000,
            "description": "Cloud automation",
        }
        scores = []

        def fake_invoke(messages):
            profile_text = json.loads(messages[1]["content"].split("\n\nProspect profile:\n", 1)[1])
            has_terraform = "Terraform" in profile_text["tech_stack"]
            scores.append(has_terraform)
            return ProspectScore(
                score=100 if has_terraform else 85,
                justification="Missing Terraform" if not has_terraform else "Has Terraform",
                rubric_breakdown={
                    "revenue_fit": 100,
                    "tech_stack_match": 100 if has_terraform else 75,
                    "segment_fit": 100,
                },
            )

        with patch("gtm_agent.gtm_agent._scoring_llm", Mock(invoke=fake_invoke)):
            baseline = score_prospect.invoke({"prospect_profile": profile, "offering": offering})
            update = update_prospect_info.invoke({
                "prospect_id": "LEAD-39002", "technology": "Terraform"
            })
            updated_profile = build_prospect_profile.invoke({
                "prospect_id": "LEAD-39002"
            })["prospect_profile"]
            rescored = score_prospect.invoke({
                "prospect_profile": updated_profile, "offering": offering
            })

        self.assertTrue(update["updated"])
        self.assertEqual(scores, [False, True])
        self.assertIn("Missing Terraform", baseline["justification"])
        self.assertNotIn("Missing Terraform", rescored["justification"])
        self.assertGreater(
            rescored["rubric_breakdown"]["tech_stack_match"],
            baseline["rubric_breakdown"]["tech_stack_match"],
        )


if __name__ == "__main__":
    unittest.main()
