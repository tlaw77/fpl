import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
SIM = Path('data/simulation.json')
PATH_SIM = Path('data/path_simulation.json')
ADAPTIVE = Path('data/adaptive_rival_simulation.json')
CHIPS = Path('data/chip_path_simulation.json')
PLAYER_POOL = Path('data/player_pool.json')
OUT = Path('data/decision_synthesis.json')
DEFAULT_FREE_TRANSFER_CAP = 5


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


def normalise_name(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(c for c in text if not unicodedata.combining(c)).lower().strip()


def fixture_timing(route, latest, player_pool):
    """Describe when a route's fixture advantage arrives without double-counting it.

    Projected points already contain fixture difficulty, so this is decision
    context and only modulates the small value assigned to an expiring FT.
    """
    if not route or '→' not in route:
        return {'available': False, 'summary': 'No measured transfer route to compare.'}
    out_name, in_name = [x.strip() for x in route.split('→', 1)]
    rows = (latest.get('current_squad_next5') or latest.get('squad_next5') or []) + (player_pool.get('players') or [])
    by_name = {}
    for row in rows:
        by_name.setdefault(normalise_name(row.get('player')), row)
    outgoing = by_name.get(normalise_name(out_name))
    incoming = by_name.get(normalise_name(in_name))
    if not outgoing or not incoming:
        return {'available': False, 'summary': 'Fixture timing unavailable for this route.'}

    next_gw = int(latest.get('next_gw') or 0)
    def difficulties(row):
        fixtures = [f for f in (row.get('fixtures') or []) if int(f.get('gw') or 0) >= next_gw]
        return [float(f.get('difficulty') or 3) for f in fixtures[:3]]
    out_diffs, in_diffs = difficulties(outgoing), difficulties(incoming)
    count = min(len(out_diffs), len(in_diffs), 3)
    if not count:
        return {'available': False, 'summary': 'Fixture timing unavailable for this route.'}
    swings = [out_diffs[i] - in_diffs[i] for i in range(count)]
    weights = [.55, .30, .15][:count]
    weighted = sum(s * w for s, w in zip(swings, weights)) / sum(weights)
    first = swings[0]
    if first >= 1 or weighted >= .6:
        label = 'front_loaded'
        wording = 'The incoming player has the easier immediate fixture run.'
    elif first <= -1 and weighted < 0:
        label = 'defer_friendly'
        wording = 'The outgoing player has the easier immediate fixture; the move can wait unless other evidence changes.'
    else:
        label = 'balanced'
        wording = 'The fixture swing is broadly balanced rather than time-critical.'
    return {
        'available': True,
        'route': route,
        'next_fixture_swing': round(first, 2),
        'weighted_three_fixture_swing': round(weighted, 2),
        'outgoing_difficulties': out_diffs[:count],
        'incoming_difficulties': in_diffs[:count],
        'timing': label,
        'summary': wording,
    }


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
    player_pool = load(PLAYER_POOL)

    sim_routes = sim.get('routes') or []
    sim_top = sim.get('recommendation') or (sim_routes[0] if sim_routes else {})
    roll = next((x for x in sim_routes if x.get('action') == 'ROLL'), {})
    sim_edge = n(sim_top.get('expected_points_6gw')) - n(roll.get('expected_points_6gw'))

    path_top = paths.get('recommendation') or {}
    adaptive_top = adaptive.get('recommendation') or {}
    pa = first_action(path_top)
    aa = first_action(adaptive_top)

    sim_route = str(sim_top.get('route') or 'ROLL')
    routes = [sim_route, route_of(pa), route_of(aa)]
    exact_counts = {r: routes.count(r) for r in set(routes)}
    exact_consensus = max(exact_counts.values(), default=0)
    measured_leader_support = routes.count(sim_route)

    incoming = [incoming_of(pa), incoming_of(aa)]
    if sim_top.get('route'):
        incoming.append(sim_route.split('→', 1)[1].strip() if '→' in sim_route else sim_route)
    incoming_counts = {r: incoming.count(r) for r in set(incoming)}
    target_consensus = max(incoming_counts.values(), default=0)
    measured_target = sim_route.split('→', 1)[1].strip() if '→' in sim_route else sim_route
    measured_target_support = incoming.count(measured_target)

    maturity = n(sim.get('season_maturity_weight'), n(paths.get('season_maturity_weight'), .25))
    hit_cost = int(latest.get('next_transfer_hit_cost') or sim.get('next_transfer_hit_cost') or 0)
    ft_cap = max(1, int(latest.get('free_transfer_cap') or DEFAULT_FREE_TRANSFER_CAP))
    ft_before = int(latest.get('free_transfers_available_before_moves') or latest.get('free_transfers_next_gw') or (latest.get('me') or {}).get('free_transfers_next_gw') or 1)
    remaining_ft = int(latest.get('free_transfers_remaining_next_gw') if latest.get('free_transfers_remaining_next_gw') is not None else ft_before)
    completed = completed_current_transfer(latest)
    timing = fixture_timing(sim_route, latest, player_pool)

    if hit_cost:
        edge_hurdle = 8.0 if maturity < .35 else 6.0 if maturity < .55 else 4.5
        consensus_required = 2
    else:
        edge_hurdle = 3.0 if maturity < .35 else 2.0
        consensus_required = 2

    base_edge_hurdle = edge_hurdle
    hold_next_ft = min(ft_cap, remaining_ft + 1)
    ft_would_expire = remaining_ft >= ft_cap and hit_cost == 0
    if ft_would_expire:
        timing_swing = n(timing.get('weighted_three_fixture_swing')) if timing.get('available') else 0
        expiry_credit = 1.0 if timing_swing >= .5 else .35 if timing_swing <= -.5 else .75
        rollover_pressure = 'expiring'
    elif remaining_ft == ft_cap - 1:
        expiry_credit = 0.0
        rollover_pressure = 'approaching_cap'
    else:
        expiry_credit = 0.0
        rollover_pressure = 'bankable'
    edge_hurdle = max(1.0, edge_hurdle - expiry_credit)

    if ft_would_expire:
        rollover_sentence = (
            f'The bank is at {remaining_ft}/{ft_cap}; holding would forfeit the next free transfer, so the edge hurdle is '
            f'reduced by {expiry_credit:.2f} points, but route agreement is still required.'
        )
    elif remaining_ft == ft_cap - 1:
        rollover_sentence = f'Holding moves the bank from {remaining_ft}/{ft_cap} to {hold_next_ft}/{ft_cap}; nothing expires this deadline, but the following hold would waste a transfer.'
    else:
        rollover_sentence = f'Holding moves the bank from {remaining_ft}/{ft_cap} to {hold_next_ft}/{ft_cap}; no free transfer expires.'

    transfer_clears = (
        sim_top.get('action') == 'TRANSFER'
        and sim_edge >= edge_hurdle
        and measured_leader_support >= consensus_required
    )

    if transfer_clears:
        action = 'TRANSFER'
        headline = sim_route
        confidence = min(91, int(62 + min(16, sim_edge * 1.8) + measured_leader_support * 4 + maturity * 8))
        reason = (
            f'The leading move clears the {edge_hurdle:.1f}-point robustness hurdle after hit cost and '
            f'the same measured route is supported by {measured_leader_support}/3 decision models. '
            f'{rollover_sentence} {timing.get("summary")}'
        )
    else:
        action = 'HOLD'
        headline = 'Transfer complete · hold' if completed else 'Hold / roll'
        confidence = min(88, int(66 + (1 - maturity) * 10 + (3 - measured_leader_support) * 3))
        if hit_cost and completed:
            reason = (
                f'{completed.get("route") or "This week’s transfer"} is already applied. A further move costs -{hit_cost}. '
                f'The best six-GW alternative is only {sim_edge:.1f} projected points ahead of holding, below the '
                f'{edge_hurdle:.1f}-point early-season hurdle, and the measured leader is supported by only {measured_leader_support}/3 models. '
                f'{rollover_sentence} {timing.get("summary")}'
            )
        elif hit_cost:
            reason = (
                f'A further move costs -{hit_cost}. The best simulated edge is {sim_edge:.1f} over holding and does not '
                f'clear the full magnitude-and-consensus robustness gate. {rollover_sentence} {timing.get("summary")}'
            )
        else:
            reason = (
                f'The leading transfer edge is {sim_edge:.1f} projected points over holding and does not yet clear the '
                f'full evidence hurdle with sufficient agreement on that exact route. {rollover_sentence} {timing.get("summary")}'
            )

    best_tc = chips.get('best_triple_captain_window') or {}
    best_bb = chips.get('best_bench_boost_window') or {}
    tc_gain = n(best_tc.get('chip_incremental_expected_points'))
    bb_gain = n(best_bb.get('chip_incremental_expected_points'))
    portfolio = paths.get('chip_portfolio_context') or {}
    pressure = str(portfolio.get('pressure') or 'comfortable').lower()

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
        'version': 3,
        'current_gw': latest.get('current_gw'),
        'next_gw': latest.get('next_gw'),
        'current_action': {
            'action': action,
            'headline': headline,
            'confidence': confidence,
            'reason': reason,
            'completed_transfer': completed,
            'free_transfers_remaining': remaining_ft,
            'free_transfer_cap': ft_cap,
            'free_transfer_would_expire_on_hold': ft_would_expire,
            'next_transfer_hit_cost': hit_cost,
        },
        'robustness': {
            'season_maturity_weight': round(maturity, 3),
            'single_step_leader': sim_top.get('route'),
            'single_step_edge_over_hold_6gw': round(sim_edge, 2),
            'multi_gw_first_action': route_of(pa),
            'adaptive_rival_first_action': route_of(aa),
            'exact_route_consensus_models': exact_consensus,
            'measured_leader_support_models': measured_leader_support,
            'same_incoming_target_consensus_models': target_consensus,
            'measured_target_support_models': measured_target_support,
            'base_required_edge': base_edge_hurdle,
            'required_edge': edge_hurdle,
            'required_consensus_models': consensus_required,
            'transfer_clears_gate': transfer_clears,
            'free_transfers_before_moves': ft_before,
            'free_transfers_before_decision': remaining_ft,
            'free_transfer_cap': ft_cap,
            'free_transfer_headroom': max(0, ft_cap - remaining_ft),
            'hold_next_week_free_transfers': hold_next_ft,
            'free_transfer_would_expire_on_hold': ft_would_expire,
            'rollover_pressure': rollover_pressure,
            'rollover_edge_credit': round(expiry_credit, 2),
            'fixture_timing': timing,
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
        'method_note': 'Authoritative decision gate. It synthesises single-step Monte Carlo, multi-GW beam search, probabilistic rival response, the five-transfer rollover ceiling, fixture timing, live transfer-hit state, season maturity and chip option value. Fixture difficulty is already priced into projected points; timing is used as context and to scale only the small credit for a transfer that would otherwise expire. A route is promoted only when it clears both magnitude and cross-model support thresholds.',
    }

    latest['decision_synthesis'] = output
    LATEST.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + '\n')
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')

    # Persist the monitoring signal after the authoritative files are written.
    try:
        from decision_signal_history import run as record_signal_history
        record_signal_history()
    except Exception as exc:
        print(json.dumps({'warning': 'decision_signal_history_failed', 'error': str(exc)}))

    print(json.dumps({'status': 'SUCCESS', 'action': action, 'headline': headline, 'sim_edge': round(sim_edge, 2), 'measured_support': measured_leader_support, 'chip_action': chip_action}))


if __name__ == '__main__':
    run()
