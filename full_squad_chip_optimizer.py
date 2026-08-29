import json
import math
from datetime import datetime, timezone
from pathlib import Path

import path_simulation as p
import simulation_engine as s
from projection_calibration import maturity_weight

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
BUDGET = Path('data/budget_state.json')
OUT = Path('data/full_squad_chip_optimizer.json')

POS_COUNTS = {'GKP': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
SHORTLIST_TOP = {'GKP': 16, 'DEF': 28, 'MID': 32, 'FWD': 24}
CHEAP_EXTRA = 8
BEAM_WIDTH = 6000
FINALISTS = 80


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def pid(x):
    return int(x.get('player_id') or 0)


def cost_tenths(x):
    return int(round(n(x.get('price')) * 10))


def shortlist(pool_rows, heur):
    out = []
    for pos, count in SHORTLIST_TOP.items():
        rows = [x for x in pool_rows if x.get('position') == pos and n(x.get('adjusted_availability', x.get('availability')), 1) >= .45]
        rows.sort(key=lambda x: heur.get(pid(x), -999), reverse=True)
        chosen = rows[:count]
        cheap = sorted(rows, key=lambda x: (n(x.get('price'), 99), -heur.get(pid(x), -999)))[:CHEAP_EXTRA]
        seen = set()
        merged = []
        for x in chosen + cheap:
            if pid(x) and pid(x) not in seen:
                seen.add(pid(x))
                merged.append(x)
        out.extend(merged)
    return out


def legal_partial(state, row):
    club = row.get('club')
    if club and state['clubs'].get(club, 0) >= 3:
        return False
    pos = row.get('position')
    if state['pos'].get(pos, 0) >= POS_COUNTS.get(pos, 0):
        return False
    return True


def min_remaining_cost(cands, picked_ids, pos_counts):
    need = {k: POS_COUNTS[k] - pos_counts.get(k, 0) for k in POS_COUNTS}
    total = 0
    for pos, cnt in need.items():
        if cnt <= 0:
            continue
        eligible = sorted(cost_tenths(x) for x in cands if x.get('position') == pos and pid(x) not in picked_ids)
        if len(eligible) < cnt:
            return 10**9
        total += sum(eligible[:cnt])
    return total


def construct_squads(pool_rows, budget, heur, final_score):
    cands = shortlist(pool_rows, heur)
    budget_t = int(round(budget * 10))
    cands.sort(key=lambda x: (x.get('position'), -heur.get(pid(x), -999), n(x.get('price'))))
    states = [{'squad': [], 'ids': set(), 'clubs': {}, 'pos': {}, 'cost': 0, 'heur': 0.0}]
    for pos in ('GKP', 'DEF', 'MID', 'FWD'):
        need = POS_COUNTS[pos]
        rows = [x for x in cands if x.get('position') == pos]
        for _ in range(need):
            expanded = []
            for st in states:
                for x in rows:
                    i = pid(x)
                    if not i or i in st['ids'] or not legal_partial(st, x):
                        continue
                    ct = cost_tenths(x)
                    ns = {
                        'squad': st['squad'] + [x],
                        'ids': set(st['ids']) | {i},
                        'clubs': dict(st['clubs']),
                        'pos': dict(st['pos']),
                        'cost': st['cost'] + ct,
                        'heur': st['heur'] + heur.get(i, 0),
                    }
                    ns['clubs'][x.get('club')] = ns['clubs'].get(x.get('club'), 0) + 1
                    ns['pos'][pos] = ns['pos'].get(pos, 0) + 1
                    if ns['cost'] > budget_t:
                        continue
                    if ns['cost'] + min_remaining_cost(cands, ns['ids'], ns['pos']) > budget_t:
                        continue
                    expanded.append(ns)
            expanded.sort(key=lambda z: z['heur'], reverse=True)
            dedup = []
            seen = set()
            for x in expanded:
                key = tuple(sorted(x['ids']))
                if key in seen:
                    continue
                seen.add(key)
                dedup.append(x)
                if len(dedup) >= BEAM_WIDTH:
                    break
            states = dedup
            if not states:
                return [], {'candidate_count': len(cands), 'beam_width': BEAM_WIDTH, 'failure': f'no states at {pos}'}
    finals = []
    for st in states[:max(FINALISTS * 6, FINALISTS)]:
        if len(st['squad']) != 15:
            continue
        score = final_score(st['squad'])
        finals.append((score, st))
    finals.sort(key=lambda z: z[0], reverse=True)
    return [x[1] for x in finals[:FINALISTS]], {'candidate_count': len(cands), 'beam_width': BEAM_WIDTH, 'finalists_scored': len(finals)}


def squad_summary(state, exp, gws, objective):
    rows = []
    total = 0.0
    for gw in gws:
        pts, xi, cap = p.lineup_expected(state['squad'], gw, exp)
        total += pts
        rows.append({'gw': gw, 'expected_points': round(pts, 2), 'xi_ids': xi, 'captain_id': cap})
    return {
        'objective': objective,
        'expected_objective_points': round(total, 2),
        'cost': round(state['cost'] / 10, 1),
        'squad': [
            {
                'player_id': pid(x),
                'player': x.get('player'),
                'club': x.get('club'),
                'position': x.get('position'),
                'price': n(x.get('price')),
            } for x in state['squad']
        ],
        'gameweeks': rows,
    }


def run():
    latest = load(LATEST, {})
    pool = load(POOL, {})
    scout = load(SCOUT, {})
    market = load(MARKET, {})
    budget_state = load(BUDGET, {})
    next_gw = int(latest.get('next_gw') or 0)
    gws = list(range(next_gw, min(39, next_gw + 6)))
    if not gws:
        raise RuntimeError('No future gameweeks')
    budget = n(budget_state.get('spendable_budget'), 100.0)
    maturity = maturity_weight(next_gw)
    scout_map = s.scout_lookup(scout)
    market_map = s.market_lookup(market)
    pool_rows = pool.get('players') or []
    pool_scores = [n(x.get('six_gw_score')) for x in pool_rows]
    exp = {gw: {} for gw in gws}
    for x in pool_rows:
        i = pid(x)
        if not i:
            continue
        for gw in gws:
            exp[gw][i] = s.expected_gw(x, gw, scout_map, market_map, pool_scores)

    wc_heur = {pid(x): sum(exp[gw][pid(x)][0] for gw in gws) for x in pool_rows}
    def wc_final(squad):
        return sum(p.lineup_expected(squad, gw, exp)[0] for gw in gws)
    wc_states, wc_meta = construct_squads(pool_rows, budget, wc_heur, wc_final)
    best_wc = squad_summary(wc_states[0], exp, gws, 'Wildcard six-GW horizon') if wc_states else None
    if best_wc:
        best_wc['bank_left'] = round(budget - best_wc['cost'], 2)
        best_wc['search_meta'] = wc_meta

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
        budget_note = 'Budget uses reconstructed selling prices from the purchase ledger and FPL sell-price rule. This is stronger than a market-value proxy but is not labelled exact because the public picks endpoint omits selling prices.'
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
