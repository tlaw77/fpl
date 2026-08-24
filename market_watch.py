import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://fantasy.premierleague.com/api"
LATEST = Path("data/latest.json")
OUT = Path("data/market.json")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-market-watch/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def collect_candidate_ids(obj, out=None):
    if out is None:
        out = set()
    if isinstance(obj, dict):
        pid = obj.get("player_id")
        if isinstance(pid, int):
            out.add(pid)
        for v in obj.values():
            collect_candidate_ids(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_candidate_ids(v, out)
    return out


def pressure(player):
    selected = max(1.0, float(player.get("selected_by_percent") or 0))
    net = (player.get("transfers_in_event") or 0) - (player.get("transfers_out_event") or 0)
    # Relative transfer pressure is a heuristic only; official FPL predictor remains authoritative.
    ratio = net / max(1000.0, selected * 100000.0)
    if ratio >= 0.05:
        status = "strong_rise_pressure"
    elif ratio >= 0.02:
        status = "rise_pressure"
    elif ratio <= -0.05:
        status = "strong_fall_pressure"
    elif ratio <= -0.02:
        status = "fall_pressure"
    else:
        status = "stable"
    return net, ratio, status


def main():
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    latest = json.loads(LATEST.read_text()) if LATEST.exists() else {}
    previous = json.loads(OUT.read_text()) if OUT.exists() else {}
    prev_prices = {p["player_id"]: p.get("price") for p in previous.get("players", [])}

    squad_ids = {p.get("player_id") for p in latest.get("squad", []) if p.get("player_id")}
    candidate_ids = collect_candidate_ids(latest.get("next_gw_decisions", {}))

    teams = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
    positions = {p["id"]: p["singular_name_short"] for p in bootstrap.get("element_types", [])}

    rows = []
    for p in bootstrap.get("elements", []):
        pid = p["id"]
        net, ratio, status = pressure(p)
        price = (p.get("now_cost") or 0) / 10
        old = prev_prices.get(pid)
        price_delta = round(price - old, 1) if isinstance(old, (int, float)) else 0
        own = pid in squad_ids
        target = pid in candidate_ids and not own
        urgency = "wait"
        reason = "No material market pressure. Preserve information before the deadline."
        if own and status in {"fall_pressure", "strong_fall_pressure"}:
            urgency = "watch"
            reason = "Owned player has negative transfer pressure; a drop could reduce flexibility."
        if target and status == "rise_pressure":
            urgency = "watch"
            reason = "Transfer target has positive pressure and may become harder to afford."
        if target and status == "strong_rise_pressure":
            urgency = "move_tonight_if_already_decided"
            reason = "Strong transfer pressure on a planned target; price risk may justify early action only if the football decision is already made."
        if p.get("chance_of_playing_next_round") is not None and (p.get("chance_of_playing_next_round") or 0) < 75:
            if urgency == "move_tonight_if_already_decided":
                urgency = "wait_for_news"
            reason = "Availability uncertainty outweighs price pressure; wait for team/news information."

        rows.append({
            "player_id": pid,
            "player": p.get("web_name"),
            "club": teams.get(p.get("team")),
            "position": positions.get(p.get("element_type")),
            "price": price,
            "price_delta_since_last_snapshot": price_delta,
            "price_change_this_gw": (p.get("cost_change_event") or 0) / 10,
            "ownership_pct": float(p.get("selected_by_percent") or 0),
            "transfers_in_event": p.get("transfers_in_event") or 0,
            "transfers_out_event": p.get("transfers_out_event") or 0,
            "net_transfers_event": net,
            "transfer_pressure_ratio": round(ratio, 5),
            "market_status": status,
            "in_my_squad": own,
            "in_recommendation_set": target,
            "availability": p.get("chance_of_playing_next_round"),
            "news": p.get("news") or "",
            "urgency": urgency,
            "urgency_reason": reason,
        })

    relevant = [r for r in rows if r["in_my_squad"] or r["in_recommendation_set"]]
    rise_watch = sorted([r for r in rows if r["market_status"] in {"rise_pressure", "strong_rise_pressure"}], key=lambda x: x["net_transfers_event"], reverse=True)[:20]
    fall_watch = sorted([r for r in rows if r["market_status"] in {"fall_pressure", "strong_fall_pressure"}], key=lambda x: x["net_transfers_event"])[:20]
    urgent = [r for r in relevant if r["urgency"] != "wait"]

    result = {
        "status": "SUCCESS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_note": "Transfer-pressure heuristic from official FPL bootstrap data. It is not the official Price Change Predictor.",
        "price_change_deadline": "00:00 UK time daily",
        "decision_rule": "Football decision first. Only act early for price if the move is already preferred and availability risk is acceptably low.",
        "urgent_relevant": urgent,
        "my_squad_and_targets": relevant,
        "rise_watch": rise_watch,
        "fall_watch": fall_watch,
        "players": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "SUCCESS", "urgent": len(urgent), "rise_watch": len(rise_watch), "fall_watch": len(fall_watch)}))


if __name__ == "__main__":
    main()
