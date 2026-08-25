import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://fantasy.premierleague.com/api"
ENTRY_ID = 5332809


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-current-squad/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def decision_score(player, fixture_list, ownership_pct=0):
    availability = (player.get("chance_of_playing_next_round") if player.get("chance_of_playing_next_round") is not None else 100) / 100
    diffs = [f.get("difficulty") or 3 for f in fixture_list[:5]]
    ease = 6 - (sum(diffs) / len(diffs) if diffs else 3)
    form = float(player.get("form") or 0)
    ppg = float(player.get("points_per_game") or 0)
    selected = float(player.get("selected_by_percent") or 0)
    return round(form * 1.7 + ppg * 1.3 + ease * 1.6 + availability * 2.2 + selected * 0.03 + ownership_pct * 0.015, 3)


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
            out[team_id].append({
                "gw": gw,
                "opponent": teams.get(opp_id),
                "opponent_id": opp_id,
                "venue": venue,
                "difficulty": f.get(diff_key),
                "kickoff_time": f.get("kickoff_time"),
            })
    for team_id in out:
        out[team_id].sort(key=lambda x: x["gw"])
    return out


def exposure_maps(data):
    expo = {x["player_id"]: x for x in data.get("player_exposure", [])}
    targets = data.get("target_rivals", [])
    target_ids = {x.get("entry_id") for x in targets}
    target_own = Counter()
    target_cap = Counter()
    for r in data.get("rivals", []):
        if r.get("entry_id") not in target_ids:
            continue
        for p in r.get("picks", []):
            target_own[p["player_id"]] += 1
            if p.get("captain"):
                target_cap[p["player_id"]] += 1
    return expo, target_own, target_cap, max(1, len(targets))


def enriched_player(pid, raw_players, teams, positions, fixture_map, expo, target_own, target_cap, target_n):
    raw = raw_players[pid]
    own_pct = expo.get(pid, {}).get("ownership_pct", 0)
    fixtures = fixture_map.get(raw["team"], [])[:5]
    base = decision_score(raw, fixtures, own_pct)
    target_pct = round(100 * target_own[pid] / target_n, 1)
    return {
        "player_id": pid,
        "player": raw["web_name"],
        "club": teams[raw["team"]],
        "position": positions[raw["element_type"]],
        "position_id": raw["element_type"],
        "team_id": raw["team"],
        "price": raw["now_cost"] / 10,
        "availability": (raw.get("chance_of_playing_next_round") if raw.get("chance_of_playing_next_round") is not None else 100) / 100,
        "news": raw.get("news") or "",
        "fixtures": fixtures,
        "fixture_ease_next5": round(6 - (sum((f.get("difficulty") or 3) for f in fixtures) / len(fixtures) if fixtures else 3), 2),
        "decision_score": base,
        "mini_league_ownership_pct": own_pct,
        "target_rival_ownership_pct": target_pct,
        "target_captain_count": target_cap[pid],
        "protective_score": round(base + target_pct * 0.055 + target_cap[pid] * 1.2, 3),
        "chase_score": round(base + (100 - target_pct) * 0.035 + max(0, 30 - own_pct) * 0.025, 3),
    }


def current_moves(data, squad_rows, raw_players, teams, positions, fixture_map, expo, target_own, target_cap, target_n, bank):
    ids = {p["player_id"] for p in squad_rows}
    candidate_pool = []
    for pid, raw in raw_players.items():
        if pid in ids or raw.get("status") == "u":
            continue
        candidate_pool.append(enriched_player(pid, raw_players, teams, positions, fixture_map, expo, target_own, target_cap, target_n))

    moves = []
    for outp in squad_rows:
        max_price = outp["price"] + bank
        same_pos = [c for c in candidate_pool if c["position_id"] == outp["position_id"] and c["price"] <= max_price and c["availability"] >= 0.75]
        if not same_pos:
            continue
        safe = max(same_pos, key=lambda c: c["protective_score"])
        chase = max(same_pos, key=lambda c: c["chase_score"])
        moves.append({
            "out": {"player_id": outp["player_id"], "player": outp["player"], "price": outp["price"], "decision_score": outp["decision_score"], "position": outp["position"]},
            "safe_in": safe,
            "aggressive_in": chase,
            "safe_gain": round(safe["protective_score"] - outp["decision_score"], 3),
            "aggressive_gain": round(chase["chase_score"] - outp["decision_score"], 3),
        })
    return {
        "model_note": "Recomputed from the post-transfer current squad using transfer history plus the same ownership/fixture heuristics as the main ETL.",
        "safe_moves": sorted(moves, key=lambda m: m["safe_gain"], reverse=True)[:5],
        "aggressive_moves": sorted(moves, key=lambda m: m["aggressive_gain"], reverse=True)[:5],
    }


