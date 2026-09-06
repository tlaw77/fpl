import unittest

from declared_transfer_overlay import set_transfer_state
from decision_synthesis import fixture_timing
from fpl_etl import free_transfers_for_next_gw


class FreeTransferReconstructionTests(unittest.TestCase):
    def test_rolls_and_spends_against_five_transfer_cap(self):
        history = {
            'current': [
                {'event': 2, 'event_transfers': 0},
                {'event': 3, 'event_transfers': 1},
                {'event': 4, 'event_transfers': 0},
                {'event': 5, 'event_transfers': 0},
                {'event': 6, 'event_transfers': 0},
                {'event': 7, 'event_transfers': 0},
            ],
            'chips': [],
        }
        self.assertEqual(free_transfers_for_next_gw(history, 3), 2)
        self.assertEqual(free_transfers_for_next_gw(history, 7), 5)

    def test_wildcard_and_free_hit_preserve_pre_chip_bank(self):
        history = {
            'current': [
                {'event': 2, 'event_transfers': 0},
                {'event': 3, 'event_transfers': 9},
                {'event': 4, 'event_transfers': 0},
                {'event': 5, 'event_transfers': 11},
            ],
            'chips': [
                {'event': 3, 'name': 'wildcard'},
                {'event': 5, 'name': 'freehit'},
            ],
        }
        self.assertEqual(free_transfers_for_next_gw(history, 3), 2)
        self.assertEqual(free_transfers_for_next_gw(history, 5), 3)

    def test_overlay_uses_reconstructed_bank(self):
        data = {'next_gw': 4, 'free_transfers_next_gw': 2}
        set_transfer_state(data, [{'event': 4}])
        self.assertEqual(data['free_transfers_available_before_moves'], 2)
        self.assertEqual(data['free_transfers_remaining_next_gw'], 1)
        self.assertEqual(data['next_transfer_hit_cost'], 0)


class FixtureTimingTests(unittest.TestCase):
    def test_front_loaded_fixture_swing(self):
        latest = {
            'next_gw': 4,
            'current_squad_next5': [
                {'player': 'Outgoing', 'fixtures': [
                    {'gw': 4, 'difficulty': 5},
                    {'gw': 5, 'difficulty': 4},
                    {'gw': 6, 'difficulty': 3},
                ]},
            ],
        }
        pool = {'players': [
            {'player': 'Incoming', 'fixtures': [
                {'gw': 4, 'difficulty': 2},
                {'gw': 5, 'difficulty': 3},
                {'gw': 6, 'difficulty': 3},
            ]},
        ]}
        result = fixture_timing('Outgoing → Incoming', latest, pool)
        self.assertTrue(result['available'])
        self.assertEqual(result['timing'], 'front_loaded')
        self.assertEqual(result['next_fixture_swing'], 3)


if __name__ == '__main__':
    unittest.main()
