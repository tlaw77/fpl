import json
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

import adaptive_rival_simulation_v2 as ar
import path_simulation as p
import simulation_budget as sb
import simulation_engine as s
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
PATHS = Path('data/path_simulation.json')
CHIPS = Path('data/chip_window.json')
OUT = Path('data/chip_path_simulation.json')

MAX_PATHS = 5
POLICY_VARIANTS = 14


def chip_inventory(chip_data):
    portfolio = chip_data.get('portfolio') or {}
    return set(portfolio.get('remaining_chips') or [])


def bench_ids(squad, xi):
    xi_set = set(xi)
    return [p.pid(x) for x in squad if p.pid(x) and p.pid(x) not in xi_set]


def build_scenarios(my_paths, gws, remaining_chips):
    scenarios = []
    for pidx, _ in enumerate(my_paths):
        scenarios.append({'path_index': pidx, 'chip': None, 'chip_gw': None})
        if 'Triple Captain' in remaining_chips:
            scenarios.extend({'path_index': pidx, 'chip': 'Triple Captain', 'chip_gw': gw} for gw in gws)
        if 'Bench Boost' in remaining_chips:
            scenarios.extend({'path_index': pidx, 'chip': 'Bench Boost', 'chip_gw': gw} for gw in gws)
    return scenarios


