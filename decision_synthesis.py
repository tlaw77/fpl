import json
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
SIM = Path('data/simulation.json')
PATH_SIM = Path('data/path_simulation.json')
ADAPTIVE = Path('data/adaptive_rival_simulation.json')
CHIPS = Path('data/chip_path_simulation.json')
OUT = Path('data/decision_synthesis.json')


def load(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if default is None else default


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def first_action(row):
    actions = (row or {}).get('actions') or []
    return actions[0] if actions else None


def route_of(action):
    if not action or action.get('action') != 'TRANSFER':
        return 'ROLL'
    return str(action.get('route') or 'TRANSFER')


def incoming_of(action):
    route = route_of(action)
    if '→' in route:
        return route.split('→', 1)[1].strip()
    return route


def completed_current_transfer(latest):
    next_gw = int(latest.get('next_gw') or 0)
    txs = [t for t in (latest.get('current_squad_transfers') or []) if int(t.get('event') or 0) == next_gw]
    if not txs:
        return None
    tx = txs[-1]
    out_name = tx.get('out_name') or tx.get('element_out_name') or ''
    in_name = tx.get('in_name') or tx.get('element_in_name') or ''
    if not out_name or not in_name:
        declared = latest.get('declared_transfer_overlay_applied') or []
        if declared:
            out_name = declared[-1].get('out_name') or out_name
            in_name = declared[-1].get('in_name') or in_name
    return {
        'event': next_gw,
        'out': out_name,
        'in': in_name,
        'route': f'{out_name} → {in_name}' if out_name and in_name else None,
        'source': tx.get('source') or tx.get('transfer_source') or latest.get('current_squad_source'),
    }


def run():
    latest = load(LATEST)
    sim = load(SIM)
    paths = load(PATH_SIM)
    adaptive = load(ADAPTIVE)
    chips = load(CHIPS)

    sim_routes = sim.get('routes') or []
    sim_top = sim.get('recommendation') or (sim_routes[0] if sim_routes else {})
    roll = next((x for x in sim_routes if x.get('action') == 'ROLL'), {})
    sim_edge = n(sim_top.get('expected_points_6gw')) - n(roll.get('expected_points_6gw'))

    path_top = paths.get('recommendation') or {}
    adaptive_top = adaptive.get('recommendation') or {}
    pa = first_action(path_top)
    aa = first_action(adaptive_top)

    routes = [str(sim_top.get('route') or 'ROLL'), route_of(pa), route_of(aa)]
    exact_counts = {r: routes.count(r) for r in set(routes)}
    exact_consensus = max(exact_counts.values(), default=0)
    incoming = [incoming_of(pa), incoming_of(aa)]
    if sim_top.get('route'):
        sr = str(sim_top.get('route'))
        incoming.append(sr.split('→', 1)[1].strip() if '→' in sr else sr)
    incoming_counts = {r: incoming.count(r) for r in set(incoming)}
    target_consensus = max(incoming_counts.values(), default=0)

    maturity = n(sim.get('season_maturity_weight'), n(paths.get('season_maturity_weight'), .25))
    hit_cost = int(latest.get('next_transfer_hit_cost') or sim.get('next_transfer_hit_cost') or 0)
    remaining_ft = int(latest.get('free_transfers_remaining_next_gw') or 0)
    completed = completed_current_transfer(latest)

    # A second current-deadline move needs materially stronger evidence than an ordinary FT.
    if hit_cost:
        edge_hurdle = 8.0 if maturity < .35 else 6.0 if maturity < .55 else 4.5
        consensus_required = 2
    else:
        edge_hurdle = 3.0 if maturity < .35 else 2.0
        consensus_required = 2

    transfer_clears = (
        sim_top.get('action') == 'TRANSFER'
        and sim_edge >= edge_hurdle
        and exact_consensus >= consensus_required
    )

    if transfer_clears:
        action = 'TRANSFER'
        headline = str(sim_top.get('route') or route_of(pa))
        confidence = min(91, int(62 + min(16, sim_edge * 1.8) + exact_consensus * 4 + maturity * 8))
        reason = (
            f'The leading move clears the {edge_hurdle:.1f}-point robustness hurdle after hit cost and '
            f'is supported by {exact_consensus}/3 decision models.'
        )
    else:
        action = 'HOLD'
        headline = 'Transfer complete · hold' if completed else 'Hold / roll'
        confidence = min(88, int(66 + (1 - maturity) * 10 + (3 - exact_consensus) * 3))
        if hit_cost and completed:
            reason = (
                f'{completed.get("route") or "This week’s transfer"} is already applied. A further move costs -{hit_cost}. '
                f'The best six-GW alternative is only {sim_edge:.1f} projected points ahead of holding, below the '
                f'{edge_hurdle:.1f}-point early-season hurdle, and the models disagree on the best second move.'
            )
        elif hit_cost:
            reason = (
                f'A further move costs -{hit_cost}. The best simulated edge is {sim_edge:.1f} over holding and does not '
                f'clear the {edge_hurdle:.1f}-point robustness hurdle.'
            )
        else:
            reason = (
                f'The leading transfer edge is {sim_edge:.1f} projected points over holding and does not yet clear the '
                f'{edge_hurdle:.1f}-point evidence hurdle with sufficient cross-model agreement.'
            )

    best_tc = chips.get('best_triple_captain_window') or {}
    best_bb = chips.get('best_bench_boost_window') or {}
    tc_gain = n(best_tc.get('chip_incremental_expected_points'))
    bb_gain = n(best_bb.get('chip_incremental_expected_points'))
    portfolio = (paths.get('chip_portfolio_context') or {})
    pressure = str(portfolio.get('pressure') or 'comfortable').lower()

    # Visible 4-GW chip gains are not enough to consume option value while the half-season has ample slack.
    chip_play = None
    if pressure in ('urgent', 'critical'):
        candidates = [
            ('Triple Captain', tc_gain, best_tc.get('chip_gw')),
            ('Bench Boost', bb_gain, best_bb.get('chip_gw')),
        ]
        chip_play = max(candidates, key=lambda x: x[1], default=None)
    chip_action = 'HOLD'
    chip_reason = (
        f'Hold chips. Best visible TC uplift is {tc_gain:.1f} and BB uplift is {bb_gain:.1f}, but the first-half portfolio '
        f'remains {pressure} with {int(portfolio.get("slack_gameweeks") or 0)} slack Gameweeks. Preserve option value for stronger blank/double or squad-structure windows.'
    )
    if chip_play and chip_play[1] >= 12:
        chip_action = 'CONSIDER'
        chip_reason = f'{chip_play[0]} in GW{chip_play[2]} has the strongest current visible window, but should still be checked against the remaining half-season portfolio before activation.'

    next_plan = first_action(path_top) or {}
    adaptive_plan = first_action(adaptive_top) or {}
    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 1,
        'current_gw': latest.get('current_gw'),
        'next_gw': latest.get('next_gw'),
        'current_action': {
            'action': action,
            'headline': headline,
            'confidence': confidence,
            'reason': reason,
            'completed_transfer': completed,
            'free_transfers_remaining': remaining_ft,
            'next_transfer_hit_cost': hit_cost,
        },
        'robustness': {
            'season_maturity_weight': round(maturity, 3),
            'single_step_leader': sim_top.get('route'),
            'single_step_edge_over_hold_6gw': round(sim_edge, 2),
            'multi_gw_first_action': route_of(pa),
            'adaptive_rival_first_action': route_of(aa),
            'exact_route_consensus_models': exact_consensus,
            'same_incoming_target_consensus_models': target_consensus,
            'required_edge': edge_hurdle,
            'required_consensus_models': consensus_required,
            'transfer_clears_gate': transfer_clears,
        },
        'forward_plan': {
            'primary_path_first_action': next_plan,
            'adaptive_path_first_action': adaptive_plan,
            'note': 'Forward paths are planning evidence, not instructions to pre-commit future transfers. Re-optimise after each deadline and new information.',
        },
        'chips': {
            'action': chip_action,
            'reason': chip_reason,
            'best_visible_triple_captain': best_tc,
            'best_visible_bench_boost': best_bb,
            'portfolio_pressure': pressure,
            'latest_safe_start_gw': portfolio.get('latest_safe_start_gw'),
        },
        'method_note': 'Authoritative decision gate. It synthesises single-step Monte Carlo, multi-GW beam search, probabilistic rival response, live transfer-hit state, season maturity and chip option value. A high-scoring route is not promoted unless it clears both magnitude and cross-model robustness thresholds.',
    }

    latest['decision_synthesis'] = output
    LATEST.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + '\n')
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'action': action, 'headline': headline, 'sim_edge': round(sim_edge, 2), 'consensus': exact_consensus, 'chip_action': chip_action}))


if __name__ == '__main__':
    run()
