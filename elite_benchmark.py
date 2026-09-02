import json
import statistics
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://fantasy.premierleague.com/api"
LATEST = Path("data/latest.json")
OUT = Path("data/elite_benchmark.json")
DETAIL_LIMIT = 10


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-elite-benchmark/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def median(values, default=0.0):
    vals = [float(x) for x in values if x is not None]
    return round(statistics.median(vals), 2) if vals else default


def mean(values, default=0.0):
    vals = [float(x) for x in values if x is not None]
    return round(sum(vals) / len(vals), 2) if vals else default


def discover_overall_league(entry_id):
    entry = get_json(f"{BASE}/entry/{entry_id}/")
    for league in (entry.get("leagues") or {}).get("classic", []):
        if str(league.get("name") or "").strip().lower() == "overall":
            return int(league["id"])
    raise RuntimeError("Could not discover Overall league from entry")


def top_entries(overall_league_id, limit=DETAIL_LIMIT):
    page = get_json(f"{BASE}/leagues-classic/{overall_league_id}/standings/?page_standings=1")
    rows = ((page.get("standings") or {}).get("results") or [])[:limit]
    return rows


def bootstrap_maps():
    b = get_json(f"{BASE}/bootstrap-static/")
    players = {int(p["id"]): p for p in b.get("elements", [])}
    teams = {int(t["id"]): t.get("short_name") or t.get("name") for t in b.get("teams", [])}
    pos = {int(p["id"]): p.get("singular_name_short") for p in b.get("element_types", [])}
    return b, players, teams, pos


def pick_detail(entry_id, gw):
    return get_json(f"{BASE}/entry/{entry_id}/event/{gw}/picks/")


def history(entry_id):
    return get_json(f"{BASE}/entry/{entry_id}/history/")


def transfer_history(entry_id):
    return get_json(f"{BASE}/entry/{entry_id}/transfers/")


def squad_ids(picks):
    return [int(x.get("element") or 0) for x in picks.get("picks", []) if int(x.get("element") or 0)]


def starter_ids(picks):
    return [int(x.get("element") or 0) for x in picks.get("picks", []) if int(x.get("multiplier") or 0) > 0]


def captain_id(picks):
    row = next((x for x in picks.get("picks", []) if x.get("is_captain")), None)
    return int(row.get("element") or 0) if row else 0


def position_spend(ids, players, pos):
    out = defaultdict(float)
    for pid in ids:
        p = players.get(pid) or {}
        out[pos.get(int(p.get("element_type") or 0), "?")] += (p.get("now_cost") or 0) / 10
    return {k: round(v, 1) for k, v in out.items()}


def style_label(avg_transfers, hit_points, template_overlap, captain_consensus):
    if hit_points >= 4 or avg_transfers >= 1.5:
        return "AGGRESSIVE"
    if template_overlap >= 65 and captain_consensus >= 60:
        return "CONTROLLED TEMPLATE"
    if template_overlap < 50:
        return "DIFFERENTIAL-LEANING"
    return "BALANCED"


