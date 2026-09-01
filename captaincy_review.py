import json
from datetime import datetime, timezone
from pathlib import Path

import captaincy_model as cm
import simulation_engine as s
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
OUT = Path('data/captaincy_review.json')


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def pid(x):
    return int(x.get('player_id') or x.get('id') or 0)


def reasons(p, mean, cv, fixture, edge=None, mode=None):
    out = []
    opp = (fixture or {}).get('opponent') or 'opponent'
    venue = str((fixture or {}).get('venue') or '').upper()
    fdr = s.n((fixture or {}).get('difficulty'), 3)
    if venue == 'H' and fdr <= 2:
        out.append(f'High-ceiling home fixture vs {opp} (FDR {int(fdr)}).')
    elif fdr <= 2:
        out.append(f'Favourable fixture vs {opp} (FDR {int(fdr)}).')
    if s.n(p.get('price')) >= 10:
        out.append('Premium asset with a stronger captaincy ceiling than a normal XI pick.')
    if s.n(p.get('form')) > 0:
        out.append(f"Recent form {s.n(p.get('form')):.1f}; PPG {s.n(p.get('points_per_game')):.1f}.")
    if s.n(p.get('availability'), 1) >= .95:
        out.append('Strong minutes/availability signal.')
    if cv <= .85:
        out.append('Lower projection uncertainty than several alternatives.')
    if edge is not None and edge > .25:
        out.append(f'Captaincy score leads the next option by {edge:.2f}.')
    ownership = s.n(p.get('mini_league_ownership_pct'))
    if mode == 'SAFE' and ownership >= 50:
        out.append(f'{ownership:.0f}% mini-league ownership gives this captain stronger shield value.')
    if mode == 'CHASE' and p.get('chase_eligible') and ownership < 50:
        out.append(f'{ownership:.0f}% mini-league ownership offers leverage without exceeding the EV-gap guardrail.')
    return out[:4]


def compact_mode(row):
    if not row:
        return None
    return {
        'player_id': row.get('player_id'),
        'player': (row.get('player') or {}).get('player'),
        'mean': round(s.n(row.get('mean')), 2),
        'captaincy_score': round(s.n(row.get('captaincy_score')), 3),
        'safe_score': round(s.n(row.get('safe_score')), 3),
        'chase_score': round(s.n(row.get('chase_score')), 3),
        'mini_league_ownership_pct': row.get('mini_league_ownership_pct'),
        'ev_gap_to_best': row.get('ev_gap_to_best'),
        'chase_eligible': row.get('chase_eligible'),
    }


