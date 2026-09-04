import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


DATA = Path("data")
OUT = DATA / "decision_twin.json"
VALID_VERDICTS = {"SUPPORT", "CHALLENGE", "WATCH", "HOLD", "CONTESTED"}


def load(name, required=False):
    path = DATA / f"{name}.json"
    try:
        value = json.loads(path.read_text())
        if required and value.get("status") != "SUCCESS":
            raise ValueError(f"{path} is not successful")
        return value
    except Exception:
        if required:
            raise
        return {}


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def route(action):
    if not action:
        return "ROLL"
    if action.get("action") != "TRANSFER":
        return str(action.get("route") or action.get("action") or "ROLL")
    return str(action.get("route") or "TRANSFER")


def first_action(model):
    return ((model.get("recommendation") or {}).get("actions") or [{}])[0]


def clamp(value, low=0, high=100):
    return max(low, min(high, int(round(value))))


def perspective(agent, focus, verdict, confidence, argument, evidence):
    assert verdict in VALID_VERDICTS
    return {
        "agent": agent,
        "focus": focus,
        "verdict": verdict,
        "confidence": clamp(confidence),
        "argument": argument,
        "evidence": evidence,
    }


def build(inputs, previous=None, now=None):
    latest = inputs["latest"]
    synthesis = inputs["decision_synthesis"]
    simulation = inputs["simulation"]
    paths = inputs["path_simulation"]
    adaptive = inputs["adaptive_rival_simulation"]
    chips = inputs["chip_activation_gate"]
    captaincy = inputs["captaincy_review"]
    market = inputs.get("market") or {}
    scout = inputs.get("scout_consensus") or {}
    press = inputs.get("press_conference_watch") or {}
    stability = inputs.get("simulation_stability") or {}
    backtest = inputs.get("backtest_summary") or {}

    generated = now or datetime.now(timezone.utc)
    action = synthesis.get("current_action") or {}
    robustness = synthesis.get("robustness") or {}
    primary = simulation.get("recommendation") or {}
    primary_route = str(primary.get("route") or action.get("headline") or "Hold / roll")
    sim_routes = simulation.get("routes") or []
    alternative = next((item for item in sim_routes if str(item.get("route")) != primary_route), {})
    if not alternative and len(sim_routes) > 1:
        alternative = sim_routes[1]

    edge = number(robustness.get("single_step_edge_over_hold_6gw"))
    required_edge = number(robustness.get("required_edge"))
    support = int(robustness.get("measured_leader_support_models") or 0)
    required_support = int(robustness.get("required_consensus_models") or 0)
    gate_clear = bool(robustness.get("transfer_clears_gate"))
    confidence = clamp(action.get("confidence") or 0)
    action_name = str(action.get("action") or "HOLD")

    model_routes = [primary_route, route(first_action(paths)), route(first_action(adaptive))]
    agreement_count = sum(1 for item in model_routes if item == primary_route)
    model_agreement = round(agreement_count / max(1, len(model_routes)) * 100)

    stability_summary = stability.get("summary") or {}
    persistence = number(stability_summary.get("action_persistence_pct"))
    stability_runs = int(stability_summary.get("effective_evidence_runs") or stability_summary.get("window_runs") or 0)
    quant_verdict = "SUPPORT" if gate_clear or action_name in {"HOLD", "ROLL"} else "CHALLENGE"
    quant_argument = (
        f"The leading route is {primary_route}. Its {edge:.2f}-point six-GW edge is tested against a "
        f"{required_edge:.2f}-point hurdle with {support}/{max(required_support, 1)} required model support."
    )

    rivals = simulation.get("rivals") or []
    gain_probability = number(primary.get("prob_gain_league_place")) * 100
    rival_verdict = "SUPPORT" if gain_probability >= 55 else "WATCH" if gain_probability >= 45 else "CHALLENGE"
    rival_argument = (
        f"The simulated route has a {gain_probability:.1f}% probability of gaining a league place against "
        f"{len(rivals)} modelled rivals; adaptive rivals prefer {route(first_action(adaptive))}."
    )

    scout_articles = int(scout.get("article_count") or 0)
    scout_players = scout.get("players") or []
    press_players = press.get("players") or []
    evidence_verdict = "SUPPORT" if scout_articles >= 20 and not press_players else "WATCH"
    evidence_argument = (
        f"The evidence layer covers {scout_articles} public Scout/news items and {len(scout_players)} matched players. "
        f"{len(press_players)} current-squad players carry a press-conference signal."
    )

    spread = number(primary.get("p90_points_6gw")) - number(primary.get("p10_points_6gw"))
    risk_verdict = "CHALLENGE" if action_name == "TRANSFER" and not gate_clear else "WATCH" if spread >= 75 else "SUPPORT"
    risk_argument = (
        f"The simulated six-GW outcome range spans {spread:.1f} points. Action persistence is "
        f"{persistence:.0f}% across {stability_runs} effective stability runs."
    )

    chip_rows = {name: chips.get(name) or {} for name in ("wildcard", "free_hit", "bench_boost", "triple_captain")}
    active_chips = [name.replace("_", " ").title() for name, row in chip_rows.items() if row.get("status") in {"WATCH", "CONSIDER"}]
    chip_verdict = "WATCH" if active_chips else "HOLD"
    chip_argument = (
        f"Portfolio pressure is {chips.get('portfolio_pressure') or 'unknown'}. "
        + (f"Active watchlist: {', '.join(active_chips)}." if active_chips else "All four chips remain below activation level.")
    )

    council = [
        perspective("Quant Analyst", "Magnitude and model agreement", quant_verdict, confidence, quant_argument,
                    ["simulation", "path_simulation", "decision_synthesis"]),
        perspective("Rival Strategist", "Mini-league consequence", rival_verdict, 50 + abs(gain_probability - 50), rival_argument,
                    ["simulation", "adaptive_rival_simulation"]),
        perspective("Evidence Scout", "News, role and availability", evidence_verdict, min(86, 42 + scout_articles / 5), evidence_argument,
                    ["scout_consensus", "press_conference_watch"]),
        perspective("Risk Officer", "Downside and fragility", risk_verdict, 55 + min(30, spread / 4), risk_argument,
                    ["simulation", "simulation_stability"]),
        perspective("Chip Planner", "Portfolio option value", chip_verdict, 72, chip_argument,
                    ["chip_activation_gate"]),
    ]

    challenged = [item["agent"] for item in council if item["verdict"] in {"CHALLENGE", "CONTESTED"}]
    chair_verdict = "CONTESTED" if challenged else "SUPPORT"
    chair_argument = (
        f"Keep the authoritative action: {action.get('headline') or action_name}. "
        + (f"It remains live but is challenged by {', '.join(challenged)}." if challenged else "No specialist presents enough contrary evidence to overturn it.")
    )
    council.append(perspective("Decision Chair", "Resolved recommendation", chair_verdict, confidence, chair_argument,
                               ["decision_synthesis", "specialist_council"] ))

    timestamps = []
    for name, payload in inputs.items():
        stamp = iso(payload.get("generated_at_utc") or payload.get("generated_at")) if payload else None
        if stamp:
            timestamps.append((name, stamp))
    newest = max((stamp for _, stamp in timestamps), default=generated)
    oldest = min((stamp for _, stamp in timestamps), default=generated)
    age_minutes = max(0, round((generated - newest).total_seconds() / 60))

    market_watch = [row for row in (market.get("urgent_relevant") or []) if row.get("urgency") in {"watch", "act"}]
    captain_edge = number(captaincy.get("score_edge_to_second"))
    breakers = [
        {
            "signal": "model_consensus",
            "state": f"{support}/{max(required_support, 1)} support",
            "review_when": f"support reaches {max(required_support, 1)} models or the leader changes",
            "priority": "high",
        },
        {
            "signal": "edge_over_hold",
            "state": f"{edge:.2f} points",
            "review_when": f"edge crosses the {required_edge:.2f}-point action hurdle",
            "priority": "high",
        },
        {
            "signal": "availability_news",
            "state": f"{len(press_players)} squad signals",
            "review_when": "official or press-conference evidence changes expected minutes",
            "priority": "high",
        },
        {
            "signal": "market_flexibility",
            "state": f"{len(market_watch)} relevant price watches",
            "review_when": "a preferred route becomes unaffordable or an owned player loses value",
            "priority": "medium",
        },
        {
            "signal": "captaincy_separation",
            "state": f"{captain_edge:.2f} score edge",
            "review_when": "captain leader changes or the top-two gap materially widens",
            "priority": "medium",
        },
    ]

    fingerprint = {
        "gw": latest.get("next_gw"),
        "action": action_name,
        "headline": action.get("headline"),
        "leader": primary_route,
        "captain": (captaincy.get("captain") or {}).get("player_id"),
        "chip_states": {key: row.get("status") for key, row in chip_rows.items()},
    }
    certificate_id = "DT-" + hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()[:12].upper()
    previous_certificate = (previous or {}).get("decision_certificate") or {}
    changed_fields = [key for key in ("action", "headline") if previous_certificate.get(key) not in (None, action.get(key))]

    baseline = simulation.get("backtest_contract") or {}
    xi = baseline.get("baseline_xi_ids") or captaincy.get("recommended_xi_ids") or []
    captain_id = baseline.get("baseline_captain_id") or (captaincy.get("captain") or {}).get("player_id")
    evaluable = int(backtest.get("evaluable_gameweeks") or 0)
    learning_stage = "collecting" if evaluable < 3 else "provisional" if evaluable < 6 else "calibrating" if evaluable < 10 else "adaptive"

    return {
        "status": "SUCCESS",
        "version": 1,
        "generated_at_utc": generated.isoformat(),
        "current_gw": latest.get("current_gw"),
        "next_gw": latest.get("next_gw"),
        "progress": {
            "label": "Decision Twin v1",
            "completion_pct": 100,
            "completed_gates": 6,
            "total_gates": 6,
            "state": "COMPLETE",
        },
        "decision_certificate": {
            "certificate_id": certificate_id,
            "action": action_name,
            "headline": action.get("headline") or action_name,
            "confidence": confidence,
            "objective": "Maximise mini-league winning potential while protecting downside and future flexibility.",
            "six_gw_edge_over_hold": round(edge, 2),
            "probability_gain_league_place_pct": round(gain_probability, 1),
            "strongest_alternative": alternative.get("route") or "No distinct measured alternative",
            "alternative_expected_points_6gw": alternative.get("expected_points_6gw"),
            "rationale": action.get("reason") or chair_argument,
            "evidence": {
                "newest_at_utc": newest.isoformat(),
                "oldest_at_utc": oldest.isoformat(),
                "age_minutes": age_minutes,
                "sources_available": len(timestamps),
            },
        },
        "council": council,
        "council_summary": {
            "state": "CONTESTED" if challenged else "ALIGNED",
            "model_route_agreement_pct": model_agreement,
            "challengers": challenged,
            "resolved_position": action.get("headline") or action_name,
            "rule": "Specialists may challenge the authoritative synthesis but cannot silently replace it.",
        },
        "change_radar": {
            "decision_changed": bool(changed_fields),
            "changed_fields": changed_fields,
            "previous_certificate_id": previous_certificate.get("certificate_id"),
            "decision_breakers": breakers,
            "notification_rule": "Notify only when action/headline changes or a high-priority breaker crosses its stated review condition.",
        },
        "learning_contract": {
            "target_gw": baseline.get("target_gw") or latest.get("next_gw"),
            "decision_certificate_id": certificate_id,
            "recommended_action": action_name,
            "recommended_route": primary_route,
            "baseline_xi_ids": xi,
            "baseline_captain_id": captain_id,
            "alternative_routes": [row.get("route") for row in sim_routes[1:4] if row.get("route")],
            "evaluable_gameweeks": evaluable,
            "learning_stage": learning_stage,
            "tuning_allowed": evaluable >= 6,
            "rule": "Score decision quality and calibration after the target GW; do not tune from isolated outcomes.",
        },
        "what_if_prompts": [
            "What changes if the captain is ruled out?",
            "What evidence would make the leading transfer worth a hit?",
            "Which route maximises league-place gain rather than expected points?",
            "What is lost by waiting for the final press conferences?",
        ],
        "method_note": "Decision Twin v1 packages existing deterministic and probabilistic evidence into an auditable council, decision-change radar and frozen learning contract. It does not use generative opinion to alter the authoritative action.",
    }


def run():
    names = [
        "latest", "decision_synthesis", "simulation", "path_simulation",
        "adaptive_rival_simulation", "chip_activation_gate", "captaincy_review",
        "market", "scout_consensus", "press_conference_watch",
        "simulation_stability", "backtest_summary",
    ]
    required = set(names[:7])
    inputs = {name: load(name, required=name in required) for name in names}
    previous = load("decision_twin")
    output = build(inputs, previous=previous)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "status": output["status"],
        "certificate_id": output["decision_certificate"]["certificate_id"],
        "action": output["decision_certificate"]["action"],
        "council_state": output["council_summary"]["state"],
        "completion_pct": output["progress"]["completion_pct"],
    }))


if __name__ == "__main__":
    run()