def main():
    latest = json.loads(LATEST.read_text())
    current_gw = int(latest.get("current_gw") or 0)
    me_id = int((latest.get("me") or {}).get("entry_id") or 0)
    if not me_id or not current_gw:
        raise RuntimeError("latest.json missing entry/current GW")

    overall_id = discover_overall_league(me_id)
    leaders = top_entries(overall_id)
    bootstrap, player_map, team_map, pos_map = bootstrap_maps()

    elite = []
    ownership = Counter()
    starter_ownership = Counter()
    captain_counts = Counter()
    transfer_counts = []
    hit_costs = []
    bank_values = []
    team_values = []
    bench_points = []
    chip_counts = Counter()
    pos_spends = defaultdict(list)

    for row in leaders:
        eid = int(row.get("entry") or 0)
        try:
            picks = pick_detail(eid, current_gw)
            hist = history(eid)
            transfers = transfer_history(eid)
        except Exception as exc:
            elite.append({"entry_id": eid, "rank": row.get("rank"), "team_name": row.get("entry_name"), "status": "fetch_failed", "error": str(exc)})
            continue

        ids = squad_ids(picks)
        starters = starter_ids(picks)
        cap = captain_id(picks)
        for pid in ids:
            ownership[pid] += 1
        for pid in starters:
            starter_ownership[pid] += 1
        if cap:
            captain_counts[cap] += 1

        eh = picks.get("entry_history") or {}
        ev_transfers = int(eh.get("event_transfers") or 0)
        hit = int(eh.get("event_transfers_cost") or 0)
        bank = (eh.get("bank") or 0) / 10
        value = (eh.get("value") or 0) / 10
        bench = int(eh.get("points_on_bench") or 0)
        transfer_counts.append(ev_transfers)
        hit_costs.append(hit)
        bank_values.append(bank)
        team_values.append(value)
        bench_points.append(bench)

        current_hist = hist.get("current") or []
        season_transfers = sum(int(x.get("event_transfers") or 0) for x in current_hist)
        season_hits = sum(int(x.get("event_transfers_cost") or 0) for x in current_hist)
        gws_played = max(1, len(current_hist))
        avg_transfers = season_transfers / gws_played
        for c in hist.get("chips") or []:
            if c.get("name"):
                chip_counts[c["name"]] += 1

        spend = position_spend(ids, player_map, pos_map)
        for k, v in spend.items():
            pos_spends[k].append(v)

        cap_player = player_map.get(cap) or {}
        elite.append({
            "status": "SUCCESS",
            "entry_id": eid,
            "overall_rank": int(row.get("rank") or 0),
            "team_name": row.get("entry_name"),
            "manager": row.get("player_name"),
            "total_points": int(row.get("total") or 0),
            "gw_points": int(eh.get("points") or 0),
            "event_transfers": ev_transfers,
            "event_hit_cost": hit,
            "season_transfers": season_transfers,
            "season_hit_cost": season_hits,
            "avg_transfers_per_gw": round(avg_transfers, 2),
            "bank": round(bank, 1),
            "team_value": round(value, 1),
            "bench_points": bench,
            "captain_id": cap,
            "captain": cap_player.get("web_name"),
            "squad_ids": ids,
            "starter_ids": starters,
            "position_spend": spend,
            "chips_used": hist.get("chips") or [],
            "transfer_history": [
                {"event": x.get("event"), "element_in": x.get("element_in"), "element_out": x.get("element_out"), "time": x.get("time")}
                for x in (transfers or [])[:20]
            ],
        })

    valid = [x for x in elite if x.get("status") == "SUCCESS"]
    cohort_n = len(valid)
    if not cohort_n:
        raise RuntimeError("No elite manager detail could be fetched")

    def player_row(pid, count, kind="squad"):
        p = player_map.get(pid) or {}
        return {
            "player_id": pid,
            "player": p.get("web_name"),
            "club": team_map.get(int(p.get("team") or 0)),
            "position": pos_map.get(int(p.get("element_type") or 0)),
            "price": round((p.get("now_cost") or 0) / 10, 1),
            "elite_ownership_pct": round(100 * count / cohort_n, 1),
            "kind": kind,
        }

    elite_template = [player_row(pid, count) for pid, count in ownership.most_common(20)]
    elite_starters = [player_row(pid, count, "starter") for pid, count in starter_ownership.most_common(20)]
    elite_captains = [player_row(pid, count, "captain") for pid, count in captain_counts.most_common(10)]

    my_effective = latest.get("current_squad_next5") or latest.get("squad_next5") or latest.get("squad") or []
    my_ids = {int(x.get("player_id") or 0) for x in my_effective if int(x.get("player_id") or 0)}
    my_xi = {int(x.get("player_id") or 0) for x in latest.get("squad", []) if x.get("starter") or int(x.get("multiplier") or 0) > 0}
    template_ids = {x["player_id"] for x in elite_template if x["elite_ownership_pct"] >= 50}
    starter_template_ids = {x["player_id"] for x in elite_starters if x["elite_ownership_pct"] >= 50}
    squad_overlap = round(100 * len(my_ids & template_ids) / max(1, len(template_ids)), 1)
    xi_overlap = round(100 * len(my_xi & starter_template_ids) / max(1, len(starter_template_ids)), 1)

    action = ((latest.get("decision_synthesis") or {}).get("current_action") or {}).get("action") or "HOLD"
    completed_route = (((latest.get("decision_synthesis") or {}).get("current_action") or {}).get("completed_transfer") or {}).get("route")
    top_cap = elite_captains[0] if elite_captains else None
    captain_consensus = float(top_cap.get("elite_ownership_pct") or 0) if top_cap else 0
    style = style_label(mean(transfer_counts), sum(hit_costs), squad_overlap, captain_consensus)

    our_unique = []
    for p in my_effective:
        pid = int(p.get("player_id") or 0)
        pct = round(100 * ownership.get(pid, 0) / cohort_n, 1)
        if pct < 50:
            our_unique.append({"player_id": pid, "player": p.get("player"), "elite_ownership_pct": pct, "club": p.get("club"), "position": p.get("position")})
    our_unique.sort(key=lambda x: x["elite_ownership_pct"])

    missing_template = [x for x in elite_template if x["elite_ownership_pct"] >= 50 and x["player_id"] not in my_ids]

    result = {
        "status": "SUCCESS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "official_public_fpl_manager_data",
        "overall_league_id": overall_id,
        "current_gw": current_gw,
        "cohort": {"requested": DETAIL_LIMIT, "available": cohort_n, "description": f"Current top {cohort_n} managers in the official Overall league"},
        "elite_managers": valid,
        "elite_scores": {
            "leader_points": max(x["total_points"] for x in valid),
            "median_total_points": median([x["total_points"] for x in valid]),
            "median_gw_points": median([x["gw_points"] for x in valid]),
            "median_team_value": median(team_values),
            "median_bank": median(bank_values),
            "median_bench_points": median(bench_points),
        },
        "behaviour": {
            "avg_transfers_this_gw": mean(transfer_counts),
            "managers_taking_hit_this_gw": sum(1 for x in hit_costs if x > 0),
            "total_hit_cost_this_gw": sum(hit_costs),
            "captain_consensus_pct": round(captain_consensus, 1),
            "top_captain": top_cap,
            "chip_usage_counts": dict(chip_counts),
            "median_position_spend": {k: median(v) for k, v in pos_spends.items()},
            "observed_style": style,
        },
        "template": {
            "squad": elite_template,
            "starters": elite_starters,
            "captains": elite_captains,
        },
        "comparison_to_us": {
            "our_total_points": int((latest.get("me") or {}).get("total_points") or 0),
            "points_to_elite_leader": max(x["total_points"] for x in valid) - int((latest.get("me") or {}).get("total_points") or 0),
            "points_to_elite_median": round(median([x["total_points"] for x in valid]) - int((latest.get("me") or {}).get("total_points") or 0), 1),
            "elite_template_overlap_pct": squad_overlap,
            "elite_starting_overlap_pct": xi_overlap,
            "our_low_elite_owned_players": our_unique[:8],
            "elite_template_players_we_lack": missing_template[:8],
            "engine_action": action,
            "completed_transfer_route": completed_route,
            "interpretation": "Elite behaviour is a benchmark, not an instruction. The decision engine should only converge with elite managers when projections, role, fixtures, value and risk independently support it.",
        },
        "method_note": "Uses observable public FPL behaviour only. It cannot know private reasoning, planned future transfers, unpublished injury beliefs or why a manager made a move.",
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "SUCCESS", "cohort": cohort_n, "leader": result["elite_scores"]["leader_points"], "style": style}))


if __name__ == "__main__":
    main()
