import json
import random
import statistics
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import captaincy_model as cm
from simulation_engine import (
    load_json, player_maps, enrich, scout_lookup, market_lookup, expected_gw,
    best_xi, valid_club_limit, sample_points, percentile, rival_squads, n
)

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
CHIPS = Path('data/chip_window.json')
OUT = Path('data/path_simulation.json')

DEPTH = 4
BEAM_WIDTH = 14
INCOMING_PER_POSITION = 8
FINALISTS = 8
ITERATIONS = 1800
MAX_FT = 5


def pid(p):
    return int(p.get('player_id') or 0)


def price(p):
    return n(p.get('price'))


def expected_table(players, gws, model_lo, model_hi, scout_maps, market_maps):
    out = {}
    for gw in gws:
        out[gw] = {}
        for p in players:
            if pid(p):
                out[gw][pid(p)] = expected_gw(p, gw, model_lo, model_hi, scout_maps, market_maps)
    return out


def lineup_expected(squad, gw, exp):
    return cm.lineup_expected(__import__(__name__), squad, gw, exp)


def horizon_value(squad, remaining_gws, exp):
    return sum(lineup_expected(squad, gw, exp)[0] for gw in remaining_gws)


def replace_player(squad, out_p, in_p):
    out_id = pid(out_p)
    new = [p for p in squad if pid(p) != out_id]
    if len(new) != 14:
        return None
    new.append(in_p)
    if len({pid(p) for p in new}) != 15 or not valid_club_limit(new):
        return None
    return new


def transfer_candidates(state, remaining_gws, pool_rows, exp, limit=10):
    squad = state['squad']
    owned = {pid(p) for p in squad}
    bank = state['bank']
    ranked_by_pos = {}
    for pos in ('GKP', 'DEF', 'MID', 'FWD'):
        rows = [
            p for p in pool_rows
            if p.get('position') == pos
            and pid(p) not in owned
            and n(p.get('adjusted_availability', p.get('availability')), 1) >= .55
        ]
        rows.sort(
            key=lambda p: sum(exp.get(g, {}).get(pid(p), (0, 0))[0] for g in remaining_gws),
            reverse=True,
        )
        ranked_by_pos[pos] = rows[:INCOMING_PER_POSITION]

    base = horizon_value(squad, remaining_gws, exp)
    moves = []
    for out_p in squad:
        for in_p in ranked_by_pos.get(out_p.get('position'), []):
            if price(in_p) > price(out_p) + bank + 1e-9:
                continue
            new = replace_player(squad, out_p, in_p)
            if not new:
                continue
            val = horizon_value(new, remaining_gws, exp)
            uplift = val - base
            if uplift <= .15:
                continue
            moves.append({
                'out': out_p,
                'in': in_p,
                'squad': new,
                'bank': round(bank + price(out_p) - price(in_p), 2),
                'uplift': uplift,
                'label': f"{out_p.get('player')} → {in_p.get('player')}",
            })
    moves.sort(key=lambda x: x['uplift'], reverse=True)
    return moves[:limit]


def record_snapshot(state, gw):
    state['squad_by_gw'] = dict(state.get('squad_by_gw') or {})
    state['squad_by_gw'][int(gw)] = deepcopy(state['squad'])


def expand_state(state, gw, gws, pool_rows, exp):
    remaining = [x for x in gws if x >= gw]
    children = []

    roll = deepcopy(state)
    roll['actions'] = state['actions'] + [{'gw': gw, 'action': 'ROLL'}]
    roll['ft'] = min(MAX_FT, state['ft'] + 1)
    record_snapshot(roll, gw)
    gw_score, _, _ = lineup_expected(roll['squad'], gw, exp)
    roll['det_points'] = state['det_points'] + gw_score
    roll['search_score'] = roll['det_points'] + horizon_value(roll['squad'], remaining[1:], exp) + .45 * roll['ft']
    children.append(roll)

    for m in transfer_candidates(state, remaining, pool_rows, exp):
        child = deepcopy(state)
        child['squad'] = m['squad']
        child['bank'] = m['bank']
        hit = 0 if state['ft'] >= 1 else 4
        ft_after = max(0, state['ft'] - 1)
        child['ft'] = min(MAX_FT, ft_after + 1)
        child['actions'] = state['actions'] + [{
            'gw': gw,
            'action': 'TRANSFER',
            'route': m['label'],
            'hit': hit,
            'out_id': pid(m['out']),
            'in_id': pid(m['in']),
        }]
        record_snapshot(child, gw)
        gw_score, _, _ = lineup_expected(child['squad'], gw, exp)
        child['det_points'] = state['det_points'] + gw_score - hit
        child['search_score'] = child['det_points'] + horizon_value(child['squad'], remaining[1:], exp) + .45 * child['ft'] - hit
        children.append(child)
    return children


