import unittest
from datetime import datetime, timezone, timedelta
from short_term_risk import build, readiness, availability
from projection_calibration import expected_gw
from press_conference_watch import player_aliases, match_players


class ShortTermRiskTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
        self.latest = {'next_gw': 9, 'squad': [{'player_id': 1}]}
        self.player = {'player_id': 1, 'player': 'Test', 'position': 'MID',
                       'availability': 1, 'adjusted_availability': .8,
                       'fixtures': [{'gw': 9}, {'gw': 10}]}
        self.review = {'player_id': 1, 'player': 'Test', 'next_gw': 9,
                       'checked_at_utc': self.now.isoformat(),
                       'valid_until_utc': (self.now+timedelta(hours=24)).isoformat(),
                       'sources': [{'url': 'https://www.chelseafc.com/news'}],
                       'availability_caps_by_gw': {'9': .5}, 'unresolved': True}

    def test_gw_specific_cap_and_no_double_discount(self):
        self.player['availability_by_gw'] = {'9': .5, '10': .9}
        self.assertEqual(availability(self.player, 9), .5)
        self.assertEqual(availability(self.player, 10), .8)
        baseline = dict(self.player, availability_by_gw={})
        args = (9, 0, 100, ({}, {}), ({}, {}))
        self.assertAlmostEqual(expected_gw(self.player, *args)[0]/expected_gw(baseline, *args)[0], .5/.8)

    def test_dated_evidence_and_readiness(self):
        pool = {'players': [self.player]}
        report = build(self.latest, pool, {'players': [self.review]}, self.now)
        self.assertEqual(self.player['availability_by_gw'], {'9': .5})
        self.assertFalse(readiness(report, 9, self.now)[0])
        self.assertFalse(readiness(report, 10, self.now)[0])
        self.assertFalse(readiness(report, 9, self.now+timedelta(hours=7))[0])
        report = build(self.latest, pool, {'players': [self.review]}, self.now+timedelta(days=2))
        self.assertNotIn('availability_by_gw', self.player)
        self.assertEqual(report['expired_reviews'], ['Test'])
        self.assertFalse(readiness(report, 9, self.now+timedelta(days=2))[0])

    def test_unsourced_or_future_reviews_never_change_projection(self):
        self.review['sources'] = []
        build(self.latest, {'players': [self.player]}, {'players': [self.review]}, self.now)
        self.assertNotIn('availability_by_gw', self.player)
        self.review['sources'] = [{'url': 'https://example.com'}]
        self.review['checked_at_utc'] = (self.now+timedelta(days=1)).isoformat()
        build(self.latest, {'players': [self.player]}, {'players': [self.review]}, self.now)
        self.assertNotIn('availability_by_gw', self.player)

    def test_aliases_include_full_names_and_accents(self):
        aliases = player_aliases([{'player_id': 165, 'player': 'João Pedro'},
                                 {'player_id': 426, 'player': 'B.Fernandes', 'full_name': 'Bruno Fernandes'}])
        self.assertEqual(match_players('Joao Pedro injured; Bruno Fernandes benched', aliases), [165, 426])


if __name__ == '__main__':
    unittest.main()
