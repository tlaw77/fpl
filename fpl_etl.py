import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

LEAGUE_ID = 582464
MY_ENTRY_ID = 5332809
BASE = "https://fantasy.premierleague.com/api"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-etl/3.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def detect_gw(events):
    current = next((e for e in events if e.get("is_current")), None)
    if current:
        return current["id"]
    nxt = next((e for e in events if e.get("is_next")), None)
    if nxt:
        return max(1, nxt["id"] - 1)
    finished = [e["id"] for e in events if e.get("finished")]
    return max(finished) if finished else 1


def fetch_all_standings():
    page, rows, league_name = 1, [], None
    while True:
        data = get_json(f"{BASE}/leagues-classic/{LEAGUE_ID}/standings/?page_standings={page}")
        league_name = league_name or data.get("league", {}).get("name")
        s = data.get("standings", {})
        rows.extend(s.get("results", []))
        if not s.get("has_next"):
            return league_name, rows
        page += 1


def pick_record(pick, players, teams, positions, slot, live_points):
    p = players.get(pick["element"], {})
    multiplier = pick.get("multiplier", 0)
    pts = live_points.get(pick["element"], 0)
    return {
        "slot": slot,
        "player_id": pick["element"],
        "player": p.get("name"),
        "club": teams.get(p.get("team")),
        "position": positions.get(p.get("position")),
        "price": p.get("price"),
        "multiplier": multiplier,
        "captain": bool(pick.get("is_captain")),
        "vice_captain": bool(pick.get("is_vice_captain")),
        "starter": multiplier > 0,
        "live_points": pts,
        "effective_points": pts * multiplier,
    }


def classify(in_my_team, own_pct, effective_ownership_pct, my_multiplier):
    # Effective ownership matters more than raw squad ownership because captaincy
    # changes how strongly a player's points move the mini-league.
    if in_my_team:
        if effective_ownership_pct >= 75:
            return "shield"
        if effective_ownership_pct >= 40:
            return "neutral"
        if my_multiplier >= 2:
            return "aggressive_leverage"
        return "leverage"
    if effective_ownership_pct >= 75:
        return "major_danger"
    if effective_ownership_pct >= 40:
        return "danger"
    if own_pct >= 25:
        return "risk"
    return "differential_against"


