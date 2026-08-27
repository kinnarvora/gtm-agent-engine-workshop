import json
import os
import re
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent import data_service, gtm_agent


class _ScoringResult:
    def model_dump(self):
        return {"score": 80, "max_score": 100, "justification": "good fit"}


class _ScoringModel:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return _ScoringResult()


class ProspectPrivacyTests(unittest.TestCase):
    def setUp(self):
        data_service._PROFILES.clear()

    def test_lookup_tools_return_only_allowlisted_fields(self):
        prospect_result = gtm_agent.get_prospect.invoke({"prospect_id": "LEAD-50003"})
        profile_result = gtm_agent.build_prospect_profile.invoke({"prospect_id": "LEAD-39002"})

        for result, key in ((prospect_result, "prospect"), (profile_result, "prospect_profile")):
            serialized = json.dumps(result)
            self.assertNotIn("billing_qualification", serialized)
            for sensitive_key in ("tax_id", "date_of_birth", "card_on_file", "credit_check_ref"):
                self.assertNotIn(sensitive_key, serialized)
            self.assertTrue(set(result[key]).issubset(set(data_service.PROSPECT_FIELDS)))

    def test_scoring_prompt_contains_only_scoring_inputs(self):
        scoring_model = _ScoringModel()
        offering = {
            "offering_id": "OFFER-10004",
            "required_tech_stack": ["AWS"],
            "min_annual_revenue": 1,
            "description": "Automate infrastructure.",
        }

        with patch.object(gtm_agent, "_scoring_llm", scoring_model):
            gtm_agent.score_prospect.invoke({
                "annual_revenue": 50000000,
                "tech_stack": ["AWS"],
                "segment": "Enterprise",
                "offering": offering,
            })

        prompt = scoring_model.messages[1]["content"]
        self.assertNotIn("prospect_profile", prompt)
        self.assertIsNone(re.search(r"\b\d{3}-\d{2}-\d{4}\b", prompt))
        self.assertIsNone(re.search(r"\b\d{16}\b", prompt))
        self.assertEqual(json.loads(prompt.split("Prospect scoring inputs:\n", 1)[1]), {
            "annual_revenue": 50000000,
            "tech_stack": ["AWS"],
            "segment": "Enterprise",
        })


if __name__ == "__main__":
    unittest.main()
