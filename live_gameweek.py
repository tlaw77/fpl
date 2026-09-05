"""Build the lightweight post-deadline FPL command-centre snapshot."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEAGUE_ID = 582464
MY_ENTRY_ID = 5332809
BASE = "https://fantasy.premierleague.com/api"
OUTPUT = Path("data/live_gameweek.json")


def get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "fpl-live-command-centre/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def monitored_event(events: list[dict], now: datetime) -> dict:
    current = next((event for event in events if event.get("is_current") and not event.get("finished")), None)
    nxt = next((event for event in events if event.get("is_next")), None)
    if nxt and (not current or current.get("finished")):
        return nxt
    if nxt and parse_time(nxt.get("deadline_time")) and now >= parse_time(nxt["deadline_time"]):
        return nxt
    if current:
        return current
    unfinished = [event for event in events if not event.get("finished")]
    if unfinished:
        return unfinished[0]
    return events[-1]


def phase_for(deadline: datetime | None, fixtures: list[dict], now: datetime) -> str:
    if deadline and now < deadline:
        return "PRE_DEADLINE"
    if fixtures and all(f.get("finished") or f.get("finished_provisional") for f in fixtures):
        return "COMPLETE"
    if any(f.get("started") and not (f.get("finished") or f.get("finished_provisional")) for f in fixtures):
        return "LIVE"
    if any(f.get("finished") or f.get("finished_provisional") for f in fixtures):
        return "BETWEEN_FIXTURES"
    return "LOCKED"


def refresh_decision(phase: str, fixtures: list[dict], previous: dict | None, now: datetime) -> tuple[bool, str]:
    """Choose the expensive snapshot cadence from the official fixture state."""
    if phase == "PRE_DEADLINE":
        return False, "before deadline"
    if phase == "LIVE":
        return True, "fixture live"

    previous = previous or {}
    previous_phase = previous.get("phase")
    generated = parse_time(previous.get("generated_at_utc"))
    age = now - generated if generated else None

    if phase in ("LOCKED", "BETWEEN_FIXTURES"):
        if previous_phase != phase:
            return True, f"phase changed to {phase.lower()}"
        if age is None or age >= timedelta(minutes=25):
            return True, "between-match refresh due"
        return False, "between-match snapshot still fresh"

    if phase == "COMPLETE":
        if previous_phase != "COMPLETE":
            return True, "final score refresh"
        kickoffs = [parse_time(fixture.get("kickoff_time")) for fixture in fixtures]
        last_kickoff = max((kickoff for kickoff in kickoffs if kickoff), default=None)
        settling = bool(last_kickoff and now <= last_kickoff + timedelta(hours=3))
        if settling and (age is None or age >= timedelta(minutes=25)):
            return True, "post-match bonus settlement"
        return False, "gameweek settled"

    return False, "unknown phase"


def fixture_state(fixture: dict) -> str:
    if fixture.get("finished") or fixture.get("finished_provisional"):
        return "complete"
    if fixture.get("started"):
        return "live"
    return "upcoming"


def player_state(team_id: int | None, fixtures_by_team: dict[int, list[dict]]) -> str:
    fixtures = fixtures_by_team.get(int(team_id or 0), [])
    states = {fixture_state(fixture) for fixture in fixtures}
    if "live" in states:
        return "live"
    if "upcoming" in states:
        return "upcoming"
    if states and states == {"complete"}:
        return "complete"
    return "unknown"


def build_snapshot(
    *,
    event: dict,
    fixtures: list[dict],
    standings: list[dict],
    picks_by_entry: dict[int, dict],
    elements: list[dict],
    teams: list[dict],
    live_elements: list[dict],
    previous: dict | None = None,
    now: datetime | None = None,
    league_name: str = "Mini League",
) -> dict:
    now = now or datetime.now(timezone.utc)
    deadline = parse_time(event.get("deadline_time"))
    phase = phase_for(deadline, fixtures, now)
    team_names = {team["id"]: team["name"] for team in teams}
    raw_players = {player["id"]: player for player in elements}
    live_stats = {row["id"]: row.get("stats") or {} for row in live_elements}
    live_points = {player_id: int(stats.get("total_points") or 0) for player_id, stats in live_stats.items()}
    fixtures_by_team: dict[int, list[dict]] = defaultdict(list)
    for fixture in fixtures:
        fixtures_by_team[int(fixture["team_h"])].append(fixture)
        fixtures_by_team[int(fixture["team_a"])].append(fixture)

    def fixture_context(team_id: int | None) -> dict | None:
        team_id = int(team_id or 0)
        rows = fixtures_by_team.get(team_id, [])
        if not rows:
            return None
        ordered = sorted(rows, key=lambda row: row.get("kickoff_time") or "")
        chosen = next((row for row in ordered if fixture_state(row) == "live"), None)
        chosen = chosen or next((row for row in ordered if fixture_state(row) == "upcoming"), None)
        chosen = chosen or ordered[-1]
        home = int(chosen.get("team_h") or 0) == team_id
        opponent_id = int(chosen.get("team_a") if home else chosen.get("team_h") or 0)
        return {
            "fixture_id": chosen.get("id"),
            "state": fixture_state(chosen),
            "kickoff_utc": chosen.get("kickoff_time"),
            "opponent": team_names.get(opponent_id, "—"),
            "home": home,
            "minutes": int(chosen.get("minutes") or 0),
        }

    ownership, captaincy, multiplier_totals = Counter(), Counter(), Counter()
    managers = []
    failures = []
    visible_standings = standings if phase != "PRE_DEADLINE" else []
    for standing in visible_standings:
        entry_id = int(standing["entry"])
        picks_data = picks_by_entry.get(entry_id)
        if not picks_data or len(picks_data.get("picks") or []) != 15:
            failures.append({"entry_id": entry_id, "team_name": standing.get("entry_name"), "reason": "squad_not_revealed"})
            continue
        picks = []
        for slot, pick in enumerate(picks_data["picks"], 1):
            player_id = int(pick["element"])
            raw = raw_players.get(player_id, {})
            multiplier = int(pick.get("multiplier") or 0)
            points = live_points.get(player_id, 0)
            item = {
                "slot": slot,
                "player_id": player_id,
                "player": raw.get("web_name") or f"Player {player_id}",
                "club": team_names.get(raw.get("team"), "—"),
                "team_id": raw.get("team"),
                "position_id": raw.get("element_type"),
                "multiplier": multiplier,
                "captain": bool(pick.get("is_captain")),
                "vice_captain": bool(pick.get("is_vice_captain")),
                "starter": multiplier > 0,
                "live_points": points,
                "effective_points": points * multiplier,
                "state": player_state(raw.get("team"), fixtures_by_team),
            }
            picks.append(item)
            ownership[player_id] += 1
            multiplier_totals[player_id] += multiplier
            if item["captain"]:
                captaincy[player_id] += 1
        history = picks_data.get("entry_history") or {}
        hit_cost = int(history.get("event_transfers_cost") or 0)
        raw_score = sum(item["effective_points"] for item in picks)
        live_score = raw_score - hit_cost
        official_gw = int(standing.get("event_total") or 0)
        official_total = int(standing.get("total") or 0)
        baseline = official_total - official_gw
        active = [item for item in picks if item["multiplier"] > 0]
        managers.append({
            "entry_id": entry_id,
            "official_rank": standing.get("rank"),
            "team_name": standing.get("entry_name"),
            "manager": standing.get("player_name"),
            "active_chip": picks_data.get("active_chip"),
            "hit_cost": hit_cost,
            "raw_gw_points": raw_score,
            "net_gw_points": live_score,
            "live_gw_points": live_score,
            "live_overall_points": baseline + live_score,
            "players_complete": sum(item["state"] == "complete" for item in active),
            "players_live": sum(item["state"] == "live" for item in active),
            "players_remaining": sum(item["state"] in ("live", "upcoming", "unknown") for item in active),
            "captain": next((item["player"] for item in picks if item["captain"]), None),
            "picks": picks,
        })

    managers.sort(key=lambda row: (-row["live_overall_points"], int(row.get("official_rank") or 999999)))
    for rank, manager in enumerate(managers, 1):
        manager["live_rank"] = rank
    me = next((manager for manager in managers if manager["entry_id"] == MY_ENTRY_ID), None)
    my_multiplier = {pick["player_id"]: pick["multiplier"] for pick in (me or {}).get("picks", [])}
    manager_count = len(standings)
    exposures = []
    for player_id in sorted(ownership, key=lambda pid: (-multiplier_totals[pid], raw_players.get(pid, {}).get("web_name", ""))):
        raw = raw_players.get(player_id, {})
        avg_multiplier = multiplier_totals[player_id] / max(1, manager_count)
        mine = my_multiplier.get(player_id, 0)
        damage_per_point = max(0.0, avg_multiplier - mine)
        gain_per_point = max(0.0, mine - avg_multiplier)
        points = live_points.get(player_id, 0)
        owners = []
        captains = []
        for manager in managers:
            pick = next((item for item in manager["picks"] if item["player_id"] == player_id), None)
            if pick:
                owners.append(manager["team_name"])
                if pick["captain"]:
                    captains.append(manager["team_name"])
        exposures.append({
            "player_id": player_id,
            "player": raw.get("web_name") or f"Player {player_id}",
            "club": team_names.get(raw.get("team"), "—"),
            "state": player_state(raw.get("team"), fixtures_by_team),
            "live_points": points,
            "gw_points": points,
            "minutes": int(live_stats.get(player_id, {}).get("minutes") or 0),
            "fixture": fixture_context(raw.get("team")),
            "owned_by": ownership[player_id],
            "captained_by": captaincy[player_id],
            "effective_ownership_pct": round(100 * avg_multiplier, 1),
            "my_multiplier": mine,
            "damage_per_point": round(damage_per_point, 3),
            "gain_per_point": round(gain_per_point, 3),
            "live_damage": round(points * damage_per_point, 2),
            "live_gain": round(points * gain_per_point, 2),
            "owners": owners,
            "captains": captains,
        })

    active_threats = sorted(
        (row for row in exposures if row["damage_per_point"] > 0 and row["state"] != "complete"),
        key=lambda row: (-row["damage_per_point"], -row["effective_ownership_pct"], row["player"]),
    )
    damage_done = sorted(
        (row for row in exposures if row["live_damage"] > 0),
        key=lambda row: (-row["live_damage"], -row["damage_per_point"], row["player"]),
    )
    state_order = {"live": 0, "upcoming": 1, "complete": 2, "unknown": 3}
    leverage = sorted(
        (row for row in exposures if row["gain_per_point"] > 0),
        key=lambda row: (-row["live_gain"], state_order.get(row["state"], 3), -row["gain_per_point"], row["effective_ownership_pct"], row["player"]),
    )
    previous_points = {int(row["player_id"]): int(row.get("live_points") or 0) for row in (previous or {}).get("exposure", [])}
    swings = []
    for row in exposures:
        delta = row["live_points"] - previous_points.get(row["player_id"], row["live_points"])
        impact = round(delta * (row["gain_per_point"] - row["damage_per_point"]), 2)
        if delta:
            swings.append({"player_id": row["player_id"], "player": row["player"], "points_delta": delta, "impact_on_you": impact})
    swings.sort(key=lambda row: (-abs(row["impact_on_you"]), row["player"]))

    fixture_counts = Counter(fixture_state(fixture) for fixture in fixtures)
    avg_live = round(sum(manager["live_gw_points"] for manager in managers) / max(1, len(managers)), 2)
    avg_raw = round(sum(manager["raw_gw_points"] for manager in managers) / max(1, len(managers)), 2)
    return {
        "status": "SUCCESS" if not failures else "PARTIAL",
        "version": 2,
        "generated_at_utc": now.isoformat(),
        "gw": int(event["id"]),
        "phase": phase,
        "picks_visible": phase != "PRE_DEADLINE",
        "provisional": phase in ("LOCKED", "LIVE", "BETWEEN_FIXTURES"),
        "refresh_seconds": 300,
        "deadline_utc": deadline.isoformat() if deadline else None,
        "league": {"id": LEAGUE_ID, "name": league_name, "expected_managers": manager_count, "visible_managers": len(managers), "average_live_points": avg_live, "average_raw_live_points": avg_raw, "average_net_live_points": avg_live},
        "fixtures": {"total": len(fixtures), "complete": fixture_counts["complete"], "live": fixture_counts["live"], "upcoming": fixture_counts["upcoming"]},
        "me": me,
        "managers": managers,
        "threats": active_threats[:12],
        "damage_done": damage_done[:12],
        "leverage": leverage[:12],
        "recent_swings": swings[:12],
        "exposure": exposures,
        "failures": failures,
        "methodology": {
            "raw_score": "Sum of official live player points × FPL multiplier.",
            "live_score": "Raw score minus transfer hit cost; this net score drives live rank.",
            "live_overall": "Official total minus official GW total, plus calculated live GW score.",
            "damage_per_point": "League-average multiplier minus your multiplier, floored at zero.",
            "remaining": "Active picks whose club fixture is live, upcoming or awaiting status; multipliers follow the official revealed squad.",
            "fixture_context": "Each tracked player carries their live or next GW fixture, kickoff, opponent, minutes, GW points and realised EO-adjusted impact.",
        },
    }


def fetch_standings() -> tuple[str, list[dict]]:
    page, rows, name = 1, [], "Mini League"
    while True:
        payload = get_json(f"{BASE}/leagues-classic/{LEAGUE_ID}/standings/?page_standings={page}")
        name = payload.get("league", {}).get("name") or name
        standings = payload.get("standings") or {}
        rows.extend(standings.get("results") or [])
        if not standings.get("has_next"):
            return name, rows
        page += 1


def main() -> None:
    now = datetime.now(timezone.utc)
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    event = monitored_event(bootstrap["events"], now)
    fixtures = [fixture for fixture in get_json(f"{BASE}/fixtures/?event={event['id']}") if int(fixture.get("event") or 0) == int(event["id"])]
    deadline = parse_time(event.get("deadline_time"))
    phase = phase_for(deadline, fixtures, now)
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else None
    previous_for_event = previous if previous and previous.get("gw") == event["id"] else None
    if "--gate" in sys.argv:
        should_run, reason = refresh_decision(phase, fixtures, previous_for_event, now)
        print(f"run={str(should_run).lower()}")
        print(f"phase={phase}")
        print(f"reason={reason}")
        return
    league_name, standings = fetch_standings()
    picks_by_entry = {}
    failures = []
    if phase != "PRE_DEADLINE":
        for standing in standings:
            entry_id = int(standing["entry"])
            try:
                picks_by_entry[entry_id] = get_json(f"{BASE}/entry/{entry_id}/event/{event['id']}/picks/")
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
                failures.append({"entry_id": entry_id, "reason": type(error).__name__})
    live = get_json(f"{BASE}/event/{event['id']}/live/") if phase != "PRE_DEADLINE" else {"elements": []}
    snapshot = build_snapshot(event=event, fixtures=fixtures, standings=standings, picks_by_entry=picks_by_entry, elements=bootstrap["elements"], teams=bootstrap["teams"], live_elements=live.get("elements") or [], previous=previous_for_event, now=now, league_name=league_name)
    if failures:
        snapshot["status"] = "PARTIAL"
        snapshot["failures"].extend(failures)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": snapshot["status"], "gw": snapshot["gw"], "phase": snapshot["phase"], "visible_managers": snapshot["league"]["visible_managers"], "threats": len(snapshot["threats"])}))


if __name__ == "__main__":
    main()
