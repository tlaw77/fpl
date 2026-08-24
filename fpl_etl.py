import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

LEAGUE_ID = 582464
MY_ENTRY_ID = 5332809
BASE = "https://fantasy.premierleague.com/api"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-etl/5.0"})
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


def fixtures_by_team(fixtures, teams, start_gw, count=5):
    out = defaultdict(list)
    for f in fixtures:
        gw = f.get("event")
        if gw is None or gw < start_gw or gw >= start_gw + count:
            continue
        for team_id, opp_id, venue, diff_key in [
            (f["team_h"], f["team_a"], "H", "team_h_difficulty"),
            (f["team_a"], f["team_h"], "A", "team_a_difficulty"),
        ]:
            out[team_id].append({"gw": gw, "opponent": teams.get(opp_id), "opponent_id": opp_id, "venue": venue, "difficulty": f.get(diff_key), "kickoff_time": f.get("kickoff_time")})
    for team_id in out:
        out[team_id].sort(key=lambda x: x["gw"])
    return out


def pick_record(pick, players, teams, positions, slot, live_points):
    p = players.get(pick["element"], {})
    multiplier = pick.get("multiplier", 0)
    pts = live_points.get(pick["element"], 0)
    return {"slot": slot, "player_id": pick["element"], "player": p.get("name"), "club": teams.get(p.get("team")), "position": positions.get(p.get("position")), "position_id": p.get("position"), "team_id": p.get("team"), "price": p.get("price"), "multiplier": multiplier, "captain": bool(pick.get("is_captain")), "vice_captain": bool(pick.get("is_vice_captain")), "starter": multiplier > 0, "live_points": pts, "effective_points": pts * multiplier}


def classify(in_my_team, own_pct, eo_pct, my_multiplier):
    if in_my_team:
        if eo_pct >= 75: return "shield"
        if eo_pct >= 40: return "neutral"
        if my_multiplier >= 2: return "aggressive_leverage"
        return "leverage"
    if eo_pct >= 75: return "major_danger"
    if eo_pct >= 40: return "danger"
    if own_pct >= 25: return "risk"
    return "differential_against"


def decision_score(player, fixture_list, ownership_pct=0):
    availability = (player.get("chance_of_playing_next_round") if player.get("chance_of_playing_next_round") is not None else 100) / 100
    diffs = [f.get("difficulty") or 3 for f in fixture_list[:5]]
    ease = 6 - (sum(diffs) / len(diffs) if diffs else 3)
    form = float(player.get("form") or 0)
    ppg = float(player.get("points_per_game") or 0)
    selected = float(player.get("selected_by_percent") or 0)
    return round(form * 1.7 + ppg * 1.3 + ease * 1.6 + availability * 2.2 + selected * 0.03 + ownership_pct * 0.015, 3)


