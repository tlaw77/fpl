import json
import urllib.request
from datetime import datetime, timezone, timedelta
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


def trim_recent_changes(changes, now):
    cutoff = now - timedelta(days=14)
    out = []
    for x in changes or []:
        try:
            when = datetime.fromisoformat(str(x.get("observed_at_utc") or "").replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when < cutoff:
                continue
        except Exception:
            continue
        out.append(x)
    out.sort(key=lambda x: x.get("observed_at_utc") or "", reverse=True)
    return out[:80]


def main():
    bootstrap = get_json(f"{BASE}/bootstrap-static/")
    latest = json.loads(LATEST.read_text()) if LATEST.exists() else {}
    previous = json.loads(OUT.read_text()) if OUT.exists() else {}
    prev_prices = {p["player_id"]: p.get("price") for p in previous.get("players", [])}
    now = datetime.now(timezone.utc)
    current_gw = latest.get("current_gw")

    squad_ids = {p.get("player_id") for p in latest.get("squad", []) if p.get("player_id")}
    candidate_ids = collect_candidate_ids(latest.get("next_gw_decisions", {}))

    teams = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
    positions = {p["id"]: p["singular_name_short"] for p in bootstrap.get("element_types", [])}

    rows = []
    detected_changes = []
    gw_price_changes = []
    for p in bootstrap.get("elements", []):
        pid = p["id"]
        net, ratio, status = pressure(p)
        price = (p.get("now_cost") or 0) / 10
        old = prev_prices.get(pid)
        price_delta = round(price - old, 1) if isinstance(old, (int, float)) else 0
        club = teams.get(p.get("team"))
        position = positions.get(p.get("element_type"))
        gw_delta = (p.get("cost_change_event") or 0) / 10

        if price_delta:
            detected_changes.append({
                "player_id": pid,
                "player": p.get("web_name"),
                "club": club,
                "position": position,
                "from_price": old,
                "to_price": price,
                "change": price_delta,
                "direction": "rise" if price_delta > 0 else "fall",
                "observed_at_utc": now.isoformat(),
                "gw": current_gw,
                "source": "official_bootstrap_snapshot_diff",
            })

        if gw_delta:
            gw_price_changes.append({
                "player_id": pid,
                "player": p.get("web_name"),
                "club": club,
                "position": position,
                "from_price": round(price - gw_delta, 1),
                "to_price": price,
                "change": round(gw_delta, 1),
                "direction": "rise" if gw_delta > 0 else "fall",
                "gw": current_gw,
                "source": "official_cost_change_event",
            })

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
            "club": club,
            "position": position,
            "price": price,
            "price_delta_since_last_snapshot": price_delta,
            "price_change_this_gw": gw_delta,
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

    # Persist observed official price-change events so they remain visible after the next 30-minute snapshot.
    recent_changes = trim_recent_changes(previous.get("recent_price_changes", []), now)
    for change in detected_changes:
        duplicate = any(
            x.get("player_id") == change.get("player_id")
            and x.get("from_price") == change.get("from_price")
            and x.get("to_price") == change.get("to_price")
            and x.get("gw") == change.get("gw")
            for x in recent_changes[:20]
        )
        if not duplicate:
            recent_changes.insert(0, change)
    recent_changes = trim_recent_changes(recent_changes, now)

    gw_price_changes.sort(key=lambda x: (abs(x.get("change") or 0), x.get("player") or ""), reverse=True)
    relevant = [r for r in rows if r["in_my_squad"] or r["in_recommendation_set"]]
    rise_watch = sorted([r for r in rows if r["market_status"] in {"rise_pressure", "strong_rise_pressure"}], key=lambda x: x["net_transfers_event"], reverse=True)[:20]
    fall_watch = sorted([r for r in rows if r["market_status"] in {"fall_pressure", "strong_fall_pressure"}], key=lambda x: x["net_transfers_event"])[:20]
    urgent = [r for r in relevant if r["urgency"] != "wait"]

    result = {
        "status": "SUCCESS",
        "generated_at_utc": now.isoformat(),
        "model_note": "Transfer-pressure heuristic from official FPL bootstrap data. It is not the official Price Change Predictor.",
        "actual_price_change_note": "Recent price changes are observed from consecutive official FPL bootstrap snapshots. Current-GW net changes come directly from official cost_change_event.",
        "price_change_deadline": "00:00 UK time daily",
        "decision_rule": "Football decision first. Only act early for price if the move is already preferred and availability risk is acceptably low.",
        "recent_price_changes": recent_changes,
        "gw_price_changes": gw_price_changes,
        "urgent_relevant": urgent,
        "my_squad_and_targets": relevant,
        "rise_watch": rise_watch,
        "fall_watch": fall_watch,
        "players": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "SUCCESS", "urgent": len(urgent), "rise_watch": len(rise_watch), "fall_watch": len(fall_watch), "actual_price_changes": len(recent_changes)}))


if __name__ == "__main__":
    main()
