import json
import random
import statistics
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from simulation_engine import (
    load_json, player_maps, enrich, scout_lookup, market_lookup, expected_gw,
    sample_points, percentile, rival_squads, n
)
from path_simulation import (
    pid, price, expected_table, lineup_expected, replace_player, transfer_candidates
)

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
PATHS = Path('data/path_simulation.json')
OUT = Path('data/adaptive_rival_simulation.json')

ITERATIONS = 1600
RIVAL_MOVE_THRESHOLD = 0.55
MAX_PATHS = 8


def reconstruct_my_path(base_squad, actions, gws, by_id, starting_bank):
    squad = deepcopy(base_squad)
    bank = starting_bank
    by_gw = {}
    for gw in gws:
        action = next((a for a in actions if int(a.get('gw') or -1) == gw), {'action': 'ROLL'})
        if action.get('action') == 'TRANSFER':
            out_id = int(action.get('out_id') or 0)
            in_id = int(action.get('in_id') or 0)
            out_p = next((p for p in squad if pid(p) == out_id), None)
            in_p = by_id.get(in_id)
            if out_p and in_p:
                new = replace_player(squad, out_p, in_p)
                if new:
                    bank = round(bank + price(out_p) - price(in_p), 2)
                    squad = new
        by_gw[gw] = deepcopy(squad)
    return by_gw


def adaptive_rival_path(rival, gws, pool_rows, exp):
    state = {'squad': deepcopy(rival['squad']), 'bank': 0.0}
    by_gw = {}
    actions = []
    for i, gw in enumerate(gws):
        remaining = gws[i:]
        moves = transfer_candidates(state, remaining, pool_rows, exp, limit=4)
        best = moves[0] if moves else None
        if best and best.get('uplift', 0) >= RIVAL_MOVE_THRESHOLD:
            state['squad'] = best['squad']
            state['bank'] = best['bank']
            actions.append({'gw': gw, 'action': 'TRANSFER', 'route': best['label'], 'uplift': round(best['uplift'], 2)})
        else:
            actions.append({'gw': gw, 'action': 'ROLL'})
        by_gw[gw] = deepcopy(state['squad'])
    return {'squad_by_gw': by_gw, 'actions': actions, 'ending_bank': state['bank']}


def lineups_from_snapshots(squad_by_gw, gws, exp):
    out = {}
    for gw in gws:
        squad = squad_by_gw.get(gw) or []
        _, xi, cap = lineup_expected(squad, gw, exp)
        out[gw] = (xi, cap)
    return out


def action_key(actions):
    return tuple((a.get('gw'), a.get('action'), a.get('route')) for a in actions)