def run():
    latest = load(LATEST, {})
    pool = load(POOL, {})
    scout = load(SCOUT, {})
    market = load(MARKET, {})
    if latest.get('status') != 'SUCCESS':
        raise RuntimeError('latest.json not ready')

    current_gw = int(latest.get('current_gw') or 0)
    gw = int(latest.get('next_gw') or current_gw + 1)
    maturity = season_maturity(current_gw)
    league_context = cm.build_league_context(latest, current_gw)
    by_id, by_name = s.player_maps(pool)
    sm, mm = s.scout_lookup(scout), s.market_lookup(market)
    rows = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    squad = [s.enrich(x, by_id, by_name) for x in rows]
    squad = [x for x in squad if x]
    pool_rows = [x for x in pool.get('players') or [] if pid(x)]
    vals = [s.n(x.get('six_gw_score')) for x in pool_rows]
    lo, hi = s.percentile(vals, .10), s.percentile(vals, .90)

    exp_for_gw = {}
    for p in squad:
        exp_for_gw[pid(p)] = calibrated_expected_gw(p, gw, lo, hi, sm, mm, current_gw=current_gw)

    means = {player_id: values[0] for player_id, values in exp_for_gw.items()}
    xi, _ = s.best_xi(squad, means)
    xi_ids = [pid(p) for p in xi]
    ranked = cm.ranked_candidates(squad, xi_ids, gw, exp_for_gw, league_context=league_context)
    modes = cm.captain_modes(ranked, league_context)

    candidates = []
    for row in ranked:
        p = row['player']
        f = row['fixture']
        candidates.append({
            'player_id': row['player_id'],
            'player': p.get('player'),
            'club': p.get('club'),
            'position': p.get('position'),
            'price': s.n(p.get('price')),
            'opponent': (f or {}).get('opponent'),
            'venue': (f or {}).get('venue'),
            'fixture_difficulty': s.n((f or {}).get('difficulty'), 3),
            'expected_points': round(row['mean'], 2),
            'projection_cv': round(row['cv'], 3),
            'form': s.n(p.get('form')),
            'points_per_game': s.n(p.get('points_per_game')),
            'availability': s.n(p.get('availability'), 1),
            'captaincy_score': round(row['captaincy_score'], 3),
            'safe_score': round(s.n(row.get('safe_score')), 3),
            'chase_score': round(s.n(row.get('chase_score')), 3),
            'mini_league_ownership_pct': row.get('mini_league_ownership_pct'),
            'mini_league_effective_ownership_pct': row.get('mini_league_effective_ownership_pct'),
            'ev_gap_to_best': row.get('ev_gap_to_best'),
            'chase_eligible': row.get('chase_eligible'),
        })

    top = candidates[:5]
    if not top:
        raise RuntimeError('No captaincy candidates')
    by_candidate_id = {int(x['player_id']): x for x in candidates}
    recommended_row = modes.get('recommended') or ranked[0]
    leader = by_candidate_id[int(recommended_row['player_id'])]
    vice = next((x for x in candidates if x['player_id'] != leader['player_id']), None)
    best_ev = compact_mode(modes.get('BEST_EV'))
    safe = compact_mode(modes.get('SAFE'))
    chase = compact_mode(modes.get('CHASE'))

    base_sorted = sorted(candidates, key=lambda x: x['captaincy_score'], reverse=True)
    base_edge = base_sorted[0]['captaincy_score'] - (base_sorted[1] if len(base_sorted) > 1 else base_sorted[0])['captaincy_score']
    leader['reasons'] = reasons(leader, leader['expected_points'], leader['projection_cv'], {
        'opponent': leader.get('opponent'), 'venue': leader.get('venue'), 'difficulty': leader.get('fixture_difficulty')
    }, base_edge if modes.get('recommended_mode') == 'BEST_EV' else None, modes.get('recommended_mode'))
    for c in top:
        if c['player_id'] == leader['player_id']:
            continue
        c['reasons'] = reasons(c, c['expected_points'], c['projection_cv'], {
            'opponent': c.get('opponent'), 'venue': c.get('venue'), 'difficulty': c.get('fixture_difficulty')
        })
        c['gap_to_best_ev'] = round(base_sorted[0]['captaincy_score'] - c['captaincy_score'], 3)

    confidence = max(45, min(90, round(58 + base_edge * 9 + max(0, .9 - leader['projection_cv']) * 18)))
    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 3,
        'next_gw': gw,
        'season_maturity_weight': round(maturity, 3),
        'recommended_xi_ids': xi_ids,
        'captain': leader,
        'vice_captain': vice,
        'shortlist': top,
        'confidence': confidence,
        'score_edge_to_second_best_ev': round(base_edge, 3),
        'league_strategy': {
            'posture': league_context.get('posture'),
            'season_stage': league_context.get('season_stage'),
            'gap_to_leader': league_context.get('gap_to_leader'),
            'recommended_mode': modes.get('recommended_mode'),
            'best_ev': best_ev,
            'safe': safe,
            'chase': chase,
            'guardrail': 'Chase leverage is considered only when the candidate lies inside the season-stage EV tolerance. Early season defaults to Best-EV.'
        },
        'method_note': 'Captaincy uses the shared calibrated football model first, then an explicit league-state overlay. Safe mode values rival coverage, Chase mode values leverage only inside an EV-gap guardrail, and Best-EV remains mandatory early season when mini-league position is noisy.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'captain': leader['player'], 'vice': (vice or {}).get('player'), 'mode': modes.get('recommended_mode'), 'posture': league_context.get('posture'), 'confidence': confidence, 'version': 3}))


if __name__ == '__main__':
    run()
