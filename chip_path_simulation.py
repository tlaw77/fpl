import json
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

from simulation_engine import (
    load_json, player_maps, enrich, scout_lookup, market_lookup, expected_gw,
    sample_points, percentile, rival_squads, n
)
from path_simulation import pid, expected_table, lineup_expected
from adaptive_rival_simulation import reconstruct_my_path, adaptive_rival_path, lineups_from_snapshots

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
PATHS = Path('data/path_simulation.json')
CHIPS = Path('data/chip_window.json')
OUT = Path('data/chip_path_simulation.json')

ITERATIONS = 1400
MAX_PATHS = 5


def chip_inventory(chip_data):
    portfolio = chip_data.get('portfolio') or {}
    return set(portfolio.get('remaining_chips') or [])


def bench_ids(squad, xi):
    xi_set = set(xi)
    return [pid(p) for p in squad if pid(p) and pid(p) not in xi_set]


def build_scenarios(my_paths, gws, remaining_chips):
    scenarios = []
    for pidx, path in enumerate(my_paths):
        scenarios.append({'path_index': pidx, 'chip': None, 'chip_gw': None})
        if 'Triple Captain' in remaining_chips:
            for gw in gws:
                scenarios.append({'path_index': pidx, 'chip': 'Triple Captain', 'chip_gw': gw})
        if 'Bench Boost' in remaining_chips:
            for gw in gws:
                scenarios.append({'path_index': pidx, 'chip': 'Bench Boost', 'chip_gw': gw})
    return scenarios


def run():
    latest = load_json(LATEST, {})
    pool = load_json(POOL, {})
    scout = load_json(SCOUT, {})
    market = load_json(MARKET, {})
    path_data = load_json(PATHS, {})
    chip_data = load_json(CHIPS, {})
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

    starting_bank = n((latest.get('me') or {}).get('bank'))
    path_rows = (path_data.get('paths') or [])[:MAX_PATHS]
    my_paths = []
    for row in path_rows:
        snaps = reconstruct_my_path(base_squad, row.get('actions') or [], gws, by_id, starting_bank)
        lineups = lineups_from_snapshots(snaps, gws, exp)
        benches = {gw: bench_ids(snaps.get(gw) or [], lineups[gw][0]) for gw in gws}
        my_paths.append({'source': row, 'snaps': snaps, 'lineups': lineups, 'benches': benches})

    rival_paths = []
    for r in rivals:
        policy = adaptive_rival_path(r, gws, pool_rows, exp)
        policy['lineups'] = lineups_from_snapshots(policy['squad_by_gw'], gws, exp)
        rival_paths.append(policy)

    universe = set()
    for p in my_paths:
        for sq in p['snaps'].values():
            universe.update(pid(x) for x in sq)
    for p in rival_paths:
        for sq in p['squad_by_gw'].values():
            universe.update(pid(x) for x in sq)
    universe.discard(0)

    scenarios = build_scenarios(my_paths, gws, chip_inventory(chip_data))
    rng = random.Random(str(latest.get('generated_at_utc')) + '|chip-path-v1')
    me_start = n((latest.get('me') or {}).get('total_points'))
    current_rank = int((latest.get('me') or {}).get('rank') or len(rivals) + 1)
    totals = [[] for _ in scenarios]
    ranks = [[] for _ in scenarios]
    beat = [[0 for _ in rivals] for _ in scenarios]

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

        for sidx, sc in enumerate(scenarios):
            p = my_paths[sc['path_index']]
            total = me_start - sum(n(a.get('hit')) for a in p['source'].get('actions') or [])
            for gw in gws:
                xi, cap = p['lineups'][gw]
                gw_points = sum(outcomes[gw].get(x, 0) for x in xi) + outcomes[gw].get(cap, 0)
                if sc['chip'] == 'Triple Captain' and sc['chip_gw'] == gw:
                    gw_points += outcomes[gw].get(cap, 0)
                elif sc['chip'] == 'Bench Boost' and sc['chip_gw'] == gw:
                    gw_points += sum(outcomes[gw].get(x, 0) for x in p['benches'][gw])
                total += gw_points
            totals[sidx].append(total - me_start)
            rank = 1 + sum(1 for x in rival_scores if x > total)
            ranks[sidx].append(rank)
            for i, rv in enumerate(rival_scores):
                if total > rv:
                    beat[sidx][i] += 1

    results = []
    no_chip_mean_by_path = {}
    for i, sc in enumerate(scenarios):
        if sc['chip'] is None:
            no_chip_mean_by_path[sc['path_index']] = statistics.fmean(totals[i]) if totals[i] else 0

    for i, sc in enumerate(scenarios):
        vals = totals[i]
        mean = statistics.fmean(vals) if vals else 0
        p10 = percentile(vals, .10)
        p90 = percentile(vals, .90)
        exp_rank = statistics.fmean(ranks[i]) if ranks[i] else current_rank
        chip_gain = mean - no_chip_mean_by_path.get(sc['path_index'], mean)
        utility = mean + (current_rank-exp_rank)*5.0 - max(0, mean-p10)*.12
        source = my_paths[sc['path_index']]['source']
        results.append({
            'actions': source.get('actions') or [],
            'chip': sc['chip'],
            'chip_gw': sc['chip_gw'],
            'expected_points': round(mean, 2),
            'chip_incremental_expected_points': round(chip_gain, 2),
            'p10_points': round(p10, 2),
            'p90_points': round(p90, 2),
            'expected_rank_after_path': round(exp_rank, 2),
            'prob_finish_ahead_each_rival': [round(x/ITERATIONS, 3) for x in beat[i]],
            'utility_score': round(utility, 3),
        })
    results.sort(key=lambda x: x['utility_score'], reverse=True)

    best_tc = max((x for x in results if x['chip'] == 'Triple Captain'), key=lambda x: x['chip_incremental_expected_points'], default=None)
    best_bb = max((x for x in results if x['chip'] == 'Bench Boost'), key=lambda x: x['chip_incremental_expected_points'], default=None)
    best_none = max((x for x in results if x['chip'] is None), key=lambda x: x['utility_score'], default=None)

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_version': 1,
        'iterations': ITERATIONS,
        'horizon_gws': gws,
        'exact_chip_branches': ['Triple Captain', 'Bench Boost'],
        'full_squad_chip_branches_pending': ['Wildcard', 'Free Hit'],
        'recommendation': results[0] if results else None,
        'best_no_chip_path': best_none,
        'best_triple_captain_window': best_tc,
        'best_bench_boost_window': best_bb,
        'scenarios': results[:30],
        'method_note': 'Triple Captain and Bench Boost are scored exactly on each shortlisted transfer path against adaptive rivals. Wildcard and Free Hit are intentionally excluded until the legal full-squad optimiser is available; they are not approximated as simple point multipliers.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'best': output['recommendation'], 'tc': best_tc, 'bb': best_bb}))


if __name__ == '__main__':
    run()
