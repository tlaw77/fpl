import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from decision_twin import VALID_VERDICTS, build


class DecisionTwinContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = [
            "latest", "decision_synthesis", "simulation", "path_simulation",
            "adaptive_rival_simulation", "chip_activation_gate", "captaincy_review",
            "market", "scout_consensus", "press_conference_watch",
            "simulation_stability", "backtest_summary",
        ]
        cls.inputs = {name: json.loads((Path("data") / f"{name}.json").read_text()) for name in names}
        cls.output = build(cls.inputs, now=datetime(2026, 9, 4, 14, 0, tzinfo=timezone.utc))

    def test_complete_and_successful(self):
        self.assertEqual(self.output["status"], "SUCCESS")
        self.assertEqual(self.output["progress"]["completion_pct"], 100)
        self.assertEqual(self.output["progress"]["state"], "COMPLETE")

    def test_certificate_is_auditable(self):
        certificate = self.output["decision_certificate"]
        self.assertTrue(certificate["certificate_id"].startswith("DT-"))
        self.assertTrue(certificate["action"])
        self.assertTrue(certificate["headline"])
        self.assertTrue(certificate["rationale"])
        self.assertGreater(certificate["evidence"]["sources_available"], 0)

    def test_six_specialists_have_valid_contracts(self):
        council = self.output["council"]
        self.assertEqual(len(council), 6)
        self.assertEqual(len({row["agent"] for row in council}), 6)
        for row in council:
            self.assertIn(row["verdict"], VALID_VERDICTS)
            self.assertGreaterEqual(row["confidence"], 0)
            self.assertLessEqual(row["confidence"], 100)
            self.assertTrue(row["argument"])

    def test_change_radar_has_actionable_breakers(self):
        breakers = self.output["change_radar"]["decision_breakers"]
        self.assertGreaterEqual(len(breakers), 3)
        self.assertGreaterEqual(sum(row["priority"] == "high" for row in breakers), 2)
        self.assertTrue(all(row["review_when"] for row in breakers))

    def test_learning_contract_freezes_legal_xi_and_captain(self):
        contract = self.output["learning_contract"]
        xi = {int(value) for value in contract["baseline_xi_ids"]}
        self.assertEqual(len(xi), 11)
        self.assertIn(int(contract["baseline_captain_id"]), xi)
        self.assertFalse(contract["tuning_allowed"])
        self.assertEqual(contract["learning_stage"], "collecting")

    def test_same_inputs_produce_same_certificate(self):
        again = build(self.inputs, now=datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc))
        self.assertEqual(
            self.output["decision_certificate"]["certificate_id"],
            again["decision_certificate"]["certificate_id"],
        )


if __name__ == "__main__":
    unittest.main()
