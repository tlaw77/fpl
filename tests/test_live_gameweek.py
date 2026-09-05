import unittest
from datetime import datetime, timedelta, timezone

from live_gameweek import build_snapshot, phase_for, refresh_decision


class LiveGameweekTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 5, 15, 0, tzinfo=timezone.utc)
        self.event = {"id": 3, "deadline_time": "2026-09-05T13:00:00Z"}
        self.fixtures = [{"id": 301, "team_h": 1, "team_a": 2, "kickoff_time": "2026-09-05T14:00:00Z", "minutes": 61, "started": True, "finished": False, "finished_provisional": False}]
        self.teams = [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]
        self.elements = [
            {"id": pid, "web_name": f"P{pid}", "team": 1 if pid % 2 else 2, "element_type": 3}
            for pid in range(1, 31)
        ]
        self.standings = [
            {"entry": 5332809, "rank": 2, "entry_name": "Mine", "player_name": "Terry", "event_total": 0, "total": 100},
            {"entry": 99, "rank": 1, "entry_name": "Rival", "player_name": "Rival M", "event_total": 0, "total": 102},
        ]
        mine = [{"element": pid, "multiplier": 2 if pid == 1 else (1 if pid <= 11 else 0), "is_captain": pid == 1, "is_vice_captain": pid == 2} for pid in range(1, 16)]
        rival = [{"element": pid, "multiplier": 2 if pid == 16 else (1 if pid <= 26 else 0), "is_captain": pid == 16, "is_vice_captain": pid == 17} for pid in range(16, 31)]
        self.picks = {
            5332809: {"picks": mine, "entry_history": {"event_transfers_cost": 4}},
            99: {"picks": rival, "entry_history": {"event_transfers_cost": 0}},
        }

    def snapshot(self, fixtures=None):
        live = [{"id": pid, "stats": {"total_points": 5 if pid in (1, 16) else 0, "minutes": 61}} for pid in range(1, 31)]
        return build_snapshot(event=self.event, fixtures=fixtures or self.fixtures, standings=self.standings, picks_by_entry=self.picks, elements=self.elements, teams=self.teams, live_elements=live, now=self.now)

    def test_phase_is_live(self):
        self.assertEqual(phase_for(datetime(2026, 9, 5, 13, tzinfo=timezone.utc), self.fixtures, self.now), "LIVE")

    def test_pre_deadline_hides_phase(self):
        before = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)
        self.assertEqual(phase_for(datetime(2026, 9, 5, 13, tzinfo=timezone.utc), self.fixtures, before), "PRE_DEADLINE")

    def test_scores_include_multiplier_and_hit(self):
        data = self.snapshot()
        me = data["me"]
        self.assertEqual(me["raw_gw_points"], 10)
        self.assertEqual(me["net_gw_points"], 6)
        self.assertEqual(me["live_gw_points"], 6)
        self.assertEqual(me["live_overall_points"], 106)
        self.assertEqual(data["league"]["visible_managers"], 2)

    def test_damage_per_point_is_multiplier_difference(self):
        data = self.snapshot()
        rival_captain = next(row for row in data["exposure"] if row["player_id"] == 16)
        my_captain = next(row for row in data["exposure"] if row["player_id"] == 1)
        self.assertEqual(rival_captain["damage_per_point"], 1.0)
        self.assertEqual(rival_captain["live_damage"], 5.0)
        self.assertEqual(my_captain["gain_per_point"], 1.0)

    def test_every_revealed_squad_has_fifteen(self):
        data = self.snapshot()
        self.assertTrue(all(len(manager["picks"]) == 15 for manager in data["managers"]))

    def test_exposure_includes_fixture_and_live_context(self):
        data = self.snapshot()
        rival_captain = next(row for row in data["exposure"] if row["player_id"] == 16)
        self.assertEqual(rival_captain["gw_points"], 5)
        self.assertEqual(rival_captain["minutes"], 61)
        self.assertEqual(rival_captain["fixture"]["state"], "live")
        self.assertEqual(rival_captain["fixture"]["opponent"], "Alpha")
        self.assertFalse(rival_captain["fixture"]["home"])

    def test_completed_leverage_remains_in_tracker(self):
        finished = [{**self.fixtures[0], "minutes": 90, "started": True, "finished": True}]
        data = self.snapshot(finished)
        my_captain = next(row for row in data["leverage"] if row["player_id"] == 1)
        self.assertEqual(my_captain["state"], "complete")
        self.assertEqual(my_captain["live_gain"], 5.0)

    def test_live_fixture_always_requests_refresh(self):
        previous = {"phase": "LIVE", "generated_at_utc": self.now.isoformat()}
        self.assertEqual(refresh_decision("LIVE", self.fixtures, previous, self.now), (True, "fixture live"))

    def test_between_fixtures_throttles_to_thirty_minutes(self):
        recent = {"phase": "BETWEEN_FIXTURES", "generated_at_utc": (self.now - timedelta(minutes=10)).isoformat()}
        stale = {"phase": "BETWEEN_FIXTURES", "generated_at_utc": (self.now - timedelta(minutes=26)).isoformat()}
        self.assertFalse(refresh_decision("BETWEEN_FIXTURES", self.fixtures, recent, self.now)[0])
        self.assertTrue(refresh_decision("BETWEEN_FIXTURES", self.fixtures, stale, self.now)[0])

    def test_complete_gameweek_gets_final_then_stops(self):
        finished = [{**self.fixtures[0], "kickoff_time": "2026-09-05T12:00:00Z", "finished": True}]
        previous_live = {"phase": "LIVE", "generated_at_utc": (self.now - timedelta(minutes=5)).isoformat()}
        settled = {"phase": "COMPLETE", "generated_at_utc": (self.now - timedelta(minutes=30)).isoformat()}
        self.assertTrue(refresh_decision("COMPLETE", finished, previous_live, self.now)[0])
        self.assertFalse(refresh_decision("COMPLETE", finished, settled, self.now + timedelta(hours=1))[0])


if __name__ == "__main__":
    unittest.main()
