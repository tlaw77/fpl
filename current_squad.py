import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
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


def best_xi(rows):
    """Return the highest decision-score legal XI and its score.

    This intentionally uses the same core decision_score carried by the squad rows.
    Transfer ranking must care about who actually starts, not only whether the incoming
    player is individually stronger than the outgoing squad member.
    """
    available = [p for p in rows if float(p.get("availability", 1) or 0) > 0]
    by_pos = defaultdict(list)
    for p in available:
        by_pos[p.get("position")].append(p)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda p: float(p.get("decision_score") or 0), reverse=True)

    keepers = by_pos.get("GKP", [])
    if not keepers:
        return [], 0.0
    keeper = keepers[0]
    best_rows, best_score = [], float("-inf")

    # Legal FPL outfield formations: 3-5 DEF, 2-5 MID, 1-3 FWD, ten outfield players.
    for nd in range(3, 6):
        for nm in range(2, 6):
            nf = 10 - nd - nm
            if nf < 1 or nf > 3:
                continue
            if len(by_pos.get("DEF", [])) < nd or len(by_pos.get("MID", [])) < nm or len(by_pos.get("FWD", [])) < nf:
                continue
            picked = [keeper] + by_pos["DEF"][:nd] + by_pos["MID"][:nm] + by_pos["FWD"][:nf]
            score = sum(float(p.get("decision_score") or 0) for p in picked)
            if score > best_score:
                best_rows, best_score = picked, score
    return best_rows, round(best_score if best_rows else 0.0, 3)


def transfer_xi_effect(squad_rows, outp, incoming):
    baseline_xi, baseline_score = best_xi(squad_rows)
    projected = [p for p in squad_rows if p.get("player_id") != outp.get("player_id")] + [incoming]
    projected_xi, projected_score = best_xi(projected)
    base_ids = {p.get("player_id") for p in baseline_xi}
    projected_ids = {p.get("player_id") for p in projected_xi}
    incoming_starts = incoming.get("player_id") in projected_ids
    outgoing_started = outp.get("player_id") in base_ids
    return {
        "baseline_xi_score": baseline_score,
        "projected_xi_score": projected_score,
        "xi_gain": round(projected_score - baseline_score, 3),
        "incoming_starts": incoming_starts,
        "outgoing_started": outgoing_started,
    }


def legal_candidate(squad_rows, outp, candidate):
    # Enforce the FPL maximum of three players from one club after the transfer.
    club_counts = Counter(p.get("team_id") for p in squad_rows if p.get("player_id") != outp.get("player_id"))
    return club_counts[candidate.get("team_id")] < 3


def action_gain(raw_gain, xi_effect):
    """Convert an individual squad upgrade into an actionable transfer score.

    Starting-XI gain dominates. A bench-only upgrade retains a small amount of
    structural value, but pays an explicit free-transfer opportunity-cost penalty.
    This prevents a goalkeeper/bench upgrade from becoming the primary GW move merely
    because the incoming player's individual score or rival leverage is attractive.
    """
    xi_gain = float(xi_effect.get("xi_gain") or 0)
    structural = max(0.0, float(raw_gain or 0))
    if xi_effect.get("incoming_starts"):
        return round(xi_gain * 1.5 + structural * 0.25, 3)
    return round(xi_gain * 1.5 + structural * 0.12 - 1.5, 3)


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
        same_pos = [
            c for c in candidate_pool
            if c["position_id"] == outp["position_id"]
            and c["price"] <= max_price
            and c["availability"] >= 0.75
            and legal_candidate(squad_rows, outp, c)
        ]
        if not same_pos:
            continue

        # Evaluate every legal candidate against the post-transfer best XI, then choose
        # the highest ACTION score rather than the highest isolated player score.
        evaluated = []
        for c in same_pos:
            effect = transfer_xi_effect(squad_rows, outp, c)
            raw_safe = round(c["protective_score"] - outp["decision_score"], 3)
            raw_chase = round(c["chase_score"] - outp["decision_score"], 3)
            evaluated.append((c, effect, raw_safe, raw_chase, action_gain(raw_safe, effect), action_gain(raw_chase, effect)))

        safe_c, safe_effect, safe_raw, _, safe_action, _ = max(evaluated, key=lambda x: x[4])
        chase_c, chase_effect, _, chase_raw, _, chase_action = max(evaluated, key=lambda x: x[5])

        moves.append({
            "out": {"player_id": outp["player_id"], "player": outp["player"], "price": outp["price"], "decision_score": outp["decision_score"], "position": outp["position"]},
            "safe_in": safe_c,
            "aggressive_in": chase_c,
            # Existing UI sorts/compares these fields, so they now represent ACTION gain.
            "safe_gain": safe_action,
            "aggressive_gain": chase_action,
            # Preserve the old isolated-player deltas for explainability/audit.
            "safe_raw_player_gain": safe_raw,
            "aggressive_raw_player_gain": chase_raw,
            "safe_xi_gain": safe_effect["xi_gain"],
            "aggressive_xi_gain": chase_effect["xi_gain"],
            "safe_incoming_starts": safe_effect["incoming_starts"],
            "aggressive_incoming_starts": chase_effect["incoming_starts"],
            "outgoing_started": safe_effect["outgoing_started"],
            "safe_baseline_xi_score": safe_effect["baseline_xi_score"],
            "safe_projected_xi_score": safe_effect["projected_xi_score"],
        })
    return {
        "model_note": "Transfers are ranked by post-transfer legal Best XI impact first, with smaller structural/ownership value. Bench-only upgrades pay a free-transfer opportunity-cost penalty.",
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
