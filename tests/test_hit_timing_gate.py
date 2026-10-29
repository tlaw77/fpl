import unittest
from decision_synthesis import hit_timing_gate

class HitTimingTests(unittest.TestCase):
    def options(self, edge):
        return [{'key':'roll','available':True,'expected_points':246.22},
                {'key':'one_now','available':True,'expected_points':246.22+edge,
                 'first_action':{'action':'TRANSFER','route':'Hughes → Tavernier'}}]

    def test_long_hold_edge_does_not_justify_paying_now(self):
        result = hit_timing_gate(self.options(1.07), 'Hughes → Tavernier', 4, 4.5)
        self.assertFalse(result['clear'])
        self.assertEqual(result['edge_vs_wait'], 1.07)

    def test_strong_timing_edge_can_justify_hit(self):
        self.assertTrue(hit_timing_gate(self.options(5), 'Hughes → Tavernier', 4, 4.5)['clear'])

    def test_missing_or_different_route_cannot_validate_hit(self):
        self.assertFalse(hit_timing_gate([], 'Hughes → Tavernier', 4, 4.5)['clear'])
        self.assertFalse(hit_timing_gate(self.options(9), 'Maguire → Konsa', 4, 4.5)['clear'])

    def test_free_transfer_keeps_existing_gate(self):
        self.assertTrue(hit_timing_gate([], 'Hughes → Tavernier', 0, 2)['clear'])

if __name__ == '__main__':
    unittest.main()
