import json
import math
import random
import statistics
from copy import deepcopy
from datetime import datetime, timezone

import current_squad as cs
import path_simulation as p
import simulation_budget as sb
import simulation_engine as s
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity

OUT = s.Path('data/adaptive_rival_simulation.json') if hasattr(s, 'Path') else None
if OUT is None:
    from pathlib import Path
    OUT = Path('data/adaptive_rival_simulation.json')

MAX_PATHS = 8
POLICY_VARIANTS = 14
MOVE_THRESHOLD = 0.45


def action_key(actions):
    return tuple((a.get('gw'), a.get('action'), a.get('route')) for a in actions)


def lineup_snapshots(squad_by_gw, gws, exp):
    out = {}
    for gw in gws:
        _, xi, cap = p.lineup_expected(squad_by_gw.get(gw) or [], gw, exp)
        out[gw] = (xi, cap)
    return out


def reconstruct_my_path(base_squad, actions, gws, by_id, starting_bank):
    squad = deepcopy(base_squad)
    bank = starting_bank
    snapshots = {}
    for gw in gws:
        action = next((a for a in actions if int(a.get('gw') or -1) == gw), {'action': 'ROLL'})
        if action.get('action') == 'TRANSFER':
            out_id = int(action.get('out_id') or 0)
            in_id = int(action.get('in_id') or 0)
            out_p = next((x for x in squad if p.pid(x) == out_id), None)
            in_p = by_id.get(in_id)
            if out_p and in_p:
                new = p.replace_player(squad, out_p, in_p)
                if new:
                    bank = round(bank + p.price(out_p) - p.price(in_p), 2)
                    squad = new
        snapshots[gw] = deepcopy(squad)
    return snapshots


def transfer_history(entry_id):
    try:
        return cs.get_json(f'{cs.BASE}/entry/{int(entry_id)}/transfers/') or []
    except Exception:
        return []


def rival_behaviour(rival, current_gw):
    rows = [x for x in transfer_history(rival.get('entry_id')) if int(x.get('event') or 0) <= current_gw]
    events = sorted({int(x.get('event') or 0) for x in rows if int(x.get('event') or 0) > 0})
    active_events = len(events)
    counts = {}
    for x in rows:
        ev = int(x.get('event') or 0)
        counts[ev] = counts.get(ev, 0) + 1
    hits = sum(max(0, c - 1) for c in counts.values())
    alpha, beta = 2.2, 2.2
    action_prob = (alpha + active_events) / (alpha + beta + max(1, current_gw))
    action_prob = max(.32, min(.78, action_prob))
    hit_prob = max(.02, min(.20, (0.3 + hits) / (3.0 + max(1, current_gw))))
    return {
        'observed_transfer_events': active_events,
        'observed_transfers': len(rows),
        'action_probability': round(action_prob, 3),
        'hit_probability': round(hit_prob, 3),
    }


def choose_move(rng, moves):
    plausible = [m for m in moves[:4] if float(m.get('uplift') or 0) >= MOVE_THRESHOLD]
    if not plausible:
        return None
    weights = [math.exp(min(2.2, max(0.0, float(m.get('uplift') or 0)) * .18)) for m in plausible]
    total = sum(weights)
    r = rng.random() * total
    acc = 0.0
    for move, w in zip(plausible, weights):
        acc += w
        if r <= acc:
            return move
    return plausible[0]


def make_policy_variant(rival, behaviour, gws, pool_rows, exp, seed):
    rng = random.Random(seed)
    state = {'squad': deepcopy(rival['squad']), 'bank': 0.0}
    snapshots, actions = {}, []
    for i, gw in enumerate(gws):
        remaining = gws[i:]
        should_act = rng.random() < behaviour['action_probability']
        move = None
        if should_act:
            moves = p.transfer_candidates(state, remaining, pool_rows, exp, limit=5)
            move = choose_move(rng, moves)
        if move:
            state['squad'] = move['squad']
            state['bank'] = move['bank']
            actions.append({'gw': gw, 'action': 'TRANSFER', 'route': move['label'], 'uplift': round(move['uplift'], 2)})
        else:
            actions.append({'gw': gw, 'action': 'ROLL'})
        snapshots[gw] = deepcopy(state['squad'])
    return {'squad_by_gw': snapshots, 'actions': actions, 'lineups': lineup_snapshots(snapshots, gws, exp)}


