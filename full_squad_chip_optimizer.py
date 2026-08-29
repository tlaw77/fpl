import json
from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import path_simulation as p
import simulation_engine as s
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
BUDGET = Path('data/budget_state.json')
OUT = Path('data/full_squad_chip_optimizer.json')

POS_COUNTS = {'GKP': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
POS_ORDER = ['GKP', 'DEF', 'MID', 'FWD']
SHORTLIST_TOP = {'GKP': 16, 'DEF': 24, 'MID': 26, 'FWD': 20}
CHEAP_EXTRA = 8
BEAM_WIDTH = 4200
FINALISTS = 120


def pid(x):
    return int(x.get('player_id') or 0)


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def club(x):
    return x.get('team_id') or x.get('club')


def shortlist(pool_rows, pos, heuristic):
    rows = [x for x in pool_rows if x.get('position') == pos and n(x.get('adjusted_availability', x.get('availability')), 1) >= .55]
    ranked = sorted(rows, key=lambda x: heuristic.get(pid(x), 0), reverse=True)[:SHORTLIST_TOP[pos]]
    cheap = sorted(rows, key=lambda x: (n(x.get('price'), 99), -heuristic.get(pid(x), 0)))[:CHEAP_EXTRA]
    out, seen = [], set()
    for x in ranked + cheap:
        if pid(x) and pid(x) not in seen:
            seen.add(pid(x)); out.append(x)
    out.sort(key=lambda x: (-heuristic.get(pid(x), 0), n(x.get('price'), 99), pid(x)))
    return out


def min_remaining_cost(shortlists, slot_sequence, start_slot, last_idx):
    """Optimistic lower cost bound; never reject a feasible combination because of shortlist order."""
    needs = Counter(slot_sequence[start_slot:])
    total = 0.0
    for pos, need in needs.items():
        rows = shortlists[pos]
        start = last_idx.get(pos, -1) + 1
        prices = sorted(n(x.get('price'), 99) for x in rows[start:])
        if len(prices) < need:
            return 1e9
        total += sum(prices[:need])
    return total


def construct_squads(pool_rows, budget, heuristic, final_score):
    shortlists = {pos: shortlist(pool_rows, pos, heuristic) for pos in POS_ORDER}
    slots = [pos for pos in POS_ORDER for _ in range(POS_COUNTS[pos])]
    beam = [{
        'players': [], 'ids': set(), 'clubs': {}, 'cost': 0.0, 'heuristic': 0.0,
        'last_idx': {pos: -1 for pos in POS_ORDER},
    }]

    for si, pos in enumerate(slots):
        expanded = []
        rows = shortlists[pos]
        for state in beam:
            start = state['last_idx'][pos] + 1
            for idx in range(start, len(rows)):
                x = rows[idx]
                xpid = pid(x)
                if not xpid or xpid in state['ids']:
                    continue
                ck = club(x)
                if state['clubs'].get(ck, 0) >= 3:
                    continue
                cost = state['cost'] + n(x.get('price'))
                if cost > budget + 1e-9:
                    continue
                last_idx = dict(state['last_idx']); last_idx[pos] = idx
                if cost + min_remaining_cost(shortlists, slots, si + 1, last_idx) > budget + 1e-9:
                    continue
                clubs = dict(state['clubs']); clubs[ck] = clubs.get(ck, 0) + 1
                expanded.append({
                    'players': state['players'] + [x],
                    'ids': state['ids'] | {xpid},
                    'clubs': clubs,
                    'cost': cost,
                    'heuristic': state['heuristic'] + heuristic.get(xpid, 0),
                    'last_idx': last_idx,
                })
        expanded.sort(key=lambda z: z['heuristic'] + max(0, budget - z['cost']) * .035, reverse=True)
        beam = expanded[:BEAM_WIDTH]
        if not beam:
            return [], {'error': f'No feasible state after slot {si+1} ({pos})', 'shortlist_sizes': {k: len(v) for k,v in shortlists.items()}}

    finalists = sorted(beam, key=lambda z: final_score(z['players']), reverse=True)[:FINALISTS]
    return finalists, {'shortlist_sizes': {k: len(v) for k,v in shortlists.items()}, 'beam_width': BEAM_WIDTH}


def squad_summary(state, exp, gws, objective):
    squad = state['players']
    per_gw = []
    total = 0.0
    for gw in gws:
        score, xi, cap = p.lineup_expected(squad, gw, exp)
        total += score
        per_gw.append({
            'gw': gw,
            'expected_points_with_captain': round(score, 2),
            'xi_ids': xi,
            'captain_id': cap,
        })
    byid = {pid(x): x for x in squad}
    return {
        'objective': objective,
        'expected_objective_points': round(total, 2),
        'cost': round(state['cost'], 2),
        'bank_left': None,
        'squad': [
            {'player_id': pid(x), 'player': x.get('player'), 'club': x.get('club'), 'position': x.get('position'), 'price': x.get('price')}
            for x in squad
        ],
        'gameweeks': [
            {
                **row,
                'xi': [byid[i].get('player') for i in row['xi_ids'] if i in byid],
                'captain': byid.get(row['captain_id'], {}).get('player'),
            }
            for row in per_gw
        ],
    }


def run():
    latest = s.load_json(LATEST, {})
    pool = s.load_json(POOL, {})
    scout = s.load_json(SCOUT, {})
    market = s.load_json(MARKET, {})
    budget_state = s.load_json(BUDGET, {})
    if budget_state.get('status') != 'SUCCESS':
        raise RuntimeError('Budget state unavailable')

    scout_maps, market_maps = s.scout_lookup(scout), s.market_lookup(market)
    pool_rows = [x for x in (pool.get('players') or []) if pid(x) and n(x.get('price')) > 0]
    next_gw = int(latest.get('next_gw') or 1)
    current_gw = int(latest.get('current_gw') or max(0, next_gw - 1))
    maturity = season_maturity(current_gw)
    gws = list(range(next_gw, min(39, next_gw + 6)))
    budget = n(budget_state.get('spendable_budget'))

    model_vals = [n(x.get('six_gw_score')) for x in pool_rows]
    lo, hi = s.percentile(model_vals, .10), s.percentile(model_vals, .90)
    exp = {gw: {} for gw in gws}
    for gw in gws:
        for x in pool_rows:
            exp[gw][pid(x)] = calibrated_expected_gw(x, gw, lo, hi, scout_maps, market_maps, current_gw=current_gw)

    wildcard_heur = {pid(x): sum(exp[g][pid(x)][0] for g in gws) for x in pool_rows}
    def wc_final(squad):
        return sum(p.lineup_expected(squad, gw, exp)[0] for gw in gws)
    wc_states, wc_meta = construct_squads(pool_rows, budget, wildcard_heur, wc_final)
    best_wc = squad_summary(wc_states[0], exp, gws, 'Wildcard six-GW horizon') if wc_states else None
    if best_wc:
        best_wc['bank_left'] = round(budget - best_wc['cost'], 2)

    free_hits = []
    for gw in gws:
        fh_heur = {pid(x): exp[gw][pid(x)][0] for x in pool_rows}
        def fh_final(squad, target=gw):
            return p.lineup_expected(squad, target, exp)[0]
        fh_states, fh_meta = construct_squads(pool_rows, budget, fh_heur, fh_final)
        if not fh_states:
            continue
        row = squad_summary(fh_states[0], exp, [gw], f'Free Hit GW{gw}')
        row['gw'] = gw
        row['bank_left'] = round(budget - row['cost'], 2)
        row['search_meta'] = fh_meta
        free_hits.append(row)

    current_raw = latest.get('current_squad_next5') or latest.get('squad_next5') or []
    by_id, by_name = s.player_maps(pool)
    current = [s.enrich(x, by_id, by_name) for x in current_raw]
    current = [x for x in current if x]
    baseline = {gw: p.lineup_expected(current, gw, exp)[0] for gw in gws}
    wc_baseline = sum(baseline.values())
    if best_wc:
        best_wc['incremental_expected_points_vs_current_squad'] = round(best_wc['expected_objective_points'] - wc_baseline, 2)
    for fh in free_hits:
        fh['incremental_expected_points_vs_current_squad'] = round(fh['expected_objective_points'] - baseline.get(fh['gw'], 0), 2)

    best_fh = max(free_hits, key=lambda x: x['incremental_expected_points_vs_current_squad'], default=None)
    budget_conf = budget_state.get('budget_confidence') or 'unknown'
    budget_exact = budget_conf == 'exact'
    if budget_conf == 'exact':
        budget_note = 'Budget legality uses public FPL selling prices.'
    elif budget_conf == 'reconstructed':
        budget_note = 'Budget uses reconstructed selling prices from the purchase ledger and FPL selling-price rule. This is stronger than a market-value proxy but is not labelled exact because public picks omit selling prices.'
    else:
        budget_note = 'Budget uses current market value as a planning proxy because a stronger selling-price reconstruction is unavailable.'
    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 1,
        'projection_model': 'season-maturity calibrated',
        'season_maturity_weight': round(maturity, 3),
        'budget': budget,
        'budget_method': budget_state.get('budget_method'),
        'budget_confidence': budget_conf,
        'legality': {
            'positions': POS_COUNTS,
            'max_players_per_club': 3,
            'budget_constraint_enforced': True,
            'budget_exact': budget_exact,
            'note': 'Roster structure and club limits are exact. ' + budget_note,
        },
        'best_wildcard': best_wc,
        'best_free_hit': best_fh,
        'free_hit_windows': free_hits,
        'wildcard_search_meta': wc_meta,
        'method_note': 'Bounded full-squad search. Candidate shortlists retain high calibrated-value players plus cheap enablers. Beam construction enforces exact position quotas, no duplicate players, max three per club and the available budget. Finalists are re-scored using legal best XI and captain for the relevant horizon.',
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({
        'status': 'SUCCESS',
        'budget': budget,
        'budget_confidence': output['budget_confidence'],
        'wc_gain': (best_wc or {}).get('incremental_expected_points_vs_current_squad'),
        'best_fh_gw': (best_fh or {}).get('gw'),
        'best_fh_gain': (best_fh or {}).get('incremental_expected_points_vs_current_squad'),
    }))


if __name__ == '__main__':
    run()
