import json
from datetime import datetime, timezone
from pathlib import Path

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


def first_fixture(p, gw):
    for f in p.get('fixtures') or []:
        if int(f.get('gw') or 0) == int(gw):
            return f
    return (p.get('fixtures') or [None])[0]


def position_ceiling(pos):
    return {'GKP': .76, 'DEF': .88, 'MID': 1.08, 'FWD': 1.12}.get(pos, 1.0)


def premium_bonus(p):
    price = s.n(p.get('price'))
    pos = p.get('position')
    threshold = {'GKP': 5.0, 'DEF': 6.0, 'MID': 8.5, 'FWD': 9.0}.get(pos, 99)
    return .65 if price >= threshold else 0


def captain_score(p, mean, cv, fixture):
    venue = str((fixture or {}).get('venue') or '').upper()
    fdr = s.n((fixture or {}).get('difficulty'), 3)
    form = s.n(p.get('form'))
    ppg = s.n(p.get('points_per_game'))
    avail = s.n(p.get('availability'), 1)
    price = s.n(p.get('price'))
    score = mean * position_ceiling(p.get('position'))
    score += max(0, 4 - fdr) * .42
    score += .35 if venue == 'H' else 0
    score += min(1.2, form * .08)
    score += min(1.0, ppg * .07)
    score += premium_bonus(p)
    score += min(.45, max(0, price - 10) * .04)
    score += avail * .5
    score -= max(0, cv - .8) * 1.4
    return score


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

    candidates = []
    for p in squad:
        mean, cv = calibrated_expected_gw(p, gw, lo, hi, sm, mm, current_gw=current_gw)
        f = first_fixture(p, gw)
        score = captain_score(p, mean, cv, f)
        candidates.append({
            'player_id': pid(p),
            'player': p.get('player'),
            'club': p.get('club'),
            'position': p.get('position'),
            'price': s.n(p.get('price')),
            'opponent': (f or {}).get('opponent'),
            'venue': (f or {}).get('venue'),
            'fixture_difficulty': s.n((f or {}).get('difficulty'), 3),
            'expected_points': round(mean, 2),
            'projection_cv': round(cv, 3),
            'form': s.n(p.get('form')),
            'points_per_game': s.n(p.get('points_per_game')),
            'availability': s.n(p.get('availability'), 1),
            'captaincy_score': round(score, 3),
        })

    candidates.sort(key=lambda x: x['captaincy_score'], reverse=True)
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
        'version': 1,
        'next_gw': gw,
        'season_maturity_weight': round(maturity, 3),
        'captain': leader,
        'vice_captain': vice,
        'shortlist': top,
        'confidence': confidence,
        'score_edge_to_second': round(edge, 3),
        'method_note': 'Captaincy is modelled separately from XI selection. It combines calibrated expected points with fixture ceiling, premium/position ceiling, availability, recent output and projection uncertainty. This avoids automatically captaining the highest XI-selection score.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'captain': leader['player'], 'vice': (vice or {}).get('player'), 'confidence': confidence}))


if __name__ == '__main__':
    run()