def run():
    latest = load_json(LATEST, {})
    pool = load_json(POOL, {})
    scout = load_json(SCOUT, {})
    market = load_json(MARKET, {})
    path_data = load_json(PATHS, {})
    if path_data.get('status') != 'SUCCESS':
        raise RuntimeError('Path simulation is not ready')

    by_id, by_name = player_maps(pool)
    scout_maps, market_maps = scout_lookup(scout), market_lookup(market)
    raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    base_squad = [enrich(p, by_id, by_name) for p in raw]
    base_squad = [p for p in base_squad if p]
    rivals = rival_squads(latest, by_id, by_name)
    gws = [int(x) for x in (path_data.get('depth_gameweeks') or [])]
    pool_rows = [p for p in pool.get('players') or [] if pid(p)]
    model_vals = [n(p.get('six_gw_score')) for p in pool_rows]
    lo, hi = percentile(model_vals, .10), percentile(model_vals, .90)
    exp = expected_table(pool_rows, gws, lo, hi, scout_maps, market_maps)

    candidate_rows = (path_data.get('paths') or [])[:MAX_PATHS]
    starting_bank = n((latest.get('me') or {}).get('bank'))
    my_paths = []
    for row in candidate_rows:
        snaps = reconstruct_my_path(base_squad, row.get('actions') or [], gws, by_id, starting_bank)
        my_paths.append({'source': row, 'squad_by_gw': snaps, 'lineups': lineups_from_snapshots(snaps, gws, exp)})

    rival_paths = []
    for r in rivals:
        policy = adaptive_rival_path(r, gws, pool_rows, exp)
        policy['lineups'] = lineups_from_snapshots(policy['squad_by_gw'], gws, exp)
        rival_paths.append(policy)

    universe = set()
    for p in my_paths:
        for sq in p['squad_by_gw'].values():
            universe.update(pid(x) for x in sq)
    for p in rival_paths:
        for sq in p['squad_by_gw'].values():
            universe.update(pid(x) for x in sq)
    universe.discard(0)

    rng = random.Random(str(latest.get('generated_at_utc')) + '|adaptive-rivals-v1')
    me_start = n((latest.get('me') or {}).get('total_points'))
    current_rank = int((latest.get('me') or {}).get('rank') or len(rivals) + 1)
    totals = [[] for _ in my_paths]
    ranks = [[] for _ in my_paths]
    gain = [0 for _ in my_paths]
    beat = [[0 for _ in rivals] for _ in my_paths]

    for _ in range(ITERATIONS):
        outcomes = {
            gw: {p: sample_points(rng, *exp[gw].get(p, (0, .8))) for p in universe}
            for gw in gws
        }
        rival_scores = []
        for i, r in enumerate(rivals):
            total = r['total_points']
            for gw in gws:
                xi, cap = rival_paths[i]['lineups'][gw]
                total += sum(outcomes[gw].get(x, 0) for x in xi) + outcomes[gw].get(cap, 0)
            rival_scores.append(total)

        for j, p in enumerate(my_paths):
            total = me_start - sum(n(a.get('hit')) for a in p['source'].get('actions') or [])
            for gw in gws:
                xi, cap = p['lineups'][gw]
                total += sum(outcomes[gw].get(x, 0) for x in xi) + outcomes[gw].get(cap, 0)
            vals = total - me_start
            totals[j].append(vals)
            rank = 1 + sum(1 for x in rival_scores if x > total)
            ranks[j].append(rank)
            if rank < current_rank:
                gain[j] += 1
            for i, rv in enumerate(rival_scores):
                if total > rv:
                    beat[j][i] += 1

    results = []
    static_map = {action_key(x.get('actions') or []): x for x in path_data.get('paths') or []}
    for j, p in enumerate(my_paths):
        vals = totals[j]
        mean = statistics.fmean(vals) if vals else 0
        p10 = percentile(vals, .10)
        p90 = percentile(vals, .90)
        exp_rank = statistics.fmean(ranks[j]) if ranks[j] else current_rank
        static = static_map.get(action_key(p['source'].get('actions') or []), {})
        utility = mean + (current_rank-exp_rank)*5.0 - max(0, mean-p10)*.12
        results.append({
            'actions': p['source'].get('actions') or [],
            'expected_points': round(mean, 2),
            'p10_points': round(p10, 2),
            'p90_points': round(p90, 2),
            'expected_rank_after_path': round(exp_rank, 2),
            'prob_gain_league_place': round(gain[j]/ITERATIONS, 3),
            'prob_finish_ahead_each_rival': [round(x/ITERATIONS, 3) for x in beat[j]],
            'static_rival_expected_rank': static.get('expected_rank_after_path'),
            'adaptive_rival_rank_penalty': round(exp_rank - n(static.get('expected_rank_after_path'), exp_rank), 2),
            'utility_score': round(utility, 3),
        })
    results.sort(key=lambda x: x['utility_score'], reverse=True)

    rival_policy_summary = []
    for i, r in enumerate(rivals):
        rival_policy_summary.append({
            'entry_id': r.get('entry_id'),
            'team_name': r.get('team_name'),
            'rank': r.get('rank'),
            'actions': rival_paths[i]['actions'],
        })

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_version': 1,
        'iterations': ITERATIONS,
        'horizon_gws': gws,
        'rival_policy': 'bounded rational one-transfer-per-GW; zero hidden bank assumed; no hits',
        'rival_move_threshold': RIVAL_MOVE_THRESHOLD,
        'recommendation': results[0] if results else None,
        'paths': results,
        'rival_policy_paths': rival_policy_summary,
        'method_note': 'Challenger model only. Re-scores the path-simulation finalists against rivals who are allowed a conservative rational transfer each Gameweek. No hidden rival bank is assumed, so rival upgrade ability is deliberately bounded. This output should calibrate, not silently replace, the primary recommendation until it is stable across refreshes.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'best': output['recommendation'], 'paths': len(results)}))


if __name__ == '__main__':
    run()