def beam_search(base_squad, bank, start_ft, gws, pool_rows, exp):
    beam = [{
        'squad': base_squad,
        'bank': bank,
        'ft': start_ft,
        'actions': [],
        'squad_by_gw': {},
        'det_points': 0.0,
        'search_score': 0.0,
    }]
    for gw in gws[:DEPTH]:
        expanded = []
        for state in beam:
            expanded.extend(expand_state(state, gw, gws[:DEPTH], pool_rows, exp))
        dedup = {}
        for s in expanded:
            squad_sig = tuple(sorted(pid(p) for p in s['squad']))
            key = (squad_sig, s['ft'], round(s['bank'], 1))
            if key not in dedup or s['search_score'] > dedup[key]['search_score']:
                dedup[key] = s
        beam = sorted(dedup.values(), key=lambda x: x['search_score'], reverse=True)[:BEAM_WIDTH]
    return sorted(beam, key=lambda x: x['search_score'], reverse=True)[:FINALISTS]


def rival_lineups(rivals, gws, exp):
    out = []
    for r in rivals:
        by_gw = {}
        for gw in gws[:DEPTH]:
            _, xi, cap = lineup_expected(r['squad'], gw, exp)
            by_gw[gw] = (xi, cap)
        out.append(by_gw)
    return out


def path_lineups(paths, gws, exp):
    out = []
    for state in paths:
        by_gw = {}
        for gw in gws[:DEPTH]:
            squad = (state.get('squad_by_gw') or {}).get(int(gw)) or state['squad']
            _, xi, cap = lineup_expected(squad, gw, exp)
            by_gw[gw] = (xi, cap)
        out.append(by_gw)
    return out


def simulate_paths(paths, rivals, gws, exp, latest):
    universe = set()
    for s in paths:
        for sq in (s.get('squad_by_gw') or {}).values():
            universe.update(pid(p) for p in sq)
    for r in rivals:
        universe.update(pid(p) for p in r['squad'])
    universe.discard(0)

    r_lineups = rival_lineups(rivals, gws, exp)
    p_lineups = path_lineups(paths, gws, exp)
    rng = random.Random(str(latest.get('generated_at_utc')) + '|path-sim-v2')
    me_start = n((latest.get('me') or {}).get('total_points'))
    current_rank = int((latest.get('me') or {}).get('rank') or len(rivals) + 1)
    totals = [[] for _ in paths]
    ranks = [[] for _ in paths]
    gain = [0 for _ in paths]
    beat = [[0 for _ in rivals] for _ in paths]

    for _ in range(ITERATIONS):
        outcomes = {}
        for gw in gws[:DEPTH]:
            outcomes[gw] = {p: sample_points(rng, *exp[gw].get(p, (0, .8))) for p in universe}

        rival_scores = []
        for i, r in enumerate(rivals):
            total = r['total_points']
            for gw in gws[:DEPTH]:
                xi, cap = r_lineups[i][gw]
                total += sum(outcomes[gw].get(x, 0) for x in xi) + outcomes[gw].get(cap, 0)
            rival_scores.append(total)

        for j, s in enumerate(paths):
            total = me_start
            hit_cost = sum(a.get('hit', 0) for a in s['actions'])
            for gw in gws[:DEPTH]:
                xi, cap = p_lineups[j][gw]
                total += sum(outcomes[gw].get(x, 0) for x in xi) + outcomes[gw].get(cap, 0)
            total -= hit_cost
            delta = total - me_start
            totals[j].append(delta)
            rank = 1 + sum(1 for x in rival_scores if x > total)
            ranks[j].append(rank)
            if rank < current_rank:
                gain[j] += 1
            for i, rv in enumerate(rival_scores):
                if total > rv:
                    beat[j][i] += 1

    results = []
    for j, s in enumerate(paths):
        vals = totals[j]
        mean = statistics.fmean(vals) if vals else 0
        p10 = percentile(vals, .10)
        p90 = percentile(vals, .90)
        exp_rank = statistics.fmean(ranks[j]) if ranks[j] else current_rank
        utility = mean + (current_rank - exp_rank) * 5.0 - max(0, mean - p10) * .12 + .35 * s['ft']
        first_gw = gws[0] if gws else None
        first_snapshot = (s.get('squad_by_gw') or {}).get(first_gw, []) if first_gw else []
        first_action = s['actions'][0] if s['actions'] else None
        incoming_starts = None
        if first_action and first_action.get('action') == 'TRANSFER' and first_gw:
            _, xi, _ = lineup_expected(first_snapshot, first_gw, exp)
            incoming_starts = int(first_action.get('in_id') or 0) in set(xi)
        results.append({
            'actions': s['actions'],
            'expected_points': round(mean, 2),
            'p10_points': round(p10, 2),
            'p90_points': round(p90, 2),
            'expected_rank_after_path': round(exp_rank, 2),
            'prob_gain_league_place': round(gain[j] / ITERATIONS, 3),
            'prob_finish_ahead_each_rival': [round(x / ITERATIONS, 3) for x in beat[j]],
            'ending_bank': s['bank'],
            'ending_free_transfers': s['ft'],
            'first_transfer_incoming_starts': incoming_starts,
            'utility_score': round(utility, 3),
        })
    results.sort(key=lambda x: x['utility_score'], reverse=True)
    return results


