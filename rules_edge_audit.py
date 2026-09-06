"""Publish a compact contract showing which official FPL edges are enforced."""

import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/rules_edge_audit.json")


RULES = [
    ("transfer_bank", "Up to five free transfers; only one earned per GW", "fpl_etl.py + path_simulation_v3.py"),
    ("transfer_cap_pressure", "Avoid wasting the earned transfer when already on five", "decision_synthesis.py"),
    ("transfer_hits", "Each transfer beyond the free bank costs four points", "declared_transfer_overlay.py + simulation_engine_v2.py"),
    ("wildcard_hit_rescue", "Wildcard erases transfer deductions already made that GW", "chip_activation_gate.py"),
    ("chip_sets", "Fresh four-chip set after GW19; unused first set expires", "strategy_watch.py + chip_window.py"),
    ("one_chip", "Only one chip may be active in a Gameweek", "chip_window.py"),
    ("free_hit_sequence", "Free Hits cannot be used in consecutive Gameweeks", "strategy_watch.py + chip_window.py"),
    ("free_hit_restore", "Free Hit is temporary and preserves the permanent squad", "strategy_watch.py"),
    ("squad_legality", "15-player positional, budget and maximum-three-per-club rules", "current_squad.py + full_squad_chip_optimizer.py"),
    ("xi_legality", "Starting XI retains one goalkeeper, three defenders and one forward", "current_squad.py"),
    ("captain_fallback", "Vice-captain inherits only when captain plays zero minutes", "live_gameweek.py + official post-GW processing"),
    ("double_gameweeks", "Every fixture in the same GW contributes independently", "projection_calibration.py"),
    ("defensive_contributions", "Position-specific defensive-contribution thresholds", "projection_calibration.py + official live points"),
    ("price_timing", "Daily price changes are assessed around 00:00 UK", "market_watch.py"),
    ("score_finalisation", "Live scores remain provisional until 09:00 UK after the final match", "live_gameweek.py"),
]


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def build():
    latest, strategy, chip = load("data/latest.json"), load("data/strategy.json"), load("data/chip_window.json")
    ft = int(latest.get("free_transfers_remaining_next_gw", latest.get("free_transfers_next_gw", 1)) or 0)
    cap = int(latest.get("free_transfer_cap", 5) or 5)
    inventory = (strategy.get("me") or {}).get("inventory") or {}
    edges = []
    if ft >= cap:
        edges.append({"severity": "action", "label": "Transfer expires if unused", "detail": f"You are on {ft}/{cap} free transfers; HOLD burns the next earned transfer."})
    elif ft == cap - 1:
        edges.append({"severity": "watch", "label": "Transfer-cap decision next", "detail": f"You are on {ft}/{cap}; rolling reaches the cap, so the following deadline becomes use-or-waste."})
    if inventory.get("free_hit_consecutive_blocked"):
        edges.append({"severity": "blocked", "label": "Free Hit unavailable", "detail": f"A Free Hit in GW{inventory.get('last_free_hit_gw')} blocks another in GW{inventory.get('planning_gw')}."})
    portfolio = chip.get("portfolio") or {}
    if portfolio.get("pressure") in ("tight", "critical"):
        edges.append({"severity": "action", "label": "Chip expiry pressure", "detail": portfolio.get("hard_inflection_explanation")})
    return {
        "status": "SUCCESS",
        "version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage": {"official_rules_tracked": len(RULES), "automated": len(RULES) - 1, "official_post_gw_resolution": 1, "gaps": 0},
        "active_edges": edges,
        "rules": [{"id": key, "rule": rule, "implementation": implementation, "status": "official_post_gw_resolution" if key == "captain_fallback" else "automated"} for key, rule, implementation in RULES],
        "principle": "Use rule mechanics as constraints and option value, never as a reason to override football quality, reliable minutes or expected points.",
    }


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result = build()
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], **result["coverage"], "active_edges": len(result["active_edges"])}))
