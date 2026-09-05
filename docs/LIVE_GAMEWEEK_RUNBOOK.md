# Live Gameweek Command Centre runbook

## Purpose

Give Terry one post-deadline view of every revealed mini-league squad, calculated live scores, live mini-league rank, players remaining, captain/chip exposure, active threats and personal leverage.

## Automatic operation

1. GitHub Actions targets `live_gameweek.py` every five minutes, offset to minutes 02, 07, 12 … 57 to avoid the busiest top-of-hour minute.
2. Before the official deadline it publishes `PRE_DEADLINE` and does not request or expose squads.
3. After lock it requests the official standings, all manager picks, fixtures and event-live points.
4. It writes only `data/live_gameweek.json`; the heavier decision pipeline remains independent.
5. The browser checks for a new live snapshot every minute while the command centre is active and every five minutes outside it. It also checks immediately when the page becomes visible again.
6. The compact freshness line says when the scores were produced. At more than eight minutes old it changes to **update delayed**.

The page reads the raw live JSON directly from the repository, so it does not wait for the GitHub Pages build to finish. A normal visible update is: GitHub schedule wait (0–5 minutes) + snapshot job (about 15 seconds) + browser check (0–1 minute). GitHub schedules are targets rather than guarantees, so the stale indicator is the operational source of truth.

## Workflow map

| Workflow | Configured cadence | Role | Live-GW priority |
|---|---:|---|---|
| **Live Gameweek** | Every 5 minutes | Official points, fixtures, revealed squads, threats and leverage | Critical |
| **FPL ETL** | Every 30 minutes | Full data and modelling pipeline | Background |
| **FPL Decision Twin** | Every 15 minutes | Current recommendation layer | Background |
| **Press Conference Watch** | Every 15 minutes Thu/Fri 07:00–19:45 UTC | Team-news changes | Low while matches are live |
| **Simulation Stability** | After each successful ETL | Model confidence checks | Low while matches are live |
| **Medium-Term Unlock Challenger** | After each successful ETL | Multi-week alternatives | Low while matches are live |
| **Elite FPL Benchmark** | After each successful ETL | Strategy comparison | Low while matches are live |
| **Fixture Calendar Intelligence** | After each successful ETL | Fixture/chip calendar | Low while matches are live |

### Cadence policy

- Live points use the lightweight five-minute workflow; the open page checks every minute.
- Prediction workflows must not be used as the live-score clock.
- Any future cadence change should be made in this table and the matching workflow together.
- Prefer one authoritative upstream trigger for modelling jobs. Multiple schedules plus multiple completion triggers can create duplicate runs and cancelled deployments.

## Operator checks

| Check | Expected |
|---|---|
| Workflow | Latest **Live Gameweek** run is green |
| Coverage | `visible_managers` equals `expected_managers` |
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