def run():
    latest = s.load_json(s.LATEST, {})
    pool = s.load_json(s.POOL, {})
    scout = s.load_json(s.SCOUT, {})
    market = s.load_json(s.MARKET, {})
    path_data = s.load_json(p.OUT, {})
    if path_data.get('status') != 'SUCCESS':
        raise RuntimeError('Path simulation is not ready')
    iterations = sb.iterations(latest, 'adaptive')
    iteration_policy = sb.metadata(latest, 'adaptive')

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

    candidate_rows = (path_data.get('paths') or [])[:MAX_PATHS]
    starting_bank = s.n(latest.get('current_bank', (latest.get('me') or {}).get('bank')))
    my_paths = []
    for row in candidate_rows:
        snaps = reconstruct_my_path(base_squad, row.get('actions') or [], gws, by_id, starting_bank)
        my_paths.append({'source': row, 'squad_by_gw': snaps, 'lineups': lineup_snapshots(snaps, gws, exp)})

    behaviour_rows = []
    rival_variants = []
    base_seed = str(latest.get('generated_at_utc') or '')
    for r in rivals:
        behaviour = rival_behaviour(r, current_gw)
        behaviour_rows.append({'entry_id': r.get('entry_id'), 'team_name': r.get('team_name'), 'rank': r.get('rank'), **behaviour})
        variants = [make_policy_variant(r, behaviour, gws, pool_rows, exp, f'{base_seed}|{r.get("entry_id")}|{k}') for k in range(POLICY_VARIANTS)]
        rival_variants.append(variants)

    universe = set()
    for mp in my_paths:
        for sq in mp['squad_by_gw'].values():
            universe.update(p.pid(x) for x in sq)
    for variants in rival_variants:
        for variant in variants:
            for sq in variant['squad_by_gw'].values():
                universe.update(p.pid(x) for x in sq)
    universe.discard(0)

    rng = random.Random(base_seed + '|adaptive-rivals-v3-deadline-budget')
    me_start = s.n((latest.get('me') or {}).get('total_points'))
    current_rank = int((latest.get('me') or {}).get('rank') or len(rivals) + 1)
    totals = [[] for _ in my_paths]
    ranks = [[] for _ in my_paths]
    gain = [0 for _ in my_paths]
    beat = [[0 for _ in rivals] for _ in my_paths]

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

        for j, mp in enumerate(my_paths):
            total = me_start - sum(s.n(a.get('hit')) for a in mp['source'].get('actions') or [])
            for gw in gws:
                xi, cap = mp['lineups'][gw]
                total += sum(outcomes[gw].get(x, 0) for x in xi) + outcomes[gw].get(cap, 0)
            totals[j].append(total - me_start)
            rank = 1 + sum(1 for x in rival_scores if x > total)
            ranks[j].append(rank)
            if rank < current_rank:
                gain[j] += 1
            for i, rv in enumerate(rival_scores):
                if total > rv:
                    beat[j][i] += 1

    static_map = {action_key(x.get('actions') or []): x for x in path_data.get('paths') or []}
    results = []
    for j, mp in enumerate(my_paths):
        vals = totals[j]
        mean = statistics.fmean(vals) if vals else 0
        p10, p90 = s.percentile(vals, .10), s.percentile(vals, .90)
        exp_rank = statistics.fmean(ranks[j]) if ranks[j] else current_rank
        static = static_map.get(action_key(mp['source'].get('actions') or []), {})
        utility = mean + (current_rank - exp_rank) * 5.0 - max(0, mean - p10) * .12
        results.append({
            'actions': mp['source'].get('actions') or [],
            'expected_points': round(mean, 2),
            'p10_points': round(p10, 2),
            'p90_points': round(p90, 2),
            'expected_rank_after_path': round(exp_rank, 2),
            'prob_gain_league_place': round(gain[j] / iterations, 3),
            'prob_finish_ahead_each_rival': [round(x / iterations, 3) for x in beat[j]],
            'static_rival_expected_rank': static.get('expected_rank_after_path'),
            'probabilistic_rival_rank_penalty': round(exp_rank - s.n(static.get('expected_rank_after_path'), exp_rank), 2),
            'utility_score': round(utility, 3),
        })
    results.sort(key=lambda x: x['utility_score'], reverse=True)

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_version': 3,
        'iterations': iterations,
        'iteration_policy': iteration_policy,
        'horizon_gws': gws,
        'projection_model': 'season-maturity calibrated + shared captaincy model',
        'season_maturity_weight': round(maturity, 3),
        'rival_policy': 'probabilistic bounded transfer behaviour learned from observed FPL transfer history; no hidden bank; no assumed hits',
        'policy_variants_per_rival': POLICY_VARIANTS,
        'rival_behaviour': behaviour_rows,
        'recommendation': results[0] if results else None,
        'paths': results,
        'method_note': 'Challenger model. Rivals are not assumed to optimise perfectly every deadline. Each rival receives multiple plausible roll/transfer paths, with action probability shrunk toward a population prior using observed transfer history. Candidate moves remain rational but noisy. Sampling precision increases as the official FPL deadline approaches.',
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'best': output['recommendation'], 'paths': len(results), 'maturity': round(maturity, 3), 'iterations': iterations, 'deadline_phase': iteration_policy['deadline_phase']}))


if __name__ == '__main__':
    run()
