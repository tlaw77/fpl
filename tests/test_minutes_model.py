import unittest
from unittest.mock import Mock
from minutes_model import profile, collect, participation
from projection_calibration import expected_gw


def history(minutes):
    return [{'gw': i+1, 'minutes': m, 'starts': int(m >= 45)} for i,m in enumerate(minutes)]


class MinutesModelTests(unittest.TestCase):
    def test_cherki_recent_nonappearance_and_early_sub(self):
        review = profile(history([65, 45, 84, 90, 0, 45]))
        self.assertEqual(review['recent_minutes'], [90, 0, 45])
        self.assertLess(review['factor'], .85)
        self.assertGreater(review['no_appearance_estimate'], .05)
        self.assertGreater(review['short_appearance_estimate'], .10)

    def test_regular_starter_and_regular_cameos_not_discounted_twice(self):
        self.assertEqual(profile(history([90]*6))['factor'], 1)
        self.assertEqual(profile(history([20]*6))['factor'], 1)
        self.assertEqual(profile(history([0,0]))['status'], 'insufficient')

    def test_workload_and_fitness_use_strongest_constraint(self):
        player = {'availability':1, 'adjusted_availability':.88, 'schedule_modifier':.88,
                  'minutes_review': {'status':'observed', 'factor':.75}}
        self.assertEqual(participation(player, .88)[0], .75)
        self.assertEqual(participation(player, .40)[0], .40)
        player['availability']=.25
        self.assertEqual(participation(player, .25)[0], .25)
        player['availability']=0
        self.assertEqual(participation(player, 0)[0], 0)

    def test_blanks_doubles_unfinished_and_feed_failure(self):
        boot={'events':[{'id':1,'finished':True},{'id':2,'finished':True},{'id':3,'finished':False}]}
        def feed(url):
            return {'elements':[{'id':1,'stats':{'minutes':0,'starts':0},'explain':[]},
                                {'id':2,'stats':{'minutes':90,'starts':1},'explain':[{}]},
                                {'id':3,'stats':{'minutes':180,'starts':2},'explain':[{},{}]}]}
        get=Mock(side_effect=feed)
        rows, coverage=collect(boot,get,3)
        self.assertNotIn(1,rows);self.assertNotIn(3,rows)
        self.assertEqual(rows[2]['sample_matches'],2)
        self.assertEqual(get.call_count,2)
        rows, coverage=collect(boot,Mock(side_effect=RuntimeError('offline')),3)
        self.assertEqual(len(coverage['failures']),2)
        self.assertEqual(coverage['observed_players'],0)

    def test_shared_projection_penalizes_dnp_risk_not_fitness_label(self):
        p={'player_id':1,'position':'MID','points_per_game':6,'availability':1,
           'adjusted_availability':1,'schedule_modifier':1,'fixtures':[{'gw':9,'difficulty':3}],
           'sample_reliability':.7,'six_gw_score':20}
        args=(9,10,30,({},{}),({},{}))
        original=expected_gw(p,*args,current_gw=8)
        p['minutes_review']=profile(history([65,45,84,90,0,45]))
        adjusted=expected_gw(p,*args,current_gw=8)
        self.assertLess(adjusted[0],original[0]);self.assertGreater(adjusted[1],original[1])


if __name__ == '__main__':
    unittest.main()
