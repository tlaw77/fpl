# Live Gameweek Command Centre runbook

## Purpose

Give Terry one post-deadline view of all eight revealed squads, calculated live scores, live mini-league rank, players remaining, captain/chip exposure, active threats and personal leverage.

## Automatic operation

1. GitHub Actions runs `live_gameweek.py` every five minutes.
2. Before the official deadline it publishes `PRE_DEADLINE` and does not request or expose squads.
3. After lock it requests the official standings, all manager picks, fixtures and event-live points.
4. It writes only `data/live_gameweek.json`; the heavier decision pipeline remains independent.
5. The browser polls the artifact every five minutes. In `LOCKED`, `LIVE`, `BETWEEN_FIXTURES` or `COMPLETE`, League Intel becomes **Live GW** and opens the command centre once per page load.

## Operator checks

| Check | Expected |
|---|---|
| Workflow | Latest **Live Gameweek** run is green |
| Coverage | `visible_managers` equals `expected_managers` (currently 8) |
| Squads | Each visible manager has exactly 15 picks |
| Freshness | `generated_at_utc` is within 10 minutes during a live match |
| Scores | Captain/triple-captain/bench-boost multipliers appear in `effective_points` |
| Status | Fixtures move from upcoming → live → complete |

## Threat interpretation

`damage_per_point = max(league-average multiplier - your multiplier, 0)`.

Example: four of eight managers captain a player and you do not own him. The league-average multiplier is `1.0`, so each point he scores costs you one point versus the league average. This is an exposure measure, not a prediction.

`gain_per_point` is the mirror calculation for your leverage. `live_damage` and `live_gain` multiply those rates by points already scored.

The scoring grid leads with **player points**. Transfer deductions are shown separately as “hit” and “net”; the net value continues to drive live overall points and rank. This prevents a legitimate large transfer hit from making the score build-up itself appear broken or negative.

## Incident response

- **PARTIAL / fewer than 8 teams:** wait for the next five-minute retry. Immediately after deadline the FPL picks endpoints can reveal at different times.
- **Stale score:** check the official FPL event-live endpoint, then rerun **Live Gameweek** manually.
- **Workflow push conflict:** the job rebases and retries three times. If still red, rerun it after the main 30-minute ETL finishes.
- **Wrong rank:** verify `official total - official GW total + calculated live GW score`; bonus and autosubs remain provisional until FPL finalises them.
- **UI unavailable:** `data/live_gameweek.json` is independent; inspect it directly while GitHub Pages catches up.

## Validation before release

Run:

```bash
python -m unittest tests.test_live_gameweek -v
node --check docs/live-gameweek-stage108.js
python -c "import yaml; yaml.safe_load(open('.github/workflows/live-gameweek.yml'))"
```

Then inspect desktop and 390px mobile widths. Confirm there is one command centre, all manager accordions open, and no horizontal overflow.
