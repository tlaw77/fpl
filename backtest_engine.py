import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY = Path('data/history')
OUT = Path('data/backtest_summary.json')


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


def archived_gws():
    out = []
    for d in HISTORY.glob('gw*'):
        try:
            gw = int(d.name[2:])
        except Exception:
            continue
        if (d / 'manifest.json').exists():
            out.append(gw)
    return sorted(out)


def outcome_points(path):
    data = load(path, {})
    return {
        int(p.get('player_id') or 0): n(p.get('total_points'))
        for p in data.get('players') or [] if p.get('player_id')
    }


def squad_points(snapshot):
    rows = snapshot.get('squad') or []
    return {int(p.get('player_id') or 0): n(p.get('live_points')) for p in rows if p.get('player_id')}


def frozen_lineup_score(xi_ids, captain_id, pts, hit=0):
    if not xi_ids:
        return None
    missing = [int(pid) for pid in xi_ids if int(pid) not in pts]
    if missing:
        return None
    score = sum(pts[int(pid)] for pid in xi_ids)
    if int(captain_id or 0):
        if int(captain_id) not in pts:
            return None
        score += pts[int(captain_id)]
    return round(score - n(hit), 2)


def evaluate_captain(source, target, target_gw):
    cap_path = source / 'captaincy_review.json'
    tc_path = source / 'triple_captain_review.json'
    outcome_path = target / 'player_outcomes.json'
    fallback_path = target / 'dashboard_snapshot.json'
    if not cap_path.exists():
        return None

    cap = load(cap_path)
    if int(cap.get('next_gw') or 0) != target_gw:
        return None

    pts = outcome_points(outcome_path) if outcome_path.exists() else squad_points(load(fallback_path, {}))
    captain = cap.get('captain') or {}
    shortlist = cap.get('shortlist') or []
    captain_id = int(captain.get('player_id') or 0)
    captain_actual = pts.get(captain_id)
    if captain_actual is None:
        return None

    evaluated = []
    for p in shortlist:
        pid = int(p.get('player_id') or 0)
        if pid not in pts:
            continue
        evaluated.append({
            'player_id': pid,
            'player': p.get('player'),
            'forecast_points': n(p.get('expected_points')),
            'actual_points': pts[pid],
            'forecast_error': round(pts[pid] - n(p.get('expected_points')), 2),
        })
    if not evaluated:
        return None
    best = max(evaluated, key=lambda x: x['actual_points'])
    captain_forecast = n(captain.get('expected_points'))

    tc = load(tc_path, {}) if tc_path.exists() else {}
    tc_decision = tc.get('decision') or {}
    tc_candidate = tc_decision.get('candidate') or {}
    tc_candidate_id = int(tc_candidate.get('player_id') or 0)
    tc_actual = pts.get(tc_candidate_id) if tc_candidate_id else None

    return {
        'captain': captain.get('player'),
        'captain_player_id': captain_id,
        'captain_forecast_points': round(captain_forecast, 2),
        'captain_actual_points': captain_actual,
        'captain_forecast_error': round(captain_actual - captain_forecast, 2),
        'best_shortlisted_player': best['player'],
        'best_shortlisted_actual_points': best['actual_points'],
        'captain_regret_points': round(best['actual_points'] - captain_actual, 2),
        'captain_was_best_shortlisted': captain_id == best['player_id'],
        'shortlist': evaluated,
        'tc_review_status': tc_decision.get('status'),
        'tc_candidate': tc_candidate.get('player'),
        'tc_candidate_actual_points': tc_actual,
        'hypothetical_extra_tc_points': tc_actual,
    }


