import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://fantasy.premierleague.com/api"
LATEST = Path("data/latest.json")
STRATEGY = Path("data/strategy.json")
OUT = Path("data/squad_intelligence.json")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-squad-intel/1.1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def player_maps():
    b = get_json(f"{BASE}/bootstrap-static/")
    teams = {t["id"]: t["name"] for t in b["teams"]}
    players = {
        p["id"]: {
            "player": p["web_name"],
            "club": teams.get(p["team"], ""),
            "team_id": p["team"],
            "position_id": p["element_type"],
        }
        for p in b["elements"]
    }
    return players


def chip_summary(strategy):
    out = {}
    for m in strategy.get("managers", []):
        inv = m.get("inventory", {}) or {}
        out[m.get("entry_id")] = {
            "used": inv.get("used_this_half", []) or [],
            "remaining": inv.get("remaining_this_half", []) or [],
            "remaining_count": len(inv.get("remaining_this_half", []) or []),
            "chip_edge_vs_me": m.get("chip_edge_vs_me", {}) or {},
        }
    return out


def transfer_profile(entry_id, players):
    try:
        transfers = get_json(f"{BASE}/entry/{entry_id}/transfers/") or []
    except Exception:
        transfers = []
    try:
        history = get_json(f"{BASE}/entry/{entry_id}/history/") or {}
    except Exception:
        history = {}

    current = history.get("current", []) or []
    total_cost = sum(int(x.get("event_transfers_cost") or 0) for x in current)
    hit_gws = [x.get("event") for x in current if int(x.get("event_transfers_cost") or 0) > 0]
    events = Counter(int(t.get("event") or 0) for t in transfers if t.get("event"))
    recent = sorted(transfers, key=lambda x: x.get("time") or "", reverse=True)[:6]

    moves = []
    club_in = Counter()
    club_out = Counter()
    for t in recent:
        i = players.get(t.get("element_in"), {})
        o = players.get(t.get("element_out"), {})
        if i.get("club"):
            club_in[i["club"]] += 1
        if o.get("club"):
            club_out[o["club"]] += 1
        moves.append({
            "gw": t.get("event"),
            "time": t.get("time"),
            "in": i.get("player"),
            "in_club": i.get("club"),
            "out": o.get("player"),
            "out_club": o.get("club"),
            "purchase_price": (t.get("element_in_cost") / 10) if t.get("element_in_cost") is not None else None,
            "selling_price": (t.get("element_out_cost") / 10) if t.get("element_out_cost") is not None else None,
        })

    total = len(transfers)
    if total == 0:
        style = "No transfer history yet"
    elif total_cost >= 8 or any(v >= 3 for v in events.values()):
        style = "Aggressive"
    elif total >= max(2, len(current) * 0.7):
        style = "Active"
    else:
        style = "Patient"

    themes = []
    if club_in:
        c, n = club_in.most_common(1)[0]
        if n >= 2:
            themes.append(f"Repeatedly bought {c}")
    if club_out:
        c, n = club_out.most_common(1)[0]
        if n >= 2:
            themes.append(f"Repeatedly sold {c}")
    if total_cost:
        themes.append(f"{total_cost} pts spent on hits")
    if not themes and total:
        themes.append("No strong transfer pattern yet")

    return {
        "total_transfers": total,
        "total_hit_cost": total_cost,
        "hit_gameweeks": hit_gws,
        "style": style,
        "recent_moves": moves,
        "themes": themes,
    }


def squad_profile(manager, exposure):
    picks = manager.get("picks", []) or []
    clubs = Counter(p.get("club") for p in picks if p.get("club"))
    heavy = [{"club": c, "count": n} for c, n in clubs.most_common() if n >= 2]
    triples = [x for x in heavy if x["count"] >= 3]

    template = 0
    differentials = 0
    high_eo = 0
    for p in picks:
        e = exposure.get(p.get("player_id"), {})
        own = float(e.get("ownership_pct") or 0)
        eo = float(e.get("effective_ownership_pct") or 0)
        if own >= 50:
            template += 1
        if own <= 25:
            differentials += 1
        if eo >= 75:
            high_eo += 1

    captain = next((p.get("player") for p in picks if p.get("captain")), manager.get("captain"))
    vice = next((p.get("player") for p in picks if p.get("vice_captain")), manager.get("vice_captain"))

    return {
        "club_concentration": heavy,
        "triple_stacks": triples,
        "template_players": template,
        "differentials": differentials,
        "high_eo_players": high_eo,
        "overlap_count": manager.get("overlap_count"),
        "overlap_pct": manager.get("overlap_pct"),
        "captain": captain,
        "vice_captain": vice,
    }