def main():
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    gw = detect_gw(bootstrap["events"])
    next_gw = min(38, gw + 1)
    live = get_json(f"{BASE}/event/{gw}/live/")
    fixtures = get_json(f"{BASE}/fixtures/")
    live_points = {x["id"]: x.get("stats", {}).get("total_points", 0) for x in live.get("elements", [])}
    raw_players = {p["id"]: p for p in bootstrap["elements"]}
    players = {p["id"]: {"name": p["web_name"], "team": p["team"], "position": p["element_type"], "price": p["now_cost"] / 10} for p in bootstrap["elements"]}
    teams = {t["id"]: t["name"] for t in bootstrap["teams"]}
    positions = {p["id"]: p["singular_name_short"] for p in bootstrap["element_types"]}
    fixture_map = fixtures_by_team(fixtures, teams, next_gw, 5)

    league_name, standings = fetch_all_standings()
    me = next((r for r in standings if r.get("entry") == MY_ENTRY_ID), None)
    if me is None: raise RuntimeError(f"Entry {MY_ENTRY_ID} not found in league {LEAGUE_ID}")

    manager_rows, ownership, starter_ownership, captaincy, total_multiplier = [], Counter(), Counter(), Counter(), defaultdict(int)
    for row in standings:
        entry_id = row["entry"]
        picks_data = get_json(f"{BASE}/entry/{entry_id}/event/{gw}/picks/")
        picks = [pick_record(p, players, teams, positions, i, live_points) for i, p in enumerate(picks_data.get("picks", []), 1)]
        if len(picks) != 15: raise RuntimeError(f"Entry {entry_id} returned {len(picks)} picks, expected 15")
        for p in picks:
            ownership[p["player_id"]] += 1; total_multiplier[p["player_id"]] += p["multiplier"]
            if p["starter"]: starter_ownership[p["player_id"]] += 1
            if p["captain"]: captaincy[p["player_id"]] += 1
        hist = picks_data.get("entry_history", {}) or {}
        live_score = sum(p["effective_points"] for p in picks) - (hist.get("event_transfers_cost") or 0)
        manager_rows.append({"rank": row.get("rank"), "entry_id": entry_id, "team_name": row.get("entry_name"), "manager": row.get("player_name"), "gw_points": row.get("event_total"), "total_points": row.get("total"), "active_chip": picks_data.get("active_chip"), "event_transfers": hist.get("event_transfers"), "event_transfers_cost": hist.get("event_transfers_cost"), "points_on_bench": hist.get("points_on_bench"), "team_value": (hist.get("value") / 10) if hist.get("value") is not None else None, "bank": (hist.get("bank") / 10) if hist.get("bank") is not None else None, "live_calculated_points": live_score, "picks": picks})

    n = len(manager_rows)
    my_team = next(x for x in manager_rows if x["entry_id"] == MY_ENTRY_ID)
    my_ids = {p["player_id"] for p in my_team["picks"]}
    my_multiplier = {p["player_id"]: p["multiplier"] for p in my_team["picks"]}

    player_exposure = []
    for pid, count in ownership.most_common():
        p = players.get(pid, {}); own_pct = round(100 * count / n, 1); cap_pct = round(100 * captaincy[pid] / n, 1); eo_pct = round(100 * total_multiplier[pid] / n, 1); mine = my_multiplier.get(pid, 0); pts = live_points.get(pid, 0); in_my_team = pid in my_ids
        player_exposure.append({"player_id": pid, "player": p.get("name"), "club": teams.get(p.get("team")), "position": positions.get(p.get("position")), "price": p.get("price"), "live_points": pts, "owned_by": count, "ownership_pct": own_pct, "starter_pct": round(100 * starter_ownership[pid] / n, 1), "captained_by": captaincy[pid], "captaincy_pct": cap_pct, "effective_ownership_pct": eo_pct, "my_multiplier": mine, "in_my_team": in_my_team, "points_swing_vs_league_avg": round(pts * (mine - total_multiplier[pid] / n), 2), "classification": classify(in_my_team, own_pct, eo_pct, mine)})
    exposure_by_id = {x["player_id"]: x for x in player_exposure}

    rivals = []
    for team in manager_rows:
        if team["entry_id"] == MY_ENTRY_ID: continue
        ids = {p["player_id"] for p in team["picks"]}; shared = my_ids & ids
        rivals.append({**{k: team[k] for k in ["rank", "entry_id", "team_name", "manager", "gw_points", "total_points", "active_chip", "event_transfers", "event_transfers_cost", "points_on_bench", "team_value", "bank", "live_calculated_points"]}, "gap_to_me": (team.get("total_points") or 0) - (me.get("total") or 0), "overlap_count": len(shared), "overlap_pct": round(100 * len(shared) / 15, 1), "shared_players": sorted(players[x]["name"] for x in shared), "captain": next((p["player"] for p in team["picks"] if p["captain"]), None), "vice_captain": next((p["player"] for p in team["picks"] if p["vice_captain"]), None), "picks": team["picks"]})
    rivals.sort(key=lambda x: (x["rank"] if x["rank"] is not None else 999999, x["entry_id"]))

    targets = sorted([r for r in rivals if (r["total_points"] or 0) > (me.get("total") or 0)], key=lambda r: (r["total_points"] or 0) - (me.get("total") or 0))[:3]
    target_ids = {r["entry_id"] for r in targets}; target_ownership, target_captaincy = Counter(), Counter()
    for r in rivals:
        if r["entry_id"] in target_ids:
            for p in r["picks"]:
                target_ownership[p["player_id"]] += 1
                if p["captain"]: target_captaincy[p["player_id"]] += 1

    squad_next5 = []
    for p in my_team["picks"]:
        raw = raw_players[p["player_id"]]; item = dict(p); item["availability"] = (raw.get("chance_of_playing_next_round") if raw.get("chance_of_playing_next_round") is not None else 100) / 100; item["news"] = raw.get("news") or ""; item["fixtures"] = fixture_map.get(p["team_id"], [])[:5]; diffs = [f["difficulty"] or 3 for f in item["fixtures"]]; item["fixture_ease_next5"] = round(6 - (sum(diffs) / len(diffs) if diffs else 3), 2); item["decision_score"] = decision_score(raw, item["fixtures"], exposure_by_id.get(p["player_id"], {}).get("ownership_pct", 0)); squad_next5.append(item)

    candidate_pool = []
    bank = my_team.get("bank") or 0
    for pid, raw in raw_players.items():
        if pid in my_ids or raw.get("status") == "u": continue
        pos_id = raw["element_type"]; own_pct = exposure_by_id.get(pid, {}).get("ownership_pct", 0); base = decision_score(raw, fixture_map.get(raw["team"], []), own_pct); target_pct = round(100 * target_ownership[pid] / max(1, len(targets)), 1)
        candidate_pool.append({"player_id": pid, "player": raw["web_name"], "club": teams[raw["team"]], "position": positions[pos_id], "position_id": pos_id, "price": raw["now_cost"] / 10, "availability": (raw.get("chance_of_playing_next_round") if raw.get("chance_of_playing_next_round") is not None else 100) / 100, "news": raw.get("news") or "", "fixtures": fixture_map.get(raw["team"], [])[:5], "decision_score": base, "mini_league_ownership_pct": own_pct, "target_rival_ownership_pct": target_pct, "target_captain_count": target_captaincy[pid], "protective_score": round(base + target_pct * 0.055 + target_captaincy[pid] * 1.2, 3), "chase_score": round(base + (100 - target_pct) * 0.035 + max(0, 30 - own_pct) * 0.025, 3)})

    moves = []
    for outp in squad_next5:
        max_price = outp["price"] + bank; same_pos = [c for c in candidate_pool if c["position_id"] == outp["position_id"] and c["price"] <= max_price and c["availability"] >= 0.75]
        if not same_pos: continue
        safe = max(same_pos, key=lambda c: c["protective_score"]); chase = max(same_pos, key=lambda c: c["chase_score"])
        moves.append({"out": {"player": outp["player"], "price": outp["price"], "decision_score": outp["decision_score"], "position": outp["position"]}, "safe_in": safe, "aggressive_in": chase, "safe_gain": round(safe["protective_score"] - outp["decision_score"], 3), "aggressive_gain": round(chase["chase_score"] - outp["decision_score"], 3)})

    captain_pool = []
    for p in squad_next5:
        if p["availability"] < 0.75 or p["position_id"] == 1: continue
        exp = exposure_by_id.get(p["player_id"], {}); target_pct = round(100 * target_ownership[p["player_id"]] / max(1, len(targets)), 1)
        captain_pool.append({**p, "mini_league_eo": exp.get("effective_ownership_pct", 0), "target_rival_ownership_pct": target_pct, "target_captain_count": target_captaincy[p["player_id"]], "protective_captain_score": round(p["decision_score"] + target_pct * 0.055 + target_captaincy[p["player_id"]] * 1.5, 3), "chase_captain_score": round(p["decision_score"] + (100 - target_pct) * 0.035 + max(0, 40 - exp.get("effective_ownership_pct", 0)) * 0.02, 3)})

    league_live_scores = [x["live_calculated_points"] for x in manager_rows]; league_avg_live = round(sum(league_live_scores) / n, 2) if n else 0
    result = {"status": "SUCCESS", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "current_gw": gw, "next_gw": next_gw, "league": {"id": LEAGUE_ID, "name": league_name, "manager_count": n, "average_live_calculated_points": league_avg_live}, "me": {"entry_id": MY_ENTRY_ID, "rank": me.get("rank"), "team_name": me.get("entry_name"), "manager": me.get("player_name"), "gw_points": me.get("event_total"), "total_points": me.get("total"), "captain": next((p["player"] for p in my_team["picks"] if p["captain"]), None), "vice_captain": next((p["player"] for p in my_team["picks"] if p["vice_captain"]), None), "active_chip": my_team.get("active_chip"), "event_transfers": my_team.get("event_transfers"), "event_transfers_cost": my_team.get("event_transfers_cost"), "points_on_bench": my_team.get("points_on_bench"), "team_value": my_team.get("team_value"), "bank": my_team.get("bank"), "live_calculated_points": my_team.get("live_calculated_points"), "live_vs_league_average": round(my_team.get("live_calculated_points", 0) - league_avg_live, 2)}, "squad_count": 15, "squad_valid": True, "squad": my_team["picks"], "squad_next5": sorted(squad_next5, key=lambda x: x["decision_score"]), "rivals": rivals, "player_exposure": sorted(player_exposure, key=lambda x: (-x["effective_ownership_pct"], -x["ownership_pct"], x["player"] or "")), "target_rivals": [{"entry_id": r["entry_id"], "team_name": r["team_name"], "manager": r["manager"], "rank": r["rank"], "gap": r["gap_to_me"]} for r in targets], "next_gw_decisions": {"model_note": "Heuristic decision support using FPL form/PPG, fixture difficulty, availability, mini-league ownership and ownership among the nearest three managers above you. It is not projected points.", "captain_protective": sorted(captain_pool, key=lambda x: x["protective_captain_score"], reverse=True)[:5], "captain_chase": sorted(captain_pool, key=lambda x: x["chase_captain_score"], reverse=True)[:5], "safe_moves": sorted(moves, key=lambda m: m["safe_gain"], reverse=True)[:5], "aggressive_moves": sorted(moves, key=lambda m: m["aggressive_gain"], reverse=True)[:5]}}
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"; Path("data").mkdir(parents=True, exist_ok=True); Path("data/latest.json").write_text(payload, encoding="utf-8"); Path(f"data/gw{gw}.json").write_text(payload, encoding="utf-8")
    print(json.dumps({"status": "SUCCESS", "gw": gw, "next_gw": next_gw, "targets": len(targets), "safe_moves": len(result["next_gw_decisions"]["safe_moves"]), "aggressive_moves": len(result["next_gw_decisions"]["aggressive_moves"])}))


if __name__ == "__main__":
    main()
