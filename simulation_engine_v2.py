import json
import random
import statistics
from datetime import datetime, timezone

import simulation_engine as s


def run():
    latest = s.load_json(s.LATEST, {})
    pool = s.load_json(s.POOL, {})
    scout = s.load_json(s.SCOUT, {})
    market = s.load_json(s.MARKET, {})
    by_id, by_name = s.player_maps(pool)
    scout_maps, market_maps = s.scout_lookup(scout), s.market_lookup(market)

    base_raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    base_squad = [s.enrich(p, by_id, by_name) for p in base_raw]
    base_squad = [p for p in base_squad if p]
    rivals = s.rival_squads(latest, by_id, by_name)
    candidates = s.candidate_routes(latest, base_squad, by_id, by_name)
    next_gw = int(latest.get('next_gw') or 1)
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
            exp[gw][pid] = s.expected_gw(player, gw, model_lo, model_hi, scout_maps, market_maps)

    cand_lineups = {}
    for c in candidates:
        cand_lineups[c['key']] = {}
        for gw in gws:
            ex = {pid: v[0] for pid, v in exp[gw].items()}
            xi, cap = s.best_xi(c['squad'], ex)
            cand_lineups[c['key']][gw] = (
                [int(p.get('player_id') or 0) for p in xi],
                int(cap.get('player_id') or 0) if cap else 0,
            )

    rival_lineups = []
    for r in rivals:
        bygw = {}
        for gw in gws:
            ex = {pid: v[0] for pid, v in exp[gw].items()}
            xi, cap = s.best_xi(r['squad'], ex)
            bygw[gw] = (
                [int(p.get('player_id') or 0) for p in xi],
                int(cap.get('player_id') or 0) if cap else 0,
            )
        rival_lineups.append(bygw)

    rng = random.Random(str(latest.get('generated_at_utc') or '') + '|simulation-v2')
    me_start = s.n((latest.get('me') or {}).get('total_points'))
    current_rank = int((latest.get('me') or {}).get('rank') or (len(rivals) + 1))
    route_totals = {c['key']: [] for c in candidates}
    route_ranks = {c['key']: [] for c in candidates}
    route_gain_places = {c['key']: 0 for c in candidates}
    route_beat = {c['key']: [0] * len(rivals) for c in candidates}

    for _ in range(s.ITERATIONS):
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
        if c['move'] is not None and gws:
            inc = c['move'].get('safe_in') or c['move'].get('in') or {}
            inc_id = int(inc.get('player_id') or 0)
            xi, _ = cand_lineups[c['key']][gws[0]]
            incoming_starts = inc_id in set(xi)
        results.append({
            'route': c['label'],
            'action': 'ROLL' if c['move'] is None else 'TRANSFER',
            'hit_cost': hit,
            'expected_points_6gw': round(mean, 2),
            'p10_points_6gw': round(p10, 2),
            'p90_points_6gw': round(p90, 2),
            'expected_rank_after_horizon': round(exp_rank, 2),
            'prob_gain_league_place': round(route_gain_places[c['key']] / s.ITERATIONS, 3),
            'prob_finish_ahead_each_rival': [round(route_beat[c['key']][i] / s.ITERATIONS, 3) for i in range(len(rivals))],
            'utility_score': round(utility, 3),
            'incoming_starts_gw3': incoming_starts,
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
        'engine_version': 2,
        'iterations': s.ITERATIONS,
        'horizon_gws': gws,
        'shared_outcome_simulation': True,
        'remaining_free_transfers_current_deadline': remaining_ft,
        'next_transfer_hit_cost': next_hit_cost,
        'candidate_count': len(results),
        'rivals': rival_meta,
        'recommendation': winner,
        'routes': results,
        'method_note': 'Monte Carlo decision support from the reconstructed current squad. A further transfer at the current deadline is charged the live hit cost when the free transfer has already been used. Shared player outcomes are used across your team and rivals, with legal XI/captain optimisation each GW.',
    }
    s.OUT.parent.mkdir(parents=True, exist_ok=True)
    s.OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'winner': winner, 'iterations': s.ITERATIONS, 'remaining_ft': remaining_ft, 'next_hit_cost': next_hit_cost}))


if __name__ == '__main__':
    run()