def run():
    latest = load_json(LATEST, {})
    pool = load_json(POOL, {})
    scout = load_json(SCOUT, {})
    market = load_json(MARKET, {})
    chip = load_json(CHIPS, {})
    by_id, by_name = player_maps(pool)
    scout_maps, market_maps = scout_lookup(scout), market_lookup(market)

    raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    base_squad = [enrich(p, by_id, by_name) for p in raw]
    base_squad = [p for p in base_squad if p]
    rivals = rival_squads(latest, by_id, by_name)
    next_gw = int(latest.get('next_gw') or 1)
    gws = list(range(next_gw, min(39, next_gw + DEPTH)))

    pool_rows = [p for p in pool.get('players') or [] if pid(p)]
    model_vals = [n(p.get('six_gw_score')) for p in pool_rows]
    lo, hi = percentile(model_vals, .10), percentile(model_vals, .90)
    exp = expected_table(pool_rows, gws, lo, hi, scout_maps, market_maps)

    start_ft = int((latest.get('me') or {}).get('free_transfers_next_gw') or 1)
    start_ft = max(1, min(MAX_FT, start_ft))
    bank = n((latest.get('me') or {}).get('bank'))

    finalists = beam_search(base_squad, bank, start_ft, gws, pool_rows, exp)
    results = simulate_paths(finalists, rivals, gws, exp, latest)
    rival_meta = [{k: r.get(k) for k in ('entry_id', 'team_name', 'manager', 'rank', 'total_points')} for r in rivals]
    portfolio = chip.get('portfolio') or chip.get('summary') or {}

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_version': 3,
        'planner': 'bounded beam search + GW-specific shared-outcome Monte Carlo + shared captaincy model',
        'depth_gameweeks': gws[:DEPTH],
        'beam_width': BEAM_WIDTH,
        'iterations': ITERATIONS,
        'starting_free_transfers': start_ft,
        'max_free_transfers': MAX_FT,
        'transfer_hit_cost': 4,
        'chip_portfolio_context': portfolio,
        'rivals': rival_meta,
        'recommendation': results[0] if results else None,
        'paths': results,
        'method_note': 'Each path is scored with the actual squad owned in each Gameweek after that deadline action. Legal XI selection is followed by the shared captaincy model used by Pick Team. Final-squad leakage into earlier Gameweeks is prevented.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'best': output['recommendation'], 'paths': len(results)}))


if __name__ == '__main__':
    run()
