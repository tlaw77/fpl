import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

LEAGUE_ID = 582464
MY_ENTRY_ID = 5332809
BASE = "https://fantasy.premierleague.com/api"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-etl/2.0"})
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


def pick_record(pick, players, teams, positions, slot):
    p = players.get(pick["element"], {})
    return {
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
    }


def main():
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    gw = detect_gw(bootstrap["events"])
    players = {p["id"]: {"name": p["web_name"], "team": p["team"], "position": p["element_type"], "price": p["now_cost"] / 10} for p in bootstrap["elements"]}
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

    for row in standings:
        entry_id = row["entry"]
        picks_data = get_json(f"{BASE}/entry/{entry_id}/event/{gw}/picks/")
        picks = [pick_record(p, players, teams, positions, i) for i, p in enumerate(picks_data.get("picks", []), 1)]
        if len(picks) != 15:
            raise RuntimeError(f"Entry {entry_id} returned {len(picks)} picks, expected 15")
        for p in picks:
            ownership[p["player_id"]] += 1
            if p["starter"]:
                starter_ownership[p["player_id"]] += 1
            if p["captain"]:
                captaincy[p["player_id"]] += 1
        manager_rows.append({
            "rank": row.get("rank"),
            "entry_id": entry_id,
            "team_name": row.get("entry_name"),
            "manager": row.get("player_name"),
            "gw_points": row.get("event_total"),
            "total_points": row.get("total"),
            "active_chip": picks_data.get("active_chip"),
            "picks": picks,
        })

    n = len(manager_rows)
    my_team = next(x for x in manager_rows if x["entry_id"] == MY_ENTRY_ID)
    my_ids = {p["player_id"] for p in my_team["picks"]}

    player_exposure = []
    for pid, count in ownership.most_common():
        p = players.get(pid, {})
        own_pct = round(100 * count / n, 1)
        cap_pct = round(100 * captaincy[pid] / n, 1)
        in_my_team = pid in my_ids
        if own_pct >= 62.5:
            label = "shield" if in_my_team else "danger"
        elif own_pct >= 37.5:
            label = "neutral" if in_my_team else "risk"
        else:
            label = "leverage" if in_my_team else "differential_against"
        player_exposure.append({
            "player_id": pid,
            "player": p.get("name"),
            "club": teams.get(p.get("team")),
            "position": positions.get(p.get("position")),
            "price": p.get("price"),
            "owned_by": count,
            "ownership_pct": own_pct,
            "starter_pct": round(100 * starter_ownership[pid] / n, 1),
            "captained_by": captaincy[pid],
            "captaincy_pct": cap_pct,
            "in_my_team": in_my_team,
            "classification": label,
        })

    rivals = []
    for team in manager_rows:
        if team["entry_id"] == MY_ENTRY_ID:
            continue
        ids = {p["player_id"] for p in team["picks"]}
        shared = my_ids & ids
        rivals.append({
            **{k: team[k] for k in ["rank", "entry_id", "team_name", "manager", "gw_points", "total_points", "active_chip"]},
            "overlap_count": len(shared),
            "overlap_pct": round(100 * len(shared) / 15, 1),
            "shared_players": [players[x]["name"] for x in shared],
            "captain": next((p["player"] for p in team["picks"] if p["captain"]), None),
            "vice_captain": next((p["player"] for p in team["picks"] if p["vice_captain"]), None),
            "picks": team["picks"],
        })

    result = {
        "status": "SUCCESS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_gw": gw,
        "league": {"id": LEAGUE_ID, "name": league_name, "manager_count": n},
        "me": {
            "entry_id": MY_ENTRY_ID,
            "rank": me.get("rank"),
            "team_name": me.get("entry_name"),
            "manager": me.get("player_name"),
            "gw_points": me.get("event_total"),
            "total_points": me.get("total"),
            "captain": next((p["player"] for p in my_team["picks"] if p["captain"]), None),
            "vice_captain": next((p["player"] for p in my_team["picks"] if p["vice_captain"]), None),
        },
        "squad_count": 15,
        "squad_valid": True,
        "squad": my_team["picks"],
        "rival_entry_ids": [r["entry_id"] for r in rivals],
        "rivals": rivals,
        "player_exposure": player_exposure,
    }

    out = Path("data/latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(f"data/gw{gw}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "SUCCESS", "gw": gw, "managers": n, "rivals": len(rivals), "exposure_players": len(player_exposure)}))


if __name__ == "__main__":
    main()
