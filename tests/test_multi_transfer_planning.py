import unittest
from unittest.mock import patch

import decision_synthesis as ds
import path_simulation as ps


class MultiTransferPlanningTests(unittest.TestCase):
    def fake_candidates(self, state, _remaining, _pool, _exp, limit=10):
        ids = {x['player_id'] for x in state['squad']}
        if ids == {1, 10}:
            return [{
                'out': {'player_id': 1}, 'in': {'player_id': 2},
                'squad': [{'player_id': 2}, {'player_id': 10}], 'bank': 1.0,
                'uplift': 2.0, 'label': 'A → B',
            }]
        if ids == {2, 10}:
            return [{
                'out': {'player_id': 10}, 'in': {'player_id': 11},
                'squad': [{'player_id': 2}, {'player_id': 11}], 'bank': 1.0,
                'uplift': 1.0, 'label': 'X → Y',
            }]
        return []

    def test_two_free_transfers_create_no_hit_double_route(self):
        state = {'squad': [{'player_id': 1}, {'player_id': 10}], 'bank': 1.0, 'ft': 2}
        with patch.object(ps, 'transfer_candidates', side_effect=self.fake_candidates):
            sequences = ps.deadline_transfer_sequences(state, [5, 6], [], {})
        double = next(x for x in sequences if len(x['moves']) == 2)
        action = ps.transfer_action(5, double['moves'], 0)
        self.assertEqual(action['transfer_count'], 2)
        self.assertEqual(action['route'], 'A → B + X → Y')
        self.assertEqual(action['hit'], 0)

    def test_option_portfolio_exposes_now_multiple_and_staged(self):
        roll = {'actions': [{'gw': 5, 'action': 'ROLL'}, {'gw': 6, 'action': 'TRANSFER', 'route': 'A → B'}], 'expected_points': 20, 'utility_score': 20}
        one = {'actions': [{'gw': 5, 'action': 'TRANSFER', 'route': 'A → B', 'transfer_count': 1}, {'gw': 6, 'action': 'TRANSFER', 'route': 'C → D'}], 'expected_points': 23, 'utility_score': 23}
        multi = {'actions': [{'gw': 5, 'action': 'TRANSFER', 'route': 'A → B + C → D', 'transfer_count': 2, 'transfers': [{}, {}]}], 'expected_points': 25, 'utility_score': 25}
        paths = {'paths': [multi, one, roll], 'recommendation': multi}
        adaptive = {'recommendation': {'actions': multi['actions']}}
        options = {x['key']: x for x in ds.build_transfer_options(paths, adaptive, 5, 2, 5)}
        self.assertTrue(options['roll']['available'])
        self.assertTrue(options['one_now']['available'])
        self.assertTrue(options['multiple_now']['available'])
        self.assertTrue(options['staged']['available'])
        self.assertEqual(options['multiple_now']['edge_vs_roll'], 5)
        self.assertEqual(options['multiple_now']['free_transfers_after_deadline'], 1)
        self.assertTrue(options['multiple_now']['adaptive_support'])


if __name__ == '__main__':
    unittest.main()