def main():
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    gw = detect_gw(bootstrap["events"])
    live = get_json(f"{BASE}/event/{gw}/live/")
    live_points = {x["id"]: x.get("stats", {}).get("total_points", 0) for x in live.get("elements", [])}

    players = {
        p["id"]: {
            "name": p["web_name"],
            "team": p["team"],
            "position": p["element_type"],
            "price": p["now_cost"] / 10,
        }
        for p in bootstrap["elements"]
    }
    teams = {t["id"]: t["name"] for t in bootstrap["teams"]}
    positions = {p["id"]: p["singular_name_short"] for p in bootstrap["element_types"]}

    league_name, standings = fetch_all_standings()
    me = next((r for r in standings if r.get("entry") == MY_ENTRY_ID), None)
    if me is None:
        raise RuntimeError(f"Entry {MY_ENTRY_ID} not found in league {LEAGUE_ID}")

    manager_rows = []
    ownership = Counter()
    starter_ownership = Counter()
    captaincy = Counter()
    total_multiplier = defaultdict(int)

    for row in standings:
        entry_id = row["entry"]
        picks_data = get_json(f"{BASE}/entry/{entry_id}/event/{gw}/picks/")
        picks = [
            pick_record(p, players, teams, positions, i, live_points)
            for i, p in enumerate(picks_data.get("picks", []), 1)
        ]
        if len(picks) != 15:
            raise RuntimeError(f"Entry {entry_id} returned {len(picks)} picks, expected 15")

        for p in picks:
            ownership[p["player_id"]] += 1
            total_multiplier[p["player_id"]] += p["multiplier"]
            if p["starter"]:
                starter_ownership[p["player_id"]] += 1
            if p["captain"]:
                captaincy[p["player_id"]] += 1

        hist = picks_data.get("entry_history", {}) or {}
        live_score = sum(p["effective_points"] for p in picks) - (hist.get("event_transfers_cost") or 0)
        manager_rows.append({
            "rank": row.get("rank"),
            "entry_id": entry_id,
            "team_name": row.get("entry_name"),
            "manager": row.get("player_name"),
            "gw_points": row.get("event_total"),
            "total_points": row.get("total"),
            "active_chip": picks_data.get("active_chip"),
            "event_transfers": hist.get("event_transfers"),
            "event_transfers_cost": hist.get("event_transfers_cost"),
            "points_on_bench": hist.get("points_on_bench"),
            "team_value": (hist.get("value") / 10) if hist.get("value") is not None else None,
            "bank": (hist.get("bank") / 10) if hist.get("bank") is not None else None,
            "live_calculated_points": live_score,
            "picks": picks,
        })

    n = len(manager_rows)
    my_team = next(x for x in manager_rows if x["entry_id"] == MY_ENTRY_ID)
    my_ids = {p["player_id"] for p in my_team["picks"]}
    my_multiplier = {p["player_id"]: p["multiplier"] for p in my_team["picks"]}

    player_exposure = []
    for pid, count in ownership.most_common():
        p = players.get(pid, {})
        own_pct = round(100 * count / n, 1)
        cap_pct = round(100 * captaincy[pid] / n, 1)
        eo_pct = round(100 * total_multiplier[pid] / n, 1)
        mine = my_multiplier.get(pid, 0)
        avg_multiplier = total_multiplier[pid] / n
        pts = live_points.get(pid, 0)
        swing = round(pts * (mine - avg_multiplier), 2)
        in_my_team = pid in my_ids

        player_exposure.append({
            "player_id": pid,
            "player": p.get("name"),
            "club": teams.get(p.get("team")),
            "position": positions.get(p.get("position")),
            "price": p.get("price"),
            "live_points": pts,
            "owned_by": count,
            "ownership_pct": own_pct,
            "starter_pct": round(100 * starter_ownership[pid] / n, 1),
            "captained_by": captaincy[pid],
            "captaincy_pct": cap_pct,
            "effective_ownership_pct": eo_pct,
            "my_multiplier": mine,
            "in_my_team": in_my_team,
            "points_swing_vs_league_avg": swing,
            "classification": classify(in_my_team, own_pct, eo_pct, mine),
        })

    player_exposure.sort(key=lambda x: (-x["effective_ownership_pct"], -x["ownership_pct"], x["player"] or ""))

    rivals = []
    for team in manager_rows:
        if team["entry_id"] == MY_ENTRY_ID:
            continue
        ids = {p["player_id"] for p in team["picks"]}
        shared = my_ids & ids
        rivals.append({
            **{k: team[k] for k in [
                "rank", "entry_id", "team_name", "manager", "gw_points", "total_points",
                "active_chip", "event_transfers", "event_transfers_cost", "points_on_bench",
                "team_value", "bank", "live_calculated_points"
            ]},
            "gap_to_me": (team.get("total_points") or 0) - (me.get("total") or 0),
            "overlap_count": len(shared),
            "overlap_pct": round(100 * len(shared) / 15, 1),
            "shared_players": sorted(players[x]["name"] for x in shared),
            "captain": next((p["player"] for p in team["picks"] if p["captain"]), None),
            "vice_captain": next((p["player"] for p in team["picks"] if p["vice_captain"]), None),
            "picks": team["picks"],
        })

    rivals.sort(key=lambda x: (x["rank"] if x["rank"] is not None else 999999, x["entry_id"]))

    my_player_swings = [x for x in player_exposure if x["in_my_team"]]
    biggest_gains = sorted(my_player_swings, key=lambda x: x["points_swing_vs_league_avg"], reverse=True)[:5]
    biggest_threats = sorted(
        [x for x in player_exposure if not x["in_my_team"]],
        key=lambda x: (x["points_swing_vs_league_avg"], -x["effective_ownership_pct"]),
    )[:5]

    league_live_scores = [x["live_calculated_points"] for x in manager_rows]
    league_avg_live = round(sum(league_live_scores) / n, 2) if n else 0

    result = {
        "status": "SUCCESS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_gw": gw,
        "league": {
            "id": LEAGUE_ID,
            "name": league_name,
            "manager_count": n,
            "average_live_calculated_points": league_avg_live,
        },
        "me": {
            "entry_id": MY_ENTRY_ID,
            "rank": me.get("rank"),
            "team_name": me.get("entry_name"),
            "manager": me.get("player_name"),
            "gw_points": me.get("event_total"),
            "total_points": me.get("total"),
            "captain": next((p["player"] for p in my_team["picks"] if p["captain"]), None),
            "vice_captain": next((p["player"] for p in my_team["picks"] if p["vice_captain"]), None),
            "active_chip": my_team.get("active_chip"),
            "event_transfers": my_team.get("event_transfers"),
            "event_transfers_cost": my_team.get("event_transfers_cost"),
            "points_on_bench": my_team.get("points_on_bench"),
            "team_value": my_team.get("team_value"),
            "bank": my_team.get("bank"),
            "live_calculated_points": my_team.get("live_calculated_points"),
            "live_vs_league_average": round(my_team.get("live_calculated_points", 0) - league_avg_live, 2),
        },
        "squad_count": 15,
        "squad_valid": True,
        "squad": my_team["picks"],
        "rival_entry_ids": [r["entry_id"] for r in rivals],
        "rivals": rivals,
        "player_exposure": player_exposure,
        "decision_signals": {
            "biggest_current_gains_vs_league": biggest_gains,
            "biggest_current_threats_not_owned": biggest_threats,
            "major_dangers_not_owned": [x for x in player_exposure if x["classification"] == "major_danger"],
            "my_leverage_players": [x for x in player_exposure if x["classification"] in {"leverage", "aggressive_leverage"}],
            "my_shields": [x for x in player_exposure if x["classification"] == "shield"],
        },
    }

    out = Path("data/latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    out.write_text(payload, encoding="utf-8")
    Path(f"data/gw{gw}.json").write_text(payload, encoding="utf-8")

    print(json.dumps({
        "status": "SUCCESS",
        "gw": gw,
        "managers": n,
        "rivals": len(rivals),
        "exposure_players": len(player_exposure),
        "league_avg_live": league_avg_live,
        "my_live": my_team.get("live_calculated_points"),
    }))


if __name__ == "__main__":
    main()
