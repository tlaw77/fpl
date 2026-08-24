import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LEAGUE_ID = 582464
MY_ENTRY_ID = 5332809
BASE = "https://fantasy.premierleague.com/api"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-etl/1.0"})
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
    page = 1
    rows = []
    league_name = None
    while True:
        data = get_json(f"{BASE}/leagues-classic/{LEAGUE_ID}/standings/?page_standings={page}")
        league_name = league_name or data.get("league", {}).get("name")
        standings = data.get("standings", {})
        rows.extend(standings.get("results", []))
        if not standings.get("has_next"):
            break
        page += 1
    return league_name, rows


def main():
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    gw = detect_gw(bootstrap["events"])

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

    picks = get_json(f"{BASE}/entry/{MY_ENTRY_ID}/event/{gw}/picks/")
    squad = []
    for slot, pick in enumerate(picks.get("picks", []), start=1):
        p = players.get(pick["element"], {})
        squad.append({
            "slot": slot,
            "player_id": pick["element"],
            "player": p.get("name"),
            "club": teams.get(p.get("team")),
            "position": positions.get(p.get("position")),
            "price": p.get("price"),
            "multiplier": pick.get("multiplier"),
            "captain": bool(pick.get("is_captain")),
            "vice_captain": bool(pick.get("is_vice_captain")),
            "starter": pick.get("multiplier", 0) > 0,
        })

    rivals = [
        {
            "rank": r.get("rank"),
            "entry_id": r.get("entry"),
            "team_name": r.get("entry_name"),
            "manager": r.get("player_name"),
            "gw_points": r.get("event_total"),
            "total_points": r.get("total"),
        }
        for r in standings
        if r.get("entry") != MY_ENTRY_ID
    ]

    result = {
        "status": "SUCCESS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_gw": gw,
        "league": {
            "id": LEAGUE_ID,
            "name": league_name,
            "manager_count": len(standings),
        },
        "me": {
            "entry_id": MY_ENTRY_ID,
            "rank": me.get("rank"),
            "team_name": me.get("entry_name"),
            "manager": me.get("player_name"),
            "gw_points": me.get("event_total"),
            "total_points": me.get("total"),
        },
        "squad_count": len(squad),
        "squad_valid": len(squad) == 15,
        "squad": squad,
        "rival_entry_ids": [r["entry_id"] for r in rivals],
        "rivals": rivals,
    }

    out = Path("data/latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": result["status"],
        "gw": gw,
        "league": league_name,
        "managers": len(standings),
        "squad_count": len(squad),
        "squad_valid": len(squad) == 15,
    }))


if __name__ == "__main__":
    main()
