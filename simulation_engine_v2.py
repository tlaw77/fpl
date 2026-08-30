import json
import random
import statistics
from datetime import datetime, timezone

import captaincy_model as cm
import simulation_budget as sb
import simulation_engine as s
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity


def model_lineup(squad, gw, exp):
    means = {pid: v[0] for pid, v in exp.get(gw, {}).items()}
    xi, _ = s.best_xi(squad, means)
    ids = [int(p.get('player_id') or 0) for p in xi]
    cap_id = cm.choose_captain(squad, ids, gw, exp.get(gw, {}))
    return ids, cap_id


def run():
    latest = s.load_json(s.LATEST, {})
    pool = s.load_json(s.POOL, {})
    scout = s.load_json(s.SCOUT, {})
    market = s.load_json(s.MARKET, {})
    iterations = sb.iterations(latest, 'single')
    iteration_policy = sb.metadata(latest, 'single')
    by_id, by_name = s.player_maps(pool)
    scout_maps, market_maps = s.scout_lookup(scout), s.market_lookup(market)

    base_raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    base_squad = [s.enrich(p, by_id, by_name) for p in base_raw]
    base_squad = [p for p in base_squad if p]
    rivals = s.rival_squads(latest, by_id, by_name)
    candidates = s.candidate_routes(latest, base_squad, by_id, by_name)
    next_gw = int(latest.get('next_gw') or 1)
    current_gw = int(latest.get('current_gw') or max(0, next_gw - 1))
    maturity = season_maturity(current_gw)
    gws = list(range(next_gw, min(39, next_gw + s.HORIZON)))

    raw_ft = latest.get('free_transfers_remaining_next_gw')
    if raw_ft is None:
        raw_ft = (latest.get('me') or {}).get('free_transfers_next_gw')
    if raw_ft is None:
        raw_ft = 1
    remaining_ft = max(0, min(5, int(raw_ft)))
    next_hit_cost = int(latest.get('next_transfer_hit_cost') or (0 if remaining_ft > 0 else 4))

    pool_models = [s.n(p.get('six_gw_score')) for p in pool.get('players') or []]
    model_lo, model_hi = s.percentile(pool_models, .10), s.percentile(pool_models, .90)

    universe = {}
    for c in candidates:
        for p in c['squad']:
            universe[int(p.get('player_id') or 0)] = p
    for r in rivals:
        for p in r['squad']:
            universe[int(p.get('player_id') or 0)] = p
    universe.pop(0, None)

    exp = {}
    for gw in gws:
        exp[gw] = {}
        for pid, player in universe.items():
            exp[gw][pid] = calibrated_expected_gw(player, gw, model_lo, model_hi, scout_maps, market_maps, current_gw=current_gw)

    cand_lineups = {}
    for c in candidates:
        cand_lineups[c['key']] = {}
        for gw in gws:
            cand_lineups[c['key']][gw] = model_lineup(c['squad'], gw, exp)

    baseline_key = next((c['key'] for c in candidates if c.get('move') is None), 'ROLL')
    baseline_first_xi, baseline_first_cap = cand_lineups.get(baseline_key, {}).get(next_gw, ([], 0))

    rival_lineups = []
    for r in rivals:
        bygw = {}
        for gw in gws:
            bygw[gw] = model_lineup(r['squad'], gw, exp)
        rival_lineups.append(bygw)

    rng = random.Random(str(latest.get('generated_at_utc') or '') + '|simulation-v6-deadline-budget')
    me_start = s.n((latest.get('me') or {}).get('total_points'))
    current_rank = int((latest.get('me') or {}).get('rank') or (len(rivals) + 1))
    route_totals = {c['key']: [] for c in candidates}
    route_ranks = {c['key']: [] for c in candidates}
    route_gain_places = {c['key']: 0 for c in candidates}
    route_beat = {c['key']: [0] * len(rivals) for c in candidates}

    for _ in range(iterations):
        outcomes = {}
        for gw in gws:
            outcomes[gw] = {pid: s.sample_points(rng, *params) for pid, params in exp[gw].items()}

        rival_scores = []
        for idx, r in enumerate(rivals):
            total = r['total_points']
            for gw in gws:
                xi, cap = rival_lineups[idx][gw]
                total += sum(outcomes[gw].get(pid, 0) for pid in xi) + outcomes[gw].get(cap, 0)
            rival_scores.append(total)

        for c in candidates:
            total = me_start
            hit = 0 if c['move'] is None else next_hit_cost
            for gw in gws:
                xi, cap = cand_lineups[c['key']][gw]
                total += sum(outcomes[gw].get(pid, 0) for pid in xi) + outcomes[gw].get(cap, 0)
            total -= hit
            route_totals[c['key']].append(total - me_start)
            rank = 1 + sum(1 for x in rival_scores if x > total)
            route_ranks[c['key']].append(rank)
            if rank < current_rank:
                route_gain_places[c['key']] += 1
            for i, rv in enumerate(rival_scores):
                if total > rv:
                    route_beat[c['key']][i] += 1

    results = []
    for c in candidates:
        vals = route_totals[c['key']]
        ranks = route_ranks[c['key']]
        p10, p90 = s.percentile(vals, .10), s.percentile(vals, .90)
        mean = statistics.fmean(vals) if vals else 0
        exp_rank = statistics.fmean(ranks) if ranks else current_rank
        utility = mean + (current_rank - exp_rank) * 5.0 - max(0, mean - p10) * .12
        hit = 0 if c['move'] is None else next_hit_cost
        incoming_starts = None
        out_id = None
        in_id = None
        post_xi, post_cap = cand_lineups.get(c['key'], {}).get(next_gw, ([], 0))
        if c['move'] is not None and gws:
            out = c['move'].get('out') or {}
            inc = c['move'].get('safe_in') or c['move'].get('in') or {}
            out_id = int(out.get('player_id') or 0) or None
            in_id = int(inc.get('player_id') or 0) or None
            incoming_starts = bool(in_id and in_id in set(post_xi))
        results.append({
            'route': c['label'],
            'action': 'ROLL' if c['move'] is None else 'TRANSFER',
            'hit_cost': hit,
            'out_player_id': out_id,
            'in_player_id': in_id,
            'expected_points_6gw': round(mean, 2),
            'p10_points_6gw': round(p10, 2),
            'p90_points_6gw': round(p90, 2),
            'expected_rank_after_horizon': round(exp_rank, 2),
            'prob_gain_league_place': round(route_gain_places[c['key']] / iterations, 3),
            'prob_finish_ahead_each_rival': [round(route_beat[c['key']][i] / iterations, 3) for i in range(len(rivals))],
            'utility_score': round(utility, 3),
            'incoming_starts_gw3': incoming_starts,
            'decision_lineup_gw': next_gw,
            'baseline_xi_ids': list(baseline_first_xi),
            'baseline_captain_id': baseline_first_cap,
            'post_transfer_xi_ids': list(post_xi),
            'post_transfer_captain_id': post_cap,
        })
    results.sort(key=lambda x: x['utility_score'], reverse=True)

    rival_meta = [
        {'entry_id': r['entry_id'], 'team_name': r['team_name'], 'manager': r['manager'], 'rank': r['rank'], 'total_points': r['total_points']}
        for r in rivals
    ]
    winner = results[0] if results else None
    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_version': 6,
        'projection_model': 'season-maturity calibrated + shared captaincy model',
        'season_maturity_weight': round(maturity, 3),
        'iterations': iterations,
        'iteration_policy': iteration_policy,
        'horizon_gws': gws,
        'shared_outcome_simulation': True,
        'remaining_free_transfers_current_deadline': remaining_ft,
        'next_transfer_hit_cost': next_hit_cost,
        'candidate_count': len(results),
        'rivals': rival_meta,
        'recommendation': winner,
        'routes': results,
        'backtest_contract': {
            'target_gw': next_gw,
            'baseline_xi_ids': list(baseline_first_xi),
            'baseline_captain_id': baseline_first_cap,
            'note': 'Each route stores exact out/in IDs plus the pre-decision and post-transfer XI/captain selected by the model at decision time. Captaincy uses the same shared model as Pick Team. Frozen lineups can be scored against archived outcomes without hindsight optimisation.'
        },
        'method_note': 'Monte Carlo decision support from the reconstructed current squad. Early-season form and six-GW model extremes are shrunk toward position/fixture priors. Legal XI selection is followed by the shared captaincy model. Monte Carlo iteration count is deadline-aware: lighter midweek, higher precision close to the official FPL deadline; decision thresholds are unchanged.',
    }
    s.OUT.parent.mkdir(parents=True, exist_ok=True)
    s.OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'winner': winner, 'iterations': iterations, 'deadline_phase': iteration_policy['deadline_phase'], 'maturity': round(maturity, 3), 'remaining_ft': remaining_ft, 'next_hit_cost': next_hit_cost, 'engine_version': 6, 'captain': baseline_first_cap}))


if __name__ == '__main__':
    run()