def run():
    latest = s.load_json(LATEST, {})
    pool = s.load_json(POOL, {})
    scout = s.load_json(SCOUT, {})
    market = s.load_json(MARKET, {})
    path_data = s.load_json(PATHS, {})
    chip_data = s.load_json(CHIPS, {})
    if path_data.get('status') != 'SUCCESS':
        raise RuntimeError('Path simulation is not ready')
    iterations = sb.iterations(latest, 'chip')
    iteration_policy = sb.metadata(latest, 'chip')

    by_id, by_name = s.player_maps(pool)
    scout_maps, market_maps = s.scout_lookup(scout), s.market_lookup(market)
    raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    base_squad = [s.enrich(x, by_id, by_name) for x in raw]
    base_squad = [x for x in base_squad if x]
    rivals = s.rival_squads(latest, by_id, by_name)
    gws = [int(x) for x in (path_data.get('depth_gameweeks') or [])]
    current_gw = int(latest.get('current_gw') or max(0, (gws[0] if gws else 1) - 1))
    maturity = season_maturity(current_gw)

    pool_rows = [x for x in pool.get('players') or [] if p.pid(x)]
    model_vals = [s.n(x.get('six_gw_score')) for x in pool_rows]
    lo, hi = s.percentile(model_vals, .10), s.percentile(model_vals, .90)
    p.expected_gw = lambda player, gw, model_lo, model_hi, sm, mm: calibrated_expected_gw(
        player, gw, model_lo, model_hi, sm, mm, current_gw=current_gw
    )
    exp = p.expected_table(pool_rows, gws, lo, hi, scout_maps, market_maps)

    starting_bank = s.n(latest.get('current_bank', (latest.get('me') or {}).get('bank')))
    path_rows = (path_data.get('paths') or [])[:MAX_PATHS]
    my_paths = []
    for row in path_rows:
        snaps = ar.reconstruct_my_path(base_squad, row.get('actions') or [], gws, by_id, starting_bank)
        lineups = ar.lineup_snapshots(snaps, gws, exp)
        benches = {gw: bench_ids(snaps.get(gw) or [], lineups[gw][0]) for gw in gws}
        my_paths.append({'source': row, 'snaps': snaps, 'lineups': lineups, 'benches': benches})

    behaviour_rows = []
    rival_variants = []
    base_seed = str(latest.get('generated_at_utc') or '')
    for r in rivals:
        behaviour = ar.rival_behaviour(r, current_gw)
        behaviour_rows.append({'entry_id': r.get('entry_id'), 'team_name': r.get('team_name'), **behaviour})
        variants = [ar.make_policy_variant(r, behaviour, gws, pool_rows, exp, f'{base_seed}|chip|{r.get("entry_id")}|{k}') for k in range(POLICY_VARIANTS)]
        rival_variants.append(variants)

    universe = set()
    for mp in my_paths:
        for sq in mp['snaps'].values():
            universe.update(p.pid(x) for x in sq)
    for variants in rival_variants:
        for variant in variants:
            for sq in variant['squad_by_gw'].values():
                universe.update(p.pid(x) for x in sq)
    universe.discard(0)

    scenarios = build_scenarios(my_paths, gws, chip_inventory(chip_data))
    rng = random.Random(base_seed + '|chip-path-v3-deadline-budget')
    me_start = s.n((latest.get('me') or {}).get('total_points'))
    current_rank = int((latest.get('me') or {}).get('rank') or len(rivals) + 1)
    totals = [[] for _ in scenarios]
    ranks = [[] for _ in scenarios]
    beat = [[0 for _ in rivals] for _ in scenarios]

    for _ in range(iterations):
        outcomes = {gw: {pid: s.sample_points(rng, *exp[gw].get(pid, (0, .85))) for pid in universe} for gw in gws}
        rival_scores = []
        for i, r in enumerate(rivals):
            variant = rival_variants[i][rng.randrange(len(rival_variants[i]))]
            total = r['total_points']
            for gw in gws:
                xi, cap = variant['lineups'][gw]
                total += sum(outcomes[gw].get(x, 0) for x in xi) + outcomes[gw].get(cap, 0)
            rival_scores.append(total)

        for sidx, scenario in enumerate(scenarios):
            mp = my_paths[scenario['path_index']]
            total = me_start - sum(s.n(a.get('hit')) for a in mp['source'].get('actions') or [])
            for gw in gws:
                xi, cap = mp['lineups'][gw]
                gw_points = sum(outcomes[gw].get(x, 0) for x in xi) + outcomes[gw].get(cap, 0)
                if scenario['chip'] == 'Triple Captain' and scenario['chip_gw'] == gw:
                    gw_points += outcomes[gw].get(cap, 0)
                elif scenario['chip'] == 'Bench Boost' and scenario['chip_gw'] == gw:
                    gw_points += sum(outcomes[gw].get(x, 0) for x in mp['benches'][gw])
                total += gw_points
            totals[sidx].append(total - me_start)
            rank = 1 + sum(1 for x in rival_scores if x > total)
            ranks[sidx].append(rank)
            for i, rv in enumerate(rival_scores):
                if total > rv:
                    beat[sidx][i] += 1

    no_chip_mean_by_path = {}
    for i, scenario in enumerate(scenarios):
        if scenario['chip'] is None:
            no_chip_mean_by_path[scenario['path_index']] = statistics.fmean(totals[i]) if totals[i] else 0

    results = []
    for i, scenario in enumerate(scenarios):
        vals = totals[i]
        mean = statistics.fmean(vals) if vals else 0
        p10, p90 = s.percentile(vals, .10), s.percentile(vals, .90)
        exp_rank = statistics.fmean(ranks[i]) if ranks[i] else current_rank
        chip_gain = mean - no_chip_mean_by_path.get(scenario['path_index'], mean)
        utility = mean + (current_rank - exp_rank) * 5.0 - max(0, mean - p10) * .12
        source = my_paths[scenario['path_index']]['source']
        results.append({
            'actions': source.get('actions') or [],
            'chip': scenario['chip'],
            'chip_gw': scenario['chip_gw'],
            'expected_points': round(mean, 2),
            'chip_incremental_expected_points': round(chip_gain, 2),
            'p10_points': round(p10, 2),
            'p90_points': round(p90, 2),
            'expected_rank_after_path': round(exp_rank, 2),
            'prob_finish_ahead_each_rival': [round(x / iterations, 3) for x in beat[i]],
            'utility_score': round(utility, 3),
        })
    results.sort(key=lambda x: x['utility_score'], reverse=True)

    best_tc = max((x for x in results if x['chip'] == 'Triple Captain'), key=lambda x: x['chip_incremental_expected_points'], default=None)
    best_bb = max((x for x in results if x['chip'] == 'Bench Boost'), key=lambda x: x['chip_incremental_expected_points'], default=None)
    best_none = max((x for x in results if x['chip'] is None), key=lambda x: x['utility_score'], default=None)

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_version': 3,
        'iterations': iterations,
        'iteration_policy': iteration_policy,
        'horizon_gws': gws,
        'projection_model': 'season-maturity calibrated + shared captaincy model',
        'season_maturity_weight': round(maturity, 3),
        'rival_policy': 'probabilistic observed-behaviour challenger',
        'exact_chip_branches': ['Triple Captain', 'Bench Boost'],
        'full_squad_chip_branches': ['Wildcard', 'Free Hit'],
        'recommendation': results[0] if results else None,
        'best_no_chip_path': best_none,
        'best_triple_captain_window': best_tc,
        'best_bench_boost_window': best_bb,
        'rival_behaviour': behaviour_rows,
        'scenarios': results[:30],
        'method_note': 'Triple Captain and Bench Boost are scored exactly on calibrated transfer paths against probabilistic rival behaviour. Values are opportunity windows, not automatic play recommendations. Sampling precision increases as the official FPL deadline approaches. Wildcard and Free Hit are handled by the separate legal full-squad optimiser and activation gate.',
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'best': output['recommendation'], 'tc': best_tc, 'bb': best_bb, 'maturity': round(maturity, 3), 'iterations': iterations, 'deadline_phase': iteration_policy['deadline_phase']}))


if __name__ == '__main__':
    run()
