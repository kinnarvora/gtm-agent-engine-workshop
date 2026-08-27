import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from gtm_agent.gtm_agent import send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(config={})
        self.prospect = {
            "prospect_id": "LEAD-12853",
            "name": "Omar Okafor",
            "email": "omar.okafor@example.com",
        }
        self.from_rep = {"name": "Test Rep", "email": "rep@example.com"}

    def test_disqualified_prospect_requires_override(self):
        prospect = {**self.prospect, "prospect_id": "LEAD-50001"}

        result = send_prospect_email.func(
            prospect,
            "Subject",
            "Body",
            self.runtime,
            self.from_rep,
        )

        self.assertEqual(result["status"], "refused")
        self.assertIn("disqualified: true", result["error"])

    def test_non_disqualified_prospect_sends_normally(self):
        result = send_prospect_email.func(
            self.prospect,
            "Subject",
            "Body",
            self.runtime,
            self.from_rep,
        )

        self.assertEqual(result["status"], "sent")
