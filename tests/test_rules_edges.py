import unittest

from chip_activation_gate import gate_wc
from chip_window import free_hit_eligible
from strategy_watch import chip_inventory


class ChipRuleEdgeTests(unittest.TestCase):
    def test_gw20_uses_fresh_second_half_chip_set(self):
        chips = [{"name": name, "event": 19} for name in ("wildcard", "freehit", "3xc", "bboost")]
        inventory = chip_inventory(chips, 20)
        self.assertEqual(inventory["half"], 2)
        self.assertEqual(inventory["remaining_count"], 4)
        self.assertTrue(inventory["free_hit_consecutive_blocked"])

    def test_consecutive_free_hit_is_hard_blocked(self):
        inventory = chip_inventory([{"name": "freehit", "event": 19}], 20)
        self.assertFalse(free_hit_eligible(inventory))
        self.assertTrue(free_hit_eligible(chip_inventory([], 20)))

    def test_wildcard_gate_counts_hit_points_it_would_erase(self):
        latest = {
            "next_gw": 8,
            "transfer_hits_already_incurred_next_gw": 8,
            "current_squad_next5": [{"player_id": i} for i in range(1, 16)],
            "deadline_context": {"phase": "deadline_day"},
        }
        full = {
            "best_wildcard": {
                "squad": [{"player_id": i} for i in range(1, 16)],
                "incremental_expected_points_vs_current_squad": 20,
                "bank_left": 1.5,
            },
            "season_maturity_weight": .5,
            "budget_confidence": "exact",
        }
        chip_window = {"portfolio": {"pressure": "comfortable"}, "evaluations": [
            {"chip": "Wildcard", "current_window": {"weak_assets": 1}}
        ]}
        stability = {"summary": {"effective_evidence_runs": 3, "wc_latest_squad_persistence_pct": 80}}
        result = gate_wc(latest, chip_window, full, stability)
        self.assertEqual(result["transfer_hit_rescue"], 8)
        self.assertAlmostEqual(result["activation_value_including_hit_rescue"], result["activation_adjusted_gain_6gw"] + 8, places=2)


if __name__ == "__main__":
    unittest.main()