def classify_alignment(transfer, previous_decisions):
    out_id = transfer["element_out"]
    in_id = transfer["element_in"]
    exact = []
    incoming = []
    for label, key, in_key in [("lower_variance", "safe_moves", "safe_in"), ("variety", "aggressive_moves", "aggressive_in")]:
        for m in previous_decisions.get(key, []):
            cand = m.get(in_key) or {}
            out = m.get("out") or {}
            if cand.get("player_id") == in_id:
                incoming.append(label)
                if out.get("player_id") == out_id or out.get("player") == transfer.get("out_name"):
                    exact.append(label)
    if exact:
        return "aligned_with_recommendation", sorted(set(exact))
    if incoming:
        return "partially_aligned", sorted(set(incoming))
    return "manager_led", []


def update_journal(data, transfers, players):
    path = Path("data/decision_history.json")
    journal = json.loads(path.read_text()) if path.exists() else {"version": 1, "decisions": []}
    seen = {(d.get("event"), d.get("element_out"), d.get("element_in"), d.get("time")) for d in journal["decisions"]}
    previous = data.get("next_gw_decisions", {})
    added = 0
    for t in sorted(transfers, key=lambda x: x.get("time") or ""):
        key = (t.get("event"), t.get("element_out"), t.get("element_in"), t.get("time"))
        if key in seen:
            continue
        out_name = players.get(t["element_out"], {}).get("web_name")
        in_name = players.get(t["element_in"], {}).get("web_name")
        tx = {**t, "out_name": out_name, "in_name": in_name}
        alignment, matched = classify_alignment(tx, previous)
        rationale = []
        if alignment == "aligned_with_recommendation":
            rationale.append("This exact transfer route appeared in the dashboard recommendation set before the move was made.")
        elif alignment == "partially_aligned":
            rationale.append("The incoming player appeared in the dashboard recommendation set, but the outgoing route differed.")
        else:
            rationale.append("No matching dashboard recommendation was found at capture time; record this as a manager-led decision.")
        journal["decisions"].append({
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "event": t.get("event"),
            "time": t.get("time"),
            "element_out": t.get("element_out"),
            "out_name": out_name,
            "element_in": t.get("element_in"),
            "in_name": in_name,
            "out_cost": t.get("element_out_cost") / 10 if t.get("element_out_cost") is not None else None,
            "in_cost": t.get("element_in_cost") / 10 if t.get("element_in_cost") is not None else None,
            "alignment": alignment,
            "matched_recommendation_types": matched,
            "rationale": rationale,
            "manager_note": None,
        })
        added += 1
    journal["decisions"].sort(key=lambda x: (x.get("event") or 0, x.get("time") or ""))
    path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n")
    return journal, added


def main():
    path = Path("data/latest.json")
    data = json.loads(path.read_text())
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    fixtures = get_json(f"{BASE}/fixtures/")
    transfers = get_json(f"{BASE}/entry/{ENTRY_ID}/transfers/")

    raw_players = {p["id"]: p for p in bootstrap["elements"]}
    teams = {t["id"]: t["name"] for t in bootstrap["teams"]}
    positions = {p["id"]: p["singular_name_short"] for p in bootstrap["element_types"]}
    next_gw = data["next_gw"]
    fixture_map = fixtures_by_team(fixtures, teams, next_gw, 5)
    expo, target_own, target_cap, target_n = exposure_maps(data)

    base = [dict(p) for p in data.get("squad_next5", [])]
    by_id = {p["player_id"]: p for p in base}
    relevant = [t for t in transfers if t.get("event") == next_gw]
    bank = float(data.get("me", {}).get("bank") or 0)

    for t in sorted(relevant, key=lambda x: x.get("time") or ""):
        out = by_id.pop(t["element_out"], None)
        if out is None:
            continue
        incoming = enriched_player(t["element_in"], raw_players, teams, positions, fixture_map, expo, target_own, target_cap, target_n)
        incoming.update({
            "slot": out.get("slot"),
            "multiplier": 0,
            "captain": False,
            "vice_captain": False,
            "starter": False,
            "live_points": 0,
            "effective_points": 0,
            "transfer_in_for_event": next_gw,
        })
        by_id[incoming["player_id"]] = incoming
        bank += (t.get("element_out_cost", int(round(out["price"] * 10))) - t.get("element_in_cost", int(round(incoming["price"] * 10)))) / 10

    current = list(by_id.values())
    current.sort(key=lambda x: x.get("slot") or 99)
    decisions = current_moves(data, current, raw_players, teams, positions, fixture_map, expo, target_own, target_cap, target_n, bank)
    journal, added = update_journal(data, relevant, raw_players)

    data["current_squad_source"] = "transfer_history_reconstruction" if relevant else "last_completed_gw_picks"
    data["current_squad_transfers"] = relevant
    data["current_squad_next5"] = current
    data["current_bank"] = round(bank, 1)
    data["current_next_gw_decisions"] = decisions
    data["decision_history_count"] = len(journal["decisions"])
    data["current_squad_generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "SUCCESS", "transfers_for_next_gw": len(relevant), "journal_added": added, "current_bank": round(bank, 1)}))


if __name__ == "__main__":
    main()