def ft_state(current_gw):
    # At the end of GW1 every manager enters GW2 with exactly one FT.
    # Current-GW transfers are private until the deadline, so do not pretend
    # we know a rival's live remaining FT before FPL publishes those moves.
    if int(current_gw or 0) == 1:
        return {
            "entering_next_gw": 1,
            "next_gw": 2,
            "remaining_publicly_known": None,
            "current_use_hidden": True,
            "confidence": "known_starting_allowance",
        }
    return {
        "entering_next_gw": None,
        "next_gw": int(current_gw or 0) + 1 if current_gw is not None else None,
        "remaining_publicly_known": None,
        "current_use_hidden": True,
        "confidence": "not_modelled_yet",
    }


def main():
    latest = json.loads(LATEST.read_text())
    strategy = json.loads(STRATEGY.read_text()) if STRATEGY.exists() else {}
    players = player_maps()
    exposure = {x.get("player_id"): x for x in latest.get("player_exposure", [])}
    chips = chip_summary(strategy)

    managers = []
    me = latest.get("me", {})
    current_gw = latest.get("current_gw")
    everyone = []
    if latest.get("rivals"):
        everyone.extend(latest["rivals"])
    everyone.append({
        **me,
        "picks": latest.get("squad", []),
        "overlap_count": 15,
        "overlap_pct": 100.0,
    })

    for m in everyone:
        entry_id = m.get("entry_id")
        if not entry_id:
            continue
        squad = squad_profile(m, exposure)
        transfer = transfer_profile(entry_id, players)
        chip = chips.get(entry_id, {"used": [], "remaining": [], "remaining_count": 0, "chip_edge_vs_me": {}})
        ft = ft_state(current_gw)

        signals = []
        if squad["triple_stacks"]:
            signals.append("Heavy club stack: " + ", ".join(f"{x['club']} ×{x['count']}" for x in squad["triple_stacks"]))
        elif squad["club_concentration"]:
            top = squad["club_concentration"][:2]
            signals.append("Concentrated in " + ", ".join(f"{x['club']} ×{x['count']}" for x in top))
        if squad["differentials"] >= 5:
            signals.append("High-differential squad")
        elif squad["template_players"] >= 10:
            signals.append("Template-heavy squad")
        if transfer["style"] in ("Aggressive", "Active"):
            signals.append(f"{transfer['style']} transfer style")
        if transfer["total_hit_cost"] > 0:
            signals.append(f"Has spent {transfer['total_hit_cost']} pts on hits")
        if chip["remaining_count"]:
            signals.append(f"{chip['remaining_count']} chips remaining this half")

        managers.append({
            "entry_id": entry_id,
            "manager": m.get("manager"),
            "team_name": m.get("team_name"),
            "rank": m.get("rank"),
            "total_points": m.get("total_points"),
            "gap_to_me": m.get("gap_to_me", 0 if entry_id == me.get("entry_id") else None),
            "is_me": entry_id == me.get("entry_id"),
            "squad": squad,
            "chips": chip,
            "free_transfers": ft,
            "transfers": transfer,
            "signals": signals[:5],
        })

    managers.sort(key=lambda x: (x.get("rank") if x.get("rank") is not None else 999999, x.get("entry_id")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "status": "SUCCESS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_gw": current_gw,
        "me": {"entry_id": me.get("entry_id")},
        "managers": managers,
    }, indent=2))
    print(f"Wrote {OUT} with {len(managers)} manager profiles")


if __name__ == "__main__":
    main()