def evaluate_transfer(source, target, target_gw):
    sim_path = source / 'simulation.json'
    synth_path = source / 'decision_synthesis.json'
    outcome_path = target / 'player_outcomes.json'
    if not sim_path.exists() or not synth_path.exists() or not outcome_path.exists():
        return None

    sim = load(sim_path)
    synth = load(synth_path)
    if int((sim.get('backtest_contract') or {}).get('target_gw') or 0) != target_gw:
        return None
    if int(sim.get('engine_version') or 0) < 4:
        return None

    pts = outcome_points(outcome_path)
    contract = sim.get('backtest_contract') or {}
    baseline_score = frozen_lineup_score(
        contract.get('baseline_xi_ids') or [], contract.get('baseline_captain_id'), pts, 0
    )
    if baseline_score is None:
        return None

    routes = []
    for route in sim.get('routes') or []:
        if route.get('action') != 'TRANSFER':
            continue
        score = frozen_lineup_score(
            route.get('post_transfer_xi_ids') or [], route.get('post_transfer_captain_id'),
            pts, route.get('hit_cost') or 0,
        )
        if score is None:
            continue
        routes.append({
            'route': route.get('route'),
            'out_player_id': route.get('out_player_id'),
            'in_player_id': route.get('in_player_id'),
            'hit_cost': n(route.get('hit_cost')),
            'realized_gw_score': score,
            'realized_delta_vs_hold': round(score - baseline_score, 2),
            'expected_points_6gw': n(route.get('expected_points_6gw')),
            'expected_rank_after_horizon': n(route.get('expected_rank_after_horizon')),
            'incoming_starts': route.get('incoming_starts_gw3'),
        })
    if not routes:
        return None

    routes.sort(key=lambda x: x['realized_gw_score'], reverse=True)
    best = routes[0]
    current_action = synth.get('current_action') or {}
    action = str(current_action.get('action') or '').upper()
    chosen_score = baseline_score if action == 'HOLD' else None
    chosen_label = 'HOLD' if action == 'HOLD' else current_action.get('headline')

    # If a future synthesis explicitly recommends a transfer and exposes its route, match
    # it here. Current completed-transfer states intentionally evaluate the *additional*
    # move decision, for which HOLD is the authoritative action.
    chosen_route = current_action.get('route')
    if action == 'TRANSFER' and chosen_route:
        match = next((x for x in routes if x['route'] == chosen_route), None)
        if match:
            chosen_score = match['realized_gw_score']
            chosen_label = match['route']

    best_available_score = max(baseline_score, best['realized_gw_score'])
    decision_regret = None if chosen_score is None else round(best_available_score - chosen_score, 2)
    decision_was_best = None if chosen_score is None else abs(chosen_score - best_available_score) < 1e-9

    return {
        'authoritative_action': action or None,
        'chosen_label': chosen_label,
        'hold_realized_score': baseline_score,
        'best_transfer_route': best['route'],
        'best_transfer_realized_score': best['realized_gw_score'],
        'best_transfer_delta_vs_hold': best['realized_delta_vs_hold'],
        'chosen_realized_score': chosen_score,
        'decision_regret_points': decision_regret,
        'decision_was_best_available': decision_was_best,
        'routes': routes,
        'method_note': 'Uses the XI/captain frozen in the simulation at decision time and scores those exact lineups against archived all-player outcomes. No hindsight lineup optimisation is allowed.',
    }


def evaluate_pair(source_gw, target_gw):
    source = HISTORY / f'gw{source_gw}'
    target = HISTORY / f'gw{target_gw}'
    captain = evaluate_captain(source, target, target_gw)
    transfer = evaluate_transfer(source, target, target_gw)
    if captain is None and transfer is None:
        return None
    return {
        'decision_archive_gw': source_gw,
        'evaluated_gw': target_gw,
        'captaincy': captain,
        'transfer_decision': transfer,
    }


def summary(rows):
    cap_rows = [r['captaincy'] for r in rows if r.get('captaincy')]
    transfer_rows = [r['transfer_decision'] for r in rows if r.get('transfer_decision')]
    out = {
        'captain_evaluable_gameweeks': len(cap_rows),
        'transfer_evaluable_gameweeks': len(transfer_rows),
        'captain_best_shortlist_rate_pct': None,
        'average_captain_regret_points': None,
        'average_captain_forecast_error': None,
        'transfer_decision_best_rate_pct': None,
        'average_transfer_decision_regret_points': None,
    }
    if cap_rows:
        out['captain_best_shortlist_rate_pct'] = round(100 * sum(1 for r in cap_rows if r['captain_was_best_shortlisted']) / len(cap_rows), 1)
        out['average_captain_regret_points'] = round(sum(n(r['captain_regret_points']) for r in cap_rows) / len(cap_rows), 2)
        out['average_captain_forecast_error'] = round(sum(n(r['captain_forecast_error']) for r in cap_rows) / len(cap_rows), 2)
    if transfer_rows:
        judged = [r for r in transfer_rows if r.get('decision_was_best_available') is not None]
        if judged:
            out['transfer_decision_best_rate_pct'] = round(100 * sum(1 for r in judged if r['decision_was_best_available']) / len(judged), 1)
            out['average_transfer_decision_regret_points'] = round(sum(n(r['decision_regret_points']) for r in judged) / len(judged), 2)
    out['message'] = (
        'Not enough completed evidence yet. Backtest rates will populate only when a pre-Gameweek decision snapshot and the following finalized all-player outcome snapshot both exist.'
        if not cap_rows and not transfer_rows else
        'Early backtest only. Treat these results as descriptive until several completed Gameweeks accumulate.'
    )
    return out


def main():
    gws = archived_gws()
    rows = []
    for source_gw in gws:
        target_gw = source_gw + 1
        if target_gw not in gws:
            continue
        row = evaluate_pair(source_gw, target_gw)
        if row:
            rows.append(row)

    out_summary = summary(rows)
    output = {
        'status': 'SUCCESS',
        'version': 2,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'finalized_gameweeks': gws,
        'evaluable_gameweeks': len(rows),
        'summary': out_summary,
        'rows': rows,
        'method_note': 'Backtest pairs a historical decision snapshot with the following finalized Gameweek. Captaincy uses archived shortlist forecasts. Transfer evaluation uses frozen pre/post-transfer XI and captain IDs stored by simulation engine v4 and all-player FPL outcomes, preventing hindsight lineup optimisation.'
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'version': 2, 'evaluable_gameweeks': len(rows), 'summary': out_summary}))


if __name__ == '__main__':
    main()
