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


def reasons(p, mean, cv, fixture, edge=None):
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
    return out[:4]


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

    # Captain candidates must be in the legal recommended XI. This avoids ever naming a
    # bench player captain merely because their standalone captain score is attractive.
    means = {player_id: vals[0] for player_id, vals in exp_for_gw.items()}
    xi, _ = s.best_xi(squad, means)
    xi_ids = [pid(p) for p in xi]
    ranked = cm.ranked_candidates(squad, xi_ids, gw, exp_for_gw)

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
        })

    top = candidates[:5]
    if not top:
        raise RuntimeError('No captaincy candidates')
    leader = top[0]
    vice = top[1] if len(top) > 1 else None
    edge = leader['captaincy_score'] - (vice or leader)['captaincy_score']
    leader['reasons'] = reasons(leader, leader['expected_points'], leader['projection_cv'], {
        'opponent': leader.get('opponent'), 'venue': leader.get('venue'), 'difficulty': leader.get('fixture_difficulty')
    }, edge)
    for c in top[1:]:
        c['reasons'] = reasons(c, c['expected_points'], c['projection_cv'], {
            'opponent': c.get('opponent'), 'venue': c.get('venue'), 'difficulty': c.get('fixture_difficulty')
        })
        c['gap_to_leader'] = round(leader['captaincy_score'] - c['captaincy_score'], 3)

    confidence = max(45, min(90, round(58 + edge * 9 + max(0, .9 - leader['projection_cv']) * 18)))
    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 2,
        'next_gw': gw,
        'season_maturity_weight': round(maturity, 3),
        'recommended_xi_ids': xi_ids,
        'captain': leader,
        'vice_captain': vice,
        'shortlist': top,
        'confidence': confidence,
        'score_edge_to_second': round(edge, 3),
        'method_note': 'Captaincy uses the shared captaincy model also used by simulations. Candidates are restricted to the legal recommended XI, then ranked by calibrated expected points, fixture ceiling, premium/position ceiling, availability, recent output and uncertainty.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'captain': leader['player'], 'vice': (vice or {}).get('player'), 'confidence': confidence, 'version': 2}))


if __name__ == '__main__':
    run()
